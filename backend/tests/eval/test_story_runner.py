import json

from app.catalog import load_catalog
from app.llm.client import LLMError
from app.story.safety import load_banned_words
from conftest import FakeLLM, segment_json
from eval.run_generate import run_model
from eval.story_runner import run_story

cat = load_catalog()
banned = load_banned_words()
CASE = {"id": "c01", "cards": ["rabbit", "rose", "star"], "picks": [0, 1, 2, 3, 4]}
MID = segment_json(pages=3, choices=("dragon", "rose", "star"))
END = segment_json(pages=4, choices=())


def story(llm, choice_count=3):
    return run_story(CASE, llm, cat, banned, choice_count, "v1")


def test_run_story_done_has_expected_segment_types():
    r = story(FakeLLM("m", [MID, MID, MID, END]))
    assert r["status"] == "done"
    assert r["failed_at"] is None
    assert [s["type"] for s in r["segments"]] == ["intro", "middle", "middle", "ending"]
    assert [s["chosen"] for s in r["segments"]] == ["dragon", "rose", "star", None]


def test_run_story_failure_recorded_not_raised():
    r = story(FakeLLM("m", [MID, "bad", "bad"]))
    assert r["status"] == "failed"
    assert r["failed_at"] == 1
    assert len(r["segments"]) == 1


def test_resume_skips_done_files(tmp_path):
    out = tmp_path / "m"
    out.mkdir()
    (out / "c01.json").write_text(json.dumps({"status": "done"}), encoding="utf-8")
    (out / "c02.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")
    cases = [CASE, {**CASE, "id": "c02"}]
    llm = FakeLLM("m", [MID, MID, MID, END])
    run_model(cases, llm, out, cat, banned, choice_count=3, version="v1")
    assert llm.calls == 4
    assert json.loads((out / "c02.json").read_text(encoding="utf-8"))["status"] == "done"


def test_stops_model_after_three_rate_limited_stories(tmp_path):
    cases = [{**CASE, "id": f"c0{i}"} for i in range(5)]
    llm = FakeLLM("m", [LLMError("limit", status=429)] * 5)
    run_model(cases, llm, tmp_path, cat, banned, choice_count=3, version="v1")
    assert llm.calls == 3
    assert len(list(tmp_path.glob("*.json"))) == 3
