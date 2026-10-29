"""여러 모델을 동시에 돌려 가장 먼저 성공한 결과를 쓴다 (실험 서버)."""
import threading

from fastapi.testclient import TestClient

from app.lab.api import create_app
from conftest import FakeLLM, segment_json

CARDS = ["rabbit", "rose", "star"]
GOOD = segment_json(pages=3)


class WaitingLLM(FakeLLM):
    """신호가 올 때까지 기다렸다가 응답하는 느린 모델"""

    def __init__(self, model, responses, gate):
        super().__init__(model, responses)
        self.gate = gate

    def complete(self, messages, temperature=0.9):
        self.gate.wait(timeout=5)
        return super().complete(messages, temperature)


def start(app, **body):
    return TestClient(app).post("/api/stories", json={"cards": CARDS, "model": "a", "choice_count": 2,
                                                      **body})


def test_race_returns_fastest_success():
    gate = threading.Event()
    slow = WaitingLLM("slow", [GOOD], gate)
    fast = FakeLLM("fast", [GOOD])
    app = create_app(models={"a": lambda: slow, "b": lambda: fast}, tts_fn=lambda *a: b"")
    r = start(app, race=["b"])
    gate.set()
    assert r.status_code == 200
    assert r.json()["model_used"] == "fast"
    assert set(r.json()["raced"]) == {"a", "b"}


def test_race_skips_failed_model():
    bad = FakeLLM("bad", ["oops", "oops"])
    good = FakeLLM("good", [GOOD])
    app = create_app(models={"a": lambda: bad, "b": lambda: good}, tts_fn=lambda *a: b"")
    r = start(app, race=["b"])
    assert r.status_code == 200 and r.json()["model_used"] == "good"


def test_race_all_fail_returns_502_with_every_attempt():
    app = create_app(models={"a": lambda: FakeLLM("x", ["oops", "oops"]),
                             "b": lambda: FakeLLM("y", ["oops", "oops"])}, tts_fn=lambda *a: b"")
    r = start(app, race=["b"])
    assert r.status_code == 502
    assert {a["model"] for a in r.json()["detail"]["attempts"]} == {"x", "y"}


def test_race_unknown_model_rejected():
    app = create_app(models={"a": lambda: FakeLLM("x", [])}, tts_fn=lambda *a: b"")
    assert start(app, race=["nope"]).status_code == 400


def test_config_shows_real_model_ids():
    app = create_app(models={"a": lambda: FakeLLM("x", [])}, labels={"a": "vendor/real-model:free"},
                     tts_fn=lambda *a: b"")
    data = TestClient(app).get("/api/config").json()
    assert data["model_ids"]["a"] == "vendor/real-model:free"
