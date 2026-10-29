"""처음 선택 후보와 구간 순서. 실험 서버와 서비스 API 가 같이 쓴다."""

import random

from app.catalog import Catalog


def segment_types(choice_count: int) -> list[str]:
    return ["intro"] + ["middle"] * (choice_count - 1) + ["ending"]


def start_options(catalog: Catalog, rng: random.Random | None = None) -> dict:
    """처음 선택 4단계 후보를 전체 목록에서 무작위로 뽑는다."""
    rng = rng or random

    def pick(ids, n):
        return [{"id": i, "name": catalog.name_of(i), "kind": catalog.kind_of(i),
                 "emoji": catalog.emoji_of(i)} for i in rng.sample(sorted(ids), n)]
    return {
        "heroes": pick(catalog.ids("characters"), 5),
        "traits": pick(catalog.ids("traits"), 4),
        "backgrounds": pick(catalog.ids("backgrounds") | catalog.ids("situations"), 4),
        "objects": pick(catalog.ids("objects"), 4),
    }


def valid_cards(catalog: Catalog, cards: list[str]) -> bool:
    """목록에 있는 카드이고, 주인공(캐릭터)이 1장 이상"""
    return set(cards) <= catalog.start_ids() and any(catalog.kind_of(c) == "character" for c in cards)
