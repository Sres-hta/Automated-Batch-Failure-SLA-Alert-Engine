#!/usr/bin/env bash
# ==============================================================================
# Job 03: End-of-Day Settlement Engine
# Simulates a hard critical database failure:
# Exit code: 2
# Stderr: "DB Connection Timeout / Deadlock"
# ==============================================================================
set -euo pipefail

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIMESTAMP] [INFO] [EOD_SETTLE] Initializing End-of-Day Core Banking Multi-Currency Settlement Cycle..."
echo "[$TIMESTAMP] [INFO] [EOD_SETTLE] Connecting to primary Oracle Real Application Clusters (RAC) Node 02..."
sleep 0.5
echo "[$TIMESTAMP] [INFO] [EOD_SETTLE] Initiating settlement batch transaction for 23,400 accounts..."

# Emit fatal error to stderr
>&2 echo "[$TIMESTAMP] [FATAL] [EOD_SETTLE] DB Connection Timeout / Deadlock"
>&2 echo "[$TIMESTAMP] [FATAL] [EOD_SETTLE] ORA-00060: Deadlock detected while waiting for resource on table T_SETTLEMENT_BATCH_MASTER"
>&2 echo "[$TIMESTAMP] [FATAL] [EOD_SETTLE] Connection to Oracle RAC cluster terminated unexpectedly (SQLSTATE: 40001)."
>&2 echo "[$TIMESTAMP] [FATAL] [EOD_SETTLE] Batch transaction rolled back. EOD settlement phase terminated."

exit 2

