#! /usr/bin/env python3

import os
import requests
import yaml
import time
import matplotlib.pyplot as plt
from resource_paths import hashed_fn
from scipy.interpolate import Akima1DInterpolator
import numpy as np
from state_machine import get_param
from dataclasses import dataclass, field
from typing import List


WMATA_API_KEY = get_param("WMATA_API_KEY", "")


COLORS = {
    "BL": "blue",
    "GR": "green",
    "OR": "orange",
    "RD": "red",
    "SV": "silver",
    "YL": "yellow"
}


@dataclass()
class Train:
    id: int = 0
    no: str = 0
    cars: int = 0
    dir: int = 0
    circuit: int = 0
    dst: str = ""
    line: str = ""
    secs: int = 0
    service: str = ""


@dataclass()
class Station:
    name: str = ""
    code: str = ""
    loc: np.array = None
    lines: List[str] = field(default_factory=list)
    together: List[str] = field(default_factory=list)


@dataclass()
class CircuitPlacement:
    id: int = 0
    track: int = 0
    left_neighbors:  List[int] = field(default_factory=list)
    right_neighbors: List[int] = field(default_factory=list)


@dataclass()
class Circuit:
    id: int = 0
    seq: int = 0
    station: Station = None
    loc: np.array = None
    parameter: float = 0
    placement: CircuitPlacement = None


@dataclass()
class Route:
    code: str = ""
    stations: List[Station] = field(default_factory=list)
    circuits: List[Circuit] = field(default_factory=list)
    interp_x = None
    interp_y = None


def wmata_api_call(endpoint, cache_ok, **params):
    params["api_key"] = WMATA_API_KEY
    params["contentType"] = "json"
    url = f"https://api.wmata.com/{endpoint}"
    fn = hashed_fn("wmata", (url + str(params)).encode(), "yaml")
    if cache_ok and os.path.exists(fn):
        print(f"Loading {fn}")
        return yaml.load(open(fn, "r"))
    r = requests.get(url, params=params)
    print(f"Writing {fn}")
    yaml.dump(r.json(), open(fn, "w"))
    return r.json()


def get_train_positions():
    stuff = wmata_api_call("TrainPositions/TrainPositions", False)
    ret = []
    for s in stuff["TrainPositions"]:
        ret.append(Train(
            int(s["TrainId"]),
            s["TrainNumber"],
            int(s["CarCount"]),
            int(s["DirectionNum"]),
            int(s["CircuitId"]),
            s["DestinationStationCode"],
            s["LineCode"],
            int(s["SecondsAtLocation"]),
            s["ServiceType"]
        ))
    return ret


def get_standard_routes(stations):
    stuff = wmata_api_call("TrainPositions/StandardRoutes", True)
    ret = []
    for s in stuff["StandardRoutes"]:
        r = Route()
        r.code = s["LineCode"]
        for tc in s["TrackCircuits"]:
            c = Circuit()
            c.id = tc["CircuitId"]
            c.seq = tc["SeqNum"]
            if tc["StationCode"]:
                stat = stations[tc["StationCode"]]
                c.station = stat
                r.stations.append(stat)
            r.circuits.append(c)
        s = 0
        i = 0
        while i < len(r.circuits):
            if not r.circuits[i].station:
                i += 1
                continue
            r.circuits[i].parameter = s
            dist = 1
            found_station = False
            while i + dist < len(r.circuits):
                if r.circuits[i + dist].station:
                    found_station = True
                    break
                dist += 1
            delta = 1 / dist if found_station else 0.03
            for j in range(0, dist):
                r.circuits[i + j].parameter = s + j * delta
            s += 1
            i += 1
        for c in r.circuits:
            c.parameter /= (len(r.stations) - 1)
        ret.append(r)
    return ret


def get_circuit_placements():
    stuff = wmata_api_call("TrainPositions/TrackCircuits", True)
    ret = {}
    for c in stuff["TrackCircuits"]:
        cr = CircuitPlacement()
        cr.id = c["CircuitId"]
        cr.track = c["Track"]
        for n in c["Neighbors"]:
            side = n["NeighborType"]
            if side == "Left":
                cr.left_neighbors.extend(n["CircuitIds"])
            if side == "Right":
                cr.right_neighbors.extend(n["CircuitIds"])
        if not cr.id in ret:
            ret[cr.id] = cr
    return ret


def get_station_list():
    stuff = wmata_api_call("Rail.svc/json/jStations", True)
    ret = {}
    for s in stuff["Stations"]:
        st = Station()
        st.name = s["Name"]
        st.loc = np.array([float(s["Lon"]), float(s["Lat"])])
        st.code = s["Code"]
        for i in range(1, 5):
            k = f"LineCode{i}"
            if s[k]:
                st.lines.append(s[k])
        for i in range(1, 3):
            k = f"StationTogether{i}"
            if s[k]:
                st.together.append(s[k])
        ret[st.code] = st
    return ret


def get_station_predictions(stations):
    s = ",".join(stations)
    return wmata_api_call(f"StationPrediction.svc/json/GetPrediction/{s}", False)


def get_interpolated_path(route: Route):
    route_s = []
    route_x = []
    route_y = []
    for c in route.circuits:
        if not c.station:
            continue
        route_s.append(c.parameter)
        route_x.append(c.station.loc[0])
        route_y.append(c.station.loc[1])
    splx = Akima1DInterpolator(route_s, route_x)
    sply = Akima1DInterpolator(route_s, route_y)
    return splx, sply


def evaluate_interp(splx, sply, val):
    return splx(val), sply(val)


def construct_static_map_info():
    stations = get_station_list()
    routes = get_standard_routes(stations)
    placements = get_circuit_placements()
    for route in routes:
        for circuit in route.circuits:
            pl = placements[circuit.id]
            circuit.placement = pl
    for route in routes:
        splx, sply = get_interpolated_path(route)
        route.interp_x = splx
        route.interp_y = sply
        for c in route.circuits:
            x, y = evaluate_interp(splx, sply, c.parameter)
            c.loc = np.array([x, y])
    return routes


def run_live_updating_map(routes):

    for route in routes:
        min_p = min(c.parameter for c in route.circuits)
        max_p = max(c.parameter for c in route.circuits)
        xi, yi = evaluate_interp(route.interp_x, route.interp_y, np.linspace(min_p, max_p, 3000))
        plt.plot(xi, yi, '-', linewidth=6, color=COLORS[route.code])
        for c in route.circuits:
            plt.plot(c.loc[0], c.loc[1], 'k.', markersize=4)
        for s in route.stations:
            plt.plot(s.loc[0], s.loc[1], 'm.', markersize=9)

    plt.axis("equal")
    plt.grid(True)

    observers = {}

    handles = []

    last_update = None
    inter_update_period = 5

    while True:

        for h in handles:
            for l in h:
                l.remove()
        handles.clear()

        now = time.time()
        if not last_update or last_update + inter_update_period < now:
            trains = get_train_positions()
            update_observers(observers, trains, routes)
            last_update = now
        predict_observers(observers, now)

        for obs in observers.values():
            h = plt.plot(obs.x[0][0], obs.x[1][0], 'k^', markersize=12)
            handles.append(h)
        plt.pause(0.5)

    plt.show()


class TrainObserver:

    def __init__(self, x, y):

        self.t = None

        # state -- [x, y, vx, vy]
        self.x = np.array([[x], [y], [0], [0]])

        # state covariance
        self.P = np.identity(4) * 10

        # measurement covariance
        self.R = np.identity(2) * 0.001

        # process covariance
        self.Q = np.array([
            [1E-7, 0,    0,     0   ],
            [0,    1E-7, 0,     0   ],
            [0,    0,    1E-5,  0   ],
            [0,    0,    0,     1E-5]
        ])

        # measurement matrix -- maps state to measurement
        self.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])

    def __str__(self):
        return f"TrainObserver({self.x.T} {np.linalg.norm(self.P)})"

    def predict(self, t):
        dt = self.t - t if not self.t is None else 0
        self.t = t
        # state transition matrix
        F = np.array([
            [1, 0, dt, 0 ],
            [0, 1, 0,  dt],
            [0, 0, 1,  0 ],
            [0, 0, 0,  1 ]
        ])
        self.x = F.dot(self.x)
        self.P = F.dot(self.P.dot(F.transpose())) + self.Q

    def update(self, z):
        assert(z.shape == (2, 1))
        assert(self.H.shape == (2, 4))
        y = z - self.H.dot(self.x)
        assert(y.shape == (2, 1))
        S = self.H.dot(self.P.dot(self.H.transpose())) + self.R
        K = self.P.dot(self.H.transpose().dot(np.linalg.inv(S)))
        self.x += K.dot(y)
        self.P = (np.identity(4) - K.dot(self.H)).dot(self.P)


def get_reported_train_location(train: Train, routes: List[Route]):
    for route in routes:
        for c in route.circuits:
            if c.id == train.circuit:
                return c.loc
    return None


def update_observers(observers: dict, trains: List[Train], routes: List[Route]):
    for train in trains:
        loc = get_reported_train_location(train, routes)
        if loc is None:
            continue
        if not train.id in observers:
            observers[train.id] = TrainObserver(loc[0], loc[1])
        else:
            meas = np.array([[loc[0]], [loc[1]]])
            observers[train.id].update(meas)


def predict_observers(observers: dict, t: float):
    for tid in observers:
        observers[tid].predict(t)


def run_train_observer_sim():

    t = 0
    i = 0
    tmax = 30
    tstop = 20
    dt = 0.1
    pos = np.array([[3], [4]], dtype=float)
    vel = np.array([[1], [0.3]], dtype=float)

    train = TrainObserver(pos[0][0], pos[1][0])
    print(train)

    times = []
    actual = [[], [], [], []]
    states = [[], [], [], [], []]

    while t < tmax:

        acc = np.array([[np.sin(t/10) * 0.2], [np.cos(t/10) * 0.2]], dtype=float)

        pos += vel * dt
        vel += acc * dt

        train.predict(t)
        if i % 10 == 0 and t <= tstop:
            train.update(pos)
        t += dt
        i += 1
        print(train)
        times.append(t)

        actual[0].append(pos[0][0])
        actual[1].append(pos[1][0])
        actual[2].append(vel[0][0])
        actual[3].append(vel[1][0])
        for k in range(4):
            states[k].append(train.x[k])
        states[4].append(np.linalg.norm(train.P))

    for k in range(4):
        plt.plot(times, states[k], '-')
    # plt.plot(times, states[4], '-')
    for k in range(4):
        plt.plot(times, actual[k], '--')
    plt.axvline(tstop)
    plt.grid(True)
    plt.show()


def main():

    run_train_observer_sim()

    # routes = construct_static_map_info()
    # run_live_updating_map(routes)


if __name__ == "__main__":
    main()

