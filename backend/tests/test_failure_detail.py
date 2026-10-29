"""실패 원인을 자세히 남기기: 모델이 보낸 선택지, 검증에서 빠진 항목, 페이지 수."""
import json

from app.catalog import load_catalog
from app.llm.client import LLMError
from app.story.generator import GenerationFailed, generate_segment
from app.story.prompt import StoryContext
from app.story.safety import load_banned_words
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()


def test_validation_result_keeps_what_model_sent():
    r = validate_segment(segment_json(pages=3, choices=("dragon", "dragon", "alien")), "middle", cat, banned)
    assert r.sent_choices == ["dragon", "dragon", "alien"]
    assert r.page_count == 3
    assert "alien" in r.dropped


def test_empty_choices_recorded_as_empty():
    data = json.loads(segment_json(pages=3))
    data["choices"] = []
    r = validate_segment(json.dumps(data, ensure_ascii=False), "middle", cat, banned)
    assert r.sent_choices == []
    assert "choices" in r.errors


def test_failed_attempts_carry_detail():
    ctx = StoryContext(cards=["rabbit", "rose", "star"], history=[], chosen=[])
    bad = segment_json(pages=1, choices=("rose", "star", "rabbit"))  # 페이지 부족 + 전부 카드
    try:
        generate_segment(ctx, "intro", primary=FakeLLM("p", [bad, bad]), secondary=None,
                         catalog=cat, banned=banned, version="v5")
        raise AssertionError("실패해야 함")
    except GenerationFailed as e:
        a = e.attempts[0]
        assert a.sent_choices == ["rose", "star", "rabbit"]
        assert set(a.dropped) >= {"rose", "star", "rabbit"}
        assert a.page_count == 1
        assert "page_count" in a.errors


def test_llm_error_attempt_has_message():
    ctx = StoryContext(cards=["rabbit", "rose", "star"], history=[], chosen=[])
    try:
        generate_segment(ctx, "intro", primary=FakeLLM("p", [LLMError("HTTP 503: overloaded", status=503)]),
                         secondary=None, catalog=cat, banned=banned, version="v5")
    except GenerationFailed as e:
        assert "overloaded" in e.attempts[0].message
