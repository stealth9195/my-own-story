from dataclasses import dataclass

from app.catalog import Catalog
from app.config import REPO_ROOT
from app.story.schema import Segment, SegmentType

INSTRUCTIONS: dict[str, str] = {
    "intro": "도입부를 3페이지로 써. 선택지 3~4개 포함.",
    "middle": "아이의 선택을 반영해서 이야기를 3~4페이지 이어 써. 선택지 3~4개 포함.",
    "ending": (
        "아이의 선택을 반영해서 이야기를 4~5페이지로 따뜻하게 마무리해. "
        '갑자기 끊기지 않게. "choices"는 빈 배열.'
    ),
}


@dataclass
class StoryContext:
    cards: list[str]
    history: list[Segment]
    chosen: list[str]
    total_segments: int | None = None  # v5부터 "전체 N구간 중 몇 번째"를 알려줄 때 사용


def _version_number(version: str) -> int:
    return int(version.lstrip("v")) if version.lstrip("v").isdigit() else 0


def forbidden_choices(ctx: StoryContext) -> set[str]:
    """처음 고른 카드, 지금까지 제시된 선택지, 이야기에 이미 등장한 캐릭터·사물.
    새 선택지로 다시 쓰지 않는다."""
    offered = _offered_items(ctx)
    in_scene = {c.id for seg in ctx.history for p in seg.pages for c in p.scene.characters}
    in_scene |= {o for seg in ctx.history for p in seg.pages for o in p.scene.objects}
    return set(ctx.cards) | offered | in_scene


def unchosen_ids(ctx: StoryContext) -> set[str]:
    """제시됐지만 고르지 않은 선택지. 처음 고른 카드는 등장해도 되므로 제외."""
    return _offered_items(ctx) - set(ctx.chosen) - set(ctx.cards)


def _offered_items(ctx: StoryContext) -> set[str]:
    return {c.id for seg in ctx.history for c in seg.choices if c.kind == "item"}


def allowed_choices(ctx: StoryContext, catalog: Catalog) -> list[str]:
    """물건형 선택지 후보: 에셋 목록의 캐릭터·사물 중 카드·이미 나온 것·이미 등장한 것을 뺀 나머지."""
    return sorted(catalog.choice_ids() - forbidden_choices(ctx))


def offered_phrases(ctx: StoryContext) -> set[str]:
    """지금까지 나온 문장형 선택지. 다시 내지 않는다."""
    return {c.label for seg in ctx.history for c in seg.choices if c.kind == "phrase"}


def _last_choice(ctx: StoryContext):
    if not ctx.chosen or not ctx.history:
        return None
    return next((c for c in ctx.history[-1].choices if c.id == ctx.chosen[-1]), None)


def build_messages(
    ctx: StoryContext,
    segment_type: SegmentType,
    catalog: Catalog,
    version: str = "v1",
) -> list[dict[str, str]]:
    template = (REPO_ROOT / "prompts" / version / "system.md").read_text(encoding="utf-8")
    # JSON 예시의 중괄호 때문에 str.format 대신 replace 사용
    system = template.replace("{catalog}", catalog.prompt_listing())

    parts = ["아이가 고른 카드: " + ", ".join(catalog.name_of(c) for c in ctx.cards)]
    if _version_number(version) >= 6:  # 처음 선택 단계별 역할을 알려준다
        roles = {"character": "주인공", "trait": "성격", "background": "배경", "situation": "배경",
                 "object": "사물"}
        parts[0] = "\n".join(f"{roles[catalog.kind_of(c)]}: {catalog.name_of(c)}" for c in ctx.cards)
    if ctx.history:
        story = "\n".join(p.text for seg in ctx.history for p in seg.pages)
        parts.append("지금까지의 이야기:\n" + story)
    last = _last_choice(ctx)
    if last and last.kind == "phrase":
        parts.append(f"아이가 방금 고른 선택지: '{last.label}' (앞 구간 마지막 문장을 이 말로 이어서 시작해)")
    elif ctx.chosen:
        parts.append("아이가 방금 고른 선택지: " + catalog.name_of(ctx.chosen[-1]))
    # v1은 비교 기준이라 그대로 두고, v2부터 선택지 이력을 알려준다
    if version != "v1":
        names = lambda ids: ", ".join(sorted(catalog.name_of(i) for i in ids))
        parts.append("이미 나온 선택지 (새 선택지로 쓰지 마): " + names(forbidden_choices(ctx)))
        if unchosen_ids(ctx):
            parts.append("고르지 않은 선택지 (등장시키지 마): " + names(unchosen_ids(ctx)))
        if _version_number(version) >= 6:
            pool = ", ".join(f"{i}({catalog.name_of(i)})" for i in allowed_choices(ctx, catalog))
            parts.append("선택지 후보 (물건형은 반드시 이 중에서만 골라): " + pool)
        if _version_number(version) >= 6 and offered_phrases(ctx):
            parts.append("이미 나온 문장 선택지 (다시 쓰지 마): " + " / ".join(sorted(offered_phrases(ctx))))
    if _version_number(version) >= 5 and ctx.total_segments:
        parts.append(f"지금은 전체 {ctx.total_segments}구간 중 {len(ctx.history) + 1}번째 구간이야.")
    parts.append(INSTRUCTIONS[segment_type])

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
