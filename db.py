# db.py — single source of truth for SQLite demo DB (recruiter-friendly)
# Usage:
#   from db import get_db_connection, ensure_demo_data, has_column
#   conn = get_db_connection(); ensure_demo_data(conn)

import os
import sqlite3
from datetime import datetime, timedelta
import random

DB_FILE = os.getenv("SCRAPSENSE_DB", "scrapsense_demo.db")

def get_db_connection():
    """Return a sqlite3 connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def has_column(conn, table_name: str, column_name: str) -> bool:
    """Cross-DB-ish helper used by generate_report/view files."""
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    cols = {row["name"] for row in cur.fetchall()}
    return column_name in cols

def _create_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrap_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_operator TEXT,
            machine_name     TEXT,
            date             TEXT,      -- ISO 'YYYY-MM-DD'
            quantity         REAL,
            unit             TEXT,
            shift            TEXT,
            reason           TEXT,
            comments         TEXT,
            total_produced   REAL,
            entry_type       TEXT
        );
    """)
    conn.commit()

def _seed_demo(conn):
    cur = conn.execute("SELECT COUNT(*) AS c FROM scrap_logs")
    if cur.fetchone()["c"] > 0:
        return

    operators = ["Operator A", "Operator B", "Operator C"]
    machines  = ["Cutter-1", "Press-2", "Roller-3", "Trimmer-4"]
    shifts    = ["A", "B", "C"]
    reasons   = ["Misalignment", "Overheat", "Material Defect", "Power Surge", "Operator Error"]
    unit      = "lbs"

    today = datetime.today().date()
    rows = []
    for d in range(30):
        day = (today - timedelta(days=d)).strftime("%Y-%m-%d")
        for _ in range(random.randint(2, 6)):
            q = max(1, int(random.gauss(120, 40)))
            tp = q + max(1000, int(random.gauss(3000, 500)))
            rows.append((
                random.choice(operators),
                random.choice(machines),
                day, float(q), unit,
                random.choice(shifts),
                random.choice(reasons),
                "",
                float(tp),
                "Manual",
            ))
    conn.executemany("""
        INSERT INTO scrap_logs (
            machine_operator, machine_name, date, quantity, unit,
            shift, reason, comments, total_produced, entry_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()

def ensure_demo_data(conn=None):
    """Create DB file, schema, and seed demo data if empty."""
    own = False
    if conn is None:
        own = True
        conn = get_db_connection()
    try:
        _create_schema(conn)
        _seed_demo(conn)
    finally:
        if own:
            conn.close()
