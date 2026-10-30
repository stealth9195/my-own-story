"""LLM 글의 '더듬기' 오타를 규칙으로 고친다. 맞춤법 검사기·LLM 교정은 쓰지 않는다(시간·무료 한도, 사용자 결정 2026-10-30).
겪은 오타: '꼬 꼭 안았어요' — 받침 없는 한 글자 뒤에, 그 글자에 받침만 붙은 글자로 시작하는 말이 이어짐.
'찾으려'(→ 찾으러) 같은 어미 오타는 규칙으로 구분할 수 없어 그대로 둔다."""
import re

from app.story.schema import Segment

HANGUL_START = 0xAC00
# 받침 없는 한 글자로 된 진짜 낱말: '이 일', '새 생일', '해 햇살' 처럼 쓰이므로 지우지 않는다
REAL_WORDS = set("이그저요새두세네다또더너나내제누뭐수해배코귀소개차마아어오와우예왜비피쥐게보하매키시지기도고모무사자파바가거여처")
# 앞이 글자가 아닌 곳(문장 처음·띄어쓰기·따옴표)에서 시작하는 한 글자 + 띄어쓰기 + 다음 글자
STUTTER = re.compile(r"(?<![가-힣])([가-힣]) (?=([가-힣]))")


def _base(ch: str) -> int:
    return (ord(ch) - HANGUL_START) // 28   # 첫소리+가운뎃소리


def _no_final(ch: str) -> bool:
    return (ord(ch) - HANGUL_START) % 28 == 0


def _is_stutter(first: str, nxt: str) -> bool:
    return (first not in REAL_WORDS and _no_final(first) and not _no_final(nxt)
            and _base(first) == _base(nxt))


def fix_stutter(text: str) -> tuple[str, list[str]]:
    """고친 글과 고친 곳 목록('꼬 꼭')을 돌려준다"""
    fixes: list[str] = []

    def drop(m: re.Match) -> str:
        if _is_stutter(m.group(1), m.group(2)):
            fixes.append(f"{m.group(1)} {m.group(2)}")
            return ""
        return m.group(0)
    return STUTTER.sub(drop, text), fixes


def tidy_segment(segment: Segment) -> tuple[Segment, list[str]]:
    fixes: list[str] = []
    pages = []
    for p in segment.pages:
        text, found = fix_stutter(p.text)
        fixes += found
        pages.append(p.model_copy(update={"text": text}))
    return segment.model_copy(update={"pages": pages}), fixes
