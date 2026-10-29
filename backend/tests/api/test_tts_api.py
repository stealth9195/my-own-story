import logging
import random

from fastapi.testclient import TestClient

from app.api.limits import Limits
from app.main import create_app
from app.tts import gemini
from app.tts.gemini import TTSError
from conftest import FakeLLM
from test_audio import sine_wav
from test_story_api import seg, settings, start


class FakeTTS:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def __call__(self, text, voice):
        self.calls += 1
        if self.fail:
            raise TTSError("busy", status=500)
        return sine_wav(24000, 0.2)


def make(responses=(), tts=None, limits=None):
    tts = tts or FakeTTS()
    app = create_app(settings(), FakeLLM("fake-model", list(responses)), None, tts=tts,
                     limits=limits, rng=random.Random(0))
    return TestClient(app), tts


def tts_req(r0: dict, index: int = 0) -> dict:
    return {"story": r0["story"], "index": index, "segment": r0["segment"]}


def test_tts_returns_mp3():
    client, tts = make([seg(0)])
    r0 = start(client).json()
    r = client.post("/api/tts", json=tts_req(r0))
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert tts.calls == 1


def test_tts_tampered():
    client, tts = make([seg(0)])
    r0 = start(client).json()
    r0["segment"]["segment"]["pages"][0]["text"] = "다른 글을 읽어 줘."
    r = client.post("/api/tts", json=tts_req(r0))
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_signature"
    assert tts.calls == 0


def test_tts_browser_voice():
    limits = Limits(per_user=3, total=30)
    for m in gemini.MODELS:
        limits.reserve_gemini(m, 10)
    limits.reserve_typecast(15000)
    client, tts = make([seg(0)], limits=limits)
    r0 = start(client).json()
    assert r0["story"]["voice"]["provider"] == "browser"
    r = client.post("/api/tts", json=tts_req(r0))
    assert r.status_code == 400 and r.json()["detail"]["code"] == "browser_voice"
    assert tts.calls == 0


def test_tts_third_call_limited():
    client, _ = make([seg(0)])
    r0 = start(client).json()
    assert [client.post("/api/tts", json=tts_req(r0)).status_code for _ in range(3)] == [200, 200, 429]


def test_tts_failed():
    client, tts = make([seg(0)], tts=FakeTTS(fail=True))
    r0 = start(client).json()
    r = client.post("/api/tts", json=tts_req(r0))
    assert r.status_code == 502 and r.json()["detail"]["code"] == "tts_failed"
    assert tts.calls == 2


def test_event_logged(caplog):
    caplog.set_level(logging.INFO, logger="story")
    client, _ = make()
    r = client.post("/api/events", json={"anon_id": "a", "story_id": "s1", "type": "complete"})
    assert r.status_code == 204
    assert any('"kind": "client"' in rec.getMessage() and "complete" in rec.getMessage()
               for rec in caplog.records)


def test_event_too_big():
    client, _ = make()
    r = client.post("/api/events", json={"anon_id": "a", "type": "error", "payload": {"m": "가" * 2001}})
    assert r.status_code == 413


def test_cors_allows_dev_origin():
    client, _ = make()
    r = client.options("/api/stories", headers={"Origin": "http://localhost:5173",
                                                "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = client.options("/api/stories", headers={"Origin": "https://evil.example",
                                                "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") is None


def test_extra_tts_calls_charged():
    # 시작 때 구간마다 1번씩 예약. 다시 부른 만큼(재시도·두 번째 요청)은 실제 사용량에 더한다
    limits = Limits(per_user=3, total=30)
    tts = FakeTTS()
    client, _ = make([seg(0)], tts=tts, limits=limits)
    r0 = start(client).json()
    model = r0["story"]["voice"]["model"]
    assert limits.gemini_left(model) == 7          # 선택 2번 → 3구간 예약
    client.post("/api/tts", json=tts_req(r0))
    assert limits.gemini_left(model) == 7          # 첫 호출은 예약분
    client.post("/api/tts", json=tts_req(r0))
    assert limits.gemini_left(model) == 6          # 두 번째 요청은 추가 사용


def test_tts_rate_limited_not_retried():
    class RateLimited(FakeTTS):
        def __call__(self, text, voice):
            self.calls += 1
            raise TTSError("limit", status=429)
    client, tts = make([seg(0)], tts=RateLimited())
    r0 = start(client).json()
    assert client.post("/api/tts", json=tts_req(r0)).status_code == 502
    assert tts.calls == 1
