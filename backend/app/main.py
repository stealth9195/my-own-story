"""서비스 API. 실행: uv run --env-file .env uvicorn --factory app.main:build_app --port 8000"""

import json
import logging
import random
import time
import uuid
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.limits import Limits
from app.api.log import log_event
from app.api.schemas import (EventRequest, NextRequest, SegmentResponse, SignedSegment, StartRequest,
                             StoryKey, TTSRequest)
from app.api.signing import BadSignature, sign_segment, verify_history, verify_segment
from app.api.tts_service import TTSFn, default_tts, synthesize_segment
from app.api.voice import pick_voice
from app.catalog import load_catalog
from app.config import Settings
from app.llm.client import OpenAICompatClient
from app.story.generator import LLM, GenerationFailed, generate_segment
from app.story.prompt import StoryContext
from app.story.safety import load_banned_words
from app.story.schema import Segment
from app.story.start import segment_types, start_options, valid_cards
from app.tts.gemini import TTSError

MAX_EVENT_PAYLOAD = 2000  # 사용 기록 payload 글자 수 (JSON)


def _fail(status: int, code: str):
    raise HTTPException(status, {"code": code})


def create_app(settings: Settings, primary: LLM, secondary: LLM | None, *,
               tts: TTSFn | None = None, limits: Limits | None = None,
               rng: random.Random | None = None) -> FastAPI:
    app = FastAPI(title="my-own-story")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    catalog, banned = load_catalog(), load_banned_words()
    tts = tts or default_tts(settings.gemini_api_key, settings.typecast_api_key)
    limits = limits or Limits(settings.daily_stories_per_user, settings.daily_stories_total)
    rng = rng or random.Random()

    def generate(story: StoryKey, history: list[Segment], chosen: list[str]) -> SegmentResponse:
        index = len(history)
        seg_type = segment_types(story.choice_count)[index]
        ctx = StoryContext(cards=story.cards, history=history, chosen=chosen,
                           total_segments=story.choice_count + 1)
        try:
            gen = generate_segment(ctx, seg_type, primary=primary, secondary=secondary,
                                   catalog=catalog, banned=banned, version=settings.prompt_version,
                                   max_page_chars=settings.max_page_chars, lenient=True)
        except GenerationFailed as e:
            log_event("segment_failed", story_id=story.id, index=index, type=seg_type,
                      attempts=[asdict(a) for a in e.attempts])
            _fail(502, "generation_failed")
        log_event("segment", story_id=story.id, index=index, type=seg_type, model_used=gen.model_used,
                  latency_ms=gen.latency_ms, attempts=[asdict(a) for a in gen.attempts],
                  warnings=sorted({w for a in gen.attempts for w in a.warnings}))
        signed = SignedSegment(segment=gen.segment,
                               sig=sign_segment(settings.story_secret, story, index, gen.segment))
        return SegmentResponse(story=story, index=index, segment=signed, done=seg_type == "ending")

    def charge_extra(voice, extra_calls: int, chars: int) -> None:
        """예약분을 넘어 실제로 더 부른 만큼 사용량에 더한다 (재시도·같은 구간 두 번째 요청)."""
        if extra_calls <= 0:
            return
        if voice.provider == "gemini":
            limits.reserve_gemini(voice.model, extra_calls)
        elif voice.provider == "typecast":
            limits.reserve_typecast(chars * extra_calls)

    @app.get("/api/start-options")
    def get_start_options():
        return start_options(catalog, rng)

    @app.post("/api/stories")
    def start(req: StartRequest) -> SegmentResponse:
        if not valid_cards(catalog, req.cards):
            _fail(400, "bad_cards")
        result = limits.try_start_story(req.anon_id)
        if result != "ok":
            _fail(429, result)
        story = StoryKey(id=uuid.uuid4().hex[:12], cards=req.cards, choice_count=req.choice_count,
                         voice=pick_voice(limits, req.choice_count, rng))
        log_event("story_start", story_id=story.id, anon_id=req.anon_id, cards=story.cards,
                  voice=story.voice.model_dump())
        return generate(story, [], [])

    @app.post("/api/stories/next")
    def next_segment(req: NextRequest) -> SegmentResponse:
        try:
            history = verify_history(settings.story_secret, req.story, req.history)
        except BadSignature:
            _fail(400, "bad_signature")
        if history[-1].type == "ending":
            _fail(409, "ended")
        if len(req.chosen) != len(history) or len(history) > req.story.choice_count:
            _fail(400, "bad_order")
        for seg, choice in zip(history, req.chosen):
            if choice not in {c.id for c in seg.choices}:
                _fail(400, "bad_choice")
        if not limits.allow_generate(req.story.id, len(history)):
            _fail(429, "regen_limit")
        return generate(req.story, history, req.chosen)

    @app.post("/api/tts")
    def segment_tts(req: TTSRequest):
        try:
            segment = verify_segment(settings.story_secret, req.story, req.index, req.segment)
        except BadSignature:
            _fail(400, "bad_signature")
        if req.story.voice.provider == "browser":
            _fail(400, "browser_voice")
        reserved = limits.tts_requests(req.story.id, req.index) == 0  # 구간마다 첫 호출 1번은 시작 때 예약됨
        if not limits.allow_tts(req.story.id, req.index):
            _fail(429, "tts_limit")
        text = "\n".join(p.text for p in segment.pages)
        voice = req.story.voice
        calls = 0

        def counted(text: str, voice):
            nonlocal calls
            calls += 1
            return tts(text, voice)

        started = time.perf_counter()
        try:
            audio = synthesize_segment(text, voice, counted)
        except TTSError as e:
            charge_extra(voice, calls - reserved, len(text))
            log_event("tts_failed", story_id=req.story.id, index=req.index,
                      voice=req.story.voice.model_dump(), status=e.status)
            _fail(502, "tts_failed")
        charge_extra(voice, calls - reserved, len(text))
        log_event("tts", story_id=req.story.id, index=req.index, voice=req.story.voice.model_dump(),
                  chars=len(text), bytes=len(audio), latency_ms=int((time.perf_counter() - started) * 1000))
        return Response(audio, media_type="audio/mpeg")

    @app.post("/api/events", status_code=204)
    def event(req: EventRequest):
        if len(json.dumps(req.payload, ensure_ascii=False)) > MAX_EVENT_PAYLOAD:
            _fail(413, "payload_too_big")
        log_event("client", anon_id=req.anon_id, story_id=req.story_id, type=req.type, payload=req.payload)
        return Response(status_code=204)

    return app


def build_clients(s: Settings) -> tuple[OpenAICompatClient, OpenAICompatClient | None]:
    primary = OpenAICompatClient(s.primary_base_url, s.primary_api_key, s.primary_model,
                                 json_mode=s.primary_json_mode, timeout=s.primary_timeout)
    secondary = None
    if s.secondary_base_url and s.secondary_api_key and s.secondary_model:
        secondary = OpenAICompatClient(s.secondary_base_url, s.secondary_api_key, s.secondary_model,
                                       json_mode=s.secondary_json_mode, timeout=s.secondary_timeout)
    return primary, secondary


def build_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    s = Settings()
    return create_app(s, *build_clients(s))
