#!/usr/bin/env bash
set -euo pipefail

source ./dataset_config.sh

###############################################################################
# Create output directories
###############################################################################

mkdir -p "$OUTPUT_ROOT"
mkdir -p "$TELEMETRY_DIR"
mkdir -p "$FIO_RESULTS_DIR"
mkdir -p "$LOG_DIR"

###############################################################################
# Count total benchmark runs
###############################################################################

TOTAL_RUNS=$(( \
    ${#WORKLOAD_CLASSES[@]} \
    * ${#BLOCK_SIZES[@]} \
    * ${#QUEUE_DEPTHS[@]} \
    * ${#NUM_JOBS[@]} \
    * ${#SCHEDULERS[@]} \
    * REPEATS ))

CURRENT_RUN=1
START_TIME=$(date +%s)

###############################################################################

echo "==============================================="
echo "     Nestor Scheduler Benchmark"
echo "==============================================="
echo
echo "Total runs : $TOTAL_RUNS"
echo

###############################################################################
# Benchmark Loop
###############################################################################

for WORKLOAD in "${WORKLOAD_CLASSES[@]}"; do

    for BS in "${BLOCK_SIZES[@]}"; do

        for QD in "${QUEUE_DEPTHS[@]}"; do

            for JOBS in "${NUM_JOBS[@]}"; do

                ################################################################
                # Prepare workload ONCE
                ################################################################

                ./prepare_workload.sh

                ################################################################
                # Benchmark every scheduler on the SAME workload
                ################################################################

                for SCHEDULER in "${SCHEDULERS[@]}"; do

                    for ((REPEAT=1; REPEAT<=REPEATS; REPEAT++)); do
                        
                        NOW=$(date +%s)
                        ELAPSED=$((NOW - START_TIME))

                        AVG_PER_RUN=$(( ELAPSED / CURRENT_RUN ))

                        REMAINING_RUNS=$(( TOTAL_RUNS - CURRENT_RUN + 1 ))
                        ETA_SECONDS=$(( AVG_PER_RUN * REMAINING_RUNS ))

                        ETA_HOURS=$(( ETA_SECONDS / 3600 ))
                        ETA_MINUTES=$(( (ETA_SECONDS % 3600) / 60 ))

                        clear

                        echo "===================================================="
                        echo "Run        : $CURRENT_RUN / $TOTAL_RUNS"
                        echo "Workload   : $WORKLOAD"
                        echo "Scheduler  : $SCHEDULER"
                        echo "Block Size : $BS"
                        echo "QueueDepth : $QD"
                        echo "Jobs       : $JOBS"
                        echo "Repeat     : $REPEAT"
                        echo "ETA        : ${ETA_HOURS}h ${ETA_MINUTES}m"
                        echo "===================================================="
                        echo

                        ########################################################
                        # Switch scheduler
                        ########################################################

                        ./set_scheduler.sh "$SCHEDULER"

                        ########################################################
                        # Execute workload
                        ########################################################

                        ./run_workload.sh \
                            "$WORKLOAD" \
                            "$BS" \
                            "$QD" \
                            "$JOBS" \
                            "$SCHEDULER" \
                            "$REPEAT"

                        ########################################################
                        # Cooldown
                        ########################################################

                        echo
                        echo "Cooling down..."

                        sleep "$COOLDOWN_TIME"

                        ((CURRENT_RUN++))

                    done

                done

            done

        done

    done

done

###############################################################################

echo
echo "==============================================="
echo "Benchmark Complete"
echo "==============================================="
echo
echo "Total runs completed : $((CURRENT_RUN-1))"
echo