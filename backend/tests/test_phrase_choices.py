"""문장형 선택지 + 시작 카드 20장(물건 12 + 느낌·행동 8)."""
import json

from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.lab.api import create_app
from app.story.prompt import StoryContext, build_messages, forbidden_choices, unchosen_ids
from app.story.safety import load_banned_words
from app.story.schema import Choice, Page, Scene, Segment
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()


def raw_with(choices, pages=3):
    data = json.loads(segment_json(pages=pages))
    data["choices"] = choices
    return json.dumps(data, ensure_ascii=False)


PHRASES = [{"kind": "phrase", "label": l} for l in ("아주 커다랬어요!", "정말 예뻤어요.", "바람에 흔들렸어요.")]


# --- 카탈로그 ---

def test_traits_have_emoji():
    assert len(cat.traits) >= 8
    assert all(t.emoji for t in cat.traits)


def test_card_kind():
    assert cat.kind_of("bear") == "character"
    assert cat.kind_of("cake") == "object"
    assert cat.kind_of("brave") == "trait"


# --- 검증기 ---

def test_phrase_choices_pass_and_get_ids():
    r = validate_segment(raw_with(PHRASES), "middle", cat, banned)
    assert r.ok
    assert [c.kind for c in r.segment.choices] == ["phrase"] * 3
    assert len({c.id for c in r.segment.choices}) == 3


def test_mixed_choice_kinds_fail():
    mixed = PHRASES[:2] + [{"kind": "item", "id": "dragon", "label": "아기 용"}]
    r = validate_segment(raw_with(mixed), "middle", cat, banned)
    assert "mixed_choices" in r.errors


def test_phrase_repeated_from_before_is_dropped():
    more = PHRASES + [{"kind": "phrase", "label": "반짝반짝 빛났어요."}]
    r = validate_segment(raw_with(more), "middle", cat, banned, forbidden_phrases={"정말 예뻤어요."})
    assert r.ok
    assert "정말 예뻤어요." not in [c.label for c in r.segment.choices]


def test_phrase_too_long_or_unsafe_dropped():
    bad = PHRASES[:2] + [{"kind": "phrase", "label": "가" * 30}, {"kind": "phrase", "label": "바보 같았어요."}]
    r = validate_segment(raw_with(bad), "middle", cat, banned)
    assert "choices" in r.errors


def test_trait_cards_do_not_need_to_appear_in_scene():
    # 카드: 토끼·장미·별 + 용감한 → 장면 검사는 물건 카드만
    r = validate_segment(segment_json(pages=3), "intro", cat, banned, cards=["rabbit", "rose", "star", "brave"])
    assert "cards_missing" not in r.errors


# --- 프롬프트 ---

def seg_with_choices(choices):
    page = Page(text="곰이 집을 발견했어요. 그 집의 생김새는...", scene=Scene(background="village"))
    return Segment(type="intro", pages=[page], choices=choices)


PHRASE_SEG = seg_with_choices([Choice(kind="phrase", id="p1", label="아주 커다랬어요!"),
                               Choice(kind="phrase", id="p2", label="정말 예뻤어요.")])


def test_v6_uses_chosen_phrase_text():
    ctx = StoryContext(cards=["bear", "cake", "brave"], history=[PHRASE_SEG], chosen=["p1"], total_segments=4)
    user = build_messages(ctx, "middle", cat, version="v6")[1]["content"]
    assert "아주 커다랬어요!" in user
    assert "이미 나온 문장 선택지" in user and "정말 예뻤어요." in user


def test_phrase_choices_not_in_item_rules():
    ctx = StoryContext(cards=["bear", "cake"], history=[PHRASE_SEG], chosen=["p1"])
    assert "p1" not in forbidden_choices(ctx) and "p2" not in unchosen_ids(ctx)


def test_v6_system_explains_phrase_choices_and_traits():
    ctx = StoryContext(cards=["bear", "brave"], history=[], chosen=[])
    system = build_messages(ctx, "intro", cat, version="v6")[0]["content"]
    assert '"kind":"phrase"' in system
    assert "성격(traits)" in system


# --- 실험 서버 ---

def test_start_requires_a_character_card():
    app = create_app(models={"f": lambda: FakeLLM("f", [])}, tts_fn=lambda *a: b"")
    r = TestClient(app).post("/api/stories", json={"cards": ["cake", "star", "brave"], "model": "f",
                                                   "choice_count": 2})
    assert r.status_code == 400


def test_config_cards_have_kind_and_emoji():
    app = create_app(models={}, tts_fn=lambda *a: b"")
    cards = TestClient(app).get("/api/config").json()["cards"]
    brave = next(c for c in cards if c["id"] == "brave")
    assert brave["kind"] == "trait" and brave["emoji"]
