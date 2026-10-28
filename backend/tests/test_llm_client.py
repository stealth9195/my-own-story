import json

import httpx
import pytest

from app.llm.client import LLMError, OpenAICompatClient

MSGS = [{"role": "user", "content": "안녕"}]


def ok_body(content="{}"):
    return {"choices": [{"message": {"content": content}}]}


def make_client(handler, json_mode=True):
    return OpenAICompatClient(
        base_url="https://x/v1", api_key="k", model="m",
        json_mode=json_mode, transport=httpx.MockTransport(handler),
    )


def test_sends_model_messages_and_json_mode():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=ok_body())

    res = make_client(handler).complete(MSGS)
    assert seen["url"] == "https://x/v1/chat/completions"
    assert seen["auth"] == "Bearer k"
    assert seen["body"]["model"] == "m"
    assert seen["body"]["messages"] == MSGS
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert res.text == "{}"
    assert res.model == "m"
    assert res.latency_ms >= 0


def test_json_mode_off_omits_response_format():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=ok_body())

    make_client(handler, json_mode=False).complete(MSGS)
    assert "response_format" not in seen["body"]


def test_non_200_raises_with_status():
    client = make_client(lambda r: httpx.Response(429, json={"error": "limit"}))
    with pytest.raises(LLMError) as e:
        client.complete(MSGS)
    assert e.value.status == 429


def test_network_error_raises():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(LLMError) as e:
        make_client(handler).complete(MSGS)
    assert e.value.status is None


@pytest.mark.parametrize("content", [None, ""])
def test_empty_content_raises(content):
    client = make_client(lambda r: httpx.Response(200, json=ok_body(content)))
    with pytest.raises(LLMError):
        client.complete(MSGS)
