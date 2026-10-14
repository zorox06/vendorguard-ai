"""Database Seeding Service for VendorGuard AI.

Loads Mode A synthetic packaging dataset into vendorguard.db:
- Creates default tenant 'Acme Packaging Co'
- Inserts 15 suppliers and 10 materials
- Populates PO lines, receipts, inventory, and demand forecasts
- Inserts labeled evidence fixtures from evidence_catalog.json
"""

import os
import csv
import json
from datetime import datetime, date
from sqlalchemy.orm import Session

from backend.app.adapters.storage import SyncSessionLocal, init_db
from backend.app.models.schema import (
    Tenant,
    Supplier,
    Material,
    SupplierMaterial,
    PurchaseOrderLine,
    Receipt,
    InventorySnapshot,
    DemandForecast,
    EvidenceItem,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATASET_DIR = os.path.join(BASE_DIR, "datasets", "synthetic", "mode_a")
EVIDENCE_CATALOG = os.path.join(BASE_DIR, "datasets", "synthetic", "evidence_catalog.json")

DEFAULT_TENANT_ID = "tenant-default"
DEFAULT_TENANT_NAME = "Acme Packaging Co"


def seed_database(db: Session = None, force_reseed: bool = False):
    init_db()
    close_db = False
    if db is None:
        db = SyncSessionLocal()
        close_db = True

    try:
        # Check if already seeded
        tenant = db.query(Tenant).filter(Tenant.id == DEFAULT_TENANT_ID).first()
        if tenant and not force_reseed:
            print("Database already contains default tenant. Skipping seed (use force_reseed=True to reset).")
            return

        if force_reseed and tenant:
            print("Purging existing database records for reseeding...")
            db.query(Receipt).delete()
            db.query(PurchaseOrderLine).delete()
            db.query(SupplierMaterial).delete()
            db.query(InventorySnapshot).delete()
            db.query(DemandForecast).delete()
            db.query(EvidenceItem).delete()
            db.query(Material).delete()
            db.query(Supplier).delete()
            db.query(Tenant).delete()
            db.commit()

        print("Seeding default tenant...")
        tenant = Tenant(id=DEFAULT_TENANT_ID, name=DEFAULT_TENANT_NAME)
        db.add(tenant)
        db.commit()

        # 1. Suppliers
        suppliers_by_name = {}
        with open(os.path.join(DATASET_DIR, "suppliers.csv"), mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aliases = [a.strip() for a in row.get("aliases", "").split(";") if a.strip()]
                sup = Supplier(
                    tenant_id=DEFAULT_TENANT_ID,
                    legal_name=row["legal_name"],
                    aliases=aliases,
                    domain=row.get("domain"),
                    location=row.get("location"),
                    registration_id=row.get("registration_id"),
                )
                db.add(sup)
                suppliers_by_name[sup.legal_name] = sup
        db.commit()
        for sup in suppliers_by_name.values():
            db.refresh(sup)
        print(f"Seeded {len(suppliers_by_name)} suppliers.")

        # 2. Materials
        materials_by_name = {}
        with open(os.path.join(DATASET_DIR, "materials.csv"), mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mat = Material(
                    tenant_id=DEFAULT_TENANT_ID,
                    name=row["name"],
                    canonical_unit=row["canonical_unit"],
                    criticality=row["criticality"],
                )
                db.add(mat)
                materials_by_name[mat.name] = mat
        db.commit()
        for mat in materials_by_name.values():
            db.refresh(mat)
        print(f"Seeded {len(materials_by_name)} materials.")

        # 3. Supplier Materials
        with open(os.path.join(DATASET_DIR, "supplier_materials.csv"), mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            sm_count = 0
            for row in reader:
                s = suppliers_by_name.get(row["supplier_name"])
                m = materials_by_name.get(row["material_name"])
                if s and m:
                    sm = SupplierMaterial(
                        supplier_id=s.id,
                        material_id=m.id,
                        normal_lead_time_days=float(row["normal_lead_time_days"]),
                        is_approved=row["is_approved"].lower() in ["true", "1", "yes"],
                    )
                    db.add(sm)
                    sm_count += 1
        db.commit()
        print(f"Seeded {sm_count} supplier-material links.")

        # 4. Inventory Snapshots
        with open(os.path.join(DATASET_DIR, "inventory_snapshots.csv"), mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                m = materials_by_name.get(row["material_name"])
                if m:
                    obs_dt = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00")).replace(tzinfo=None)
                    snap = InventorySnapshot(
                        tenant_id=DEFAULT_TENANT_ID,
                        material_id=m.id,
                        warehouse=row["warehouse"],
                        on_hand_quantity=float(row["on_hand_quantity"]),
                        reserved_quantity=float(row["reserved_quantity"]),
                        observed_at=obs_dt,
                    )
                    db.add(snap)
        db.commit()
        print("Seeded inventory snapshots.")

        # 5. Demand Forecasts
        with open(os.path.join(DATASET_DIR, "demand_forecasts.csv"), mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            df_count = 0
            for row in reader:
                m = materials_by_name.get(row["material_name"])
                if m:
                    df = DemandForecast(
                        tenant_id=DEFAULT_TENANT_ID,
                        material_id=m.id,
                        date=date.fromisoformat(row["date"]),
                        daily_quantity=float(row["daily_quantity"]),
                    )
                    db.add(df)
                    df_count += 1
        db.commit()
        print(f"Seeded {df_count} demand forecast points.")

        # 6. Purchase Order Lines
        po_lines_by_key = {}
        with open(os.path.join(DATASET_DIR, "purchase_order_lines.csv"), mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = suppliers_by_name.get(row["supplier_name"])
                m = materials_by_name.get(row["material_name"])
                if s and m:
                    pol = PurchaseOrderLine(
                        tenant_id=DEFAULT_TENANT_ID,
                        supplier_id=s.id,
                        material_id=m.id,
                        po_number=row["po_number"],
                        line_number=int(row["line_number"]),
                        ordered_quantity=float(row["ordered_quantity"]),
                        unit=row["unit"],
                        committed_due_date=date.fromisoformat(row["committed_due_date"]),
                    )
                    db.add(pol)
                    key = (row["po_number"], int(row["line_number"]))
                    po_lines_by_key[key] = pol
        db.commit()
        for pol in po_lines_by_key.values():
            db.refresh(pol)
        print(f"Seeded {len(po_lines_by_key)} purchase order lines.")

        # 7. Receipts
        with open(os.path.join(DATASET_DIR, "receipts.csv"), mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rec_count = 0
            for row in reader:
                key = (row["po_number"], int(row["line_number"]))
                pol = po_lines_by_key.get(key)
                if pol:
                    rec_dt = datetime.fromisoformat(row["received_at"].replace("Z", "+00:00")).replace(tzinfo=None)
                    rec = Receipt(
                        po_line_id=pol.id,
                        accepted_quantity=float(row["accepted_quantity"]),
                        rejected_quantity=float(row.get("rejected_quantity", 0.0)),
                        received_at=rec_dt,
                    )
                    db.add(rec)
                    rec_count += 1
        db.commit()
        print(f"Seeded {rec_count} receipts.")

        # 8. Evidence Items
        if os.path.exists(EVIDENCE_CATALOG):
            with open(EVIDENCE_CATALOG, mode="r", encoding="utf-8") as f:
                catalog = json.load(f)
                ev_count = 0
                for item in catalog:
                    s = suppliers_by_name.get(item["supplier_legal_name"])
                    if s:
                        pub_dt = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).replace(tzinfo=None)
                        f_dt = datetime.fromisoformat(item["fetched_at"].replace("Z", "+00:00")).replace(tzinfo=None)
                        ev = EvidenceItem(
                            id=item["evidence_id"],
                            supplier_id=s.id,
                            source_url=item["source_url"],
                            publisher=item["publisher"],
                            published_at=pub_dt,
                            fetched_at=f_dt,
                            event_type=item["event_type"],
                            entity_match=item["entity_match"],
                            source_quality=item.get("source_quality", "primary_or_verified_report"),
                            severity=float(item["severity"]),
                            reliability_factor=float(item["reliability_factor"]),
                            freshness_factor=float(item["freshness_factor"]),
                            supporting_excerpt=item["supporting_excerpt"],
                            is_synthetic=item.get("is_synthetic", True),
                        )
                        db.add(ev)
                        ev_count += 1
                db.commit()
                print(f"Seeded {ev_count} evidence items from catalog.")

        print("Database seed completed successfully!")

    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    seed_database(force_reseed=True)
