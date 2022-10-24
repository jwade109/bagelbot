#! /usr/bin/env python3

import sys
import requests
from state_machine import get_param
from dataclasses import dataclass, field
from typing import List


API_KEY = get_param("YOUTUBE_API_KEY", "")
API_ROOT = "https://www.googleapis.com/youtube/v3"


@dataclass
class YoutubeVideo:
    id: str = ""
    title: str = ""
    url: str = ""
    thumbnail: str = ""


@dataclass
class Comment:
    id: str = ""
    text: str = ""
    author: str = ""


@dataclass
class CommentThread:
    id: str = ""
    video_id = str = ""
    comments: List[Comment] = field(default_factory=list)


def video_id_to_url(id):
    return f"https://youtube.com/watch?v={id}"


def parse_video_from_json(j):
    v = YoutubeVideo()
    v.title = j["snippet"]["title"]
    # v.desc = j["snippet"]["description"]
    v.id = j["id"]
    v.url = video_id_to_url(v.id)
    v.thumbnail = j["snippet"]["thumbnails"]["high"]["url"]
    return v


def parse_comment_from_json(j):
    c = Comment()
    c.id = j["id"]
    s = j["snippet"]["topLevelComment"]["snippet"]
    # c.video_id = s["videoId"]
    c.text = s["textDisplay"]
    c.author = s["authorDisplayName"]
    return c


def get_video_from_id(id):
    endpoint = f"{API_ROOT}/videos"
    params = {"id": id, "key": API_KEY, "part": "snippet"}
    r = requests.get(endpoint, params=params)
    v = parse_video_from_json(r.json()["items"][0])
    return v


def do_search(search_key) -> List[YoutubeVideo]:
    endpoint = f"{API_ROOT}/search"
    params = {"q": search_key, "key": API_KEY, "part": "snippet"}
    r = requests.get(endpoint, params=params)
    j = r.json()
    ret = []
    for result in j["items"]:
        v = parse_video_from_json(result)
        ret.append(v)
    return ret


def get_video_comments(v: YoutubeVideo):
    endpoint = f"{API_ROOT}/commentThreads"
    params = {"videoId": v.id, "key": API_KEY, "part": "snippet"}
    r = requests.get(endpoint, params=params)
    j = r.json()
    ret = []
    for result in j["items"]:
        c = parse_comment_from_json(result)
        ret.append(c)
    return ret


def get_file_info(v: YoutubeVideo):
    endpoint = f"{API_ROOT}/videos"
    params = {"id": v.id, "key": API_KEY, "part": "contentDetails "}
    r = requests.get(endpoint, params=params)
    print(r.text)


def main():

    v = get_video_from_id("P1ww1IXRfTA")
    print(v)
    get_file_info(v)

    pass

if __name__ == "__main__":
    main()
