import pytest

from app.api.schemas import Voice
from app.api.tts_service import synthesize_segment
from app.tts.gemini import TTSError
from test_audio import is_mp3, sine_wav

VOICE = Voice(provider="gemini", model="gemini-2.5-flash-preview-tts", voice="Kore")


class FakeTTS:
    def __init__(self, results: list):
        self.results = list(results)
        self.calls = 0

    def __call__(self, text: str, voice: Voice) -> bytes:
        self.calls += 1
        item = self.results.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_retry_once_then_ok():
    tts = FakeTTS([TTSError("busy", status=500), sine_wav(24000, 0.2)])
    assert is_mp3(synthesize_segment("안녕", VOICE, tts))
    assert tts.calls == 2


def test_fail_twice_raises():
    tts = FakeTTS([TTSError("limit", status=429), TTSError("limit", status=429)])
    with pytest.raises(TTSError):
        synthesize_segment("안녕", VOICE, tts)
    assert tts.calls == 2


def test_browser_voice_not_called():
    tts = FakeTTS([])
    with pytest.raises(ValueError):
        synthesize_segment("안녕", Voice(provider="browser"), tts)
    assert tts.calls == 0
