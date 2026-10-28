import csv
import json

from eval.export import export


def write_story(path, model, case, status="done"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "case_id": case, "model": model, "status": status, "card_names": ["토끼"],
        "segments": [{"type": "ending", "pages": [{"text": "토끼 이야기"}],
                      "choices": [], "chosen": None}],
    }, ensure_ascii=False), encoding="utf-8")


def make_run(tmp_path):
    run = tmp_path / "run"
    write_story(run / "gemma" / "c01.json", "gemma-id", "c01")
    write_story(run / "gemma" / "c02.json", "gemma-id", "c02", status="failed")
    write_story(run / "nemotron" / "c01.json", "nemo-id", "c01")
    return run


def test_export_writes_anonymous_story_files_and_mapping(tmp_path):
    run = make_run(tmp_path)
    out = export(run, seed=1)
    files = sorted(p.name for p in out.glob("s*.md"))
    assert files == ["s01.md", "s02.md"]
    for f in out.glob("s*.md"):
        text = f.read_text(encoding="utf-8")
        assert "gemma" not in text and "nemotron" not in text
    with (out / "mapping.csv").open(encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    assert sorted((r["model"], r["case_id"]) for r in rows) == [("gemma", "c01"), ("nemotron", "c01")]


def test_export_copies_fixed_judge_prompt(tmp_path):
    out = export(make_run(tmp_path), seed=1)
    assert (out / "평가질문.md").read_text(encoding="utf-8").strip()


def test_export_same_seed_same_order(tmp_path):
    run = make_run(tmp_path)
    first = (export(run, seed=7) / "mapping.csv").read_text(encoding="utf-8")
    second = (export(run, seed=7) / "mapping.csv").read_text(encoding="utf-8")
    assert first == second
