#!/usr/bin/env bash
set -euo pipefail

source ./dataset_config.sh

echo "Preparing workload..."

# Create parent directory if it doesn't exist
mkdir -p "$(dirname "$TESTFILE")"

# Remove any existing test file
rm -f "$TESTFILE"

# Ensure all pending writes are flushed
sync

# Create a fresh test file
dd if=/dev/urandom \
   of="$TESTFILE" \
   bs=1M \
   count=4096 \
   status=progress

# Flush file creation to disk
sync

# Force eviction of clean cached pages so the very next fio run can't
# be served from RAM instead of hitting the device
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# Allow the storage device to settle before the next run
sleep 1

echo "Test file ready:"
echo "  File : $TESTFILE"
echo "  Size : $TESTFILE_SIZE"