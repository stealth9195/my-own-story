"""결과 요약 표.

uv run python -m eval.summarize eval/results/<run>
"""

import json
import sys
from pathlib import Path

from eval.judge import CRITERIA


def _pct(n: int, d: int) -> str:
    return f"{round(n / d * 100)}%" if d else "-"


def summarize(run_dir: Path) -> str:
    scores_path = run_dir / "scores.jsonl"
    scores = []
    if scores_path.exists():
        scores = [json.loads(l) for l in scores_path.read_text(encoding="utf-8").splitlines() if l]

    header = ["모델", "완료율", "첫 시도 성공률", "평균 생성 시간(초)"] + CRITERIA + ["총점(30)"]
    rows = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]

    for model_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        stories = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(model_dir.glob("*.json"))]
        done = sum(s["status"] == "done" for s in stories)
        segs = [seg for s in stories for seg in s.get("segments", [])]
        first_ok = sum(seg["attempts"][0]["ok"] for seg in segs)
        avg_sec = f"{sum(seg['latency_ms'] for seg in segs) / len(segs) / 1000:.1f}" if segs else "-"

        model_scores = [x["scores"] for x in scores if x["model"] == model_dir.name]
        if model_scores:
            avgs = [sum(s[c] for s in model_scores) / len(model_scores) for c in CRITERIA]
            crit_cells = [f"{a:.1f}" for a in avgs] + [f"{sum(avgs):.1f}"]
        else:
            crit_cells = ["-"] * (len(CRITERIA) + 1)

        cells = [model_dir.name, _pct(done, len(stories)), _pct(first_ok, len(segs)), avg_sec]
        rows.append("| " + " | ".join(cells + crit_cells) + " |")
    return "\n".join(rows)


def main() -> None:
    run_dir = Path(sys.argv[1])
    table = summarize(run_dir)
    (run_dir / "summary.md").write_text(table + "\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
