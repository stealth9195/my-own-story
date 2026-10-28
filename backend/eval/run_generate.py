"""모델별 이야기 생성 실행.

uv run --env-file .env python -m eval.run_generate --out eval/results/<run> [--cases c01,c02]
API 키는 .env의 환경 변수(models.json의 api_key_env)에서 읽는다.
"""

import argparse
import json
import os
from pathlib import Path

from app.catalog import Catalog, load_catalog
from app.config import Settings
from app.llm.client import OpenAICompatClient
from app.story.generator import LLM
from app.story.safety import load_banned_words
from eval.story_runner import is_rate_limited, run_story

EVAL_DIR = Path(__file__).parent
MAX_RATE_LIMITED = 3


def run_model(
    cases: list[dict],
    llm: LLM,
    out_dir: Path,
    catalog: Catalog,
    banned: list[str],
    choice_count: int,
    version: str,
) -> None:
    """완료된 케이스는 건너뛰고, 한도 초과가 연속 3편이면 이 모델은 중단."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rate_limited = 0
    for case in cases:
        path = out_dir / f"{case['id']}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "done":
            continue
        story = run_story(case, llm, catalog, banned, choice_count, version)
        path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{llm.model}] {case['id']}: {story['status']}")
        rate_limited = rate_limited + 1 if is_rate_limited(story) else 0
        if rate_limited >= MAX_RATE_LIMITED:
            print(f"[{llm.model}] 한도 초과 {MAX_RATE_LIMITED}회 연속 → 중단. 나중에 다시 실행하세요.")
            return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, default=EVAL_DIR / "models.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cases", help="쉼표로 구분한 케이스 ID (생략 시 전체)")
    parser.add_argument("--choice-count", type=int, default=Settings.model_fields["choice_count"].default)
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()

    cases = json.loads((EVAL_DIR / "cases.json").read_text(encoding="utf-8"))
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    catalog, banned = load_catalog(), load_banned_words()

    for m in json.loads(args.models.read_text(encoding="utf-8")):
        key = os.environ.get(m["api_key_env"])
        if not key:
            print(f"[{m['name']}] 환경 변수 {m['api_key_env']} 없음 → 건너뜀")
            continue
        llm = OpenAICompatClient(m["base_url"], key, m["model"], json_mode=m.get("json_mode", True))
        run_model(cases, llm, args.out / m["name"], catalog, banned, args.choice_count, args.version)


if __name__ == "__main__":
    main()
