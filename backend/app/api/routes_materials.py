"""Materials and Inventory Exposure REST routes for VendorGuard AI.

Implements Sections 11 & 13 of the Blueprint:
- Real database querying of materials, inventory on-hand, and burn rates
- Dynamic daily inventory simulation B[d] base vs stress delay
- Stockout day prediction and qualified alternative suppliers
"""

from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from datetime import datetime, date, timezone
from sqlalchemy.orm import Session

from backend.app.adapters.storage import get_sync_session
from backend.app.models.schema import Material, InventorySnapshot, DemandForecast, SupplierMaterial, Supplier
from backend.app.domain.impact import evaluate_material_exposure
from backend.app.domain.models_domain import MaterialCriticality

router = APIRouter(prefix="/api/materials", tags=["Materials"])

DEFAULT_TENANT_ID = "tenant-default"


@router.get("")
def list_materials(tenant_id: str = DEFAULT_TENANT_ID, db: Session = Depends(get_sync_session)):
    """Returns materials with inventory coverage and 30-day simulation trajectories."""
    materials = (
        db.query(Material)
        .filter(Material.tenant_id == tenant_id)
        .order_by(Material.name.asc())
        .all()
    )

    results = []
    start_d = date(2026, 10, 10)

    for m in materials:
        # Latest snapshot
        snap = (
            db.query(InventorySnapshot)
            .filter(InventorySnapshot.material_id == m.id)
            .order_by(InventorySnapshot.observed_at.desc())
            .first()
        )
        on_hand = snap.on_hand_quantity if snap else 800.0
        reserved = snap.reserved_quantity if snap else 0.0

        # Demand
        demand_row = (
            db.query(DemandForecast)
            .filter(DemandForecast.material_id == m.id)
            .first()
        )
        burn_rate = demand_row.daily_quantity if demand_row else 50.0

        # Primary and alternate suppliers
        sup_links = (
            db.query(SupplierMaterial)
            .filter(SupplierMaterial.material_id == m.id)
            .all()
        )
        primary_sup = sup_links[0].supplier.legal_name if (sup_links and sup_links[0].supplier) else "Primary Supplier"
        lead_time = sup_links[0].normal_lead_time_days if sup_links else 10.0

        alternate_list = []
        if len(sup_links) > 1:
            for sm in sup_links[1:]:
                if sm.supplier:
                    alternate_list.append({
                        "name": sm.supplier.legal_name,
                        "lead_time_days": sm.normal_lead_time_days,
                        "approved": sm.is_approved,
                    })

        crit_enum = MaterialCriticality.TIER_2
        if m.criticality == "tier_1":
            crit_enum = MaterialCriticality.TIER_1
        elif m.criticality == "tier_3":
            crit_enum = MaterialCriticality.TIER_3

        exposure = evaluate_material_exposure(
            material_id=m.id,
            material_name=m.name,
            criticality=crit_enum,
            unit=m.canonical_unit,
            on_hand_stock=on_hand,
            reserved_stock=reserved,
            daily_consumption=burn_rate,
            start_date=start_d,
            normal_receipts_by_date={},
            normal_lead_time_days=lead_time,
            stress_delay_days=6.0,
            alternate_suppliers_count=len(alternate_list),
        )

        results.append({
            "material_id": m.id,
            "material_name": m.name,
            "criticality": m.criticality,
            "unit": m.canonical_unit,
            "on_hand_stock": exposure.on_hand_stock,
            "reserved_stock": exposure.reserved_stock,
            "available_stock": exposure.available_stock,
            "daily_consumption": exposure.daily_consumption,
            "coverage_days": exposure.coverage_days,
            "scenario_arrival_days": exposure.scenario_arrival_days,
            "scenario_gap_days": exposure.scenario_gap_days,
            "day_to_stockout": exposure.day_to_stockout,
            "primary_supplier": primary_sup,
            "has_alternate_supplier": exposure.has_alternate_supplier,
            "alternate_suppliers": alternate_list,
            "trajectory_base": [
                {
                    "day": p.day,
                    "date_str": p.date_str,
                    "balance": p.ending_balance,
                    "is_stockout": p.is_stockout,
                }
                for p in exposure.trajectory_base
            ],
            "trajectory_stress": [
                {
                    "day": p.day,
                    "date_str": p.date_str,
                    "balance": p.ending_balance,
                    "is_stockout": p.is_stockout,
                }
                for p in exposure.trajectory_stress
            ],
        })

    return results
