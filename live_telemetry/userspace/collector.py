#!/usr/bin/env python3

"""
Nestor Telemetry Collector

Thin wrapper around the eBPF loader.

Responsibilities
----------------
- Launch the eBPF loader
- Collect telemetry for a fixed duration
- Stop collection
- Return the generated CSV path
"""

from pathlib import Path
import subprocess
import signal
import time
import pandas as pd

class TelemetryCollector:

    def __init__(self):

        # live-telemetry/userspace/
        self.root = Path(__file__).resolve().parent

        # loader.c resolves collector.bpf.o relative to its OWN executable
        # directory (via /proc/self/exe), and the Makefile builds both
        # collector.bpf.o and loader into ebpf/build/ together. The loader
        # binary must stay there, not in userspace/, or it won't find its
        # BPF object.
        self.loader = self.root.parent / "ebpf" / "build" / "loader"

        # Default output for CLI
        self.output_csv = Path("/tmp/nestor/live.csv")

        self.process = None

    def collect(
        self,
        device: str,
        workload_class: str | None = None,
        duration: int = 20,
    ) -> Path:
        """
        Collect telemetry for 'duration' seconds.

        Parameters
        ----------
        device : str
            Block device (e.g. nvme0n1)

        workload_class : str | None
            Optional label. Used only during dataset generation.

        duration : int
            Collection time in seconds.

        Returns
        -------
        pathlib.Path
            Path to generated telemetry CSV.
        """

        if not self.loader.exists():
            raise FileNotFoundError(
                f"Loader not found: {self.loader}"
            )

        # Ensure output directory exists
        self.output_csv.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Remove stale file
        if self.output_csv.exists():
            self.output_csv.unlink()

        command = [
            str(self.loader),
            device,
            workload_class or "",
            str(self.output_csv),
        ]

        print(f"Collecting telemetry from {device}...")
        print(f"Sampling for {duration} seconds...\n")

        self.process = subprocess.Popen(command)

        try:
            time.sleep(duration)

        finally:
            self.stop()

        if not self.output_csv.exists():
            raise RuntimeError(
                "Telemetry collection failed. No CSV was generated."
            )

        return self.output_csv

    def stop(self):
        """
        Gracefully stop the running loader.
        """

        if self.process is None:
            return

        if self.process.poll() is None:

            self.process.send_signal(signal.SIGINT)

            try:
                self.process.wait(timeout=5)

            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

        self.process = None
    
    def collect_dataframe(
        self,
        device,
        workload_class=None,
        duration=20,
    ):
        """
        Collect telemetry and return it as a pandas DataFrame.
        """

        csv = self.collect(
            device=device,
            workload_class=workload_class,
            duration=duration,
        )

        return pd.read_csv(csv)