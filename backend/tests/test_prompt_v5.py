from app.catalog import load_catalog
from app.story.prompt import StoryContext, build_messages
from app.story.schema import Page, Scene, Segment

cat = load_catalog()
CARDS = ["bear", "cat", "cake"]


def ctx_after_intro(total):
    seg = Segment(type="intro", pages=[Page(text="곰이 케이크를 봤어요.", scene=Scene(background="village"))])
    return StoryContext(cards=CARDS, history=[seg], chosen=[], total_segments=total)


def test_v5_tells_position_in_story():
    user = build_messages(ctx_after_intro(5), "middle", cat, version="v5")[1]["content"]
    assert "전체 5구간 중 2번째" in user


def test_v4_has_no_position_line():
    user = build_messages(ctx_after_intro(5), "middle", cat, version="v4")[1]["content"]
    assert "번째" not in user


def test_v5_system_rules():
    system = build_messages(ctx_after_intro(5), "middle", cat, version="v5")[0]["content"]
    assert "비우지 마" in system          # 빈 선택지 방지
    assert "모순" in system               # 앞뒤가 맞지 않는 문장 방지
    assert "결말 구간에서" in system       # 문제가 너무 일찍 풀리는 것 방지
    assert r"\~" not in system and r"\[" not in system  # 편집기 이스케이프 없음
