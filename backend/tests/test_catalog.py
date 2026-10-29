from app.catalog import load_catalog

KINDS = ["backgrounds", "characters", "objects", "states", "moods", "sfx", "times"]


def test_real_catalog_loads_and_ids_are_unique_across_kinds():
    cat = load_catalog()
    all_ids = [i for k in KINDS for i in cat.ids(k)]
    assert len(all_ids) == len(set(all_ids))


def test_defaults_exist():
    cat = load_catalog()
    assert cat.default_background in cat.ids("backgrounds")
    assert cat.default_state in cat.ids("states")
    assert cat.default_mood in cat.ids("moods")


def test_cards_are_choice_ids_and_at_least_10():
    cat = load_catalog()
    assert len(cat.card_ids()) >= 10
    item_cards = [c for c in cat.card_ids() if cat.kind_of(c) != "trait"]
    assert set(item_cards) <= cat.choice_ids()


def test_bgm_mood_refers_to_existing_mood():
    cat = load_catalog()
    assert all(b.mood in cat.ids("moods") for b in cat.bgm)


def test_name_of_and_listing():
    cat = load_catalog()
    assert cat.name_of("rabbit") == "토끼"
    assert "rabbit(토끼)" in cat.prompt_listing()
