#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path

import pandas as pd


FILENAME_PATTERN = re.compile(
    r"(.+)_bs(.+)_qd(\d+)_jobs(\d+)_(.+)_r(\d+)"
)


def parse_filename(stem):
    match = FILENAME_PATTERN.fullmatch(stem)

    if not match:
        raise ValueError(f"Invalid filename: {stem}")

    return {
        "workload_class": match.group(1),
        "block_size": match.group(2),
        "queue_depth": int(match.group(3)),
        "num_jobs": int(match.group(4)),
        "scheduler": match.group(5),
        "repeat": int(match.group(6)),
    }


def extract_fio_metrics(path):
    with open(path) as f:
        fio = json.load(f)

    job = fio["jobs"][0]

    read = job["read"]
    write = job["write"]

    if read["io_bytes"] > 0:
        stats = read
    else:
        stats = write

    throughput_mb = stats["bw_bytes"] / (1024 * 1024)
    latency_us = stats["clat_ns"]["mean"] / 1000

    return throughput_mb, latency_us


def main():

    parser = argparse.ArgumentParser(
        description="Merge all telemetry with fio benchmark results."
    )

    parser.add_argument(
        "--telemetry-dir",
        default="output/telemetry"
    )

    parser.add_argument(
        "--fio-dir",
        default="output/fio_results"
    )

    parser.add_argument(
        "--output",
        default="benchmark_results.csv"
    )

    args = parser.parse_args()

    telemetry_dir = Path(args.telemetry_dir)
    fio_dir = Path(args.fio_dir)

    merged = []

    telemetry_files = sorted(telemetry_dir.glob("*.csv"))

    print(f"Found {len(telemetry_files)} telemetry files.")

    for telemetry_path in telemetry_files:

        metadata = parse_filename(telemetry_path.stem)

        fio_path = fio_dir / (telemetry_path.stem + ".json")

        if not fio_path.exists():
            print(f"Skipping {telemetry_path.name} (missing JSON)")
            continue

        telemetry = pd.read_csv(telemetry_path)

        throughput, latency = extract_fio_metrics(fio_path)

        for key, value in metadata.items():
            telemetry[key] = value

        telemetry["throughput_mb"] = throughput
        telemetry["fio_latency_us"] = latency

        merged.append(telemetry)

        print(f"Merged {telemetry_path.name}")

    if not merged:
        print("No data merged.")
        return

    dataset = pd.concat(merged, ignore_index=True)

    dataset.to_csv(args.output, index=False)

    print()
    print("=" * 60)
    print("Benchmark Merge Complete")
    print("=" * 60)
    print(f"Experiments : {len(telemetry_files)}")
    print(f"Samples     : {len(dataset)}")
    print(f"Output      : {args.output}")


if __name__ == "__main__":
    main()