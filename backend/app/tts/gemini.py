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
# 한국어 지시문은 3.x 모델이 소리 내어 읽은 사례가 있어 영어로 구분해 둔다.
STYLES: dict[str, str | None] = {
    "slow": "Read the following Korean text aloud slowly and gently, like a bedtime story "
            "for a young child. Do not read this instruction.\n\n",
    "normal": None,
}


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


def _body(text: str, voice: str, instruction: str | None) -> dict:
    return {"contents": [{"parts": [{"text": (instruction or "") + text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
            }}


def synthesize(text: str, voice: str, key: str, model: str = MODELS[0], style: str = "slow") -> bytes:
    """Gemini TTS는 16비트 PCM(24kHz)을 돌려주므로 WAV로 감싼다."""
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key},
            json=_body(text, voice, STYLES.get(style)),
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
