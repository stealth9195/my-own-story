"""TTS 업체·목소리 비교. 결과 파일을 직접 들어보고 고른다.

uv run --env-file .env python -m eval.tts_check [--text "..."]
출력: eval/tts_out/<업체>_<목소리>.(mp3|wav)
"""

import argparse
import os
import time
from pathlib import Path
from xml.sax.saxutils import escape

import httpx

from app.tts import gemini as gemini_tts
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
        jobs += [("gemini", v, "wav", lambda v=v: gemini_tts.synthesize(args.text, v, gkey))
                 for v in gemini_tts.VOICES]

    skipped = [n for n, ok in [("azure", akey and region), ("gemini", gkey)] if not ok]
    if skipped:
        print(f"키 없음: {', '.join(skipped)} 건너뜀")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"문장 길이: {len(args.text)}자")
    for vendor, voice, ext, synth in jobs:
        start = time.perf_counter()
        try:
            audio = synth()
        except (httpx.HTTPError, gemini_tts.TTSError) as e:
            print(f"{vendor} {voice}: 실패 ({e})")
            continue
        ms = int((time.perf_counter() - start) * 1000)
        path = OUT_DIR / f"{vendor}_{voice}.{ext}"
        path.write_bytes(audio)
        print(f"{vendor} {voice}: {ms}ms, {len(audio) // 1024}KB → {path.name}")


if __name__ == "__main__":
    main()
