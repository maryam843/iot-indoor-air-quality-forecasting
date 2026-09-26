# Data card

Indoor air-quality readings from one Arduino sensor node, collected by the authors (Maryam Mahaboob) for a university course project.

## Source

| | |
|---|---|
| Device | Arduino MKR WiFi 1010 + Arduino MKR IoT Carrier. Sensor: Bosch BME68x gas sensor on the carrier. |
| Location | Indoors, a university computer lab in Qatar. The room is not given on purpose. |
| Collection | Arduino IoT Cloud, exported with "download historic data" on 17 June 2025 |
| Period | 3 June 2025 00:00:00 UTC → 17 June 2025 14:17:54 UTC (14.6 days) |
| Time zone | All timestamps are UTC (Qatar local time is UTC+3) |

## Files

| File | Rows | Columns | Notes |
|---|---|---|---|
| `raw/humidity_raw.csv.gz` | 373,745 | `time`, `value` | Relative humidity, %RH. One reading about every 3.34 s. |
| `raw/temperature_raw.csv.gz` | 359,436 | `time`, `value` | Temperature, °C. About every 3.34 s. |
| `raw/voc_raw.csv.gz` | 1,121,175 | `time`, `value` | VOC. About every 1.05 s. |
| `sensors_1min.csv` | 21,016 | `time`, `humidity`, `temperature`, `VOC` | Built by `scripts/build_1min_dataset.py`: 1-minute means per sensor, joined on the timestamp, minutes with a missing sensor dropped. |
| `samples/api_dump_sample.csv` | 1,700 | `timestamp`, `humidity`, `temperature`, `volatileOrganicCompounds` | Output of `iot/api_client/fetch_timeseries.py` on 10 June 2025, 15:41–16:39 UTC. Exactly 1,000 values per variable (the API limit), blanks where a sensor had no reading at that timestamp. Not used for modelling. |

Raw timestamps are ISO 8601 with nanoseconds and a `Z` suffix, e.g. `2025-06-03T00:00:00.150610304Z`. There are 1.85 million raw readings in total.

## Units

- **Temperature:** °C
- **Humidity:** % relative humidity
- **VOC:** the value from Bosch's BSEC library, reported in ppm. It is a breath-VOC *equivalent* estimate, **not a calibrated concentration**. Use it for trends, not for comparing with air-quality limits.

## Summary of `sensors_1min.csv`

| | humidity (%RH) | temperature (°C) | VOC (ppm-eq.) |
|---|---|---|---|
| mean | 40.14 | 23.78 | 0.665 |
| std | 2.75 | 0.34 | 0.221 |
| min | 34.61 | 22.99 | 0.490 |
| max | 51.99 | 26.18 | 2.906 |

## Known issues

- **VOC repeats:** VOC is sent every second but the sensor only updates about every 3 s, so about 67 % of raw VOC readings are the same as the previous one.
- **Spikes:** VOC has short spikes up to 4.74 in the raw data (e.g. 3 June around 14:20 UTC). About 3 % of raw VOC readings are more than 3 standard deviations from the mean. They are kept in the files.
- **Gaps:** there are no missing values, but there are short gaps between readings. The largest is 133 s. Two minutes (12 June 08:56 and 16 June 12:19 UTC) have no reading from any sensor, so `sensors_1min.csv` has 21,016 rows instead of 21,018.
- **Partial last day:** 17 June stops at 14:17 UTC.
- **One room, two weeks:** the data covers one indoor space for 14.6 days, so daily patterns have only about 14 repetitions.
- **Old `processed_data.csv` (not included):** during the course project we used a file called `processed_data.csv` (3–7 June, 7,005 rows). Its temperature and VOC columns were correct, but its humidity column was **not aligned in time**: it held humidity from the whole 14.6 days squeezed into 4.9 days of rows, about 3.1 %RH off on average. That file is **not used in this repo**. `sensors_1min.csv` replaces it. The saved outputs in notebooks 03 and 04 still come from the old file (see the note at the top of each notebook). The misaligned humidity affected the auto-ARIMA humidity score in notebook 03 and the Random Forest in notebook 04, which uses humidity and temperature as inputs alongside the VOC lags. Because the old file covered only 3–7 June and the notebooks now read all of 3–17 June, every score from notebooks 03 and 04 will change when re-run. The last cell of notebook 02 also read the old file, but it uses only VOC and only plots a forecast.

## Licence

The data in this folder is licensed under **Creative Commons Attribution 4.0 (CC BY 4.0)**: https://creativecommons.org/licenses/by/4.0/

Please cite as: Maryam Mahaboob (2025), *Indoor air-quality sensor data (VOC, temperature, humidity), Arduino MKR IoT Carrier, 3–17 June 2025.*
