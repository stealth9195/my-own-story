import json
from pathlib import Path

from pydantic import BaseModel

from app.config import REPO_ROOT

KINDS = ["backgrounds", "times", "characters", "objects", "states", "moods", "sfx"]


class Asset(BaseModel):
    id: str
    name: str
    tags: list[str] = []
    card: bool = False


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
        return [a.id for a in self.characters + self.objects if a.card]

    def name_of(self, asset_id: str) -> str:
        for kind in KINDS:
            for a in getattr(self, kind):
                if a.id == asset_id:
                    return a.name
        raise KeyError(asset_id)

    def prompt_listing(self) -> str:
        lines = []
        for kind in KINDS:
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
