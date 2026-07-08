#!/usr/bin/env python3

import sys
import pandas as pd


def main():
    if len(sys.argv) != 2:
        print("Usage: python inspect_dataset.py <dataset.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    df = pd.read_csv(csv_path)

    print("=" * 60)
    print("DATASET INSPECTION REPORT")
    print("=" * 60)

    # ---------------- Basic Info ----------------
    print("\nDataset Shape")
    print("-" * 30)
    print(f"Rows    : {df.shape[0]}")
    print(f"Columns : {df.shape[1]}")

    # ---------------- Column Types ----------------
    print("\nColumn Data Types")
    print("-" * 30)
    print(df.dtypes)

    # ---------------- Missing Values ----------------
    print("\nMissing Values")
    print("-" * 30)
    missing = df.isnull().sum()

    if missing.sum() == 0:
        print("No missing values found.")
    else:
        print(missing[missing > 0])

    # ---------------- Duplicate Rows ----------------
    print("\nDuplicate Rows")
    print("-" * 30)
    duplicates = df.duplicated().sum()
    print(f"Duplicate rows: {duplicates}")

    # ---------------- Numeric Summary ----------------
    print("\nNumeric Statistics")
    print("-" * 30)
    print(df.describe())

    # ---------------- Impossible Values ----------------
    print("\nChecking for Impossible Values")
    print("-" * 30)

    checks = [
        "avg_latency_ns",
        "p50_latency_ns",
        "p95_latency_ns",
        "p99_latency_ns",
        "read_iops",
        "write_iops",
        "throughput_bytes_per_sec",
        "avg_queue_depth",
        "avg_request_size",
        "sequential_ratio"
    ]

    for col in checks:
        if col not in df.columns:
            continue

        if col == "sequential_ratio":
            bad = df[(df[col] < 0) | (df[col] > 1)]
        else:
            bad = df[df[col] < 0]

        if len(bad):
            print(f"{col}: {len(bad)} invalid values")
        else:
            print(f"{col}: OK")

    # ---------------- Label Distribution ----------------
    if "best_scheduler" in df.columns:
        print("\nScheduler Distribution")
        print("-" * 30)
        print(df["best_scheduler"].value_counts())

    print("\nInspection Complete.")


if __name__ == "__main__":
    main()