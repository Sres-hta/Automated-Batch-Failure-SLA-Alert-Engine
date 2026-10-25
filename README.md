# FinOps-BatchGuard: Automated Batch Failure & SLA Alert Engine

[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/)
[![Platform Linux](https://img.shields.io/badge/Platform-Linux%20%7C%20Unix-orange.svg)]()
[![Standards ITIL v4](https://img.shields.io/badge/Standard-ITIL%20v4%20Incident%20Mgmt-purple.svg)]()
[![Model Control-M / JP1](https://img.shields.io/badge/Scheduler-Control--M%20%2F%20Hitachi%20JP1-green.svg)]()

> **Enterprise-grade banking batch operations and automated shift handover engine.**  
> Designed for tier-1 financial institutions (e.g., MUFG Bank, Citi, JPMorgan) to automate overnight batch execution, mitigate cascading failures, guarantee SLA compliance, auto-generate ServiceNow incident payloads, and export production shift handover check-sheets.

---

## 1. Executive Summary & Capabilities

`FinOps-BatchGuard` models the end-to-end responsibilities of a **Global Core Banking Operations & Batch Support Analyst**:

1. **Phase 1: DAG Dependency, Execution & Auto-Retry Engine**
   - Resolves job schedules and dependencies (`depends_on`) using topological sorting.
   - Executes jobs via isolated subprocesses, capturing real exit codes, stdout, stderr, and durations.
   - **Auto-Retry & Backoff**: Handles transient lock contention (e.g., Oracle `ORA-04021`) by switching state to `RETRYING`, applying backoff delays, and recovering on subsequent attempts.
   - **Cascading Failure Protection**: When a hard failure occurs (e.g., Oracle Deadlock `ORA-00060`), downstream dependent jobs are automatically halted with status `BLOCKED_BY_UPSTREAM` to avoid corrupted ledger data.
   - **SLA Breach Tracking**: Evaluates overall wall-clock elapsed time against defined SLA thresholds.

2. **Phase 2: ITIL Incident Triage & ServiceNow Auto-Ticketing Engine**
   - Applies ITIL v4 triage rules to distinguish hard failures, cascading blocks, and recovered SLA warnings:
     - **Rule A (Hard Failure → P1 Major Incident):** Triggers P1 Critical ticket (`Core-Banking-DBA-L3`, Runbook `KB0041209`) with full stderr diagnostics.
     - **Rule B (Cascading Block → Parent-Child Correlation):** Triggers P3 Moderate ticket (`Regulatory-Reporting-L2`), sets state to `On Hold - Awaiting Upstream`, and links `parent_incident` to the P1 failure (suppressing alert fatigue).
     - **Rule C (Recovered Job with SLA Breach → P2 Warning):** Triggers P2 High SLA Warning ticket (`FinControl-GL-Support-L2`) highlighting lock contention backoff delays.
   - Generates compliant ServiceNow Table API REST payloads (`POST /api/now/table/incident`) in `data/servicenow_outbox/<incident_number>.json`.

3. **Phase 3: Unix System Housekeeping & Automated Shift Handover Reporting**
   - **Real OS Telemetry**: Queries Linux kernel and system state for Disk (`df -h /`), Memory (`free -m`), CPU Load Average (`uptime`), and Zombie processes (`ps aux`).
   - **Banking Housekeeping**: Purges mock spool buffers (`data/spool_tmp/`) and validates core daemons (`controlm-agent`, `swift-mq-listener`, `as400-tn5250-bridge`).
   - **Shift Handover Reports (`reports/`)**:
     - `Daily_Ops_CheckSheet_<run_id>.csv`: Tabular check-sheet for Excel audit review.
     - `Shift_Handover_Dashboard_<run_id>.html`: Dark-themed operational dashboard formatted for 24x7 Command Center shift handover.

---

## 2. System Architecture

```
[config/batch_schedule.json]            [config/escalation_matrix.json]
             │                                        │
             ▼                                        ▼
┌───────────────────────────┐            ┌───────────────────────────┐
│       src/engine.py       │            │  src/incident_manager.py  │
│   (DAG Batch Scheduler)   │            │ (ITIL Triage & Ticketing) │
└─────────────┬─────────────┘            └─────────────┬─────────────┘
              │                                        │
              ▼                                        ▼
   ┌────────────────────┐                     ┌────────────────────┐
   │    jobs/ Scripts   │                     │ data/              │
   │  (Mock Core Jobs)  │                     │ servicenow_outbox/ │
   └──────────┬─────────┘                     │ (*.json REST API)  │
              │                               └────────────────────┘
              ▼
   ┌───────────────────────────────────────────────────────────────┐
   │                       src/database.py                         │
   │                  SQLite Data Store (WAL Mode)                 │
   │  - job_runs            - incidents                            │
   │  - job_run_attempts    - housekeeping_checks                  │
   └──────────────────────────────┬────────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌──────────────────┐                            ┌─────────────────────┐
│src/housekeeping  │                            │src/checksheet_report│
│(Unix OS Telemetry│                            │(CSV & HTML Handover │
│ & Spool Cleanup) │                            │ Dashboards)         │
└──────────────────┘                            └─────────────────────┘
```

---

## 3. Directory Layout

```
.
├── config/
│   ├── batch_schedule.json          # Declarative schedule, retries, and SLA thresholds
│   └── escalation_matrix.json       # ITIL support groups, SLA tiers, and runbook IDs
├── data/
│   ├── batch_ops.db                 # SQLite persistent database (WAL mode)
│   ├── servicenow_outbox/           # Exported ServiceNow Table API JSON payloads
│   │   ├── INC0010404.json          # P1 Critical incident payload (DBA L3)
│   │   ├── INC0010405.json          # P2 High SLA warning payload (GL Support L2)
│   │   └── INC0010406.json          # P3 Moderate correlated child payload (Reg Ops L2)
│   └── spool_tmp/                   # Banking temp and spool buffer directory
├── jobs/
│   ├── job_01_fx_ingest.sh          # SWIFT MT940 / MT535 statement feed ingestion (Exit 0)
│   ├── job_02_ledger_recon.py       # GL reconciliation: transient lock -> retry recovery
│   ├── job_03_eod_settlement.sh     # Hard failure: Oracle RAC deadlock (Exit 2)
│   ├── job_04_reg_report.sh         # Statutory reporting (BLOCKED_BY_UPSTREAM)
│   └── system_housekeeping.sh       # Unix OS health telemetry and daemon checks
├── logs/
│   └── batch_engine.log             # Unified structured timestamped logging
├── reports/
│   ├── Daily_Ops_CheckSheet_*.csv   # Tabular operational check-sheet for Excel
│   └── Shift_Handover_Dashboard_*.html # Dark-themed executive shift handover dashboard
├── src/
│   ├── __init__.py                  # Source package descriptor
│   ├── database.py                  # SQLite schema creation, connection pool & queries
│   ├── engine.py                    # DAG resolution, retry backoff, SLA calculation
│   ├── incident_manager.py          # ITIL triage, parent-child linking, REST payloads
│   ├── housekeeping.py              # Unix housekeeping parser & SQLite persistence
│   └── checksheet_reporter.py       # CSV and HTML handover dashboard generator
├── main.py                          # Unified CLI entry point (--run-batch, --show-db)
└── README.md                        # Complete project documentation
```

---

## 4. Operational Walkthrough & Commands

### 1. Execute Full End-to-End Banking Batch & Shift Handover:
```bash
python3 main.py --run-batch
```

**Pipeline Execution Flow:**
1. **Step 1:** Executes `jobs/system_housekeeping.sh` to capture real Linux OS metrics, purge stale temp files in `data/spool_tmp/`, and verify banking daemons.
2. **Step 2:** Resolves the DAG schedule, executes `JOB_01_FX_INGEST` (Success), `JOB_02_LEDGER_RECON` (Transient lock contention → Retry → Success with SLA breach), `JOB_03_EOD_SETTLEMENT` (Deadlock → Retries exhausted → Failed), and skips `JOB_04_REG_REPORT` (`BLOCKED_BY_UPSTREAM`).
3. **Step 3:** Analyzes execution states, auto-generates ServiceNow tickets `INC0010404`, `INC0010405`, `INC0010406` with parent-child correlation, and exports REST API JSON payloads to `data/servicenow_outbox/`.
4. **Step 4:** Generates `reports/Daily_Ops_CheckSheet_<run_id>.csv` and `reports/Shift_Handover_Dashboard_<run_id>.html`.
5. **Terminal Output:** Prints 3 formatted ASCII summary tables.

### 2. Inspect SQLite Database State:
```bash
python3 main.py --show-db
```
Displays persistent records across:
- `job_runs`: Authoritative job execution states.
- `job_run_attempts`: Detailed audit log of every individual execution attempt.
- `incidents`: ServiceNow incident numbers, priorities, states, and assignment groups.
- `housekeeping_checks`: Unix OS telemetry metrics, thresholds, and compliance flags.

---

## 5. Sample ServiceNow Incident JSON Payload

Generated at `data/servicenow_outbox/INC0010404.json` (ServiceNow Table API compliant):

```json
{
  "number": "INC0010404",
  "caller_id": "batchguard.automation",
  "category": "Database Infrastructure",
  "subcategory": "Deadlock & Lock Contention",
  "contact_type": "Automated Event",
  "impact": "1",
  "urgency": "1",
  "priority": "P1 - Critical",
  "state": "Assigned",
  "assignment_group": "Core-Banking-DBA-L3",
  "assigned_to": "Oracle RAC Escalation Desk",
  "short_description": "[P1 INCIDENT] Hard Failure in End-of-Day Settlement Engine (JOB_03_EOD_SETTLEMENT) - Exit Code 2",
  "description": "Critical banking batch job 'JOB_03_EOD_SETTLEMENT' encountered an unrecoverable failure after 3 attempts with exit code 2.\nAll auto-retries exhausted. Downstream settlement and statutory reporting are compromised.\nRefer to Runbook KB0041209 for immediate remediation steps.",
  "u_kb_article": "KB0041209",
  "parent_incident": null,
  "u_batch_run_id": "RUN-20261014-171845",
  "u_job_id": "JOB_03_EOD_SETTLEMENT",
  "u_incident_type": "HARD_FAILURE",
  "sys_created_on": "2026-10-14 17:18:55"
}
```

---

## 6. HTML Shift Handover Dashboard Preview

The generated dashboard in `reports/Shift_Handover_Dashboard_<run_id>.html` includes:
- **Shift Rota Header:** Night Shift (22:00-06:00) → Morning Shift Handover.
- **Executive KPI Cards:** Batch Operational State, SLA Compliance Rate (%), Incidents Raised, System Health (100%).
- **Section 1:** Unix System Housekeeping & Health Check-Sheet (Disk, Memory, CPU Load, Zombies, Spool, Daemons).
- **Section 2:** Batch Schedule Execution & SLA Performance Matrix (Color-coded badges).
- **Section 3:** ServiceNow Incident Escalations & Morning Shift Analyst Action Items (L2/L3 Bridge, Regulatory Deadlines, Runbooks).
- **Operations Sign-Off Block:** Formal sign-off signatures for outgoing analyst, incoming analyst, and Shift Commander.

---

## 7. Tech Stack

- **Language:** Python 3.13+, Bash
- **Database:** SQLite3 (WAL mode, Foreign Keys enabled)
- **Architecture Model:** BMC Control-M / Hitachi JP1 / ITIL Incident Management
- **Integrations:** ServiceNow Table API REST JSON Outbox
- **Reporting:** Tabular CSV & Dark-Themed Executive HTML5/CSS3 Dashboard

- **Language:** Python 3.13+, Bash
- **Database:** SQLite3 (WAL mode, Foreign Keys enabled)
- **Architecture Model:** BMC Control-M / Hitachi JP1 / ITIL Incident Management
- **Integrations:** ServiceNow Table API REST JSON Outbox
- **Reporting:** Tabular CSV & Dark-Themed Executive HTML5/CSS3 Dashboard

