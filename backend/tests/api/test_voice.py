import random
from datetime import datetime, timedelta, timezone

from app.api.limits import Limits
from app.api.schemas import Voice
from app.api.voice import ELEVENLABS_CHARS_PER_STORY, pick_voice
from app.tts import gemini, typecast

NOW = datetime(2026, 10, 29, 12, tzinfo=timezone(timedelta(hours=9)))


def limits() -> Limits:
    return Limits(per_user=3, total=30, clock=lambda: NOW)


def test_first_gemini_with_room():
    lim = limits()
    v = pick_voice(lim, choice_count=4, rng=random.Random(0))
    assert v.provider == "gemini" and v.model == gemini.MODELS[0] and v.voice in gemini.VOICES
    assert lim.gemini_left(gemini.MODELS[0]) == 5


def test_skips_full_model():
    lim = limits()
    lim.reserve_gemini(gemini.MODELS[0], 6)
    v = pick_voice(lim, choice_count=4, rng=random.Random(0))
    assert v.model == gemini.MODELS[1]


def test_typecast_when_gemini_full():
    lim = limits()
    for m in gemini.MODELS:
        lim.reserve_gemini(m, 6)
    v = pick_voice(lim, choice_count=4, rng=random.Random(0))
    assert v.provider == "typecast" and v.model == typecast.MODELS[0] and v.voice in typecast.VOICES
    assert lim.typecast_left() == 14000


def test_browser_when_all_full():
    lim = limits()
    for m in gemini.MODELS:
        lim.reserve_gemini(m, 6)
    lim.reserve_typecast(14001)
    v = pick_voice(lim, choice_count=4, rng=random.Random(0))
    assert v.provider == "browser" and v.model is None


def test_preferred_gemini_voice_is_used():
    v = pick_voice(limits(), choice_count=4, rng=random.Random(0), preferred="Aoede")
    assert v.provider == "gemini" and v.voice == "Aoede"


def test_preferred_voice_ignored_for_typecast():
    lim = limits()
    for m in gemini.MODELS:
        lim.reserve_gemini(m, 10)
    v = pick_voice(lim, choice_count=4, rng=random.Random(0), preferred="Aoede")
    assert v.provider == "typecast" and v.voice in typecast.VOICES


# 시연용 ElevenLabs: 키·목소리가 설정돼 있으면 먼저 쓰고, 하루 글자 수 상한을 넘으면 Gemini 로
ELEVEN = Voice(provider="elevenlabs", model="eleven_multilingual_v2", voice="voice123")


def test_elevenlabs_first_when_set():
    lim = limits()
    v = pick_voice(lim, choice_count=4, rng=random.Random(0), elevenlabs=ELEVEN)
    assert v == ELEVEN
    assert lim.gemini_left(gemini.MODELS[0]) == 10      # Gemini 는 예약하지 않음
    assert lim.elevenlabs_left(daily_chars=5000) == 5000 - ELEVENLABS_CHARS_PER_STORY


def test_elevenlabs_daily_cap_falls_back_to_gemini():
    lim = limits()
    lim.reserve_elevenlabs(5000)
    v = pick_voice(lim, choice_count=4, rng=random.Random(0), elevenlabs=ELEVEN, elevenlabs_daily_chars=5000)
    assert v.provider == "gemini"
