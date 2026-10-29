from dataclasses import dataclass, field
from typing import Protocol

from app.catalog import Catalog
from app.llm.client import LLMError, LLMResponse
from app.story.prompt import (StoryContext, allowed_choices, build_messages, forbidden_choices,
                              offered_phrases, unchosen_ids)
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
    # 실패 원인 확인용
    dropped: list[str] = field(default_factory=list)       # 검증에서 빠진 항목
    sent_choices: list[str] = field(default_factory=list)  # 모델이 보낸 선택지
    page_count: int = 0
    message: str = ""                                      # API 오류 내용
    warnings: list[str] = field(default_factory=list)      # 관대한 모드에서 통과시킨 규칙 위반


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
    version: str = "v2",
    max_page_chars: int = 150,
    lenient: bool = False,
) -> GenerationResult:
    """기본 1차 → (검증 실패 시) 기본 2차 → 예비 1회. 기본에서 LLMError면 바로 예비로."""
    messages = build_messages(ctx, segment_type, catalog, version)
    rules = {"forbidden_choices": forbidden_choices(ctx), "forbidden_scene": unchosen_ids(ctx),
             "cards": ctx.cards, "forbidden_phrases": offered_phrases(ctx),
             "fill_pool": allowed_choices(ctx, catalog)}
    attempts: list[Attempt] = []

    def try_once(llm: LLM) -> Segment | None:
        try:
            resp = llm.complete(messages)
        except LLMError as e:
            attempts.append(Attempt(llm.model, False, [f"llm_error:{e.status}"], 0, message=str(e)[:200]))
            raise
        result = validate_segment(resp.text, segment_type, catalog, banned, max_page_chars,
                                  lenient=lenient, **rules)
        attempts.append(Attempt(llm.model, result.ok, result.errors, resp.latency_ms,
                                dropped=result.dropped, sent_choices=result.sent_choices,
                                page_count=result.page_count, warnings=result.warnings))
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
