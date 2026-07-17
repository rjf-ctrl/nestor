#!/usr/bin/env python3

"""
Nestor CLI Commands
"""

import subprocess
import time

from live_telemetry.userspace.collector import TelemetryCollector
from ml.workload_classifier.predictor import WorkloadPredictor
from ml.workload_classifier.hueristics import SchedulerAdvisor

from .printer import (
    banner,
    workload,
    recommendation,
    applied,
    monitoring,
)
from .utils import require_root


collector = TelemetryCollector()
predictor = WorkloadPredictor()
advisor = SchedulerAdvisor()


# ==========================================================
# classify
# ==========================================================

def classify_command(args):

    require_root()

    banner()

    df = collector.collect_dataframe(
        device=args.device,
        duration=args.duration,
    )

    result = predictor.predict(df)

    workload(result)


# ==========================================================
# recommend
# ==========================================================

def recommend_command(args):

    require_root()

    banner()

    df = collector.collect_dataframe(
        device=args.device,
        duration=args.duration,
    )

    result = predictor.predict(df)

    recommendations = advisor.recommend(
        result["workload"]
    )

    recommendation(
        result,
        recommendations,
    )


# ==========================================================
# apply
# ==========================================================

def apply_command(args):

    require_root()

    banner()

    df = collector.collect_dataframe(
        device=args.device,
        duration=args.duration,
    )

    result = predictor.predict(df)

    recommendations = advisor.recommend(
        result["workload"]
    )

    scheduler = recommendations[0]["scheduler"]

    print(f"\nApplying scheduler: {scheduler}\n")

    subprocess.run(
        [
            "sudo",
            "sh",
            "-c",
            f"echo {scheduler} > /sys/block/{args.device}/queue/scheduler",
        ],
        check=True,
    )

    applied(scheduler)


# ==========================================================
# monitor
# ==========================================================

def monitor_command(args):

    require_root()

    banner()

    print("Press Ctrl+C to stop.\n")

    try:

        while True:

            df = collector.collect_dataframe(
                device=args.device,
                duration=args.interval,
            )
            
            if df.empty:
                print("No I/O activity detected in this window — skipping.\n")
                time.sleep(1)
                continue

            result = predictor.predict(df)

            monitoring(result)

            time.sleep(1)

    except KeyboardInterrupt:

        print("\nMonitoring stopped.")


# ==========================================================
# benchmark
# ==========================================================

def benchmark_command(args):

    require_root()

    banner()

    print("Launching benchmark suite...\n")

    subprocess.run(
        [
            "./collect_dataset.sh",
            args.device,
        ],
        check=True,
    )

    print("\nBenchmark completed.")