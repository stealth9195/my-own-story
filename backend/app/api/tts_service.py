from collections.abc import Callable

from app.api.audio import wav_to_mp3
from app.api.schemas import Voice
from app.tts import gemini, typecast
from app.tts.gemini import TTSError

# 본문 → WAV
TTSFn = Callable[[str, Voice], bytes]


def default_tts(gemini_key: str, typecast_key: str) -> TTSFn:
    # 연출 지시문 없이(normal) 읽는다. 지시문을 붙이면 3.x 모델이 지시문까지 소리 내어 읽음. 속도는 프론트 playbackRate
    def tts(text: str, voice: Voice) -> bytes:
        if voice.provider == "typecast":
            return typecast.synthesize(text, voice.voice, typecast_key, voice.model, style="normal")
        return gemini.synthesize(text, voice.voice, gemini_key, voice.model, style="normal")
    return tts


def synthesize_segment(text: str, voice: Voice, tts: TTSFn) -> bytes:
    """구간 본문 전체를 한 번에 읽어 MP3 로 돌려준다. 실패하면 같은 목소리로 1번 더 (목소리 섞지 않음)."""
    if voice.provider == "browser":
        raise ValueError("브라우저 TTS 이야기는 서버에서 음성을 만들지 않음")
    try:
        wav = tts(text, voice)
    except TTSError:
        wav = tts(text, voice)
    return wav_to_mp3(wav)
