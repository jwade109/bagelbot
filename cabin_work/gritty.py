#! /usr/bin/env python3

import sys
import cv2
import os
import random
import numpy as np

def get_gritty_pic():
    path = "gritty_pics/" + random.choice(os.listdir("gritty_pics"))
    return cv2.imread(path, -1)

def main():

    if len(sys.argv) < 4:
        print("Requires image, classification, output paths.")
        return 1
    image_path = sys.argv[1]
    cascade_path = sys.argv[2]
    output_path = sys.argv[3]
    print(f"Image: {image_path}")
    print(f"Cascade: {cascade_path}")
    print(f"Output: {output_path}")

    cascade = cv2.CascadeClassifier(cascade_path)
    image = cv2.imread(image_path, -1)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.05,
        minNeighbors=4,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    print(f"Found {len(faces)} faces.")

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


if __name__ == "__main__":
    main()

