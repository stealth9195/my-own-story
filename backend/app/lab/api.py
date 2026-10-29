"""실험용 서버: 모델·카드·선택지를 골라 이야기를 구간별로 생성하고 음성을 들어본다.
저장소 없이 메모리에만 보관한다 (서버를 끄면 사라짐)."""

import json
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.catalog import load_catalog
from app.config import REPO_ROOT
from app.llm.client import OpenAICompatClient
from app.story.generator import LLM, GenerationFailed, generate_segment
from app.story.prompt import StoryContext
from app.story.safety import load_banned_words
from app.tts import gemini as gemini_tts
from app.tts import typecast as typecast_tts

BACKEND_DIR = Path(__file__).resolve().parents[2]
PAGE = Path(__file__).with_name("lab.html")

TTSFn = Callable[[str, str, str, str], bytes]


class StartRequest(BaseModel):
    cards: list[str] = Field(min_length=3, max_length=5)
    model: str
    choice_count: int = Field(default=4, ge=2, le=5)
    prompt_version: str = "v2"
    fallback_model: str | None = None
    race: list[str] = []  # 함께 동시에 돌릴 모델 (가장 먼저 성공한 결과를 씀)


class NextRequest(BaseModel):
    choice_id: str


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str
    model: str
    style: str = "slow"


def load_model_factories(path: Path | None = None) -> dict[str, Callable[[], LLM]]:
    """eval/models.json 형식을 읽어 API 키가 있는 모델만 등록한다."""
    path = path or Path(os.environ.get("LAB_MODELS", BACKEND_DIR / "eval" / "models.json"))
    factories = {}
    for m in json.loads(path.read_text(encoding="utf-8")):
        key = os.environ.get(m["api_key_env"])
        if not key:
            continue
        factories[m["name"]] = lambda m=m, key=key: OpenAICompatClient(
            m["base_url"], key, m["model"], json_mode=m.get("json_mode", True),
            merge_system=m.get("merge_system", False), extra_body=m.get("extra"),
            timeout=m.get("timeout", 60))
    return factories


def load_model_labels(path: Path | None = None) -> dict[str, str]:
    """화면에 보여줄 실제 모델 ID (예: nvidia/nemotron-3.5-super-vl:free)"""
    path = path or Path(os.environ.get("LAB_MODELS", BACKEND_DIR / "eval" / "models.json"))
    return {m["name"]: m["model"] for m in json.loads(path.read_text(encoding="utf-8"))}


def prompt_versions() -> list[str]:
    return sorted(p.name for p in (REPO_ROOT / "prompts").iterdir() if (p / "system.md").exists())


def default_tts(text: str, voice: str, model: str, style: str) -> bytes:
    if model in typecast_tts.MODELS:
        return typecast_tts.synthesize(text, voice, os.environ.get("TYPECAST_API_KEY", ""), model, style)
    return gemini_tts.synthesize(text, voice, os.environ.get("GEMINI_API_KEY", ""), model, style)


def tts_voices() -> dict[str, list[dict]]:
    """음성 모델마다 고를 수 있는 목소리 (값: id, 표시: name)"""
    gemini = [{"id": v, "name": v} for v in gemini_tts.VOICES]
    typecast = [{"id": i, "name": n} for i, n in typecast_tts.VOICES.items()]
    return {**{m: gemini for m in gemini_tts.MODELS}, **{m: typecast for m in typecast_tts.MODELS}}


def segment_types(choice_count: int) -> list[str]:
    return ["intro"] + ["middle"] * (choice_count - 1) + ["ending"]


def create_app(models: dict[str, Callable[[], LLM]] | None = None,
               tts_fn: TTSFn | None = None, labels: dict[str, str] | None = None) -> FastAPI:
    app = FastAPI(title="my-own-story 실험실")
    catalog, banned = load_catalog(), load_banned_words()
    if models is None:
        models, labels = load_model_factories(), labels or load_model_labels()
    labels = labels or {}
    tts_fn = tts_fn or default_tts
    stories: dict[str, dict] = {}

    def run_one(story: dict, seg_type: str, llm: LLM, fallback: LLM | None):
        return generate_segment(story["ctx"], seg_type, primary=llm, secondary=fallback,
                                catalog=catalog, banned=banned, version=story["version"],
                                lenient=True)  # 실험 서버: 결과 먼저, 규칙 위반은 경고로

    def race(story: dict, seg_type: str):
        """여러 모델을 동시에 돌려 가장 먼저 성공한 결과를 쓴다. 늦게 끝난 호출은 버린다(한도는 씀)."""
        pool = ThreadPoolExecutor(max_workers=len(story["racers"]))
        futures = [pool.submit(run_one, story, seg_type, llm, None) for llm in story["racers"]]
        failed: list = []
        try:
            for f in as_completed(futures):
                try:
                    return f.result()
                except GenerationFailed as e:
                    failed += e.attempts
            raise GenerationFailed(failed)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def generate(story: dict) -> dict:
        index = len(story["ctx"].history)
        seg_type = story["types"][index]
        try:
            if len(story["racers"]) > 1:
                gen = race(story, seg_type)
            else:
                gen = run_one(story, seg_type, story["racers"][0], story["fallback"])
        except GenerationFailed as e:
            raise HTTPException(502, {"message": "생성 실패",
                                      "attempts": [asdict(a) for a in e.attempts]})
        story["ctx"].history.append(gen.segment)
        return {
            "story_id": story["id"],
            "index": index,
            "type": seg_type,
            "pages": [p.model_dump() for p in gen.segment.pages],
            "choices": [c.model_dump() for c in gen.segment.choices],
            "model_used": gen.model_used,
            "attempts": [asdict(a) for a in gen.attempts],
            "latency_ms": gen.latency_ms,
            "done": seg_type == "ending",
            "raced": story["race_names"],
        }

    @app.get("/")
    def index():
        return FileResponse(PAGE)

    @app.get("/api/config")
    def config():
        return {
            "cards": [{"id": c, "name": catalog.name_of(c), "kind": catalog.kind_of(c),
                       "emoji": catalog.emoji_of(c)} for c in catalog.card_ids()],
            "models": list(models),
            "model_ids": {n: labels.get(n, n) for n in models},
            "tts_models": gemini_tts.MODELS + typecast_tts.MODELS,
            "voices": tts_voices(),
            "tts_styles": list(gemini_tts.STYLES),
            "prompt_versions": prompt_versions(),
        }

    @app.get("/api/start-options")
    def start_options():
        """처음 선택 4단계 후보를 전체 목록에서 무작위로 뽑는다."""
        def pick(ids, n):
            return [{"id": i, "name": catalog.name_of(i), "kind": catalog.kind_of(i),
                     "emoji": catalog.emoji_of(i)} for i in random.sample(sorted(ids), n)]
        return {
            "heroes": pick(catalog.ids("characters"), 5),
            "traits": pick(catalog.ids("traits"), 4),
            "backgrounds": pick(catalog.ids("backgrounds") | catalog.ids("situations"), 4),
            "objects": pick(catalog.ids("objects"), 4),
        }

    @app.post("/api/stories")
    def start(req: StartRequest):
        if not set(req.cards) <= catalog.start_ids():
            raise HTTPException(400, "없는 카드")
        if not any(catalog.kind_of(c) == "character" for c in req.cards):
            raise HTTPException(400, "캐릭터 카드를 1장 이상 골라야 해요")
        if req.model not in models:
            raise HTTPException(400, "없는 모델")
        if req.fallback_model and req.fallback_model not in models:
            raise HTTPException(400, "없는 예비 모델")
        if any(m not in models for m in req.race):
            raise HTTPException(400, "없는 동시 실행 모델")
        if req.prompt_version not in prompt_versions():
            raise HTTPException(400, "없는 프롬프트 버전")
        race_names = list(dict.fromkeys([req.model, *req.race]))
        story = {"id": uuid.uuid4().hex[:8], "racers": [models[n]() for n in race_names],
                 "race_names": race_names if len(race_names) > 1 else [],
                 "fallback": models[req.fallback_model]() if req.fallback_model else None,
                 "types": segment_types(req.choice_count), "version": req.prompt_version,
                 "ctx": StoryContext(cards=req.cards, history=[], chosen=[],
                                    total_segments=req.choice_count + 1)}
        stories[story["id"]] = story
        return generate(story)

    @app.post("/api/stories/{story_id}/next")
    def next_segment(story_id: str, req: NextRequest):
        story = stories.get(story_id)
        if story is None:
            raise HTTPException(404, "없는 이야기")
        last = story["ctx"].history[-1]
        if last.type == "ending":
            raise HTTPException(409, "이미 끝난 이야기")
        if req.choice_id not in {c.id for c in last.choices}:
            raise HTTPException(400, "제시되지 않은 선택지")
        story["ctx"].chosen.append(req.choice_id)
        return generate(story)

    @app.post("/api/tts")
    def tts(req: TTSRequest):
        try:
            audio = tts_fn(req.text, req.voice, req.model, req.style)
        except gemini_tts.TTSError as e:
            status = e.status if e.status in (400, 402, 429) else 502  # 402: Typecast 크레딧 부족
            raise HTTPException(status, str(e)[:300])
        return Response(audio, media_type="audio/wav")

    return app
