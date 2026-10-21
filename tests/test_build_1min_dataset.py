"""Tests for scripts/build_1min_dataset.py on a tiny fixture (no real data needed)."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_1min_dataset.py"


@pytest.fixture
def build(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("build_1min_dataset", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RAW", raw)
    monkeypatch.setattr(module, "OUT", tmp_path / "data" / "sensors_1min.csv")
    return module, raw


def write_raw(raw, name, rows):
    pd.DataFrame(rows, columns=["time", "value"]).to_csv(raw / name, index=False, compression="gzip")


def test_build_on_tiny_fixture(build):
    module, raw = build
    # Minute 00:00 has all three sensors, 00:01 has no humidity, 00:02 has all three.
    write_raw(raw, "humidity_raw.csv.gz", [
        ("2025-06-03T00:00:00.150610304Z", 40.0),
        ("2025-06-03T00:00:59.999999999Z", 42.0),
        ("2025-06-03T00:02:10.5Z", 44.0),
    ])
    write_raw(raw, "temperature_raw.csv.gz", [
        ("2025-06-03T00:00:03.5Z", 23.0),
        ("2025-06-03T00:01:30Z", 23.5),
        ("2025-06-03T00:02:00Z", 24.0),
    ])
    write_raw(raw, "voc_raw.csv.gz", [
        ("2025-06-03T00:00:01Z", 0.5),
        ("2025-06-03T00:00:30Z", 0.7),
        ("2025-06-03T00:01:00Z", 9.9),  # belongs to minute 00:01, must not leak into 00:00
        ("2025-06-03T00:02:30Z", 0.6),
    ])

    module.main()
    out = pd.read_csv(module.OUT, parse_dates=["time"])

    # Row count: the minute with a missing sensor is dropped
    assert len(out) == 2
    assert list(out.columns) == ["time", "humidity", "temperature", "VOC"]

    # 1-minute grid: every timestamp is on a whole minute and increasing
    times = pd.DatetimeIndex(out["time"])
    assert (times.second == 0).all() and (times.microsecond == 0).all()
    assert times.is_monotonic_increasing
    assert list(times.strftime("%H:%M")) == ["00:00", "00:02"]

    # No future leakage: minute 00:00 averages only readings from [00:00, 00:01)
    first = out.iloc[0]
    assert first["humidity"] == pytest.approx(41.0)
    assert first["temperature"] == pytest.approx(23.0)
    assert first["VOC"] == pytest.approx(0.6)
    assert out.iloc[1]["VOC"] == pytest.approx(0.6)
