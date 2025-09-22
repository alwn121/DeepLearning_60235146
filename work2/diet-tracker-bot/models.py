"""Domain models and calculations for user profile and macros."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

ACTIVITY_MAP = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very": 1.725,
    "athlete": 1.9,
}


@dataclass
class UserProfile:
    gender: str
    age: int
    height_cm: float
    weight_kg: float
    activity: str
    target_kcal: float | None
    macro_ratio: Dict[str, float]

    def bmr(self) -> float:
        if self.gender == "female":
            return 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age - 161
        return 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + 5

    def tdee(self) -> float:
        factor = ACTIVITY_MAP.get(self.activity, 1.375)
        return self.bmr() * factor

    def resolve_target_kcal(self, deficit: float | None = None) -> float:
        base = self.target_kcal if self.target_kcal is not None else self.tdee()
        if deficit is not None and 0 < deficit < 0.9:
            return base * (1 - deficit)
        return base

    def macro_targets_g(self, target_kcal: float | None = None) -> Dict[str, float]:
        tk = target_kcal if target_kcal is not None else self.resolve_target_kcal()
        carb_ratio = self.macro_ratio.get("carb", 0.4)
        protein_ratio = self.macro_ratio.get("protein", 0.3)
        fat_ratio = self.macro_ratio.get("fat", 0.3)
        return {
            "carb_g": tk * carb_ratio / 4.0,
            "protein_g": tk * protein_ratio / 4.0,
            "fat_g": tk * fat_ratio / 9.0,
        }


def parse_macro_str(s: str) -> Dict[str, float]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 3:
        raise ValueError("macro must be 'carb,protein,fat'")
    c, p, f = (float(parts[0]), float(parts[1]), float(parts[2]))
    total = c + p + f
    if total <= 0:
        raise ValueError("macro ratios must be positive")
    # normalize if not summing to 1
    return {"carb": c / total, "protein": p / total, "fat": f / total}

