from pathlib import Path

from app.story.validator import extract_json

CRITERIA = ["length", "vocabulary", "plot", "coherence", "safety", "choices"]
PROMPT_PATH = Path(__file__).with_name("judge_prompt.md")


def story_to_text(story: dict) -> str:
    parts = []
    for i, seg in enumerate(story["segments"], 1):
        lines = [f"[구간 {i}: {seg['type']}]"] + [p["text"] for p in seg["pages"]]
        if seg["choices"]:
            labels = {c["id"]: c["label"] for c in seg["choices"]}
            lines.append("선택지: " + ", ".join(labels.values()))
            if seg.get("chosen"):
                lines.append("고른 선택지: " + labels.get(seg["chosen"], seg["chosen"]))
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def build_judge_messages(story_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8")},
        {"role": "user", "content": "이야기:\n\n" + story_text},
    ]


def parse_judge(raw: str) -> dict[str, int]:
    data = extract_json(raw)
    if data is None:
        raise ValueError("JSON 아님")
    result = {}
    for c in CRITERIA:
        v = data.get(c)
        if type(v) is not int or not 1 <= v <= 5:
            raise ValueError(f"{c} 점수 오류: {v!r}")
        result[c] = v
    return result
