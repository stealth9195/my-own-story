import random

from app.api.limits import Limits
from app.api.schemas import Voice
from app.tts import gemini, typecast

TYPECAST_CHARS_PER_STORY = 1000  # 1편 600~1,000자


def pick_voice(limits: Limits, choice_count: int, rng: random.Random) -> Voice:
    """이야기 시작 때 한 번 정하고 끝까지 바꾸지 않는다. 1편 분량을 미리 예약한다.
    Gemini(구간 수만큼 호출 남은 첫 모델) → Typecast(월 글자 수) → 브라우저 TTS."""
    calls = choice_count + 1
    for model in gemini.MODELS:
        if limits.gemini_left(model) >= calls:
            limits.reserve_gemini(model, calls)
            return Voice(provider="gemini", model=model, voice=rng.choice(gemini.VOICES))
    if limits.typecast_left() >= TYPECAST_CHARS_PER_STORY:
        limits.reserve_typecast(TYPECAST_CHARS_PER_STORY)
        return Voice(provider="typecast", model=typecast.MODELS[0],
                     voice=rng.choice(sorted(typecast.VOICES)))
    return Voice(provider="browser")
