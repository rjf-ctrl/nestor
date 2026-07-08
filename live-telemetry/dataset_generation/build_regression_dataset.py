#!/usr/bin/env python3

import argparse
import os

import pandas as pd
from sklearn.preprocessing import LabelEncoder


def main():

    parser = argparse.ArgumentParser(
        description="Build regression dataset from benchmark results."
    )

    parser.add_argument(
        "input_csv",
        help="benchmark_results.csv"
    )

    parser.add_argument(
        "output_csv",
        help="regression_dataset.csv"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("BUILDING REGRESSION DATASET")
    print("=" * 60)

    df = pd.read_csv(args.input_csv)

    ############################################################
    # Collapse the 84 telemetry samples into one row
    # per (experiment, scheduler)
    ############################################################

    experiment_cols = [
        "workload_class",
        "block_size",
        "queue_depth",
        "num_jobs",
        "repeat",
        "scheduler",
    ]

    feature_cols = [
        "read_iops",
        "write_iops",
        "read_throughput_mb",
        "write_throughput_mb",
        "avg_request_size",
        "avg_latency_us",
        "read_sequential_ratio",
        "write_sequential_ratio",
        "p50_latency_us",
        "p95_latency_us",
        "p99_latency_us",
        "avg_queue_depth",
        "read_write_ratio",
        "burstiness",
        "other_iops",
        "avg_other_latency_us",
    ]

    agg = {}

    for f in feature_cols:
        agg[f] = "mean"

    agg["throughput_mb"] = "first"
    agg["fio_latency_us"] = "first"

    dataset = (
        df.groupby(experiment_cols)
          .agg(agg)
          .reset_index()
    )

    ############################################################
    # Assign experiment IDs
    ############################################################

    exp_keys = [
        "workload_class",
        "block_size",
        "queue_depth",
        "num_jobs",
        "repeat",
    ]

    experiment_table = (
        dataset[exp_keys]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    experiment_table["experiment_id"] = (
        experiment_table.index + 1
    )

    dataset = dataset.merge(
        experiment_table,
        on=exp_keys,
        how="left"
    )

    ############################################################
    # Encode categorical features
    ############################################################

    os.makedirs("encoders", exist_ok=True)

    for col in [
        "workload_class",
        "block_size",
        "scheduler",
    ]:

        encoder = LabelEncoder()

        dataset[col] = encoder.fit_transform(
            dataset[col]
        )

        pd.Series(
            encoder.classes_
        ).to_csv(
            f"encoders/{col}_encoder.csv",
            index=False,
            header=False,
        )

        print(f"\n{col}")

        for i, name in enumerate(encoder.classes_):
            print(f"  {name:<20} -> {i}")

    ############################################################
    # Save
    ############################################################

    dataset.to_csv(
        args.output_csv,
        index=False
    )

    print("\n" + "=" * 60)
    print("Done")
    print("=" * 60)

    print(f"Experiments : {dataset['experiment_id'].nunique()}")
    print(f"Rows        : {len(dataset)}")
    print(f"Schedulers  : {dataset['scheduler'].nunique()}")
    print(f"Output      : {args.output_csv}")


if __name__ == "__main__":
    main()