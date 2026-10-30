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
    tts = FakeTTS([TTSError("busy", status=500), TTSError("busy", status=500)])
    with pytest.raises(TTSError):
        synthesize_segment("안녕", VOICE, tts)
    assert tts.calls == 2


def test_browser_voice_not_called():
    tts = FakeTTS([])
    with pytest.raises(ValueError):
        synthesize_segment("안녕", Voice(provider="browser"), tts)
    assert tts.calls == 0


def test_rate_limit_not_retried():
    # 429 는 한도 초과라 바로 다시 불러도 실패하고 한도만 더 쓴다
    tts = FakeTTS([TTSError("limit", status=429)])
    with pytest.raises(TTSError):
        synthesize_segment("안녕", VOICE, tts)
    assert tts.calls == 1


# 겪은 문제(2026-10-30): 3.8 이 한 문장(20자)을 읽으라는데 영어 연출 지시까지 읽어 25초가 나왔다.
# 보통은 글자당 약 0.19초(샘플 190자 → 35~37초). 지나치게 길면 실패로 보고 다음 모델로 넘긴다
def test_too_long_audio_is_rejected():
    tts = FakeTTS([sine_wav(24000, 25.0), sine_wav(24000, 25.0)])
    with pytest.raises(TTSError) as info:
        synthesize_segment("토끼가 숲속으로 깡충깡충 뛰어갔어요.", VOICE, tts)
    assert "too_long" in str(info.value)
    assert tts.calls == 2          # 정해진 모델은 한 번 더 시도


def test_normal_length_passes():
    text = "가" * 190
    tts = FakeTTS([sine_wav(24000, 40.0)])
    assert is_mp3(synthesize_segment(text, VOICE, tts))


def test_too_long_then_ok_on_retry():
    tts = FakeTTS([sine_wav(24000, 25.0), sine_wav(24000, 4.0)])
    assert is_mp3(synthesize_segment("토끼가 숲속으로 깡충깡충 뛰어갔어요.", VOICE, tts))


# ElevenLabs(유료): 연출 지시가 없으니 길이 검사를 하지 않고, 서버 일시 오류(5xx)일 때만 다시 부른다
ELEVEN_VOICE = Voice(provider="elevenlabs", model="eleven_multilingual_v2", voice="v")


def test_elevenlabs_skips_length_check():
    tts = FakeTTS([sine_wav(24000, 25.0)])
    assert is_mp3(synthesize_segment("토끼가 숲속으로 깡충깡충 뛰어갔어요.", ELEVEN_VOICE, tts))
    assert tts.calls == 1


def test_elevenlabs_no_retry_on_network_error():
    tts = FakeTTS([TTSError("요청 실패"), sine_wav(24000, 0.2)])
    with pytest.raises(TTSError):
        synthesize_segment("안녕", ELEVEN_VOICE, tts)
    assert tts.calls == 1


def test_elevenlabs_retry_on_server_error():
    tts = FakeTTS([TTSError("busy", status=503), sine_wav(24000, 0.2)])
    assert is_mp3(synthesize_segment("안녕", ELEVEN_VOICE, tts))
    assert tts.calls == 2
