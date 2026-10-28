"""수동 심사용: 이야기 → 읽기용 텍스트, 챗봇이 돌려준 점수 CSV 읽기."""

import csv
import io
from pathlib import Path

# 기준별 배점 (합계 100). judge_prompt.md와 같은 값이어야 한다.
CRITERIA: dict[str, int] = {
    "vocabulary": 15,
    "plot": 15,
    "structure": 15,
    "moral": 10,
    "coherence": 20,
    "choices": 10,
    "length": 5,
    "safety": 10,
}
PROMPT_PATH = Path(__file__).with_name("judge_prompt.md")


def story_to_text(story: dict) -> str:
    parts = []
    if story.get("card_names"):
        parts.append("아이가 고른 카드: " + ", ".join(story["card_names"]))
    for i, seg in enumerate(story["segments"], 1):
        lines = [f"[구간 {i}: {seg['type']}]"] + [p["text"] for p in seg["pages"]]
        if seg["choices"]:
            labels = {c["id"]: c["label"] for c in seg["choices"]}
            lines.append("선택지: " + ", ".join(labels.values()))
            if seg.get("chosen"):
                lines.append("고른 선택지: " + labels.get(seg["chosen"], seg["chosen"]))
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def parse_scores_csv(path: Path) -> list[dict]:
    """챗봇 답변을 붙여넣은 CSV를 읽는다. 파일 이름(확장자 제외)이 심사자 이름.
    코드 블록 표시, 헤더 앞 설명 문장, total 등 추가 열은 무시한다."""
    lines = [l for l in path.read_text(encoding="utf-8-sig").splitlines()
             if l.strip() and not l.strip().startswith("```")]
    start = next((i for i, l in enumerate(lines) if l.strip().lower().startswith("file")), None)
    if start is None:
        raise ValueError(f"{path.name}: 'file'로 시작하는 헤더 없음")
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
    missing = [c for c in CRITERIA if c not in reader.fieldnames]
    if missing:
        raise ValueError(f"{path.name}: 열 없음 {missing}")

    rows = []
    for row in reader:
        scores = {}
        for c, max_score in CRITERIA.items():
            value = int(row[c].strip())
            if not 0 <= value <= max_score:
                raise ValueError(f"{path.name} {row['file']}: {c}={value} (0~{max_score})")
            scores[c] = value
        rows.append({"file": row["file"].strip().removesuffix(".md"),
                     "judge": path.stem, "scores": scores})
    return rows
