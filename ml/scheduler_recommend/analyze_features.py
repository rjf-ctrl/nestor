#!/usr/bin/env python3

import sys
import pandas as pd
import matplotlib.pyplot as plt

if len(sys.argv) != 2:
    print("Usage: python analyze_features.py dataset.csv")
    sys.exit(1)

df = pd.read_csv(sys.argv[1])

features = [
    "avg_queue_depth",
    "avg_latency_us",
    "p95_latency_us",
    "read_throughput_mb",
    "read_iops"
]

for feature in features:

    plt.figure(figsize=(8,5))

    data = [
        df[df.best_scheduler == label][feature]
        for label in sorted(df.best_scheduler.unique())
    ]

    plt.boxplot(
        data,
        tick_labels=sorted(df.best_scheduler.unique())
    )

    plt.title(feature)
    plt.ylabel(feature)

    plt.tight_layout()
    plt.savefig(f"{feature}.png", dpi=300)
    plt.close()