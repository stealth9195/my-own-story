import base64
import json

import httpx

from app.catalog import load_catalog
from app.story.prompt import StoryContext, build_messages, forbidden_choices
from app.story.safety import load_banned_words
from app.story.schema import Page, Scene, SceneCharacter, Segment
from app.story.validator import validate_segment
from app.tts import gemini

cat = load_catalog()
banned = load_banned_words()
CARDS = ["bear", "star", "rainbow"]


def intro(pages_scene):
    """pages_scene: 페이지별 (캐릭터 id 목록, 사물 id 목록)"""
    pages = [{"text": "별이 반짝였어요. 무지개가 떴어요.",
              "scene": {"background": "meadow", "characters": [{"id": c, "state": "idle"} for c in chars],
                        "objects": objs}} for chars, objs in pages_scene]
    return json.dumps({"pages": pages, "choices": [{"id": i, "label": i} for i in ("dragon", "cake", "moon")]})


def check(raw):
    return validate_segment(raw, "intro", cat, banned, cards=CARDS)


def test_intro_with_two_cards_first_and_all_cards_passes():
    assert check(intro([([], ["star", "rainbow"]), (["bear"], []), (["bear"], ["star"])])).ok


def test_intro_first_page_needs_two_cards():
    r = check(intro([([], ["star"]), (["bear"], ["rainbow"]), (["bear"], [])]))
    assert "cards_missing" in r.errors


def test_intro_must_show_every_card():
    r = check(intro([([], ["star", "rainbow"]), ([], ["star"]), ([], ["rainbow"])]))
    assert "cards_missing" in r.errors


def test_intro_first_page_hero_must_be_a_card():
    r = check(intro([(["rabbit"], ["star", "rainbow"]), (["bear"], []), (["bear"], [])]))
    assert "wrong_hero" in r.errors


def test_scene_items_already_in_story_are_forbidden_choices():
    seg = Segment(type="intro", pages=[Page(text="보물 상자가 있었어요.", scene=Scene(
        background="forest", characters=[SceneCharacter(id="fox")], objects=["treasure_box"]))])
    ctx = StoryContext(cards=CARDS, history=[seg], chosen=[])
    assert {"treasure_box", "fox"} <= forbidden_choices(ctx)


def test_v3_example_has_no_concrete_ids():
    system = build_messages(StoryContext(CARDS, [], []), "intro", cat, version="v3")[0]["content"]
    example = system.split("## 출력 형식")[1]
    assert "rabbit" not in example and "forest" not in example


def capture_tts(monkeypatch):
    sent = {}

    def fake_post(url, **kw):
        sent["body"] = kw["json"]
        part = {"inlineData": {"data": base64.b64encode(b"\x00\x00").decode()}}
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [part]}}]})

    monkeypatch.setattr(gemini.httpx, "post", fake_post)
    return sent


def test_tts_slow_style_prefixes_director_note(monkeypatch):
    # TTS 모델은 systemInstruction을 거부함(400) → 본문 앞 지시문 방식
    sent = capture_tts(monkeypatch)
    gemini.synthesize("안녕", "Kore", "k", style="slow")
    text = sent["body"]["contents"][0]["parts"][0]["text"]
    assert text.endswith("안녕") and text != "안녕"
    assert "systemInstruction" not in sent["body"]


def test_tts_normal_style_has_no_instruction(monkeypatch):
    sent = capture_tts(monkeypatch)
    gemini.synthesize("안녕", "Kore", "k", style="normal")
    assert sent["body"]["contents"][0]["parts"][0]["text"] == "안녕"
    assert "systemInstruction" not in sent["body"]


def test_choice_already_in_same_segment_scene_is_dropped():
    raw = intro([([], ["star", "rainbow"]), (["bear"], ["balloon"]), (["bear"], [])])
    data = json.loads(raw)
    data["choices"] = [{"id": i, "label": i} for i in ("balloon", "cake", "moon", "ship")]
    r = check(json.dumps(data))
    assert r.ok
    assert [c.id for c in r.segment.choices] == ["cake", "moon", "ship"]
