import os
import cv2
import sys
import matplotlib.pyplot as plt
import shutil

from motion_buffer import MotionBuffer, fn_to_timestamp
from to_avi import to_avi


RPI_BIRDFEEDER_CENTER = (290, 190)
RPI_BIRDFEEDER_RADIUS = (40, 10)


motion_buffer = MotionBuffer(RPI_BIRDFEEDER_CENTER, RPI_BIRDFEEDER_RADIUS)

frame_dir = sys.argv[1]
outdir = sys.argv[2]

if os.path.exists(outdir):
    shutil.rmtree(outdir)
os.makedirs(outdir, exist_ok=True)

event_id = 0

for fn in os.listdir(frame_dir):
    img = cv2.imread(os.path.join(frame_dir, fn))
    ts = fn_to_timestamp(fn)

    event = motion_buffer.add(ts, img, os.path.join(frame_dir, fn))
    if event:
        dirname = os.path.join(outdir, f"event-{event_id}")
        os.makedirs(dirname)
        event_id += 1
        for t, m in event:
            if m.is_bird:
                newfn = os.path.join(dirname, os.path.basename(m.descriptor))
                print(newfn)
                shutil.copyfile(m.descriptor, newfn)
        to_avi(dirname, os.path.join(dirname, "movie.mp4"))

plt.show()
