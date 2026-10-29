"""서버가 이야기를 저장하지 않으므로, 돌려준 구간에 서명을 붙여 두고
다음 요청에서 프론트가 보낸 지난 구간이 서버가 만든 그대로인지 확인한다 (자유 입력 차단)."""

import hashlib
import hmac
import json

from app.api.schemas import SignedSegment, StoryKey
from app.story.schema import Segment


class BadSignature(Exception):
    pass


def sign_segment(secret: str, story: StoryKey, index: int, segment: Segment) -> str:
    payload = json.dumps({"story": story.model_dump(mode="json"), "index": index,
                          "segment": segment.model_dump(mode="json")},
                         sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify_segment(secret: str, story: StoryKey, index: int, item: SignedSegment) -> Segment:
    if not hmac.compare_digest(sign_segment(secret, story, index, item.segment), item.sig):
        raise BadSignature(index)
    return item.segment


def verify_history(secret: str, story: StoryKey, history: list[SignedSegment]) -> list[Segment]:
    return [verify_segment(secret, story, index, item) for index, item in enumerate(history)]
