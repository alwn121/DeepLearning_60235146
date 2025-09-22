"""Rule-based meal recommender.

Strategy:
- Prioritize protein foods to meet protein target (~1.6g/kg body weight)
- Distribute carbs via rice/sweet potato/fruit; fats from fish/dairy
- Greedy allocation per meal with +/-10% tolerance of per-meal kcal

This is a heuristic, not an optimizer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from db import get_food

PROTEIN_FOODS = ["닭가슴살", "참치캔(물)", "계란", "두부", "요거트", "연어", "고등어"]
CARB_FOODS = ["백미밥", "현미밥", "고구마", "바나나", "사과"]
FAT_HELPERS = ["연어", "고등어", "요거트"]


@dataclass
class FoodPortion:
    name: str
    grams: float
    kcal: float
    protein: float
    fat: float
    carbs: float


def nutrition_for(name: str, grams: float) -> FoodPortion:
    f = get_food(name)
    if not f:
        return FoodPortion(name=name, grams=grams, kcal=0, protein=0, fat=0, carbs=0)
    factor = grams / 100.0
    return FoodPortion(
        name=name,
        grams=grams,
        kcal=f["kcal"] * factor,
        protein=f["protein"] * factor,
        fat=f["fat"] * factor,
        carbs=f["carbs"] * factor,
    )


def recommend_meals(target_kcal: float, macro_ratio: Dict[str, float], body_weight: float, meals: int = 3, avoid: List[str] | None = None, prefer: List[str] | None = None) -> List[Dict]:
    avoid = set(avoid or [])
    prefer = set(prefer or [])
    per_meal = target_kcal / meals
    lower = per_meal * 0.9
    upper = per_meal * 1.1

    protein_target_g = max(1.6 * body_weight, (target_kcal * macro_ratio.get("protein", 0.3)) / 4)
    protein_per_meal = protein_target_g / meals

    plans: List[Dict] = []
    for _ in range(meals):
        portions: List[FoodPortion] = []
        total_kcal = 0.0
        total_p = 0.0
        total_f = 0.0
        total_c = 0.0
        # add protein source
        candidates = [f for f in (list(prefer) + PROTEIN_FOODS) if f not in avoid]
        picked = None
        for cand in candidates:
            info = get_food(cand)
            if info:
                picked = cand
                break
        if picked:
            # rough grams to hit protein_per_meal from this source alone capped by kcal window
            p100 = get_food(picked)["protein"]
            grams = min(200.0, max(50.0, protein_per_meal / max(p100, 0.1) * 100.0))
            fp = nutrition_for(picked, grams)
            portions.append(fp)
            total_kcal += fp.kcal
            total_p += fp.protein
            total_f += fp.fat
            total_c += fp.carbs
        # add carb base
        for carb in (list(prefer) + CARB_FOODS):
            if carb in avoid:
                continue
            info = get_food(carb)
            if not info:
                continue
            # choose grams to approach per_meal kcal
            remain = max(lower - total_kcal, 0) if total_kcal < lower else (per_meal - total_kcal)
            if remain <= 0:
                break
            g = min(250.0, max(80.0, remain / max(info["kcal"], 1e-6) * 100.0))
            fp = nutrition_for(carb, g)
            portions.append(fp)
            total_kcal += fp.kcal
            total_p += fp.protein
            total_f += fp.fat
            total_c += fp.carbs
            if total_kcal >= lower:
                break
        # small fat helper if kcal below lower
        if total_kcal < lower:
            for fatname in FAT_HELPERS:
                if fatname in avoid:
                    continue
                info = get_food(fatname)
                if not info:
                    continue
                add = min(100.0, max(30.0, (per_meal - total_kcal) / max(info["kcal"], 1e-6) * 100.0))
                fp = nutrition_for(fatname, add)
                portions.append(fp)
                total_kcal += fp.kcal
                total_p += fp.protein
                total_f += fp.fat
                total_c += fp.carbs
                if total_kcal >= lower:
                    break
        plans.append({
            "items": [p.__dict__ for p in portions],
            "kcal": total_kcal,
            "protein": total_p,
            "fat": total_f,
            "carbs": total_c,
        })
    return plans

