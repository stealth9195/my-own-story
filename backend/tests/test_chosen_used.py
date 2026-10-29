"""아이가 고른 물건형 선택지는 다음 구간(결말 포함) 장면에 꼭 나와야 한다.
관대한 모드에서도 고른 것이 빠지거나 안 고른 것이 나오면 1번은 다시 생성한다."""
import json

from app.catalog import load_catalog
from app.story.generator import generate_segment
from app.story.prompt import StoryContext, build_messages
from app.story.safety import load_banned_words
from app.story.schema import Choice, Page, Scene, Segment
from app.story.validator import validate_segment
from conftest import FakeLLM, segment_json

cat = load_catalog()
banned = load_banned_words()
CARDS = ["rabbit", "rose", "star"]


def prev_segment():
    page = Page(text="그때 눈앞에 나타난 것은 바로...", scene=Scene(background="forest"))
    return Segment(type="middle", pages=[page],
                   choices=[Choice(id=i, label=cat.name_of(i)) for i in ("hedgehog", "squirrel", "moon")])


CTX = StoryContext(cards=CARDS, history=[prev_segment()], chosen=["hedgehog"], total_segments=3)


def ending(objects=(), characters=("rabbit",)):
    data = json.loads(segment_json(pages=4, choices=()))
    for p in data["pages"]:
        p["scene"]["characters"] = [{"id": c, "state": "happy"} for c in characters]
        p["scene"]["objects"] = list(objects)
    return json.dumps(data, ensure_ascii=False)


def test_chosen_missing_is_error():
    r = validate_segment(ending(), "ending", cat, banned, chosen_item="hedgehog")
    assert "chosen_missing" in r.errors
    ok = validate_segment(ending(characters=("rabbit", "hedgehog")), "ending", cat, banned, chosen_item="hedgehog")
    assert "chosen_missing" not in ok.errors


def test_v6_message_requires_chosen_on_first_page():
    user = build_messages(CTX, "ending", cat, version="v6")[1]["content"]
    assert "고슴도치" in user and "첫 페이지" in user


def test_lenient_retries_once_when_chosen_missing():
    llm = FakeLLM("p", [ending(characters=("rabbit", "squirrel")), ending(characters=("rabbit", "hedgehog"))])
    r = generate_segment(CTX, "ending", primary=llm, secondary=None, catalog=cat, banned=banned,
                         version="v6", lenient=True)
    assert llm.calls == 2
    assert "hedgehog" in {c.id for p in r.segment.pages for c in p.scene.characters}


def test_lenient_accepts_second_try_even_if_still_missing():
    llm = FakeLLM("p", [ending(), ending()])
    r = generate_segment(CTX, "ending", primary=llm, secondary=None, catalog=cat, banned=banned,
                         version="v6", lenient=True)
    assert llm.calls == 2 and "chosen_missing" in r.attempts[-1].warnings
