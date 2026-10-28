import json
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.catalog import Catalog
from app.config import PAGE_RANGES
from app.story.safety import find_banned
from app.story.schema import Choice, Page, Scene, SceneCharacter, Segment, SegmentType

HANGUL = re.compile(r"[가-힣]")
MAX_CHOICES = 4
MIN_CHOICES = 3


@dataclass
class ValidationResult:
    ok: bool
    segment: Segment | None
    errors: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


def extract_json(raw: str) -> dict | None:
    """응답에서 첫 '{'부터 마지막 '}'까지 꺼내 파싱. 코드 블록·설명 문장 대응."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _clean_scene(scene: Scene, catalog: Catalog, dropped: list[str]) -> Scene:
    if scene.background not in catalog.ids("backgrounds"):
        dropped.append(scene.background)
        scene.background = catalog.default_background
    if scene.time not in catalog.ids("times"):
        dropped.append(scene.time)
        scene.time = "day"
    characters = []
    for c in scene.characters:
        if c.id not in catalog.ids("characters"):
            dropped.append(c.id)
            continue
        if c.state not in catalog.ids("states"):
            dropped.append(c.state)
            c = SceneCharacter(id=c.id, state=catalog.default_state)
        characters.append(c)
    scene.characters = characters
    objects = []
    for o in scene.objects:
        if o in catalog.ids("objects"):
            objects.append(o)
        else:
            dropped.append(o)
    scene.objects = objects
    return scene


def _clean_choices(choices: list[Choice], catalog: Catalog, dropped: list[str]) -> list[Choice]:
    seen: set[str] = set()
    result = []
    for c in choices:
        if c.id not in catalog.choice_ids():
            dropped.append(c.id)
        elif c.id not in seen:
            seen.add(c.id)
            result.append(c)
    return result[:MAX_CHOICES]


def validate_segment(
    raw: str,
    segment_type: SegmentType,
    catalog: Catalog,
    banned: list[str],
    max_page_chars: int = 250,
) -> ValidationResult:
    data = extract_json(raw)
    if data is None:
        return ValidationResult(ok=False, segment=None, errors=["json"])
    try:
        pages = [Page.model_validate(p) for p in data.get("pages", [])]
        choices = [Choice.model_validate(c) for c in data.get("choices") or []]
    except (ValidationError, TypeError):
        return ValidationResult(ok=False, segment=None, errors=["json"])

    errors: list[str] = []
    dropped: list[str] = []

    low, high = PAGE_RANGES[segment_type]
    if not low <= len(pages) <= high:
        errors.append("page_count")

    for p in pages:
        text = p.text.strip()
        if not text:
            errors.append("empty_text")
        elif not HANGUL.search(text):
            errors.append("not_korean")
        elif len(text) > max_page_chars:
            errors.append("too_long")
        p.text = text
        p.scene = _clean_scene(p.scene, catalog, dropped)
        if p.mood not in catalog.ids("moods"):
            dropped.append(p.mood)
            p.mood = catalog.default_mood
        if p.sfx is not None and p.sfx not in catalog.ids("sfx"):
            dropped.append(p.sfx)
            p.sfx = None

    if segment_type == "ending":
        choices = []
    else:
        choices = _clean_choices(choices, catalog, dropped)
        if len(choices) < MIN_CHOICES:
            errors.append("choices")

    texts = [p.text for p in pages] + [c.label for c in choices]
    if any(find_banned(t, banned) for t in texts):
        errors.append("unsafe")

    errors = list(dict.fromkeys(errors))
    segment = Segment(type=segment_type, pages=pages, choices=choices)
    return ValidationResult(ok=not errors, segment=segment, errors=errors, dropped=dropped)
