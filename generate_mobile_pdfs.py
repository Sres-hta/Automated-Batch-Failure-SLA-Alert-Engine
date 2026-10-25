#!/usr/bin/env python3
"""
FinOps-BatchGuard: Mobile-First PDF Generator
Generates 5 dedicated, high-contrast, mobile-optimized PDFs (4.5" x 8.0" e-reader portrait)
for offline study and revision on smartphones without pinching or horizontal scrolling.
"""

import os
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "docs" / "mobile_pdfs"

# 4.5 inches x 8.0 inches @ 72 points per inch
PAGE_WIDTH = 324.0
PAGE_HEIGHT = 576.0
MARGIN_LEFT = 24.0
MARGIN_RIGHT = 24.0
MARGIN_TOP = 28.0
MARGIN_BOTTOM = 28.0
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # 276.0 pt
CONTENT_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM  # 520.0 pt


class MobilePdfWriter:
    """
    Lightweight, pure-Python PDF 1.4 Vector Document Generator.
    Built specifically for mobile/e-reader portrait screens with automatic pagination,
    word-wrapping, high-contrast visual cards, callout boxes, and running footers.
    Zero external dependencies.
    """

    def __init__(self, output_path: Path, doc_title: str, doc_category: str = "MUFG Interview Masterclass") -> None:
        self.output_path = output_path
        self.doc_title = doc_title
        self.doc_category = doc_category

        self.pages: List[List[str]] = []
        self.current_commands: List[str] = []
        self.current_y = PAGE_HEIGHT - MARGIN_TOP
        self.page_number = 1

        # Start first page
        self._start_new_page()

    def _start_new_page(self) -> None:
        if self.current_commands:
            self.pages.append(self.current_commands)
            self.current_commands = []
            self.page_number += 1

        self.current_y = PAGE_HEIGHT - MARGIN_TOP

        # Draw running header (subtle line and category)
        self.current_commands.append("0.58 0.64 0.72 RG 0.5 w")  # Slate gray stroke
        self.current_commands.append(f"{MARGIN_LEFT} {PAGE_HEIGHT - 20} m {PAGE_WIDTH - MARGIN_RIGHT} {PAGE_HEIGHT - 20} l S")
        
        # Header text
        header_text = self._escape(f"{self.doc_category} • {self.doc_title[:32]}")
        self.current_commands.append(
            f"BT /F1 7.5 Tf 0.45 0.52 0.60 rg {MARGIN_LEFT} {PAGE_HEIGHT - 16} Td ({header_text}) Tj ET"
        )

        self.current_y -= 14

    def _check_space(self, needed_height: float) -> None:
        if self.current_y - needed_height < MARGIN_BOTTOM + 16:
            self._start_new_page()

    def _escape(self, text: str) -> str:
        # Standard PDF text escaping
        # Replace non-latin1 / unicode smart quotes
        text = (
            text.replace("—", "--")
            .replace("–", "-")
            .replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
            .replace("•", "*")
            .replace("➔", "->")
            .replace("▶", ">")
            .replace("✅", "[OK]")
            .replace("🚨", "[ALERT]")
            .replace("⚠️", "[WARN]")
            .replace("⏱️", "[SLA]")
            .replace("🏦", "[BANK]")
            .replace("💡", "[TIP]")
            .replace("❓", "[Q]")
            .replace("🎯", "[FOCUS]")
        )
        return (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

    def add_hero_banner(self, title: str, subtitle: str, tag: str = "MUFG INTERVIEW MASTERCLASS") -> None:
        needed = 75.0
        self._check_space(needed)

        # Background card
        y_top = self.current_y
        h = 68.0
        y_bot = y_top - h
        
        # Draw dark navy rounded card
        self.current_commands.append(f"0.07 0.13 0.24 rg {MARGIN_LEFT} {y_bot} {CONTENT_WIDTH} {h} re f")
        self.current_commands.append(f"0.12 0.24 0.45 RG 1 w {MARGIN_LEFT} {y_bot} {CONTENT_WIDTH} {h} re s")
        # Red/Blue accent stripe
        self.current_commands.append(f"0.89 0.18 0.18 rg {MARGIN_LEFT} {y_bot} 4 {h} re f")

        # Tag
        self.current_commands.append(
            f"BT /F2 7.5 Tf 0.35 0.65 0.95 rg {MARGIN_LEFT + 12} {y_top - 16} Td ({self._escape(tag)}) Tj ET"
        )
        # Title
        self.current_commands.append(
            f"BT /F2 13 Tf 0.98 0.98 1.0 rg {MARGIN_LEFT + 12} {y_top - 34} Td ({self._escape(title)}) Tj ET"
        )
        # Subtitle
        self.current_commands.append(
            f"BT /F1 8.5 Tf 0.70 0.78 0.88 rg {MARGIN_LEFT + 12} {y_top - 50} Td ({self._escape(subtitle)}) Tj ET"
        )

        self.current_y -= (h + 16.0)

    def add_section_heading(self, title: str) -> None:
        self._check_space(34.0)
        self.current_y -= 8.0
        # Underline
        self.current_commands.append(f"0.80 0.84 0.90 RG 0.75 w {MARGIN_LEFT} {self.current_y - 4} m {PAGE_WIDTH - MARGIN_RIGHT} {self.current_y - 4} l S")
        # Text
        self.current_commands.append(
            f"BT /F2 13.5 Tf 0.08 0.15 0.30 rg {MARGIN_LEFT} {self.current_y} Td ({self._escape(title)}) Tj ET"
        )
        self.current_y -= 18.0

    def add_subheading(self, title: str) -> None:
        self._check_space(24.0)
        self.current_y -= 4.0
        self.current_commands.append(
            f"BT /F2 11 Tf 0.15 0.25 0.45 rg {MARGIN_LEFT} {self.current_y} Td ({self._escape(title)}) Tj ET"
        )
        self.current_y -= 15.0

    def add_paragraph(self, text: str, font_size: float = 10.0, line_spacing: float = 13.5) -> None:
        # Wrap at ~50 characters for Helvetica 10pt on 276pt width
        lines = textwrap.wrap(text, width=50)
        needed = len(lines) * line_spacing + 6.0
        self._check_space(needed)

        for line in lines:
            escaped = self._escape(line)
            self.current_commands.append(
                f"BT /F1 {font_size} Tf 0.20 0.24 0.30 rg {MARGIN_LEFT} {self.current_y} Td ({escaped}) Tj ET"
            )
            self.current_y -= line_spacing
        self.current_y -= 4.0

    def add_bullet(self, title: str, text: str) -> None:
        full_text = f"• {title}: {text}" if title else f"• {text}"
        lines = textwrap.wrap(full_text, width=48)
        needed = len(lines) * 13.0 + 4.0
        self._check_space(needed)

        first = True
        for line in lines:
            indent = MARGIN_LEFT if first else MARGIN_LEFT + 10.0
            font = "/F2" if (first and title) else "/F1"
            escaped = self._escape(line)
            self.current_commands.append(
                f"BT {font} 9.5 Tf 0.18 0.22 0.28 rg {indent} {self.current_y} Td ({escaped}) Tj ET"
            )
            self.current_y -= 13.0
            first = False
        self.current_y -= 3.0

    def add_callout(self, title: str, text: str, kind: str = "tip") -> None:
        """
        kind: 'tip' (Blue), 'warning' (Red/Amber), 'key' (Green), 'model' (Purple)
        """
        lines = textwrap.wrap(text, width=47)
        h = len(lines) * 12.5 + 26.0
        self._check_space(h + 8.0)

        y_top = self.current_y
        y_bot = y_top - h

        if kind == "warning":
            bg_rg, border_rg, stripe_rg = "0.99 0.95 0.95", "0.95 0.80 0.80", "0.89 0.18 0.18"
            t_rg = "0.70 0.10 0.10"
        elif kind == "key":
            bg_rg, border_rg, stripe_rg = "0.95 0.99 0.95", "0.80 0.95 0.80", "0.15 0.65 0.25"
            t_rg = "0.10 0.50 0.15"
        elif kind == "model":
            bg_rg, border_rg, stripe_rg = "0.97 0.95 0.99", "0.88 0.80 0.95", "0.55 0.20 0.85"
            t_rg = "0.40 0.10 0.65"
        else:  # tip
            bg_rg, border_rg, stripe_rg = "0.94 0.97 1.00", "0.78 0.88 0.98", "0.12 0.45 0.85"
            t_rg = "0.08 0.32 0.65"

        # Background card
        self.current_commands.append(f"{bg_rg} rg {MARGIN_LEFT} {y_bot} {CONTENT_WIDTH} {h} re f")
        self.current_commands.append(f"{border_rg} RG 0.75 w {MARGIN_LEFT} {y_bot} {CONTENT_WIDTH} {h} re s")
        # Left accent stripe
        self.current_commands.append(f"{stripe_rg} rg {MARGIN_LEFT} {y_bot} 3.5 {h} re f")

        # Title
        self.current_commands.append(
            f"BT /F2 9.5 Tf {t_rg} rg {MARGIN_LEFT + 10} {y_top - 13} Td ({self._escape(title)}) Tj ET"
        )

        # Body
        cur_text_y = y_top - 25.0
        for line in lines:
            self.current_commands.append(
                f"BT /F1 9.0 Tf 0.15 0.20 0.25 rg {MARGIN_LEFT + 10} {cur_text_y} Td ({self._escape(line)}) Tj ET"
            )
            cur_text_y -= 12.5

        self.current_y -= (h + 8.0)

    def add_card(self, title: str, pairs: List[Tuple[str, str]], status_badge: Optional[str] = None) -> None:
        """
        Mobile-optimized key-value card (replaces wide tabular layouts).
        """
        row_count = len(pairs)
        h = row_count * 15.0 + 26.0
        self._check_space(h + 8.0)

        y_top = self.current_y
        y_bot = y_top - h

        # Card border and soft background
        self.current_commands.append(f"0.97 0.98 0.99 rg {MARGIN_LEFT} {y_bot} {CONTENT_WIDTH} {h} re f")
        self.current_commands.append(f"0.82 0.86 0.90 RG 0.75 w {MARGIN_LEFT} {y_bot} {CONTENT_WIDTH} {h} re s")

        # Header bar
        self.current_commands.append(f"0.92 0.94 0.97 rg {MARGIN_LEFT} {y_top - 18} {CONTENT_WIDTH} 18 re f")
        self.current_commands.append(
            f"BT /F2 9.0 Tf 0.10 0.18 0.35 rg {MARGIN_LEFT + 8} {y_top - 12} Td ({self._escape(title)}) Tj ET"
        )

        if status_badge:
            badge_esc = self._escape(status_badge)
            self.current_commands.append(
                f"BT /F2 8.0 Tf 0.85 0.15 0.15 rg {PAGE_WIDTH - MARGIN_RIGHT - 75} {y_top - 12} Td ({badge_esc}) Tj ET"
            )

        cur_row_y = y_top - 30.0
        for k, v in pairs:
            k_esc = self._escape(k)
            v_esc = self._escape(v)
            self.current_commands.append(
                f"BT /F2 8.5 Tf 0.30 0.35 0.45 rg {MARGIN_LEFT + 8} {cur_row_y} Td ({k_esc}:) Tj ET"
            )
            self.current_commands.append(
                f"BT /F1 8.5 Tf 0.12 0.15 0.20 rg {MARGIN_LEFT + 95} {cur_row_y} Td ({v_esc}) Tj ET"
            )
            cur_row_y -= 15.0

        self.current_y -= (h + 8.0)

    def add_code_block(self, code_text: str) -> None:
        """
        Dark-themed monospace code block with automatic line wrapping.
        """
        raw_lines = code_text.strip().split("\n")
        wrapped_lines: List[str] = []
        for rl in raw_lines:
            if len(rl) > 42:
                wrapped_lines.extend(textwrap.wrap(rl, width=42))
            else:
                wrapped_lines.append(rl)

        h = len(wrapped_lines) * 11.5 + 16.0
        self._check_space(h + 8.0)

        y_top = self.current_y
        y_bot = y_top - h

        # Dark card
        self.current_commands.append(f"0.08 0.11 0.16 rg {MARGIN_LEFT} {y_bot} {CONTENT_WIDTH} {h} re f")
        self.current_commands.append(f"0.18 0.22 0.30 RG 0.75 w {MARGIN_LEFT} {y_bot} {CONTENT_WIDTH} {h} re s")

        cur_code_y = y_top - 13.0
        for cl in wrapped_lines:
            escaped = self._escape(cl)
            self.current_commands.append(
                f"BT /F4 8.0 Tf 0.85 0.92 1.0 rg {MARGIN_LEFT + 8} {cur_code_y} Td ({escaped}) Tj ET"
            )
            cur_code_y -= 11.5

        self.current_y -= (h + 8.0)

    def add_qa_card(self, q_num: int, category: str, question: str, why_ask: str, answer: str) -> None:
        self._check_space(60.0)
        self.add_subheading(f"Q{q_num} [{category}]: {question}")
        self.add_callout("WHY THE HIRING MANAGER ASKS THIS:", why_ask, kind="tip")
        self.add_callout("CRISP SENIOR MODEL ANSWER:", answer, kind="model")
        self.current_y -= 6.0

    def add_page_break(self) -> None:
        self._start_new_page()

    def build(self) -> None:
        # Save last page
        if self.current_commands:
            self.pages.append(self.current_commands)

        total_pages = len(self.pages)
        objects: List[str] = []

        def add_obj(content: str) -> int:
            objects.append(content)
            return len(objects)

        # 1. Catalog
        catalog_id = add_obj("<< /Type /Catalog /Pages 2 0 R >>")
        # 2. Pages (placeholder, updated later)
        pages_id = add_obj("")

        # 3-7. Standard PDF Core Fonts
        f1_id = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        f2_id = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        f3_id = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>")
        f4_id = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
        f5_id = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>")

        font_res = (
            f"<< /Font << /F1 {f1_id} 0 R /F2 {f2_id} 0 R /F3 {f3_id} 0 R "
            f"/F4 {f4_id} 0 R /F5 {f5_id} 0 R >> /ProcSet [/PDF /Text] >>"
        )

        page_ids: List[int] = []

        for p_idx, p_cmds in enumerate(self.pages, 1):
            # Append running footer (Page X of Y)
            footer_line = f"0.58 0.64 0.72 RG 0.5 w {MARGIN_LEFT} {MARGIN_BOTTOM + 10} m {PAGE_WIDTH - MARGIN_RIGHT} {MARGIN_BOTTOM + 10} l S"
            footer_text = self._escape(f"Page {p_idx} of {total_pages} • FinOps-BatchGuard MUFG Prep")
            footer_cmd = (
                f"BT /F1 7.5 Tf 0.45 0.52 0.60 rg {MARGIN_LEFT} {MARGIN_BOTTOM + 1} Td ({footer_text}) Tj ET"
            )
            p_cmds.append(footer_line)
            p_cmds.append(footer_cmd)

            stream_str = "\n".join(p_cmds) + "\n"
            stream_bytes = stream_str.encode("latin1")
            stream_id = add_obj(f"<< /Length {len(stream_bytes)} >>\nstream\n{stream_str}endstream")

            p_obj_id = add_obj(
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Contents {stream_id} 0 R /Resources {font_res} >>"
            )
            page_ids.append(p_obj_id)

        # Update Pages object
        kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
        objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>"

        # Build final byte stream with xref
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n{obj}\nendobj\n".encode("latin1"))

        xref_offset = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        out.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
                "latin1"
            )
        )

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "wb") as f:
            f.write(out)


# ==============================================================================
# PDF 1: Pitch & Banking Domain
# ==============================================================================
def build_pdf_01(out_dir: Path) -> Path:
    target = out_dir / "01_Pitch_and_Banking_Domain.pdf"
    doc = MobilePdfWriter(target, "01 Pitch & Banking Domain", "MUFG Masterclass")

    doc.add_hero_banner("Banking Domain & Pitch", "Core Banking Batch Architecture", "MUFG IT OPS CANDIDATE GUIDE")

    doc.add_section_heading("1. Executive Pitch Playbook")
    doc.add_callout(
        "30-SECOND ELEVATOR PITCH (MEMORIZE):",
        "I built FinOps-BatchGuard, an enterprise batch execution, auto-recovery, and SLA alert engine modeled after Control-M and JP1 used at banks like MUFG. It orchestrates overnight SWIFT feeds and settlement, auto-retries transient database lock timeouts, suppresses cascading false P1 alarms on dependent reporting jobs, auto-generates ServiceNow tickets with parent-child links, and publishes automated shift handover dashboards.",
        kind="model",
    )

    doc.add_paragraph(
        "In a global corporate and investment bank like MUFG, batch operations represent the vital heartbeat of financial stability. Between 22:00 and 06:00, hundreds of mission-critical jobs execute in strict sequential dependency."
    )

    doc.add_callout(
        "KEY TAKEAWAY FOR INTERVIEWERS:",
        "Banks do not fail because code is poorly written; banks fail because operational failure modes (locks, deadlocks, race conditions) are not isolated, leading to cascading alert storms that overwhelm the Command Center.",
        kind="key",
    )

    doc.add_section_heading("2. The 4 Mock Banking Jobs")

    # Job 1 Card
    doc.add_card(
        "JOB 01: FX Swift Feed Ingestion",
        [
            ("Script", "jobs/job_01_fx_ingest.sh"),
            ("Domain", "Foreign Exchange & Trade Services"),
            ("SWIFT MT940", "Customer Statement (End-of-day balances)"),
            ("SWIFT MT535", "Statement of Holdings (Custody portfolios)"),
            ("Volume", "14,820 FX payment messages staged"),
            ("Checksum", "SHA256 hash match against header"),
            ("Exit Code", "0 (SUCCESS on Attempt 1, ~0.63s)"),
        ],
        status_badge="SUCCESS (0)",
    )

    doc.add_paragraph(
        "Why SWIFT matters: Before domestic clearing houses open, external bank account statements (MT940) and security holdings (MT535) must be parsed and staged into STG_SWIFT_FX_TRANSACTIONS so cash balancing can commence."
    )

    # Job 2 Card
    doc.add_card(
        "JOB 02: General Ledger Reconciliation",
        [
            ("Script", "jobs/job_02_ledger_recon.py"),
            ("Domain", "Financial Accounting & Control"),
            ("Function", "Balances Chart of Accounts lines"),
            ("Verification", "Total Debits == Total Credits ($4.28B)"),
            ("Failure", "Attempt 1: ORA-04021 lock timeout"),
            ("Recovery", "Attempt 2: Auto-retry succeeds"),
            ("SLA Window", "1.50s threshold (Wall-Clock: 3.20s)"),
            ("SLA State", "SLA BREACH (Triggers P2 Warning)"),
        ],
        status_badge="SLA BREACH",
    )

    doc.add_paragraph(
        "Why transient locks happen: High-volume ETL loaders frequently lock database library objects during partition swaps. BatchGuard avoids waking on-call DBAs by executing an automatic backoff retry."
    )

    doc.add_page_break()

    # Job 3 Card
    doc.add_card(
        "JOB 03: End-of-Day Settlement Engine",
        [
            ("Script", "jobs/job_03_eod_settlement.sh"),
            ("Domain", "Core Banking Settlement Core"),
            ("Function", "Multi-currency net cash settlements"),
            ("Accounts", "23,400 corporate accounts committed"),
            ("Root Failure", "ORA-00060 Deadlock on T_SETTLEMENT"),
            ("Retries", "Exhausts all 3 attempts (Exit Code 2)"),
            ("Incident", "INC0010404 (P1 Major Incident Bridge)"),
            ("Runbook", "KB0041209 (Oracle RAC Escalation)"),
        ],
        status_badge="FAILED (2)",
    )

    doc.add_paragraph(
        "Why ORA-00060 is a Hard Failure: Two concurrent batch sessions locked resources in reverse order. In Oracle RAC, deadlocks cannot self-heal without terminating one transaction (SQLSTATE 40001). Retrying without clearing the orphan session will fail every time."
    )

    # Job 4 Card
    doc.add_card(
        "JOB 04: Daily Regulatory MAS/Fed Report",
        [
            ("Script", "jobs/job_04_reg_report.sh"),
            ("Domain", "Statutory Risk & Compliance"),
            ("MAS 610", "Monetary Authority of Singapore Return"),
            ("Fed CCAR", "Federal Reserve Daily Capital Summary"),
            ("Status", "BLOCKED_BY_UPSTREAM (Not Executed)"),
            ("Incident", "INC0010406 (P3 Linked Child Ticket)"),
            ("Parent Ref", "Correlated to INC0010404"),
            ("State", "On Hold - Awaiting Upstream"),
        ],
        status_badge="BLOCKED",
    )

    doc.add_callout(
        "CRITICAL COMPLIANCE PRINCIPLE:",
        "Never run statutory regulatory reports against failed or unposted EOD settlement ledgers. Submitting incorrect capital returns to central banks results in regulatory censure, public enforcement notices, and statutory fines.",
        kind="warning",
    )

    doc.build()
    return target


# ==============================================================================
# PDF 2: Architecture & Control-M Map
# ==============================================================================
def build_pdf_02(out_dir: Path) -> Path:
    target = out_dir / "02_Architecture_and_ControlM_Map.pdf"
    doc = MobilePdfWriter(target, "02 Architecture & Control-M", "MUFG Masterclass")

    doc.add_hero_banner("Architecture & Control-M", "Enterprise Schedulers & Pipelines", "CONTROL-M / JP1 PLAYBOOK")

    doc.add_section_heading("1. 4-Step Pipeline Execution Flow")
    doc.add_paragraph(
        "Every batch execution triggered via 'python3 main.py --run-batch' follows an audited 4-step pipeline designed to prevent unmonitored production drift:"
    )

    doc.add_bullet("STEP 1: Unix Housekeeping", "Captures real Linux OS metrics (df, free, uptime, ps aux), purges data/spool_tmp, verifies daemons.")
    doc.add_bullet("STEP 2: DAG Batch Engine", "Resolves schedule dependencies, executes isolated subprocesses, applies retry loops, and evaluates SLAs.")
    doc.add_bullet("STEP 3: ServiceNow ITIL Triage", "Applies Rules A, B, and C to create P1, P2, and P3 tickets with parent-child correlation in data/servicenow_outbox/.")
    doc.add_bullet("STEP 4: Shift Handover Reports", "Generates CSV check-sheet and dark-themed HTML shift handover dashboard in reports/.")

    doc.add_section_heading("2. Control-M / JP1 Enterprise Mapping")
    doc.add_paragraph(
        "Use this side-by-side mapping when interviewing at MUFG to prove you understand their enterprise tooling:"
    )

    doc.add_card(
        "1. Schedule Definition",
        [
            ("BatchGuard", "config/batch_schedule.json"),
            ("BMC Control-M", "Job Definition XML / Smart Folder"),
            ("Hitachi JP1", "Jobnet Definition / Group"),
            ("CA AutoSys", "JIL (Job Instruction Language)"),
            ("Function", "Centralized schedule & agent configs"),
        ],
    )

    doc.add_card(
        "2. Dependency Ordering",
        [
            ("BatchGuard", "depends_on: ['JOB_01_FX_INGEST']"),
            ("BMC Control-M", "IN-Conditions & OUT-Conditions"),
            ("Hitachi JP1", "Preceding Job Execution Conditions"),
            ("CA AutoSys", "condition: success(JOB_01)"),
            ("Function", "Prevents downstream start until OK"),
        ],
    )

    doc.add_card(
        "3. Cyclic Retries",
        [
            ("BatchGuard", "max_retries: 2, retry_delay_sec: 2"),
            ("BMC Control-M", "MAXRERUN=2, RERUNMEM=2M"),
            ("Hitachi JP1", "Auto-Retry Settings / Interval"),
            ("CA AutoSys", "n_retrys: 2, retry_interval: 2"),
            ("Function", "Absorbs transient lock/network spikes"),
        ],
    )

    doc.add_page_break()

    doc.add_card(
        "4. SLA Tracking",
        [
            ("BatchGuard", "sla_max_duration_sec: 1.5"),
            ("BMC Control-M", "Batch Impact Manager (BIM) Alert"),
            ("Hitachi JP1", "JP1/AJS3 SLA Monitoring"),
            ("CA AutoSys", "term_run_time / alarm_if_fail"),
            ("Function", "Alerts when critical path is delayed"),
        ],
    )

    doc.add_card(
        "5. Alert Forwarding",
        [
            ("BatchGuard", "src/incident_manager.py"),
            ("BMC Control-M", "Control-M Shout to ServiceNow"),
            ("Hitachi JP1", "JP1/IM Incident Bridge Forwarder"),
            ("CA AutoSys", "AutoSys Alarm to SNOW API Bridge"),
            ("Function", "Converts exit codes to ITIL tickets"),
        ],
    )

    doc.add_section_heading("3. Operational Actions & Resuming Batches")
    doc.add_callout(
        "INTERVIEW SCENARIO: RESUMING FROM FAILURE",
        "If JOB_03 is fixed by the DBA team at 3:15 AM, how do you resume without re-running JOB_01 and JOB_02? In Control-M, you perform a 'Rerun from Failed Job'. In BatchGuard, because states are saved in SQLite, we inspect job_runs, verify JOB_01 and JOB_02 are SUCCESS, and start directly at JOB_03, unblocking JOB_04 upon completion.",
        kind="tip",
    )

    doc.add_bullet("Force OK", "Manually sets job state to Success in Control-M to allow downstream jobs to proceed when safe.")
    doc.add_bullet("Bypass / Skip", "Temporarily disables a job without breaking DAG topological dependencies.")
    doc.add_bullet("Kill / Terminate", "Sends SIGKILL to a hung batch process exceeding max run time.")

    doc.build()
    return target


# ==============================================================================
# PDF 3: Code & Unix DeepDive
# ==============================================================================
def build_pdf_03(out_dir: Path) -> Path:
    target = out_dir / "03_Code_and_Unix_DeepDive.pdf"
    doc = MobilePdfWriter(target, "03 Code & Unix Deep-Dive", "MUFG Masterclass")

    doc.add_hero_banner("Code & Unix Deep-Dive", "Algorithms, Subprocesses & Kernels", "TECHNICAL CODE LEVEL")

    doc.add_section_heading("1. Kahn's Algorithm in src/engine.py")
    doc.add_paragraph(
        "The scheduler implements Kahn's topological sort algorithm to order jobs and detect circular dependencies before spawning processes:"
    )

    doc.add_code_block(
        """# Kahn's Algorithm in src/engine.py
in_degree = {jid: 0 for jid in job_map}
adj_list = {jid: [] for jid in job_map}
for jid, job in job_map.items():
  for up in job.get('depends_on', []):
    adj_list[up].append(jid)
    in_degree[jid] += 1
queue = [j for j, d in in_degree.items() if d == 0]
while queue:
  curr = queue.pop(0)
  ordered.append(curr)
  for n in adj_list[curr]:
    in_degree[n] -= 1
    if in_degree[n] == 0:
      queue.append(n)
if len(ordered) != len(job_map):
  raise ValueError('Cyclic dependency!')"""
    )

    doc.add_section_heading("2. True Wall-Clock SLA Calculation")
    doc.add_paragraph(
        "SLA measurement must not rely on CPU execution time; it must measure real wall-clock latency including retry delays:"
    )

    doc.add_code_block(
        """# Measuring Wall-Clock Duration
job_start_dt = datetime.now()
while attempt <= max_attempts:
  exit_code, out, err, dur = execute()
  if exit_code != 0 and attempt < max:
    time.sleep(retry_delay_sec)
    attempt += 1
job_end_dt = datetime.now()
total_sec = (job_end_dt - job_start_dt).total_seconds()
sla_breached = 1 if total_sec > sla_max else 0"""
    )

    doc.add_page_break()

    doc.add_section_heading("3. SQLite WAL Mode Architecture")
    doc.add_paragraph(
        "Database persistence in src/database.py uses SQLite Write-Ahead Logging (WAL) for high concurrency:"
    )

    doc.add_code_block(
        """# WAL Mode & Pragmas in src/database.py
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
conn.execute('PRAGMA foreign_keys = ON;')
conn.execute('PRAGMA journal_mode = WAL;')"""
    )

    doc.add_bullet("Why WAL?", "Writers write to a separate -wal log file. Readers never block writers, and writers never block readers.")
    doc.add_bullet("Upsert Logic", "Uses ON CONFLICT(run_id, job_id) DO UPDATE to ensure idempotent status transitions.")

    doc.add_section_heading("4. Unix Housekeeping Commands")
    doc.add_paragraph(
        "Exact bash commands in jobs/system_housekeeping.sh explained line-by-line:"
    )

    doc.add_card(
        "Unix Command Reference",
        [
            ("Disk Space", "df -h / | awk 'NR==2 {print $5, $4}'"),
            ("Memory Usage", "free -m | awk '/^Mem:/ {print $2, $7}'"),
            ("CPU Load Avg", "awk '{print $1}' /proc/loadavg"),
            ("Zombie Check", "ps aux | awk '$8==\"Z\"' | wc -l"),
            ("Spool Purge", "find spool_tmp/ -name '*.tmp' -delete"),
            ("Daemon Check", "Verifies PIDs & Ports (7005)"),
        ],
    )

    doc.add_callout(
        "ZOMBIE PROCESSES EXPLAINED:",
        "A zombie process (state Z in ps aux) has terminated, but its parent has not read its exit status with wait(). Zombies consume zero CPU/RAM, but they consume PID slots. Kill -9 cannot kill a zombie! You must send SIGCHLD to the parent (kill -s SIGCHLD <ppid>) or restart the parent.",
        kind="warning",
    )

    doc.build()
    return target


# ==============================================================================
# PDF 4: ITIL ServiceNow & SLAs
# ==============================================================================
def build_pdf_04(out_dir: Path) -> Path:
    target = out_dir / "04_ITIL_ServiceNow_and_SLAs.pdf"
    doc = MobilePdfWriter(target, "04 ITIL ServiceNow & SLAs", "MUFG Masterclass")

    doc.add_hero_banner("ITIL & ServiceNow Engine", "Incident Triage & Parent-Child Linking", "ITIL v4 OPERATIONS")

    doc.add_section_heading("1. The 3 Core Operational Rules")

    # Rule A
    doc.add_card(
        "RULE A: Hard Failure ➔ P1 Major Incident",
        [
            ("Trigger", "Process exits non-zero after retries"),
            ("Target Job", "JOB_03_EOD_SETTLEMENT (Exit 2)"),
            ("Priority", "P1 - Critical (Impact 1, Urgency 1)"),
            ("State", "Assigned (Major Incident Bridge)"),
            ("Group", "Core-Banking-DBA-L3"),
            ("Primary SME", "Oracle RAC Escalation Desk"),
            ("Runbook SOP", "KB0041209 (Deadlock Clearing)"),
            ("Diagnostics", "Captures full stderr stack trace"),
        ],
        status_badge="P1 CRITICAL",
    )

    # Rule B
    doc.add_card(
        "RULE B: Cascading Block ➔ Linked Child Ticket",
        [
            ("Trigger", "Downstream job blocked by upstream"),
            ("Target Job", "JOB_04_REG_REPORT (MAS/Fed Report)"),
            ("Priority", "P3 - Moderate (Alert Suppressed)"),
            ("State", "On Hold - Awaiting Upstream"),
            ("Group", "Regulatory-Reporting-L2"),
            ("Parent Incident", "INC0010404 (Linked to JOB_03)"),
            ("Purpose", "Eliminates Command Center alert storms"),
        ],
        status_badge="P3 CHILD",
    )

    doc.add_page_break()

    # Rule C
    doc.add_card(
        "RULE C: Recovered Job with SLA Breach",
        [
            ("Trigger", "Job succeeds but exceeds SLA limit"),
            ("Target Job", "JOB_02_LEDGER_RECON (Balanced $4.28B)"),
            ("Runtime", "3.20s wall-clock (SLA limit: 1.50s)"),
            ("Priority", "P2 - High (Non-outage warning)"),
            ("State", "New"),
            ("Group", "FinControl-GL-Support-L2"),
            ("Runbook SOP", "KB0038912 (Lock Contention Tune)"),
            ("Purpose", "Catches silent pipeline degradation"),
        ],
        status_badge="P2 WARNING",
    )

    doc.add_section_heading("2. ServiceNow Table API REST Outbox")
    doc.add_paragraph(
        "Saved in data/servicenow_outbox/<incident_number>.json formatted for ServiceNow Table API ingestion (POST /api/now/table/incident):"
    )

    doc.add_code_block(
        """// ServiceNow REST Payload Schema
{
  "number": "INC0010404",
  "caller_id": "batchguard.automation",
  "category": "Database Infrastructure",
  "subcategory": "Deadlock & Lock Contention",
  "impact": "1", "urgency": "1",
  "priority": "P1 - Critical",
  "state": "Assigned",
  "assignment_group": "Core-Banking-DBA-L3",
  "assigned_to": "Oracle RAC Escalation Desk",
  "u_kb_article": "KB0041209",
  "parent_incident": null,
  "short_description": "[P1 INCIDENT] Hard Failure in...",
  "work_notes": "Diagnostic stderr: ORA-00060..."
}"""
    )

    doc.add_section_heading("3. Shift Handover Reports")
    doc.add_bullet("CSV Check-Sheet", "Structured tabular export in reports/Daily_Ops_CheckSheet_*.csv for audit logs.")
    doc.add_bullet("HTML Dashboard", "Dark-themed responsive dashboard in reports/Shift_Handover_Dashboard_*.html with KPI cards, action items, and sign-off blocks.")

    doc.build()
    return target


# ==============================================================================
# PDF 5: 15 Tough Q&A & CheatSheet
# ==============================================================================
def build_pdf_05(out_dir: Path) -> Path:
    target = out_dir / "05_15_Tough_Interview_QnA_CheatSheet.pdf"
    doc = MobilePdfWriter(target, "05 15 Q&As & Cheat Sheet", "MUFG Masterclass")

    doc.add_hero_banner("15 Q&As & Cheat Sheet", "Technical Cross-Questions & Flashcards", "MUFG INTERVIEW DRILLS")

    doc.add_section_heading("Top 15 Interview Cross-Questions")

    doc.add_qa_card(
        1,
        "Algorithms",
        "What happens if there is a circular dependency in batch_schedule.json?",
        "Tests understanding of DAG scheduling algorithms.",
        "Kahn's algorithm tracks in-degrees. Cycle nodes never hit in-degree 0. The engine checks if len(ordered) != len(jobs) and raises ValueError immediately before executing any processes.",
    )

    doc.add_qa_card(
        2,
        "Database",
        "Why use SQLite WAL mode instead of PostgreSQL?",
        "Tests distributed systems & high availability knowledge.",
        "For an on-host batch orchestrator agent, local storage prevents external network dependencies. WAL mode allows concurrent reads and writes without file-level locks.",
    )

    doc.add_qa_card(
        3,
        "Reliability",
        "How do you handle a job that hangs indefinitely?",
        "Tests process lifecycle management under failure.",
        "Pass timeout to subprocess.run(..., timeout=sec). On TimeoutExpired, catch exception, call proc.kill(), mark FAILED, and trigger an immediate P1 incident.",
    )

    doc.add_page_break()

    doc.add_qa_card(
        4,
        "SLA Governance",
        "Why measure wall-clock time instead of CPU time?",
        "Tests banking operational awareness.",
        "Banking deadlines depend on absolute clock time. A job taking 0.5s of CPU but sleeping 2 minutes on retry delays the entire core banking window by 2 minutes.",
    )

    doc.add_qa_card(
        5,
        "Testing",
        "How does job_02 handle attempt detection idempotently?",
        "Tests testing design and subprocess environment variables.",
        "Inspects BATCH_ATTEMPT environment variable first, falling back to data/.job_02_recon_state.json. Attempt 1 fails with lock error; Attempt 2 succeeds and unlinks state.",
    )

    doc.add_qa_card(
        6,
        "Unix OS",
        "Walk me through your df and free parsing commands.",
        "Tests practical Linux sysadmin competence.",
        "We use awk to search for the token with % in df -h /, making it resilient to shifting columns. In free -m, we check available memory (column 7) rather than raw free.",
    )

    doc.add_qa_card(
        7,
        "Incident",
        "If /var/log hits 94% disk usage before EOD, what do you do?",
        "Tests emergency L1 triage under pressure.",
        "Run df -h to verify, du -ahx /var/log | sort -rh | head -20 to find runaway logs, lsof +L1 to check for deleted files held open by processes, and gzip old logs.",
    )

    doc.add_qa_card(
        8,
        "Unix OS",
        "What are zombie processes and how do you kill them?",
        "Tests OS kernel process lifecycle knowledge.",
        "Zombies (state Z) have finished execution but their parent hasn't reaped them with wait(). Kill -9 fails on zombies. Send SIGCHLD to the parent or bounce the parent.",
    )

    doc.add_page_break()

    doc.add_qa_card(
        9,
        "Architecture",
        "Why check daemons like controlm-agent and swift-mq?",
        "Tests middleware awareness in financial networks.",
        "Batch scripts rely on external bridges. Control-M agent receives instructions on port 7005; SWIFT MQ listener receives payments on IBM MQ channels. We verify them before batch start.",
    )

    doc.add_qa_card(
        10,
        "Operations",
        "How do you prevent batch_engine.log from filling the disk?",
        "Tests logging best practices.",
        "Configure RotatingFileHandler(maxBytes=50MB, backupCount=10) in Python, and configure Linux logrotate with daily, rotate 30, compress, and copytruncate.",
    )

    doc.add_qa_card(
        11,
        "Banking",
        "Why didn't you auto-retry JOB_04 when it was blocked?",
        "Tests understanding of financial accounting integrity.",
        "JOB_04 was deliberately blocked because EOD settlement failed. Retrying statutory reporting against uncommitted ledger balances causes invalid regulatory returns.",
    )

    doc.add_qa_card(
        12,
        "Operations",
        "If JOB_03 is fixed at 3:15 AM, how do you resume?",
        "Tests disaster recovery & operational restart procedures.",
        "Query SQLite job_runs, confirm JOB_01 and JOB_02 are SUCCESS, bypass them, and resume directly from JOB_03, unblocking JOB_04 upon settlement completion.",
    )

    doc.add_page_break()

    doc.add_qa_card(
        13,
        "ITIL",
        "How does parent-child correlation stop Alert Storms?",
        "Tests ITIL incident deduplication understanding.",
        "Creates 1 primary P1 ticket for the root failure (JOB_03) and marks downstream blocked jobs (JOB_04) as child tickets on hold, focusing everyone on 1 bridge.",
    )

    doc.add_qa_card(
        14,
        "ITIL",
        "Why raise a P2 ticket for JOB_02 if it ended with Exit 0?",
        "Tests performance tuning vs functional success.",
        "Functional success does not equal SLA compliance. Taking 3.20s vs 1.5s SLA window delays downstream cutoffs. P2 ticket alerts GL support to tune lock contention.",
    )

    doc.add_qa_card(
        15,
        "Audit",
        "How does this report satisfy MAS and Fed audit rules?",
        "Tests regulatory and audit compliance knowledge.",
        "MAS TRM and Fed FFIEC require immutable event logs and formal handovers. Our engine provides pre-batch OS telemetry, execution logs, tickets, and analyst sign-offs.",
    )

    doc.add_page_break()

    # FLASHCARD CHEAT SHEET
    doc.add_section_heading("Rapid-Fire Flashcard Cheat Sheet")

    doc.add_card(
        "1. Jobs & Exit Codes",
        [
            ("JOB_01_FX_INGEST", "Exit 0 (Success, 0.63s, SLA 5.0s)"),
            ("JOB_02_LEDGER_RECON", "Exit 0 Att 2 (SLA BREACH 3.20s > 1.5s)"),
            ("JOB_03_EOD_SETTLEMENT", "Exit 2 Att 3 (FAILED, Deadlock ORA-00060)"),
            ("JOB_04_REG_REPORT", "Exit - (BLOCKED_BY_UPSTREAM)"),
        ],
    )

    doc.add_card(
        "2. Incidents & Runbooks",
        [
            ("INC0010404 (P1)", "JOB_03 | Core-Banking-DBA-L3 | KB0041209"),
            ("INC0010405 (P2)", "JOB_02 | FinControl-GL-Support-L2 | KB0038912"),
            ("INC0010406 (P3)", "JOB_04 | Regulatory-Reporting-L2 | Parent: INC0010404"),
        ],
    )

    doc.add_card(
        "3. Linux Telemetry & Daemons",
        [
            ("Disk Usage", "df -h / (< 85% threshold, 0.0% measured)"),
            ("Memory Usage", "free -m (< 90% threshold, 70.8% measured)"),
            ("CPU Load (1m)", "/proc/loadavg (< 4.0 threshold, 0.96 measured)"),
            ("Zombies", "ps aux | awk '$8==\"Z\"' (0 detected)"),
            ("Spool Purge", "3 files purged from data/spool_tmp/"),
            ("Daemons Verified", "controlm (7005), swift-mq, as400"),
        ],
    )

    doc.add_card(
        "4. CLI Commands Quick Reference",
        [
            ("Run Full Batch", "python3 main.py --run-batch"),
            ("Inspect Database", "python3 main.py --show-db"),
            ("View CSV Report", "cat reports/Daily_Ops_CheckSheet_*.csv"),
            ("View HTML Report", "google-chrome reports/Shift_Handover_*.html"),
            ("View Outbox REST", "cat data/servicenow_outbox/INC0010404.json"),
        ],
    )

    doc.build()
    return target


# ==============================================================================
# Main Orchestrator
# ==============================================================================
def main():
    print("=" * 80)
    print(" FINOPS-BATCHGUARD: MOBILE-FIRST PDF GENERATOR")
    print(" Target: 4.5\" x 8.0\" Mobile E-Reader Portrait (High-Contrast, Zero-Clipping)")
    print(" Output Directory: docs/mobile_pdfs/")
    print("=" * 80)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = [
        ("01_Pitch_and_Banking_Domain.pdf", build_pdf_01),
        ("02_Architecture_and_ControlM_Map.pdf", build_pdf_02),
        ("03_Code_and_Unix_DeepDive.pdf", build_pdf_03),
        ("04_ITIL_ServiceNow_and_SLAs.pdf", build_pdf_04),
        ("05_15_Tough_Interview_QnA_CheatSheet.pdf", build_pdf_05),
    ]

    generated_files = []
    for filename, builder_func in targets:
        print(f"Generating {filename}...")
        path = builder_func(OUTPUT_DIR)
        size_kb = path.stat().st_size / 1024.0
        generated_files.append((filename, path, size_kb))
        print(f"  [OK] {filename} ({size_kb:.1f} KB)")

    print("\n" + "=" * 80)
    print(" ALL 5 MOBILE-OPTIMIZED PDFS GENERATED SUCCESSFULLY:")
    for fn, p, sz in generated_files:
        print(f" - {fn:<42} | Size: {sz:>5.1f} KB | Path: {p}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

