"""결말 장면에는 처음 고른 주인공이 꼭 나온다(사용자 요청 2026-10-31).
겪은 문제: 프롬프트·검사기 모두 주인공은 첫 페이지에만 요구해, 결말 장면에서 주인공이 빠지는 이야기가 있었다.
LLM 을 다시 부르지 않고 서버가 서명 전에 장면에 넣는다(무료 한도·시간 그대로)."""
from app.catalog import load_catalog
from app.story.hero import ensure_hero, hero_of
from app.story.schema import Page, Scene, SceneCharacter, Segment

CATALOG = load_catalog()


def page(*chars: str) -> Page:
    return Page(text="모두 함께 웃었어요.",
                scene=Scene(background="forest", characters=[SceneCharacter(id=c, state="happy") for c in chars]))


def ids(p: Page) -> list[str]:
    return [c.id for c in p.scene.characters]


def test_hero_is_first_character_card():
    # 카드 순서: 주인공·성격·배경·사물. 성격·배경은 캐릭터가 아니다
    assert hero_of(["fox", "kind", "forest", "letter"], CATALOG) == "fox"
    assert hero_of(["kind", "forest"], CATALOG) is None


def test_missing_hero_is_added_to_every_ending_page():
    seg = Segment(type="ending", pages=[page("rabbit"), page(), page("fox", "rabbit")])
    fixed, added = ensure_hero(seg, "fox", CATALOG)
    assert [ids(p)[0] for p in fixed.pages] == ["fox", "fox", "fox"]
    assert ids(fixed.pages[0]) == ["fox", "rabbit"]   # 다른 캐릭터는 그대로
    assert ids(fixed.pages[2]) == ["fox", "rabbit"]   # 이미 있던 페이지는 바꾸지 않음
    assert added == [0, 1]


def test_full_scene_keeps_three_characters():
    seg = Segment(type="ending", pages=[page("rabbit", "bear", "owl")])
    fixed, _ = ensure_hero(seg, "fox", CATALOG)
    assert ids(fixed.pages[0]) == ["fox", "rabbit", "bear"]   # 장면은 3명까지 → 마지막 한 명이 빠짐


def test_added_hero_has_valid_state():
    seg = Segment(type="ending", pages=[page()])
    fixed, _ = ensure_hero(seg, "fox", CATALOG)
    assert fixed.pages[0].scene.characters[0].state in CATALOG.ids("states")


def test_only_ending_is_changed():
    seg = Segment(type="middle", pages=[page("rabbit")])
    fixed, added = ensure_hero(seg, "fox", CATALOG)
    assert ids(fixed.pages[0]) == ["rabbit"] and added == []


def test_no_hero_card_changes_nothing():
    seg = Segment(type="ending", pages=[page("rabbit")])
    fixed, added = ensure_hero(seg, None, CATALOG)
    assert ids(fixed.pages[0]) == ["rabbit"] and added == []
