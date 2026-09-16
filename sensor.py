"""DHT11 sensor access with retry logic.

DHT11 reads over the single-wire protocol fail routinely (bad checksum,
timing glitches), and the Adafruit library reports those failures either
by returning ``None`` or by raising ``RuntimeError``. ``read_temperature``
wraps the raw read with bounded retries and exponential backoff so a
transient glitch never produces a null row in the log.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger(__name__)

RawReader = Callable[[], tuple[Optional[float], Optional[float]]]


class SensorReadError(Exception):
    """Raised when every retry attempt failed to produce a valid reading."""

    def __init__(self, attempts: int, last_error: BaseException | None = None):
        self.attempts = attempts
        self.last_error = last_error
        detail = f": {last_error!r}" if last_error else ""
        super().__init__(f"sensor read failed after {attempts} attempt(s){detail}")


@dataclass
class Reading:
    temperature: float
    humidity: float | None
    attempts: int


def _is_valid(temperature: float | None, humidity: float | None) -> bool:
    if temperature is None:
        return False
    # DHT11 datasheet operating ranges; anything outside is a corrupt frame.
    if not -20.0 <= temperature <= 60.0:
        return False
    return humidity is None or 0.0 <= humidity <= 100.0


def read_temperature(
    raw_read: RawReader,
    retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 10.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Reading:
    """Read the sensor, retrying on ``None`` results, exceptions, or out-of-range values.

    ``retries`` is the total number of attempts. Delay between attempts grows
    exponentially from ``base_delay`` and is capped at ``max_delay``. The
    DHT11 needs ~2s between polls, so ``base_delay`` should not go below that.
    """
    if retries < 1:
        raise ValueError("retries must be >= 1")

    last_error: BaseException | None = None
    for attempt in range(1, retries + 1):
        try:
            humidity, temperature = raw_read()
        except (RuntimeError, OSError) as exc:
            last_error = exc
            log.warning("sensor read attempt %d/%d raised %r", attempt, retries, exc)
        else:
            if _is_valid(temperature, humidity):
                assert temperature is not None
                return Reading(temperature=float(temperature), humidity=humidity, attempts=attempt)
            last_error = None
            log.warning(
                "sensor read attempt %d/%d returned invalid data (temp=%r, humidity=%r)",
                attempt,
                retries,
                temperature,
                humidity,
            )

        if attempt < retries:
            sleep(min(base_delay * (2 ** (attempt - 1)), max_delay))

    raise SensorReadError(retries, last_error)


def adafruit_reader(pin: int) -> RawReader:
    """Return a raw reader backed by the Adafruit_DHT library."""
    import Adafruit_DHT  # imported lazily so the rest of the project runs off-Pi

    def _read() -> tuple[float | None, float | None]:
        return Adafruit_DHT.read(Adafruit_DHT.DHT11, pin)

    return _read


def simulated_reader(failure_rate: float = 0.3, seed: int | None = None) -> RawReader:
    """Return a fake reader that mimics DHT11 flakiness, for development without hardware."""
    rng = random.Random(seed)
    state = {"temp": 22.0}

    def _read() -> tuple[float | None, float | None]:
        roll = rng.random()
        if roll < failure_rate / 2:
            return None, None
        if roll < failure_rate:
            raise RuntimeError("simulated checksum failure")
        state["temp"] += rng.uniform(-0.3, 0.3)
        return round(rng.uniform(35, 55), 1), round(state["temp"], 1)

    return _read
