#!/usr/bin/env python3

import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Analyze Nestor dataset")
    parser.add_argument("csv", help="Path to telemetry_dataset.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)

    print("=" * 60)
    print("Nestor Dataset Analysis")
    print("=" * 60)

    print(f"\nSamples            : {len(df)}")
    print(f"Features           : {len(df.columns)}")
    print(f"Columns            :\n{list(df.columns)}")

    print("\n------------------------------")
    print("Missing Values")
    print("------------------------------")
    print(df.isnull().sum())

    print("\n------------------------------")
    print("Duplicate Rows")
    print("------------------------------")
    print(df.duplicated().sum())

    if "workload_class" in df.columns:
        print("\n------------------------------")
        print("Samples per Workload")
        print("------------------------------")
        print(df["workload_class"].value_counts().sort_index())

    print("\n------------------------------")
    print("Numeric Summary")
    print("------------------------------")
    print(df.describe())

    print("\n------------------------------")
    print("Feature Ranges")
    print("------------------------------")

    numeric = df.select_dtypes(include="number")

    for col in numeric.columns:
        print(f"{col:25s} "
              f"min={numeric[col].min():10.3f} "
              f"max={numeric[col].max():10.3f}")

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()