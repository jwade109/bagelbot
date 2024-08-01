import cv2
import os
import sys
import yaml
import random


indir = sys.argv[1]
outfn = sys.argv[2]

labels = {}

cx = 290
cy = 190
rx = 40
ry = 10

if os.path.exists(outfn):
    labels = yaml.safe_load(open(outfn, "r"))

candidates = []


def stack_frames(imgs):
    assert len(imgs) == 16
    imgs = [cv2.resize(im, (0, 0), fx=7, fy=7) for im in imgs]
    return cv2.vconcat([
        cv2.hconcat(imgs[0:4]),
        cv2.hconcat(imgs[4:8]),
        cv2.hconcat(imgs[8:12]),
        cv2.hconcat(imgs[12:16])])


unlabeled = []

for i, fn in enumerate(os.listdir(indir)):
    fn = os.path.join(indir, fn)
    if fn in labels:
        continue
    unlabeled.append(fn)


print(f"{len(unlabeled)} unlabeled files remain.")

for fn in unlabeled:
    print(fn)
    img = cv2.imread(fn)
    img = img[cy - ry:cy + ry, cx - rx:cx + rx]
    if baseline is None:
        baseline = img.copy()
    else:
        baseline = cv2.addWeighted(baseline, alpha, img, 1 - alpha, 0)
    cv2.imshow("img", cv2.resize(img, (0, 0), fx=8, fy=8))

    candidates.append((img, fn))

    if len(candidates) == 16:
        stacked = stack_frames([img for img, _ in candidates])
        cv2.imshow("candidate birbs", stacked)
        key = cv2.waitKey(0)
        print(key)
        if key == 109: # m - yes birb
            print("YES BIRBS")
            for _, fn in candidates:
                labels[fn] = True
        elif key == 122: # z - no birb
            print("NO BIRBS")
            for _, fn in candidates:
                labels[fn] = False
        else:
            break
        candidates = []

    cv2.waitKey(1)

yaml.safe_dump(labels, open(outfn, "w"))
print("Done.")
