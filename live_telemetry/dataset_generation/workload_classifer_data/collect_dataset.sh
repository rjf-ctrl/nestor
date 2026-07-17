#!/usr/bin/env bash
set -euo pipefail

source ./dataset_config.sh

mkdir -p "$(dirname "$TESTFILE")"

echo "======================================="
echo "      Nestor Dataset Generation"
echo "======================================="

TOTAL_RUNS=0

TOTAL_EXPECTED=$(( \
    ${#WORKLOAD_CLASSES[@]} * \
    ${#BLOCK_SIZES[@]} * \
    ${#QUEUE_DEPTHS[@]} * \
    ${#NUM_JOBS[@]} * \
    REPEATS \
))

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKLOAD_DIR="$SCRIPT_DIR/workloads"

LOADER_PID=""

cleanup() {
    if [[ -n "${LOADER_PID:-}" ]]; then
        sudo kill -INT "$LOADER_PID" 2>/dev/null || true
        wait "$LOADER_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

for workload in "${WORKLOAD_CLASSES[@]}"; do
    
    TEMPLATE="$WORKLOAD_DIR/${workload}.fio"

    if [[ ! -f "$TEMPLATE" ]]; then
        echo "Missing template: $TEMPLATE"
        exit 1
    fi

    for bs in "${BLOCK_SIZES[@]}"; do
        for qd in "${QUEUE_DEPTHS[@]}"; do
            for jobs in "${NUM_JOBS[@]}"; do
                for ((rep=1; rep<=REPEATS; rep++)); do

                    TOTAL_RUNS=$((TOTAL_RUNS+1))

                    echo
                    echo "===================================================="
                    echo "Run $TOTAL_RUNS / $TOTAL_EXPECTED"
                    echo "Workload : $workload"
                    echo "BlockSize: $bs"
                    echo "QD       : $qd"
                    echo "Jobs     : $jobs"
                    echo "Repeat   : $rep/$REPEATS"
                    echo "===================================================="

                    #######################################################
                    # Prepare test file
                    #######################################################

                    ./prepare_workload.sh \
                        "$workload" \
                        "$bs" \
                        "$qd" \
                        "$jobs"

                    #######################################################
                    # Start collector
                    #######################################################


                    echo "Starting collector..."

                    sudo "$LOADER" "$DEVICE" "$workload" &

                    LOADER_PID=$!

                    sleep "$LOADER_STARTUP_DELAY"

                    if ! kill -0 "$LOADER_PID" 2>/dev/null; then
                        echo "Collector failed to start."
                        exit 1
                    fi

                    #######################################################
                    # Execute workload
                    #######################################################

                    echo "Running workload..."
                    echo "Running:"
                    echo fio "$TEMPLATE" \
                        --filename="$TESTFILE" \
                        --bs="$bs" \
                        --iodepth="$qd" \
                        --numjobs="$jobs" \
                        --runtime="$RUNTIME"


                    if ! fio "$TEMPLATE" \
                        --filename="$TESTFILE" \
                        --direct=1 \
                        --bs="$bs" \
                        --iodepth="$qd" \
                        --numjobs="$jobs" \
                        --runtime="$RUNTIME"; then

                        echo "fio failed."

                        sudo kill -INT "$LOADER_PID"
                        wait "$LOADER_PID" || true
                        LOADER_PID=""

                        exit 1
                    fi

                    #######################################################
                    # Allow collector to flush remaining events
                    #######################################################

                    sleep "$POST_WORKLOAD_DELAY"

                    #######################################################
                    # Stop collector
                    #######################################################

                    echo "Stopping collector..."

                    sudo kill -INT "$LOADER_PID"
                    wait "$LOADER_PID" || true
                    LOADER_PID=""

                    #######################################################
                    # Cooldown
                    #######################################################

                    

                done
            done
        done
    done
done

echo
echo "======================================="
echo "Dataset generation complete."
echo "Total experiments: $TOTAL_RUNS"
echo "======================================="