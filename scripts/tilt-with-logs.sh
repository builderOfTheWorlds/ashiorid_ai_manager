#!/bin/bash
# Run Tilt with logging enabled
# This script captures all Tilt output to timestamped log files

set -e

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p tilt-logs

# Generate timestamp for log files
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
LOG_FILE="tilt-logs/tilt-output-${TIMESTAMP}.log"

# Print information
echo "=========================================="
echo "🚀 Starting Tilt with logging enabled"
echo "=========================================="
echo "Log file: $LOG_FILE"
echo "Project root: $PROJECT_ROOT"
echo ""
echo "Logs will be saved to: tilt-logs/"
echo ""
echo "To commit logs for analysis:"
echo "  git add -f $LOG_FILE"
echo "  git commit -m 'Add Tilt logs for debugging'"
echo ""
echo "Press Ctrl+C to stop Tilt"
echo "=========================================="
echo ""

# Run Tilt and capture output
# Use 'tee' to both display and save logs
# The '-a' flag appends to the log file
# 2>&1 redirects stderr to stdout so both are captured
echo "Starting Tilt at $(date)" | tee "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Run tilt up and capture all output
tilt up 2>&1 | tee -a "$LOG_FILE"

# Capture exit status
EXIT_STATUS=$?

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Tilt stopped at $(date)" | tee -a "$LOG_FILE"
echo "Exit status: $EXIT_STATUS" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE" | tee -a "$LOG_FILE"

exit $EXIT_STATUS
