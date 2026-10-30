import httpx

from app.tts.gemini import TTSError, pcm_to_wav

# 시연용 (유료 구독의 월 크레딧 안에서만, 글자당 1크레딧). 키를 비우면 쓰지 않는다
MODELS = ["eleven_multilingual_v2"]
RATE = 24000
# Gemini 연출 지시('조금 느리게')에 맞춰 말 빠르기를 조금 낮춘다 (0.7~1.2)
SPEED = 0.9


def synthesize(text: str, voice: str, key: str, model: str = MODELS[0]) -> bytes:
    """PCM(16비트, 24kHz)으로 받아 WAV 로 감싼다. MP3 로 받지 않는 이유: 길이 검사·끝 처리를 Gemini 와 같게.
    크레딧을 다 쓰면 401(quota_exceeded)"""
    if not key:
        raise TTSError("ELEVENLABS_API_KEY 없음 (.env 확인)")
    try:
        resp = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
            params={"output_format": f"pcm_{RATE}"},
            headers={"xi-api-key": key},
            json={"text": text, "model_id": model, "voice_settings": {"speed": SPEED}},
            timeout=120,
        )
    except httpx.HTTPError as e:
        raise TTSError(f"요청 실패: {type(e).__name__}") from e  # 예외 글에 요청 머리(키)가 들어갈 수 있다
    if resp.status_code != 200:
        raise TTSError(f"HTTP {resp.status_code}: {resp.text[:300]}", status=resp.status_code)
    return pcm_to_wav(resp.content, RATE)
