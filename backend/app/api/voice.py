import random

from app.api.limits import Limits
from app.api.schemas import Voice
from app.tts import gemini, typecast

TYPECAST_CHARS_PER_STORY = 1000  # 1편 600~1,000자
ELEVENLABS_CHARS_PER_STORY = 1000


def pick_voice(limits: Limits, choice_count: int, rng: random.Random, preferred: str | None = None,
               elevenlabs: Voice | None = None, elevenlabs_daily_chars: int = 10000) -> Voice:
    """이야기 시작 때 한 번 정하고 끝까지 바꾸지 않는다. 1편 분량을 미리 예약한다.
    ElevenLabs(시연용, 설정돼 있을 때만) → Gemini(구간 수만큼 호출 남은 첫 모델) → Typecast(월 글자 수) → 브라우저 TTS.
    preferred: 설정에서 고른 Gemini 목소리. 없으면 무작위 (ElevenLabs·Typecast 로 정해지면 쓰지 않음)"""
    if elevenlabs and limits.elevenlabs_left(elevenlabs_daily_chars) >= ELEVENLABS_CHARS_PER_STORY:
        limits.reserve_elevenlabs(ELEVENLABS_CHARS_PER_STORY)
        return elevenlabs
    calls = choice_count + 1
    for model in gemini.MODELS:
        if limits.gemini_left(model) >= calls:
            limits.reserve_gemini(model, calls)
            voice = preferred if preferred in gemini.VOICES else rng.choice(gemini.VOICES)
            return Voice(provider="gemini", model=model, voice=voice)
    if limits.typecast_left() >= TYPECAST_CHARS_PER_STORY:
        limits.reserve_typecast(TYPECAST_CHARS_PER_STORY)
        return Voice(provider="typecast", model=typecast.MODELS[0],
                     voice=rng.choice(sorted(typecast.VOICES)))
    return Voice(provider="browser")
