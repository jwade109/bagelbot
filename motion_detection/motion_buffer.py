import cv2
import numpy as np
from collections import deque
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from dataclasses import dataclass
from scipy.ndimage import gaussian_filter1d


def compute_motion(curr, prev):
    curr = cv2.GaussianBlur(curr, (7, 7), 0)
    prev = cv2.GaussianBlur(prev, (7, 7), 0)
    d1 = cv2.subtract(curr, prev)
    d2 = cv2.subtract(prev, curr)
    d1 = cv2.cvtColor(d1, cv2.COLOR_BGR2GRAY)
    d2 = cv2.cvtColor(d2, cv2.COLOR_BGR2GRAY)
    d3 = np.zeros(d1.shape, np.uint8)
    diff = cv2.merge([d3, d1, d2])
    norm = np.linalg.norm(diff)
    cv2.imshow("curr", cv2.resize(curr, (0, 0), fx=4, fy=4))
    cv2.imshow("diff", cv2.resize(diff, (0, 0), fx=4, fy=4))
    score = norm / (diff.shape[0] * diff.shape[1])
    return score


def drop_all_before(buffer, time):
    while buffer and buffer[0][0] < time:
        buffer.popleft()


RISING_EDGE = 0.1
FALLING_EDGE = 0.02


@dataclass
class MotionFrame:
    stamp: datetime
    descriptor: str
    raw_score: float
    baseline: float


class MotionBuffer:

    def __init__(self, duration, center=None, dims=None):
        self.center = center
        self.dims = dims
        self.duration = timedelta(seconds=duration)
        self.metadata = deque(maxlen=1000)
        self.boundaries = deque(maxlen=1000)
        self.is_motion = False
        self.baseline = None
        self.baseline_diff = None
        self.alpha = 0.98
        self.baseline_alpha = 0.1

    def sample(self, img):
        if not self.center or not self.dims:
            return img
        cx, cy = self.center
        rx, ry = self.dims
        return img[cy - ry:cy + ry, cx - rx:cx + rx]

    def add(self, timestamp, curr, desc):

        self.baseline_alpha = min(self.baseline_alpha + 0.03, 0.993)

        drop_all_before(self.metadata,   timestamp - timedelta(seconds=300))
        drop_all_before(self.boundaries, timestamp - timedelta(seconds=300))

        if self.baseline is None:
            self.baseline = self.sample(curr)
        else:
            self.baseline = cv2.addWeighted(self.baseline,
                self.alpha, self.sample(curr), 1 - self.alpha, 0)

        cv2.imshow("baseline", cv2.resize(self.baseline, (0, 0), fx=4, fy=4))

        c = curr.copy()
        cx, cy = self.center
        rx, ry = self.dims
        cv2.rectangle(c, (cx - rx, cy - ry), (cx + rx, cy + ry), (255, 0, 0), 1)
        cv2.imshow('current', c)
        c = self.sample(curr)
        score = compute_motion(c, self.baseline)
        if self.baseline_diff is None:
            self.baseline_diff = score
        else:
            self.baseline_diff = self.baseline_diff * self.baseline_alpha + \
                score * (1 - self.baseline_alpha)
        frame = MotionFrame(timestamp, desc, score, self.baseline_diff)
        self.metadata.append((timestamp, frame))

    def plot(self):

        if not self.metadata:
            return

        t = np.array([t for t, _ in self.metadata])
        y = np.array([x.raw_score for _, x in self.metadata])
        b = np.array([x.baseline for _, x in self.metadata])
        d = [y - b for _, y, b in zip(t, y, b) if b]
        td = [t for t, _, b in zip(t, y, b) if b]
        # g = gaussian_filter1d(b, 30)

        latest = y[-1]
        if not self.is_motion and latest > RISING_EDGE:
            print("MOTION")
            self.boundaries.append((t[-1], True))
            self.is_motion = True
        elif self.is_motion and latest < FALLING_EDGE:
            print("NO MOTION")
            self.boundaries.append((t[-1], False))
            self.is_motion = False

        plt.figure(0)
        plt.clf()
        plt.plot(t, y, label="Raw")
        plt.plot(t, b, label="Baseline")
        if td:
            plt.plot(td, d, label="Raw - Baseline")
        plt.legend()
        plt.grid()

        plt.pause(0.02)
