"""Supplier REST routes for VendorGuard AI.

Implements Sections 7 & 13 of the Blueprint:
- List suppliers with latest assessment and risk band
- Detailed supplier dossier with order line history, factor breakdown, materials, and verified evidence
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.adapters.storage import get_sync_session
from backend.app.models.schema import (
    Supplier,
    Assessment,
    AssessmentEvidence,
    PurchaseOrderLine,
    Receipt,
    SupplierMaterial,
    Material,
    EvidenceItem,
)

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])

DEFAULT_TENANT_ID = "tenant-default"


@router.get("")
def list_suppliers(tenant_id: str = DEFAULT_TENANT_ID, db: Session = Depends(get_sync_session)):
    """Returns all suppliers for tenant with their latest calculated risk indicators."""
    suppliers = (
        db.query(Supplier)
        .filter(Supplier.tenant_id == tenant_id)
        .order_by(Supplier.legal_name.asc())
        .all()
    )

    if not suppliers:
        return []

    results = []
    for s in suppliers:
        # Get latest assessment
        latest_assessment = (
            db.query(Assessment)
            .filter(Assessment.supplier_id == s.id)
            .order_by(Assessment.created_at.desc())
            .first()
        )

        materials_supplied = [
            sm.material.name for sm in s.materials if sm.material
        ]

        if latest_assessment:
            feat = latest_assessment.features or {}
            internal = feat.get("internal") or {}
            external = feat.get("external") or {}
            score = latest_assessment.index_score
            band = latest_assessment.band or "low"

            results.append({
                "id": s.id,
                "legal_name": s.legal_name,
                "aliases": s.aliases or [],
                "location": s.location or "Unknown",
                "materials_supplied": materials_supplied,
                "total_due_lines": internal.get("total_due_lines", 0),
                "on_time_rate": internal.get("on_time_fulfillment_rate", 1.0),
                "late_fraction_L": internal.get("late_fraction_L", 0.0),
                "delay_factor_D": internal.get("delay_factor_D", 0.0),
                "trend_factor_T": internal.get("deterioration_factor_T", 0.0),
                "shortfall_F": internal.get("fulfillment_shortfall_F", 0.0),
                "internal_index_I": internal.get("internal_index_I", round((score or 0.0) * 0.9, 1)),
                "external_index_E": external.get("max_event_score"),
                "blended_risk_R": score if score is not None else 0.0,
                "band": band,
                "external_status": external.get("status", "no_relevant_evidence"),
                "critical_override": band == "high" and (score is not None and score < 60.0),
                "last_assessed": latest_assessment.created_at.isoformat(),
            })
        else:
            results.append({
                "id": s.id,
                "legal_name": s.legal_name,
                "aliases": s.aliases or [],
                "location": s.location or "Unknown",
                "materials_supplied": materials_supplied,
                "total_due_lines": len(s.order_lines),
                "on_time_rate": 1.0,
                "late_fraction_L": 0.0,
                "delay_factor_D": 0.0,
                "trend_factor_T": 0.0,
                "shortfall_F": 0.0,
                "internal_index_I": 0.0,
                "external_index_E": None,
                "blended_risk_R": 0.0,
                "band": "low",
                "external_status": "no_relevant_evidence",
                "critical_override": False,
                "last_assessed": s.created_at.isoformat(),
            })

    return results


@router.get("/{supplier_id}")
def get_supplier(supplier_id: str, db: Session = Depends(get_sync_session)):
    """Returns detailed dossier for a specific supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        # Check by legal_name prefix if ID not direct match
        supplier = db.query(Supplier).filter(Supplier.legal_name.ilike(f"%{supplier_id}%")).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    latest_assessment = (
        db.query(Assessment)
        .filter(Assessment.supplier_id == supplier.id)
        .order_by(Assessment.created_at.desc())
        .first()
    )

    materials_data = []
    for sm in supplier.materials:
        if sm.material:
            materials_data.append({
                "material_id": sm.material.id,
                "material_name": sm.material.name,
                "canonical_unit": sm.material.canonical_unit,
                "criticality": sm.material.criticality,
                "normal_lead_time_days": sm.normal_lead_time_days,
                "is_approved": sm.is_approved,
            })

    # Order line delivery history
    order_lines_data = []
    po_lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.supplier_id == supplier.id)
        .order_by(PurchaseOrderLine.committed_due_date.desc())
        .limit(50)
        .all()
    )
    for pol in po_lines:
        tot_accepted = sum(r.accepted_quantity for r in pol.receipts)
        is_on_time = any(r.accepted_quantity >= pol.ordered_quantity and r.received_at.date() <= pol.committed_due_date for r in pol.receipts)
        order_lines_data.append({
            "po_number": pol.po_number,
            "material_name": pol.material_id,
            "ordered_quantity": pol.ordered_quantity,
            "unit": pol.unit,
            "committed_due_date": pol.committed_due_date.isoformat(),
            "accepted_quantity": tot_accepted,
            "is_on_time": is_on_time,
        })

    # Evidence items
    evidence_data = []
    evidence_items = (
        db.query(EvidenceItem)
        .filter(EvidenceItem.supplier_id == supplier.id)
        .all()
    )
    for ev in evidence_items:
        evidence_data.append({
            "id": ev.id,
            "source_url": ev.source_url,
            "publisher": ev.publisher,
            "published_at": ev.published_at.isoformat(),
            "event_type": ev.event_type,
            "entity_match": ev.entity_match,
            "severity": ev.severity,
            "reliability_factor": ev.reliability_factor,
            "freshness_factor": ev.freshness_factor,
            "supporting_excerpt": ev.supporting_excerpt,
            "is_synthetic": ev.is_synthetic,
        })

    internal_feats = {}
    external_feats = {}
    if latest_assessment and latest_assessment.features:
        internal_feats = latest_assessment.features.get("internal") or {}
        external_feats = latest_assessment.features.get("external") or {}

    return {
        "id": supplier.id,
        "legal_name": supplier.legal_name,
        "aliases": supplier.aliases or [],
        "domain": supplier.domain,
        "location": supplier.location or "Unknown",
        "materials_supplied": [m["material_name"] for m in materials_data],
        "materials": materials_data,
        "total_due_lines": internal_feats.get("total_due_lines", len(po_lines)),
        "on_time_rate": internal_feats.get("on_time_fulfillment_rate", 1.0),
        "late_fraction_L": internal_feats.get("late_fraction_L", 0.0),
        "delay_factor_D": internal_feats.get("delay_factor_D", 0.0),
        "trend_factor_T": internal_feats.get("deterioration_factor_T", 0.0),
        "shortfall_F": internal_feats.get("fulfillment_shortfall_F", 0.0),
        "internal_index_I": internal_feats.get("internal_index_I", 0.0),
        "external_index_E": external_feats.get("max_event_score"),
        "blended_risk_R": latest_assessment.index_score if latest_assessment else 0.0,
        "band": latest_assessment.band if latest_assessment else "low",
        "external_status": external_feats.get("status", "no_relevant_evidence"),
        "last_assessed": latest_assessment.created_at.isoformat() if latest_assessment else supplier.created_at.isoformat(),
        "order_lines": order_lines_data,
        "evidence_items": evidence_data,
    }
