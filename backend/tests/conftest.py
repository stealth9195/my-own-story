import json

from app.llm.client import LLMError, LLMResponse


class FakeLLM:
    """응답 목록을 차례로 돌려주는 가짜 LLM. LLMError 항목은 예외로 던진다."""

    def __init__(self, model: str, responses: list):
        self.model = model
        self.responses = list(responses)
        self.calls = 0

    def complete(self, messages, temperature=0.9) -> LLMResponse:
        self.calls += 1
        item = self.responses.pop(0)
        if isinstance(item, LLMError):
            raise item
        return LLMResponse(text=item, model=self.model, latency_ms=10)


def segment_json(pages=3, choices=("dragon", "rose", "star")) -> str:
    page = {"text": "토끼가 숲에서 놀았어요.",
            "scene": {"background": "forest", "time": "day", "characters": [], "objects": []},
            "mood": "calm", "sfx": None}
    return json.dumps({"pages": [page] * pages,
                       "choices": [{"id": c, "label": c} for c in choices]},
                      ensure_ascii=False)
