# Tilt Logs Directory

This directory contains Tilt logs for debugging and analysis purposes.

## Purpose

Tilt logs are captured here to help diagnose issues with the development environment,
build failures, and service deployments. These logs can be committed to git for
collaborative debugging and issue analysis.

## Log Files

- `tilt-output-TIMESTAMP.log` - Full Tilt output including all service logs
- `snapshot-TIMESTAMP/` - Complete snapshot of all pod logs and cluster state

## Usage

### Option 1: Run Tilt with Automatic Logging

Start Tilt and automatically capture all output to a timestamped log file:

```bash
./scripts/tilt-with-logs.sh
```

This will:
- Start Tilt and display output in your terminal
- Save all output to `tilt-logs/tilt-output-TIMESTAMP.log`
- Continue logging until you stop Tilt (Ctrl+C)

### Option 2: Collect Logs from Running System

If Tilt is already running, collect a snapshot of all logs and status:

```bash
./scripts/collect-tilt-logs.sh
```

This will:
- Capture Tilt status and resource information
- Collect logs from all pods in ashiorid namespace
- Collect logs from infrastructure pods (postgres, redis, qdrant, etc.)
- Save Kubernetes events and pod descriptions
- Create a complete snapshot in `tilt-logs/snapshot-TIMESTAMP/`

## Committing Logs for Analysis

By default, log files are gitignored. To commit specific logs for analysis:

```bash
# Commit a specific log file
git add -f tilt-logs/tilt-output-20231107-143022.log
git commit -m "Add Tilt logs showing startup error"

# Commit an entire snapshot
git add -f tilt-logs/snapshot-20231107-143022/
git commit -m "Add complete log snapshot for debugging"

# Push to your branch
git push
```

## Log Analysis

When analyzing logs:
1. Check `tilt-status.txt` for overall system health
2. Review `pods-status.txt` for pod states
3. Examine individual `pod-*.log` files for service-specific errors
4. Check `events.txt` for Kubernetes-level issues
5. Look at `pods-describe.txt` for detailed pod information
