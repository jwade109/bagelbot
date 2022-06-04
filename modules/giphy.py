#! /usr/bin/env python3

from state_machine import get_param
import requests
import sys
import logging

log = logging.getLogger("giphy")
log.setLevel(logging.DEBUG)


API_KEY = get_param("GIPHY_API_KEY", "")


def log_request(url, params):
    log.debug(f"Request: {url}, {params}")
    r = requests.get(url, params=params)
    return r

def gurl(endpoint):
    return f"https://api.giphy.com/v1/gifs/{endpoint}"

def get_trending():
    d = { "api_key": API_KEY }
    r = log_request(gurl("trending"), params=d)
    j = r.json()
    u = [x["embed_url"] for x in j["data"]]
    log.debug(u)
    return u

def search(search_key):
    d = { "api_key": API_KEY, "q": search_key }
    r = log_request(gurl("search"), params=d)
    j = r.json()
    u = [x["embed_url"] for x in j["data"]]
    log.debug(u)
    return u

def translate(english):
    d = { "api_key": API_KEY, "s": english, "weirdness": 3 }
    r = log_request(gurl("translate"), params=d)
    j = r.json()
    u = j["data"]["embed_url"]
    log.debug(u)
    return u

def random(tag = None):
    d = { "api_key": API_KEY }
    if tag:
        d["tag"] = tag
    r = log_request(gurl("random"), params=d)
    j = r.json()
    u = j["data"]["embed_url"]
    log.debug(u)
    return u

def main():
    print(translate(" ".join(sys.argv[1:])))
    pass


if __name__ == "__main__":
    main()
