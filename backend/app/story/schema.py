from typing import Literal

from pydantic import BaseModel, field_validator

SegmentType = Literal["intro", "middle", "ending"]

# 아래 before 검증기들: 무료 모델이 빈 값을 null로 보내는 경우 기본값으로 바꾼다.


class SceneCharacter(BaseModel):
    id: str
    state: str = "idle"

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, v):
        return "idle" if v is None else v


class Scene(BaseModel):
    background: str
    time: str = "day"
    characters: list[SceneCharacter] = []
    objects: list[str] = []

    @field_validator("time", mode="before")
    @classmethod
    def _time(cls, v):
        return "day" if v is None else v

    @field_validator("characters", "objects", mode="before")
    @classmethod
    def _lists(cls, v):
        return [] if v is None else v


class Page(BaseModel):
    text: str
    scene: Scene
    mood: str = "calm"
    sfx: str | None = None

    @field_validator("mood", mode="before")
    @classmethod
    def _mood(cls, v):
        return "calm" if v is None else v


class Choice(BaseModel):
    # item: 캐릭터·사물(그림 있음, id는 카탈로그 값) / phrase: 묘사·행동 문장(그림 없음, id는 검증기가 붙임)
    kind: Literal["item", "phrase"] = "item"
    id: str = ""
    label: str


class Segment(BaseModel):
    type: SegmentType
    pages: list[Page]
    choices: list[Choice] = []
