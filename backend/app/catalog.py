import json
from pathlib import Path

from pydantic import BaseModel

from app.config import REPO_ROOT

KINDS = ["backgrounds", "times", "characters", "objects", "traits", "situations", "states", "moods", "sfx"]
# traits: 시작 선택 '성격'(용감한 등), situations: 시작 선택 '배경' 중 상황(비 오는 날 등).
# 둘 다 그림 대신 이모지를 쓰고 장면 id가 아니다


class Asset(BaseModel):
    id: str
    name: str
    tags: list[str] = []
    card: bool = False
    emoji: str | None = None


class Bgm(BaseModel):
    id: str
    name: str
    mood: str


class Catalog(BaseModel):
    version: int
    default_background: str
    backgrounds: list[Asset]
    times: list[Asset]
    characters: list[Asset]
    objects: list[Asset]
    traits: list[Asset] = []
    situations: list[Asset] = []
    states: list[Asset]
    moods: list[Asset]
    sfx: list[Asset]
    bgm: list[Bgm]

    default_state: str = "idle"
    default_mood: str = "calm"

    def ids(self, kind: str) -> set[str]:
        return {a.id for a in getattr(self, kind)}

    def choice_ids(self) -> set[str]:
        return self.ids("characters") | self.ids("objects")

    def card_ids(self) -> list[str]:
        return [a.id for a in self.characters + self.objects + self.traits if a.card]

    def kind_of(self, asset_id: str) -> str:
        """시작 선택 종류: character / object / trait / background / situation"""
        for kind, items in (("character", self.characters), ("object", self.objects),
                            ("trait", self.traits), ("background", self.backgrounds),
                            ("situation", self.situations)):
            if any(a.id == asset_id for a in items):
                return kind
        raise KeyError(asset_id)

    def emoji_of(self, asset_id: str) -> str | None:
        return next((a.emoji for a in self.traits + self.situations if a.id == asset_id), None)

    def start_ids(self) -> set[str]:
        """처음 선택에 쓸 수 있는 모든 id (주인공·성격·배경·사물)"""
        return (self.ids("characters") | self.ids("traits") | self.ids("backgrounds")
                | self.ids("situations") | self.ids("objects"))

    def name_of(self, asset_id: str) -> str:
        for kind in KINDS:
            for a in getattr(self, kind):
                if a.id == asset_id:
                    return a.name
        raise KeyError(asset_id)

    def prompt_listing(self, exclude: set[str] = frozenset()) -> str:
        lines = []
        for kind in (k for k in KINDS if k not in exclude):
            items = ", ".join(f"{a.id}({a.name})" for a in getattr(self, kind))
            lines.append(f"{kind}: {items}")
        return "\n".join(lines)


def load_catalog(path: Path | None = None) -> Catalog:
    path = path or REPO_ROOT / "shared" / "catalog.json"
    catalog = Catalog.model_validate(json.loads(path.read_text(encoding="utf-8")))
    all_ids = [a.id for kind in KINDS for a in getattr(catalog, kind)]
    duplicates = {i for i in all_ids if all_ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"중복 ID: {sorted(duplicates)}")
    return catalog
