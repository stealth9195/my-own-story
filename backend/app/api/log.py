"""사용 기록·생성 기록을 JSON 한 줄로 남긴다 (DB 없음 → Render 로그에서 모아 본다).
API 키·서명 비밀값은 넣지 않는다. 그래도 오류 글에 섞여 들어오는 경우를 막으려고 등록한 비밀값은 끝 4자리만 남긴다.
겪은 사고(2026-10-31): 키 끝 줄바꿈 때문에 난 httpx 오류 글에 키가 그대로 들어가 Render 로그에 남았다."""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from app.api.limits import KST

logger = logging.getLogger("story")
_secrets: set[str] = set()


def register_secrets(*values: str) -> None:
    """로그에서 가릴 값. 너무 짧은 값은 평범한 글자까지 가릴 수 있어 넣지 않는다"""
    _secrets.update(v.strip() for v in values if v and len(v.strip()) >= 8)


def _mask(text: str) -> str:
    for s in _secrets:
        if s in text:
            text = text.replace(s, f"…{s[-4:]}")
    return text


def log_event(kind: str, **fields) -> None:
    logger.info(_mask(json.dumps({"kind": kind, **fields}, ensure_ascii=False, default=str)))


class DailyFileHandler(logging.Handler):
    """로컬 전용: logs/2026-10-31.log 처럼 KST 날짜별 파일에 '시각 내용' 한 줄씩 덧붙인다.
    콘솔 기록은 창을 닫으면 사라지고 Windows 콘솔에서는 한글이 깨져 보여서 만들었다.
    서버 오류(uvicorn.error)의 예외 내용도 들어오므로 여기서도 비밀값을 가린다."""

    def __init__(self, folder: Path, clock: Callable[[], datetime] = lambda: datetime.now(KST)):
        super().__init__(level=logging.INFO)
        self.folder = Path(folder)
        self._clock = clock

    def emit(self, record: logging.LogRecord) -> None:
        try:
            now = self._clock().astimezone(KST)
            line = _mask(f"{now:%H:%M:%S} {self.format(record)}")
            self.folder.mkdir(parents=True, exist_ok=True)
            with open(self.folder / f"{now:%Y-%m-%d}.log", "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            self.handleError(record)


def save_to_files(folder: Path) -> None:
    """이야기 기록(story)과 서버 오류(uvicorn.error)를 날짜별 파일에도 남긴다"""
    handler = DailyFileHandler(folder)
    for name in ("story", "uvicorn.error"):
        logging.getLogger(name).addHandler(handler)
