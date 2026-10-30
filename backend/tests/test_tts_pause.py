"""(실험) 문장 사이 쉼(초)을 연출 지시에 넣기"""
from app.tts import gemini


def test_direction_default_says_short_pause():
    assert "short pause" in gemini.direction(None)
    assert gemini.direction(None) == gemini.DIRECTION


def test_direction_with_seconds():
    d = gemini.direction(1.5)
    assert "1.5 seconds" in d and "short pause" not in d
