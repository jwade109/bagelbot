#! /usr/bin/env python3

from bs4 import BeautifulSoup
import requests

page = requests.get("https://www.youtube.com")
print(page.content)
# soup = BeautifulSoup(page.content, 'html.parser')