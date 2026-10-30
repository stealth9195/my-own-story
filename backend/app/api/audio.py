import io
import struct
import wave

import lameenc

FADE_SECONDS = 0.15     # 끝을 서서히 줄이는 길이
SILENCE_SECONDS = 0.3   # 뒤에 붙이는 무음


def soften_end(pcm: bytes, rate: int) -> bytes:
    """모노 16비트 PCM 의 끝을 서서히 줄이고 무음을 붙인다.
    Gemini 음성은 말이 끝까지 이어지다 툭 끊기는 경우가 있어, 끝에서 '틱·치직' 소리가 날 수 있다 (2026-10-30)"""
    n = len(pcm) // 2
    samples = list(struct.unpack(f"<{n}h", pcm[: n * 2]))
    fade = min(int(rate * FADE_SECONDS), n)
    for i in range(fade):
        k = n - fade + i
        samples[k] = int(samples[k] * (fade - 1 - i) / fade)
    return struct.pack(f"<{n}h", *samples) + bytes(2) * int(rate * SILENCE_SECONDS)


def wav_to_mp3(wav: bytes, kbps: int = 48) -> bytes:
    """모노 16비트 WAV → MP3. 음성은 프론트 IndexedDB 에 쌓이므로 WAV(1편 6~8MB)를 약 1/8로 줄인다."""
    with wave.open(io.BytesIO(wav), "rb") as w:
        rate, channels, pcm = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    if channels == 1 and w.getsampwidth() == 2:
        pcm = soften_end(pcm, rate)
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(rate)
    enc.set_channels(channels)
    enc.set_quality(2)
    return bytes(enc.encode(pcm) + enc.flush())  # lameenc 는 bytearray 를 돌려준다
