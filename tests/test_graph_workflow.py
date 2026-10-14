"""Unit and Integration tests for LangGraph Workflow."""

import pytest
from datetime import datetime
from backend.app.adapters.storage import SyncSessionLocal
from backend.app.models.schema import Supplier, Alert, Assessment
from backend.app.graph.builder import run_supplier_risk_cycle, build_supplier_risk_graph


def test_graph_compilation():
    graph = build_supplier_risk_graph()
    assert graph is not None


def test_apex_polymers_graph_run():
    db = SyncSessionLocal()
    try:
        sup = db.query(Supplier).filter(Supplier.legal_name == "Apex Polymers Ltd").first()
        assert sup is not None, "Apex Polymers Ltd should exist in seeded database"

        run_id = "run-unit-test-apex"
        as_of = "2026-10-10T00:00:00Z"

        state = run_supplier_risk_cycle(
            tenant_id="tenant-default",
            supplier_id=sup.id,
            run_id=run_id,
            as_of=as_of,
        )

        assert state["status"] == "completed"
        assert state["supplier_name"] == "Apex Polymers Ltd"

        # Check internal metrics
        internal = state["internal_result"]
        assert internal is not None
        assert internal["late_fraction_L"] == pytest.approx(0.60, abs=0.05)

        # Check external evidence
        external = state["external_result"]
        assert external is not None
        assert external["status"] == "reliable_evidence"
        assert len(external["evidence_items"]) >= 1

        # Check score & critical override
        score = state["score_result"]
        assert score is not None
        assert score["band"] == "high"
        assert score["critical_override_active"] is True

        # Check explanation
        explanation = state["explanation_result"]
        assert explanation is not None
        assert "Apex Polymers Ltd" in explanation["summary"]
        assert len(explanation["evidence_ids"]) >= 1
        assert "supply_gap_days" in explanation["impact_assumptions"]

        # Check persistence
        assert state["persisted_assessment_id"] is not None
        assert state["persisted_alert_id"] is not None

        # Verify idempotency: run again and verify no duplicate alert is created
        state2 = run_supplier_risk_cycle(
            tenant_id="tenant-default",
            supplier_id=sup.id,
            run_id="run-unit-test-apex-2",
            as_of=as_of,
        )
        assert state2["persisted_alert_id"] == state["persisted_alert_id"]

    finally:
        db.close()


def test_missing_supplier_graceful_handling():
    run_id = "run-unit-test-missing"
    as_of = "2026-10-10T00:00:00Z"

    state = run_supplier_risk_cycle(
        tenant_id="tenant-default",
        supplier_id="non-existent-supplier-id",
        run_id=run_id,
        as_of=as_of,
    )

    # Should not crash the process; handles failure state gracefully
    assert "not found" in str(state.get("errors", []))
