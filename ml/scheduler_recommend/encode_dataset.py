#!/usr/bin/env python3

import sys
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import joblib
import os


def main():
    if len(sys.argv) != 3:
        print("Usage: python encode_dataset.py <input.csv> <output.csv>")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2]

    df = pd.read_csv(input_csv)

    print("=" * 60)
    print("ENCODING DATASET")
    print("=" * 60)

    encoders = {}

    categorical_columns = [
        "workload_class",
        "block_size",
        "best_scheduler",
    ]

    for col in categorical_columns:
        if col not in df.columns:
            continue

        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])

        encoders[col] = le

        print(f"\n{col}")
        for i, label in enumerate(le.classes_):
            print(f"  {label:<20} -> {i}")

    df.to_csv(output_csv, index=False)

    encoder_dir = "encoders"
    os.makedirs(encoder_dir, exist_ok=True)

    for name, encoder in encoders.items():
        joblib.dump(encoder, f"{encoder_dir}/{name}_encoder.pkl")

    print("\n" + "=" * 60)
    print("Encoding Complete")
    print("=" * 60)
    print(f"Encoded dataset : {output_csv}")
    print(f"Encoders saved  : {encoder_dir}/")


if __name__ == "__main__":
    main()
    