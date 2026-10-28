"""실험용 서버: 모델·카드·선택지를 골라 이야기를 구간별로 생성하고 음성을 들어본다.
저장소 없이 메모리에만 보관한다 (서버를 끄면 사라짐)."""

import json
import os
import uuid
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.catalog import load_catalog
from app.llm.client import OpenAICompatClient
from app.story.generator import LLM, GenerationFailed, generate_segment
from app.story.prompt import StoryContext
from app.story.safety import load_banned_words
from app.tts import gemini as gemini_tts

BACKEND_DIR = Path(__file__).resolve().parents[2]
PAGE = Path(__file__).with_name("lab.html")

TTSFn = Callable[[str, str, str], bytes]


class StartRequest(BaseModel):
    cards: list[str] = Field(min_length=3, max_length=5)
    model: str
    choice_count: int = Field(default=4, ge=2, le=5)


class NextRequest(BaseModel):
    choice_id: str


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str
    model: str


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


def default_tts(text: str, voice: str, model: str) -> bytes:
    return gemini_tts.synthesize(text, voice, os.environ.get("GEMINI_API_KEY", ""), model)


def segment_types(choice_count: int) -> list[str]:
    return ["intro"] + ["middle"] * (choice_count - 1) + ["ending"]


def create_app(models: dict[str, Callable[[], LLM]] | None = None,
               tts_fn: TTSFn | None = None) -> FastAPI:
    app = FastAPI(title="my-own-story 실험실")
    catalog, banned = load_catalog(), load_banned_words()
    models = models if models is not None else load_model_factories()
    tts_fn = tts_fn or default_tts
    stories: dict[str, dict] = {}

    def generate(story: dict) -> dict:
        index = len(story["ctx"].history)
        seg_type = story["types"][index]
        try:
            gen = generate_segment(story["ctx"], seg_type, primary=story["llm"], secondary=None,
                                   catalog=catalog, banned=banned)
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
        }

    @app.get("/")
    def index():
        return FileResponse(PAGE)

    @app.get("/api/config")
    def config():
        return {
            "cards": [{"id": c, "name": catalog.name_of(c)} for c in catalog.card_ids()],
            "models": list(models),
            "tts_models": gemini_tts.MODELS,
            "voices": gemini_tts.VOICES,
        }

    @app.post("/api/stories")
    def start(req: StartRequest):
        if not set(req.cards) <= set(catalog.card_ids()):
            raise HTTPException(400, "없는 카드")
        if req.model not in models:
            raise HTTPException(400, "없는 모델")
        story = {"id": uuid.uuid4().hex[:8], "llm": models[req.model](),
                 "types": segment_types(req.choice_count),
                 "ctx": StoryContext(cards=req.cards, history=[], chosen=[])}
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
            audio = tts_fn(req.text, req.voice, req.model)
        except gemini_tts.TTSError as e:
            status = e.status if e.status in (400, 429) else 502
            raise HTTPException(status, str(e)[:300])
        return Response(audio, media_type="audio/wav")

    return app
