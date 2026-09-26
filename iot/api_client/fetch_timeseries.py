"""
Fetch the time series of an Arduino IoT Cloud Thing and save it as one wide CSV.

Version used on 10 June 2025. Known limitation: no pagination: the raw series
endpoint returns at most 1,000 points per variable, so a 10-day request returns
only the latest ~1 hour.

This is a cleaned copy of the client we used in Part A, Task 2 of the course
project. The logic is unchanged; only the credentials were moved out of the code
and into environment variables. Output of the original run: data/samples/api_dump_sample.csv

Setup:
    pip install arduino-iot-client requests-oauthlib python-dotenv
    cp .env.example .env      # then fill in your own values (never commit .env)
    python fetch_timeseries.py

TODO (not implemented, ideas for fixing the limitation above):
  * Pagination by time chunks: split [EXTRACT_FROM, EXTRACT_TO] into windows small
    enough to stay under 1,000 points (about 15 minutes for VOC at 1 s, about
    50 minutes for temperature/humidity at ~3.3 s), request each window, and
    append the results. Stop early when a window returns no points.
  * Token refresh: the access token expires after about 5 minutes. A long export
    needs to fetch a new token before it expires (or on a 401) and rebuild the
    API client with it.
  * Rate limits: replace the fixed 1 s sleep with retry and exponential backoff
    when the API answers 429.
"""

import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from time import sleep

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

import iot_api_client as iot
from iot_api_client.api import PropertiesV2Api, SeriesV2Api, ThingsV2Api
from iot_api_client.configuration import Configuration
from iot_api_client.models import BatchQueryRawRequestMediaV1, BatchQueryRawRequestsMediaV1
from iot_api_client.rest import ApiException

try:
    # Optional: load variables from a local .env file
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# === Configuration (all from environment variables) ===
HOST = "https://api2.arduino.cc"
TOKEN_URL = "https://api2.arduino.cc/iot/v1/clients/token"
CLIENT_ID = os.environ["ARDUINO_CLIENT_ID"]
CLIENT_SECRET = os.environ["ARDUINO_CLIENT_SECRET"]
ORG_ID = os.environ.get("ARDUINO_ORG_ID") or None  # optional
TARGET_THING_ID = os.environ["ARDUINO_THING_ID"]
TARGET_VAR_NAMES = None  # or e.g. ["temperature", "humidity"]
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "10"))
FILENAME = os.environ.get("OUTPUT_CSV", "dump1.csv")

# === Time window (UTC) ===
UTC_NOW = datetime.now(timezone.utc)
EXTRACT_TO = UTC_NOW.replace(microsecond=0).isoformat().replace("+00:00", "Z")
EXTRACT_FROM = (UTC_NOW - timedelta(days=RETENTION_DAYS)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# === Storage for merged time series: {timestamp: {variable: value}} ===
merged_data = defaultdict(dict)
variable_names = []


# === Auth: OAuth2 client-credentials flow ===
def get_token():
    client = BackendApplicationClient(client_id=CLIENT_ID)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url=TOKEN_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        include_client_id=True,
        audience="https://api2.arduino.cc/iot",
        headers={"X-Organization": ORG_ID} if ORG_ID else None,
    )
    return token  # never print this


def init_client(token):
    config = Configuration(HOST)
    config.access_token = token.get("access_token")
    if ORG_ID:
        return iot.ApiClient(config, header_name="X-Organization", header_value=ORG_ID)
    return iot.ApiClient(config)


# === Data fetch (one raw query per variable; returns at most 1,000 points) ===
def dump_property_data(client, thing_name, prop_name, prop_id):
    sleep(1)  # avoid rate limits
    print(f"Fetching: {thing_name}.{prop_name}")
    series_api = SeriesV2Api(client)

    property_request = BatchQueryRawRequestMediaV1(
        q=f"property.{prop_id}", var_from=EXTRACT_FROM, to=EXTRACT_TO
    )
    batch_request = BatchQueryRawRequestsMediaV1(resp_version=1, requests=[property_request])

    try:
        timeseries = series_api.series_v2_batch_query_raw(batch_request)
        variable_names.append(prop_name)
        for response in timeseries.responses:
            for time, value in zip(response.times, response.values):
                merged_data[time][prop_name] = value
    except ApiException as e:
        print(f"Error while fetching {prop_name}: HTTP {e.status}")


def get_things_and_props():
    token = get_token()
    client = init_client(token)

    things_api = ThingsV2Api(client)
    properties_api = PropertiesV2Api(client)

    try:
        thing = things_api.things_v2_show(TARGET_THING_ID)
        print(f"Found Thing: {thing.name}")

        properties = properties_api.properties_v2_list(id=TARGET_THING_ID, show_deleted=False)
        for prop in properties:
            if prop.type not in ("FLOAT", "INT"):
                continue
            if TARGET_VAR_NAMES and prop.name not in TARGET_VAR_NAMES:
                continue
            dump_property_data(client, thing.name, prop.name, prop.id)

    except ApiException as e:
        print(f"Error while listing things/properties: HTTP {e.status}")


# === Write one wide CSV: timestamp + one column per variable (blank if missing) ===
def write_merged_to_csv(filename):
    with open(filename, "w", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["timestamp"] + variable_names)
        for timestamp in sorted(merged_data.keys()):
            writer.writerow([timestamp] + [merged_data[timestamp].get(var, "") for var in variable_names])


if __name__ == "__main__":
    get_things_and_props()
    write_merged_to_csv(FILENAME)
    print(f"Data written to {FILENAME}")
