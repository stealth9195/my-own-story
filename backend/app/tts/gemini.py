import base64
import io
import wave

import httpx

# 무료 한도: 모델마다 하루 10회, 분당 3회 (2026-10 AI Studio 기준)
MODELS = [
    "gemini-2.5-flash-preview-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-3.8-flash-tts",
    "gemini-3.8-flash-lite-tts",
]
VOICES = ["Kore", "Aoede", "Leda"]
# TTS 모델은 systemInstruction을 거부(400)하므로 본문 앞에 연출 지시를 붙인다.
# 한국어 지시문은 3.x 모델이 소리 내어 읽은 사례가 있어 영어로, 짧게, 콜론(:)으로 본문과 나눈다.
# 속도: 너무 빠르면 아이가 못 따라오고, 너무 느리면 졸리다 → '보통 대화보다 조금 느리게, 또렷하고 생기 있게'.
# 재생 속도(playbackRate)를 낮추면 음질이 나빠져서, 속도는 되도록 이 지시로 맞춘다 (2026-10-30)
DIRECTION = ("Read the following Korean story aloud like a warm, friendly picture-book storyteller "
             "for young children: a little slower than normal conversation, clear and gently lively "
             "(not sleepy), with a short pause between sentences:\n\n")


def direction(pause: float | None) -> str:
    """(실험) pause 초를 주면 'short pause' 대신 '약 N초 쉼'으로 지시한다"""
    if pause is None:
        return DIRECTION
    return DIRECTION.replace("a short pause", f"a pause of about {pause:g} seconds")


class TTSError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def _body(text: str, voice: str, pause: float | None = None) -> dict:
    return {"contents": [{"parts": [{"text": direction(pause) + text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
            }}


def synthesize(text: str, voice: str, key: str, model: str = MODELS[0], pause: float | None = None) -> bytes:
    """Gemini TTS는 16비트 PCM(24kHz)을 돌려주므로 WAV로 감싼다."""
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key},
            json=_body(text, voice, pause),
            timeout=120,
        )
    except httpx.HTTPError as e:
        raise TTSError(f"요청 실패: {e}") from e
    if resp.status_code != 200:
        raise TTSError(f"HTTP {resp.status_code}: {resp.text[:200]}", status=resp.status_code)
    try:
        data = resp.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except (ValueError, KeyError, IndexError) as e:
        raise TTSError(f"응답 형식 오류: {resp.text[:200]}", status=200) from e
    return pcm_to_wav(base64.b64decode(data))
