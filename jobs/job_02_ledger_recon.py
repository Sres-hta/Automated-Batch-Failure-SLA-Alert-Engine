#!/usr/bin/env python3
"""
Job 02: General Ledger Reconciliation
Simulates a transient DB lock contention failure on attempt 1,
followed by successful lock acquisition and ledger balancing on retry attempt 2.
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / ".job_02_recon_state.json"


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def determine_attempt() -> int:
    # 1. First check environment variable passed by engine
    env_attempt = os.environ.get("BATCH_ATTEMPT")
    if env_attempt is not None:
        try:
            return int(env_attempt)
        except ValueError:
            pass

    # 2. Fall back to local state file tracking
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    current_attempt = 1
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                current_attempt = data.get("attempt", 0) + 1
        except Exception:
            current_attempt = 1

    # Save state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"attempt": current_attempt, "updated_at": get_timestamp()}, f)

    return current_attempt


def main():
    attempt = determine_attempt()
    ts = get_timestamp()

    print(f"[{ts}] [INFO] [LEDGER_RECON] Starting General Ledger Reconciliation (Execution Attempt #{attempt})...")
    print(f"[{ts}] [INFO] [LEDGER_RECON] Scanning Chart of Accounts and Staged FX Feeds...")
    time.sleep(0.5)

    if attempt == 1:
        # Transient Failure: Lock contention / Resource busy
        err_msg = (
            f"[{ts}] [ERROR] [LEDGER_RECON] ORA-04021: timeout occurred while waiting to lock library object GL_BALANCES_STG\n"
            f"[{ts}] [ERROR] [LEDGER_RECON] Transient lock contention detected on table GL_BALANCES_STG (Session #290 held by ETL_LOADER).\n"
            f"[{ts}] [ERROR] [LEDGER_RECON] General ledger reconciliation aborted on attempt #{attempt}."
        )
        sys.stderr.write(err_msg + "\n")
        sys.stderr.flush()
        sys.exit(1)
    else:
        # Success on Retry
        print(f"[{ts}] [INFO] [LEDGER_RECON] Lock acquired successfully on GL_BALANCES_STG.")
        print(f"[{ts}] [INFO] [LEDGER_RECON] Reconciling 48,290 journal voucher lines across 12 branch entities...")
        print(f"[{ts}] [INFO] [LEDGER_RECON] Debit Total:  $4,281,902,110.45")
        print(f"[{ts}] [INFO] [LEDGER_RECON] Credit Total: $4,281,902,110.45")
        print(f"[{ts}] [INFO] [LEDGER_RECON] Variance: $0.00 (General Ledger is perfectly balanced).")
        print(f"[{ts}] [INFO] [LEDGER_RECON] Reconciliation completed successfully on attempt #{attempt}.")
        
        # Clean up state file on successful recovery
        if STATE_FILE.exists():
            try:
                STATE_FILE.unlink()
            except OSError:
                pass
        sys.exit(0)


if __name__ == "__main__":
    main()

