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
    "repeat",
    "scheduler"
]

# Collapse the 84 telemetry samples into one benchmark result
summary = (
    df.groupby(experiment_cols)
      .agg(
          throughput_mb=("throughput_mb", "first"),
          fio_latency_us=("fio_latency_us", "first")
      )
      .reset_index()
)

# Remove scheduler from grouping to compare schedulers
compare_cols = [
    "workload_class",
    "block_size",
    "queue_depth",
    "num_jobs",
    "repeat"
]

margins = []

print("=" * 70)
print("PER-EXPERIMENT WINNERS")
print("=" * 70)

for config, group in summary.groupby(compare_cols):

    group = group.sort_values(
        by="throughput_mb",
        ascending=False
    ).reset_index(drop=True)

    best = group.iloc[0]
    second = group.iloc[1]

    margin = (
        (best["throughput_mb"] - second["throughput_mb"])
        / second["throughput_mb"]
    ) * 100

    margins.append({
        "winner": best["scheduler"],
        "runner_up": second["scheduler"],
        "winner_tp": best["throughput_mb"],
        "runner_tp": second["throughput_mb"],
        "margin_percent": margin,
        "winner_latency": best["fio_latency_us"],
        "runner_latency": second["fio_latency_us"],
        "latency_diff_percent":
        (
            (second["fio_latency_us"] - best["fio_latency_us"])
            / second["fio_latency_us"]
        ) * 100
    })

margins = pd.DataFrame(margins)

print()
print("=" * 70)
print("Margin Statistics")
print("=" * 70)
print(margins["margin_percent"].describe())

print()
print("=" * 70)
print("Close Decisions")
print("=" * 70)

for threshold in [1, 2, 5, 10]:

    count = (margins["margin_percent"] < threshold).sum()

    print(
        f"< {threshold:2d}% : "
        f"{count:3d} / {len(margins)} "
        f"({100*count/len(margins):.1f}%)"
    )

print()
print("=" * 70)
print("20 Smallest Margins")
print("=" * 70)

print(
    margins.sort_values("margin_percent")
           .head(20)
           .to_string(index=False)
)