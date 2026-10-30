from collections.abc import Callable

from app.api.audio import wav_to_mp3
from app.api.schemas import Voice
from app.tts import gemini, typecast
from app.tts.gemini import TTSError

# 본문 → WAV
TTSFn = Callable[[str, Voice], bytes]
# 한도 초과(429)·크레딧 부족(402)은 바로 다시 불러도 실패하고 한도만 더 쓴다
NO_RETRY = {429, 402}


def default_tts(gemini_key: str, typecast_key: str) -> TTSFn:
    # Gemini 는 gemini.DIRECTION(이야기꾼 말투·조금 느리게)을 붙여 읽는다. Typecast 는 보통 빠르기
    def tts(text: str, voice: Voice) -> bytes:
        if voice.provider == "typecast":
            return typecast.synthesize(text, voice.voice, typecast_key, voice.model, style="normal")
        return gemini.synthesize(text, voice.voice, gemini_key, voice.model)
    return tts


def is_daily_quota(e: TTSError) -> bool:
    """Google 429 중 하루 한도(분당 한도와 구분). 오류 본문의 한도 이름으로 판단"""
    text = str(e).lower()
    return e.status == 429 and ("per_day" in text or "perday" in text)


def voices_to_try(voice: Voice, gemini_left: Callable[[str], int], used_up: Callable[[str], bool]) -> list[Voice]:
    """정해진 목소리가 막히면 같은 목소리 이름으로 한도가 남은 다른 Gemini 모델 (목소리가 거의 비슷하게 이어짐).
    오늘 다 쓴 모델은 처음부터 건너뛴다. Typecast 는 대신할 모델이 없다"""
    if voice.provider != "gemini":
        return [voice]
    first = [] if used_up(voice.model) else [voice]
    others = [Voice(provider="gemini", model=m, voice=voice.voice) for m in gemini.MODELS
              if m != voice.model and gemini_left(m) > 0]
    return first + others


def synthesize_segment(text: str, voice: Voice, tts: TTSFn, retry: bool = True) -> bytes:
    """구간 본문 전체를 한 번에 읽어 MP3 로 돌려준다. 실패하면 같은 목소리로 1번 더 (retry).
    다른 모델로 대신 읽을 때는 다시 시도하지 않는다 (화면이 음성을 90초까지 기다리고, 한 번에 약 15초)"""
    if voice.provider == "browser":
        raise ValueError("브라우저 TTS 이야기는 서버에서 음성을 만들지 않음")
    try:
        wav = tts(text, voice)
    except TTSError as e:
        if e.status in NO_RETRY or not retry:
            raise
        wav = tts(text, voice)
    return wav_to_mp3(wav)
