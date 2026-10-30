"""사용 기록·생성 기록을 JSON 한 줄로 남긴다 (DB 없음 → Render 로그에서 모아 본다).
API 키·서명 비밀값은 넣지 않는다. 그래도 오류 글에 섞여 들어오는 경우를 막으려고 등록한 비밀값은 끝 4자리만 남긴다.
겪은 사고(2026-10-31): 키 끝 줄바꿈 때문에 난 httpx 오류 글에 키가 그대로 들어가 Render 로그에 남았다."""

import json
import logging

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
