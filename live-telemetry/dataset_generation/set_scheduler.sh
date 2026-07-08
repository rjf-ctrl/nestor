#!/usr/bin/env bash
set -euo pipefail

source ./dataset_config.sh

###############################################################################
# Usage:
#
#   ./set_scheduler.sh none
#   ./set_scheduler.sh mq-deadline
#   ./set_scheduler.sh kyber
#   ./set_scheduler.sh bfq
###############################################################################

if [ $# -ne 1 ]; then
    echo "Usage: $0 <scheduler>"
    exit 1
fi

SCHEDULER="$1"

SCHEDULER_FILE="/sys/block/$DEVICE/queue/scheduler"

if [ ! -f "$SCHEDULER_FILE" ]; then
    echo "Error: $SCHEDULER_FILE not found."
    exit 1
fi

AVAILABLE=$(tr -d '[]' < "$SCHEDULER_FILE")

if ! echo "$AVAILABLE" | grep -qw "$SCHEDULER"; then
    echo "Error: Scheduler '$SCHEDULER' is not available."
    echo
    echo "Available schedulers:"
    cat "$SCHEDULER_FILE"
    exit 1
fi

echo "Switching scheduler to: $SCHEDULER"

echo "$SCHEDULER" | sudo tee "$SCHEDULER_FILE" > /dev/null

CURRENT=$(cat "$SCHEDULER_FILE")

echo "Current scheduler:"
echo "  $CURRENT"

echo "Scheduler successfully switched."