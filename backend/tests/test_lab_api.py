from fastapi.testclient import TestClient

from app.lab.api import create_app
from app.tts.gemini import TTSError
from conftest import FakeLLM, middles, segment_json

MID = segment_json(pages=3)
END = segment_json(pages=4, choices=())
CARDS = ["rabbit", "rose", "star"]


def make(responses, tts=None):
    llm = FakeLLM("fake-model", responses)
    app = create_app(models={"fake": lambda: llm},
                     tts_fn=tts or (lambda *args: b"RIFFwav"))
    return TestClient(app), llm


def start(client, choice_count=2):
    return client.post("/api/stories", json={"cards": CARDS, "model": "fake",
                                             "choice_count": choice_count})


def test_config_lists_cards_and_models():
    client, _ = make([])
    data = client.get("/api/config").json()
    assert "fake" in data["models"]
    assert any(c["id"] == "rabbit" and c["name"] == "토끼" for c in data["cards"])
    assert data["tts_models"] and data["voices"]


def test_full_story_flow():
    client, _ = make([*middles(2), END])
    r = start(client).json()
    assert r["type"] == "intro" and len(r["choices"]) == 3 and r["done"] is False
    assert r["model_used"] == "fake-model" and r["attempts"][0]["ok"]
    sid = r["story_id"]
    r = client.post(f"/api/stories/{sid}/next", json={"choice_id": "dragon"}).json()
    assert r["type"] == "middle" and r["index"] == 1
    r = client.post(f"/api/stories/{sid}/next", json={"choice_id": "balloon"}).json()
    assert r["type"] == "ending" and r["done"] is True and r["choices"] == []


def test_choice_not_offered_is_rejected():
    client, _ = make([MID])
    sid = start(client).json()["story_id"]
    r = client.post(f"/api/stories/{sid}/next", json={"choice_id": "robot"})
    assert r.status_code == 400


def test_next_after_ending_is_rejected():
    client, _ = make([*middles(2), END])
    sid = start(client, choice_count=2).json()["story_id"]
    client.post(f"/api/stories/{sid}/next", json={"choice_id": "dragon"})
    client.post(f"/api/stories/{sid}/next", json={"choice_id": "balloon"})
    r = client.post(f"/api/stories/{sid}/next", json={"choice_id": "dragon"})
    assert r.status_code == 409


def test_invalid_cards_and_unknown_model_rejected():
    client, _ = make([])
    assert client.post("/api/stories", json={"cards": ["rabbit"], "model": "fake",
                                              "choice_count": 2}).status_code == 422
    assert client.post("/api/stories", json={"cards": ["alien", "rose", "star"], "model": "fake",
                                              "choice_count": 2}).status_code == 400
    assert client.post("/api/stories", json={"cards": CARDS, "model": "nope",
                                              "choice_count": 2}).status_code == 400


def test_generation_failure_returns_502_with_attempts():
    client, _ = make(["bad", "bad"])
    r = start(client)
    assert r.status_code == 502
    assert len(r.json()["detail"]["attempts"]) == 2


def test_unknown_story_404():
    client, _ = make([])
    assert client.post("/api/stories/xxx/next", json={"choice_id": "dragon"}).status_code == 404


def test_tts_returns_wav():
    client, _ = make([])
    r = client.post("/api/tts", json={"text": "안녕", "voice": "Kore", "model": "m"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content == b"RIFFwav"


def test_tts_quota_error_passes_status():
    def fail(*args):
        raise TTSError("limit", status=429)

    client, _ = make([], tts=fail)
    r = client.post("/api/tts", json={"text": "안녕", "voice": "Kore", "model": "m"})
    assert r.status_code == 429


def test_index_page_served():
    client, _ = make([])
    r = client.get("/")
    assert r.status_code == 200 and "<html" in r.text


def test_prompt_versions_listed_and_unknown_rejected():
    client, _ = make([MID])
    assert {"v1", "v2"} <= set(client.get("/api/config").json()["prompt_versions"])
    r = client.post("/api/stories", json={"cards": CARDS, "model": "fake", "choice_count": 2,
                                          "prompt_version": "v999"})
    assert r.status_code == 400
    r = client.post("/api/stories", json={"cards": CARDS, "model": "fake", "choice_count": 2,
                                          "prompt_version": "v1"})
    assert r.status_code == 200


def test_fallback_model_used_when_primary_fails():
    primary = FakeLLM("primary", ["bad", "bad"])
    backup = FakeLLM("backup", [MID])
    app = create_app(models={"p": lambda: primary, "b": lambda: backup}, tts_fn=lambda *a: b"")
    client = TestClient(app)
    r = client.post("/api/stories", json={"cards": CARDS, "model": "p", "fallback_model": "b",
                                          "choice_count": 2})
    assert r.status_code == 200
    assert r.json()["model_used"] == "backup"
    assert [a["model"] for a in r.json()["attempts"]] == ["primary", "primary", "backup"]


def test_unknown_fallback_model_rejected():
    client, _ = make([])
    r = client.post("/api/stories", json={"cards": CARDS, "model": "fake", "fallback_model": "nope",
                                          "choice_count": 2})
    assert r.status_code == 400
