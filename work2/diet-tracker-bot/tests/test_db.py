from db import init_db, upsert_food, get_food, insert_entry, sum_entries, DEFAULT_DB_PATH


def test_food_insert_and_sum():
    init_db(DEFAULT_DB_PATH)
    upsert_food("테스트식품", 100, 5, 2, 10)
    f = get_food("테스트식품")
    assert f and f["kcal"] == 100
    # add entry 200g => kcal 200
    entry_id = insert_entry(
        dt_iso="2025-01-01T08:00",
        date_str="2025-01-01",
        time_str="08:00",
        food_name="테스트식품",
        grams=200.0,
        kcal=200.0,
        protein=10.0,
        fat=4.0,
        carbs=20.0,
        raw_input="테스트식품 200g",
    )
    assert entry_id > 0
    totals = sum_entries("2025-01-01")
    assert totals["kcal"] == 200.0

