from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, date
from typing import List

from db import (
    DEFAULT_DB_PATH,
    add_synonym,
    delete_entry,
    get_food,
    get_profile as db_get_profile,
    import_csv,
    init_db,
    insert_entry,
    list_entries_by_date,
    resolve_canonical,
    search_foods,
    set_profile,
    sum_entries,
)
from food_parser import parse_text, compute_nutrition
from models import UserProfile, parse_macro_str
from recommender import recommend_meals
from reporter import daily_markdown, plot_daily_macros, plot_weekly_trend, weekly_data


def verbose_print(verbose: bool, *args):
    if verbose:
        print(*args)


def cmd_profile_show(args):
    init_db(args.db)
    p = db_get_profile(args.db)
    prof = UserProfile(
        gender=p.get("gender", "male"),
        age=int(p.get("age", 25)),
        height_cm=float(p.get("height_cm", 175.0)),
        weight_kg=float(p.get("weight_kg", 70.0)),
        activity=p.get("activity", "light"),
        target_kcal=p.get("target_kcal"),
        macro_ratio=p.get("macro_ratio", {"carb": 0.4, "protein": 0.3, "fat": 0.3}),
    )
    bmr = prof.bmr()
    tdee = prof.tdee()
    tk = prof.resolve_target_kcal()
    m = prof.macro_targets_g(tk)
    print(f"Gender: {prof.gender}, Age: {prof.age}, Height: {prof.height_cm}, Weight: {prof.weight_kg}, Activity: {prof.activity}")
    print(f"BMR: {bmr:.1f} kcal, TDEE: {tdee:.1f} kcal")
    print(f"Target kcal: {tk:.1f}")
    print(f"Macros (g): carb {m['carb_g']:.1f}, protein {m['protein_g']:.1f}, fat {m['fat_g']:.1f}")


def cmd_profile_set(args):
    macro_ratio = None
    if args.macro:
        macro_ratio = parse_macro_str(args.macro)
    set_profile(
        gender=args.gender,
        age=args.age,
        height_cm=args.height,
        weight_kg=args.weight,
        activity=args.activity,
        target_kcal=args.target_kcal,
        macro_ratio=macro_ratio,
        db_path=args.db,
    )
    cmd_profile_show(args)


def cmd_log(args):
    init_db(args.db)
    dt = datetime.now()
    date_str = args.date or dt.date().isoformat()
    time_str = args.time or dt.strftime("%H:%M")
    items, unresolved = parse_text(args.text)
    verbose_print(args.verbose, "Parsed items:", items, "Unresolved:", unresolved)
    for it in items:
        n = compute_nutrition(it.canonical_name, it.grams)
        insert_entry(
            dt_iso=f"{date_str}T{time_str}",
            date_str=date_str,
            time_str=time_str,
            food_name=it.canonical_name,
            grams=it.grams,
            kcal=n["kcal"],
            protein=n["protein"],
            fat=n["fat"],
            carbs=n["carbs"],
            raw_input=args.text,
            db_path=args.db,
        )
    print(f"Logged {len(items)} items. Skipped {len(unresolved)} unresolved.")


def cmd_list(args):
    init_db(args.db)
    date_str = args.date or date.today().isoformat()
    rows = list_entries_by_date(date_str, args.db)
    for r in rows:
        print(f"[{r['id']}] {r['time']} {r['food_name']} {r['grams']:.0f}g => kcal {r['kcal']:.0f} P{r['protein']:.1f} F{r['fat']:.1f} C{r['carbs']:.1f}")


def cmd_delete(args):
    delete_entry(args.id, args.db)
    print(f"Deleted id {args.id}")


def cmd_summary(args):
    init_db(args.db)
    p = db_get_profile(args.db)
    prof = UserProfile(
        gender=p.get("gender", "male"),
        age=int(p.get("age", 25)),
        height_cm=float(p.get("height_cm", 175.0)),
        weight_kg=float(p.get("weight_kg", 70.0)),
        activity=p.get("activity", "light"),
        target_kcal=p.get("target_kcal"),
        macro_ratio=p.get("macro_ratio", {"carb": 0.4, "protein": 0.3, "fat": 0.3}),
    )
    date_str = args.date or date.today().isoformat()
    totals = sum_entries(date_str, args.db)
    tk = prof.resolve_target_kcal(args.deficit)
    target = {"kcal": tk, **prof.macro_targets_g(tk)}
    md = daily_markdown(date_str, {"kcal": target["kcal"]}, totals)
    out_dir = os.path.join("storage", "reports")
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, f"summary_{date_str}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    img1 = plot_daily_macros(date_str, totals, out_dir)
    print(md)
    print(f"Saved: {md_path}, {img1}")


def cmd_weekly(args):
    init_db(args.db)
    end = args.end or date.today().isoformat()
    labels, kcals = weekly_data(end)
    out_dir = os.path.join("storage", "reports")
    img = plot_weekly_trend(end, kcals, labels, out_dir)
    print(f"Saved: {img}")


def cmd_recommend(args):
    init_db(args.db)
    p = db_get_profile(args.db)
    prof = UserProfile(
        gender=p.get("gender", "male"),
        age=int(p.get("age", 25)),
        height_cm=float(p.get("height_cm", 175.0)),
        weight_kg=float(p.get("weight_kg", 70.0)),
        activity=p.get("activity", "light"),
        target_kcal=p.get("target_kcal"),
        macro_ratio=p.get("macro_ratio", {"carb": 0.4, "protein": 0.3, "fat": 0.3}),
    )
    tk = prof.resolve_target_kcal(args.deficit)
    plans = recommend_meals(
        target_kcal=tk,
        macro_ratio=prof.macro_ratio,
        body_weight=prof.weight_kg,
        meals=args.meals,
        avoid=[s.strip() for s in (args.avoid or "").split(",") if s.strip()],
        prefer=[s.strip() for s in (args.prefer or "").split(",") if s.strip()],
    )
    for i, plan in enumerate(plans, 1):
        print(f"== Meal {i} ==")
        for it in plan["items"]:
            print(f"- {it['name']} {it['grams']:.0f}g: {it['kcal']:.0f} kcal (P{it['protein']:.1f} F{it['fat']:.1f} C{it['carbs']:.1f})")
        print(f"Subtotal: {plan['kcal']:.0f} kcal (P{plan['protein']:.1f} F{plan['fat']:.1f} C{plan['carbs']:.1f})\n")


def cmd_foods_add(args):
    from db import upsert_food

    upsert_food(args.name, args.kcal, args.protein, args.fat, args.carbs, db_path=args.db)
    print(f"Upserted food: {args.name}")


def cmd_foods_search(args):
    rows = search_foods(args.q, args.db)
    for r in rows:
        print(f"{r['name']}: kcal {r['kcal']} P{r['protein']} F{r['fat']} C{r['carbs']}")


def cmd_foods_import(args):
    count = import_csv(args.csv, args.db)
    print(f"Imported {count} rows from {args.csv}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="diet-tracker-bot (offline)")
    p.add_argument("--db", default=DEFAULT_DB_PATH)
    p.add_argument("--lang", default="ko")
    p.add_argument("--verbose", action="store_true")

    sub = p.add_subparsers(dest="cmd", required=True)

    # profile
    p_show = sub.add_parser("profile")
    sub_profile = p_show.add_subparsers(dest="sub", required=True)
    sub_profile_show = sub_profile.add_parser("show")
    sub_profile_show.set_defaults(func=cmd_profile_show)

    sub_profile_set = sub_profile.add_parser("set")
    sub_profile_set.add_argument("--gender", choices=["male", "female"])
    sub_profile_set.add_argument("--age", type=int)
    sub_profile_set.add_argument("--height", type=float)
    sub_profile_set.add_argument("--weight", type=float)
    sub_profile_set.add_argument("--activity", choices=["sedentary", "light", "moderate", "very", "athlete"])
    sub_profile_set.add_argument("--target-kcal", type=float)
    sub_profile_set.add_argument("--macro", type=str)
    sub_profile_set.set_defaults(func=cmd_profile_set)

    # log
    p_log = sub.add_parser("log")
    p_log.add_argument("--text", required=True)
    p_log.add_argument("--date")
    p_log.add_argument("--time")
    p_log.set_defaults(func=cmd_log)

    # list
    p_list = sub.add_parser("list")
    p_list.add_argument("--date")
    p_list.set_defaults(func=cmd_list)

    # delete
    p_del = sub.add_parser("delete")
    p_del.add_argument("--id", type=int, required=True)
    p_del.set_defaults(func=cmd_delete)

    # recommend
    p_rec = sub.add_parser("recommend")
    p_rec.add_argument("--meals", type=int, default=3)
    p_rec.add_argument("--deficit", type=float)
    p_rec.add_argument("--avoid")
    p_rec.add_argument("--prefer")
    p_rec.set_defaults(func=cmd_recommend)

    # summary
    p_sum = sub.add_parser("summary")
    p_sum.add_argument("--date")
    p_sum.add_argument("--deficit", type=float)
    p_sum.set_defaults(func=cmd_summary)

    # weekly-report
    p_week = sub.add_parser("weekly-report")
    p_week.add_argument("--end")
    p_week.set_defaults(func=cmd_weekly)

    # foods
    p_foods = sub.add_parser("foods")
    sub_foods = p_foods.add_subparsers(dest="sub", required=True)
    f_add = sub_foods.add_parser("add")
    f_add.add_argument("--name", required=True)
    f_add.add_argument("--kcal", type=float, required=True)
    f_add.add_argument("--protein", type=float, required=True)
    f_add.add_argument("--fat", type=float, required=True)
    f_add.add_argument("--carbs", type=float, required=True)
    f_add.set_defaults(func=cmd_foods_add)

    f_search = sub_foods.add_parser("search")
    f_search.add_argument("--q", required=True)
    f_search.set_defaults(func=cmd_foods_search)

    f_import = sub_foods.add_parser("import-csv")
    f_import.add_argument("--csv", default=os.path.join("data", "food_db.csv"))
    f_import.set_defaults(func=cmd_foods_import)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    # Ensure DB exists
    init_db(args.db)
    args.func(args)


if __name__ == "__main__":
    main()

