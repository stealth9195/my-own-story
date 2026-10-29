"""관대한 모드(lenient): 형식·안전 문제만 거절하고, 나머지 규칙 위반은 경고로 남긴 채 결과를 쓴다.
실험 서버는 결과를 먼저 보는 게 중요해서 관대한 모드로 생성한다."""
import json

from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.lab.api import create_app
from app.story.generator import generate_segment
from app.story.prompt import StoryContext
from app.story.safety import load_banned_words
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()
POOL = ["moon", "apple", "ship", "kite", "map"]


def test_page_count_is_warning_in_lenient_mode():
    r = validate_segment(segment_json(pages=1), "middle", cat, banned, lenient=True, fill_pool=POOL)
    assert r.ok
    assert "page_count" in r.warnings and r.errors == []


def test_unsafe_still_rejected_in_lenient_mode():
    data = json.loads(segment_json(pages=3))
    data["pages"][0]["text"] = "용이 기사를 죽였어요."
    r = validate_segment(json.dumps(data, ensure_ascii=False), "middle", cat, banned, lenient=True)
    assert not r.ok and "unsafe" in r.errors


def test_broken_json_still_rejected_in_lenient_mode():
    r = validate_segment("{pages", "middle", cat, banned, lenient=True)
    assert not r.ok


def test_bad_phrase_choices_replaced_by_items_in_lenient_mode():
    data = json.loads(segment_json(pages=3))
    data["choices"] = [{"kind": "phrase", "label": "가" * 40}]
    r = validate_segment(json.dumps(data, ensure_ascii=False), "middle", cat, banned,
                         lenient=True, fill_pool=POOL)
    assert r.ok and len(r.segment.choices) >= 3
    assert all(c.kind == "item" for c in r.segment.choices)


def test_mixed_choices_keep_items_in_lenient_mode():
    data = json.loads(segment_json(pages=3))
    data["choices"] = [{"kind": "phrase", "label": "커다랬어요."}, {"kind": "item", "id": "dragon", "label": "아기 용"}]
    r = validate_segment(json.dumps(data, ensure_ascii=False), "middle", cat, banned,
                         lenient=True, fill_pool=POOL)
    assert r.ok and "dragon" in [c.id for c in r.segment.choices]
    assert "mixed_choices" in r.warnings


def test_generator_accepts_first_try_with_warnings():
    ctx = StoryContext(cards=["rabbit", "rose", "star"], history=[], chosen=[])
    r = generate_segment(ctx, "intro", primary=FakeLLM("p", [segment_json(pages=1)]), secondary=None,
                         catalog=cat, banned=banned, version="v6", lenient=True)
    assert len(r.attempts) == 1 and r.attempts[0].ok
    assert "page_count" in r.attempts[0].warnings


def test_lab_uses_lenient_mode():
    app = create_app(models={"f": lambda: FakeLLM("f", [segment_json(pages=1)])}, tts_fn=lambda *a: b"")
    r = TestClient(app).post("/api/stories", json={"cards": ["rabbit", "rose", "star"], "model": "f",
                                                   "choice_count": 2})
    assert r.status_code == 200
    assert "page_count" in r.json()["attempts"][0]["warnings"]
