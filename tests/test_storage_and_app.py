from datetime import datetime

import pytest

from app import create_app
from sensor import SensorReadError
from storage import TemperatureStore
from temperature_logger import log_cycle


@pytest.fixture
def store(tmp_path):
    with TemperatureStore(tmp_path / "t.db") as s:
        yield s


def test_add_and_recent_order(store):
    for i, t in enumerate([20.0, 21.0, 22.0]):
        store.add_reading(t, timestamp=datetime(2026, 1, 1, 0, i))
    rows = store.recent(2)
    assert [r["temperature"] for r in rows] == [21.0, 22.0]
    assert store.latest()["temperature"] == 22.0


def test_stats_counts_retries_and_failures(store):
    store.add_reading(20.0, attempts=1)
    store.add_reading(24.0, attempts=3)
    store.add_failure(5, "RuntimeError('x')")
    s = store.stats()
    assert s["readings"] == 2
    assert s["min"] == 20.0 and s["max"] == 24.0 and s["avg"] == 22.0
    assert s["recovered_by_retry"] == 1
    assert s["total_attempts"] == 4
    assert s["failed_cycles"] == 1


def test_import_csv_skips_null_rows(store, tmp_path):
    csv_path = tmp_path / "legacy.csv"
    csv_path.write_text(
        "timestamp,temperature\n"
        "2026-07-08 14:28:22,22.5\n"
        "2026-07-08 14:28:23,\n"
        "2026-07-08 14:28:24,None\n"
        "2026-07-08 14:28:25,23\n"
    )
    assert store.import_csv(csv_path) == {"imported": 2, "skipped": 2}
    assert [r["temperature"] for r in store.recent()] == [22.5, 23.0]


def test_log_cycle_never_writes_null_rows(store):
    assert log_cycle(store, lambda: (None, None), retries=2, retry_delay=0) is False
    assert store.recent() == []
    assert store.stats()["failed_cycles"] == 1

    assert log_cycle(store, lambda: (45.0, 21.5), retries=2, retry_delay=0) is True
    assert store.latest()["temperature"] == 21.5


def test_api_endpoints(tmp_path):
    db = tmp_path / "api.db"
    with TemperatureStore(db) as s:
        s.add_reading(19.0, timestamp=datetime(2026, 1, 1, 12, 0))
        s.add_reading(20.0, timestamp=datetime(2026, 1, 1, 12, 1))

    client = create_app(str(db)).test_client()

    assert client.get("/").status_code == 200
    assert b"<canvas" in client.get("/").data

    body = client.get("/api/readings?limit=1").get_json()
    assert body == [{"timestamp": "2026-01-01 12:01:00", "temperature": 20.0, "humidity": None, "attempts": 1}]

    assert client.get("/api/readings?limit=abc").status_code == 400
    assert client.get("/api/latest").get_json()["temperature"] == 20.0
    assert client.get("/api/stats").get_json()["readings"] == 2


def test_api_latest_404_when_empty(tmp_path):
    client = create_app(str(tmp_path / "empty.db")).test_client()
    assert client.get("/api/latest").status_code == 404


def test_sensor_error_message():
    assert "2 attempt" in str(SensorReadError(2))
