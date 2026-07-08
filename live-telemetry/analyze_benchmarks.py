#!/usr/bin/env python3

import sys
import pandas as pd


def main():

    if len(sys.argv) != 2:
        print("Usage: python analyze_benchmarks.py benchmark_results.csv")
        sys.exit(1)

    df = pd.read_csv(sys.argv[1])

    print("=" * 70)
    print("BENCHMARK ANALYSIS")
    print("=" * 70)

    print("\nColumns:")
    print(df.columns.tolist())

    # ---------------------------------------------------------
    # Guess the performance metric
    # ---------------------------------------------------------

    candidate_metrics = [
        "throughput_mb",
        "throughput",
        "bandwidth_mb",
        "bandwidth",
        "iops",
    ]

    metric = None

    for c in candidate_metrics:
        if c in df.columns:
            metric = c
            break

    if metric is None:
        print("\nCouldn't automatically determine performance metric.")
        print("Available columns:")
        print(df.columns.tolist())
        return

    print(f"\nUsing metric: {metric}")

    # ---------------------------------------------------------
    # Find experiment identifier
    # ---------------------------------------------------------

    if "experiment_id" in df.columns:
        group_col = "experiment_id"
    else:
        group_cols = [
            c for c in df.columns
            if c != metric and c != "scheduler"
        ]

        print("\nGrouping by:")
        print(group_cols)

    margins = []
    winners = []

    if "experiment_id" in df.columns:

        grouped = df.groupby(group_col)

    else:

        grouped = df.groupby(group_cols)

    for _, group in grouped:

        group = group.sort_values(metric, ascending=False)

        if len(group) < 2:
            continue

        winner = group.iloc[0]
        second = group.iloc[1]

        margin = (
            winner[metric] - second[metric]
        ) / second[metric] * 100

        winners.append(winner["scheduler"])
        margins.append(margin)

    margins = pd.Series(margins)

    print("\n" + "=" * 70)
    print("Winning Scheduler Distribution")
    print("=" * 70)

    print(pd.Series(winners).value_counts())

    print("\n" + "=" * 70)
    print("Winning Margin Statistics (%)")
    print("=" * 70)

    print(margins.describe())

    print("\nExperiments with close finishes")

    for threshold in [1, 2, 5, 10]:

        count = (margins < threshold).sum()

        print(
            f"Margin < {threshold:2d}% : "
            f"{count:3d} / {len(margins)} "
            f"({100*count/len(margins):.1f}%)"
        )


if __name__ == "__main__":
    main()