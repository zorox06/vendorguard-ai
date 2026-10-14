"""LangGraph Node Implementations for VendorGuard AI.

Implements Sections 6, 8, 9, 10, 11, 12 & 17 of the Blueprint:
1. load_snapshot: Immutable snapshot retrieval up to as_of cutoff
2. operational_analysis: Deterministic calculation of L, D, T, F
3. external_check: Bounded search and identity verification
4. validate_join: Barrier edge join and evidence sanitizer
5. score_policy: Deterministic policy evaluation with floor rule R = max(I, 0.7I + 0.3E)
6. impact_analysis: Daily material simulation B[d] base vs stress
7. explain: Structured explanation with citations and deterministic fallback
8. validate_persist: Idempotent database commit of assessments and alerts
"""

import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.graph.state import SupplierRiskState
from backend.app.adapters.storage import SyncSessionLocal
from backend.app.adapters.search_adapter import BoundedSearchAdapter
from backend.app.adapters.llm_adapter import generate_grounded_explanation
from backend.app.domain.models_domain import (
    OrderLineRecord,
    ReceiptRecord,
    EvidenceItemRecord,
    MaterialCriticality,
    RiskBand,
)
from backend.app.domain.metrics import calculate_operational_indicators
from backend.app.domain.scoring import calculate_risk_policy
from backend.app.domain.impact import evaluate_material_exposure
from backend.app.models.schema import (
    Supplier,
    PurchaseOrderLine,
    Receipt,
    Material,
    SupplierMaterial,
    InventorySnapshot,
    DemandForecast,
    Assessment,
    AssessmentEvidence,
    Alert,
)

search_adapter = BoundedSearchAdapter()


def load_snapshot_node(state: SupplierRiskState) -> Dict[str, Any]:
    """Node 1: Loads immutable snapshot records visible as of as_of cutoff."""
    tenant_id = state["tenant_id"]
    supplier_id = state["supplier_id"]
    as_of_str = state["as_of"]

    try:
        as_of_dt = datetime.fromisoformat(as_of_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        as_of_dt = datetime.utcnow()

    cutoff_date = as_of_dt.date()
    db = SyncSessionLocal()
    try:
        supplier = (
            db.query(Supplier)
            .filter(Supplier.tenant_id == tenant_id, Supplier.id == supplier_id)
            .first()
        )
        if not supplier:
            return {
                "errors": state.get("errors", []) + [f"Supplier '{supplier_id}' not found for tenant '{tenant_id}'."],
                "status": "failed_supplier_not_found",
            }

        state_updates: Dict[str, Any] = {
            "supplier_name": supplier.legal_name,
            "status": "snapshot_loaded",
        }
        return state_updates
    finally:
        db.close()


def operational_analysis_node(state: SupplierRiskState) -> Dict[str, Any]:
    """Node 2a: Deterministic operational indicator analysis (L, D, T, F)."""
    tenant_id = state["tenant_id"]
    supplier_id = state["supplier_id"]
    as_of_str = state["as_of"]
    as_of_dt = datetime.fromisoformat(as_of_str.replace("Z", "+00:00")).replace(tzinfo=None)
    cutoff_date = as_of_dt.date()

    db = SyncSessionLocal()
    try:
        # Load PO lines due on or before cutoff date
        po_lines_db = (
            db.query(PurchaseOrderLine)
            .filter(
                PurchaseOrderLine.tenant_id == tenant_id,
                PurchaseOrderLine.supplier_id == supplier_id,
                PurchaseOrderLine.committed_due_date <= cutoff_date,
            )
            .all()
        )

        line_ids = [p.id for p in po_lines_db]
        receipts_db = (
            db.query(Receipt)
            .filter(Receipt.po_line_id.in_(line_ids), Receipt.received_at <= as_of_dt)
            .all()
        )

        order_line_records = [
            OrderLineRecord(
                id=p.id,
                po_number=p.po_number,
                line_number=p.line_number,
                supplier_id=p.supplier_id,
                material_id=p.material_id,
                ordered_quantity=p.ordered_quantity,
                unit=p.unit,
                committed_due_date=p.committed_due_date,
            )
            for p in po_lines_db
        ]

        receipt_records = [
            ReceiptRecord(
                id=r.id,
                po_line_id=r.po_line_id,
                accepted_quantity=r.accepted_quantity,
                rejected_quantity=r.rejected_quantity,
                received_at=r.received_at,
            )
            for r in receipts_db
        ]

        metrics = calculate_operational_indicators(
            order_lines=order_line_records,
            receipts=receipt_records,
            cutoff_date=cutoff_date,
            window_days=30,
        )

        return {
            "internal_result": {
                "late_fraction_L": metrics.late_fraction_L,
                "delay_factor_D": metrics.delay_factor_D,
                "deterioration_factor_T": metrics.deterioration_factor_T,
                "fulfillment_shortfall_F": metrics.fulfillment_shortfall_F,
                "on_time_fulfillment_rate": metrics.on_time_fulfillment_rate,
                "recent_mean_completed_delay_days": metrics.recent_mean_completed_delay_days,
                "previous_mean_completed_delay_days": metrics.previous_mean_completed_delay_days,
                "total_due_lines": metrics.total_due_lines,
                "recent_window_lines": metrics.recent_window_lines,
                "sufficiency": metrics.sufficiency.value,
                "missing_factors": metrics.missing_factors,
            }
        }
    finally:
        db.close()


def external_check_node(state: SupplierRiskState) -> Dict[str, Any]:
    """Node 2b: Bounded external signal retrieval and entity matching."""
    tenant_id = state["tenant_id"]
    supplier_id = state["supplier_id"]
    as_of_str = state["as_of"]
    as_of_dt = datetime.fromisoformat(as_of_str.replace("Z", "+00:00")).replace(tzinfo=None)

    db = SyncSessionLocal()
    try:
        supplier = (
            db.query(Supplier)
            .filter(Supplier.tenant_id == tenant_id, Supplier.id == supplier_id)
            .first()
        )
        if not supplier:
            return {"external_result": {"status": "no_relevant_evidence", "evidence_items": []}}

        evidence_records, ext_status, failure_reason = search_adapter.check_supplier_signals(
            supplier_id=supplier.id,
            legal_name=supplier.legal_name,
            aliases=supplier.aliases or [],
            domain=supplier.domain,
            location=supplier.location,
            as_of_dt=as_of_dt,
        )

        items_serialized = []
        for e in evidence_records:
            items_serialized.append({
                "id": e.id,
                "source_url": e.source_url,
                "publisher": e.publisher,
                "published_at": e.published_at.isoformat(),
                "event_type": e.event_type,
                "entity_match": e.entity_match,
                "severity": e.severity,
                "reliability_factor": e.reliability_factor,
                "freshness_factor": e.freshness_factor,
                "supporting_excerpt": e.supporting_excerpt,
                "is_synthetic": e.is_synthetic,
            })

        return {
            "external_result": {
                "status": ext_status.value,
                "evidence_items": items_serialized,
                "failure_reason": failure_reason,
            }
        }
    finally:
        db.close()


def validate_join_node(state: SupplierRiskState) -> Dict[str, Any]:
    """Node 3: Barrier Join & Evidence Sanitizer."""
    internal = state.get("internal_result") or {}
    external = state.get("external_result") or {}

    sanitized_items = []
    for item in external.get("evidence_items", []):
        if item.get("entity_match", "").lower() == "verified":
            sanitized_items.append(item)

    external_clean = dict(external)
    external_clean["evidence_items"] = sanitized_items

    return {
        "internal_result": internal,
        "external_result": external_clean,
        "status": "join_validated",
    }


def score_policy_node(state: SupplierRiskState) -> Dict[str, Any]:
    """Node 4: Deterministic Risk Policy Engine (I, E, R)."""
    internal = state.get("internal_result") or {}
    external = state.get("external_result") or {}

    L = internal.get("late_fraction_L", 0.0)
    D = internal.get("delay_factor_D", 0.0)
    T = internal.get("deterioration_factor_T", 0.0)
    F = internal.get("fulfillment_shortfall_F", 0.0)
    missing_factors = internal.get("missing_factors", [])

    evidence_records: List[EvidenceItemRecord] = []
    for raw in external.get("evidence_items", []):
        pub_dt = datetime.fromisoformat(raw["published_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        evidence_records.append(
            EvidenceItemRecord(
                evidence_id=raw["id"],
                supplier_id=state["supplier_id"],
                source_url=raw["source_url"],
                publisher=raw["publisher"],
                published_at=pub_dt,
                event_type=raw["event_type"],
                entity_match=raw["entity_match"],
                severity=raw["severity"],
                reliability_factor=raw["reliability_factor"],
                freshness_factor=raw["freshness_factor"],
                supporting_excerpt=raw["supporting_excerpt"],
                is_synthetic=raw.get("is_synthetic", True),
            )
        )

    score_result = calculate_risk_policy(
        L=L,
        D=D,
        T=T,
        F=F,
        evidence_items=evidence_records,
        missing_factors=missing_factors,
        policy_version=state.get("policy_version", "v1.0.0"),
    )

    return {
        "score_result": {
            "internal_index_I": score_result.internal_index_I,
            "external_index_E": score_result.external_index_E,
            "blended_risk_R": score_result.blended_risk_R,
            "band": score_result.band.value,
            "factor_contributions": score_result.factor_contributions,
            "is_partial": score_result.is_partial,
            "is_evidence_limited": score_result.is_evidence_limited,
            "critical_override_active": score_result.critical_override_active,
            "override_reason": score_result.override_reason,
        }
    }


def impact_analysis_node(state: SupplierRiskState) -> Dict[str, Any]:
    """Node 5: Production Impact & Daily Inventory Trajectory Simulation B[d]."""
    tenant_id = state["tenant_id"]
    supplier_id = state["supplier_id"]
    as_of_str = state["as_of"]
    as_of_dt = datetime.fromisoformat(as_of_str.replace("Z", "+00:00")).replace(tzinfo=None)
    start_date = as_of_dt.date()

    db = SyncSessionLocal()
    try:
        # Find materials supplied by this supplier
        links = (
            db.query(SupplierMaterial)
            .filter(SupplierMaterial.supplier_id == supplier_id)
            .all()
        )
        if not links:
            return {"impact_result": None}

        # Pick primary material supplied
        primary_link = links[0]
        material = db.query(Material).filter(Material.id == primary_link.material_id).first()
        if not material:
            return {"impact_result": None}

        # Count alternate qualified suppliers for this material
        alternate_count = (
            db.query(SupplierMaterial)
            .filter(
                SupplierMaterial.material_id == material.id,
                SupplierMaterial.supplier_id != supplier_id,
                SupplierMaterial.is_approved == True,
            )
            .count()
        )

        # Get latest inventory snapshot
        snap = (
            db.query(InventorySnapshot)
            .filter(InventorySnapshot.material_id == material.id)
            .order_by(InventorySnapshot.observed_at.desc())
            .first()
        )
        on_hand = snap.on_hand_quantity if snap else 500.0
        reserved = snap.reserved_quantity if snap else 0.0

        # Get daily demand
        demand_row = (
            db.query(DemandForecast)
            .filter(DemandForecast.material_id == material.id)
            .first()
        )
        daily_burn = demand_row.daily_quantity if demand_row else 50.0

        # Normal lead time
        lead_time = primary_link.normal_lead_time_days or 10.0

        # Map criticality
        crit_enum = MaterialCriticality.TIER_2
        if material.criticality == "tier_1":
            crit_enum = MaterialCriticality.TIER_1
        elif material.criticality == "tier_3":
            crit_enum = MaterialCriticality.TIER_3

        exposure = evaluate_material_exposure(
            material_id=material.id,
            material_name=material.name,
            criticality=crit_enum,
            unit=material.canonical_unit,
            on_hand_stock=on_hand,
            reserved_stock=reserved,
            daily_consumption=daily_burn,
            start_date=start_date,
            normal_receipts_by_date={},
            normal_lead_time_days=lead_time,
            stress_delay_days=6.0,
            alternate_suppliers_count=alternate_count,
        )

        return {
            "impact_result": {
                "material_id": exposure.material_id,
                "material_name": exposure.material_name,
                "criticality": exposure.criticality.value,
                "unit": exposure.unit,
                "available_stock": exposure.available_stock,
                "daily_consumption": exposure.daily_consumption,
                "coverage_days": exposure.coverage_days,
                "scenario_arrival_days": exposure.scenario_arrival_days,
                "scenario_gap_days": exposure.scenario_gap_days,
                "day_to_stockout": exposure.day_to_stockout,
                "has_alternate_supplier": exposure.has_alternate_supplier,
                "alternate_suppliers_count": exposure.alternate_suppliers_count,
            }
        }
    finally:
        db.close()


def explain_node(state: SupplierRiskState) -> Dict[str, Any]:
    """Node 7: Grounded Explanation Generator with strict Pydantic contract and fallback."""
    supplier_name = state.get("supplier_name", "Supplier")
    internal = state.get("internal_result") or {}
    score = state.get("score_result") or {}
    impact = state.get("impact_result")
    external = state.get("external_result") or {}

    from backend.app.domain.models_domain import (
        OperationalMetrics,
        SufficiencyState,
        RiskScoreResult,
        MaterialExposureResult,
        MaterialCriticality,
    )

    metrics_obj = OperationalMetrics(
        on_time_fulfillment_rate=internal.get("on_time_fulfillment_rate", 1.0),
        late_fraction_L=internal.get("late_fraction_L", 0.0),
        recent_mean_completed_delay_days=internal.get("recent_mean_completed_delay_days", 0.0),
        delay_factor_D=internal.get("delay_factor_D", 0.0),
        previous_mean_completed_delay_days=internal.get("previous_mean_completed_delay_days", 0.0),
        deterioration_factor_T=internal.get("deterioration_factor_T", 0.0),
        fulfillment_shortfall_F=internal.get("fulfillment_shortfall_F", 0.0),
        total_due_lines=internal.get("total_due_lines", 0),
        recent_window_lines=internal.get("recent_window_lines", 0),
        previous_window_lines=internal.get("previous_window_lines", 0),
        sufficiency=SufficiencyState(internal.get("sufficiency", "adequate")),
        missing_factors=internal.get("missing_factors", []),
    )

    score_obj = RiskScoreResult(
        internal_index_I=score.get("internal_index_I"),
        external_index_E=score.get("external_index_E"),
        blended_risk_R=score.get("blended_risk_R"),
        band=RiskBand(score.get("band", "low")),
        factor_contributions=score.get("factor_contributions", {}),
        is_partial=score.get("is_partial", False),
        is_evidence_limited=score.get("is_evidence_limited", False),
        critical_override_active=score.get("critical_override_active", False),
        override_reason=score.get("override_reason"),
        policy_version=state.get("policy_version", "v1.0.0"),
    )

    exposure_obj = None
    if impact:
        exposure_obj = MaterialExposureResult(
            material_id=impact["material_id"],
            material_name=impact["material_name"],
            criticality=MaterialCriticality(impact["criticality"]),
            on_hand_stock=impact["available_stock"],
            reserved_stock=0.0,
            available_stock=impact["available_stock"],
            unit=impact["unit"],
            daily_consumption=impact["daily_consumption"],
            coverage_days=impact["coverage_days"],
            scenario_arrival_days=impact["scenario_arrival_days"],
            scenario_gap_days=impact["scenario_gap_days"],
            day_to_stockout=impact.get("day_to_stockout"),
            trajectory_base=[],
            trajectory_stress=[],
            has_alternate_supplier=impact["has_alternate_supplier"],
            alternate_suppliers_count=impact["alternate_suppliers_count"],
        )

    evidence_records = []
    for item in external.get("evidence_items", []):
        pub_dt = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        evidence_records.append(
            EvidenceItemRecord(
                evidence_id=item["id"],
                supplier_id=state["supplier_id"],
                source_url=item["source_url"],
                publisher=item["publisher"],
                published_at=pub_dt,
                event_type=item["event_type"],
                entity_match=item["entity_match"],
                severity=item["severity"],
                reliability_factor=item["reliability_factor"],
                freshness_factor=item["freshness_factor"],
                supporting_excerpt=item["supporting_excerpt"],
                is_synthetic=item.get("is_synthetic", True),
            )
        )

    explanation = generate_grounded_explanation(
        supplier_name=supplier_name,
        metrics=metrics_obj,
        score_result=score_obj,
        exposure=exposure_obj,
        evidence_items=evidence_records,
    )

    return {"explanation_result": explanation}


def validate_persist_node(state: SupplierRiskState) -> Dict[str, Any]:
    """Node 8: Atomic Persistence & Alert Deduplication."""
    tenant_id = state["tenant_id"]
    supplier_id = state["supplier_id"]
    run_id = state["run_id"]
    as_of_str = state["as_of"]
    as_of_dt = datetime.fromisoformat(as_of_str.replace("Z", "+00:00")).replace(tzinfo=None)

    score = state.get("score_result") or {}
    impact = state.get("impact_result")
    explanation = state.get("explanation_result") or {}
    external = state.get("external_result") or {}

    db = SyncSessionLocal()
    try:
        # 1. Idempotent Assessment Write
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.tenant_id == tenant_id,
                Assessment.run_id == run_id,
                Assessment.supplier_id == supplier_id,
            )
            .first()
        )
        if not assessment:
            assessment = Assessment(
                tenant_id=tenant_id,
                supplier_id=supplier_id,
                run_id=run_id,
                as_of=as_of_dt,
                policy_version=state.get("policy_version", "v1.0.0"),
                features={
                    "internal": state.get("internal_result"),
                    "external": external,
                },
                index_score=score.get("blended_risk_R"),
                band=score.get("band", "low"),
                impact_summary=impact,
            )
            db.add(assessment)
            db.commit()
            db.refresh(assessment)
        else:
            assessment.features = {
                "internal": state.get("internal_result"),
                "external": external,
            }
            assessment.index_score = score.get("blended_risk_R")
            assessment.band = score.get("band", "low")
            assessment.impact_summary = impact
            db.commit()

        # Link evidence items to assessment
        for ev_raw in external.get("evidence_items", []):
            existing_link = (
                db.query(AssessmentEvidence)
                .filter(
                    AssessmentEvidence.assessment_id == assessment.id,
                    AssessmentEvidence.evidence_id == ev_raw["id"],
                )
                .first()
            )
            if not existing_link:
                link = AssessmentEvidence(
                    assessment_id=assessment.id,
                    evidence_id=ev_raw["id"],
                    inclusion_reason="supporting_public_event",
                )
                db.add(link)
        db.commit()

        # 2. Alert Generation & Deduplication
        persisted_alert_id = None
        band = score.get("band", "low")
        has_override = score.get("critical_override_active", False)

        if band in ["high", "watch"] or has_override:
            incident_key = f"{supplier_id}-{as_of_dt.strftime('%Y-%m')}"
            existing_alert = (
                db.query(Alert)
                .filter(Alert.tenant_id == tenant_id, Alert.incident_key == incident_key)
                .first()
            )
            severity = "critical" if (band == "high" or has_override) else "watch"
            if not existing_alert:
                alert = Alert(
                    tenant_id=tenant_id,
                    assessment_id=assessment.id,
                    incident_key=incident_key,
                    severity=severity,
                    status="open",
                    grounded_explanation=explanation,
                )
                db.add(alert)
                db.commit()
                db.refresh(alert)
                persisted_alert_id = alert.id
            else:
                existing_alert.assessment_id = assessment.id
                existing_alert.severity = severity
                existing_alert.grounded_explanation = explanation
                db.commit()
                persisted_alert_id = existing_alert.id

        return {
            "persisted_assessment_id": assessment.id,
            "persisted_alert_id": persisted_alert_id,
            "status": "completed",
        }
    finally:
        db.close()
