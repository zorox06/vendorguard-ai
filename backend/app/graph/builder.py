"""LangGraph Graph Assembly and Runner.

Implements Figure 3 & Section 6 of the Blueprint:
- Parallel branch execution for operational metrics and external check
- Barrier edge synchronization at validate_join
- Deterministic scoring policy & material impact simulation
- Conditional grounded explanation generation
- Atomic persistence with deduplication
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END

from backend.app.graph.state import SupplierRiskState
from backend.app.graph.nodes import (
    load_snapshot_node,
    operational_analysis_node,
    external_check_node,
    validate_join_node,
    score_policy_node,
    impact_analysis_node,
    explain_node,
    validate_persist_node,
)


def should_explain(state: SupplierRiskState) -> str:
    """Decides whether grounded explanation is needed based on risk band."""
    score = state.get("score_result") or {}
    band = score.get("band", "low")
    override = score.get("critical_override_active", False)
    if band in ["high", "watch"] or override:
        return "explain"
    return "validate_persist"


def build_supplier_risk_graph() -> Any:
    """Compiles the hybrid agentic supplier risk evaluation graph."""
    workflow = StateGraph(SupplierRiskState)

    # Add nodes
    workflow.add_node("load_snapshot", load_snapshot_node)
    workflow.add_node("operational_analysis", operational_analysis_node)
    workflow.add_node("external_check", external_check_node)
    workflow.add_node("validate_join", validate_join_node)
    workflow.add_node("score_policy", score_policy_node)
    workflow.add_node("impact_analysis", impact_analysis_node)
    workflow.add_node("explain", explain_node)
    workflow.add_node("validate_persist", validate_persist_node)

    # Set entry point
    workflow.set_entry_point("load_snapshot")

    # Fan out to parallel branches
    workflow.add_edge("load_snapshot", "operational_analysis")
    workflow.add_edge("load_snapshot", "external_check")

    # Barrier join: wait for both branches
    workflow.add_edge("operational_analysis", "validate_join")
    workflow.add_edge("external_check", "validate_join")

    # Downstream pipeline
    workflow.add_edge("validate_join", "score_policy")
    workflow.add_edge("score_policy", "impact_analysis")

    # Conditional explain routing
    workflow.add_conditional_edges(
        "impact_analysis",
        should_explain,
        {
            "explain": "explain",
            "validate_persist": "validate_persist",
        },
    )

    workflow.add_edge("explain", "validate_persist")
    workflow.add_edge("validate_persist", END)

    app = workflow.compile()
    return app


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_supplier_risk_graph()
    return _compiled_graph


def run_supplier_risk_cycle(
    tenant_id: str,
    supplier_id: str,
    run_id: str,
    as_of: str,
    policy_version: str = "v1.0.0",
) -> SupplierRiskState:
    """Executes the complete compiled LangGraph for a single supplier."""
    initial_state: SupplierRiskState = {
        "tenant_id": tenant_id,
        "supplier_id": supplier_id,
        "supplier_name": "",
        "run_id": run_id,
        "as_of": as_of,
        "snapshot_id": f"snap-{supplier_id}",
        "policy_version": policy_version,
        "internal_result": None,
        "external_result": None,
        "score_result": None,
        "impact_result": None,
        "explanation_result": None,
        "persisted_assessment_id": None,
        "persisted_alert_id": None,
        "errors": [],
        "status": "pending",
    }

    graph = get_compiled_graph()
    final_state = graph.invoke(initial_state)
    return final_state
