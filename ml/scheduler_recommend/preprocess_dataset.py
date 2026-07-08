#!/usr/bin/env python3

import sys
import pandas as pd


def main():
    if len(sys.argv) != 3:
        print("Usage: python preprocess_dataset.py <input.csv> <output.csv>")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2]

    df = pd.read_csv(input_csv)

    print("=" * 60)
    print("PREPROCESSING DATASET")
    print("=" * 60)

    # -------------------------------------------------
    # Remove constant columns
    # -------------------------------------------------
    constant_cols = [col for col in df.columns if df[col].nunique() == 1]

    if constant_cols:
        print(f"Removing constant columns: {constant_cols}")
        df.drop(columns=constant_cols, inplace=True)
    else:
        print("No constant columns found.")

    # -------------------------------------------------
    # Encode categorical features
    # -------------------------------------------------
    categorical_features = ["workload_class", "block_size"]

    for col in categorical_features:
        if col in df.columns:
            df[col] = df[col].astype("category")
            print(f"Encoded '{col}' as categorical.")

    # -------------------------------------------------
    # Encode target
    # -------------------------------------------------
    if "best_scheduler" in df.columns:
        df["best_scheduler"] = df["best_scheduler"].astype("category")
        print("Encoded 'best_scheduler' as categorical.")

    # -------------------------------------------------
    # Save cleaned dataset
    # -------------------------------------------------
    df.to_csv(output_csv, index=False)

    print("\nDone.")
    print(f"Output written to: {output_csv}")

    print("\nDataset shape:", df.shape)

    print("\nCategories:")
    for col in categorical_features + ["best_scheduler"]:
        if col in df.columns:
            print(f"\n{col}")
            print(list(df[col].cat.categories))


if __name__ == "__main__":
    main()