"""SQLite storage for temperature readings."""

from __future__ import annotations

import csv
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

DEFAULT_DB = "temperature_log.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    temperature REAL    NOT NULL,
    humidity    REAL,
    attempts    INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings (timestamp);

CREATE TABLE IF NOT EXISTS read_failures (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT    NOT NULL,
    attempts  INTEGER NOT NULL,
    error     TEXT
);
"""


class TemperatureStore:
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> TemperatureStore:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def add_reading(
        self,
        temperature: float,
        timestamp: datetime | None = None,
        humidity: float | None = None,
        attempts: int = 1,
    ) -> int:
        ts = (timestamp or datetime.now()).isoformat(sep=" ", timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO readings (timestamp, temperature, humidity, attempts) VALUES (?, ?, ?, ?)",
                (ts, float(temperature), humidity, attempts),
            )
        return int(cur.lastrowid)

    def add_failure(self, attempts: int, error: str | None, timestamp: datetime | None = None) -> None:
        ts = (timestamp or datetime.now()).isoformat(sep=" ", timespec="seconds")
        with self._conn:
            self._conn.execute(
                "INSERT INTO read_failures (timestamp, attempts, error) VALUES (?, ?, ?)",
                (ts, attempts, error),
            )

    def recent(self, limit: int = 500) -> list[dict]:
        """Most recent ``limit`` readings, oldest first (ready for charting)."""
        rows = self._conn.execute(
            "SELECT timestamp, temperature, humidity, attempts FROM readings ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def latest(self) -> dict | None:
        row = self._conn.execute(
            "SELECT timestamp, temperature, humidity, attempts FROM readings ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def stats(self) -> dict:
        r = self._conn.execute(
            "SELECT COUNT(*) AS n, MIN(temperature) AS lo, MAX(temperature) AS hi, "
            "AVG(temperature) AS avg, SUM(attempts) AS attempts, "
            "SUM(CASE WHEN attempts > 1 THEN 1 ELSE 0 END) AS recovered "
            "FROM readings"
        ).fetchone()
        f = self._conn.execute("SELECT COUNT(*) AS n FROM read_failures").fetchone()
        return {
            "readings": r["n"],
            "min": r["lo"],
            "max": r["hi"],
            "avg": round(r["avg"], 2) if r["avg"] is not None else None,
            "recovered_by_retry": r["recovered"] or 0,
            "total_attempts": r["attempts"] or 0,
            "failed_cycles": f["n"],
        }

    def import_csv(self, csv_path: str | Path) -> dict[str, int]:
        """Import rows from the legacy ``timestamp,temperature`` CSV; skip null/blank rows."""
        imported = skipped = 0
        with open(csv_path, newline="") as fh:
            rows: Iterable[dict[str, str]] = csv.DictReader(fh)
            with self._conn:
                for row in rows:
                    raw = (row.get("temperature") or "").strip()
                    if raw in ("", "None"):
                        skipped += 1
                        continue
                    try:
                        temp = float(raw)
                    except ValueError:
                        skipped += 1
                        continue
                    self._conn.execute(
                        "INSERT INTO readings (timestamp, temperature) VALUES (?, ?)",
                        (row["timestamp"].strip(), temp),
                    )
                    imported += 1
        return {"imported": imported, "skipped": skipped}
