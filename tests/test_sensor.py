import pytest

from sensor import SensorReadError, read_temperature


def _reader(results):
    it = iter(results)

    def _read():
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r

    return _read


def test_returns_first_valid_reading():
    reading = read_temperature(_reader([(40.0, 22.5)]), sleep=lambda _: None)
    assert reading.temperature == 22.5
    assert reading.humidity == 40.0
    assert reading.attempts == 1


def test_retries_past_none_and_runtime_error():
    slept = []
    reading = read_temperature(
        _reader([(None, None), RuntimeError("checksum"), (41.0, 23.0)]),
        retries=5,
        base_delay=2.0,
        sleep=slept.append,
    )
    assert reading.temperature == 23.0
    assert reading.attempts == 3
    assert slept == [2.0, 4.0]


def test_backoff_is_capped():
    slept = []
    with pytest.raises(SensorReadError):
        read_temperature(_reader([(None, None)] * 5), retries=5, base_delay=2.0, max_delay=5.0, sleep=slept.append)
    assert slept == [2.0, 4.0, 5.0, 5.0]


def test_out_of_range_values_are_rejected():
    reading = read_temperature(_reader([(40.0, 150.0), (120.0, 22.0), (40.0, 21.0)]), sleep=lambda _: None)
    assert reading.temperature == 21.0
    assert reading.attempts == 3


def test_raises_after_exhausting_retries_with_last_error():
    err = RuntimeError("boom")
    with pytest.raises(SensorReadError) as exc_info:
        read_temperature(_reader([(None, None), err]), retries=2, sleep=lambda _: None)
    assert exc_info.value.attempts == 2
    assert exc_info.value.last_error is err


def test_retries_must_be_positive():
    with pytest.raises(ValueError):
        read_temperature(_reader([]), retries=0)
