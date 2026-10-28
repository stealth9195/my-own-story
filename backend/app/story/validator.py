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


FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json(raw: str) -> dict | None:
    """응답에서 JSON 객체를 꺼낸다. 코드 블록 우선, 없으면 '{' 위치마다 파싱 시도.
    앞뒤 설명 문장에 중괄호가 섞여 있어도 처리한다."""
    fenced = FENCE.search(raw)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    decoder = json.JSONDecoder()
    pos = raw.find("{")
    while pos != -1:
        try:
            data, _ = decoder.raw_decode(raw, pos)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        pos = raw.find("{", pos + 1)
    return None


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


def _clean_choices(choices: list[Choice], catalog: Catalog, dropped: list[str],
                   forbidden: set[str]) -> list[Choice]:
    seen: set[str] = set()
    result = []
    for c in choices:
        if c.id not in catalog.choice_ids() or c.id in forbidden:
            dropped.append(c.id)
        elif c.id not in seen:
            seen.add(c.id)
            result.append(c)
    return result[:MAX_CHOICES]


def _page_ids(page: Page) -> set[str]:
    return {c.id for c in page.scene.characters} | set(page.scene.objects)


def _check_intro_cards(pages: list[Page], cards: set[str], catalog: Catalog) -> list[str]:
    """도입: 첫 페이지에 카드 2개 이상, 도입 안에 카드 모두 등장, 첫 페이지 캐릭터는 고른 카드만."""
    errors = []
    first = _page_ids(pages[0])
    shown = set().union(*(_page_ids(p) for p in pages))
    if len(first & cards) < min(2, len(cards)) or not cards <= shown:
        errors.append("cards_missing")
    if {c.id for c in pages[0].scene.characters} - cards:
        errors.append("wrong_hero")
    return errors


def validate_segment(
    raw: str,
    segment_type: SegmentType,
    catalog: Catalog,
    banned: list[str],
    max_page_chars: int = 250,
    forbidden_choices: set[str] = frozenset(),
    forbidden_scene: set[str] = frozenset(),
    cards: list[str] | None = None,
) -> ValidationResult:
    """forbidden_choices: 이미 나온 선택지(새 선택지에서 제거).
    forbidden_scene: 고르지 않은 선택지(장면에 나오면 실패)."""
    data = extract_json(raw)
    if data is None:
        return ValidationResult(ok=False, segment=None, errors=["json"])
    try:
        pages = [Page.model_validate(p) for p in data.get("pages", [])]
        choices = [Choice.model_validate(c) for c in data.get("choices") or []]
    except (ValidationError, TypeError, AttributeError):
        return ValidationResult(ok=False, segment=None, errors=["schema"])

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
        # 같은 구간 장면에 이미 나온 것도 선택지로 쓰지 않는다
        in_scene = {c.id for p in pages for c in p.scene.characters} | {
            o for p in pages for o in p.scene.objects}
        choices = _clean_choices(choices, catalog, dropped, set(forbidden_choices) | in_scene)
        if len(choices) < MIN_CHOICES:
            errors.append("choices")

    scene_ids = {c.id for p in pages for c in p.scene.characters} | {
        o for p in pages for o in p.scene.objects}
    if scene_ids & forbidden_scene:
        errors.append("unchosen_used")
    if segment_type == "intro" and cards and pages:
        errors += _check_intro_cards(pages, set(cards), catalog)

    texts = [p.text for p in pages] + [c.label for c in choices]
    if any(find_banned(t, banned) for t in texts):
        errors.append("unsafe")

    errors = list(dict.fromkeys(errors))
    segment = Segment(type=segment_type, pages=pages, choices=choices)
    return ValidationResult(ok=not errors, segment=segment, errors=errors, dropped=dropped)
