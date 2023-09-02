#! /usr/bin/env python3

import os
import requests
import yaml
from bblog import log
import matplotlib.pyplot as plt
from resource_paths import hashed_fn
from scipy import interpolate
import numpy as np
from state_machine import get_param


WMATA_API_KEY = get_param("WMATA_API_KEY", "")


COLORS = {
    "BL": "blue",
    "GR": "green",
    "OR": "orange",
    "RD": "red",
    "SV": "silver",
    "YL": "yellow"
}


def wmata_api_call(endpoint, **params):
    params["api_key"] = WMATA_API_KEY
    params["contentType"] = "json"
    url = f"https://api.wmata.com/{endpoint}"
    fn = hashed_fn("wmata", (url + str(params)).encode(), "yaml")
    if os.path.exists(fn):
        print(f"Loading {fn}")
        return yaml.load(open(fn, "r"))
    r = requests.get(url, params=params)
    print(f"Writing {fn}")
    yaml.dump(r.json(), open(fn, "w"))
    return r.json()


def get_train_positions():
    return wmata_api_call("TrainPositions/TrainPositions")


def get_standard_routes():
    return wmata_api_call("TrainPositions/StandardRoutes")


def get_track_circuits():
    return wmata_api_call("TrainPositions/TrackCircuits")


def get_station_list():
    return wmata_api_call("Rail.svc/json/jStations")


def get_station_predictions(stations):
    s = ",".join(stations)
    return wmata_api_call(f"StationPrediction.svc/json/GetPrediction/{s}")


stations = get_station_list()
routes = get_standard_routes()

station_map = {}

for s in stations["Stations"]:
    station_map[s["Code"]] = (s["Name"], s["Lon"], s["Lat"])


for route in routes["StandardRoutes"]:
    route_stations = []
    route_x = []
    route_y = []
    for segment in route["TrackCircuits"]:
        s = segment["StationCode"]
        if s:
            route_stations.append(s)
    for s in route_stations:
        sinfo = station_map[s]
        _, x, y = sinfo
        route_x.append(x)
        route_y.append(y)

    tck, u = interpolate.splprep([route_x, route_y], s=0)
    xi, yi = interpolate.splev(np.linspace(0, 1, 1000), tck)

    plt.plot(xi, yi, '-', linewidth=3, color=COLORS[route["LineCode"]])


for name, x, y in station_map.values():
    plt.plot(x, y, 'k.')
    # plt.annotate(name, (x, y))

plt.axis("equal")
plt.grid(True)

plt.show()
