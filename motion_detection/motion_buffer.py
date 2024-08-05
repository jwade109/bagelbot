import cv2
import numpy as np
from collections import deque
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from dataclasses import dataclass


def compute_rgb_diff(a, b, threshold=30):
    d1 = cv2.subtract(a, b)
    d2 = cv2.subtract(b, a)
    d1 = cv2.cvtColor(d1, cv2.COLOR_BGR2GRAY)
    d2 = cv2.cvtColor(d2, cv2.COLOR_BGR2GRAY)
    d3 = np.zeros(d1.shape, np.uint8)
    _, d1u = cv2.threshold(d1, threshold, 255, cv2.THRESH_BINARY)
    _, d2u = cv2.threshold(d2, threshold, 255, cv2.THRESH_BINARY)
    _, d1l = cv2.threshold(d1, threshold, 255, cv2.THRESH_BINARY_INV)
    _, d2l = cv2.threshold(d2, threshold, 255, cv2.THRESH_BINARY_INV)
    return cv2.merge([d3, d1u, d2u]), cv2.merge([d3, d1l, d2l])


def compute_motion(curr, prev):
    curr = cv2.GaussianBlur(curr, (7, 7), 0)
    prev = cv2.GaussianBlur(prev, (7, 7), 0)
    diff, noise = compute_rgb_diff(curr, prev)
    norm = np.linalg.norm(diff)
    score = norm / (diff.shape[0] * diff.shape[1])
    return score, diff


def drop_all_before(buffer, time):
    ret = []
    while buffer and buffer[0][0] < time:
        ret.append(buffer.popleft())
    return ret


def magnify_with_max_size(img, maxw, maxh):
    f1 = maxw / img.shape[1]
    f2 = maxh / img.shape[0]
    f = min(f1, f2)  # resizing factor
    dim = (int(img.shape[1] * f), int(img.shape[0] * f))
    return cv2.resize(img, dim)


def fn_to_timestamp(fn):
    ts = fn.replace("cap-picam-big-bird-data-", "").replace(".jpg", "")
    return datetime.strptime(ts, "%Y-%m-%dT%H-%M-%S.%f")


@dataclass
class MotionFrame:
    stamp: datetime
    descriptor: str
    raw_score: float
    is_bird: bool
    keep_level: int


class MotionBuffer:

    def __init__(self, center=None, dims=None):
        self.center = center
        self.dims = dims
        self.metadata = deque(maxlen=1000)
        self.baseline = None
        self.alpha = 0.98
        self.left_stamp = None
        self.diff = None
        self.sampled = None

    def sample(self, img):
        if not self.center or not self.dims:
            return img
        cx, cy = self.center
        rx, ry = self.dims
        return img[cy - ry:cy + ry, cx - rx:cx + rx]

    def get_next_zero(self):
        for i in range(len(self.metadata)):
            m = self.metadata[i][1]
            if m.stamp <= self.left_stamp:
                continue
            if m.keep_level == 0:
                return m.stamp
        return None

    def add(self, timestamp, curr, desc):

        if self.left_stamp is None:
            self.left_stamp = timestamp

        if self.baseline is None:
            self.baseline = self.sample(curr)
        else:
            self.baseline = cv2.addWeighted(self.baseline,
                self.alpha, self.sample(curr), 1 - self.alpha, 0)

        self.sampled = self.sample(curr)
        score, self.diff = compute_motion(self.sampled, self.baseline)

        is_bird = score > 0.1
        if is_bird:
            keep_level = 6
        elif not self.metadata:
            keep_level = 0
        else:
            keep_level = max(0, self.metadata[-1][1].keep_level - 1)
        frame = MotionFrame(timestamp, desc, score, is_bird, keep_level)
        self.metadata.append((timestamp, frame))

        nxt = self.get_next_zero()
        if nxt and timestamp - nxt > timedelta(seconds=60):
            self.left_stamp = nxt

        dropped = drop_all_before(self.metadata, self.left_stamp)
        if any(dr.is_bird for _, dr in dropped):
            return dropped

        return []


    def plot(self):

        if not self.metadata:
            return

        t = np.array([t for t, _ in self.metadata])
        y = np.array([x.raw_score for _, x in self.metadata])
        b = np.array([int(x.is_bird) for _, x in self.metadata])
        k = np.array([int(x.keep_level) for _, x in self.metadata])

        plt.figure(0)
        plt.clf()
        plt.plot(t, y, label="Birb")
        plt.plot(t, b, label="Is Birb")
        plt.plot(t, k, label="Keep")
        for ts, _ in self.metadata:
            plt.axvline(ts, color="grey", alpha=0.1)
        plt.axvline(self.left_stamp, color="red")
        nxt = self.get_next_zero()
        if nxt:
            plt.axvline(nxt, color="red", alpha=0.4, linestyle="--")
        plt.legend()
        plt.pause(0.02)
