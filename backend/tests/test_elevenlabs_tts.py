"""ElevenLabs TTS (시연용). 소리는 PCM(24kHz)으로 받아 WAV 로 감싼다 → 길이 검사·MP3 변환을 그대로 쓴다"""
import io
import struct
import wave

import pytest

from app.tts import elevenlabs
from app.tts.gemini import TTSError

PCM = struct.pack("<4h", 100, -100, 200, -200)


class Resp:
    def __init__(self, status: int, content: bytes = b"", text: str = ""):
        self.status_code, self.content, self.text = status, content, text


def test_pcm_is_wrapped_as_wav(monkeypatch):
    seen = {}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return Resp(200, PCM)
    monkeypatch.setattr(elevenlabs.httpx, "post", post)
    wav = elevenlabs.synthesize("안녕", "voice123", "key", "eleven_multilingual_v2")
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getframerate(), w.readframes(w.getnframes())) == (24000, PCM)
    assert "voice123" in seen["url"] and seen["params"]["output_format"] == "pcm_24000"
    assert seen["headers"]["xi-api-key"] == "key"
    assert seen["json"]["model_id"] == "eleven_multilingual_v2"


def test_error_keeps_status(monkeypatch):
    monkeypatch.setattr(elevenlabs.httpx, "post",
                        lambda url, **kw: Resp(401, text='{"detail":{"status":"quota_exceeded"}}'))
    with pytest.raises(TTSError) as info:
        elevenlabs.synthesize("안녕", "voice123", "key", "eleven_multilingual_v2")
    assert info.value.status == 401 and "quota_exceeded" in str(info.value)


def test_no_key():
    with pytest.raises(TTSError):
        elevenlabs.synthesize("안녕", "voice123", "", "eleven_multilingual_v2")
