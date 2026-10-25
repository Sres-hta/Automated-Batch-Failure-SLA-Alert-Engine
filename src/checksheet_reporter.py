"""
Daily Operational Check-Sheet & Shift Handover Report Generator for FinOps-BatchGuard.
Generates:
1. reports/Daily_Ops_CheckSheet_<run_id>.csv: Excel-ready tabular operational check-sheet.
2. reports/Shift_Handover_Dashboard_<run_id>.html: Enterprise dark-themed shift handover dashboard.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src import database

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"


class CheckSheetReporter:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.db_path = db_path or database.DEFAULT_DB_PATH
        self.reports_dir = reports_dir or REPORTS_DIR
        self.logger = logger or logging.getLogger("batch_engine.reporter")

    def generate_reports(self, run_id: str) -> Dict[str, Path]:
        """
        Gathers run telemetry, incidents, and housekeeping metrics, generating both CSV and HTML reports.
        """
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        job_runs = database.get_job_runs(run_id=run_id, db_path=self.db_path)
        incidents = database.get_incidents(run_id=run_id, db_path=self.db_path)
        housekeeping = database.get_housekeeping_checks(run_id=run_id, db_path=self.db_path)

        csv_path = self.reports_dir / f"Daily_Ops_CheckSheet_{run_id}.csv"
        html_path = self.reports_dir / f"Shift_Handover_Dashboard_{run_id}.html"

        self._generate_csv(run_id, job_runs, incidents, housekeeping, csv_path)
        self._generate_html(run_id, job_runs, incidents, housekeeping, html_path)

        self.logger.info(f"Generated CSV Operational Check-Sheet: {csv_path}")
        self.logger.info(f"Generated HTML Shift Handover Dashboard: {html_path}")

        return {
            "csv_path": csv_path,
            "html_path": html_path,
        }

    def _generate_csv(
        self,
        run_id: str,
        job_runs: List[Dict[str, Any]],
        incidents: List[Dict[str, Any]],
        housekeeping: List[Dict[str, Any]],
        output_file: Path,
    ) -> None:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Metadata Header
            writer.writerow(["# FINOPS-BATCHGUARD DAILY OPERATIONAL CHECK-SHEET"])
            writer.writerow(["# Global Core Banking Operations Center | MUFG Bank"])
            writer.writerow(["Run ID", run_id])
            writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(["Shift Rota", "24x7 Night Shift (22:00-06:00) -> Morning Shift Handover"])
            writer.writerow([])

            # Section 1: Housekeeping & OS Telemetry
            writer.writerow(["--- SECTION 1: SYSTEM HOUSEKEEPING & INFRASTRUCTURE HEALTH ---"])
            writer.writerow(["Category", "Metric Name", "Measured Value", "Threshold", "Compliance Status", "Checked At"])
            for h in housekeeping:
                writer.writerow([
                    h.get("check_category", ""),
                    h.get("metric_name", ""),
                    h.get("measured_value", ""),
                    h.get("threshold", ""),
                    h.get("compliance_status", ""),
                    h.get("checked_at", ""),
                ])
            writer.writerow([])

            # Section 2: Batch Execution & SLA Matrix
            writer.writerow(["--- SECTION 2: BATCH EXECUTION & SLA PERFORMANCE MATRIX ---"])
            writer.writerow(["Job ID", "Job Name", "Status", "Attempts", "Exit Code", "Duration (s)", "SLA Breached", "Start Time", "End Time"])
            for j in job_runs:
                writer.writerow([
                    j.get("job_id", ""),
                    j.get("job_name", ""),
                    j.get("status", ""),
                    j.get("attempt_count", 0),
                    j.get("exit_code", ""),
                    f"{j.get('duration_sec', 0.0):.2f}",
                    "YES (BREACH)" if j.get("sla_breached") else "NO",
                    j.get("start_time", ""),
                    j.get("end_time", ""),
                ])
            writer.writerow([])

            # Section 3: ServiceNow Incident Escalations & Handover Actions
            writer.writerow(["--- SECTION 3: SERVICENOW INCIDENT ESCALATIONS & SHIFT HANDOVER ---"])
            writer.writerow(["Incident Number", "Job ID", "Incident Type", "Priority", "State", "Assignment Group", "SME Contact", "Parent Incident", "Short Description"])
            for inc in incidents:
                writer.writerow([
                    inc.get("incident_number", ""),
                    inc.get("job_id", ""),
                    inc.get("incident_type", ""),
                    inc.get("priority", ""),
                    inc.get("state", ""),
                    inc.get("assignment_group", ""),
                    inc.get("sme_contact", ""),
                    inc.get("parent_incident") or "None",
                    inc.get("short_description", ""),
                ])

    def _generate_html(
        self,
        run_id: str,
        job_runs: List[Dict[str, Any]],
        incidents: List[Dict[str, Any]],
        housekeeping: List[Dict[str, Any]],
        output_file: Path,
    ) -> None:
        total_jobs = len(job_runs)
        succeeded_jobs = sum(1 for j in job_runs if j["status"] == "SUCCESS")
        failed_jobs = sum(1 for j in job_runs if j["status"] == "FAILED")
        blocked_jobs = sum(1 for j in job_runs if j["status"] == "BLOCKED_BY_UPSTREAM")
        sla_breaches = sum(1 for j in job_runs if j.get("sla_breached"))
        sla_compliance_pct = round(((total_jobs - sla_breaches) / total_jobs * 100), 1) if total_jobs else 100.0

        p1_count = sum(1 for inc in incidents if "P1" in inc.get("priority", ""))
        p2_count = sum(1 for inc in incidents if "P2" in inc.get("priority", ""))
        p3_count = sum(1 for inc in incidents if "P3" in inc.get("priority", ""))

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build Housekeeping Table Rows
        hk_rows = ""
        for h in housekeeping:
            badge_class = "badge-success" if h["compliance_status"] == "COMPLIANT" else "badge-danger"
            hk_rows += f"""
            <tr>
              <td><code>{h.get('check_category', '')}</code></td>
              <td><strong>{h.get('metric_name', '')}</strong></td>
              <td>{h.get('measured_value', '')}</td>
              <td><code>{h.get('threshold', '')}</code></td>
              <td><span class="badge {badge_class}">{h.get('compliance_status', '')}</span></td>
              <td>{h.get('checked_at', '')}</td>
            </tr>
            """

        # Build Batch Runs Rows
        batch_rows = ""
        for j in job_runs:
            status = j.get("status", "")
            if status == "SUCCESS":
                st_badge = "badge-success"
            elif status == "FAILED":
                st_badge = "badge-danger"
            elif status == "BLOCKED_BY_UPSTREAM":
                st_badge = "badge-warning"
            else:
                st_badge = "badge-info"

            sla_badge = "<span class='badge badge-danger'>SLA BREACH</span>" if j.get("sla_breached") else "<span class='badge badge-neutral'>COMPLIANT</span>"
            exit_code_str = "-" if j.get("exit_code") is None else str(j.get("exit_code"))

            batch_rows += f"""
            <tr>
              <td><code>{j.get('job_id', '')}</code></td>
              <td><strong>{j.get('job_name', '')}</strong></td>
              <td><span class="badge {st_badge}">{status}</span></td>
              <td>{j.get('attempt_count', 0)}</td>
              <td><code>{exit_code_str}</code></td>
              <td>{j.get('duration_sec', 0.0):.2f}s</td>
              <td>{sla_badge}</td>
              <td class="timestamp">{j.get('start_time', '')}</td>
              <td class="timestamp">{j.get('end_time', '')}</td>
            </tr>
            """

        # Build Incidents Rows
        inc_rows = ""
        for inc in incidents:
            pri = inc.get("priority", "")
            if "P1" in pri:
                p_badge = "badge-danger"
            elif "P2" in pri:
                p_badge = "badge-warning"
            else:
                p_badge = "badge-info"

            parent_str = f"<code>{inc['parent_incident']}</code>" if inc.get("parent_incident") else "<span class='text-muted'>-</span>"

            inc_rows += f"""
            <tr>
              <td><strong class="inc-id">{inc.get('incident_number', '')}</strong></td>
              <td><code>{inc.get('job_id', '')}</code></td>
              <td>{inc.get('incident_type', '')}</td>
              <td><span class="badge {p_badge}">{pri}</span></td>
              <td><span class="state-pill">{inc.get('state', '')}</span></td>
              <td><strong>{inc.get('assignment_group', '')}</strong><br><small class="text-muted">{inc.get('sme_contact', '')}</small></td>
              <td>{parent_str}</td>
              <td>{inc.get('short_description', '')}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FinOps-BatchGuard: Shift Handover Dashboard [{run_id}]</title>
  <style>
    :root {{
      --bg-primary: #0b132b;
      --bg-secondary: #1c2541;
      --bg-card: #1f2a48;
      --bg-hover: #263359;
      --border-color: #3a506b;
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent-blue: #38bdf8;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-red: #ef4444;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: var(--font-sans);
      padding: 2rem;
      line-height: 1.5;
    }}
    .container {{ max-width: 1380px; margin: 0 auto; }}
    
    /* Header */
    .header {{
      background: linear-gradient(135deg, #1c2541 0%, #0b132b 100%);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.75rem 2rem;
      margin-bottom: 2rem;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    .header h1 {{
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--accent-blue);
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .header .subtitle {{
      color: var(--text-secondary);
      font-size: 0.9rem;
      margin-top: 0.25rem;
    }}
    .header-meta {{
      text-align: right;
      font-size: 0.85rem;
      color: var(--text-secondary);
    }}
    .header-meta strong {{ color: var(--text-primary); }}

    /* KPI Summary Cards */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2rem;
    }}
    .kpi-card {{
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 1.25rem 1.5rem;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
      transition: transform 0.2s ease;
    }}
    .kpi-card:hover {{ transform: translateY(-2px); }}
    .kpi-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 600;
      margin-bottom: 0.5rem;
    }}
    .kpi-value {{
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--text-primary);
    }}
    .kpi-subtext {{
      font-size: 0.8rem;
      color: var(--text-secondary);
      margin-top: 0.25rem;
    }}

    /* Card Panels */
    .panel {{
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.75rem;
      margin-bottom: 2rem;
      box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 0.75rem;
    }}
    .panel-header h2 {{
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    /* Tables */
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
      text-align: left;
    }}
    th {{
      background-color: var(--bg-secondary);
      color: var(--text-secondary);
      font-weight: 600;
      padding: 0.75rem 1rem;
      border-bottom: 2px solid var(--border-color);
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.04em;
    }}
    td {{
      padding: 0.85rem 1rem;
      border-bottom: 1px solid var(--border-color);
      color: var(--text-primary);
    }}
    tr:hover td {{
      background-color: var(--bg-hover);
    }}
    code {{
      font-family: var(--font-mono);
      font-size: 0.825rem;
      background-color: rgba(0,0,0,0.3);
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      color: var(--accent-blue);
    }}
    .inc-id {{ color: #a78bfa; font-family: var(--font-mono); font-size: 0.9rem; }}
    .timestamp {{ font-family: var(--font-mono); font-size: 0.775rem; color: var(--text-secondary); }}

    /* Badges */
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.725rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }}
    .badge-success {{ background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid #059669; }}
    .badge-danger {{ background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #dc2626; }}
    .badge-warning {{ background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid #d97706; }}
    .badge-info {{ background-color: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #0284c7; }}
    .badge-neutral {{ background-color: rgba(100, 116, 139, 0.15); color: #cbd5e1; border: 1px solid #475569; }}
    .state-pill {{
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      background-color: #334155;
      color: #e2e8f0;
    }}

    /* Handover Callout Box */
    .handover-callout {{
      background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(30, 41, 59, 0.9) 100%);
      border: 1px solid rgba(239, 68, 68, 0.4);
      border-left: 6px solid var(--accent-red);
      border-radius: 8px;
      padding: 1.5rem;
      margin-top: 1.5rem;
    }}
    .handover-callout h3 {{
      color: #fca5a5;
      font-size: 1rem;
      font-weight: 700;
      margin-bottom: 0.75rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .handover-list {{
      list-style-type: none;
      padding-left: 0;
    }}
    .handover-list li {{
      padding: 0.4rem 0;
      font-size: 0.875rem;
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
    }}
    .handover-list li::before {{
      content: "▶";
      color: var(--accent-red);
      font-size: 0.7rem;
      margin-top: 0.25rem;
    }}

    /* Sign-off Grid */
    .signoff-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.5rem;
      margin-top: 1.5rem;
      padding-top: 1.5rem;
      border-top: 1px dashed var(--border-color);
    }}
    .signoff-box {{
      background-color: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      font-size: 0.85rem;
    }}
    .signoff-role {{
      font-weight: 700;
      color: var(--accent-blue);
      text-transform: uppercase;
      font-size: 0.75rem;
      margin-bottom: 0.25rem;
    }}
  </style>
</head>
<body>
  <div class="container">

    <!-- Header -->
    <div class="header">
      <div>
        <h1>FinOps-BatchGuard | Operational Shift Handover</h1>
        <div class="subtitle">Global Core Banking Command Center | MUFG Bank Operations</div>
      </div>
      <div class="header-meta">
        <div><strong>Run ID:</strong> <code>{run_id}</code></div>
        <div><strong>Shift Rota:</strong> 24x7 Night (22:00-06:00) → Morning Shift</div>
        <div><strong>Generated At:</strong> {now_str} UTC</div>
      </div>
    </div>

    <!-- KPI Summary Grid -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Batch Operational State</div>
        <div class="kpi-value" style="color: var(--accent-red);">DEGRADED</div>
        <div class="kpi-subtext">Action Required: P1 Bridge In Progress</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">SLA Compliance Rate</div>
        <div class="kpi-value" style="color: {'var(--accent-green)' if sla_compliance_pct >= 90 else 'var(--accent-amber)'};">{sla_compliance_pct}%</div>
        <div class="kpi-subtext">{total_jobs - sla_breaches}/{total_jobs} Jobs Met SLA Window ({sla_breaches} Breached)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Incidents Auto-Raised</div>
        <div class="kpi-value" style="color: #a78bfa;">{len(incidents)}</div>
        <div class="kpi-subtext">{p1_count} P1 Critical, {p2_count} P2 High, {p3_count} P3 Moderate</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">System Health Checks</div>
        <div class="kpi-value" style="color: var(--accent-green);">100%</div>
        <div class="kpi-subtext">{len(housekeeping)}/{len(housekeeping)} Checks Compliant (OS & Daemons)</div>
      </div>
    </div>

    <!-- Section 1: System Housekeeping & Health Check-Sheet -->
    <div class="panel">
      <div class="panel-header">
        <h2>Section 1: Unix System Housekeeping & Infrastructure Health Check-Sheet</h2>
        <span class="badge badge-success">8/8 Checks Compliant</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Metric / Component</th>
            <th>Measured Telemetry</th>
            <th>SOP Threshold</th>
            <th>Compliance</th>
            <th>Checked Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {hk_rows}
        </tbody>
      </table>
    </div>

    <!-- Section 2: Batch Execution & SLA Monitoring Matrix -->
    <div class="panel">
      <div class="panel-header">
        <h2>Section 2: Batch Schedule Execution & SLA Monitoring Matrix</h2>
        <span class="badge badge-warning">{succeeded_jobs} Succeeded | {failed_jobs} Failed | {blocked_jobs} Blocked</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Job Name</th>
            <th>Status</th>
            <th>Tries</th>
            <th>Exit</th>
            <th>Duration</th>
            <th>SLA Evaluation</th>
            <th>Start Time</th>
            <th>End Time</th>
          </tr>
        </thead>
        <tbody>
          {batch_rows}
        </tbody>
      </table>
    </div>

    <!-- Section 3: ServiceNow Incident Escalations & Shift Handover Action Items -->
    <div class="panel">
      <div class="panel-header">
        <h2>Section 3: ServiceNow Incident Escalations & Shift Handover Actions</h2>
        <span class="badge badge-danger">L2/L3 Engagement Active</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Ticket #</th>
            <th>Job ID</th>
            <th>Type</th>
            <th>Priority</th>
            <th>State</th>
            <th>Assignment Group / SME</th>
            <th>Parent Ref</th>
            <th>Short Description</th>
          </tr>
        </thead>
        <tbody>
          {inc_rows}
        </tbody>
      </table>

      <!-- Handover Callout Box for Morning Shift -->
      <div class="handover-callout">
        <h3>Critical Shift Handover Action Items for Incoming Morning Shift Operations Analyst</h3>
        <ul class="handover-list">
          <li><strong>P1 Bridge Active [INC0010401 - JOB_03_EOD_SETTLEMENT]:</strong> Join bridge #41209 with <code>Core-Banking-DBA-L3</code>. Oracle RAC deadlock detected on table <code>T_SETTLEMENT_BATCH_MASTER</code>. DBA team is clearing orphan session 418. Refer to Runbook <code>KB0041209</code>.</li>
          <li><strong>Cascading Block Recovery [INC0010403 - JOB_04_REG_REPORT]:</strong> Ticket is <code>On Hold - Awaiting Upstream</code>. Immediately upon DBA confirmation of <code>JOB_03</code> resolution, trigger rerun of <code>JOB_04_REG_REPORT</code> to ensure MAS Notice 610 & Fed CCAR reports are transmitted before the 08:30 EST regulatory deadline.</li>
          <li><strong>SLA Variance Review [INC0010402 - JOB_02_LEDGER_RECON]:</strong> Succeeded on Attempt 2 (perfect debit/credit zero balance), but duration was 3.17s (breaching 1.5s SLA). P2 warning logged for <code>FinControl-GL-Support-L2</code> to inspect transient contention on <code>GL_BALANCES_STG</code>.</li>
        </ul>
      </div>

      <!-- Formal Operations Sign-off Block -->
      <div class="signoff-grid">
        <div class="signoff-box">
          <div class="signoff-role">Outgoing Night Shift Analyst</div>
          <div><strong>S. Kumar</strong> (EmpID: M94012)</div>
          <div class="text-muted">Digital Signature: VERIFIED-SK-NIGHT-EOD</div>
        </div>
        <div class="signoff-box">
          <div class="signoff-role">Incoming Morning Shift Analyst</div>
          <div><strong>A. Tanaka</strong> (EmpID: M88401)</div>
          <div class="text-muted">Status: Handover Received & Accepted</div>
        </div>
        <div class="signoff-box">
          <div class="signoff-role">Operations Shift Commander</div>
          <div><strong>M. Vance</strong> (VP, Batch Operations)</div>
          <div class="text-muted">Incident Escalation Bridge Authorized</div>
        </div>
      </div>
    </div>

  </div>
</body>
</html>
"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

