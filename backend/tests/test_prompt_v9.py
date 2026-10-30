"""v9: 중간 페이지가 '...'로 끊기지 않게 (2026-10-30 실제로 겪음: 2페이지가 '아기 용의 표정은...'으로 끝남)"""
import json

from app.catalog import load_catalog
from app.config import REPO_ROOT
from app.story.safety import load_banned_words
from app.story.validator import validate_segment
from conftest import segment_json

cat = load_catalog()
banned = load_banned_words()


def with_texts(*texts: str) -> str:
    data = json.loads(segment_json(pages=len(texts)))
    for page, text in zip(data["pages"], texts):
        page["text"] = text
    return json.dumps(data, ensure_ascii=False)


def check(raw: str):
    return validate_segment(raw, "middle", cat, banned, lenient=True)


def test_middle_page_ending_with_ellipsis_is_rejected():
    raw = with_texts("토끼가 바구니를 열었어요.", "바구니가 텅 비어 있어서 토끼의 표정은...", "토끼는 주변을 살폈어요.")
    r = check(raw)
    assert not r.ok and "cut_off" in r.errors  # 느슨한 검사에서도 거절 → 같이 쓴 다른 모델 글을 쓴다


def test_unicode_ellipsis_too():
    assert "cut_off" in check(with_texts("토끼가 웃었어요…", "토끼가 걸었어요.", "토끼가 쉬었어요.")).errors


def test_last_page_may_end_with_ellipsis():
    # 마지막 페이지는 다음 선택이 궁금해지게 끝내도 된다 (문장형 선택지의 빈칸 등)
    r = check(with_texts("토끼가 걸었어요.", "토끼가 쉬었어요.", "그때 숲속에서 들려온 소리는..."))
    assert r.ok


def test_v9_prompt_says_where_suspense_goes():
    text = (REPO_ROOT / "prompts" / "v9" / "system.md").read_text(encoding="utf-8")
    assert "마침표" in text and "맨 마지막 페이지" in text
