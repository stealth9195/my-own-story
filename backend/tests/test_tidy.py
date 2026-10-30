"""LLM 글의 더듬기 고치기. 겪은 오타(2026-10-30): '꼬 꼭 안았어요'.
'찾으려'(→ 찾으러) 같은 어미 오타는 규칙으로 못 잡아 그대로 둔다(사용자 결정: 맞춤법 검사기·LLM 교정은 쓰지 않음)"""
import pytest

from app.story.schema import Segment
from app.story.tidy import fix_stutter, tidy_segment


@pytest.mark.parametrize("before,after", [
    ("토끼를 꼬 꼭 안았어요.", "토끼를 꼭 안았어요."),
    ("까 깜짝 놀랐어요.", "깜짝 놀랐어요."),
    ("\"따 딱 맞아!\" 하고 웃었어요.", "\"딱 맞아!\" 하고 웃었어요."),
])
def test_stutter_is_removed(before, after):
    assert fix_stutter(before)[0] == after


@pytest.mark.parametrize("text", [
    "이 일은 비밀이에요.",        # '이'(이것) + '일'
    "새 생일 선물을 받았어요.",    # '새' + '생일'
    "그 금빛 열쇠를 찾았어요.",
    "해 햇살이 따뜻했어요.",
    "꼭 꼭 숨어라.",              # 같은 글자 반복은 일부러 쓴 말일 수 있음
    "쉴 곳을 찾으려 했어요.",      # 어미 오타는 그대로
])
def test_real_words_are_kept(text):
    assert fix_stutter(text) == (text, [])


def test_fixes_are_reported():
    assert fix_stutter("꼬 꼭 안고 까 깜짝")[1] == ["꼬 꼭", "까 깜"]   # 지운 글자와 다음 글자


def test_tidy_segment_changes_only_text():
    seg = Segment.model_validate({"type": "intro", "pages": [
        {"text": "꼬 꼭 안았어요.", "scene": {"background": "forest", "characters": []}},
        {"text": "잘 잤어요.", "scene": {"background": "forest", "characters": []}}]})
    tidy, fixes = tidy_segment(seg)
    assert [p.text for p in tidy.pages] == ["꼭 안았어요.", "잘 잤어요."]
    assert tidy.pages[0].scene == seg.pages[0].scene and fixes == ["꼬 꼭"]
