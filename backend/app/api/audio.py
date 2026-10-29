import io
import wave

import lameenc


def wav_to_mp3(wav: bytes, kbps: int = 48) -> bytes:
    """모노 16비트 WAV → MP3. 음성은 프론트 IndexedDB 에 쌓이므로 WAV(1편 6~8MB)를 약 1/8로 줄인다."""
    with wave.open(io.BytesIO(wav), "rb") as w:
        rate, channels, pcm = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(rate)
    enc.set_channels(channels)
    enc.set_quality(2)
    return enc.encode(pcm) + enc.flush()
