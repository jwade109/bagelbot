import cv2
import numpy as np
from collections import deque
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from dataclasses import dataclass
from scipy.ndimage import gaussian_filter1d


def compute_motion(curr, prev):
    cv2.imshow("curr", cv2.resize(curr, (0, 0), fx=8, fy=8, interpolation=cv2.INTER_NEAREST))
    curr = cv2.GaussianBlur(curr, (7, 7), 0)
    prev = cv2.GaussianBlur(prev, (7, 7), 0)
    d1 = cv2.subtract(curr, prev)
    d2 = cv2.subtract(prev, curr)
    d1 = cv2.cvtColor(d1, cv2.COLOR_BGR2GRAY)
    d2 = cv2.cvtColor(d2, cv2.COLOR_BGR2GRAY)
    _, d1 = cv2.threshold(d1, 30, 255, cv2.THRESH_BINARY)
    _, d2 = cv2.threshold(d2, 30, 255, cv2.THRESH_BINARY)
    d3 = np.zeros(d1.shape, np.uint8)
    diff = cv2.merge([d3, d1, d2])
    norm = np.linalg.norm(diff)
    cv2.imshow("diff", cv2.resize(diff, (0, 0), fx=8, fy=8))
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
    kf_x: np.ndarray
    kf_p: np.ndarray


class Kalman1D:
    def __init__(self):
        self.n = 3
        self.x = np.zeros((self.n, 1))
        self.P = np.eye(self.n) * 0.01
        self.F = np.eye(self.n)
        self.F[0, 1] = 1
        self.F[0, 2] = 0.5
        self.F[1, 2] = 1
        self.H = np.array([[1, 0, 0]])
        self.Q = np.eye(self.n)
        self.Q[0, 0] = 1E-3
        self.Q[1, 1] = 1E-8
        self.Q[2, 2] = 1E-7
        self.R = np.reshape(np.array([5]), (1, 1))

    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.transpose() + self.Q

    def update(self, pos):
        z = np.array([pos])
        y = z - np.dot(self.H, self.x)
        S = self.R + np.dot(self.H, np.dot(self.P, self.H.T))
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        I = np.eye(self.n)
        self.P = np.dot(np.dot(I - np.dot(K, self.H), self.P),
        	(I - np.dot(K, self.H)).T) + np.dot(np.dot(K, self.R), K.T)


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
        self.kf = Kalman1D()
        self.csv = open("scores.csv", "w")
        self.csv.write("stamp,score\n")

    def sample(self, img):
        if not self.center or not self.dims:
            return img
        cx, cy = self.center
        rx, ry = self.dims
        return img[cy - ry:cy + ry, cx - rx:cx + rx]

    def add(self, timestamp, curr, desc):

        self.baseline_alpha = min(self.baseline_alpha + 0.1, 0.8)

        drop_all_before(self.metadata,   timestamp - timedelta(seconds=300))
        drop_all_before(self.boundaries, timestamp - timedelta(seconds=300))

        if self.baseline is None:
            self.baseline = self.sample(curr)
        else:
            self.baseline = cv2.addWeighted(self.baseline,
                self.alpha, self.sample(curr), 1 - self.alpha, 0)

        cv2.imshow("baseline", cv2.resize(self.baseline, (0, 0), fx=8, fy=8,
            interpolation=cv2.INTER_NEAREST))

        c = curr.copy()
        cx, cy = self.center
        rx, ry = self.dims
        cv2.rectangle(c, (cx - rx, cy - ry), (cx + rx, cy + ry), (255, 0, 0), 1)
        cv2.imshow('current', c)
        c = self.sample(curr)
        score = compute_motion(c, self.baseline)

        self.csv.write(f"{timestamp.timestamp()},{score:0.6f}")

        self.kf.predict()
        self.kf.update(score)

        if self.baseline_diff is None:
            self.baseline_diff = score
        else:
            self.baseline_diff = self.baseline_diff * self.baseline_alpha + \
                score * (1 - self.baseline_alpha)
        frame = MotionFrame(timestamp, desc, score, self.baseline_diff, self.kf.x, self.kf.P.tolist())
        self.metadata.append((timestamp, frame))

    def plot(self):

        if not self.metadata:
            return

        t = np.array([t for t, _ in self.metadata])
        y = np.array([x.raw_score for _, x in self.metadata])
        b = np.array([x.baseline for _, x in self.metadata])
        k = np.array([x.kf_x[0] for _, x in self.metadata])
        v = np.array([x.kf_x[1] * 20 for _, x in self.metadata])
        a = np.array([x.kf_x[2] * 20 for _, x in self.metadata])
        p = np.reshape(np.array([x.kf_p[0][0] for _, x in self.metadata]), (len(t), 1))
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
        # plt.plot(t, b, label="Baseline")
        # plt.plot(t, k, label="Kalman")
        # plt.plot(t, k.flatten() - y.flatten(), label="Deviation")
        # if td:
        #     plt.plot(td, d, label="Raw - Baseline")
        plt.legend()
        plt.grid()

        plt.pause(0.02)
