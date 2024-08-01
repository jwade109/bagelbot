import os
import cv2
from datetime import datetime
import sys
import matplotlib.pyplot as plt

from motion_buffer import MotionBuffer

cx = 290
cy = 190
rx = 40
ry = 10


def fn_to_timestamp(fn):
    ts = fn.replace("cap-picam-big-bird-data-", "").replace(".jpg", "")
    return datetime.strptime(ts, "%Y-%m-%dT%H-%M-%S.%f")


motion_buffer = MotionBuffer(1, (cx, cy), (rx, ry))

frame_dir = sys.argv[1]

for fn in os.listdir(frame_dir):
    img = cv2.imread(os.path.join(frame_dir, fn))
    ts = fn_to_timestamp(fn)
    print(ts)

    motion_buffer.add(ts, img, fn)
    motion_buffer.plot()

    # cv2.waitKey(1)


plt.show()
