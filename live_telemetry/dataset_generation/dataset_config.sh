#!/usr/bin/env bash

###############################################################################
# Nestor Scheduler Benchmark Configuration
###############################################################################

#------------------------------------------------------------------------------
# Project Paths
#------------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(realpath "$SCRIPT_DIR/..")"

LOADER="$PROJECT_ROOT/ebpf/build/loader"

WORKLOAD_DIR="$SCRIPT_DIR/workloads"

#------------------------------------------------------------------------------
# Output Directories
#------------------------------------------------------------------------------

OUTPUT_ROOT="$SCRIPT_DIR/output"

TELEMETRY_DIR="$OUTPUT_ROOT/telemetry"
FIO_RESULTS_DIR="$OUTPUT_ROOT/fio_results"
LOG_DIR="$OUTPUT_ROOT/logs"

#------------------------------------------------------------------------------
# Storage Device
#------------------------------------------------------------------------------

DEVICE="nvme0n1"

#------------------------------------------------------------------------------
# Test File
#------------------------------------------------------------------------------

TESTFILE="/mnt/nestor-scratch/testfile"
TESTFILE_SIZE="4G"

#------------------------------------------------------------------------------
# Benchmark Parameters
#------------------------------------------------------------------------------

LOADER_STARTUP_DELAY=1
POST_WORKLOAD_DELAY=1
COOLDOWN_TIME=3

#------------------------------------------------------------------------------
# Linux I/O Schedulers
#------------------------------------------------------------------------------

SCHEDULERS=(
    none
    mq-deadline
    kyber
    bfq
)

#------------------------------------------------------------------------------
# Mode
#------------------------------------------------------------------------------

TEST_MODE="${TEST_MODE:-true}"

if [ "$TEST_MODE" = true ]; then

    RUNTIME=5
    REPEATS=1

    WORKLOAD_CLASSES=(
        seqread
    )

    BLOCK_SIZES=(
        4k
    )

    QUEUE_DEPTHS=(
        1
    )

    NUM_JOBS=(
        1
    )

else

    RUNTIME=20
    REPEATS=1

    WORKLOAD_CLASSES=(
        seqread
        seqwrite
        randread
        randwrite
        mixed_readheavy
        mixed_writeheavy
    )

    BLOCK_SIZES=(
        4k
        64k
        256k
    )

    QUEUE_DEPTHS=(
        1
        16
        64
    )

    NUM_JOBS=(
        1
        4
    )

fi