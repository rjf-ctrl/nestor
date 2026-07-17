#!/usr/bin/env python3

"""
Nestor CLI Configuration
"""

from pathlib import Path

# -------------------------------------------------------
# Telemetry
# -------------------------------------------------------

DEFAULT_COLLECTION_TIME = 20          # seconds
DEFAULT_MONITOR_INTERVAL = 20         # seconds

LIVE_CSV = Path("/tmp/nestor/live.csv")

# -------------------------------------------------------
# Models
# -------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

WORKLOAD_MODEL_DIR = (
    ROOT / "ml" / "workload_classifier" / "models"
)

HEURISTICS_JSON = (
    ROOT
    / "ml"
    / "workload_classifier"
    / "scheduler_heuristics.json"
)

# -------------------------------------------------------
# Default device
# -------------------------------------------------------

DEFAULT_DEVICE = "nvme0n1"