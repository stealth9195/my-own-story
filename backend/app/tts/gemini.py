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
# 한 문장짜리 지시(콜론으로 본문과 구분)는 3.x 모델이 지시까지 소리 내어 읽었다(2026-10-30).
# Gemini TTS 안내서의 형식처럼 '연출 메모'와 '읽을 글(TRANSCRIPT)'을 제목으로 나눈다.
# 속도: 너무 빠르면 아이가 못 따라오고, 너무 느리면 졸리다 → '보통보다 조금 느리게, 또렷하고 생기 있게'.
# 재생 속도(playbackRate)를 낮추면 음질이 나빠져서, 속도는 되도록 이 지시로 맞춘다
DIRECTION = ("### DIRECTOR'S NOTES\n"
             "Voice: a warm, friendly picture-book storyteller for young children.\n"
             "Pace: a little slower than normal conversation, clear and gently lively (not sleepy), "
             "with a short pause between sentences.\n"
             "Read ONLY the transcript below, in Korean. Never read these notes aloud.\n\n"
             "#### TRANSCRIPT\n")


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


def _error_summary(resp) -> str:
    """오류 본문에서 한도 이름(quotaId: 하루 PerDay·분당 PerMinute)과 다시 되는 시간만 뽑는다.
    본문을 앞에서부터 잘라 남겼더니 긴 안내문에 밀려 한도 이름이 빠졌다(2026-10-30)"""
    try:
        details = resp.json()["error"].get("details", [])
    except (ValueError, KeyError, TypeError, AttributeError):
        return resp.text[:300]
    quotas = [v.get("quotaId", "") for d in details for v in d.get("violations", [])]
    retry = next((d["retryDelay"] for d in details if "retryDelay" in d), "")
    if not quotas and not retry:
        return resp.text[:300]
    return f"quota={','.join(q for q in quotas if q)} retry={retry}"


def _body(text: str, voice: str) -> dict:
    return {"contents": [{"parts": [{"text": DIRECTION + text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
            }}


def _to_wav(mime: str, raw: bytes) -> bytes:
    """2.5 는 순수 PCM(audio/L16;...;rate=24000), 3.8 은 WAV 파일 통째(audio/wav)를 보낸다.
    WAV 를 PCM 으로 보고 다시 감쌌더니 앞의 파일 정보와 뒤의 출처 표시(약 6KB)가
    소리로 재생돼 시작 잡음·끝 '콱' 소리가 났다(2026-10-30). 소리 부분(data)만 꺼낸다"""
    if raw[:4] == b"RIFF":
        with wave.open(io.BytesIO(raw), "rb") as w:
            return pcm_to_wav(w.readframes(w.getnframes()), w.getframerate())
    rate = next((int(p.split("=")[1]) for p in mime.split(";") if p.strip().startswith("rate=")), 24000)
    return pcm_to_wav(raw, rate)


def synthesize(text: str, voice: str, key: str, model: str = MODELS[0]) -> bytes:
    """Gemini TTS 응답(PCM 또는 WAV)을 16비트 모노 WAV 로 맞춘다."""
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key},
            json=_body(text, voice),
            timeout=120,
        )
    except httpx.HTTPError as e:
        raise TTSError(f"요청 실패: {e}") from e
    if resp.status_code != 200:
        raise TTSError(f"HTTP {resp.status_code}: {_error_summary(resp)}", status=resp.status_code)
    try:
        inline = resp.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
        mime, data = inline.get("mimeType", ""), inline["data"]
    except (ValueError, KeyError, IndexError) as e:
        raise TTSError(f"응답 형식 오류: {resp.text[:200]}", status=200) from e
    try:
        return _to_wav(mime, base64.b64decode(data))
    except (wave.Error, EOFError, ValueError) as e:
        raise TTSError(f"소리 형식 오류: {mime}", status=200) from e
