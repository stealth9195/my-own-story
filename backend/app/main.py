"""서비스 API. 실행: uv run --env-file .env uvicorn --factory app.main:build_app --port 8000"""

import logging
import random
import uuid
from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from app.api.limits import Limits
from app.api.log import log_event
from app.api.schemas import NextRequest, SegmentResponse, SignedSegment, StartRequest, StoryKey
from app.api.signing import BadSignature, sign_segment, verify_history
from app.api.tts_service import TTSFn, default_tts
from app.api.voice import pick_voice
from app.catalog import load_catalog
from app.config import Settings
from app.llm.client import OpenAICompatClient
from app.story.generator import LLM, GenerationFailed, generate_segment
from app.story.prompt import StoryContext
from app.story.safety import load_banned_words
from app.story.schema import Segment
from app.story.start import segment_types, start_options, valid_cards


def _fail(status: int, code: str):
    raise HTTPException(status, {"code": code})


def create_app(settings: Settings, primary: LLM, secondary: LLM | None, *,
               tts: TTSFn | None = None, limits: Limits | None = None,
               rng: random.Random | None = None) -> FastAPI:
    app = FastAPI(title="my-own-story")
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
        return generate(req.story, history, req.chosen)

    return app


def build_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    s = Settings()
    primary = OpenAICompatClient(s.primary_base_url, s.primary_api_key, s.primary_model,
                                 json_mode=s.primary_json_mode)
    secondary = None
    if s.secondary_base_url and s.secondary_api_key and s.secondary_model:
        secondary = OpenAICompatClient(s.secondary_base_url, s.secondary_api_key, s.secondary_model,
                                       json_mode=s.secondary_json_mode)
    return create_app(s, primary, secondary)
