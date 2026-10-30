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
    assert tts.calls == 2 + len(gemini.MODELS) - 1  # 정해진 모델 2번(다시 시도) + 다른 모델 1번씩


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
    assert tts.calls == len(gemini.MODELS)  # 429 는 같은 모델로 다시 부르지 않고, 모델마다 1번씩


def test_tts_failure_log_keeps_reason(caplog):
    # 429 가 분당 한도인지 하루 한도인지 알 수 있게 Google 오류 내용을 남긴다
    caplog.set_level(logging.INFO, logger="story")

    def quota(text, voice):
        raise TTSError("HTTP 429: Quota exceeded for metric generate_requests_per_model_per_day", status=429)

    client, _ = make([seg(0)], tts=quota)
    r0 = start(client).json()
    assert client.post("/api/tts", json=tts_req(r0)).status_code == 502
    text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "per_model_per_day" in text


class ModelTTS:
    """모델마다 정해 둔 오류를 내는 가짜 TTS. 부른 모델 순서를 기록"""

    def __init__(self, errors: dict[str, TTSError]):
        self.errors = errors
        self.models: list[str] = []

    def __call__(self, text, voice):
        self.models.append(voice.model)
        if voice.model in self.errors:
            raise self.errors[voice.model]
        return sine_wav(24000, 0.2)


PER_MINUTE = TTSError("HTTP 429: Quota exceeded for metric generate_requests_per_model_per_minute", status=429)
PER_DAY = TTSError("HTTP 429: Quota exceeded for metric generate_requests_per_model_per_day", status=429)


def test_falls_back_to_next_model_with_same_voice():
    tts = ModelTTS({gemini.MODELS[0]: PER_MINUTE})
    client, _ = make([seg(0)], tts=tts)
    r0 = start(client).json()
    assert r0["story"]["voice"]["model"] == gemini.MODELS[0]
    r = client.post("/api/tts", json=tts_req(r0))
    assert r.status_code == 200
    assert tts.models == [gemini.MODELS[0], gemini.MODELS[1]]  # 429 는 같은 모델로 다시 부르지 않고 다음 모델로


def test_daily_quota_marks_model_used_up():
    limits = Limits(3, 30)
    tts = ModelTTS({gemini.MODELS[0]: PER_DAY})
    client, _ = make([seg(0), seg(0)], tts=tts, limits=limits)
    r0 = start(client).json()
    assert client.post("/api/tts", json=tts_req(r0)).status_code == 200
    assert limits.gemini_left(gemini.MODELS[0]) == 0           # 오늘은 다 쓴 것으로 기억
    tts.models.clear()
    assert client.post("/api/tts", json=tts_req(r0)).status_code == 200
    assert tts.models == [gemini.MODELS[1]]                     # 다 쓴 모델은 건너뜀
    assert start(client).json()["story"]["voice"]["model"] != gemini.MODELS[0]  # 새 이야기도


def test_all_models_fail_is_502():
    tts = ModelTTS({m: PER_MINUTE for m in gemini.MODELS})
    client, _ = make([seg(0)], tts=tts)
    r0 = start(client).json()
    assert client.post("/api/tts", json=tts_req(r0)).status_code == 502
    assert tts.models == gemini.MODELS


class VoiceTTS(FakeTTS):
    def __call__(self, text, voice):
        self.voices = getattr(self, "voices", []) + [voice.provider]
        return super().__call__(text, voice)


ELEVEN = {"elevenlabs_api_key": "k", "elevenlabs_voice_id": "voice123", "elevenlabs_voice_name": "경상도 사투리",
          "elevenlabs_voice_id_2": "voice456", "elevenlabs_voice_name_2": "둘째"}


def eleven_client(tts, **update):
    s = settings().model_copy(update={**ELEVEN, **update})
    return TestClient(create_app(s, FakeLLM("fake-model", [seg(0)]), None, tts=tts, rng=random.Random(0)))


def start_with(client, voice):
    return client.post("/api/stories", json={"anon_id": "anon-1", "cards": ["rabbit", "rose", "star"],
                                             "choice_count": 2, "voice": voice})


# 시연용 목소리는 설정 창에서 골랐을 때만 쓴다. 목록에는 목소리 ID 대신 번호(eleven1, eleven2)와 이름만
def test_voices_lists_demo_voices_without_ids():
    client = eleven_client(VoiceTTS())
    assert client.get("/api/voices").json() == [{"id": "eleven1", "name": "경상도 사투리"},
                                                {"id": "eleven2", "name": "둘째"}]


def test_no_demo_voices_without_key():
    client = eleven_client(VoiceTTS(), elevenlabs_api_key="")
    assert client.get("/api/voices").json() == []


def test_chosen_demo_voice_is_used():
    tts = VoiceTTS()
    client = eleven_client(tts)
    r0 = start_with(client, "eleven2").json()
    assert r0["story"]["voice"] == {"provider": "elevenlabs", "model": "eleven_multilingual_v2", "voice": "voice456"}
    assert client.post("/api/tts", json=tts_req(r0)).status_code == 200
    assert tts.voices == ["elevenlabs"]


def test_gemini_unless_demo_voice_chosen():
    client = eleven_client(VoiceTTS())
    assert start_with(client, None).json()["story"]["voice"]["provider"] == "gemini"


def test_unknown_voice_falls_back_to_gemini():
    # 시연이 끝나 목소리를 지웠는데 기기에 'eleven1' 이 남아 있는 경우
    client = eleven_client(VoiceTTS(), elevenlabs_voice_id="")
    r = start_with(client, "eleven1")
    assert r.status_code == 200 and r.json()["story"]["voice"]["provider"] == "gemini"


def test_elevenlabs_failure_does_not_switch_voice():
    tts = FakeTTS(fail=True)
    client = eleven_client(tts)
    r0 = start_with(client, "eleven1").json()
    assert client.post("/api/tts", json=tts_req(r0)).status_code == 502
    assert tts.calls == 2          # 같은 목소리로 1번 더, Gemini 로는 넘어가지 않음
