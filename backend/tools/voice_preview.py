"""시연용 ElevenLabs 목소리 미리 듣기 파일 → frontend/public/voice/eleven1.mp3, eleven2.mp3
설정 창에서 누를 때마다 만들면 크레딧이 빠지므로 한 번 만들어 둔다. 목소리 ID 를 바꾸면 다시 실행한다.

uv run --env-file .env python -m tools.voice_preview
"""
from app.api.audio import wav_to_mp3
from app.config import REPO_ROOT, Settings
from app.tts import elevenlabs

TEXT = "옛날 옛적, 작은 토끼가 숲속 친구들을 만나러 길을 떠났어요."
OUT_DIR = REPO_ROOT / "frontend" / "public" / "voice"


def main() -> None:
    s = Settings()
    for slot, (name, voice_id) in s.demo_voices().items():
        wav = elevenlabs.synthesize(TEXT, voice_id, s.elevenlabs_api_key, s.elevenlabs_model)
        out = OUT_DIR / f"{slot}.mp3"
        out.write_bytes(wav_to_mp3(wav))
        print(f"{slot} ({name}, …{voice_id[-4:]}) → {out.name}")


if __name__ == "__main__":
    main()
