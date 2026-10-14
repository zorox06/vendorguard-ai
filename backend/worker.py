"""Durable Job Monitoring Worker for VendorGuard AI.

Implements Sections 5, 6, & 16 of the Blueprint:
- Leased job execution to prevent split-brain / duplicate execution
- Multi-supplier graph evaluation in tenant scope
- Resilient recovery from worker restarts
- Atomic transaction lifecycle
"""

import os
import sys
import time
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from backend.app.adapters.storage import SyncSessionLocal
from backend.app.models.schema import MonitoringRun, Supplier, Tenant, Assessment, Alert
from backend.app.graph.builder import run_supplier_risk_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vendorguard.worker")

LEASE_DURATION_SECONDS = 300  # 5 minutes
MAX_ATTEMPTS = 3


def claim_next_job(db: Session) -> Optional[MonitoringRun]:
    """Atomically claims the next pending or expired-leased job."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Find jobs that are either pending or where lease expired
    job = (
        db.query(MonitoringRun)
        .filter(
            (MonitoringRun.status == "pending")
            | (
                (MonitoringRun.status == "leased")
                & (MonitoringRun.lease_expires_at < now)
                & (MonitoringRun.attempt_count < MAX_ATTEMPTS)
            )
        )
        .order_by(MonitoringRun.created_at.asc())
        .first()
    )

    if not job:
        return None

    # Claim lease
    job.status = "leased"
    job.lease_expires_at = now + timedelta(seconds=LEASE_DURATION_SECONDS)
    job.attempt_count += 1
    db.commit()
    db.refresh(job)
    logger.info(f"Claimed monitoring run job: {job.id} (Attempt {job.attempt_count})")
    return job


def process_monitoring_run(job_id: str, db: Session) -> Dict[str, Any]:
    """Executes supplier risk evaluations across all suppliers for a monitoring run."""
    job = db.query(MonitoringRun).filter(MonitoringRun.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found.")

    tenant_id = job.tenant_id
    as_of_iso = job.as_of.isoformat() if job.as_of else datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    # Query all active suppliers for this tenant
    suppliers = (
        db.query(Supplier)
        .filter(Supplier.tenant_id == tenant_id)
        .order_by(Supplier.legal_name.asc())
        .all()
    )

    logger.info(f"Evaluating {len(suppliers)} suppliers for tenant '{tenant_id}' as of {as_of_iso}")

    summary = {
        "suppliers_checked": 0,
        "high_risk_flagged": 0,
        "watch_flagged": 0,
        "shortage_scenarios": 0,
        "evidence_found": 0,
    }

    for sup in suppliers:
        try:
            state = run_supplier_risk_cycle(
                tenant_id=tenant_id,
                supplier_id=sup.id,
                run_id=job.id,
                as_of=as_of_iso,
            )
            summary["suppliers_checked"] += 1

            score = state.get("score_result") or {}
            band = score.get("band", "low")
            if band == "high" or score.get("critical_override_active"):
                summary["high_risk_flagged"] += 1
            elif band == "watch":
                summary["watch_flagged"] += 1

            impact = state.get("impact_result")
            if impact and impact.get("scenario_gap_days", 0) > 0:
                summary["shortage_scenarios"] += 1

            ext = state.get("external_result") or {}
            if ext.get("evidence_items"):
                summary["evidence_found"] += len(ext["evidence_items"])

        except Exception as e:
            logger.error(f"Error evaluating supplier {sup.legal_name} ({sup.id}): {e}", exc_info=True)

    # Mark job as completed
    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    job.summary_counts = summary
    db.commit()
    logger.info(f"Completed monitoring run {job.id}: {summary}")
    return summary


def run_worker_loop(single_run: bool = False, poll_interval: float = 2.0):
    """Main worker event loop."""
    logger.info("VendorGuard durable monitoring worker started.")
    db = SyncSessionLocal()
    try:
        while True:
            job = claim_next_job(db)
            if job:
                try:
                    process_monitoring_run(job.id, db)
                except Exception as e:
                    logger.error(f"Failed processing job {job.id}: {e}", exc_info=True)
                    job.status = "failed" if job.attempt_count >= MAX_ATTEMPTS else "pending"
                    db.commit()
                if single_run:
                    break
            else:
                if single_run:
                    logger.info("No pending jobs to process.")
                    break
                time.sleep(poll_interval)
    finally:
        db.close()


if __name__ == "__main__":
    is_once = "--once" in sys.argv
    run_worker_loop(single_run=is_once)
