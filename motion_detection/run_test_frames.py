import os
import cv2
from datetime import datetime
import sys
import matplotlib.pyplot as plt
import time

from motion_buffer import MotionBuffer


RPI_BIRDFEEDER_CENTER = (290, 190)
RPI_BIRDFEEDER_RADIUS = (40, 10)


def fn_to_timestamp(fn):
    ts = fn.replace("cap-picam-big-bird-data-", "").replace(".jpg", "")
    return datetime.strptime(ts, "%Y-%m-%dT%H-%M-%S.%f")


motion_buffer = MotionBuffer(RPI_BIRDFEEDER_CENTER, RPI_BIRDFEEDER_RADIUS)

frame_dir = sys.argv[1]

for fn in os.listdir(frame_dir):
    img = cv2.imread(os.path.join(frame_dir, fn))
    ts = fn_to_timestamp(fn)

    group = motion_buffer.add(ts, img, os.path.join(frame_dir, fn))
    for t, m in group:
        print(m)
        if m.is_bird:
            img = cv2.imread(m.descriptor)
            cv2.imshow("img", img)
            cv2.waitKey(2)
    if group:
        print()


plt.show()
