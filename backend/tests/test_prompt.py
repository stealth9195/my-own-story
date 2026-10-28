import pytest

from app.catalog import load_catalog
from app.story.prompt import StoryContext, build_messages
from app.story.schema import Page, Scene, Segment

cat = load_catalog()
CARDS = ["rabbit", "rose", "star"]


def one_segment():
    page = Page(text="토끼가 숲에 갔어요.", scene=Scene(background="forest"))
    return Segment(type="intro", pages=[page])


def test_system_contains_catalog_listing():
    msgs = build_messages(StoryContext(cards=CARDS, history=[], chosen=[]), "intro", cat)
    assert msgs[0]["role"] == "system"
    assert "rabbit(토끼)" in msgs[0]["content"]
    assert "{catalog}" not in msgs[0]["content"]


def test_intro_user_message_has_card_names_and_no_history():
    user = build_messages(StoryContext(cards=CARDS, history=[], chosen=[]), "intro", cat)[1]
    assert user["role"] == "user"
    for name in ["토끼", "장미", "별"]:
        assert name in user["content"]
    assert "지금까지의 이야기" not in user["content"]
    assert "3페이지" in user["content"]


def test_middle_includes_history_and_last_choice_name():
    ctx = StoryContext(cards=CARDS, history=[one_segment()], chosen=["dragon"])
    user = build_messages(ctx, "middle", cat)[1]["content"]
    assert "토끼가 숲에 갔어요." in user
    assert "아기 용" in user
    assert "3~4페이지" in user


def test_ending_requests_empty_choices():
    ctx = StoryContext(cards=CARDS, history=[one_segment()], chosen=["dragon"])
    user = build_messages(ctx, "ending", cat)[1]["content"]
    assert "빈 배열" in user
    assert "4~5페이지" in user


def test_unknown_version_raises():
    ctx = StoryContext(cards=CARDS, history=[], chosen=[])
    with pytest.raises(FileNotFoundError):
        build_messages(ctx, "intro", cat, version="v999")
