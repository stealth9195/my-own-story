from typing import Literal

from pydantic import BaseModel, Field

from app.story.schema import Segment


class Voice(BaseModel):
    # browser: 서버 TTS 한도가 부족해 처음부터 브라우저 TTS 로 읽는 이야기
    provider: Literal["gemini", "typecast", "browser"]
    model: str | None = None
    voice: str | None = None


class StoryKey(BaseModel):
    """이야기 하나를 가리키는 값. 서명에 함께 들어가므로 프론트가 바꾸면 서명이 깨진다."""
    id: str
    cards: list[str] = Field(min_length=3, max_length=5)
    choice_count: int = Field(ge=2, le=5)
    voice: Voice


class SignedSegment(BaseModel):
    segment: Segment
    sig: str
