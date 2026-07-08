#!/usr/bin/env python3

import sys
import pandas as pd

if len(sys.argv) != 2:
    print("Usage: python analyze_label_margins.py benchmark_results.csv")
    sys.exit(1)

df = pd.read_csv(sys.argv[1])

experiment_cols = [
    "workload_class",
    "block_size",
    "queue_depth",
    "num_jobs",
    "repeat"
]

summary = (
    df.groupby(experiment_cols + ["scheduler"])
      .agg(
          throughput=("throughput_mb","first"),
          latency=("fio_latency_us","first")
      )
      .reset_index()
)

margins = []

for _, group in summary.groupby(experiment_cols):

    group = group.sort_values(
        by="throughput",
        ascending=False
    )

    best = group.iloc[0]
    second = group.iloc[1]

    margin = (
        best.throughput - second.throughput
    ) / second.throughput * 100

    margins.append(margin)

margins = pd.Series(margins)

print("="*60)
print("Winning Margin Statistics")
print("="*60)
print(margins.describe())

print()

for t in [1,2,5,10]:

    n = (margins < t).sum()

    print(f"< {t:2d}% : {n:3d} experiments ({100*n/len(margins):.1f}%)")