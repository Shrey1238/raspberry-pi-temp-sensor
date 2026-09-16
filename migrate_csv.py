"""One-off import of the legacy temperature_log.csv into the SQLite database.

python3 migrate_csv.py temperature_log.csv --db temperature_log.db
"""

from __future__ import annotations

import argparse
import sys

from storage import DEFAULT_DB, TemperatureStore


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Import legacy CSV readings into SQLite.")
    p.add_argument("csv", help="Path to the legacy timestamp,temperature CSV")
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite database path (default: %(default)s)")
    args = p.parse_args(argv)

    with TemperatureStore(args.db) as store:
        result = store.import_csv(args.csv)
    print(f"imported {result['imported']} rows, skipped {result['skipped']} null/invalid rows -> {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
