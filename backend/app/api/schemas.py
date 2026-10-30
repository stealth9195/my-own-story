from typing import Literal

from pydantic import BaseModel, Field

from app.story.schema import Segment


class Voice(BaseModel):
    # browser: 서버 TTS 한도가 부족해 처음부터 브라우저 TTS 로 읽는 이야기
    provider: Literal["gemini", "typecast", "elevenlabs", "browser"]
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


class StartRequest(BaseModel):
    anon_id: str = Field(min_length=1, max_length=64)
    cards: list[str] = Field(min_length=3, max_length=5)
    choice_count: int = Field(default=4, ge=2, le=5)
    # 설정에서 고른 이야기 목소리: Gemini 이름(Kore 등) 또는 시연용 번호(eleven1). 모르는 값·없음은 무작위 Gemini
    voice: str | None = Field(default=None, max_length=20)


class NextRequest(BaseModel):
    """지난 구간 전체(서명 포함)와 지금까지 고른 선택지. 서버는 이야기를 저장하지 않는다."""
    anon_id: str = Field(min_length=1, max_length=64)
    story: StoryKey
    history: list[SignedSegment] = Field(min_length=1)
    chosen: list[str]


class SpeakRequest(BaseModel):
    """안내·질문·선택지처럼 짧은 글 (이야기 본문은 /api/tts)"""
    text: str = Field(min_length=1, max_length=200)
    voice: Literal["female", "male"] = "female"


class TTSRequest(BaseModel):
    """서버가 만든 구간만 읽는다 (서명 확인)."""
    story: StoryKey
    index: int = Field(ge=0)
    segment: SignedSegment


EventType = Literal["card_select", "choice_time", "drop_off", "complete", "replay", "mute", "error", "voice_failed"]


class EventRequest(BaseModel):
    anon_id: str = Field(min_length=1, max_length=64)
    story_id: str | None = Field(default=None, max_length=64)
    type: EventType
    payload: dict = {}


class SegmentResponse(BaseModel):
    story: StoryKey
    index: int
    segment: SignedSegment
    done: bool
