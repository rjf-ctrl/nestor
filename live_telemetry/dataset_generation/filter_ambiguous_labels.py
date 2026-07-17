#!/usr/bin/env python3

import argparse
import pandas as pd


def main():

    parser = argparse.ArgumentParser(
        description="Remove experiments whose best scheduler wins by less than a given throughput margin."
    )

    parser.add_argument(
        "benchmark_csv",
        help="benchmark_results.csv"
    )

    parser.add_argument(
        "output_csv",
        help="Filtered dataset"
    )

    parser.add_argument(
        "--margin",
        type=float,
        default=5.0,
        help="Minimum throughput margin percentage (default: 5)"
    )

    args = parser.parse_args()

    df = pd.read_csv(args.benchmark_csv)

    experiment_cols = [
        "workload_class",
        "block_size",
        "queue_depth",
        "num_jobs",
        "repeat",
    ]

    keep_experiments = []

    for config, group in df.groupby(experiment_cols):

        # One row per scheduler
        schedulers = (
            group.groupby("scheduler")
                 .agg(
                     throughput=("throughput_mb", "first")
                 )
                 .reset_index()
                 .sort_values(
                     by="throughput",
                     ascending=False
                 )
        )

        if len(schedulers) < 2:
            continue

        best = schedulers.iloc[0]["throughput"]
        second = schedulers.iloc[1]["throughput"]

        margin = ((best - second) / second) * 100

        if margin >= args.margin:
            keep_experiments.append(config)

    keep_df = pd.DataFrame(
        keep_experiments,
        columns=experiment_cols
    )

    filtered = df.merge(
        keep_df,
        on=experiment_cols,
        how="inner"
    )

    # ---------------------------------------------------
    # Regenerate labels
    # ---------------------------------------------------

    THROUGHPUT_MARGIN = 0.05

    def choose_best_scheduler(group):

        max_tp = group["throughput_mb"].max()

        candidates = group[
            group["throughput_mb"] >= max_tp * (1 - THROUGHPUT_MARGIN)
        ]

        winner = candidates.sort_values(
            by="fio_latency_us",
            ascending=True
        ).iloc[0]

        return winner["scheduler"]

    labels = (
        filtered.groupby(experiment_cols, group_keys=False)
        .apply(choose_best_scheduler)
        .rename("best_scheduler")
        .reset_index()
    )

    dataset = filtered.merge(
        labels,
        on=experiment_cols,
        how="left"
    )

    dataset = dataset.drop(
        columns=[
            "scheduler",
            "throughput_mb",
            "fio_latency_us",
        ]
    )

    dataset.to_csv(
        args.output_csv,
        index=False
    )

    print("=" * 60)
    print("AMBIGUOUS LABEL FILTERING")
    print("=" * 60)

    print(f"Margin threshold : {args.margin:.1f}%")
    print(f"Experiments kept : {len(keep_df)}")
    print(f"Experiments removed : {108-len(keep_df)}")
    print(f"Samples kept : {len(dataset)}")
    print(f"Output : {args.output_csv}")


if __name__ == "__main__":
    main()