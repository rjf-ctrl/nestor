#!/usr/bin/env python3

import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Nestor Dataset EDA")
    parser.add_argument("csv", help="Path to cleaned dataset")
    parser.add_argument(
        "--output",
        default="eda_output",
        help="Directory to save plots"
    )

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    df = pd.read_csv(args.csv)

    numeric_cols = df.select_dtypes(include="number").columns

    print("=" * 60)
    print("Generating EDA")
    print("=" * 60)

    ###########################################################
    # Histograms
    ###########################################################

    hist_dir = os.path.join(args.output, "histograms")
    os.makedirs(hist_dir, exist_ok=True)

    for col in numeric_cols:

        plt.figure(figsize=(6,4))
        plt.hist(df[col], bins=40)

        plt.title(col)
        plt.xlabel(col)
        plt.ylabel("Count")

        plt.tight_layout()

        plt.savefig(os.path.join(hist_dir, f"{col}.png"))

        plt.close()

    ###########################################################
    # Boxplots grouped by workload
    ###########################################################

    if "workload_class" in df.columns:

        box_dir = os.path.join(args.output, "boxplots")
        os.makedirs(box_dir, exist_ok=True)

        for col in numeric_cols:

            plt.figure(figsize=(8,5))

            df.boxplot(
                column=col,
                by="workload_class",
                rot=30,
                grid=False,
                showfliers=False
            )
            
            plt.title(col)
            plt.suptitle("")

            plt.tight_layout()

            plt.savefig(os.path.join(box_dir, f"{col}.png"))

            plt.close()

    ###########################################################
    # Per-Class Feature Statistics
    ###########################################################

    if "workload_class" in df.columns:

        stats_dir = os.path.join(args.output, "statistics")
        os.makedirs(stats_dir, exist_ok=True)

        mean_df = (
            df.groupby("workload_class")[numeric_cols]
            .mean()
            .round(3)
        )

        median_df = (
            df.groupby("workload_class")[numeric_cols]
            .median()
            .round(3)
        )

        std_df = (
            df.groupby("workload_class")[numeric_cols]
            .std()
            .round(3)
        )

        print("\n============================================================")
        print("Mean Feature Values Per Workload")
        print("============================================================")
        print(mean_df)

        mean_df.to_csv(
            os.path.join(stats_dir, "feature_means.csv")
        )

        median_df.to_csv(
            os.path.join(stats_dir, "feature_medians.csv")
        )

        std_df.to_csv(
            os.path.join(stats_dir, "feature_std.csv")
        )

    ###########################################################
    # Correlation Heatmap
    ###########################################################

    corr = df[numeric_cols].corr()

    plt.figure(figsize=(12,10))

    plt.imshow(corr)

    plt.xticks(
        range(len(corr.columns)),
        corr.columns,
        rotation=90,
        fontsize=8
    )

    plt.yticks(
        range(len(corr.columns)),
        corr.columns,
        fontsize=8
    )

    plt.colorbar()

    plt.tight_layout()

    plt.savefig(os.path.join(args.output, "correlation_heatmap.png"))

    plt.close()

    ###########################################################
    # Class Distribution
    ###########################################################

    if "workload_class" in df.columns:

        counts = df["workload_class"].value_counts().sort_index()

        plt.figure(figsize=(8,4))

        plt.bar(counts.index, counts.values)

        plt.xticks(rotation=30)

        plt.ylabel("Samples")
        plt.title("Samples per Workload")

        plt.tight_layout()

        plt.savefig(os.path.join(args.output,
                                 "class_distribution.png"))

        plt.close()

    ###########################################################
    # Scatter Plots
    ###########################################################

    scatter_dir = os.path.join(args.output, "scatterplots")
    os.makedirs(scatter_dir, exist_ok=True)

    scatter_pairs = [

        ("read_iops", "write_iops"),
        ("avg_latency_us", "avg_queue_depth"),
        ("avg_request_size", "write_throughput_mb"),
        ("avg_request_size", "read_throughput_mb"),
        ("read_sequential_ratio", "read_iops"),
        ("write_sequential_ratio", "write_iops"),
    ]

    for x, y in scatter_pairs:

        if x not in df.columns or y not in df.columns:
            continue

        plt.figure(figsize=(6,5))

        if "workload_class" in df.columns:

            classes = sorted(df["workload_class"].unique())

            for cls in classes:

                subset = df[df["workload_class"] == cls]

                plt.scatter(
                    subset[x],
                    subset[y],
                    s=8,
                    alpha=0.6,
                    label=cls,
                )

            plt.legend(fontsize=8)

        else:

            plt.scatter(df[x], df[y], s=8)

        plt.xlabel(x)
        plt.ylabel(y)

        plt.tight_layout()

        plt.savefig(
            os.path.join(scatter_dir, f"{x}_vs_{y}.png")
        )

        plt.close()

    print()
    print("EDA complete.")
    print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()