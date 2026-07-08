#!/usr/bin/env python3

import sys
import pandas as pd


def main():
    if len(sys.argv) != 3:
        print("Usage: python add_experiment_id.py <input.csv> <output.csv>")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2]

    df = pd.read_csv(input_csv)

    # Columns that define a unique experiment
    experiment_cols = [
        "workload_class",
        "block_size",
        "queue_depth",
        "num_jobs",
        "best_scheduler",
    ]

    # Verify required columns exist
    missing = [c for c in experiment_cols if c not in df.columns]
    if missing:
        print(f"Missing required columns: {missing}")
        sys.exit(1)

    experiment_ids = []

    current_experiment = 0
    previous_config = None

    for _, row in df.iterrows():

        current_config = tuple(row[col] for col in experiment_cols)

        if previous_config is None:
            current_experiment = 1

        elif current_config != previous_config:
            current_experiment += 1

        experiment_ids.append(current_experiment)
        previous_config = current_config

    # Insert as the first column
    df.insert(0, "experiment_id", experiment_ids)

    df.to_csv(output_csv, index=False)

    print("=" * 60)
    print("Experiment IDs Added")
    print("=" * 60)
    print(f"Experiments found : {current_experiment}")
    print(f"Samples           : {len(df)}")
    print(f"Output            : {output_csv}")

    print("\nSamples per experiment:")
    print(df["experiment_id"].value_counts().sort_index())


if __name__ == "__main__":
    main()