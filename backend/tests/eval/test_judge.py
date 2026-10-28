import pytest

from eval.judge import CRITERIA, parse_scores_csv, story_to_text

STORY = {
    "card_names": ["토끼", "장미"],
    "segments": [
        {"type": "intro", "pages": [{"text": "토끼가 숲에 갔어요."}],
         "choices": [{"id": "dragon", "label": "아기 용"}, {"id": "rose", "label": "장미"}],
         "chosen": "dragon"},
        {"type": "ending", "pages": [{"text": "모두 행복했어요."}], "choices": [], "chosen": None},
    ],
}
HEADER = "file," + ",".join(CRITERIA)


def test_criteria_total_is_100():
    assert sum(CRITERIA.values()) == 100


def test_story_to_text_contains_cards_pages_and_chosen():
    text = story_to_text(STORY)
    assert "아이가 고른 카드: 토끼, 장미" in text
    assert "토끼가 숲에 갔어요." in text and "모두 행복했어요." in text
    assert "고른 선택지: 아기 용" in text


def test_parse_scores_csv_valid(tmp_path):
    row = ",".join(str(v) for v in CRITERIA.values())
    p = tmp_path / "chatgpt.csv"
    p.write_text(f"{HEADER}\ns01,{row}\n", encoding="utf-8")
    rows = parse_scores_csv(p)
    assert rows == [{"file": "s01", "judge": "chatgpt", "scores": dict(CRITERIA)}]


def test_parse_scores_csv_ignores_extra_text_and_total_column(tmp_path):
    row = ",".join(str(v) for v in CRITERIA.values())
    p = tmp_path / "gemini.csv"
    p.write_text(f"```csv\n{HEADER},total\ns01.md,{row},100\n```\n", encoding="utf-8")
    assert parse_scores_csv(p)[0]["file"] == "s01"


def test_parse_scores_csv_over_max_raises(tmp_path):
    first = next(iter(CRITERIA))
    over = {k: (v + 1 if k == first else v) for k, v in CRITERIA.items()}
    p = tmp_path / "claude.csv"
    p.write_text(f"{HEADER}\ns01,{','.join(str(v) for v in over.values())}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_scores_csv(p)


def test_parse_scores_csv_missing_column_raises(tmp_path):
    p = tmp_path / "claude.csv"
    p.write_text("file,vocabulary\ns01,10\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_scores_csv(p)
