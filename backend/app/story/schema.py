from typing import Literal

from pydantic import BaseModel

SegmentType = Literal["intro", "middle", "ending"]


class SceneCharacter(BaseModel):
    id: str
    state: str = "idle"


class Scene(BaseModel):
    background: str
    time: str = "day"
    characters: list[SceneCharacter] = []
    objects: list[str] = []


class Page(BaseModel):
    text: str
    scene: Scene
    mood: str = "calm"
    sfx: str | None = None


class Choice(BaseModel):
    id: str
    label: str


class Segment(BaseModel):
    type: SegmentType
    pages: list[Page]
    choices: list[Choice] = []
