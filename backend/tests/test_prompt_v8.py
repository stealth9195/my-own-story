"""v8: 프롬프트 충돌 정리 (A-1 ~ A-11 결정)."""
import json
import random

from app.catalog import load_catalog
from app.story.generator import generate_segment
from app.story.prompt import (ENDING_EXAMPLES, StoryContext, build_messages, choose_ending_kind)
from app.story.safety import load_banned_words
from app.story.schema import Choice, Page, Scene, SceneCharacter, Segment
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()
CARDS = ["bear", "brave", "forest", "cake"]  # 주인공·성격·장소·사물


def seg(kind="item", choices=("dragon", "moon", "apple")):
    page = Page(text="곰이 숲에 있었어요.", scene=Scene(background="forest"))
    cs = ([Choice(kind="item", id=i, label=cat.name_of(i)) for i in choices] if kind == "item"
          else [Choice(kind="phrase", id=f"phrase-{n}", label=l)
                for n, l in enumerate(("아주 커다랬어요!", "작고 귀여웠어요.", "반짝였어요."), 1)])
    return Segment(type="middle", pages=[page], choices=cs)


def ctx(history=(), chosen=(), total=5):
    return StoryContext(cards=CARDS, history=list(history), chosen=list(chosen), total_segments=total)


# --- A-3 끝맺음 종류: 코드가 정함 ---

def test_ending_has_no_kind():
    assert choose_ending_kind(ctx(history=[seg()] * 4), "ending") is None


def test_segment_before_ending_is_item():
    # 5구간 중 4번째(결말 직전) → 물건형
    assert choose_ending_kind(ctx(history=[seg("phrase")] * 3), "middle") == "item"


def test_no_three_in_a_row():
    two_items = [seg("item"), seg("item")]
    assert choose_ending_kind(ctx(history=two_items, total=6), "middle", rng=random.Random(0)) == "phrase"
    two_phrases = [seg("phrase"), seg("phrase")]
    assert choose_ending_kind(ctx(history=two_phrases, total=6), "middle", rng=random.Random(0)) == "item"


def test_random_kind_uses_both():
    kinds = {choose_ending_kind(ctx(), "intro", rng=random.Random(s)) for s in range(20)}
    assert kinds == {"item", "phrase"}


# --- A-3/A-9 사용자 메시지: 종류 지시 + 예시 3개 ---

def test_v8_message_states_kind_and_three_examples():
    user = build_messages(ctx(), "intro", cat, version="v8", ending_kind="phrase",
                          rng=random.Random(1))[1]["content"]
    assert "문장형" in user
    shown = [e for e in ENDING_EXAMPLES["phrase"] if e in user]
    assert len(shown) == 3


def test_examples_have_ten_per_kind():
    assert len(ENDING_EXAMPLES["item"]) >= 10 and len(ENDING_EXAMPLES["phrase"]) >= 10


# --- A-4 목록 하나, A-5 성격·상황 제외, A-7 발단 ---

def test_v8_message_has_single_candidate_list():
    user = build_messages(ctx(history=[seg()], chosen=["dragon"]), "middle", cat, version="v8",
                          ending_kind="item")[1]["content"]
    assert "선택지 후보" in user and "이미 나온 선택지" not in user


def test_v8_system_listing_excludes_traits_and_situations():
    system = build_messages(ctx(), "intro", cat, version="v8", ending_kind="item")[0]["content"]
    listing = system.split("## 사용 가능한 목록")[1].split("## 출력 형식")[0]
    assert "brave" not in listing and "rainy_day" not in listing and "forest" in listing


def test_v8_system_uses_baldan_not_doip():
    system = build_messages(ctx(), "intro", cat, version="v8", ending_kind="item")[0]["content"]
    assert "도입" not in system and "발단" in system


def test_v7_listing_unchanged():
    system = build_messages(ctx(), "intro", cat, version="v7")[0]["content"]
    assert "brave" in system


# --- A-6 문장형 이어 시작 ---

def test_v8_phrase_choice_restated():
    user = build_messages(ctx(history=[seg("phrase")], chosen=["phrase-1"]), "middle", cat,
                          version="v8", ending_kind="item")[1]["content"]
    assert "아주 커다랬어요!" in user and "첫 문장" in user


# --- A-1/A-2 발단 검사 ---

def intro_raw(pages_scene, background="forest"):
    pages = [{"text": "곰이 숲에서 놀았어요. 케이크가 있었어요.",
              "scene": {"background": bg, "characters": [{"id": c, "state": "idle"} for c in chars],
                        "objects": objs}} for (chars, objs, bg) in pages_scene]
    return json.dumps({"pages": pages, "choices": [{"kind": "item", "id": i, "label": i}
                                                   for i in ("dragon", "moon", "apple")]})


def check_v8(raw):
    return validate_segment(raw, "intro", cat, banned, cards=CARDS, intro_v8=True)


def test_v8_intro_hero_on_first_page_object_later_ok():
    r = check_v8(intro_raw([(["bear"], [], "meadow"), ([], ["cake"], "forest"), (["bear"], [], "forest")]))
    assert not {"cards_missing", "hero_missing", "background_mismatch"} & set(r.errors)


def test_v8_intro_hero_missing_on_first_page():
    r = check_v8(intro_raw([([], ["cake"], "forest"), (["bear"], [], "forest"), (["bear"], [], "forest")]))
    assert "hero_missing" in r.errors


def test_v8_intro_object_never_shown():
    r = check_v8(intro_raw([(["bear"], [], "forest")] * 3))
    assert "cards_missing" in r.errors


def test_v8_intro_place_never_used():
    r = check_v8(intro_raw([(["bear"], ["cake"], "sea")] * 3))
    assert "background_mismatch" in r.errors


# --- A-8 선택지 글자는 에셋 이름 ---

def test_item_label_replaced_by_asset_name():
    data = json.loads(segment_json(pages=3, choices=("apple", "dragon", "moon")))
    data["choices"][0]["label"] = "빨간 사과"
    r = validate_segment(json.dumps(data, ensure_ascii=False), "middle", cat, banned)
    assert r.segment.choices[0].label == "사과"


# --- 생성기: 종류 지시와 검사 ---

def test_generator_v8_wrong_kind_is_warning_in_lenient():
    raw = segment_json(pages=3)  # 물건형 선택지
    r = generate_segment(StoryContext(cards=["rabbit", "rose", "star"], history=[], chosen=[], total_segments=5),
                         "intro", primary=FakeLLM("p", [raw, raw]), secondary=None, catalog=cat,
                         banned=banned, version="v8", lenient=True, ending_kind="phrase")
    assert "wrong_kind" in r.attempts[-1].warnings


# --- 문장형: 빈칸에 들어갈 답 (짝 예시 + 문장 끝 검사) ---

def test_phrase_examples_are_pairs_with_answers():
    from app.story.prompt import PHRASE_ANSWERS
    assert set(PHRASE_ANSWERS) == set(ENDING_EXAMPLES["phrase"])
    assert all(len(a) >= 2 for a in PHRASE_ANSWERS.values())


def test_v8_phrase_message_shows_ending_answer_pairs():
    from app.story.prompt import PHRASE_ANSWERS
    user = build_messages(ctx(), "intro", cat, version="v8", ending_kind="phrase",
                          rng=random.Random(3))[1]["content"]
    shown = [e for e in ENDING_EXAMPLES["phrase"] if e in user]
    assert len(shown) == 3
    assert all(any(a in user for a in PHRASE_ANSWERS[e]) for e in shown)


def test_v8_system_describes_phrase_as_answer():
    system = build_messages(ctx(), "intro", cat, version="v8", ending_kind="phrase")[0]["content"]
    assert "빈칸에 들어갈 답" in system


def phrase_raw(labels):
    data = json.loads(segment_json(pages=3))
    data["choices"] = [{"kind": "phrase", "label": l} for l in labels]
    return json.dumps(data, ensure_ascii=False)


def test_unfinished_phrase_choices_dropped():
    r = validate_segment(phrase_raw(["자물쇠를 톡톡 두드려 보니...", "아주 커다랬어요!",
                                     "노랫소리가 들렸어요", "별이 쏟아졌어요.", "문이 열리자…"]),
                         "middle", cat, banned)
    assert [c.label for c in r.segment.choices] == ["아주 커다랬어요!", "노랫소리가 들렸어요", "별이 쏟아졌어요."]
    assert "자물쇠를 톡톡 두드려 보니..." in r.dropped
