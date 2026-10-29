import io
import math
import struct
import wave

from app.api.audio import wav_to_mp3


def sine_wav(rate: int, seconds: float = 1.0) -> bytes:
    frames = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
                      for i in range(int(rate * seconds)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    return buf.getvalue()


def is_mp3(data: bytes) -> bool:
    return data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0)


def test_mp3_24k():  # Gemini TTS
    wav = sine_wav(24000)
    out = wav_to_mp3(wav)
    assert is_mp3(out) and len(out) < len(wav) / 4


def test_mp3_44k():  # Typecast
    wav = sine_wav(44100)
    out = wav_to_mp3(wav)
    assert is_mp3(out) and len(out) < len(wav) / 4
