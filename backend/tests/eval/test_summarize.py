import json

from eval.judge import CRITERIA
from eval.summarize import summarize


def seg(ok_first=True, latency=1000):
    attempts = [{"model": "x", "ok": ok_first, "errors": [], "latency_ms": latency}]
    if not ok_first:
        attempts.append({"model": "x", "ok": True, "errors": [], "latency_ms": latency})
    return {"type": "middle", "pages": [], "choices": [], "chosen": None,
            "attempts": attempts, "latency_ms": latency * len(attempts)}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_summarize_table(tmp_path):
    # 모델 a: 완료 2편 (구간 4개 중 1개만 첫 시도 실패), 모델 b: 완료 1 + 실패 1
    write(tmp_path / "a" / "c01.json", {"status": "done", "segments": [seg(), seg(False)]})
    write(tmp_path / "a" / "c02.json", {"status": "done", "segments": [seg(), seg()]})
    write(tmp_path / "b" / "c01.json", {"status": "done", "segments": [seg()]})
    write(tmp_path / "b" / "c02.json", {"status": "failed", "segments": []})
    lines = [{"model": "a", "case_id": c, "judge": "j", "scores": {k: 4 for k in CRITERIA}}
             for c in ["c01", "c02"]]
    (tmp_path / "scores.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines), encoding="utf-8")

    table = summarize(tmp_path)
    assert "| a | 100% | 75% |" in table
    assert "| b | 50% | 100% |" in table
    assert "24.0" in table
    assert (tmp_path / "summary.md").exists() is False  # 파일 저장은 CLI 책임
