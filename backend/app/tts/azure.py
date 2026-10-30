"""Azure 음성(무료 F0: 월 50만 자, 넘으면 거절되고 요금은 없음). 안내·질문·선택지처럼 짧은 글을 읽는다."""
from xml.sax.saxutils import escape

import httpx

from app.tts.gemini import TTSError

# 화면에서 고르는 이름 → Azure 목소리
VOICES = {"female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"}
# 아이에게 안내하는 말이라 아주 조금 느리게
RATE = "-5%"


def synthesize(text: str, voice: str, key: str, region: str) -> bytes:
    """MP3(24kHz, 48kbps)를 돌려준다."""
    ssml = (f"<speak version='1.0' xml:lang='ko-KR'><voice name='{VOICES[voice]}'>"
            f"<prosody rate='{RATE}'>{escape(text)}</prosody></voice></speak>")
    try:
        resp = httpx.post(
            f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
            headers={"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
                     "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"},
            content=ssml.encode("utf-8"), timeout=20,
        )
    except httpx.HTTPError as e:
        raise TTSError(f"요청 실패: {e}") from e
    if resp.status_code != 200:
        raise TTSError(f"HTTP {resp.status_code}: {resp.text[:200]}", status=resp.status_code)
    return resp.content
