#! /usr/bin/env python3

import sys
import cv2
import os
import random
import numpy as np
import logging


log = logging.getLogger("gritty")
log.setLevel(logging.DEBUG)


CASCADE_PATH = "/home/pi/bagelbot/misc/haarcascade_frontalface_default.xml"
GRITTY_PICS_DIR = "/home/pi/bagelbot/media/gritty_pics/"


def get_gritty_pic():
    path = random.choice(os.listdir(GRITTY_PICS_DIR))
    path = GRITTY_PICS_DIR + "/" + path
    log.debug(f"Selecting image at {path}.")
    return cv2.imread(path, -1)


def do_gritty(image_path, output_path, opts = {}):

    cascade = cv2.CascadeClassifier(CASCADE_PATH)
    image = cv2.imread(image_path, -1)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

    if "scale" not in opts:
        opts["scale"] = 1.2
    if "neighbors" not in opts:
        opts["neighbors"] = 6
    if "size" not in opts:
        opts["size"] = 50

    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=opts["scale"],
        minNeighbors=opts["neighbors"],
        minSize=(opts["size"], opts["size"]),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    log.debug(f"Found {len(faces)} faces.")

    if not len(faces):
        return False

    # Draw a rectangle around the faces
    for (x, y, w, h) in faces:
        grit = get_gritty_pic()
        grit = cv2.cvtColor(grit, cv2.COLOR_BGR2BGRA)
        mask = np.zeros((w, h), np.uint8)
        cv2.ellipse(mask, (int(w/2), int(h/2)), (int(w/2), int(h/2)), 0, 0, 360, 255, cv2.FILLED)
        grit = cv2.resize(grit, (w, h))
        subset = image[y:y+h,x:x+w]
        subset[mask>0] = grit[mask>0]
        image[y:y+h,x:x+w] = subset
        # image = cv2.ellipse(image, (x, y), (w, h), 0.0, 0.0, 360.0, (255, 255, 255), -1);

    cv2.imwrite(output_path, image)

    log.debug(f"Wrote to {output_path}.")

    return True
    


def main():

    if len(sys.argv) < 4:
        print("Requires image, classification, output paths.")
        return 1
    
    image_path = sys.argv[1]
    cascade_path = sys.argv[2]
    output_path = sys.argv[3]

    do_gritty(cascade_path, image_path, output_path)


if __name__ == "__main__":
    main()

