import urllib.parse
import requests
import asyncio
import logging
import sys


log = logging.getLogger("moonbase")
log.setLevel(logging.DEBUG)


def commit_moonbase(text, filename):
    params = {"text": text}
    q = urllib.parse.urlencode(params)
    url = "http://tts.cyzon.us/tts"
    try:
        r = requests.get(url, params, allow_redirects=True)
    except Exception as e:
        logging.error(e)
        return False, -1, str(e)
    if r.status_code != 200:
        logging.error(f"Failed with code {r.status_code}: {r.text}")
        return False, r.status_code, r.text
    open(filename, 'wb').write(r.content)
    logging.info(f"Wrote to {filename}.")
    return True, None, None


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
        format="[%(levelname)s] [%(name)s] %(message)s")
    print(commit_moonbase("john madden", "jm.wav"))
    print(commit_moonbase("john madden" * 200, "jm2.wav"))


if __name__ == "__main__":
    main()
