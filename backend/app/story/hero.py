"""결말 장면에는 처음 고른 주인공이 꼭 나오게 한다(사용자 요청 2026-10-31).
겪은 문제: 프롬프트(v9)·검사기 모두 주인공은 발단 첫 페이지에만 요구해, 결말 장면에서 주인공이 빠지는 이야기가 있었다.
LLM 을 다시 부르지 않고 서버가 서명 전에 장면에 넣는다(무료 한도·시간 그대로). 글은 고치지 않는다."""
from app.catalog import Catalog
from app.story.schema import SceneCharacter, Segment

MAX_SCENE_CHARACTERS = 3   # 프롬프트의 장면 규칙(characters 0~3개)과 같게
HERO_STATE = "happy"       # 결말은 따뜻하게 끝나므로


def hero_of(cards: list[str], catalog: Catalog) -> str | None:
    """처음 고른 카드 중 첫 캐릭터(주인공). 카드 순서는 주인공·성격·배경·사물"""
    return next((c for c in cards if c in catalog.ids("characters")), None)


def ensure_hero(segment: Segment, hero: str | None, catalog: Catalog) -> tuple[Segment, list[int]]:
    """결말 구간의 각 페이지 장면에 주인공이 없으면 맨 앞에 넣는다. 넣은 페이지 번호(로그용)를 함께 돌려준다.
    장면이 3명으로 꽉 차 있으면 마지막 한 명을 뺀다."""
    if segment.type != "ending" or hero is None:
        return segment, []
    state = HERO_STATE if HERO_STATE in catalog.ids("states") else catalog.default_state
    added: list[int] = []
    pages = []
    for i, p in enumerate(segment.pages):
        if any(c.id == hero for c in p.scene.characters):
            pages.append(p)
            continue
        others = p.scene.characters[:MAX_SCENE_CHARACTERS - 1]
        scene = p.scene.model_copy(update={"characters": [SceneCharacter(id=hero, state=state), *others]})
        pages.append(p.model_copy(update={"scene": scene}))
        added.append(i)
    return segment.model_copy(update={"pages": pages}), added
