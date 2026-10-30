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
    assert type(out) is bytes  # lameenc 는 bytearray 를 돌려줌 → Response 가 처리 못 함


def test_mp3_44k():  # Typecast
    wav = sine_wav(44100)
    out = wav_to_mp3(wav)
    assert is_mp3(out) and len(out) < len(wav) / 4


def test_soften_end_fades_out_and_adds_silence():
    # 끝이 툭 끊기면 '틱·치직' 소리가 날 수 있어, 끝 0.15초를 서서히 줄이고 0.3초 무음을 붙인다
    from app.api.audio import soften_end
    rate = 24000
    pcm = struct.pack("<h", 8000) * rate  # 1초 동안 큰 값이 이어지다 끝남
    out = soften_end(pcm, rate)
    samples = struct.unpack(f"<{len(out) // 2}h", out)
    assert len(samples) == rate + int(rate * 0.3)
    assert samples[rate - int(rate * 0.15) - 1] == 8000     # 줄이기 전은 그대로
    assert abs(samples[rate - 1]) < 100                      # 원래 끝은 거의 0
    assert set(samples[rate:]) == {0}                        # 붙인 무음
