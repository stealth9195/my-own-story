"""TTS 업체·목소리 비교. 결과 mp3를 직접 들어보고 고른다.

uv run --env-file .env python -m eval.tts_check [--text "..."]
출력: eval/tts_out/<업체>_<목소리>.mp3
"""

import argparse
import base64
import os
import time
from pathlib import Path
from xml.sax.saxutils import escape

import httpx

OUT_DIR = Path(__file__).parent / "tts_out"
SAMPLE = (
    "옛날 옛적, 장미가 가득한 정원에 작은 토끼가 살았어요. "
    "토끼는 매일 아침 꽃잎에 맺힌 이슬을 보며 인사를 했지요. "
    "어느 날 밤, 하늘에서 반짝이는 별 하나가 정원으로 툭 떨어졌어요. "
    "토끼는 깜짝 놀라 귀를 쫑긋 세웠어요. 별이 작은 목소리로 말했어요. "
    "\"안녕, 나는 길을 잃었어. 집에 가는 길을 함께 찾아 줄래?\""
)
GOOGLE_VOICES = ["ko-KR-Neural2-A", "ko-KR-Wavenet-A", "ko-KR-Standard-A"]
AZURE_VOICES = ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"]


def google(text: str, voice: str, key: str) -> bytes:
    resp = httpx.post(
        f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}",
        json={"input": {"text": text},
              "voice": {"languageCode": "ko-KR", "name": voice},
              "audioConfig": {"audioEncoding": "MP3"}},
        timeout=60,
    )
    resp.raise_for_status()
    return base64.b64decode(resp.json()["audioContent"])


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default=SAMPLE)
    args = parser.parse_args()

    jobs = []
    if key := os.environ.get("GOOGLE_TTS_API_KEY"):
        jobs += [("google", v, lambda v=v: google(args.text, v, key)) for v in GOOGLE_VOICES]
    key, region = os.environ.get("AZURE_SPEECH_KEY"), os.environ.get("AZURE_SPEECH_REGION")
    if key and region:
        jobs += [("azure", v, lambda v=v: azure(args.text, v, key, region)) for v in AZURE_VOICES]

    skipped = [n for n, ok in [("google", os.environ.get("GOOGLE_TTS_API_KEY")),
                               ("azure", key and region)] if not ok]
    if skipped:
        print(f"키 없음: {', '.join(skipped)} 건너뜀")

    OUT_DIR.mkdir(exist_ok=True)
    print(f"문장 길이: {len(args.text)}자")
    for vendor, voice, synth in jobs:
        start = time.perf_counter()
        try:
            audio = synth()
        except httpx.HTTPError as e:
            print(f"{vendor} {voice}: 실패 ({e})")
            continue
        ms = int((time.perf_counter() - start) * 1000)
        path = OUT_DIR / f"{vendor}_{voice}.mp3"
        path.write_bytes(audio)
        print(f"{vendor} {voice}: {ms}ms, {len(audio) // 1024}KB → {path.name}")


if __name__ == "__main__":
    main()
