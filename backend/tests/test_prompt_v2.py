import json

from app.catalog import load_catalog
from app.story.generator import generate_segment
from app.story.prompt import StoryContext, build_messages, forbidden_choices, unchosen_ids
from app.story.safety import load_banned_words
from app.story.schema import Choice, Page, Scene, Segment
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()
CARDS = ["rabbit", "rose", "star"]


def intro_with_choices(ids):
    page = Page(text="토끼가 숲에 갔어요.", scene=Scene(background="forest"))
    return Segment(type="intro", pages=[page],
                   choices=[Choice(id=i, label=cat.name_of(i)) for i in ids])


CTX = StoryContext(cards=CARDS, history=[intro_with_choices(["dragon", "cake", "rose"])],
                   chosen=["dragon"])


def test_forbidden_choices_are_previously_offered_and_cards():
    assert forbidden_choices(CTX) == {"dragon", "cake", "rose", "rabbit", "star"}


def test_intro_v2_forbids_cards_as_choices():
    ctx = StoryContext(cards=CARDS, history=[], chosen=[])
    assert forbidden_choices(ctx) == set(CARDS)
    user = build_messages(ctx, "intro", cat, version="v2")[1]["content"]
    assert "이미 나온 선택지" in user and "토끼" in user


def test_unchosen_excludes_chosen_and_cards():
    assert unchosen_ids(CTX) == {"cake"}


def test_v2_user_message_lists_used_and_unchosen_choices():
    user = build_messages(CTX, "middle", cat, version="v2")[1]["content"]
    assert "이미 나온 선택지" in user and "케이크" in user
    assert "고르지 않은 선택지" in user


def test_v1_user_message_unchanged():
    user = build_messages(CTX, "middle", cat, version="v1")[1]["content"]
    assert "이미 나온 선택지" not in user


def test_v2_system_asks_two_sentences():
    system = build_messages(CTX, "middle", cat, version="v2")[0]["content"]
    assert "2문장" in system


def test_validator_drops_forbidden_choices_then_too_few_fails():
    raw = segment_json(pages=3, choices=("dragon", "cake", "star"))
    r = validate_segment(raw, "middle", cat, banned, forbidden_choices={"dragon", "cake"})
    assert "choices" in r.errors
    assert {"dragon", "cake"} <= set(r.dropped)


def test_validator_rejects_unchosen_in_scene():
    data = json.loads(segment_json(pages=3))
    data["pages"][1]["scene"]["objects"] = ["cake"]
    raw = json.dumps(data, ensure_ascii=False)
    r = validate_segment(raw, "middle", cat, banned, forbidden_scene={"cake"})
    assert "unchosen_used" in r.errors


def test_generator_applies_rules_from_context():
    bad = segment_json(pages=3, choices=("dragon", "star", "moon"))  # dragon 반복 → 2개만 남음
    good = segment_json(pages=3, choices=("moon", "apple", "ship"))
    r = generate_segment(CTX, "middle", primary=FakeLLM("p", [bad, good]), secondary=None,
                         catalog=cat, banned=banned, version="v2")
    assert [a.ok for a in r.attempts] == [False, True]
    assert r.attempts[0].errors == ["choices"]
