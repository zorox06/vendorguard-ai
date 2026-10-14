"""Monitoring Runs and Leased Job REST routes for VendorGuard AI.

Implements Sections 5, 6, 13, & 16 of the Blueprint:
- Enqueues durable monitoring runs with HTTP 202 Accepted
- Idempotency key protection
- Progress polling and summary telemetry
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status, BackgroundTasks, Depends, HTTPException
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.adapters.storage import get_sync_session, SyncSessionLocal
from backend.app.models.schema import MonitoringRun
from backend.worker import process_monitoring_run

router = APIRouter(prefix="/api/monitoring-runs", tags=["Monitoring Runs"])

DEFAULT_TENANT_ID = "tenant-default"


def run_worker_task(job_id: str):
    """Background task runner for executing monitoring run."""
    db = SyncSessionLocal()
    try:
        process_monitoring_run(job_id=job_id, db=db)
    finally:
        db.close()


@router.get("")
def list_monitoring_runs(tenant_id: str = DEFAULT_TENANT_ID, db: Session = Depends(get_sync_session)):
    """Returns list of recent monitoring runs."""
    runs = (
        db.query(MonitoringRun)
        .filter(MonitoringRun.tenant_id == tenant_id)
        .order_by(MonitoringRun.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": r.id,
            "as_of": r.as_of.isoformat() if r.as_of else None,
            "status": r.status,
            "attempt_count": r.attempt_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "summary": r.summary_counts or {},
        }
        for r in runs
    ]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def trigger_monitoring_run(
    background_tasks: BackgroundTasks,
    tenant_id: str = DEFAULT_TENANT_ID,
    idempotency_key: Optional[str] = None,
    db: Session = Depends(get_sync_session),
):
    """Enqueues a durable monitoring run and returns HTTP 202 Accepted."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not idempotency_key:
        idempotency_key = f"run-idem-{uuid.uuid4().hex[:12]}"

    # Check existing idempotency
    existing = (
        db.query(MonitoringRun)
        .filter(MonitoringRun.tenant_id == tenant_id, MonitoringRun.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        return {
            "job_id": existing.id,
            "status": existing.status,
            "message": "Existing run with idempotency key found",
            "summary": existing.summary_counts,
        }

    job_id = f"run-{uuid.uuid4().hex[:8]}"
    run_obj = MonitoringRun(
        id=job_id,
        tenant_id=tenant_id,
        as_of=now,
        status="pending",
        attempt_count=0,
        idempotency_key=idempotency_key,
        summary_counts={
            "suppliers_checked": 0,
            "high_risk_flagged": 0,
            "watch_flagged": 0,
            "shortage_scenarios": 0,
            "evidence_found": 0,
        },
    )
    db.add(run_obj)
    db.commit()

    # Enqueue background execution
    background_tasks.add_task(run_worker_task, job_id)

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Monitoring run enqueued for durable execution",
    }


@router.get("/{job_id}")
def get_run_status(job_id: str, db: Session = Depends(get_sync_session)):
    """Returns status and live progress for a specific job."""
    run = db.query(MonitoringRun).filter(MonitoringRun.id == job_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Monitoring run not found")
    return {
        "id": run.id,
        "as_of": run.as_of.isoformat() if run.as_of else None,
        "status": run.status,
        "attempt_count": run.attempt_count,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "summary": run.summary_counts or {},
    }
