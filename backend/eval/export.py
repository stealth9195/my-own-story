"""수동 심사용 내보내기. 완료된 이야기를 익명 파일(s01.md, s02.md...)로 만든다.

uv run python -m eval.export eval/results/<run> [--seed 42]
결과: <run>/export/ 에 이야기 파일, 평가질문.md, mapping.csv(파일 → 모델), scores/ 폴더
챗봇 답변의 CSV는 scores/<챗봇 이름>.csv 로 저장 (예: scores/chatgpt.csv)
"""

import argparse
import csv
import json
import random
import shutil
from pathlib import Path

from eval.console import setup_console
from eval.judge import PROMPT_PATH, story_to_text

EXPORT_DIR = "export"


def export(run_dir: Path, seed: int = 42) -> Path:
    out = run_dir / EXPORT_DIR
    scores_dir = out / "scores"
    if scores_dir.exists() and any(scores_dir.glob("*.csv")):
        raise RuntimeError("이미 점수가 입력돼 있음. 다시 내보내면 파일 번호가 바뀌므로 중단")

    stories = []
    for model_dir in sorted(p for p in run_dir.iterdir() if p.is_dir() and p.name != EXPORT_DIR):
        for f in sorted(model_dir.glob("*.json")):
            story = json.loads(f.read_text(encoding="utf-8"))
            if story.get("status") == "done":
                stories.append((model_dir.name, story))
    # 모델별로 몰려 있으면 심사자가 패턴을 눈치챌 수 있어 섞는다
    random.Random(seed).shuffle(stories)

    out.mkdir(parents=True, exist_ok=True)
    scores_dir.mkdir(exist_ok=True)
    for old in out.glob("s*.md"):
        old.unlink()
    rows = []
    for i, (model, story) in enumerate(stories, 1):
        name = f"s{i:02d}"
        (out / f"{name}.md").write_text(f"# {name}\n\n{story_to_text(story)}\n", encoding="utf-8")
        rows.append({"file": name, "model": model, "case_id": story["case_id"]})
    with (out / "mapping.csv").open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["file", "model", "case_id"])
        writer.writeheader()
        writer.writerows(rows)
    shutil.copyfile(PROMPT_PATH, out / "평가질문.md")
    return out


def main() -> None:
    setup_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    out = export(args.run_dir, args.seed)
    print(f"{len(list(out.glob('s*.md')))}편 내보냄 → {out}")


if __name__ == "__main__":
    main()
