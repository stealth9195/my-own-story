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


def segment_json(pages=3, choices=("dragon", "cake", "moon")) -> str:
    page = {"text": "토끼가 숲에서 놀았어요.",
            "scene": {"background": "forest", "time": "day", "characters": [], "objects": []},
            "mood": "calm", "sfx": None}
    return json.dumps({"pages": [page] * pages,
                       "choices": [{"id": c, "label": c} for c in choices]},
                      ensure_ascii=False)


# 구간마다 새 선택지 (v2 규칙: 이미 나온 선택지는 다시 쓰지 않음)
# 테스트 카드(토끼·장미·별)와 겹치지 않게 구성
CHOICE_SETS = [("dragon", "cake", "moon"), ("apple", "balloon", "ship"),
               ("bear", "fox", "owl"), ("puppy", "princess", "treasure_box")]


def middles(n: int) -> list[str]:
    return [segment_json(pages=3, choices=CHOICE_SETS[i]) for i in range(n)]
