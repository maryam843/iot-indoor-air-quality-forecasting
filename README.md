# IoT indoor air-quality forecasting

[![CI](https://github.com/maryam843/iot-indoor-air-quality-forecasting/actions/workflows/ci.yml/badge.svg)](https://github.com/maryam843/iot-indoor-air-quality-forecasting/actions/workflows/ci.yml)

An Arduino sensor node that sent 1.85 million indoor VOC, temperature and humidity readings to Arduino IoT Cloud, a tested script that turns them into a clean 1-minute dataset, and forecasting models checked against naive baselines on time-ordered splits.

## Key results

- **Data:** 1,854,356 raw readings over 14.6 days rebuilt into a 21,016-row, 1-minute dataset by joining the three sensors on the timestamp.
- **Next-minute VOC:** a Random Forest on 60 lags reaches R² 0.9709, below "repeat the last value" at 0.9886. The baseline wins.
- **VOC over 4,204 minutes (70.1 h):** ARIMA(1,1,1) has a slightly lower RMSE than persistence (0.3478 vs 0.3516), but its MAE is worse than a 5-minute moving average (0.2583 vs 0.2403). No model is clearly better than the simple baselines.
- **Next-minute humidity:** a Bayesian neural network ties with persistence (R² 0.9985 vs 0.9987 over 5 time-ordered folds); its 95% intervals cover 0.9236 of the true values.

## Hardware and dashboard

Arduino MKR WiFi 1010 with an Arduino MKR IoT Carrier (Bosch BME68x gas sensor). The board reads the sensor about every second and publishes three cloud variables to Arduino IoT Cloud. Sketch, cloud variables and API client: [`iot/README.md`](iot/README.md).

![The sensor node connected to a PC showing the live dashboard](iot/images/device.jpg)

![Arduino IoT Cloud dashboard with value widgets and live charts](iot/images/dashboard.png)

**Tools:** Python, pandas, scikit-learn, statsmodels, Prophet, PyTorch, Pyro, Arduino C++, Arduino IoT Cloud, pytest, GitHub Actions

## Data

- **Source:** own measurements from one indoor room in Qatar, exported from Arduino IoT Cloud ("download historic data"). Full description in the [data card](data/README.md).
- **Period:** 3 June 2025 00:00 to 17 June 2025 14:17 UTC (14.6 days).
- **Size:** three gzipped raw files (`data/raw/`) with 373,745 humidity, 359,436 temperature and 1,121,175 VOC readings; `data/sensors_1min.csv` with 21,016 rows.
- **Units:** °C, %RH, and VOC as a Bosch BSEC breath-VOC equivalent in ppm. VOC is an estimate, not a calibrated concentration.
- **Licence:** [CC BY 4.0](data/LICENSE).
- **Getting it:** all data is in the repo, so there is no download step. `data/sensors_1min.csv` can be rebuilt from the raw files with `python scripts/build_1min_dataset.py`.

## Approach

1. **Collect:** the firmware reads temperature, humidity and VOC about every second and publishes them to Arduino IoT Cloud. The Python API client returns at most 1,000 points per variable (about one hour), so the analysis uses the cloud's historic export.
2. **Align:** the sensors report at different rates (VOC about every 1.05 s, the others about every 3.34 s), so `scripts/build_1min_dataset.py` parses timestamps as UTC, averages each sensor per minute and joins on the timestamp, not by row. Two minutes with no reading are dropped. A pytest test checks that no reading leaks into an earlier minute.
3. **Split by time:** every split is chronological: last 20% as test, the last 100 minutes, or 5 expanding-window folds (`TimeSeriesSplit`).
4. **No look-ahead:** outlier limits and scalers are fitted on training rows only, test points are never dropped, and model inputs use minute t-1 or earlier.
5. **Baselines first:** every results table prints naive baselines on the same rows: persistence (repeat the last value), training mean, SMA(5) and the mean of the last 5 minutes.
6. **Models:** time-of-day regressions (01), ARIMA, auto-ARIMA, ETS and Prophet (02, 03), a Random Forest on 60 VOC lags plus humidity and temperature at t-1 (04), and two Bayesian neural networks in Pyro with 95% intervals (05).
7. **Reproducibility:** exact package pins for Python 3.12, fixed seeds, and a leakage-check cell at the end of every modelling notebook.

## Results

All numbers are the printed outputs of the notebooks. RMSE and MAE are in the unit of the target.

| Task (notebook) | Test set | Model | Model score | Baselines (same rows) | Verdict |
|---|---|---|---|---|---|
| VOC next minute (04) | 4,192 min | Random Forest | R² 0.9709, RMSE 0.0594 | persistence R² 0.9886, RMSE 0.0371; mean of last 5 min R² 0.9793, RMSE 0.0501 | baseline wins |
| VOC next hour, recursive (04) | last 60 min | Random Forest | RMSE 0.0835, MAE 0.0735 | persistence RMSE 0.0816, MAE 0.0723 | baseline wins |
| VOC 1-minute, whole test set (02) | 4,204 min (70.1 h) | ARIMA(1,1,1) / ETS / Prophet | RMSE 0.3478 / 0.3624 / 0.4091; MAE 0.2583 / 0.2894 / 0.2533 | persistence RMSE 0.3516, MAE 0.2770; SMA(5) RMSE 0.3536, MAE 0.2403; train mean RMSE 0.3968, MAE 0.2445 | ARIMA has the lowest RMSE but a worse MAE than SMA(5): no clear winner |
| VOC raw readings (02) | 224,235 readings (about 2.9 days) | auto-ARIMA, picks (0,1,0) | RMSE 0.3664, MAE 0.2349 | persistence RMSE 0.3664, MAE 0.2349 | identical: the model is persistence |
| Temperature / humidity / VOC (03) | last 100 min | auto-ARIMA | RMSE 0.2094 / 0.6628 / 0.1170 | best baseline RMSE 0.2086 / 0.5353 / 0.0713 | no sensor beats its best baseline |
| Humidity next minute (05) | 5 folds | Bayesian NN (3-10-1) | R² 0.9985, RMSE 0.0757, 95% coverage 0.9236 | persistence R² 0.9987, RMSE 0.0697 | tie; useful only for the intervals |
| VOC next minute (05) | 5 folds | deep Bayesian NN (64-32-16) | R² 0.5330, RMSE 0.0621, 95% coverage 0.9998 | persistence R² 0.9610, RMSE 0.0253 | baseline wins; intervals far too wide |
| Each sensor from time of day (01) | last 20% | Linear, polynomial, Lasso, Ridge | e.g. VOC Ridge RMSE 0.393 | train mean RMSE 0.393 | no skill |

The 1-minute readings are very smooth, so "repeat the last value" is hard to beat at one minute. The test period (14 to 17 June) is also spikier than training, so long-horizon forecasts end up close to flat lines.

## Limitations

- One sensor in one room for 14.6 days, with no occupancy or HVAC data, so the results do not carry over to other rooms or seasons.
- VOC is an uncalibrated breath-VOC estimate and cannot be compared with air-quality limits.
- No model beats persistence at one minute, and the long-horizon forecasts come from a single forecast origin.
- Notebook 02 needs about 11 GB RAM and 49 minutes. CI runs lint and the build-script test only, not the notebooks.

## How to run

Python 3.12 (the pins in `requirements.txt` are exact for 3.12).

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check . && pytest -q
python scripts/build_1min_dataset.py
jupyter notebook notebooks/
```

CI installs only `pandas==2.2.3 numpy==1.26.4 -r requirements-dev.txt` and runs `ruff check .` and `pytest -q`, so tests do not need PyTorch or Prophet. The API client in `iot/api_client/` needs your own Arduino Cloud API key; see `iot/api_client/.env.example`.

## Repo structure

```
iot-indoor-air-quality-forecasting/
├── .github/workflows/ci.yml   ruff + pytest on Python 3.12
├── data/
│   ├── README.md              data card
│   ├── LICENSE                CC BY 4.0
│   ├── raw/                   humidity, temperature and VOC exports (.csv.gz)
│   ├── samples/               api_dump_sample.csv
│   └── sensors_1min.csv       21,016 rows
├── figures/                   plots written by the notebooks
├── iot/
│   ├── README.md              hardware, cloud variables, API client
│   ├── api_client/            fetch_timeseries.py, .env.example
│   ├── firmware/              air_quality_node.ino, thingProperties.h, arduino_secrets.h.example
│   └── images/                device.jpg, setup.png, dashboard.png
├── notebooks/                 01 to 05
├── scripts/build_1min_dataset.py
├── tests/test_build_1min_dataset.py
├── requirements.txt
├── requirements-dev.txt
└── LICENSE
```

## Licence and credits

- Code: [MIT](LICENSE).
- Data (everything in `data/`): [CC BY 4.0](data/LICENSE). Cite as: Maryam Mahaboob (2025), *Indoor air-quality sensor data (VOC, temperature, humidity), Arduino MKR IoT Carrier, 3-17 June 2025.*
- `iot/firmware/thingProperties.h` and the base of `air_quality_node.ino` are generated by Arduino IoT Cloud. VOC values come from Bosch's BSEC library on the MKR IoT Carrier.
