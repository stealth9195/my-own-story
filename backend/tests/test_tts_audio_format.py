"""Gemini TTS 응답의 소리 형식. 2.5 는 순수 PCM(audio/L16), 3.8 은 WAV 파일 통째(audio/wav)를 보낸다.
겪은 문제(2026-10-30): 3.8 의 WAV 를 PCM 으로 보고 다시 감싸서, 앞의 파일 정보(44바이트)와
뒤에 붙은 출처 표시(C2PA·IPTC 'trainedAlgorithmicMedia', 약 6KB)가 소리로 재생됐다 → 시작 잡음·끝 '콱'"""
import base64
import io
import json
import struct
import wave

import pytest

from app.tts import gemini

SPEECH = struct.pack("<4h", 100, -100, 200, -200)


class Resp:
    status_code = 200

    def __init__(self, mime: str, raw: bytes):
        self.text = json.dumps({"candidates": [{"content": {"parts": [{"inlineData": {
            "mimeType": mime, "data": base64.b64encode(raw).decode()}}]}}]})

    def json(self):
        return json.loads(self.text)


def frames_of(wav: bytes) -> tuple[int, bytes]:
    with wave.open(io.BytesIO(wav), "rb") as w:
        return w.getframerate(), w.readframes(w.getnframes())


def wav_with_trailer(pcm: bytes, rate: int) -> bytes:
    trailer = b"LIST" + struct.pack("<I", 70) + b"INFO" + b"digitalsourcetype/trainedAlgorithmicMedia".ljust(66, b"\0")
    return gemini.pcm_to_wav(pcm, rate) + trailer


def test_pcm_response_is_wrapped(monkeypatch):
    monkeypatch.setattr(gemini.httpx, "post", lambda *a, **k: Resp("audio/L16;codec=pcm;rate=24000", SPEECH))
    assert frames_of(gemini.synthesize("안녕", "Kore", "k")) == (24000, SPEECH)


def test_wav_response_keeps_only_sound(monkeypatch):
    raw = wav_with_trailer(SPEECH, 24000)
    monkeypatch.setattr(gemini.httpx, "post", lambda *a, **k: Resp("audio/wav", raw))
    assert frames_of(gemini.synthesize("안녕", "Kore", "k")) == (24000, SPEECH)


def test_pcm_rate_is_read_from_mime(monkeypatch):
    monkeypatch.setattr(gemini.httpx, "post", lambda *a, **k: Resp("audio/L16;codec=pcm;rate=16000", SPEECH))
    assert frames_of(gemini.synthesize("안녕", "Kore", "k"))[0] == 16000


def test_stereo_wav_is_rejected(monkeypatch):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(SPEECH)
    monkeypatch.setattr(gemini.httpx, "post", lambda *a, **k: Resp("audio/wav", buf.getvalue()))
    with pytest.raises(gemini.TTSError):
        gemini.synthesize("안녕", "Kore", "k")
