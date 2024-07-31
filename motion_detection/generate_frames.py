import sys
import cv2
import os
from datetime import datetime
import time

DUR = 1

outdir = sys.argv[1]

os.makedirs(sys.argv[1], exist_ok=True)

def main():

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    while True:

        ret, frame = cap.read()
        if not ret:
            print("Can't receive frame.")
            return 1

        now = datetime.now()
        fn = now.strftime("%Y-%m-%dT%H-%M-%S.%f")

        cv2.imshow("frame", frame)
        cv2.imwrite(os.path.join(outdir, f"cap-picam-test-dataset-{fn}.jpg"), frame)
        cv2.waitKey(1)

        time.sleep(1)


if __name__ == "__main__":
    main()
