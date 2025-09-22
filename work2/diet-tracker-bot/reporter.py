"""Reporter that generates daily and weekly summaries with plots.
Ensures Korean fonts on each OS.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Dict, List

import matplotlib
import matplotlib.pyplot as plt

from db import list_entries_by_date, sum_entries, get_profile
from models import UserProfile


def set_korean_font():
    try:
        if os.name == "nt":
            matplotlib.rc("font", family="Malgun Gothic")
        elif sys.platform == "darwin":
            matplotlib.rc("font", family="AppleGothic")
        else:
            # Linux
            matplotlib.rc("font", family="NanumGothic")
    except Exception:
        matplotlib.rc("font", family="sans-serif")
    matplotlib.rcParams["axes.unicode_minus"] = False


def daily_markdown(date_str: str, target: Dict[str, float], totals: Dict[str, float], unresolved: List[str] | None = None) -> str:
    unresolved = unresolved or []
    achieved = totals["kcal"] <= target["kcal"] * 1.05 and totals["kcal"] >= target["kcal"] * 0.85
    lines = [
        f"# Daily Summary {date_str}",
        "",
        f"- 총 칼로리: {totals['kcal']:.0f} kcal / 목표 {target['kcal']:.0f} kcal",
        f"- 탄수화물: {totals['carbs']:.1f} g",
        f"- 단백질: {totals['protein']:.1f} g",
        f"- 지방: {totals['fat']:.1f} g",
        f"- 달성 여부: {'달성' if achieved else '미달/초과'}",
    ]
    if unresolved:
        lines.append("\n## 미해석 항목")
        for u in unresolved:
            lines.append(f"- {u}")
    return "\n".join(lines)


def plot_daily_macros(date_str: str, totals: Dict[str, float], out_dir: str) -> str:
    set_korean_font()
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["탄수화물", "단백질", "지방"], [totals["carbs"], totals["protein"], totals["fat"]], color=["#4e79a7", "#59a14f", "#f28e2b"])
    ax.set_title(f"매크로 요약 {date_str}")
    ax.set_ylabel("g")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"daily_bar_{date_str}.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_weekly_trend(end_date: str, kcal_list: List[float], date_labels: List[str], out_dir: str) -> str:
    set_korean_font()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(date_labels, kcal_list, marker="o")
    ax.set_title(f"최근 7일 칼로리 추세 ({end_date})")
    ax.set_ylabel("kcal")
    ax.set_xlabel("날짜")
    plt.xticks(rotation=45, ha="right")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"weekly_trend_{end_date}.png")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def weekly_data(end_date: str) -> tuple[list[str], list[float]]:
    end = datetime.fromisoformat(end_date).date()
    labels: List[str] = []
    kcals: List[float] = []
    for i in range(6, -1, -1):
        d = end - timedelta(days=i)
        labels.append(d.isoformat())
        totals = sum_entries(d.isoformat())
        kcals.append(totals["kcal"])
    return labels, kcals

