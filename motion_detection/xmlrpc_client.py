import xmlrpc.client
import cv2
import pickle
import time
from datetime import datetime

from motion_buffer import MotionBuffer

s = xmlrpc.client.ServerProxy('http://127.0.0.1:8000')
mb = MotionBuffer((100, 100), (50, 50))

while True:

    bin = s.get_camera()
    img = pickle.loads(bin.data)

    mb.add(datetime.now(), img, "")
    mb.plot()

    cv2.imshow("baseline", mb.baseline)

    cv2.imshow("img", img)
    cv2.waitKey(10)
    time.sleep(0.5)
