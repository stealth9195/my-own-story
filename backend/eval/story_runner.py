from dataclasses import asdict

from app.catalog import Catalog
from app.story.generator import LLM, GenerationFailed, generate_segment
from app.story.prompt import StoryContext


def segment_types(choice_count: int) -> list[str]:
    """선택 횟수 N → 도입 1 + 중간 N-1 + 결말 1."""
    return ["intro"] + ["middle"] * (choice_count - 1) + ["ending"]


def run_story(
    case: dict,
    llm: LLM,
    catalog: Catalog,
    banned: list[str],
    choice_count: int,
    version: str,
) -> dict:
    """이야기 1편을 끝까지 생성. 실패해도 예외 대신 status=failed로 기록."""
    ctx = StoryContext(cards=case["cards"], history=[], chosen=[])
    result = {"case_id": case["id"], "model": llm.model, "version": version,
              "cards": case["cards"], "card_names": [catalog.name_of(c) for c in case["cards"]],
              "status": "done", "segments": [], "failed_at": None}

    for i, seg_type in enumerate(segment_types(choice_count)):
        try:
            gen = generate_segment(ctx, seg_type, primary=llm, secondary=None,
                                   catalog=catalog, banned=banned, version=version)
        except GenerationFailed as e:
            result["status"] = "failed"
            result["failed_at"] = i
            result["failed_attempts"] = [asdict(a) for a in e.attempts]
            return result

        chosen = None
        if gen.segment.choices:
            chosen = gen.segment.choices[case["picks"][i] % len(gen.segment.choices)].id
            ctx.chosen.append(chosen)
        ctx.history.append(gen.segment)
        result["segments"].append({
            "type": seg_type,
            "pages": [p.model_dump() for p in gen.segment.pages],
            "choices": [c.model_dump() for c in gen.segment.choices],
            "chosen": chosen,
            "attempts": [asdict(a) for a in gen.attempts],
            "latency_ms": gen.latency_ms,
        })
    return result


def is_rate_limited(story: dict) -> bool:
    attempts = story.get("failed_attempts") or []
    return bool(attempts) and attempts[-1]["errors"] == ["llm_error:429"]
