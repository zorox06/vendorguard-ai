"""Alerts and Feedback REST routes for VendorGuard AI.

Implements Sections 12 & 13 of the Blueprint:
- Database-backed alert listing and triage
- Grounded explanation with citation chips
- Alert state machine: open -> acknowledged -> resolved / dismissed
- Reviewer feedback recording stored separately from ground truth labels
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.adapters.storage import get_sync_session
from backend.app.models.schema import Alert, AlertFeedback, Assessment, Supplier

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

DEFAULT_TENANT_ID = "tenant-default"


class AlertUpdatePayload(BaseModel):
    status: str
    reason: Optional[str] = None
    actor: Optional[str] = "purchasing_manager"


class FeedbackPayload(BaseModel):
    reviewer_id: str = "purchasing_manager"
    disposition: str  # useful, false_alarm, unhelpful
    reason: Optional[str] = None


@router.get("")
def list_alerts(
    status_filter: Optional[str] = None,
    tenant_id: str = DEFAULT_TENANT_ID,
    db: Session = Depends(get_sync_session),
):
    """Returns alerts requiring attention, sorted by priority."""
    query = (
        db.query(Alert)
        .filter(Alert.tenant_id == tenant_id)
        .order_by(Alert.created_at.desc())
    )
    if status_filter:
        query = query.filter(Alert.status == status_filter)

    alerts = query.all()
    results = []
    for a in alerts:
        sup_name = "Supplier"
        mat_name = "Packaging Material"
        sup_id = ""
        if a.assessment and a.assessment.supplier:
            sup_name = a.assessment.supplier.legal_name
            sup_id = a.assessment.supplier.id
            if a.assessment.supplier.materials:
                mat_name = a.assessment.supplier.materials[0].material.name

        expl = a.grounded_explanation or {}
        results.append({
            "id": a.id,
            "supplier_id": sup_id,
            "supplier_name": sup_name,
            "material_name": expl.get("impact_assumptions", {}).get("material", mat_name),
            "incident_key": a.incident_key,
            "severity": a.severity,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else datetime.now(timezone.utc).isoformat(),
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            "acknowledged_by": a.acknowledged_by,
            "grounded_explanation": expl,
            "feedback_count": len(a.feedback),
        })

    return results


@router.get("/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_sync_session)):
    """Returns detailed alert record."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    sup_name = "Supplier"
    sup_id = ""
    if alert.assessment and alert.assessment.supplier:
        sup_name = alert.assessment.supplier.legal_name
        sup_id = alert.assessment.supplier.id

    expl = alert.grounded_explanation or {}
    return {
        "id": alert.id,
        "supplier_id": sup_id,
        "supplier_name": sup_name,
        "material_name": expl.get("impact_assumptions", {}).get("material", "Packaging Material"),
        "incident_key": alert.incident_key,
        "severity": alert.severity,
        "status": alert.status,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "acknowledged_by": alert.acknowledged_by,
        "grounded_explanation": expl,
        "feedbacks": [
            {
                "id": f.id,
                "reviewer_id": f.reviewer_id,
                "disposition": f.disposition,
                "reason": f.reason,
                "created_at": f.created_at.isoformat(),
            }
            for f in alert.feedback
        ],
    }


@router.patch("/{alert_id}")
def update_alert(alert_id: str, payload: AlertUpdatePayload, db: Session = Depends(get_sync_session)):
    """Updates alert status (acknowledged, resolved, dismissed)."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = payload.status
    if payload.status in ["acknowledged", "resolved"]:
        alert.acknowledged_at = datetime.now(timezone.utc).replace(tzinfo=None)
        alert.acknowledged_by = payload.actor or "purchasing_manager"

    db.commit()
    db.refresh(alert)
    return {"id": alert.id, "status": alert.status, "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None}


@router.post("/{alert_id}/feedback")
def submit_feedback(alert_id: str, payload: FeedbackPayload, db: Session = Depends(get_sync_session)):
    """Records human usefulness feedback on an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    feedback = AlertFeedback(
        alert_id=alert.id,
        reviewer_id=payload.reviewer_id,
        disposition=payload.disposition,
        reason=payload.reason,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return {"status": "recorded", "feedback_id": feedback.id, "disposition": feedback.disposition}
