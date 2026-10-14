"""Domain models and value objects for VendorGuard AI."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class MaterialCriticality(str, Enum):
    TIER_1 = "tier_1"  # Halts production immediately if stocked out
    TIER_2 = "tier_2"  # Affects secondary lines or packaging sub-steps
    TIER_3 = "tier_3"  # Non-critical consumables with high substitution


class RiskBand(str, Enum):
    LOW = "low"        # < 30
    WATCH = "watch"    # 30 - 59.99
    HIGH = "high"      # >= 60


class ExternalEvidenceStatus(str, Enum):
    RELIABLE_EVIDENCE = "reliable_evidence"
    NO_RELEVANT_EVIDENCE = "no_relevant_evidence"
    AMBIGUOUS_ENTITY = "ambiguous_entity"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


class SufficiencyState(str, Enum):
    ADEQUATE = "adequate"
    LIMITED_HISTORY = "limited_history"
    NO_DATA = "no_data"


@dataclass
class OrderLineRecord:
    id: str
    supplier_id: str
    material_id: str
    po_number: str
    line_number: int
    ordered_quantity: float
    unit: str
    committed_due_date: date
    created_at: Optional[datetime] = None
    # Revisions / versions can alter committed_due_date
    version_id: Optional[str] = None


@dataclass
class ReceiptRecord:
    id: str
    po_line_id: str
    accepted_quantity: float
    rejected_quantity: float
    received_at: datetime
    recorded_at: Optional[datetime] = None


@dataclass
class EvidenceItemRecord:
    evidence_id: str
    supplier_id: str
    source_url: str
    published_at: datetime
    event_type: str
    entity_match: str  # 'verified', 'ambiguous', 'unrelated'
    severity: float  # [0.0, 1.0]
    reliability_factor: float  # [0.0, 1.0]
    freshness_factor: float  # [0.0, 1.0]
    supporting_excerpt: str
    publisher: str = "Verified Source"
    fetched_at: Optional[datetime] = None
    source_quality: str = "primary_or_verified_report"
    is_synthetic: bool = True

    @property
    def id(self) -> str:
        return self.evidence_id


@dataclass
class OperationalMetrics:
    on_time_fulfillment_rate: float
    late_fraction_L: float
    recent_mean_completed_delay_days: float
    delay_factor_D: float
    previous_mean_completed_delay_days: float
    deterioration_factor_T: float
    fulfillment_shortfall_F: float
    total_due_lines: int
    recent_window_lines: int
    previous_window_lines: int
    sufficiency: SufficiencyState
    missing_factors: List[str] = field(default_factory=list)


@dataclass
class RiskScoreResult:
    internal_index_I: Optional[float]
    external_index_E: Optional[float]
    blended_risk_R: Optional[float]
    band: RiskBand
    factor_contributions: Dict[str, float]
    is_partial: bool
    is_evidence_limited: bool
    critical_override_active: bool
    override_reason: Optional[str] = None
    policy_version: str = "v1.0.0"


@dataclass
class DailyInventoryPoint:
    day: int
    date_str: str
    starting_balance: float
    scheduled_receipts: float
    required_consumption: float
    ending_balance: float
    is_stockout: bool


@dataclass
class MaterialExposureResult:
    material_id: str
    material_name: str
    criticality: MaterialCriticality
    on_hand_stock: float
    reserved_stock: float
    available_stock: float
    unit: str
    daily_consumption: float
    coverage_days: float
    scenario_arrival_days: float
    scenario_gap_days: float
    day_to_stockout: Optional[int]
    trajectory_base: List[DailyInventoryPoint]
    trajectory_stress: List[DailyInventoryPoint]
    has_alternate_supplier: bool
    alternate_suppliers_count: int
