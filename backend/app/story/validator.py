import json
import random
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
    # 실패 원인 확인용: 모델이 보낸 선택지(id 또는 문장)와 페이지 수
    sent_choices: list[str] = field(default_factory=list)
    page_count: int = 0
    filled: list[str] = field(default_factory=list)  # 선택지가 모자라 후보에서 채운 것
    warnings: list[str] = field(default_factory=list)  # 관대한 모드에서 통과시킨 규칙 위반


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


MAX_PHRASE_CHARS = 20
# 문장형 선택지는 빈칸을 채워 문장을 끝내는 답이라 '요', '다', 문장부호로 끝나야 한다 ('...', '~보니' 같은 미완성은 뺌)
SENTENCE_END = re.compile(r"(요|다)[!.?~]*$|[!?]$")
# 관대한 모드에서도 거절하는 오류: 읽을 수 없는 응답, 빈 본문, 한글 아님, 아이에게 부적절한 내용
HARD_ERRORS = {"json", "schema", "empty_text", "not_korean", "unsafe"}


def _clean_phrases(choices: list[Choice], banned: list[str], dropped: list[str],
                   forbidden: set[str]) -> list[Choice]:
    """문장형 선택지: 한글, 20자 이하, 금지어 없음, 이전에 나온 문장 아님, 중복 없음."""
    result: list[Choice] = []
    for c in choices:
        label = c.label.strip()
        if (not HANGUL.search(label) or len(label) > MAX_PHRASE_CHARS or label in forbidden
                or not SENTENCE_END.search(label)
                or find_banned(label, banned) or label in [r.label for r in result]):
            dropped.append(label)
            continue
        result.append(Choice(kind="phrase", id=f"phrase-{len(result) + 1}", label=label))
    return result[:MAX_CHOICES]


def _clean_choices(choices: list[Choice], catalog: Catalog, dropped: list[str],
                   forbidden: set[str]) -> list[Choice]:
    seen: set[str] = set()
    result = []
    for c in choices:
        if c.id not in catalog.choice_ids() or c.id in forbidden:
            dropped.append(c.id)
        elif c.id not in seen:
            seen.add(c.id)
            result.append(Choice(kind="item", id=c.id, label=catalog.name_of(c.id)))
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


def _check_intro_v8(pages: list[Page], cards: list[str], catalog: Catalog) -> list[str]:
    """v8 발단: 첫 페이지에 주인공, 발단 안에 사물, 장소 카드는 발단 안의 배경으로."""
    errors = []
    heroes = {c for c in cards if catalog.kind_of(c) == "character"}
    objects = {c for c in cards if catalog.kind_of(c) == "object"}
    places = {c for c in cards if catalog.kind_of(c) == "background"}
    if heroes and not heroes & {c.id for c in pages[0].scene.characters}:
        errors.append("hero_missing")
    shown = set().union(*(_page_ids(p) for p in pages))
    if not objects <= shown:
        errors.append("cards_missing")
    if places and not places & {p.scene.background for p in pages}:
        errors.append("background_mismatch")
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
    forbidden_phrases: set[str] = frozenset(),
    fill_pool: list[str] | None = None,
    lenient: bool = False,
    chosen_item: str | None = None,
    max_choices: int = MAX_CHOICES,
    page_range: tuple[int, int] | None = None,
    intro_v8: bool = False,
    expected_kind: str | None = None,
) -> ValidationResult:
    """forbidden_choices: 이미 나온 선택지(새 선택지에서 제거).
    forbidden_scene: 고르지 않은 선택지(장면에 나오면 실패)."""
    data = extract_json(raw)
    if data is None:
        return ValidationResult(ok=False, segment=None, errors=["json"])
    try:
        pages = [Page.model_validate(p) for p in data.get("pages", [])]
        choices = [Choice.model_validate(c) for c in data.get("choices") or []]
        sent_choices = [c.id or c.label for c in choices]
        sent_kinds = {c.kind for c in choices}
    except (ValidationError, TypeError, AttributeError):
        return ValidationResult(ok=False, segment=None, errors=["schema"])

    errors: list[str] = []
    dropped: list[str] = []
    filled: list[str] = []

    low, high = page_range or PAGE_RANGES[segment_type]
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
        kinds = {c.kind for c in choices}
        if len(kinds) > 1:
            errors.append("mixed_choices")
            if lenient:  # 섞였으면 물건형만 남긴다
                choices = [c for c in choices if c.kind == "item"]
        if choices and all(c.kind == "phrase" for c in choices):
            choices = _clean_phrases(choices, banned, dropped, set(forbidden_phrases))
            if lenient and len(choices) < MIN_CHOICES:  # 문장형이 모자라면 물건형 후보로 대신한다
                choices = []
        if (lenient or len(kinds) <= 1) and not (choices and choices[0].kind == "phrase"):
            choices = _clean_choices(choices, catalog, dropped, set(forbidden_choices) | in_scene)
            # 물건형은 에셋 목록에서 가져오는 것이라, 모델이 비우거나 지어내도 후보에서 채운다
            if fill_pool and len(choices) < MIN_CHOICES:
                used = {c.id for c in choices} | in_scene | set(forbidden_choices)
                spare = [i for i in fill_pool if i not in used and i in catalog.choice_ids()]
                random.shuffle(spare)
                for i in spare[:max_choices - len(choices)]:
                    choices.append(Choice(kind="item", id=i, label=catalog.name_of(i)))
                    filled.append(i)
        choices = choices[:max_choices]
        if len(choices) < MIN_CHOICES and (lenient or "mixed_choices" not in errors):
            errors.append("choices")

    scene_ids = {c.id for p in pages for c in p.scene.characters} | {
        o for p in pages for o in p.scene.objects}
    if scene_ids & forbidden_scene:
        errors.append("unchosen_used")
    # 아이가 방금 고른 물건형 선택지는 이번 구간 장면에 꼭 나와야 한다
    if chosen_item and pages and chosen_item not in scene_ids:
        errors.append("chosen_missing")
    # 느낌·행동 카드는 장면 id가 아니라서 도입 장면 검사에서 뺀다
    item_cards = {c for c in (cards or []) if c in catalog.choice_ids()}
    if intro_v8:
        if segment_type == "intro" and cards and pages:
            errors += _check_intro_v8(pages, cards, catalog)
    else:
        if segment_type == "intro" and item_cards and pages:
            errors += _check_intro_cards(pages, item_cards, catalog)
        # 배경(장소) 카드를 골랐으면 첫 장면이 그 장소여야 한다
        places = [c for c in (cards or []) if c in catalog.ids("backgrounds")]
        if segment_type == "intro" and places and pages and pages[0].scene.background not in places:
            errors.append("background_mismatch")
    # v8: 코드가 정한 선택지 종류(물건형/문장형)와 다르게 보냈으면
    if expected_kind and sent_kinds and sent_kinds != {expected_kind}:
        errors.append("wrong_kind")

    texts = [p.text for p in pages] + [c.label for c in choices]
    if any(find_banned(t, banned) for t in texts):
        errors.append("unsafe")

    errors = list(dict.fromkeys(errors))
    warnings: list[str] = []
    if lenient:  # 형식·안전 문제만 거절하고 나머지는 경고로 남긴다
        warnings = [e for e in errors if e not in HARD_ERRORS]
        errors = [e for e in errors if e in HARD_ERRORS]
    segment = Segment(type=segment_type, pages=pages, choices=choices)
    return ValidationResult(ok=not errors, segment=segment, errors=errors, dropped=dropped,
                            sent_choices=sent_choices, page_count=len(pages), filled=filled,
                            warnings=warnings)
