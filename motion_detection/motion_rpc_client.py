import xmlrpc.client
import cv2
import pickle
from datetime import datetime, timedelta
from loop_rate_limiters import RateLimiter
import time
import sys

from motion_buffer import MotionBuffer, magnify_with_max_size

RPI_BIRDFEEDER_CENTER = (300, 190)
RPI_BIRDFEEDER_RADIUS = (60, 20)

ipaddr = sys.argv[1]
port = int(sys.argv[2])

s = xmlrpc.client.ServerProxy(f"http://{ipaddr}:{port}")
mb = MotionBuffer(RPI_BIRDFEEDER_CENTER, RPI_BIRDFEEDER_RADIUS)

for method in s.system.listMethods():
    print(method)


last = None
last_bird_time = None


while True:

    now = datetime.now()

    if last:
        dt = now - last
    else:
        dt = timedelta(seconds=100)

    y_text = 40

    def put_text(img, text):
        global y_text
        cv2.putText(img, text, (20,  y_text), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 0), 5)
        cv2.putText(img, text, (20,  y_text), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 2)
        y_text += 40

    if dt > timedelta(seconds=5):
        last = now
        try:
            sno, stamp, bin = s.get_frame()
        except Exception as e:
            print(e)
            continue
        img = pickle.loads(bin.data)

        frames = mb.add(now, img, "")

        for i, f in enumerate(frames):
            print(i, f)
        if frames:
            print()

        meta = mb.metadata[-1][1]
        if meta.is_bird:
            last_bird_time = now
            cv2.imshow("bird", img)

    c = img.copy()
    cx, cy = RPI_BIRDFEEDER_CENTER
    rx, ry = RPI_BIRDFEEDER_RADIUS
    cv2.rectangle(c, (cx - rx, cy - ry), (cx + rx, cy + ry), (255, 255, 0), 1)
    c = magnify_with_max_size(c, 1800, 900)
    put_text(c, f"{now}")
    put_text(c, f"{meta.stamp}")
    put_text(c, f"last bird = {last_bird_time}")
    put_text(c, f"score = {meta.raw_score:0.2f}")
    put_text(c, f"bird = {meta.is_bird}")
    put_text(c, f"keep = {meta.keep_level}")

    cv2.imshow("baseline", magnify_with_max_size(mb.baseline, 800,  500))
    cv2.imshow("diff",     magnify_with_max_size(mb.diff,     800,  500))
    cv2.imshow("sampled",  magnify_with_max_size(mb.sampled,  800,  500))
    cv2.imshow("img",      c)
    cv2.waitKey(2)

