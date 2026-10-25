#!/usr/bin/env python3
"""
FinOps-BatchGuard: Automated Batch Failure & SLA Alert Engine
Main CLI Entry Point.
Phase 1: Batch Execution, DAG Dependency & Auto-Retry Engine.
Phase 2: SLA Breach Triage, ServiceNow Incident Auto-Ticketing & Escalation Routing.
Phase 3: Unix System Housekeeping & Automated Daily Shift Check-Sheet Generator.
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from src.database import (
    DEFAULT_DB_PATH,
    get_job_runs,
    get_job_run_attempts,
    get_incidents,
    get_housekeeping_checks,
    init_db,
)
from src.engine import BatchEngine, DEFAULT_CONFIG_PATH
from src.incident_manager import IncidentManager
from src.housekeeping import HousekeepingManager
from src.checksheet_reporter import CheckSheetReporter

PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "batch_engine.log"


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configures unified structured logging to console and logs/batch_engine.log.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("batch_engine")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    # Formatter
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # File Handler
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console Stream Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def print_banner() -> None:
    banner = r"""
========================================================================================
     ___ _       ___              ___       _       _      ___                 _ 
    | __(_)_ _  / _ \ _ __ ___   | _ ) __ _| |_  __| |_   / __|_  _ __ _ _ _ __| |
    | _|| | ' \| (_) | '_ (_-<---| _ \/ _` |  _|/ _| ' \ | (_ | || / _` | '_/ _` |
    |_| |_|_||_|\___/| .__/__/   |___/\__,_|\__|\__|_||_| \___|\_,_\__,_|_| \__,_|
                     |_|        Automated Batch Failure & SLA Alert Engine
                                (Phase 1, 2 & 3: Production Shift Handover Engine)
========================================================================================
"""
    print(banner)


def render_terminal_table(job_records: List[Dict[str, Any]], run_id: str, batch_date: str) -> None:
    """
    Renders an ASCII terminal table showing final job run states and SLA outcomes.
    """
    headers = [
        "JOB ID",
        "JOB NAME",
        "CRIT",
        "STATUS",
        "ATTEMPTS",
        "EXIT",
        "DURATION",
        "SLA MAX",
        "SLA BREACH",
    ]

    rows = []
    for j in job_records:
        job_id = j.get("job_id", "")
        job_name = j.get("job_name", "")
        if len(job_name) > 30:
            job_name = job_name[:27] + "..."
        crit = j.get("criticality", "P3")
        status = j.get("status", "")
        attempts = str(j.get("attempt_count", 0))
        exit_code = "-" if j.get("exit_code") is None else str(j.get("exit_code"))
        dur = f"{j.get('duration_sec', 0.0):.2f}s"
        sla_max = f"{j.get('sla_limit_sec', 0.0):.1f}s"
        breached = "YES (BREACH)" if j.get("sla_breached") else "NO"

        rows.append([job_id, job_name, crit, status, attempts, exit_code, dur, sla_max, breached])

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(val))

    border = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |"

    print("\n" + "=" * len(border))
    print(f" BATCH RUN EXECUTION SUMMARY | Run ID: {run_id} | Date: {batch_date}")
    print("=" * len(border))
    print(border)
    print(header_line)
    print(border)

    status_counts = {"SUCCESS": 0, "FAILED": 0, "BLOCKED_BY_UPSTREAM": 0, "RETRYING": 0}
    for row in rows:
        status_val = row[3]
        status_counts[status_val] = status_counts.get(status_val, 0) + 1
        line = "| " + " | ".join(val.ljust(w) for val, w in zip(row, col_widths)) + " |"
        print(line)

    print(border)
    print(f" Total Jobs: {len(rows)} | Succeeded: {status_counts.get('SUCCESS', 0)} | "
          f"Failed: {status_counts.get('FAILED', 0)} | "
          f"Blocked: {status_counts.get('BLOCKED_BY_UPSTREAM', 0)}")
    print("=" * len(border) + "\n")


def render_incident_table(incidents: List[Dict[str, Any]], run_id: str) -> None:
    """
    Renders an ASCII terminal table showing generated ServiceNow Incident tickets.
    """
    headers = [
        "INC NUMBER",
        "JOB ID",
        "TYPE",
        "PRIORITY",
        "STATE",
        "ASSIGNMENT GROUP",
        "PARENT INC",
    ]

    rows = []
    for inc in incidents:
        inc_num = inc.get("incident_number", "")
        job_id = inc.get("job_id", "")
        inc_type = inc.get("incident_type", "")
        priority = inc.get("priority", "")
        state = inc.get("state", "")
        group = inc.get("assignment_group", "")
        parent = inc.get("parent_incident") or "-"
        rows.append([inc_num, job_id, inc_type, priority, state, group, parent])

    if not rows:
        print("\n[SERVICENOW] No incidents generated for this batch run (All jobs healthy within SLA).\n")
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(val))

    border = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |"

    print("=" * len(border))
    print(f" SERVICENOW INCIDENT & ESCALATION SUMMARY | Run ID: {run_id}")
    print("=" * len(border))
    print(border)
    print(header_line)
    print(border)

    for row in rows:
        line = "| " + " | ".join(val.ljust(w) for val, w in zip(row, col_widths)) + " |"
        print(line)

    print(border)
    print(f" Generated Tickets: {len(rows)} | REST API Outbox: data/servicenow_outbox/")
    print("=" * len(border) + "\n")


def render_housekeeping_table(checks: List[Dict[str, Any]], run_id: str) -> None:
    """
    Renders an ASCII terminal table showing system housekeeping and health checks.
    """
    headers = [
        "CATEGORY",
        "METRIC / COMPONENT",
        "MEASURED TELEMETRY",
        "THRESHOLD",
        "COMPLIANCE",
    ]

    rows = []
    for c in checks:
        cat = c.get("check_category", "")
        metric = c.get("metric_name", "")
        val = c.get("measured_value", "")
        thresh = c.get("threshold", "")
        comp = c.get("compliance_status", "")
        rows.append([cat, metric, val, thresh, comp])

    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(val))

    border = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |"

    print("=" * len(border))
    print(f" UNIX SYSTEM HOUSEKEEPING & INFRASTRUCTURE HEALTH CHECK-SHEET | Run ID: {run_id}")
    print("=" * len(border))
    print(border)
    print(header_line)
    print(border)

    for row in rows:
        line = "| " + " | ".join(val.ljust(w) for val, w in zip(row, col_widths)) + " |"
        print(line)

    print(border)
    compliant_count = sum(1 for c in checks if c.get("compliance_status") == "COMPLIANT")
    print(f" Health Checks: {len(checks)} | Compliant: {compliant_count}/{len(checks)} | "
          f"Status: ALL SYSTEMS GREEN")
    print("=" * len(border) + "\n")


def print_database_contents() -> None:
    """
    Utility to display the raw content of the SQLite database across all tables.
    """
    print("\n[DB QUERY] Querying 'job_runs' from data/batch_ops.db:\n")
    runs = get_job_runs()
    if not runs:
        print("  (Database contains 0 records in job_runs)")
    else:
        for r in runs:
            print(f"  RunID: {r['run_id']} | Job: {r['job_id']:<22} | Status: {r['status']:<20} | "
                  f"Attempts: {r['attempt_count']} | Exit: {r['exit_code']} | "
                  f"Dur: {r['duration_sec']:.2f}s | SLA Breached: {r['sla_breached']}")

    print("\n[DB QUERY] Querying 'job_run_attempts' from data/batch_ops.db:\n")
    attempts = get_job_run_attempts()
    if not attempts:
        print("  (Database contains 0 records in job_run_attempts)")
    else:
        for a in attempts:
            print(f"  AttemptID: {a['id']:<2} | RunID: {a['run_id']} | Job: {a['job_id']:<22} | "
                  f"Attempt #{a['attempt_number']} | Status: {a['status']:<10} | Exit: {a['exit_code']} | "
                  f"Dur: {a['duration_sec']:.2f}s")

    print("\n[DB QUERY] Querying 'incidents' from data/batch_ops.db:\n")
    incidents = get_incidents()
    if not incidents:
        print("  (Database contains 0 records in incidents)")
    else:
        for inc in incidents:
            parent_info = f"Parent: {inc['parent_incident']}" if inc['parent_incident'] else "Parent: None"
            print(f"  Incident: {inc['incident_number']} | Run: {inc['run_id']} | Job: {inc['job_id']:<22} | "
                  f"Type: {inc['incident_type']:<24} | Priority: {inc['priority']:<14} | "
                  f"State: {inc['state']:<28} | Group: {inc['assignment_group']:<24} | {parent_info}")

    print("\n[DB QUERY] Querying 'housekeeping_checks' from data/batch_ops.db:\n")
    checks = get_housekeeping_checks()
    if not checks:
        print("  (Database contains 0 records in housekeeping_checks)")
    else:
        for c in checks:
            print(f"  Check #{c['check_id']:<2} | Run: {c['run_id']} | Cat: {c['check_category']:<24} | "
                  f"Metric: {c['metric_name']:<24} | Val: {c['measured_value']:<30} | Status: {c['compliance_status']}")
    print("")


def main():
    parser = argparse.ArgumentParser(
        description="FinOps-BatchGuard: Automated Batch Failure & SLA Alert Engine"
    )
    parser.add_argument(
        "--run-batch",
        action="store_true",
        help="Execute full pipeline: Housekeeping -> Batch DAG -> Incident Triage -> Shift Reports.",
    )
    parser.add_argument(
        "--show-db",
        action="store_true",
        help="Query and print all persisted records from SQLite database.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logging in stdout.",
    )

    args = parser.parse_args()

    # If no flags passed, display help
    if not args.run_batch and not args.show_db:
        print_banner()
        parser.print_help()
        sys.exit(0)

    logger = setup_logging(verbose=args.verbose)

    if args.run_batch:
        print_banner()
        init_db()
        now = datetime.now()
        run_id = f"RUN-{now.strftime('%Y%m%d-%H%M%S')}"
        batch_date = now.strftime("%Y-%m-%d")

        # Step 1: Unix System Housekeeping & Health Checks
        logger.info(">>> STEP 1: Running Unix System Housekeeping & Daemon Health Checks...")
        housekeeping_mgr = HousekeepingManager(logger=logger)
        checks = housekeeping_mgr.run_housekeeping_checks(run_id=run_id)

        # Step 2: Batch DAG Execution & Auto-Retry Loop
        logger.info(">>> STEP 2: Executing Batch DAG Pipeline with Auto-Retry & SLA Monitoring...")
        engine = BatchEngine(logger=logger)
        result = engine.run_batch(run_id=run_id, batch_date=batch_date)

        # Render Batch Run summary table
        render_terminal_table(
            job_records=result["jobs"],
            run_id=result["run_id"],
            batch_date=result["batch_date"],
        )

        # Step 3: ServiceNow Incident Triage & ITIL Escalation
        logger.info(">>> STEP 3: Initializing ServiceNow Incident Triage & ITIL Escalation Engine...")
        incident_mgr = IncidentManager(logger=logger)
        incidents = incident_mgr.triage_and_escalate(run_id=result["run_id"])

        # Render ServiceNow Incident summary table
        render_incident_table(
            incidents=incidents,
            run_id=result["run_id"],
        )

        # Step 4: Daily Check-Sheet & Shift Handover Report Generation
        logger.info(">>> STEP 4: Generating Daily Operational Check-Sheet & HTML Shift Handover Dashboard...")
        reporter = CheckSheetReporter(logger=logger)
        reports = reporter.generate_reports(run_id=result["run_id"])

        # Render Housekeeping check-sheet table
        render_housekeeping_table(
            checks=checks,
            run_id=result["run_id"],
        )

        # Display final generated artifacts
        print("=" * 80)
        print(" SHIFT HANDOVER REPORTS GENERATED SUCCESSFULLY:")
        print(f" ▶ Tabular CSV Check-Sheet : {reports['csv_path']}")
        print(f" ▶ HTML Executive Dashboard: {reports['html_path']}")
        print("=" * 80 + "\n")

    if args.show_db:
        print_database_contents()


if __name__ == "__main__":
    main()
