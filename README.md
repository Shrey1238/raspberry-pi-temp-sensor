# Raspberry Pi Temperature Logger

A Python temperature logging system for a Raspberry Pi and a DHT11 sensor. A logger process samples the sensor at a fixed interval, retries transient read failures, and stores clean readings in SQLite. A Flask app serves a live temperature chart and a small JSON API to any device on the local network.

## Features

* Reads temperature (and humidity) from a DHT11 sensor
* **Retry with exponential backoff** around sensor reads: `None` results, `RuntimeError`s from the driver, and out-of-range frames are retried instead of being logged, so no null rows reach storage
* Failed cycles are recorded separately (`read_failures` table) so data quality can be measured
* **SQLite storage** (WAL mode) instead of a flat CSV; indexed on timestamp
* **Flask dashboard** with a live-updating chart plus `/api/readings`, `/api/latest`, `/api/stats`
* `--simulate` flag to run the whole stack without hardware
* One-off migration script for the legacy CSV log
* Unit tests for retry logic, storage, and the API

## Hardware Requirements

* Raspberry Pi
* DHT11 Temperature Sensor Module
* Jumper wires
* MicroSD card with Raspberry Pi OS installed

## Wiring

| DHT11 Pin | Raspberry Pi |
| --------- | ------------ |
| VCC       | 3.3V         |
| DATA      | GPIO 4       |
| GND       | Ground       |

If a different GPIO pin is used, pass `--pin <n>` to the logger.

## Install

```bash
pip3 install -r requirements.txt
```

`Adafruit-DHT` is only installed on ARM (the Pi). On a laptop use `--simulate`.

## Run

Start the logger (on the Pi):

```bash
python3 temperature_logger.py --interval 60 --pin 4
```

Start the dashboard, then open `http://<pi-ip>:5000` from any device on the same network:

```bash
python3 app.py --port 5000
```

Without hardware:

```bash
python3 temperature_logger.py --simulate --interval 2
python3 app.py
```

Logger options: `--db`, `--pin`, `--interval`, `--retries` (default 5), `--retry-delay` (default 2s, doubles each attempt up to 10s), `--once`, `--simulate`, `-v`.

## How It Works

1. `sensor.read_temperature()` calls the driver. If it returns `None`, raises, or gives a value outside the DHT11's range, it sleeps (2s → 4s → 8s → 10s cap) and tries again, up to `--retries` times.
2. On success the reading (temperature, humidity, number of attempts) is inserted into `readings`.
3. If every attempt fails, a row goes into `read_failures` and the cycle is skipped; nothing null is ever written to `readings`.
4. The loop sleeps for the remainder of the interval so retries don't drift the schedule.
5. `app.py` reads the same SQLite file and serves the chart, which polls `/api/readings` every 10s.

## API

| Endpoint                   | Returns                                                                      |
| -------------------------- | ---------------------------------------------------------------------------- |
| `GET /`                    | Live chart page                                                              |
| `GET /api/readings?limit=` | Most recent readings, oldest first (default 300, max 5000)                   |
| `GET /api/latest`          | Latest reading, or 404 if none                                               |
| `GET /api/stats`           | `readings`, `min`, `max`, `avg`, `recovered_by_retry`, `total_attempts`, `failed_cycles` |

## Migrating the old CSV

```bash
python3 migrate_csv.py temperature_log.csv --db temperature_log.db
```

Rows with a blank or `None` temperature are skipped and counted.

## Development

```bash
pip3 install -r requirements-dev.txt
pytest
ruff check . && ruff format --check .
```

## File Structure

```
├── temperature_logger.py   # logging loop / CLI
├── sensor.py               # DHT11 access + retry/backoff
├── storage.py              # SQLite store
├── app.py                  # Flask dashboard + JSON API
├── templates/index.html    # Chart.js front end
├── migrate_csv.py          # legacy CSV import
└── tests/
```

## Author

Shrey1238
