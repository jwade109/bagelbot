import time
import cv2
from datetime import datetime
import os
from motion_buffer import MotionBuffer

def main():

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    motion_buffer = MotionBuffer((200, 200), (20, 10))

    while True:

        ret, curr = cap.read()
        if not ret:
            print("Can't receive frame.")
            break

        cv2.imshow("frame", curr)

        now = datetime.now()

        group = motion_buffer.add(now, curr, None)
        for g in group:
            print(g)
        if group:
            print()

        cv2.imshow("baseline", motion_buffer.baseline)

        motion_buffer.plot()

        time.sleep(0.5)

        cv2.waitKey(1)


    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
