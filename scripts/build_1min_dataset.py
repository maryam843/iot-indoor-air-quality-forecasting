"""
Rebuild the 1-minute dataset from the raw Arduino Cloud exports.

Input:  data/raw/{humidity,temperature,voc}_raw.csv.gz   (columns: time, value)
Output: data/sensors_1min.csv                            (time, humidity, temperature, VOC)

Steps: parse timestamps as UTC, take the 1-minute mean of each sensor separately,
join the three series on the timestamp (not by row position), and drop minutes
where any sensor has no reading.

This replaces the old processed_data.csv, whose humidity column was not aligned
in time with temperature and VOC.

Run from the repo root:  python scripts/build_1min_dataset.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "sensors_1min.csv"

SENSORS = {"humidity": "humidity_raw.csv.gz", "temperature": "temperature_raw.csv.gz", "VOC": "voc_raw.csv.gz"}


def load_1min(filename):
    df = pd.read_csv(RAW / filename)
    df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
    return df.set_index("time")["value"].resample("1min").mean()


def main():
    series = {name: load_1min(fn) for name, fn in SENSORS.items()}
    data = pd.concat(series, axis=1, join="outer").dropna()  # aligned on the time index
    data.index.name = "time"
    data.to_csv(OUT, float_format="%.6f", date_format="%Y-%m-%dT%H:%M:%SZ")

    # Sanity checks
    print(f"rows: {len(data):,}")
    print(f"range: {data.index.min()} -> {data.index.max()}")
    window = data.loc["2025-06-03 00:00":"2025-06-07 20:44"]
    print(f"humidity mean 3-7 Jun: {window['humidity'].mean():.2f} (the old processed_data.csv had 40.14)")
    print(f"written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
