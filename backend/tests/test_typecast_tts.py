import httpx
import pytest

from app.tts import typecast
from app.tts.gemini import TTSError


class FakeResp:
    def __init__(self, status, content=b"", text=""):
        self.status_code, self.content, self.text = status, content, text


def test_missing_key_fails_without_calling(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("호출하면 안 됨"))
    with pytest.raises(TTSError):
        typecast.synthesize("안녕", "tc_x", "")


def test_request_uses_smart_emotion_and_style_tempo(monkeypatch):
    sent = {}

    def post(url, headers, json, timeout):
        sent.update(json=json, headers=headers)
        return FakeResp(200, b"RIFFwav")

    monkeypatch.setattr(httpx, "post", post)
    assert typecast.synthesize("안녕", "tc_x", "key", style="slow") == b"RIFFwav"
    assert sent["json"]["prompt"] == {"emotion_type": "smart"}
    assert sent["json"]["output"]["audio_tempo"] == typecast.TEMPOS["slow"]
    assert sent["json"]["language"] == "kor" and sent["headers"]["X-API-KEY"] == "key"


def test_credit_error_keeps_status(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResp(402, text="Insufficient credits"))
    with pytest.raises(TTSError) as e:
        typecast.synthesize("안녕", "tc_x", "key")
    assert e.value.status == 402
