#!/bin/bash
# Collect logs from running Tilt resources
# This script captures logs from all pods and Tilt status

set -e

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p tilt-logs

# Generate timestamp for log files
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
LOG_DIR="tilt-logs/snapshot-${TIMESTAMP}"
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "📊 Collecting Tilt logs and status"
echo "=========================================="
echo "Output directory: $LOG_DIR"
echo ""

# Collect Tilt status
echo "Collecting Tilt status..."
if command -v tilt &> /dev/null; then
    tilt get all > "$LOG_DIR/tilt-status.txt" 2>&1 || echo "Failed to get Tilt status" > "$LOG_DIR/tilt-status.txt"
else
    echo "Tilt command not found" > "$LOG_DIR/tilt-status.txt"
fi

# Collect kubectl cluster info
echo "Collecting cluster info..."
kubectl cluster-info > "$LOG_DIR/cluster-info.txt" 2>&1 || echo "Failed to get cluster info" > "$LOG_DIR/cluster-info.txt"

# Get all pods in ashiorid namespace
echo "Collecting pod status..."
kubectl get pods -n ashiorid > "$LOG_DIR/pods-status.txt" 2>&1 || echo "No pods found or namespace doesn't exist" > "$LOG_DIR/pods-status.txt"

# Get all pods in default namespace (infrastructure)
kubectl get pods -n default > "$LOG_DIR/pods-status-default.txt" 2>&1 || echo "No pods found in default namespace" > "$LOG_DIR/pods-status-default.txt"

# Collect logs from all pods in ashiorid namespace
echo "Collecting pod logs..."
PODS=$(kubectl get pods -n ashiorid -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

if [ -n "$PODS" ]; then
    for POD in $PODS; do
        echo "  - $POD"
        kubectl logs -n ashiorid "$POD" --all-containers=true --tail=1000 > "$LOG_DIR/pod-${POD}.log" 2>&1 || \
            echo "Failed to get logs for $POD" > "$LOG_DIR/pod-${POD}.log"

        # Also get previous logs if pod restarted
        kubectl logs -n ashiorid "$POD" --previous --all-containers=true --tail=1000 > "$LOG_DIR/pod-${POD}-previous.log" 2>&1 || \
            echo "No previous logs for $POD" > "$LOG_DIR/pod-${POD}-previous.log"
    done
else
    echo "No pods found in ashiorid namespace" > "$LOG_DIR/no-pods.txt"
fi

# Collect logs from infrastructure pods in default namespace
echo "Collecting infrastructure logs..."
INFRA_PODS=$(kubectl get pods -n default -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

if [ -n "$INFRA_PODS" ]; then
    for POD in $INFRA_PODS; do
        echo "  - $POD (default namespace)"
        kubectl logs -n default "$POD" --all-containers=true --tail=1000 > "$LOG_DIR/infra-${POD}.log" 2>&1 || \
            echo "Failed to get logs for $POD" > "$LOG_DIR/infra-${POD}.log"
    done
fi

# Describe all pods for detailed status
echo "Collecting pod descriptions..."
kubectl describe pods -n ashiorid > "$LOG_DIR/pods-describe.txt" 2>&1 || echo "Failed to describe pods" > "$LOG_DIR/pods-describe.txt"
kubectl describe pods -n default > "$LOG_DIR/infra-pods-describe.txt" 2>&1 || echo "Failed to describe infrastructure pods" > "$LOG_DIR/infra-pods-describe.txt"

# Get events
echo "Collecting events..."
kubectl get events -n ashiorid --sort-by='.lastTimestamp' > "$LOG_DIR/events.txt" 2>&1 || echo "Failed to get events" > "$LOG_DIR/events.txt"
kubectl get events -n default --sort-by='.lastTimestamp' > "$LOG_DIR/events-default.txt" 2>&1 || echo "Failed to get default namespace events" > "$LOG_DIR/events-default.txt"

# Create a summary file
cat > "$LOG_DIR/summary.txt" <<EOF
Tilt Log Collection Summary
===========================
Timestamp: $(date)
Collection ID: ${TIMESTAMP}

Files collected:
- tilt-status.txt: Tilt resource status
- cluster-info.txt: Kubernetes cluster information
- pods-status.txt: Pod status in ashiorid namespace
- pods-status-default.txt: Pod status in default namespace
- pod-*.log: Container logs from each pod
- pod-*-previous.log: Previous logs if pod restarted
- infra-*.log: Infrastructure pod logs
- pods-describe.txt: Detailed pod information
- events.txt: Recent Kubernetes events

To commit these logs for analysis:
  git add -f $LOG_DIR
  git commit -m "Add Tilt logs snapshot ${TIMESTAMP}"
EOF

echo ""
echo "=========================================="
echo "✅ Log collection complete!"
echo "=========================================="
echo "Logs saved to: $LOG_DIR"
echo ""
echo "To commit these logs for analysis:"
echo "  git add -f $LOG_DIR"
echo "  git commit -m 'Add Tilt logs snapshot ${TIMESTAMP}'"
echo ""
cat "$LOG_DIR/summary.txt"
