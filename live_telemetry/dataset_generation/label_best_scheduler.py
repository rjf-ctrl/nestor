#!/usr/bin/env python3

import argparse

import pandas as pd


THROUGHPUT_MARGIN = 0.05


def choose_best_scheduler(group):
    """
    Choose scheduler with:
    1. Highest throughput
    2. If within 5% throughput, choose lowest latency
    """

    max_tp = group["throughput_mb"].max()

    candidates = group[
        group["throughput_mb"] >= max_tp * (1 - THROUGHPUT_MARGIN)
    ]

    winner = candidates.sort_values(
        by="fio_latency_us",
        ascending=True
    ).iloc[0]

    return winner["scheduler"]


def main():

    parser = argparse.ArgumentParser(
        description="Label best scheduler for every workload configuration."
    )

    parser.add_argument(
        "input_csv",
        help="Merged benchmark dataset"
    )

    parser.add_argument(
        "output_csv",
        help="Scheduler-labelled dataset"
    )

    parser.add_argument(
        "--margin",
        type=float,
        default=0.05,
        help="Throughput margin (default 5%%)"
    )

    args = parser.parse_args()

    global THROUGHPUT_MARGIN
    THROUGHPUT_MARGIN = args.margin

    df = pd.read_csv(args.input_csv)

    ############################################################
    # One experiment is uniquely identified by these columns
    ############################################################

    experiment_cols = [
        "workload_class",
        "block_size",
        "queue_depth",
        "num_jobs",
        "repeat",
    ]

    ############################################################
    # Determine best scheduler
    ############################################################

    labels = (
        df.groupby(experiment_cols, group_keys=False)
        .apply(choose_best_scheduler)
        .rename("best_scheduler")
        .reset_index()
    )

    ############################################################
    # Merge labels back
    ############################################################

    dataset = df.merge(
        labels,
        on=experiment_cols,
        how="left"
    )

    ############################################################
    # Remove scheduler column
    #
    # IMPORTANT:
    # We are training the model to PREDICT the scheduler.
    # Therefore the scheduler actually used during benchmarking
    # must NOT be part of the input features.
    ############################################################

    dataset = dataset.drop(
        columns=[
            "scheduler",
            "throughput_mb",
            "fio_latency_us",
        ],
        errors="ignore",
    )

    ############################################################
    # Save
    ############################################################

    dataset.to_csv(args.output_csv, index=False)

    print("=" * 60)
    print("Scheduler Labeling Complete")
    print("=" * 60)

    print()
    print("Best Scheduler Distribution")
    print("---------------------------")
    print(dataset["best_scheduler"].value_counts())

    print()
    print(f"Experiments : {len(labels)}")
    print(f"Samples     : {len(dataset)}")
    print(f"Output      : {args.output_csv}")


if __name__ == "__main__":
    main()