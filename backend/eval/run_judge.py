"""완료된 이야기를 심사 모델들로 채점.

uv run --env-file .env python -m eval.run_judge --results eval/results/<run>
결과: <run>/scores.jsonl. 이미 채점한 (모델, 케이스, 심사자) 조합은 건너뜀.
"""

import argparse
import json
import os
from pathlib import Path

from app.llm.client import LLMError, OpenAICompatClient
from eval.judge import build_judge_messages, parse_judge, story_to_text

EVAL_DIR = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--judges", type=Path, default=EVAL_DIR / "judges.json")
    args = parser.parse_args()

    out = args.results / "scores.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line:
                x = json.loads(line)
                done.add((x["model"], x["case_id"], x["judge"]))

    for j in json.loads(args.judges.read_text(encoding="utf-8")):
        key = os.environ.get(j["api_key_env"])
        if not key:
            print(f"[{j['name']}] 환경 변수 {j['api_key_env']} 없음 → 건너뜀")
            continue
        judge = OpenAICompatClient(j["base_url"], key, j["model"], json_mode=j.get("json_mode", True))
        for model_dir in sorted(p for p in args.results.iterdir() if p.is_dir()):
            for f in sorted(model_dir.glob("*.json")):
                story = json.loads(f.read_text(encoding="utf-8"))
                k = (model_dir.name, story["case_id"], j["name"])
                if story["status"] != "done" or k in done:
                    continue
                try:
                    resp = judge.complete(build_judge_messages(story_to_text(story)), temperature=0.0)
                    scores = parse_judge(resp.text)
                except (LLMError, ValueError) as e:
                    print(f"[{j['name']}] {k[0]}/{k[1]} 실패: {e}")
                    continue
                with out.open("a", encoding="utf-8") as fp:
                    fp.write(json.dumps({"model": k[0], "case_id": k[1], "judge": k[2],
                                         "scores": scores}, ensure_ascii=False) + "\n")
                print(f"[{j['name']}] {k[0]}/{k[1]}: {sum(scores.values())}점")


if __name__ == "__main__":
    main()
