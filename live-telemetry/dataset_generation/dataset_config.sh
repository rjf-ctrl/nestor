#!/usr/bin/env bash

# Nestor Dataset Generation Configuration
###############################################################################

#------------------------------------------------------------------------------
# Project Paths

# Root directory of the live-telemetry project
PROJECT_ROOT="$HOME/nestor/live-telemetry"

# Userspace collector executable
LOADER="$PROJECT_ROOT/ebpf/build/loader"

# Directory containing fio workload templates
WORKLOAD_DIR="$PROJECT_ROOT/workloads/templates"

#------------------------------------------------------------------------------
# Storage Device

# Block device to monitor
DEVICE="nvme0n1"

#------------------------------------------------------------------------------
# Test File

# File used by fio for workload generation
TESTFILE="/mnt/nestor-scratch/testfile"

# Size of the generated test file
TESTFILE_SIZE="4G"

#------------------------------------------------------------------------------
# Dataset Generation Parameters

# Number of times to repeat every workload configuration
REPEATS=1

# Runtime (seconds) of each workload execution
RUNTIME=20

# Wait after starting the collector before launching fio
LOADER_STARTUP_DELAY=1

# Wait after fio finishes before stopping the collector
POST_WORKLOAD_DELAY=1

# Cooldown period between workload runs
COOLDOWN_TIME=3

#------------------------------------------------------------------------------
# Workload Classes

WORKLOAD_CLASSES=(
                 mixed_readheavy
                 mixed_writeheavy)

#------------------------------------------------------------------------------
# Parameter Sweep


# Block sizes to evaluate
BLOCK_SIZES=(4k
             16k
             64k
             128k)

# Queue depths to evaluate
QUEUE_DEPTHS=(1
              4
              16
              32)

# Number of concurrent fio jobs
NUM_JOBS=(1
          2
          4)

###############################################################################
# Expected Dataset Size (Approximate)
#
# 6 workload classes
# × 4 block sizes
# × 4 queue depths
# × 3 job counts
# × REPEATS
#
# = 288 × REPEATS workload executions
#
# Each 20-second run produces roughly 17–18 usable telemetry windows
# after discarding warm-up and cooldown periods.
###############################################################################