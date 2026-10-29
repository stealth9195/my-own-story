import httpx

from app.tts.gemini import TTSError

# 무료 플랜: 월 15,000자(글자당 1크레딧), 동시 호출 2개. 무료 음성은 비상업·출처 표기 필수
MODELS = ["ssfm-v30"]
# 목소리 ID → 화면 표시 이름. /v3/voices 의 ssfm-v30 중 용도 'Audiobook/Storytelling' 에서 골랐다.
# API 정보로는 지원 언어를 알 수 없어 한국어 이름인 목소리로 추렸다 (2026-10-29)
VOICES: dict[str, str] = {
    "tc_6a4f2130d153a5cac8e19996": "Jiseon (여·중년)",
    "tc_6699eb0f10b8e361d6a9aba1": "Minjung (여·청년)",
    "tc_600697fd8a8ea9b977284703": "Yeonhwa (여·중년)",
    "tc_5d01a52563338e00072b8c9c": "Juha (여·노년)",
    "tc_65571d1aa52fc0f2872045fa": "Storyteller Jinsub (남·중년)",
}
# Gemini 와 같은 이름을 쓰되, 연출 지시 대신 말 빠르기로 맞춘다. 감정은 Smart Emotion 이 문맥에서 고른다.
TEMPOS = {"slow": 0.9, "normal": 1.0}
# Typecast 문서가 요구하는 연동 출처 표시 (기능에는 영향 없음)
USER_AGENT = "typecast-direct/1 httpx typecast-integration/1 (source=api-docs; generated_by=claude-code)"


def _body(text: str, voice: str, model: str, style: str) -> dict:
    return {"model": model, "voice_id": voice, "text": text, "language": "kor",
            "prompt": {"emotion_type": "smart"},
            "output": {"audio_format": "wav", "audio_tempo": TEMPOS.get(style, 1.0)}}


def synthesize(text: str, voice: str, key: str, model: str = MODELS[0], style: str = "slow") -> bytes:
    """WAV(16비트, 44.1kHz)를 그대로 돌려준다. 402 는 크레딧 부족."""
    if not key:
        raise TTSError("TYPECAST_API_KEY 없음 (.env 확인)")
    try:
        resp = httpx.post(
            "https://api.typecast.ai/v1/text-to-speech",
            headers={"X-API-KEY": key, "User-Agent": USER_AGENT},
            json=_body(text, voice, model, style),
            timeout=120,
        )
    except httpx.HTTPError as e:
        raise TTSError(f"요청 실패: {e}") from e
    if resp.status_code != 200:
        raise TTSError(f"HTTP {resp.status_code}: {resp.text[:200]}", status=resp.status_code)
    return resp.content
