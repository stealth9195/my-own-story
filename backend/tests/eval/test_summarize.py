import json

from eval.judge import CRITERIA
from eval.summarize import summarize


def seg(ok_first=True, latency=1000):
    attempts = [{"model": "x", "ok": ok_first, "errors": [], "latency_ms": latency}]
    if not ok_first:
        attempts.append({"model": "x", "ok": True, "errors": [], "latency_ms": latency})
    return {"type": "middle", "pages": [], "choices": [], "chosen": None,
            "attempts": attempts, "latency_ms": latency * len(attempts)}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_summarize_table(tmp_path):
    # 모델 a: 완료 2편 (구간 4개 중 1개만 첫 시도 실패), 모델 b: 완료 1 + 실패 1
    write(tmp_path / "a" / "c01.json", json.dumps({"status": "done", "segments": [seg(), seg(False)]}))
    write(tmp_path / "a" / "c02.json", json.dumps({"status": "done", "segments": [seg(), seg()]}))
    write(tmp_path / "b" / "c01.json", json.dumps({"status": "done", "segments": [seg()]}))
    write(tmp_path / "b" / "c02.json", json.dumps({"status": "failed", "segments": []}))
    write(tmp_path / "export" / "mapping.csv",
          "file,model,case_id\ns01,a,c01\ns02,a,c02\ns03,b,c01\n")
    full = ",".join(str(v) for v in CRITERIA.values())
    half = ",".join(str(v // 2) for v in CRITERIA.values())
    header = "file," + ",".join(CRITERIA)
    write(tmp_path / "export" / "scores" / "chatgpt.csv", f"{header}\ns01,{full}\ns02,{full}\n")
    write(tmp_path / "export" / "scores" / "claude.csv", f"{header}\ns01,{half}\ns02,{half}\n")

    table = summarize(tmp_path)
    assert "| a | 100% | 75% |" in table
    assert "| b | 50% | 100% |" in table
    a_row = next(line for line in table.splitlines() if line.startswith("| a |"))
    expected_total = (100 + sum(v // 2 for v in CRITERIA.values())) / 2
    assert a_row.endswith(f"| {expected_total:.1f} |")
    assert "export" not in table
