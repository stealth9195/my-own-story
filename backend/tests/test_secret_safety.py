"""배포 사고(2026-10-31): Render 에 넣은 GEMINI_API_KEY 끝에 줄바꿈이 붙어 있었다.
httpx 가 'Illegal header value b'Bearer <키>\\n'' 오류를 냈고, 그 오류 글이 그대로 segment_failed 로그에 남아
키가 로그에 노출됐다. → 키 값의 앞뒤 빈칸 제거, 요청 오류 글에 예외 내용 대신 종류만, 로그에서 비밀값 가리기"""
import json
import logging

import httpx
import pytest

from app.api.log import log_event, register_secrets
from app.config import Settings
from app.llm.client import LLMError, OpenAICompatClient
from app.tts import azure, elevenlabs, gemini, typecast
from app.tts.gemini import TTSError

KEY = "AQ.secret-key-value-1234"


def test_keys_are_stripped(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", KEY + "\n")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "  el-key\r\n")
    s = Settings(_env_file=None, primary_model="m", story_secret="s" * 32 + "\n")
    assert s.gemini_api_key == KEY and s.elevenlabs_api_key == "el-key" and s.story_secret == "s" * 32


def raise_header_error(*a, **k):
    raise httpx.LocalProtocolError(f"Illegal header value b'Bearer {KEY}\\n'")


def test_llm_request_error_hides_header():
    client = OpenAICompatClient(base_url="http://x", api_key=KEY, model="m",
                                transport=httpx.MockTransport(raise_header_error))
    with pytest.raises(LLMError) as info:
        client.complete([{"role": "user", "content": "hi"}])
    assert KEY not in str(info.value) and "LocalProtocolError" in str(info.value)


@pytest.mark.parametrize("call", [
    lambda: gemini.synthesize("안녕", "Kore", KEY),
    lambda: elevenlabs.synthesize("안녕", "v", KEY),
    lambda: typecast.synthesize("안녕", "v", KEY),
    lambda: azure.synthesize("안녕", "female", KEY, "koreacentral"),
])
def test_tts_request_error_hides_header(monkeypatch, call):
    monkeypatch.setattr(httpx, "post", raise_header_error)
    with pytest.raises(TTSError) as info:
        call()
    assert KEY not in str(info.value)


def test_log_masks_registered_secrets(caplog):
    caplog.set_level(logging.INFO, logger="story")
    register_secrets(KEY, "", "short")
    log_event("x", message=f"Bearer {KEY}", nested={"m": [KEY]})
    text = caplog.records[-1].getMessage()
    assert KEY not in text and "…1234" in text
    assert json.loads(text)["kind"] == "x"
