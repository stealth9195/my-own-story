"""처음 선택 4단계: 주인공(캐릭터 5장 중 1) → 성격(4개 중 1) → 배경(장소·상황 4개 중 1) → 사물(4개 중 1).
보여줄 후보는 서버가 전체 목록에서 무작위로 뽑는다."""
from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.lab.api import create_app
from app.story.prompt import StoryContext, build_messages
from app.story.safety import load_banned_words
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()


def client(responses=()):
    return TestClient(create_app(models={"f": lambda: FakeLLM("f", list(responses))},
                                 tts_fn=lambda *a: b""))


def test_situations_are_backgrounds_not_traits():
    assert cat.kind_of("rainy_day") == "situation"
    assert cat.kind_of("forest") == "background"
    assert "rainy_day" not in cat.ids("traits")
    assert len(cat.traits) >= 8 and len(cat.situations) >= 4
    assert all(s.emoji for s in cat.situations)


def test_start_options_are_random_picks_by_step():
    data = client().get("/api/start-options").json()
    assert len(data["heroes"]) == 5 and all(c["kind"] == "character" for c in data["heroes"])
    assert len(data["traits"]) == 4 and all(c["kind"] == "trait" for c in data["traits"])
    assert len(data["backgrounds"]) == 4
    assert all(c["kind"] in ("background", "situation") for c in data["backgrounds"])
    assert len(data["objects"]) == 4 and all(c["kind"] == "object" for c in data["objects"])


def test_start_with_one_of_each_step():
    # 장면에 rabbit·rose·star 가 있는 가짜 응답 → 주인공 토끼, 사물 장미
    r = client([segment_json(pages=3)]).post("/api/stories", json={
        "cards": ["rabbit", "brave", "forest", "rose"], "model": "f", "choice_count": 2})
    assert r.status_code == 200


def test_unknown_start_card_rejected():
    r = client().post("/api/stories", json={"cards": ["rabbit", "brave", "moon_base"], "model": "f",
                                            "choice_count": 2})
    assert r.status_code == 400


def test_v6_user_message_lists_roles():
    ctx = StoryContext(cards=["bear", "brave", "rainy_day", "cake"], history=[], chosen=[])
    user = build_messages(ctx, "intro", cat, version="v6")[1]["content"]
    assert "주인공: 곰" in user and "성격: 용감한" in user
    assert "배경: 비 오는 날" in user and "사물: 케이크" in user


def test_place_card_must_be_first_background():
    # 가짜 응답의 배경은 forest → 카드로 sea 를 고르면 경고/오류
    r = validate_segment(segment_json(pages=3), "intro", cat, banned, cards=["rabbit", "sea", "rose", "star"])
    assert "background_mismatch" in r.errors
    ok = validate_segment(segment_json(pages=3), "intro", cat, banned, cards=["rabbit", "forest", "rose", "star"])
    assert "background_mismatch" not in ok.errors
