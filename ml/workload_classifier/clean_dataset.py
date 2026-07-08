#!/usr/bin/env python3

import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Clean Nestor dataset")

    parser.add_argument("input_csv")
    parser.add_argument("output_csv")

    args = parser.parse_args()

    # Load dataset
    df = pd.read_csv(args.input_csv)

    original_rows = len(df)

    # Remove duplicates
    df = df.drop_duplicates()

    # Remove rows with missing values
    df = df.dropna()

    # Reset index
    df = df.reset_index(drop=True)

    # Save cleaned dataset
    df.to_csv(args.output_csv, index=False)

    print("=" * 60)
    print("Cleaning Complete")
    print("=" * 60)
    print(f"Original rows : {original_rows}")
    print(f"Final rows    : {len(df)}")
    print(f"Removed       : {original_rows - len(df)}")
    print(f"Saved to      : {args.output_csv}")


if __name__ == "__main__":
    main()