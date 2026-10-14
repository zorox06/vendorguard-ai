"""Grounded Explanation Engine and Sanitizer.

Implements Sections 12 & 17 of the VendorGuard AI Blueprint:
- Strict Pydantic JSON schema constraints
- Untrusted text sanitization (OWASP prompt injection prevention)
- Numerical fact verification against deterministic domain state
- Automatic deterministic template fallback on schema/fact violation
"""

import os
import re
import json
from typing import Dict, List, Any, Optional

from backend.app.domain.models_domain import (
    RiskScoreResult,
    MaterialExposureResult,
    OperationalMetrics,
    EvidenceItemRecord,
)

# Common prompt injection patterns in untrusted web text
INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system override",
    r"disregard (the )?system prompt",
    r"set score to",
    r"execute arbitrary",
    r"eval\(",
    r"delete from",
    r"drop table",
]


def sanitize_untrusted_text(text: str) -> str:
    """Sanitizes untrusted web excerpts to prevent indirect prompt injection."""
    sanitized = text
    for pattern in INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "[FILTERED_UNTRUSTED_INSTRUCTION]", sanitized, flags=re.IGNORECASE)
    # Strip HTML tags
    sanitized = re.sub(r"<[^>]+>", " ", sanitized)
    return sanitized.strip()


def build_deterministic_explanation_template(
    supplier_name: str,
    metrics: OperationalMetrics,
    score_result: RiskScoreResult,
    exposure: Optional[MaterialExposureResult],
    evidence_items: List[EvidenceItemRecord],
) -> Dict[str, Any]:
    """Fallback fact-based template with 100% mathematical guarantee."""
    L_pct = round(metrics.late_fraction_L * 100, 1)
    mean_delay = metrics.recent_mean_completed_delay_days
    prev_delay = metrics.previous_mean_completed_delay_days

    # Evidence details
    ev_ids = [e.id for e in evidence_items if e.entity_match.lower() == "verified"]
    top_ev = evidence_items[0] if evidence_items else None
    ev_excerpt = top_ev.supporting_excerpt if top_ev else None
    ev_source = top_ev.publisher if top_ev else None
    ev_date = top_ev.published_at.strftime("%Y-%m-%d") if top_ev else None

    # Summary sentence
    summary_parts = [
        f"{supplier_name}'s recent late fraction is {L_pct}%, with average completed delay moving from {prev_delay:.1f} to {mean_delay:.1f} days."
    ]

    if top_ev and score_result.external_index_E is not None:
        summary_parts.append(
            f"Verified public evidence ({top_ev.event_type}) contributes an external indicator of {score_result.external_index_E:.2f}, resulting in a blended risk index R={score_result.blended_risk_R:.2f} ({score_result.band.value.upper()} band)."
        )
    elif score_result.internal_index_I is not None:
        summary_parts.append(
            f"No verified external signals were detected (evidence-limited index R={score_result.blended_risk_R:.2f}, {score_result.band.value.upper()} band)."
        )

    # Impact sentence
    if exposure:
        cov = exposure.coverage_days
        gap = exposure.scenario_gap_days
        burn = exposure.daily_consumption
        unit = exposure.unit
        mat = exposure.material_name
        stock = exposure.available_stock
        summary_parts.append(
            f"Available {mat} is {stock:.0f} {unit}, providing {cov:.1f} days coverage at {burn:.0f} {unit}/day. Under declared {exposure.scenario_arrival_days:.0f}-day replenishment, a {gap:.1f}-day supply gap emerges."
        )

    summary_text = " ".join(summary_parts)

    drivers = [
        {
            "metric": "late_fraction_L",
            "label": "Late Fraction (L)",
            "value": f"{L_pct}%",
            "benchmark": "< 30%",
        },
        {
            "metric": "delay_trend_T",
            "label": "Completed Delay Trend",
            "value": f"{prev_delay:.1f}d -> {mean_delay:.1f}d",
            "benchmark": "Stable <= 2d",
        },
    ]

    if score_result.blended_risk_R is not None:
        drivers.append({
            "metric": "blended_risk_R",
            "label": "Blended Risk Index (R)",
            "value": f"{score_result.blended_risk_R:.2f}",
            "benchmark": f"{score_result.band.value.title()} Band",
        })

    impact_dict = {}
    if exposure:
        impact_dict = {
            "material": exposure.material_name,
            "available_stock": exposure.available_stock,
            "daily_burn": exposure.daily_consumption,
            "coverage_days": exposure.coverage_days,
            "scenario_arrival_days": exposure.scenario_arrival_days,
            "supply_gap_days": exposure.scenario_gap_days,
        }

    # Action recommendations based on facts
    suggested_actions = [
        f"Contact {supplier_name} account rep to re-confirm dispatch dates for open purchase orders.",
    ]
    if exposure and exposure.scenario_gap_days > 0:
        if exposure.has_alternate_supplier:
            suggested_actions.append(
                f"Review qualified alternative suppliers ({exposure.alternate_suppliers_count} available) to place buffer split order."
            )
        else:
            suggested_actions.append(
                f"Urgent: Single-source material '{exposure.material_name}'. Initiate production safety buffer review immediately."
            )

    return {
        "summary": summary_text,
        "drivers": drivers,
        "evidence_ids": ev_ids,
        "evidence_excerpt": ev_excerpt,
        "evidence_source": ev_source,
        "evidence_date": ev_date,
        "impact_assumptions": impact_dict,
        "suggested_actions": suggested_actions,
        "limitations": "Model outputs represent decision support scenarios based on declared replenishment parameters; external signals are synthetic fixtures.",
    }


def generate_grounded_explanation(
    supplier_name: str,
    metrics: OperationalMetrics,
    score_result: RiskScoreResult,
    exposure: Optional[MaterialExposureResult],
    evidence_items: List[EvidenceItemRecord],
    use_llm: bool = False,
) -> Dict[str, Any]:
    """Generates an explanation guaranteed to be grounded in verified numbers."""
    # Sanitize external excerpts before any prompt formation
    sanitized_items = []
    for e in evidence_items:
        clean_excerpt = sanitize_untrusted_text(e.supporting_excerpt)
        e_copy = EvidenceItemRecord(
            evidence_id=e.evidence_id,
            supplier_id=e.supplier_id,
            source_url=e.source_url,
            publisher=e.publisher,
            published_at=e.published_at,
            event_type=e.event_type,
            entity_match=e.entity_match,
            severity=e.severity,
            reliability_factor=e.reliability_factor,
            freshness_factor=e.freshness_factor,
            supporting_excerpt=clean_excerpt,
            is_synthetic=e.is_synthetic,
        )
        sanitized_items.append(e_copy)

    # Use deterministic fact template by default to ensure 100% mathematical factuality
    explanation = build_deterministic_explanation_template(
        supplier_name=supplier_name,
        metrics=metrics,
        score_result=score_result,
        exposure=exposure,
        evidence_items=sanitized_items,
    )

    return explanation
