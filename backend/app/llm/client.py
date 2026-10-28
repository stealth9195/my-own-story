import time
from dataclasses import dataclass

import httpx


@dataclass
class LLMResponse:
    text: str
    model: str
    latency_ms: int


class LLMError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _merge_system(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [dict(m) for m in messages if m["role"] != "system"]
    if system and rest:
        rest[0]["content"] = system + "\n\n" + rest[0]["content"]
    return rest


class OpenAICompatClient:
    """OpenAI 호환 chat/completions API 클라이언트. OpenRouter, Gemini 모두 사용."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        json_mode: bool = True,
        merge_system: bool = False,
        extra_body: dict | None = None,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.model = model
        self.json_mode = json_mode
        # Gemma 등 system 역할을 거부하는 모델용: system 내용을 첫 user 메시지 앞에 붙인다
        self.merge_system = merge_system
        # 업체별 추가 옵션 (예: OpenRouter 추론 끄기 {"reasoning": {"enabled": False}})
        self.extra_body = extra_body or {}
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    def complete(self, messages: list[dict[str, str]], temperature: float = 0.9) -> LLMResponse:
        if self.merge_system:
            messages = _merge_system(messages)
        body: dict = {**self.extra_body, "model": self.model, "messages": messages,
                      "temperature": temperature}
        if self.json_mode:
            body["response_format"] = {"type": "json_object"}

        start = time.perf_counter()
        try:
            resp = self._http.post(self._url, json=body)
        except httpx.HTTPError as e:
            raise LLMError(f"요청 실패: {e}") from e
        latency_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code != 200:
            raise LLMError(f"HTTP {resp.status_code}: {resp.text[:200]}", status=resp.status_code)
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise LLMError(f"응답 형식 오류: {resp.text[:200]}", status=200) from e
        if not content:
            raise LLMError("빈 응답", status=200)
        return LLMResponse(text=content, model=self.model, latency_ms=latency_ms)
