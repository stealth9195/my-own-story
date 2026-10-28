import json

import pytest

from eval.judge import CRITERIA, build_judge_messages, parse_judge, story_to_text

STORY = {
    "segments": [
        {"type": "intro", "pages": [{"text": "토끼가 숲에 갔어요."}],
         "choices": [{"id": "dragon", "label": "아기 용"}, {"id": "rose", "label": "장미"}],
         "chosen": "dragon"},
        {"type": "ending", "pages": [{"text": "모두 행복했어요."}], "choices": [], "chosen": None},
    ]
}


def scores(value=4, **override):
    s = {c: value for c in CRITERIA}
    s.update(override)
    return s


def test_parse_judge_valid():
    raw = "```json\n" + json.dumps(scores()) + "\n```"
    assert parse_judge(raw) == scores()


def test_parse_judge_missing_key_raises():
    s = scores()
    del s["plot"]
    with pytest.raises(ValueError):
        parse_judge(json.dumps(s))


@pytest.mark.parametrize("bad", [0, 6, "5"])
def test_parse_judge_out_of_range_raises(bad):
    with pytest.raises(ValueError):
        parse_judge(json.dumps(scores(plot=bad)))


def test_story_to_text_contains_pages_and_chosen():
    text = story_to_text(STORY)
    assert "토끼가 숲에 갔어요." in text
    assert "모두 행복했어요." in text
    assert "아기 용" in text and "장미" in text
    assert "고른 선택지: 아기 용" in text


def test_build_judge_messages_includes_story():
    msgs = build_judge_messages("이야기 본문")
    assert msgs[0]["role"] == "system"
    assert "이야기 본문" in msgs[1]["content"]
