import pandas as pd
import sys
import matplotlib.pyplot as plt
import yaml
from datetime import datetime
import os
from motion_buffer import Kalman1D
import numpy as np


kf = Kalman1D()


infn = sys.argv[1]
labelfn = sys.argv[2]

df = pd.read_csv(infn)

labels = yaml.safe_load(open(labelfn, "r"))


def fn_to_timestamp(fn):
    ts = fn.replace("cap-picam-big-bird-data-", "").replace(".jpg", "")
    return datetime.strptime(ts, "%Y-%m-%dT%H-%M-%S.%f")


stamps = []
label_list = []

for fn, label in labels.items():
    ts = fn_to_timestamp(os.path.basename(fn))
    stamps.append(ts.timestamp())
    label_list.append(label)


kf_score = []

for score in df["score"]:
    kf.predict()
    kf.update(score)
    kf_score.append(kf.x[0])


deviation = np.array(kf_score).flatten() - df["score"]
threshold = 0.1
flag = deviation > threshold

ax = df.plot(x="stamp", y="score")
ax.plot(stamps, label_list)
ax.plot(df["stamp"], kf_score)
ax.plot(df["stamp"], deviation)
ax.plot(df["stamp"], flag)
plt.show()
