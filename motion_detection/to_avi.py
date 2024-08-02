import sys
import os
import cv2
import ffmpeg
import shutil


def to_avi(indir, outfile):
    working_dir = "/tmp/to_avi/"
    if os.path.exists(working_dir):
        shutil.rmtree(working_dir)
    os.makedirs(working_dir, exist_ok=True)
    for i, fn in enumerate(os.listdir(indir)):
        fn = os.path.join(indir, fn)
        print(fn)
        img = cv2.imread(fn)
        cv2.putText(img, f"{i:04}", (10, 20), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 0, 255), 1)
        cv2.putText(img, fn, (10, 40), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 0, 255), 1)
        outfn = os.path.normpath(os.path.join(working_dir, f"{i:04}.jpg"))
        cv2.imwrite(outfn, img)
        if i > 200:
            break
    ffmpeg.input(os.path.join(working_dir, "%04d.jpg"), framerate=30) \
        .output(outfile).run()


def main():

    indir = sys.argv[1]
    outfile = sys.argv[2]

    print(f"{indir} -> {outfile}")

    to_avi(indir, outfile)


if __name__ == "__main__":
    main()
