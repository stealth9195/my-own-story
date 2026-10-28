from dataclasses import dataclass
from typing import Protocol

from app.catalog import Catalog
from app.llm.client import LLMError, LLMResponse
from app.story.prompt import StoryContext, build_messages
from app.story.schema import Segment, SegmentType
from app.story.validator import validate_segment


class LLM(Protocol):
    model: str

    def complete(self, messages: list[dict[str, str]], temperature: float = 0.9) -> LLMResponse: ...


@dataclass
class Attempt:
    model: str
    ok: bool
    errors: list[str]
    latency_ms: int


@dataclass
class GenerationResult:
    segment: Segment
    model_used: str
    attempts: list[Attempt]
    latency_ms: int


class GenerationFailed(Exception):
    def __init__(self, attempts: list[Attempt]):
        super().__init__(f"생성 실패 ({len(attempts)}회 시도)")
        self.attempts = attempts


def generate_segment(
    ctx: StoryContext,
    segment_type: SegmentType,
    *,
    primary: LLM,
    secondary: LLM | None,
    catalog: Catalog,
    banned: list[str],
    version: str = "v1",
    max_page_chars: int = 250,
) -> GenerationResult:
    """기본 1차 → (검증 실패 시) 기본 2차 → 예비 1회. 기본에서 LLMError면 바로 예비로."""
    messages = build_messages(ctx, segment_type, catalog, version)
    attempts: list[Attempt] = []

    def try_once(llm: LLM) -> Segment | None:
        try:
            resp = llm.complete(messages)
        except LLMError as e:
            attempts.append(Attempt(llm.model, False, [f"llm_error:{e.status}"], 0))
            raise
        result = validate_segment(resp.text, segment_type, catalog, banned, max_page_chars)
        attempts.append(Attempt(llm.model, result.ok, result.errors, resp.latency_ms))
        return result.segment if result.ok else None

    def done(segment: Segment, llm: LLM) -> GenerationResult:
        total = sum(a.latency_ms for a in attempts)
        return GenerationResult(segment, llm.model, attempts, total)

    try:
        for _ in range(2):
            segment = try_once(primary)
            if segment:
                return done(segment, primary)
    except LLMError:
        pass

    if secondary is not None:
        try:
            segment = try_once(secondary)
            if segment:
                return done(segment, secondary)
        except LLMError:
            pass

    raise GenerationFailed(attempts)
