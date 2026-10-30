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
    def tts(text: str, voice: Voice, pause: float | None = None) -> bytes:
        if voice.provider == "typecast":
            return typecast.synthesize(text, voice.voice, typecast_key, voice.model, style="normal")
        return gemini.synthesize(text, voice.voice, gemini_key, voice.model, pause)
    return tts


def synthesize_segment(text: str, voice: Voice, tts: TTSFn) -> bytes:
    """구간 본문 전체를 한 번에 읽어 MP3 로 돌려준다. 실패하면 같은 목소리로 1번 더 (목소리 섞지 않음)."""
    if voice.provider == "browser":
        raise ValueError("브라우저 TTS 이야기는 서버에서 음성을 만들지 않음")
    try:
        wav = tts(text, voice)
    except TTSError as e:
        if e.status in NO_RETRY:
            raise
        wav = tts(text, voice)
    return wav_to_mp3(wav)
