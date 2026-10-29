import random
from datetime import datetime, timedelta, timezone

from app.api.limits import Limits
from app.api.voice import pick_voice
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
