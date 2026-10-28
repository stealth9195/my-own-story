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
    if ctx.history:
        story = "\n".join(p.text for seg in ctx.history for p in seg.pages)
        parts.append("지금까지의 이야기:\n" + story)
    if ctx.chosen:
        parts.append("아이가 방금 고른 선택지: " + catalog.name_of(ctx.chosen[-1]))
    parts.append(INSTRUCTIONS[segment_type])

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
