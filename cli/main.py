#!/usr/bin/env python3

import argparse

from . import __version__
from . import config
from .commands import (
    classify_command,
    recommend_command,
    apply_command,
    monitor_command,
    benchmark_command,
)


def _add_device_arg(parser):

    parser.add_argument(
        "device",
        nargs="?",
        default=config.DEFAULT_DEVICE,
        help=f"Block device (default: {config.DEFAULT_DEVICE})",
    )


def _add_duration_arg(parser):

    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=config.DEFAULT_COLLECTION_TIME,
        help="Telemetry collection duration in seconds.",
    )


def main():

    parser = argparse.ArgumentParser(
        prog="nestor",
        description="Nestor - Intelligent Linux Storage Workload Advisor",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"Nestor {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # ---------------------------------------------------------
    # classify
    # ---------------------------------------------------------

    classify = subparsers.add_parser(
        "classify",
        aliases=["c"],
        help="Classify the current storage workload.",
    )
    _add_device_arg(classify)
    _add_duration_arg(classify)
    classify.set_defaults(func=classify_command)

    # ---------------------------------------------------------
    # recommend
    # ---------------------------------------------------------

    recommend = subparsers.add_parser(
        "recommend",
        aliases=["rec", "r"],
        help="Recommend an I/O scheduler.",
    )
    _add_device_arg(recommend)
    _add_duration_arg(recommend)
    recommend.set_defaults(func=recommend_command)

    # ---------------------------------------------------------
    # apply
    # ---------------------------------------------------------

    apply_ = subparsers.add_parser(
        "apply",
        aliases=["a"],
        help="Recommend and apply the best I/O scheduler.",
    )
    _add_device_arg(apply_)
    _add_duration_arg(apply_)
    apply_.set_defaults(func=apply_command)

    # ---------------------------------------------------------
    # monitor
    # ---------------------------------------------------------

    monitor = subparsers.add_parser(
        "monitor",
        aliases=["mon", "m"],
        help="Continuously monitor and classify workload.",
    )
    _add_device_arg(monitor)
    monitor.add_argument(
        "--interval", "-i",
        type=int,
        default=config.DEFAULT_MONITOR_INTERVAL,
        help="Sampling interval in seconds.",
    )
    monitor.set_defaults(func=monitor_command)

    # ---------------------------------------------------------
    # benchmark
    # ---------------------------------------------------------

    benchmark = subparsers.add_parser(
        "benchmark",
        aliases=["bench", "b"],
        help="Run the benchmark suite to collect training data.",
    )
    _add_device_arg(benchmark)
    benchmark.set_defaults(func=benchmark_command)

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()