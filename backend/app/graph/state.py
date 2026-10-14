"""LangGraph State Specification for VendorGuard AI.

Implements Section 6 of the VendorGuard AI Blueprint:
- Immutable identifiers (tenant, supplier, run, as_of)
- Distinct result branches for operational metrics and external evidence
- Strict serialization (dictionaries, numbers, lists; no raw ORM objects or unparsed CSVs)
"""

from typing import TypedDict, Optional, List, Dict, Any


class SupplierRiskState(TypedDict):
    tenant_id: str
    supplier_id: str
    supplier_name: str
    run_id: str
    as_of: str
    snapshot_id: str
    policy_version: str
    # Node outputs
    internal_result: Optional[Dict[str, Any]]
    external_result: Optional[Dict[str, Any]]
    score_result: Optional[Dict[str, Any]]
    impact_result: Optional[Dict[str, Any]]
    explanation_result: Optional[Dict[str, Any]]
    persisted_assessment_id: Optional[str]
    persisted_alert_id: Optional[str]
    errors: List[str]
    status: str
