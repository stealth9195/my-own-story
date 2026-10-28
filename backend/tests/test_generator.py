import pytest

from app.catalog import load_catalog
from app.llm.client import LLMError
from app.story.generator import GenerationFailed, generate_segment
from app.story.prompt import StoryContext
from app.story.safety import load_banned_words
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()
CTX = StoryContext(cards=["rabbit", "rose", "star"], history=[], chosen=[])
GOOD = segment_json()
BAD = "not json"


def run(primary, secondary=None):
    return generate_segment(CTX, "intro", primary=primary, secondary=secondary,
                            catalog=cat, banned=banned)


def test_first_try_valid():
    r = run(FakeLLM("p", [GOOD]), FakeLLM("s", []))
    assert len(r.attempts) == 1
    assert r.model_used == "p"
    assert len(r.segment.pages) == 3


def test_invalid_then_valid_retries_same_model():
    r = run(FakeLLM("p", [BAD, GOOD]), FakeLLM("s", []))
    assert [a.model for a in r.attempts] == ["p", "p"]
    assert [a.ok for a in r.attempts] == [False, True]
    assert r.latency_ms == 20


def test_invalid_twice_uses_secondary():
    r = run(FakeLLM("p", [BAD, BAD]), FakeLLM("s", [GOOD]))
    assert [a.model for a in r.attempts] == ["p", "p", "s"]
    assert r.model_used == "s"


def test_llm_error_skips_retry_and_uses_secondary():
    primary = FakeLLM("p", [LLMError("limit", status=429)])
    r = run(primary, FakeLLM("s", [GOOD]))
    assert len(r.attempts) == 2
    assert r.attempts[0].errors == ["llm_error:429"]
    assert primary.calls == 1


def test_all_fail_raises_with_attempts():
    with pytest.raises(GenerationFailed) as e:
        run(FakeLLM("p", [BAD, BAD]), FakeLLM("s", [BAD]))
    assert len(e.value.attempts) == 3


def test_no_secondary_fails_after_two():
    with pytest.raises(GenerationFailed) as e:
        run(FakeLLM("p", [BAD, BAD]), None)
    assert len(e.value.attempts) == 2
