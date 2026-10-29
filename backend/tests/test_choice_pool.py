"""물건형 선택지는 코드가 정한 후보(에셋 목록 - 이미 쓴 것)에서만 나오게 한다.
모델이 목록 밖 ID를 지어내거나 비워 보내도, 후보에서 채워 실패하지 않게 한다."""
import json

from app.catalog import load_catalog
from app.story.generator import generate_segment
from app.story.prompt import StoryContext, allowed_choices, build_messages
from app.story.safety import load_banned_words
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()
CTX = StoryContext(cards=["rabbit", "rose", "star"], history=[], chosen=[])


def raw(choices):
    data = json.loads(segment_json(pages=3))
    data["choices"] = choices
    return json.dumps(data, ensure_ascii=False)


def test_allowed_choices_exclude_cards():
    pool = allowed_choices(CTX, cat)
    assert "rabbit" not in pool and "dragon" in pool
    assert set(pool) <= cat.choice_ids()


def test_v6_prompt_lists_candidates():
    user = build_messages(CTX, "intro", cat, version="v6")[1]["content"]
    assert "선택지 후보" in user and "dragon(아기 용)" in user and "rabbit(토끼)" not in user.split("선택지 후보")[1]


def test_invented_ids_are_filled_from_pool():
    sent = [{"id": i, "label": i} for i in ("dragon", "stone", "box")]
    r = validate_segment(raw(sent), "middle", cat, banned, fill_pool=["moon", "apple", "ship"])
    assert r.ok
    ids = [c.id for c in r.segment.choices]
    assert ids[0] == "dragon" and len(ids) == 4 and set(ids[1:]) <= {"moon", "apple", "ship"}
    assert r.filled and set(r.filled) <= {"moon", "apple", "ship"}


def test_empty_choices_are_filled():
    r = validate_segment(raw([]), "middle", cat, banned, fill_pool=["moon", "apple", "ship", "kite", "map"])
    assert r.ok and len(r.segment.choices) == 4
    assert all(c.label == cat.name_of(c.id) for c in r.segment.choices)


def test_fill_skips_items_already_in_scene():
    # 장면에 rabbit(토끼), rose, star 가 있음
    r = validate_segment(raw([]), "middle", cat, banned, fill_pool=["rose", "moon", "apple", "ship"])
    assert "rose" not in [c.id for c in r.segment.choices]


def test_generator_fills_instead_of_failing():
    llm = FakeLLM("p", [raw([{"id": "stone", "label": "돌"}])])
    r = generate_segment(CTX, "intro", primary=llm, secondary=None, catalog=cat, banned=banned, version="v6")
    assert len(r.attempts) == 1 and len(r.segment.choices) == 4
