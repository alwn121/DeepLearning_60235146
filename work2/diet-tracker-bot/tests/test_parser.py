from db import init_db, DEFAULT_DB_PATH
from food_parser import parse_text, compute_nutrition


def test_parse_and_total_kcal():
    init_db(DEFAULT_DB_PATH)
    text = "계란 2개, 토마토 100g, 닭가슴살 150g"
    items, unresolved = parse_text(text)
    assert not unresolved
    grams_map = {it.canonical_name: it.grams for it in items}
    assert grams_map.get("계란") in (100, 100.0)
    assert grams_map.get("토마토") in (100, 100.0)
    assert grams_map.get("닭가슴살") in (150, 150.0)
    total = {"kcal":0.0,"protein":0.0,"fat":0.0,"carbs":0.0}
    for it in items:
        n = compute_nutrition(it.canonical_name, it.grams)
        for k in total:
            total[k] += n[k]
    # Rough expected using provided DB
    # 계란 100g: 155 kcal, 토마토 100g: 18 kcal, 닭가슴살 150g: 165*1.5=247.5 kcal => total ~ 420.5 kcal
    assert abs(total["kcal"] - 420.5) / 420.5 < 0.03


def test_bap_bowl():
    init_db(DEFAULT_DB_PATH)
    text = "밥 1공기"
    items, unresolved = parse_text(text)
    assert not unresolved
    assert items[0].grams == 210.0

