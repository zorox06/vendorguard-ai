"""SQLAlchemy 2.0 ORM Schema for VendorGuard AI.

Implements Sections 7 & 14 data dictionary:
- Multi-tenant boundary
- Immutable historical audit trails
- Relational schema + JSON metadata fields
"""

import uuid
from datetime import datetime, date, timezone
from typing import Optional, List, Any, Dict
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    Index,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    suppliers: Mapped[List["Supplier"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    materials: Mapped[List["Material"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    monitoring_runs: Mapped[List["MonitoringRun"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    registration_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="suppliers")
    materials: Mapped[List["SupplierMaterial"]] = relationship(back_populates="supplier")
    order_lines: Mapped[List["PurchaseOrderLine"]] = relationship(back_populates="supplier")
    assessments: Mapped[List["Assessment"]] = relationship(back_populates="supplier")

    __table_args__ = (
        UniqueConstraint("tenant_id", "legal_name", name="uq_supplier_tenant_name"),
    )


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_unit: Mapped[str] = mapped_column(String(32), nullable=False)  # kg, rolls, units
    criticality: Mapped[str] = mapped_column(String(32), nullable=False)  # tier_1, tier_2, tier_3
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    tenant: Mapped["Tenant"] = relationship(back_populates="materials")
    suppliers: Mapped[List["SupplierMaterial"]] = relationship(back_populates="material")
    inventory_snapshots: Mapped[List["InventorySnapshot"]] = relationship(back_populates="material")
    demand_forecasts: Mapped[List["DemandForecast"]] = relationship(back_populates="material")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_material_tenant_name"),
    )


class SupplierMaterial(Base):
    __tablename__ = "supplier_materials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("suppliers.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(String(64), ForeignKey("materials.id"), nullable=False, index=True)
    normal_lead_time_days: Mapped[float] = mapped_column(Float, default=14.0)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    known_capacity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    supplier: Mapped["Supplier"] = relationship(back_populates="materials")
    material: Mapped["Material"] = relationship(back_populates="suppliers")

    __table_args__ = (
        UniqueConstraint("supplier_id", "material_id", name="uq_supplier_material"),
    )


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("suppliers.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(String(64), ForeignKey("materials.id"), nullable=False, index=True)
    po_number: Mapped[str] = mapped_column(String(64), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, default=1)
    ordered_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="kg")
    committed_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    supplier: Mapped["Supplier"] = relationship(back_populates="order_lines")
    receipts: Mapped[List["Receipt"]] = relationship(back_populates="order_line", cascade="all, delete-orphan")
    versions: Mapped[List["OrderLineVersion"]] = relationship(back_populates="order_line", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_po_lines_tenant_supplier_due", "tenant_id", "supplier_id", "committed_due_date"),
        UniqueConstraint("tenant_id", "po_number", "line_number", name="uq_po_line_number"),
    )


class OrderLineVersion(Base):
    __tablename__ = "order_line_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    po_line_id: Mapped[str] = mapped_column(String(64), ForeignKey("purchase_order_lines.id"), nullable=False, index=True)
    committed_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    ordered_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    order_line: Mapped["PurchaseOrderLine"] = relationship(back_populates="versions")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    po_line_id: Mapped[str] = mapped_column(String(64), ForeignKey("purchase_order_lines.id"), nullable=False, index=True)
    accepted_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    rejected_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    order_line: Mapped["PurchaseOrderLine"] = relationship(back_populates="receipts")


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(String(64), ForeignKey("materials.id"), nullable=False, index=True)
    warehouse: Mapped[str] = mapped_column(String(128), default="Main Warehouse")
    on_hand_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    reserved_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    material: Mapped["Material"] = relationship(back_populates="inventory_snapshots")

    __table_args__ = (
        Index("ix_inv_tenant_material_observed", "tenant_id", "material_id", "observed_at"),
    )


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(String(64), ForeignKey("materials.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_as_of: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    material: Mapped["Material"] = relationship(back_populates="demand_forecasts")


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, leased, running, completed, failed
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    summary_counts: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="monitoring_runs")
    assessments: Mapped[List["Assessment"]] = relationship(back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_run_idempotency"),
    )


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("suppliers.id"), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_match: Mapped[str] = mapped_column(String(32), default="verified")  # verified, ambiguous, unrelated
    source_quality: Mapped[str] = mapped_column(String(64), default="primary_or_verified_report")
    severity: Mapped[float] = mapped_column(Float, default=0.5)
    reliability_factor: Mapped[float] = mapped_column(Float, default=0.8)
    freshness_factor: Mapped[float] = mapped_column(Float, default=1.0)
    supporting_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("suppliers.id"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("monitoring_runs.id"), nullable=False, index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), default="v1.0.0")
    features: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    index_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    band: Mapped[str] = mapped_column(String(32), default="low")  # low, watch, high
    impact_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    supplier: Mapped["Supplier"] = relationship(back_populates="assessments")
    run: Mapped["MonitoringRun"] = relationship(back_populates="assessments")
    evidence_links: Mapped[List["AssessmentEvidence"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", "supplier_id", name="uq_assessment_run_supplier"),
    )


class AssessmentEvidence(Base):
    __tablename__ = "assessment_evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(String(64), ForeignKey("assessments.id"), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(64), ForeignKey("evidence_items.id"), nullable=False, index=True)
    inclusion_reason: Mapped[str] = mapped_column(String(255), default="supporting_evidence")

    assessment: Mapped["Assessment"] = relationship(back_populates="evidence_links")
    evidence: Mapped["EvidenceItem"] = relationship()


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    assessment_id: Mapped[str] = mapped_column(String(64), ForeignKey("assessments.id"), nullable=False, index=True)
    incident_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="high")  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(32), default="open")  # open, acknowledged, resolved, dismissed
    grounded_explanation: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="alerts")
    feedback: Mapped[List["AlertFeedback"]] = relationship(back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "incident_key", name="uq_alert_incident_key"),
    )


class AlertFeedback(Base):
    __tablename__ = "alert_feedback"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    alert_id: Mapped[str] = mapped_column(String(64), ForeignKey("alerts.id"), nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String(128), default="purchasing_manager")
    disposition: Mapped[str] = mapped_column(String(64), nullable=False)  # useful, false_alarm, unhelpful
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    alert: Mapped["Alert"] = relationship(back_populates="feedback")
