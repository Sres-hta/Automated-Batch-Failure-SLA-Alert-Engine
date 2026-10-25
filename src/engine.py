"""
Core Orchestration and Dependency Engine for FinOps-BatchGuard.
Handles DAG dependency resolution, job execution, auto-retry loops, SLA tracking, and status persistence.
"""

import os
import json
import time
import shlex
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src import database

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "batch_schedule.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class BatchEngine:
    def __init__(
        self,
        config_path: Optional[Path] = None,
        db_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.db_path = db_path or database.DEFAULT_DB_PATH
        self.logger = logger or logging.getLogger("batch_engine")
        self.schedule_config: Dict[str, Any] = {}
        self.jobs: List[Dict[str, Any]] = []

    def load_schedule(self) -> None:
        """
        Loads and validates batch schedule configuration from JSON file.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.schedule_config = json.load(f)

        raw_jobs = self.schedule_config.get("jobs", [])
        if not raw_jobs:
            raise ValueError("No jobs defined in batch schedule configuration.")

        # Validate job fields
        required_fields = {"job_id", "job_name", "command", "depends_on"}
        seen_ids = set()
        for job in raw_jobs:
            missing = required_fields - set(job.keys())
            if missing:
                raise ValueError(f"Job {job.get('job_id', 'UNKNOWN')} missing required fields: {missing}")
            job_id = job["job_id"]
            if job_id in seen_ids:
                raise ValueError(f"Duplicate job_id found in schedule: {job_id}")
            seen_ids.add(job_id)

        self.jobs = raw_jobs
        self.logger.info(f"Loaded schedule '{self.schedule_config.get('batch_name')}' with {len(self.jobs)} jobs.")

    def resolve_execution_order(self) -> List[Dict[str, Any]]:
        """
        Performs topological sort to determine valid execution order based on depends_on.
        Detects circular dependencies or invalid upstream references.
        """
        job_map = {job["job_id"]: job for job in self.jobs}
        in_degree: Dict[str, int] = {job_id: 0 for job_id in job_map}
        adj_list: Dict[str, List[str]] = {job_id: [] for job_id in job_map}

        for job_id, job in job_map.items():
            for upstream in job.get("depends_on", []):
                if upstream not in job_map:
                    raise ValueError(f"Job '{job_id}' depends on undefined upstream job '{upstream}'.")
                adj_list[upstream].append(job_id)
                in_degree[job_id] += 1

        # Queue of jobs with zero dependencies
        queue = [job_id for job_id, deg in in_degree.items() if deg == 0]
        ordered_ids: List[str] = []

        while queue:
            # Deterministic ordering by job_id for consistent execution
            queue.sort()
            curr = queue.pop(0)
            ordered_ids.append(curr)

            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered_ids) != len(job_map):
            raise ValueError("Cyclic dependency detected in batch schedule configuration.")

        return [job_map[jid] for jid in ordered_ids]

    def _execute_single_attempt(
        self,
        command: str,
        run_id: str,
        batch_date: str,
        job_id: str,
        attempt: int,
    ) -> Tuple[int, str, str, float]:
        """
        Executes a job command via subprocess, capturing exit code, stdout, stderr, and duration.
        """
        env = os.environ.copy()
        env["BATCH_RUN_ID"] = run_id
        env["BATCH_DATE"] = batch_date
        env["BATCH_JOB_ID"] = job_id
        env["BATCH_ATTEMPT"] = str(attempt)

        start_time = time.perf_counter()
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        duration = time.perf_counter() - start_time
        return proc.returncode, proc.stdout, proc.stderr, duration

    def run_batch(
        self,
        run_id: Optional[str] = None,
        batch_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full batch schedule:
          - Initializes database
          - Resolves DAG order
          - Evaluates dependencies (marks BLOCKED_BY_UPSTREAM if upstream failed)
          - Executes jobs with auto-retry logic
          - Evaluates SLAs
          - Persists state to SQLite
        """
        database.init_db(self.db_path)
        self.load_schedule()
        ordered_jobs = self.resolve_execution_order()

        now = datetime.now()
        run_id = run_id or f"RUN-{now.strftime('%Y%m%d-%H%M%S')}"
        batch_date = batch_date or now.strftime("%Y-%m-%d")

        self.logger.info("=" * 80)
        self.logger.info(f"STARTING BATCH RUN: {run_id} | DATE: {batch_date}")
        self.logger.info(f"Schedule: {self.schedule_config.get('batch_name', 'Unnamed')}")
        self.logger.info(f"Resolved Execution Order: {' -> '.join(j['job_id'] for j in ordered_jobs)}")
        self.logger.info("=" * 80)

        # In-memory tracking of status per job
        job_status_map: Dict[str, str] = {}
        batch_summary: List[Dict[str, Any]] = []

        batch_start_ts = datetime.now()

        for job in ordered_jobs:
            job_id = job["job_id"]
            job_name = job["job_name"]
            command = job["command"]
            depends_on = job.get("depends_on", [])
            max_retries = int(job.get("max_retries", 0))
            retry_delay_sec = float(job.get("retry_delay_sec", 1.0))
            sla_max_duration_sec = float(job.get("sla_max_duration_sec", 10.0))
            criticality = job.get("criticality", "P3")

            self.logger.info("-" * 60)
            self.logger.info(f"EVALUATING JOB: [{job_id}] - {job_name} ({criticality})")
            if depends_on:
                self.logger.info(f"Dependencies: {depends_on}")

            # Check if any upstream job failed or was blocked
            blocked_upstream = None
            for upstream_id in depends_on:
                upstream_status = job_status_map.get(upstream_id)
                if upstream_status != "SUCCESS":
                    blocked_upstream = (upstream_id, upstream_status)
                    break

            if blocked_upstream:
                up_id, up_stat = blocked_upstream
                block_reason = f"Dependency failure: Upstream job '{up_id}' status is '{up_stat}'."
                self.logger.warning(f"[BLOCKED] Job [{job_id}] marked as BLOCKED_BY_UPSTREAM. Reason: {block_reason}")

                now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                database.upsert_job_run(
                    run_id=run_id,
                    batch_date=batch_date,
                    job_id=job_id,
                    job_name=job_name,
                    status="BLOCKED_BY_UPSTREAM",
                    attempt_count=0,
                    exit_code=None,
                    start_time=now_iso,
                    end_time=now_iso,
                    duration_sec=0.0,
                    sla_breached=0,
                    stdout_log="",
                    stderr_log=f"[ENGINE] Execution bypassed. {block_reason}",
                    db_path=self.db_path,
                )

                job_status_map[job_id] = "BLOCKED_BY_UPSTREAM"
                batch_summary.append({
                    "job_id": job_id,
                    "job_name": job_name,
                    "criticality": criticality,
                    "status": "BLOCKED_BY_UPSTREAM",
                    "attempt_count": 0,
                    "exit_code": None,
                    "duration_sec": 0.0,
                    "sla_breached": False,
                    "sla_limit_sec": sla_max_duration_sec,
                })
                continue

            # Execute Job with Auto-Retry Logic
            max_attempts = 1 + max_retries
            current_attempt = 1
            final_status = "FAILED"
            final_exit_code = None
            accumulated_stdout: List[str] = []
            accumulated_stderr: List[str] = []
            total_duration_sec = 0.0

            job_overall_start_dt = datetime.now()
            start_iso = job_overall_start_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Initial status record
            database.upsert_job_run(
                run_id=run_id,
                batch_date=batch_date,
                job_id=job_id,
                job_name=job_name,
                status="RUNNING",
                attempt_count=1,
                exit_code=None,
                start_time=start_iso,
                end_time=None,
                duration_sec=0.0,
                sla_breached=0,
                stdout_log="",
                stderr_log="",
                db_path=self.db_path,
            )

            while current_attempt <= max_attempts:
                att_start_dt = datetime.now()
                att_start_iso = att_start_dt.strftime("%Y-%m-%d %H:%M:%S")

                self.logger.info(
                    f"Executing [{job_id}] attempt {current_attempt}/{max_attempts} "
                    f"via '{command}'..."
                )

                exit_code, stdout, stderr, attempt_dur = self._execute_single_attempt(
                    command=command,
                    run_id=run_id,
                    batch_date=batch_date,
                    job_id=job_id,
                    attempt=current_attempt,
                )

                total_duration_sec += attempt_dur
                att_end_dt = datetime.now()
                att_end_iso = att_end_dt.strftime("%Y-%m-%d %H:%M:%S")

                if stdout:
                    accumulated_stdout.append(f"--- Attempt {current_attempt} STDOUT ---\n{stdout}")
                if stderr:
                    accumulated_stderr.append(f"--- Attempt {current_attempt} STDERR ---\n{stderr}")

                final_exit_code = exit_code

                if exit_code == 0:
                    final_status = "SUCCESS"
                    self.logger.info(
                        f"[SUCCESS] Job [{job_id}] succeeded on attempt {current_attempt} "
                        f"(duration: {attempt_dur:.2f}s)."
                    )
                    # Record attempt audit
                    database.record_attempt(
                        run_id=run_id,
                        batch_date=batch_date,
                        job_id=job_id,
                        job_name=job_name,
                        attempt_number=current_attempt,
                        status="SUCCESS",
                        exit_code=exit_code,
                        start_time=att_start_iso,
                        end_time=att_end_iso,
                        duration_sec=attempt_dur,
                        stdout_log=stdout,
                        stderr_log=stderr,
                        db_path=self.db_path,
                    )
                    break
                else:
                    # Non-zero exit code
                    if current_attempt < max_attempts:
                        self.logger.warning(
                            f"[RETRY] Job [{job_id}] failed attempt {current_attempt} "
                            f"with exit code {exit_code}. Status: RETRYING. "
                            f"Waiting {retry_delay_sec:.1f}s before retry..."
                        )
                        # Record attempt audit
                        database.record_attempt(
                            run_id=run_id,
                            batch_date=batch_date,
                            job_id=job_id,
                            job_name=job_name,
                            attempt_number=current_attempt,
                            status="RETRYING",
                            exit_code=exit_code,
                            start_time=att_start_iso,
                            end_time=att_end_iso,
                            duration_sec=attempt_dur,
                            stdout_log=stdout,
                            stderr_log=stderr,
                            db_path=self.db_path,
                        )
                        # Update authoritative status to RETRYING in DB
                        database.upsert_job_run(
                            run_id=run_id,
                            batch_date=batch_date,
                            job_id=job_id,
                            job_name=job_name,
                            status="RETRYING",
                            attempt_count=current_attempt,
                            exit_code=exit_code,
                            start_time=start_iso,
                            end_time=att_end_iso,
                            duration_sec=total_duration_sec,
                            sla_breached=0,
                            stdout_log="\n".join(accumulated_stdout),
                            stderr_log="\n".join(accumulated_stderr),
                            db_path=self.db_path,
                        )
                        time.sleep(retry_delay_sec)
                        current_attempt += 1
                    else:
                        final_status = "FAILED"
                        self.logger.error(
                            f"[FAILED] Job [{job_id}] permanently FAILED after {current_attempt} "
                            f"attempt(s) with exit code {exit_code}."
                        )
                        # Record final failed attempt audit
                        database.record_attempt(
                            run_id=run_id,
                            batch_date=batch_date,
                            job_id=job_id,
                            job_name=job_name,
                            attempt_number=current_attempt,
                            status="FAILED",
                            exit_code=exit_code,
                            start_time=att_start_iso,
                            end_time=att_end_iso,
                            duration_sec=attempt_dur,
                            stdout_log=stdout,
                            stderr_log=stderr,
                            db_path=self.db_path,
                        )
                        break

            job_overall_end_dt = datetime.now()
            end_iso = job_overall_end_dt.strftime("%Y-%m-%d %H:%M:%S")
            total_duration_sec = (job_overall_end_dt - job_overall_start_dt).total_seconds()

            # Evaluate SLA
            is_sla_breached = 1 if total_duration_sec > sla_max_duration_sec else 0
            if is_sla_breached:
                self.logger.warning(
                    f"[SLA BREACH] Job [{job_id}] duration ({total_duration_sec:.2f}s) "
                    f"exceeded SLA threshold ({sla_max_duration_sec:.2f}s)!"
                )

            # Persist authoritative final state
            database.upsert_job_run(
                run_id=run_id,
                batch_date=batch_date,
                job_id=job_id,
                job_name=job_name,
                status=final_status,
                attempt_count=current_attempt,
                exit_code=final_exit_code,
                start_time=start_iso,
                end_time=end_iso,
                duration_sec=round(total_duration_sec, 3),
                sla_breached=is_sla_breached,
                stdout_log="\n".join(accumulated_stdout),
                stderr_log="\n".join(accumulated_stderr),
                db_path=self.db_path,
            )

            job_status_map[job_id] = final_status
            batch_summary.append({
                "job_id": job_id,
                "job_name": job_name,
                "criticality": criticality,
                "status": final_status,
                "attempt_count": current_attempt,
                "exit_code": final_exit_code,
                "duration_sec": round(total_duration_sec, 3),
                "sla_breached": bool(is_sla_breached),
                "sla_limit_sec": sla_max_duration_sec,
            })

        batch_end_ts = datetime.now()
        batch_total_duration = (batch_end_ts - batch_start_ts).total_seconds()

        self.logger.info("=" * 80)
        self.logger.info(f"BATCH RUN COMPLETED: {run_id} in {batch_total_duration:.2f}s")
        self.logger.info("=" * 80)

        return {
            "run_id": run_id,
            "batch_date": batch_date,
            "schedule_name": self.schedule_config.get("batch_name"),
            "start_time": batch_start_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": batch_end_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_sec": round(batch_total_duration, 3),
            "jobs": batch_summary,
        }

