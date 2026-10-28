import json

import pytest

from app.catalog import load_catalog
from app.story.safety import load_banned_words
from app.story.validator import validate_segment

cat = load_catalog()
banned = load_banned_words()

TEXT = "토끼가 숲에서 놀았어요."


def page(text=TEXT, **scene):
    base = {"background": "forest", "time": "day",
            "characters": [{"id": "rabbit", "state": "happy"}], "objects": ["rose"]}
    base.update(scene)
    return {"text": text, "scene": base, "mood": "calm", "sfx": "birds"}


def make_raw(pages=3, choices=("dragon", "star", "moon"), page_list=None):
    return json.dumps({
        "pages": page_list if page_list is not None else [page() for _ in range(pages)],
        "choices": [{"id": c, "label": cat.name_of(c) if c in cat.choice_ids() else c}
                    for c in choices],
    }, ensure_ascii=False)


def check(raw, segment_type="intro"):
    return validate_segment(raw, segment_type, cat, banned)


def test_valid_intro_passes():
    r = check(make_raw())
    assert r.ok
    assert len(r.segment.pages) == 3
    assert len(r.segment.choices) == 3


def test_json_inside_code_fence_and_text():
    raw = "여기 있어요\n```json\n" + make_raw() + "\n```"
    assert check(raw).ok


def test_broken_json_fails():
    r = check('{"pages": [')
    assert not r.ok
    assert r.errors == ["json"]


def test_page_count_out_of_range():
    r = check(make_raw(pages=2), "middle")
    assert "page_count" in r.errors


def test_empty_text_fails():
    r = check(make_raw(page_list=[page("   "), page(), page()]))
    assert "empty_text" in r.errors


def test_english_only_text_fails():
    r = check(make_raw(page_list=[page("The rabbit played."), page(), page()]))
    assert "not_korean" in r.errors


def test_too_long_text_fails():
    r = check(make_raw(page_list=[page("가" * 251), page(), page()]))
    assert "too_long" in r.errors


def test_unknown_scene_ids_are_replaced_not_failed():
    odd = page(background="moon_base", characters=[{"id": "alien", "state": "happy"},
                                                   {"id": "rabbit", "state": "dancing"}])
    odd["mood"] = "spooky"
    odd["sfx"] = "boom"
    r = check(make_raw(page_list=[odd, page(), page()]))
    assert r.ok
    p = r.segment.pages[0]
    assert p.scene.background == "meadow"
    assert [c.id for c in p.scene.characters] == ["rabbit"]
    assert p.scene.characters[0].state == "idle"
    assert p.mood == "calm"
    assert p.sfx is None
    assert {"moon_base", "alien", "dancing", "spooky", "boom"} <= set(r.dropped)


def test_duplicate_and_unknown_choices_removed_then_too_few_fails():
    r = check(make_raw(choices=("dragon", "dragon", "alien", "rose")))
    assert "choices" in r.errors


def test_more_than_four_choices_trimmed():
    r = check(make_raw(choices=("dragon", "rose", "star", "cake", "moon")))
    assert r.ok
    assert len(r.segment.choices) == 4


def test_ending_choices_dropped():
    r = check(make_raw(pages=4), "ending")
    assert r.ok
    assert r.segment.choices == []


def test_banned_word_fails():
    r = check(make_raw(page_list=[page("용이 기사를 죽였어요."), page(), page()]))
    assert "unsafe" in r.errors
