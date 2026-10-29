import random
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


# v7: 도입·결말 3페이지, 중간 2~3페이지, 선택지 3개 (아이가 듣기에 짧게, 선택지 수를 일정하게)
INSTRUCTIONS_V7: dict[str, str] = {
    "intro": "도입부를 3페이지로 써. 선택지 3개 포함.",
    "middle": "아이의 선택을 반영해서 이야기를 2~3페이지 이어 써. 선택지 3개 포함.",
    "ending": (
        "아이의 선택을 반영해서 이야기를 3페이지로 따뜻하게 마무리해. "
        '갑자기 끊기지 않게. "choices"는 빈 배열.'
    ),
}

# v7: 5단계 플롯. 구간 수(선택 횟수 + 1)에 맞춰 단계를 나눠 준다
STAGES = ["발단", "전개", "위기", "절정", "결말"]
STAGE_GOALS = {
    "발단": "인물과 배경을 소개하고 작은 문제(사건의 실마리)를 보여줘",
    "전개": "문제가 본격적으로 드러나고 일이 얽혀",
    "위기": "뜻밖의 일로 문제가 더 어려워져",
    "절정": "문제가 가장 커진 순간, 주인공이 스스로 마음을 정하거나 용기를 내",
    "결말": "문제가 풀리고 따뜻하게 마무리돼",
}


def plot_stage(index: int, total: int) -> str:
    """구간 번호(0부터)를 5단계 플롯 이름으로. 중간 구간이 3개보다 적으면 단계를 합친다."""
    if index == 0:
        return "발단"
    if index == total - 1:
        return "결말"
    middle = ["전개", "위기", "절정"]
    m = total - 2
    if m >= 3:
        return middle[min((index - 1) * 3 // m, 2)]
    groups = [middle] if m == 1 else [middle[:1], middle[1:]]
    return "·".join(groups[index - 1])


# v8: 구간 끝맺음 예시. 코드가 정한 종류에서 3개를 무작위로 골라 보여준다 (한 형식으로 쏠리지 않게)
ENDING_EXAMPLES: dict[str, list[str]] = {
    "item": [
        "그때 눈앞에 나타난 것은 바로...",
        "손에 들고 있던 건...",
        "하늘에서 내려온 건...",
        "풀숲에서 쏙 나온 건...",
        "문을 똑똑 두드린 건...",
        "상자 안에 들어 있던 건...",
        "물속에서 퐁 떠오른 건...",
        "바람에 날아온 건...",
        "나무 위에서 내려다보던 건...",
        "멀리서 손을 흔드는 친구는...",
    ],
    "phrase": [
        "지름길로 향했는데...",
        "함께 여행을 가게 됐는데...",
        "그 집의 생김새는...",
        "문을 살짝 열어 보니...",
        "한 입 먹어 보니 맛이...",
        "갑자기 하늘이...",
        "강을 건너려고 하자...",
        "구름 위에 올라가 보니...",
        "편지를 펼쳐 보니...",
        "그 말을 들은 친구의 기분은...",
    ],
}
# 문장형 끝맺음 → 빈칸에 들어갈 답 예시. 답의 끝말을 다양하게 둬서 한 형태로 쏠리지 않게 한다
PHRASE_ANSWERS: dict[str, list[str]] = {
    "지름길로 향했는데...": ["길이 꼬불꼬불했어요", "커다란 강이 나왔어요", "길이 반짝반짝 빛났어요"],
    "함께 여행을 가게 됐는데...": ["둘 다 신이 났어요", "가방이 너무 무거웠어요", "비가 내리기 시작했어요"],
    "그 집의 생김새는...": ["과자로 만들어져 있었어요", "거꾸로 서 있었어요", "아주 커다랬어요!"],
    "문을 살짝 열어 보니...": ["노랫소리가 들렸어요", "방이 꽃으로 가득했어요", "고양이가 낮잠을 자고 있었어요"],
    "한 입 먹어 보니 맛이...": ["아주 달콤했어요", "너무 셨어요", "몸이 둥실 떠올랐어요"],
    "갑자기 하늘이...": ["무지개색으로 변했어요", "컴컴해졌어요", "별이 쏟아졌어요"],
    "강을 건너려고 하자...": ["징검다리가 나타났어요", "물이 너무 깊었어요", "물고기가 말을 걸었어요"],
    "구름 위에 올라가 보니...": ["폭신폭신했어요", "구름 마을이 있었어요", "바람이 세게 불었어요"],
    "편지를 펼쳐 보니...": ["그림이 그려져 있었어요", "글씨가 반짝였어요", "아무것도 없었어요"],
    "그 말을 들은 친구의 기분은...": ["날아갈 듯 기뻤어요", "조금 서운했어요", "깜짝 놀랐어요"],
}
KIND_NAMES = {"item": "물건형", "phrase": "문장형"}


@dataclass
class StoryContext:
    cards: list[str]
    history: list[Segment]
    chosen: list[str]
    total_segments: int | None = None  # v5부터 "전체 N구간 중 몇 번째"를 알려줄 때 사용


def choose_ending_kind(ctx: "StoryContext", segment_type: SegmentType,
                       rng: random.Random | None = None) -> str | None:
    """v8: 이번 구간을 물건형/문장형 중 무엇으로 끝낼지 코드가 정한다.
    결말은 없음, 결말 직전은 물건형(결말에 나올 주연을 분명히), 같은 종류 3번 연속 금지, 나머지는 무작위."""
    if segment_type == "ending":
        return None
    index = len(ctx.history)
    if ctx.total_segments and index == ctx.total_segments - 2:
        return "item"
    recent = [seg.choices[0].kind for seg in ctx.history[-2:] if seg.choices]
    if len(recent) == 2 and recent[0] == recent[1]:
        return "phrase" if recent[0] == "item" else "item"
    return (rng or random).choice(["item", "phrase"])


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


def chosen_item(ctx: StoryContext) -> str | None:
    """방금 고른 선택지가 물건형이면 그 id (문장형이면 None)"""
    last = _last_choice(ctx)
    return last.id if last and last.kind == "item" else None


def _last_choice(ctx: StoryContext):
    if not ctx.chosen or not ctx.history:
        return None
    return next((c for c in ctx.history[-1].choices if c.id == ctx.chosen[-1]), None)


def build_messages(
    ctx: StoryContext,
    segment_type: SegmentType,
    catalog: Catalog,
    version: str = "v1",
    ending_kind: str | None = None,
    rng: random.Random | None = None,
) -> list[dict[str, str]]:
    template = (REPO_ROOT / "prompts" / version / "system.md").read_text(encoding="utf-8")
    # JSON 예시의 중괄호 때문에 str.format 대신 replace 사용
    v = _version_number(version)
    # v8: 성격·상황은 장면에 쓰지 않으므로 장면용 목록에서 뺀다
    exclude = {"traits", "situations"} if v >= 8 else frozenset()
    system = template.replace("{catalog}", catalog.prompt_listing(exclude))

    parts = ["아이가 고른 카드: " + ", ".join(catalog.name_of(c) for c in ctx.cards)]
    if _version_number(version) >= 6:  # 처음 선택 단계별 역할을 알려준다
        roles = {"character": "주인공", "trait": "성격", "background": "배경", "situation": "배경",
                 "object": "사물"}
        parts[0] = "\n".join(f"{roles[catalog.kind_of(c)]}: {catalog.name_of(c)}" for c in ctx.cards)
    if ctx.history:
        story = "\n".join(p.text for seg in ctx.history for p in seg.pages)
        parts.append("지금까지의 이야기:\n" + story)
    last = _last_choice(ctx)
    if last and last.kind == "phrase" and v >= 8:
        parts.append(f"아이가 방금 고른 선택지: '{last.label}' (이번 구간 첫 문장에 이 말을 넣어서 이어 시작해)")
    elif last and last.kind == "phrase":
        parts.append(f"아이가 방금 고른 선택지: '{last.label}' (앞 구간 마지막 문장을 이 말로 이어서 시작해)")
    elif ctx.chosen:
        parts.append("아이가 방금 고른 선택지: " + catalog.name_of(ctx.chosen[-1]))
        if _version_number(version) >= 6:
            name = catalog.name_of(ctx.chosen[-1])
            parts.append(f"'{name}'를 이번 구간 첫 페이지에 꼭 등장시키고 이야기의 중심으로 써 "
                         f"(장면 정보에도 {ctx.chosen[-1]} 넣기). 결말이어도 마찬가지야")
    # v1은 비교 기준이라 그대로 두고, v2부터 선택지 이력을 알려준다
    if version != "v1":
        names = lambda ids: ", ".join(sorted(catalog.name_of(i) for i in ids))
        if v < 8:  # v8: 후보 목록 하나만 보낸다 (금지 목록은 코드가 검사)
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
    if _version_number(version) >= 7 and ctx.total_segments:
        stage = plot_stage(len(ctx.history), ctx.total_segments)
        goals = " / ".join(STAGE_GOALS[s] for s in stage.split("·"))
        parts.append(f"이번 구간은 이야기의 '{stage}' 단계야: {goals}")
    if v >= 8 and ending_kind:
        picked = (rng or random).sample(ENDING_EXAMPLES[ending_kind], 3)
        if ending_kind == "phrase":
            examples = " / ".join(f"'{e}' → " + ", ".join(PHRASE_ANSWERS[e]) for e in picked)
            parts.append(f"이번 구간은 문장형 선택지로 끝내 (kind \"phrase\"). "
                         f"마지막 문장 → 선택지 예: {examples}")
        else:
            parts.append(f"이번 구간은 물건형 선택지로 끝내 (kind \"item\"). "
                         f"마지막 문장 예: {' / '.join(picked)}")
    parts.append((INSTRUCTIONS_V7 if _version_number(version) >= 7 else INSTRUCTIONS)[segment_type])

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
