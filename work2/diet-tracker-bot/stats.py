from __future__ import annotations

from typing import Dict, List


def weekly_stats(kcal_list: List[float], targets_kcal: float | None = None) -> Dict[str, float]:
    n = len(kcal_list) or 1
    avg = sum(kcal_list) / n
    above = sum(1 for k in kcal_list if targets_kcal is not None and k > targets_kcal * 1.05)
    below = sum(1 for k in kcal_list if targets_kcal is not None and k < targets_kcal * 0.95)
    return {"avg_kcal": avg, "above_days": above, "below_days": below}

