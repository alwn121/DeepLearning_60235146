"""Korean food quantity parser.

Parses inputs like:
- "계란 2개, 토마토 100g, 닭가슴살 150g"
- "밥 1공기"

Rules:
- Units: g, kg, ml, l, 개, 공기, 큰술, 작은술
- If number without unit after a food -> grams
- ml ~ g for liquids (approximate)
- 계란 1개=50g, 밥 1공기=210g, 큰술=~13.5g, 작은술=~4.5g
- Fallback: resolve synonyms and partial matches via DB
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from db import get_food, resolve_canonical

NUM_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(g|kg|ml|l|개|공기|큰술|작은술)?", re.IGNORECASE)

UNIT_TO_G = {
    "g": 1.0,
    "kg": 1000.0,
    "ml": 1.0,  # approx density 1g/ml
    "l": 1000.0,
    "개": 50.0,  # egg default
    "공기": 210.0,  # rice bowl
    "큰술": 13.5,
    "작은술": 4.5,
}


@dataclass
class ParsedItem:
    raw_name: str
    canonical_name: str
    grams: float


def split_items(text: str) -> List[str]:
    text = text.replace("그리고", ",")
    parts = [p.strip() for p in re.split(r",|\n|/", text) if p.strip()]
    return parts


def extract_amount(segment: str) -> Optional[Tuple[float, Optional[str]]]:
    m = NUM_UNIT_RE.search(segment)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower() if m.group(2) else None
    return value, unit


def to_grams(value: float, unit: Optional[str], food_name: str) -> float:
    if unit is None:
        return value  # assume grams
    # If unit is count based but food is not egg/rice, still approximate
    base = UNIT_TO_G.get(unit)
    if base is None:
        return value
    return value * base


def parse_text(text: str) -> Tuple[List[ParsedItem], List[str]]:
    items: List[ParsedItem] = []
    unresolved: List[str] = []
    for segment in split_items(text):
        if not segment:
            continue
        # Find name by removing trailing number+unit
        amt = extract_amount(segment)
        name_part = segment
        if amt:
            start, end = NUM_UNIT_RE.search(segment).span()
            name_part = (segment[:start] + segment[end:]).strip()
        name_part = re.sub(r"\s+", " ", name_part).strip()
        if not name_part:
            # try using the whole segment as name
            name_part = segment.strip()
        canonical = resolve_canonical(name_part)
        value_g = 0.0
        if amt:
            value_g = to_grams(amt[0], amt[1], canonical)
        else:
            # default 100g if only a name given
            value_g = 100.0
        food = get_food(canonical)
        if not food:
            # try fallback contains
            food = get_food(name_part)
        if not food:
            unresolved.append(segment)
            continue
        items.append(ParsedItem(raw_name=name_part, canonical_name=food["name"], grams=value_g))
    return items, unresolved


def compute_nutrition(canonical_name: str, grams: float) -> Dict[str, float]:
    food = get_food(canonical_name)
    if not food:
        return {"kcal": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    factor = grams / 100.0
    return {
        "kcal": food["kcal"] * factor,
        "protein": food["protein"] * factor,
        "fat": food["fat"] * factor,
        "carbs": food["carbs"] * factor,
    }

