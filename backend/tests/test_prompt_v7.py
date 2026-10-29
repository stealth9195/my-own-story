"""v7: 선택지 3개, 모든 구간(도입·중간·결말) 2~3페이지."""
import json

from app.catalog import load_catalog
from app.story.generator import generate_segment
from app.story.prompt import StoryContext, build_messages
from app.story.safety import load_banned_words
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()
CTX = StoryContext(cards=["rabbit", "rose", "star"], history=[], chosen=[])


def test_v7_system_asks_three_choices():
    system = build_messages(CTX, "intro", cat, version="v7")[0]["content"]
    assert "반드시 3개" in system and "반드시 4개" not in system


def test_v7_page_instructions():
    # 도입·결말은 3페이지 고정, 중간은 2~3페이지
    assert "3페이지로" in build_messages(CTX, "intro", cat, version="v7")[1]["content"]
    assert "3페이지로" in build_messages(CTX, "ending", cat, version="v7")[1]["content"]
    assert "2~3페이지" in build_messages(CTX, "middle", cat, version="v7")[1]["content"]


def test_v6_instructions_unchanged():
    user = build_messages(CTX, "ending", cat, version="v6")[1]["content"]
    assert "4~5페이지" in user


def test_validator_trims_to_max_choices():
    r = validate_segment(segment_json(pages=3, choices=("dragon", "cake", "moon", "apple")), "middle", cat,
                         banned, max_choices=3)
    assert len(r.segment.choices) == 3


def test_validator_page_range_override():
    r = validate_segment(segment_json(pages=2, choices=()), "ending", cat, banned, page_range=(2, 3))
    assert "page_count" not in r.errors
    r = validate_segment(segment_json(pages=4, choices=()), "ending", cat, banned, page_range=(2, 3))
    assert "page_count" in r.errors


def test_generator_v7_uses_new_limits():
    raw = segment_json(pages=3, choices=("dragon", "cake", "moon", "apple"))
    r = generate_segment(CTX, "intro", primary=FakeLLM("p", [raw]), secondary=None, catalog=cat,
                         banned=banned, version="v7")
    assert r.attempts[0].ok and len(r.segment.choices) == 3


def test_v7_intro_two_pages_is_page_count_error():
    raw = segment_json(pages=2)
    r = generate_segment(CTX, "intro", primary=FakeLLM("p", [raw, raw]), secondary=None, catalog=cat,
                         banned=banned, version="v7", lenient=True)
    assert "page_count" in r.attempts[0].warnings


# --- 5단계 플롯: 발단 - 전개 - 위기 - 절정 - 결말 ---

def ctx_at(index, total):
    from app.story.schema import Page, Scene, Segment
    seg = Segment(type="intro", pages=[Page(text="토끼가 놀았어요.", scene=Scene(background="forest"))])
    return StoryContext(cards=["rabbit", "rose", "star"], history=[seg] * index, chosen=[],
                        total_segments=total)


def test_plot_stage_for_five_segments():
    from app.story.prompt import plot_stage
    assert [plot_stage(i, 5) for i in range(5)] == ["발단", "전개", "위기", "절정", "결말"]


def test_plot_stage_for_four_segments_merges_crisis():
    from app.story.prompt import plot_stage
    assert [plot_stage(i, 4) for i in range(4)] == ["발단", "전개", "위기·절정", "결말"]


def test_plot_stage_for_three_segments():
    from app.story.prompt import plot_stage
    assert [plot_stage(i, 3) for i in range(3)] == ["발단", "전개·위기·절정", "결말"]


def test_v7_user_message_tells_stage():
    user = build_messages(ctx_at(2, 5), "middle", cat, version="v7")[1]["content"]
    assert "'위기'" in user


def test_v7_system_has_five_stage_plot():
    system = build_messages(CTX, "intro", cat, version="v7")[0]["content"]
    for stage in ("발단", "전개", "위기", "절정", "결말"):
        assert stage in system
