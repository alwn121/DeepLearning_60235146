"""SQLite wrapper and initialization for diet-tracker-bot.

- Creates database and tables if missing.
- Imports CSV food DB and synonyms JSON on first run.
- Provides CRUD helpers for user profile, food items, synonyms, and entries.

All text files are assumed UTF-8.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

DEFAULT_DB_PATH = os.path.join("storage", "diet.db")
DATA_DIR = os.path.join("data")
FOOD_CSV_PATH = os.path.join(DATA_DIR, "food_db.csv")
SYN_JSON_PATH = os.path.join(DATA_DIR, "synonyms.json")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user_profile(
    id INTEGER PRIMARY KEY,
    gender TEXT,
    age INTEGER,
    height_cm REAL,
    weight_kg REAL,
    activity TEXT,
    target_kcal REAL,
    macro_ratio TEXT
);

CREATE TABLE IF NOT EXISTS food_items(
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    kcal REAL,
    protein REAL,
    fat REAL,
    carbs REAL,
    unit_base TEXT
);

CREATE TABLE IF NOT EXISTS food_synonyms(
    id INTEGER PRIMARY KEY,
    alias TEXT UNIQUE,
    canonical TEXT
);

CREATE TABLE IF NOT EXISTS entries(
    id INTEGER PRIMARY KEY,
    dt TEXT,
    date TEXT,
    time TEXT,
    food_name TEXT,
    grams REAL,
    kcal REAL,
    protein REAL,
    fat REAL,
    carbs REAL,
    raw_input TEXT
);
"""


def ensure_dirs(db_path: str) -> None:
    storage_dir = os.path.dirname(db_path)
    if storage_dir and not os.path.isdir(storage_dir):
        os.makedirs(storage_dir, exist_ok=True)
    # reports/logs directories
    os.makedirs(os.path.join("storage", "logs"), exist_ok=True)
    os.makedirs(os.path.join("storage", "reports"), exist_ok=True)


@contextmanager
def get_conn(db_path: str = DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    ensure_dirs(db_path)
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        # defaults
        seed_foods(conn)
        seed_synonyms(conn)
        seed_default_profile(conn)


def seed_foods(conn: sqlite3.Connection) -> None:
    # load CSV to dataframe
    if not os.path.isfile(FOOD_CSV_PATH):
        return
    df = pd.read_csv(FOOD_CSV_PATH)
    df = df.fillna(0)
    for _, row in df.iterrows():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO food_items(name,kcal,protein,fat,carbs,unit_base) VALUES(?,?,?,?,?,?)",
                (str(row["name"]).strip(), float(row["kcal"]), float(row["protein"]), float(row["fat"]), float(row["carbs"]), "100g"),
            )
        except Exception:
            # Skip malformed rows gracefully
            continue


def seed_synonyms(conn: sqlite3.Connection) -> None:
    if not os.path.isfile(SYN_JSON_PATH):
        return
    try:
        with open(SYN_JSON_PATH, "r", encoding="utf-8") as f:
            mapping = json.load(f)
    except Exception:
        return
    for alias, canonical in mapping.items():
        conn.execute(
            "INSERT OR IGNORE INTO food_synonyms(alias, canonical) VALUES(?,?)",
            (alias.strip(), canonical.strip()),
        )


def seed_default_profile(conn: sqlite3.Connection) -> None:
    cur = conn.execute("SELECT COUNT(*) FROM user_profile")
    cnt = cur.fetchone()[0]
    if cnt:
        return
    default_macro = json.dumps({"carb": 0.4, "protein": 0.3, "fat": 0.3}, ensure_ascii=False)
    conn.execute(
        "INSERT INTO user_profile(id, gender, age, height_cm, weight_kg, activity, target_kcal, macro_ratio) VALUES(1,?,?,?,?,?,?,?)",
        ("male", 25, 175.0, 70.0, "light", None, default_macro),
    )


# CRUD helpers

def get_profile(db_path: str = DEFAULT_DB_PATH) -> Dict:
    with get_conn(db_path) as conn:
        cur = conn.execute("SELECT id, gender, age, height_cm, weight_kg, activity, target_kcal, macro_ratio FROM user_profile ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if not row:
            return {}
        macro_ratio = json.loads(row[7]) if row[7] else {"carb": 0.4, "protein": 0.3, "fat": 0.3}
        return {
            "id": row[0],
            "gender": row[1],
            "age": row[2],
            "height_cm": row[3],
            "weight_kg": row[4],
            "activity": row[5],
            "target_kcal": row[6],
            "macro_ratio": macro_ratio,
        }


def set_profile(
    gender: Optional[str] = None,
    age: Optional[int] = None,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
    activity: Optional[str] = None,
    target_kcal: Optional[float] = None,
    macro_ratio: Optional[Dict[str, float]] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    init_db(db_path)
    with get_conn(db_path) as conn:
        cur = conn.execute("SELECT id FROM user_profile ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if not row:
            seed_default_profile(conn)
        # Build update
        current = get_profile(db_path)
        gender = gender or current.get("gender")
        age = age if age is not None else current.get("age")
        height_cm = height_cm if height_cm is not None else current.get("height_cm")
        weight_kg = weight_kg if weight_kg is not None else current.get("weight_kg")
        activity = activity or current.get("activity")
        target_kcal = target_kcal if target_kcal is not None else current.get("target_kcal")
        macro_ratio_json = json.dumps(macro_ratio or current.get("macro_ratio"), ensure_ascii=False)
        conn.execute(
            "UPDATE user_profile SET gender=?, age=?, height_cm=?, weight_kg=?, activity=?, target_kcal=?, macro_ratio=? WHERE id=1",
            (gender, age, height_cm, weight_kg, activity, target_kcal, macro_ratio_json),
        )


def upsert_food(
    name: str,
    kcal: float,
    protein: float,
    fat: float,
    carbs: float,
    unit_base: str = "100g",
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    init_db(db_path)
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO food_items(name,kcal,protein,fat,carbs,unit_base) VALUES(?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET kcal=excluded.kcal, protein=excluded.protein, fat=excluded.fat, carbs=excluded.carbs, unit_base=excluded.unit_base",
            (name.strip(), float(kcal), float(protein), float(fat), float(carbs), unit_base),
        )


def search_foods(q: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict]:
    init_db(db_path)
    like = f"%{q}%"
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "SELECT name,kcal,protein,fat,carbs FROM food_items WHERE name LIKE ? ORDER BY name",
            (like,),
        )
        return [
            {"name": r[0], "kcal": r[1], "protein": r[2], "fat": r[3], "carbs": r[4]} for r in cur.fetchall()
        ]


def import_csv(csv_path: str, db_path: str = DEFAULT_DB_PATH) -> int:
    df = pd.read_csv(csv_path)
    count = 0
    with get_conn(db_path) as conn:
        for _, row in df.iterrows():
            try:
                upsert_food(
                    name=str(row["name"]).strip(),
                    kcal=float(row["kcal"]),
                    protein=float(row["protein"]),
                    fat=float(row["fat"]),
                    carbs=float(row["carbs"]),
                    db_path=db_path,
                )
                count += 1
            except Exception:
                continue
    return count


def add_synonym(alias: str, canonical: str, db_path: str = DEFAULT_DB_PATH) -> None:
    init_db(db_path)
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO food_synonyms(alias, canonical) VALUES(?,?)",
            (alias.strip(), canonical.strip()),
        )


def resolve_canonical(name: str, db_path: str = DEFAULT_DB_PATH) -> str:
    init_db(db_path)
    name = name.strip()
    with get_conn(db_path) as conn:
        cur = conn.execute("SELECT canonical FROM food_synonyms WHERE alias=?", (name,))
        r = cur.fetchone()
        if r:
            return r[0]
        # Partial or startswith suggestions
        cur = conn.execute("SELECT name FROM food_items WHERE name=?", (name,))
        r = cur.fetchone()
        return r[0] if r else name


def get_food(name: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict]:
    init_db(db_path)
    with get_conn(db_path) as conn:
        cur = conn.execute("SELECT name,kcal,protein,fat,carbs FROM food_items WHERE name=?", (name,))
        r = cur.fetchone()
        if not r:
            # try contains
            like = f"%{name}%"
            cur = conn.execute("SELECT name,kcal,protein,fat,carbs FROM food_items WHERE name LIKE ? ORDER BY LENGTH(name) ASC LIMIT 1", (like,))
            r = cur.fetchone()
        if not r:
            return None
        return {"name": r[0], "kcal": r[1], "protein": r[2], "fat": r[3], "carbs": r[4]}


def insert_entry(
    dt_iso: str,
    date_str: str,
    time_str: str,
    food_name: str,
    grams: float,
    kcal: float,
    protein: float,
    fat: float,
    carbs: float,
    raw_input: str,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    init_db(db_path)
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO entries(dt,date,time,food_name,grams,kcal,protein,fat,carbs,raw_input) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (dt_iso, date_str, time_str, food_name, grams, kcal, protein, fat, carbs, raw_input),
        )
        return cur.lastrowid


def list_entries_by_date(date_str: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict]:
    init_db(db_path)
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "SELECT id, food_name, grams, kcal, protein, fat, carbs, time FROM entries WHERE date=? ORDER BY time",
            (date_str,),
        )
        return [
            {
                "id": r[0],
                "food_name": r[1],
                "grams": r[2],
                "kcal": r[3],
                "protein": r[4],
                "fat": r[5],
                "carbs": r[6],
                "time": r[7],
            }
            for r in cur.fetchall()
        ]


def delete_entry(entry_id: int, db_path: str = DEFAULT_DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))


def sum_entries(date_str: str, db_path: str = DEFAULT_DB_PATH) -> Dict[str, float]:
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "SELECT SUM(kcal), SUM(protein), SUM(fat), SUM(carbs) FROM entries WHERE date=?",
            (date_str,),
        )
        s = cur.fetchone() or (0, 0, 0, 0)
        return {"kcal": s[0] or 0.0, "protein": s[1] or 0.0, "fat": s[2] or 0.0, "carbs": s[3] or 0.0}

