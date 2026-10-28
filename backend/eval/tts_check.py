"""TTS 업체·목소리 비교. 결과 파일을 직접 들어보고 고른다.

uv run --env-file .env python -m eval.tts_check [--text "..."]
출력: eval/tts_out/<업체>_<목소리>.(mp3|wav)
"""

import argparse
import base64
import io
import os
import time
import wave
from pathlib import Path
from xml.sax.saxutils import escape

import httpx

from eval.console import setup_console

OUT_DIR = Path(__file__).parent / "tts_out"
SAMPLE = (
    "옛날 옛적, 장미가 가득한 정원에 작은 토끼가 살았어요. "
    "토끼는 매일 아침 꽃잎에 맺힌 이슬을 보며 인사를 했지요. "
    "어느 날 밤, 하늘에서 반짝이는 별 하나가 정원으로 툭 떨어졌어요. "
    "토끼는 깜짝 놀라 귀를 쫑긋 세웠어요. 별이 작은 목소리로 말했어요. "
    "\"안녕, 나는 길을 잃었어. 집에 가는 길을 함께 찾아 줄래?\""
)
AZURE_VOICES = ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"]
# Gemini TTS: 모델 ID는 바뀔 수 있어 환경 변수로 덮어쓸 수 있게 함
GEMINI_TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_VOICES = ["Kore", "Aoede", "Leda"]
GEMINI_STYLE = "아이에게 잠자리 동화를 읽어주듯 다정하고 천천히 읽어줘: "


def azure(text: str, voice: str, key: str, region: str) -> bytes:
    ssml = (f"<speak version='1.0' xml:lang='ko-KR'><voice name='{voice}'>"
            f"{escape(text)}</voice></speak>")
    resp = httpx.post(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={"Ocp-Apim-Subscription-Key": key,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"},
        content=ssml.encode("utf-8"),
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def gemini(text: str, voice: str, key: str) -> bytes:
    """Gemini TTS는 16비트 PCM(24kHz)을 돌려주므로 WAV로 감싼다."""
    resp = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TTS_MODEL}:generateContent",
        headers={"x-goog-api-key": key},
        json={"contents": [{"parts": [{"text": GEMINI_STYLE + text}]}],
              "generationConfig": {
                  "responseModalities": ["AUDIO"],
                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
              }},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    return pcm_to_wav(base64.b64decode(data))


def main(argv: list[str] | None = None) -> None:
    setup_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default=SAMPLE)
    args = parser.parse_args(argv)

    gkey = os.environ.get("GEMINI_API_KEY")
    akey, region = os.environ.get("AZURE_SPEECH_KEY"), os.environ.get("AZURE_SPEECH_REGION")
    jobs = []
    if akey and region:
        jobs += [("azure", v, "mp3", lambda v=v: azure(args.text, v, akey, region))
                 for v in AZURE_VOICES]
    if gkey:
        jobs += [("gemini", v, "wav", lambda v=v: gemini(args.text, v, gkey))
                 for v in GEMINI_VOICES]

    skipped = [n for n, ok in [("azure", akey and region), ("gemini", gkey)] if not ok]
    if skipped:
        print(f"키 없음: {', '.join(skipped)} 건너뜀")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"문장 길이: {len(args.text)}자")
    for vendor, voice, ext, synth in jobs:
        start = time.perf_counter()
        try:
            audio = synth()
        except (httpx.HTTPError, KeyError, IndexError) as e:
            print(f"{vendor} {voice}: 실패 ({e})")
            continue
        ms = int((time.perf_counter() - start) * 1000)
        path = OUT_DIR / f"{vendor}_{voice}.{ext}"
        path.write_bytes(audio)
        print(f"{vendor} {voice}: {ms}ms, {len(audio) // 1024}KB → {path.name}")


if __name__ == "__main__":
    main()
