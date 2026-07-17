#!/usr/bin/env bash
set -euo pipefail

source ./dataset_config.sh

if [ $# -ne 6 ]; then
    echo "Usage:"
    echo "$0 workload bs qd jobs scheduler repeat"
    exit 1
fi

WORKLOAD="$1"
BS="$2"
QD="$3"
JOBS="$4"
SCHEDULER="$5"
REPEAT="$6"

mkdir -p "$TELEMETRY_DIR"
mkdir -p "$FIO_RESULTS_DIR"
mkdir -p "$LOG_DIR"

RUN_NAME="${WORKLOAD}_bs${BS}_qd${QD}_jobs${JOBS}_${SCHEDULER}_r${REPEAT}"

TELEMETRY_OUT="${TELEMETRY_DIR}/${RUN_NAME}.csv"
FIO_JSON="${FIO_RESULTS_DIR}/${RUN_NAME}.json"
LOADER_LOG="${LOG_DIR}/${RUN_NAME}.log"

rm -f nestor_dataset.csv

echo
echo "Starting collector..."

sudo "$LOADER" \
    "$DEVICE" \
    "$WORKLOAD" \
    >"$LOADER_LOG" 2>&1 &

LOADER_PID=$!

sleep "$LOADER_STARTUP_DELAY"

if ! kill -0 "$LOADER_PID" 2>/dev/null; then
    echo "Collector failed to start."
    cat "$LOADER_LOG"
    exit 1
fi

echo "Running fio..."

fio "${WORKLOAD_DIR}/${WORKLOAD}.fio" \
    --filename="$TESTFILE" \
    --bs="$BS" \
    --iodepth="$QD" \
    --numjobs="$JOBS" \
    --runtime="$RUNTIME" \
    --output-format=json \
    --output="$FIO_JSON"

sleep "$POST_WORKLOAD_DELAY"

echo "Stopping collector..."

if kill -0 "$LOADER_PID" 2>/dev/null; then
    sudo kill -INT "$LOADER_PID"
    wait "$LOADER_PID" || true
fi

if [ ! -f nestor_dataset.csv ]; then
    echo
    echo "Telemetry file not produced."
    echo "Collector log:"
    echo "----------------------------------------"
    cat "$LOADER_LOG"
    exit 1
fi

mv nestor_dataset.csv "$TELEMETRY_OUT"

echo
echo "========================================"
echo "Benchmark Complete"
echo "========================================"
echo "Workload    : $WORKLOAD"
echo "Scheduler   : $SCHEDULER"
echo "Block Size  : $BS"
echo "Queue Depth : $QD"
echo "Jobs        : $JOBS"
echo "Repeat      : $REPEAT"
echo
echo "Telemetry : $TELEMETRY_OUT"
echo "fio JSON  : $FIO_JSON"
echo