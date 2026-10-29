"""사용 기록·생성 기록을 JSON 한 줄로 남긴다 (DB 없음 → Cloud Run 로그에서 모아 본다).
API 키·서명 비밀값은 넣지 않는다."""

import json
import logging

logger = logging.getLogger("story")


def log_event(kind: str, **fields) -> None:
    logger.info(json.dumps({"kind": kind, **fields}, ensure_ascii=False, default=str))
