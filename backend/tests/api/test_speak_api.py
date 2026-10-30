"""안내·선택지 읽기 (Azure). 실제 Azure 는 부르지 않고 가짜 함수를 넣는다"""
import random

from fastapi.testclient import TestClient

from app.api.limits import Limits
from app.main import create_app
from app.tts.gemini import TTSError
from conftest import FakeLLM
from test_story_api import settings


class FakeSpeak:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    def __call__(self, text, voice):
        self.calls.append((text, voice))
        if self.fail:
            raise TTSError("busy", status=500)
        return b"ID3mp3"


def make(speak=None, limits=None):
    speak = speak if speak is not None else FakeSpeak()
    app = create_app(settings(), FakeLLM("fake-model", []), None, speak=speak, limits=limits,
                     rng=random.Random(0))
    return TestClient(app), speak


def test_speak_returns_mp3_in_chosen_voice():
    client, speak = make()
    r = client.post("/api/speak", json={"text": "누가 주인공일까요?", "voice": "male"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert speak.calls == [("누가 주인공일까요?", "male")]


def test_speak_rejects_long_text_and_unknown_voice():
    client, speak = make()
    assert client.post("/api/speak", json={"text": "가" * 201, "voice": "female"}).status_code == 422
    assert client.post("/api/speak", json={"text": "안녕", "voice": "robot"}).status_code == 422
    assert speak.calls == []


def test_speak_daily_char_limit():
    limits = Limits(3, 30)
    client, speak = make(limits=limits)
    limits.reserve_azure(limits.azure_left())  # 오늘 글자 수를 다 씀
    r = client.post("/api/speak", json={"text": "안녕", "voice": "female"})
    assert r.status_code == 429 and r.json()["detail"]["code"] == "speak_limit"
    assert speak.calls == []


def test_speak_unavailable_without_key():
    app = create_app(settings(), FakeLLM("fake-model", []), None, rng=random.Random(0))  # Azure 키 없음
    r = TestClient(app).post("/api/speak", json={"text": "안녕", "voice": "female"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "speak_unavailable"


def test_speak_failure_is_502():
    client, _ = make(FakeSpeak(fail=True))
    r = client.post("/api/speak", json={"text": "안녕", "voice": "female"})
    assert r.status_code == 502 and r.json()["detail"]["code"] == "speak_failed"
