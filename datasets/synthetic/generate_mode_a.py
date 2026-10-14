"""Synthetic Dataset Generator for VendorGuard AI (Mode A: Packaging Manufacturing).

Implements Section 12 worked example and Section 14 dataset construction:
- 15 Fictional packaging suppliers
- 10 Raw packaging materials
- Exact arithmetic validation for Supplier A (Apex Polymers)
- 12-month PO history, receipts, inventory, and demand records
"""

import os
import csv
import json
from datetime import date, datetime, timedelta
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "mode_a")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CUTOFF_DATE = date(2026, 10, 10)
random.seed(42)

SUPPLIERS = [
    {
        "legal_name": "Apex Polymers Ltd",
        "aliases": "Apex Poly;Apex Chem;Apex Resin",
        "domain": "apexpolymers.local",
        "location": "Houston, TX",
        "registration_id": "US-TX-882910",
    },
    {
        "legal_name": "NovaPlast Resins Corp",
        "aliases": "NovaPlast;Nova Polymers",
        "domain": "novaplast.local",
        "location": "Baton Rouge, LA",
        "registration_id": "US-LA-110294",
    },
    {
        "legal_name": "FlexiFilm Global",
        "aliases": "FlexiFilm;Flexi Extrusions",
        "domain": "flexifilm.local",
        "location": "Greenville, SC",
        "registration_id": "US-SC-449102",
    },
    {
        "legal_name": "PackPro Corrugated Co",
        "aliases": "PackPro Boxes;PackPro Ohio",
        "domain": "packprobox.local",
        "location": "Columbus, OH",
        "registration_id": "US-OH-993812",
    },
    {
        "legal_name": "ChromaColor Labs",
        "aliases": "ChromaColor;Chroma Masterbatch",
        "domain": "chromacolor.local",
        "location": "McHenry, IL",
        "registration_id": "US-IL-332190",
    },
    {
        "legal_name": "ShieldBarrier Films",
        "aliases": "ShieldBarrier;Shield Polymer Films",
        "domain": "shieldbarrier.local",
        "location": "Allentown, PA",
        "registration_id": "US-PA-554109",
    },
    {
        "legal_name": "Delta Resins & Chemicals",
        "aliases": "Delta Resins;Delta Gulf Chem",
        "domain": "deltaresins.local",
        "location": "Beaumont, TX",
        "registration_id": "US-TX-774019",
    },
    {
        "legal_name": "SunPoly Masterbatches",
        "aliases": "SunPoly Colorants",
        "domain": "sunpoly.local",
        "location": "Charlotte, NC",
        "registration_id": "US-NC-228193",
    },
    {
        "legal_name": "Midwest Carton Works",
        "aliases": "Midwest Box & Board",
        "domain": "midwestcarton.local",
        "location": "Indianapolis, IN",
        "registration_id": "US-IN-662910",
    },
    {
        "legal_name": "EcoAdhesive Solutions",
        "aliases": "EcoAdhesives;EcoBond",
        "domain": "ecoadhesives.local",
        "location": "Atlanta, GA",
        "registration_id": "US-GA-881920",
    },
    {
        "legal_name": "PurePolymer Fine Chem",
        "aliases": "PurePolymer;PurePolymer Specialty",
        "domain": "purepolymerchem.local",
        "location": "Freeport, TX",
        "registration_id": "US-TX-102948",
    },
    {
        "legal_name": "Horizon Logistics & Films",
        "aliases": "Horizon Films;Horizon Freight Supply",
        "domain": "horizonfilms.local",
        "location": "Richmond, VA",
        "registration_id": "US-VA-551029",
    },
    {
        "legal_name": "Atlas Packaging Supply",
        "aliases": "Atlas Packaging;Atlas Box Supply",
        "domain": "atlaspackaging.local",
        "location": "Louisville, KY",
        "registration_id": "US-KY-771920",
    },
    {
        "legal_name": "Precision Inks International",
        "aliases": "Precision Inks;PII Coatings",
        "domain": "precisioninks.local",
        "location": "Cincinnati, OH",
        "registration_id": "US-OH-883921",
    },
    {
        "legal_name": "Vanguard Desiccant Corp",
        "aliases": "Vanguard Desiccants",
        "domain": "vanguarddesiccant.local",
        "location": "Nashville, TN",
        "registration_id": "US-TN-991024",
    },
]

MATERIALS = [
    {"name": "Polyethylene Resin HD-500", "canonical_unit": "kg", "criticality": "tier_1", "on_hand": 800.0, "reserved": 0.0, "daily_burn": 100.0},
    {"name": "Polyethylene Resin LD-200", "canonical_unit": "kg", "criticality": "tier_1", "on_hand": 1500.0, "reserved": 200.0, "daily_burn": 80.0},
    {"name": "High Barrier PVDC Film 25um", "canonical_unit": "rolls", "criticality": "tier_1", "on_hand": 120.0, "reserved": 20.0, "daily_burn": 10.0},
    {"name": "Biaxially-Oriented PP Film", "canonical_unit": "rolls", "criticality": "tier_2", "on_hand": 250.0, "reserved": 50.0, "daily_burn": 15.0},
    {"name": "White Masterbatch MB-01", "canonical_unit": "kg", "criticality": "tier_2", "on_hand": 450.0, "reserved": 50.0, "daily_burn": 25.0},
    {"name": "Slip Additive SA-90", "canonical_unit": "kg", "criticality": "tier_2", "on_hand": 180.0, "reserved": 30.0, "daily_burn": 5.0},
    {"name": "3-Ply Corrugated Shipping Cartons", "canonical_unit": "units", "criticality": "tier_3", "on_hand": 5000.0, "reserved": 500.0, "daily_burn": 400.0},
    {"name": "Solvent-Based Flexographic Inks", "canonical_unit": "liters", "criticality": "tier_2", "on_hand": 300.0, "reserved": 50.0, "daily_burn": 20.0},
    {"name": "Hot-Melt Adhesive Granules", "canonical_unit": "kg", "criticality": "tier_3", "on_hand": 600.0, "reserved": 100.0, "daily_burn": 30.0},
    {"name": "Silica Gel Desiccant Pouches", "canonical_unit": "packs", "criticality": "tier_3", "on_hand": 2000.0, "reserved": 200.0, "daily_burn": 150.0},
]

SUPPLIER_MATERIALS = [
    {"supplier_name": "Apex Polymers Ltd", "material_name": "Polyethylene Resin HD-500", "normal_lead_time_days": 6.0, "is_approved": "true"},
    {"supplier_name": "Delta Resins & Chemicals", "material_name": "Polyethylene Resin HD-500", "normal_lead_time_days": 5.0, "is_approved": "true"},
    {"supplier_name": "NovaPlast Resins Corp", "material_name": "Polyethylene Resin LD-200", "normal_lead_time_days": 7.0, "is_approved": "true"},
    {"supplier_name": "Delta Resins & Chemicals", "material_name": "Polyethylene Resin LD-200", "normal_lead_time_days": 6.0, "is_approved": "true"},
    {"supplier_name": "FlexiFilm Global", "material_name": "High Barrier PVDC Film 25um", "normal_lead_time_days": 10.0, "is_approved": "true"},
    {"supplier_name": "ShieldBarrier Films", "material_name": "Biaxially-Oriented PP Film", "normal_lead_time_days": 8.0, "is_approved": "true"},
    {"supplier_name": "Horizon Logistics & Films", "material_name": "Biaxially-Oriented PP Film", "normal_lead_time_days": 10.0, "is_approved": "true"},
    {"supplier_name": "ChromaColor Labs", "material_name": "White Masterbatch MB-01", "normal_lead_time_days": 6.0, "is_approved": "true"},
    {"supplier_name": "SunPoly Masterbatches", "material_name": "White Masterbatch MB-01", "normal_lead_time_days": 5.0, "is_approved": "true"},
    {"supplier_name": "SunPoly Masterbatches", "material_name": "Slip Additive SA-90", "normal_lead_time_days": 7.0, "is_approved": "true"},
    {"supplier_name": "PackPro Corrugated Co", "material_name": "3-Ply Corrugated Shipping Cartons", "normal_lead_time_days": 4.0, "is_approved": "true"},
    {"supplier_name": "Midwest Carton Works", "material_name": "3-Ply Corrugated Shipping Cartons", "normal_lead_time_days": 5.0, "is_approved": "true"},
    {"supplier_name": "Precision Inks International", "material_name": "Solvent-Based Flexographic Inks", "normal_lead_time_days": 5.0, "is_approved": "true"},
    {"supplier_name": "EcoAdhesive Solutions", "material_name": "Hot-Melt Adhesive Granules", "normal_lead_time_days": 7.0, "is_approved": "true"},
    {"supplier_name": "Atlas Packaging Supply", "material_name": "Hot-Melt Adhesive Granules", "normal_lead_time_days": 6.0, "is_approved": "true"},
    {"supplier_name": "Vanguard Desiccant Corp", "material_name": "Silica Gel Desiccant Pouches", "normal_lead_time_days": 12.0, "is_approved": "true"},
    {"supplier_name": "PurePolymer Fine Chem", "material_name": "Slip Additive SA-90", "normal_lead_time_days": 8.0, "is_approved": "true"},
]


def generate_all():
    print(f"Generating Mode A packaging manufacturing dataset in: {OUTPUT_DIR}")

    # 1. Suppliers CSV
    with open(os.path.join(OUTPUT_DIR, "suppliers.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["legal_name", "aliases", "domain", "location", "registration_id"])
        writer.writeheader()
        for s in SUPPLIERS:
            writer.writerow(s)

    # 2. Materials CSV
    with open(os.path.join(OUTPUT_DIR, "materials.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "canonical_unit", "criticality"])
        writer.writeheader()
        for m in MATERIALS:
            writer.writerow({"name": m["name"], "canonical_unit": m["canonical_unit"], "criticality": m["criticality"]})

    # 3. Supplier Materials CSV
    with open(os.path.join(OUTPUT_DIR, "supplier_materials.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["supplier_name", "material_name", "normal_lead_time_days", "is_approved"])
        writer.writeheader()
        for sm in SUPPLIER_MATERIALS:
            writer.writerow(sm)

    # 4. Inventory Snapshots CSV
    with open(os.path.join(OUTPUT_DIR, "inventory_snapshots.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["material_name", "warehouse", "on_hand_quantity", "reserved_quantity", "observed_at"])
        writer.writeheader()
        for m in MATERIALS:
            writer.writerow({
                "material_name": m["name"],
                "warehouse": "Main Extrusion Plant (Building 1)",
                "on_hand_quantity": m["on_hand"],
                "reserved_quantity": m["reserved"],
                "observed_at": f"{CUTOFF_DATE.isoformat()}T08:00:00Z",
            })

    # 5. Demand Forecasts CSV
    with open(os.path.join(OUTPUT_DIR, "demand_forecasts.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["material_name", "date", "daily_quantity"])
        writer.writeheader()
        for m in MATERIALS:
            for day_offset in range(30):
                d = CUTOFF_DATE + timedelta(days=day_offset)
                writer.writerow({
                    "material_name": m["name"],
                    "date": d.isoformat(),
                    "daily_quantity": m["daily_burn"],
                })

    # 6. Purchase Order Lines & Receipts
    # Construct historical lines across 12 months (2025-10-10 to 2026-10-10)
    po_lines = []
    receipts = []
    po_counter = 1000

    # SPECIAL CONSTRUCT: Apex Polymers Ltd to EXACTLY match Section 12 Worked Example!
    # Requirements at Cutoff Date 2026-10-10:
    # Recent 30-day window: [2026-09-10, 2026-10-10]
    # Previous 30-day window: [2026-08-11, 2026-09-09]
    # Recent Window: 10 due lines
    #   L = 0.60 => exactly 6 late lines, 4 on-time lines
    #   recent mean completed delay = 6.0 days
    #   6 late lines have delay = 6.0 days (completed), 4 on-time lines have delay = 0.0 days
    #   Shortfall F = 0.10 => e.g. 1 line has 0.0 delivered (shortfall 1.0) / 10 = 0.10, or each late line has 10% shortfall
    # Previous Window: 10 due lines
    #   previous mean completed delay = 2.0 days

    apex_recent_due = [CUTOFF_DATE - timedelta(days=i * 3) for i in range(1, 11)]
    for idx, due_d in enumerate(apex_recent_due):
        po_counter += 1
        po_num = f"PO-APEX-{po_counter}"
        ordered_qty = 500.0
        po_lines.append({
            "po_number": po_num,
            "line_number": 1,
            "supplier_name": "Apex Polymers Ltd",
            "material_name": "Polyethylene Resin HD-500",
            "ordered_quantity": ordered_qty,
            "unit": "kg",
            "committed_due_date": due_d.isoformat(),
        })
        # idx 0..3: On-Time lines (4 lines = 40% on time -> late fraction L = 60%)
        # idx 4..9: Late lines (6 lines)
        if idx < 4:
            # Delivered on due date
            receipts.append({
                "po_number": po_num,
                "line_number": 1,
                "accepted_quantity": ordered_qty,
                "rejected_quantity": 0.0,
                "received_at": f"{due_d.isoformat()}T10:00:00Z",
            })
        else:
            # Late lines completed with 6-day delay
            rec_d = due_d + timedelta(days=6)
            # Shortfall F: let one line be short delivered by 500 kg (unfulfilled) or across 6 lines:
            # 6 * 0.1666 * 500 = total 10% shortfall overall
            accepted_qty = 416.67 if idx == 4 else ordered_qty
            receipts.append({
                "po_number": po_num,
                "line_number": 1,
                "accepted_quantity": accepted_qty,
                "rejected_quantity": 0.0,
                "received_at": f"{rec_d.isoformat()}T14:00:00Z",
            })

    # Previous Window for Apex: 10 lines, all completed with 2-day delay on average
    apex_prev_due = [CUTOFF_DATE - timedelta(days=32 + i * 2) for i in range(10)]
    for idx, due_d in enumerate(apex_prev_due):
        po_counter += 1
        po_num = f"PO-APEX-PREV-{po_counter}"
        ordered_qty = 500.0
        po_lines.append({
            "po_number": po_num,
            "line_number": 1,
            "supplier_name": "Apex Polymers Ltd",
            "material_name": "Polyethylene Resin HD-500",
            "ordered_quantity": ordered_qty,
            "unit": "kg",
            "committed_due_date": due_d.isoformat(),
        })
        rec_d = due_d + timedelta(days=2)
        receipts.append({
            "po_number": po_num,
            "line_number": 1,
            "accepted_quantity": ordered_qty,
            "rejected_quantity": 0.0,
            "received_at": f"{rec_d.isoformat()}T10:00:00Z",
        })

    # Historical orders for other suppliers across 12 months
    for sup in SUPPLIERS:
        sname = sup["legal_name"]
        if sname == "Apex Polymers Ltd":
            continue

        # Cold-start supplier: only 4 lines total (< 10 lines)
        if sname == "Vanguard Desiccant Corp":
            num_orders = 4
        elif sname in ["NovaPlast Resins Corp", "PackPro Corrugated Co"]:
            num_orders = 40  # High volume stable
        else:
            num_orders = 25  # Normal volume

        matched_mats = [sm["material_name"] for sm in SUPPLIER_MATERIALS if sm["supplier_name"] == sname]
        mat_name = matched_mats[0] if matched_mats else "White Masterbatch MB-01"

        for o_idx in range(num_orders):
            po_counter += 1
            po_num = f"PO-{sname[:4].upper()}-{po_counter}"
            days_ago = int((o_idx / max(1, num_orders - 1)) * 340) + random.randint(1, 10)
            due_d = CUTOFF_DATE - timedelta(days=days_ago)

            qty = random.choice([200.0, 500.0, 1000.0, 2500.0])

            po_lines.append({
                "po_number": po_num,
                "line_number": 1,
                "supplier_name": sname,
                "material_name": mat_name,
                "ordered_quantity": qty,
                "unit": "kg" if "Resin" in mat_name or "Masterbatch" in mat_name else "units",
                "committed_due_date": due_d.isoformat(),
            })

            # Delivery performance rules
            if sname == "NovaPlast Resins Corp":
                # High reliability: 95% on-time, delays 0-1 days
                delay = 0 if random.random() < 0.95 else random.randint(1, 2)
            elif sname == "FlexiFilm Global":
                # Deteriorating: recent 30 days has high delays
                if days_ago <= 30:
                    delay = random.randint(4, 8)
                else:
                    delay = random.randint(0, 2)
            elif sname == "EcoAdhesive Solutions":
                # Isolated single late shipment
                delay = 5 if o_idx == 0 else 0
            elif sname == "ChromaColor Labs":
                delay = random.randint(2, 5) if days_ago <= 30 else 1
            else:
                delay = random.choice([0, 0, 1, 2])

            rec_d = due_d + timedelta(days=delay)
            # Only record receipt if it happened on or before cutoff date
            if rec_d <= CUTOFF_DATE:
                receipts.append({
                    "po_number": po_num,
                    "line_number": 1,
                    "accepted_quantity": qty,
                    "rejected_quantity": 0.0,
                    "received_at": f"{rec_d.isoformat()}T11:00:00Z",
                })

    # Write PO Lines CSV
    with open(os.path.join(OUTPUT_DIR, "purchase_order_lines.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["po_number", "line_number", "supplier_name", "material_name", "ordered_quantity", "unit", "committed_due_date"])
        writer.writeheader()
        for p in po_lines:
            writer.writerow(p)

    # Write Receipts CSV
    with open(os.path.join(OUTPUT_DIR, "receipts.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["po_number", "line_number", "accepted_quantity", "rejected_quantity", "received_at"])
        writer.writeheader()
        for r in receipts:
            writer.writerow(r)

    print(f"Generated {len(po_lines)} PO lines and {len(receipts)} receipts successfully.")


if __name__ == "__main__":
    generate_all()
