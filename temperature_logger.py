"""Continuously log DHT11 temperature readings to SQLite.

Usage on the Pi:
    python3 temperature_logger.py --interval 60 --pin 4

Without hardware (development / demo):
    python3 temperature_logger.py --simulate --interval 2
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime

from sensor import SensorReadError, adafruit_reader, read_temperature, simulated_reader
from storage import DEFAULT_DB, TemperatureStore

log = logging.getLogger("temperature_logger")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Log DHT11 temperature readings to SQLite.")
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite database path (default: %(default)s)")
    p.add_argument("--pin", type=int, default=4, help="GPIO pin the DHT11 data line is on (default: %(default)s)")
    p.add_argument("--interval", type=float, default=60.0, help="Seconds between readings (default: %(default)s)")
    p.add_argument("--retries", type=int, default=5, help="Read attempts per cycle (default: %(default)s)")
    p.add_argument("--retry-delay", type=float, default=2.0, help="Initial retry backoff in seconds (default: 2)")
    p.add_argument("--simulate", action="store_true", help="Use a fake sensor instead of Adafruit_DHT")
    p.add_argument("--once", action="store_true", help="Take a single reading and exit")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def log_cycle(store: TemperatureStore, raw_read, retries: int, retry_delay: float) -> bool:
    """Take one reading and persist it. Returns True on success, False if all retries failed."""
    now = datetime.now()
    try:
        reading = read_temperature(raw_read, retries=retries, base_delay=retry_delay)
    except SensorReadError as exc:
        store.add_failure(exc.attempts, repr(exc.last_error) if exc.last_error else None, timestamp=now)
        log.error("skipping cycle: %s", exc)
        return False

    store.add_reading(reading.temperature, timestamp=now, humidity=reading.humidity, attempts=reading.attempts)
    log.info(
        "%s  %.1f°C%s%s",
        now.strftime("%Y-%m-%d %H:%M:%S"),
        reading.temperature,
        f"  {reading.humidity:.0f}%RH" if reading.humidity is not None else "",
        f"  (after {reading.attempts} attempts)" if reading.attempts > 1 else "",
    )
    return True


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.simulate:
        raw_read = simulated_reader()
        log.info("using simulated sensor")
    else:
        try:
            raw_read = adafruit_reader(args.pin)
        except ImportError:
            log.error("Adafruit_DHT is not installed; run `pip3 install Adafruit-DHT` or use --simulate")
            return 1

    with TemperatureStore(args.db) as store:
        log.info("logging to %s every %.0fs (retries=%d)", store.path, args.interval, args.retries)
        try:
            while True:
                started = time.monotonic()
                log_cycle(store, raw_read, args.retries, args.retry_delay)
                if args.once:
                    break
                # Keep cycles aligned to the interval even if retries ate into it.
                time.sleep(max(0.0, args.interval - (time.monotonic() - started)))
        except KeyboardInterrupt:
            log.info("stopped")
        finally:
            s = store.stats()
            log.info(
                "%d readings stored, %d recovered by retry, %d cycles failed",
                s["readings"],
                s["recovered_by_retry"],
                s["failed_cycles"],
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
