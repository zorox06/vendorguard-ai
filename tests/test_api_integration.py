"""Integration tests for FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_and_readiness():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res = client.get("/ready")
    assert res.status_code == 200


def test_suppliers_endpoints():
    res = client.get("/api/suppliers")
    assert res.status_code == 200
    suppliers = res.json()
    assert len(suppliers) >= 7

    # Find Apex Polymers
    apex = next(s for s in suppliers if s["legal_name"] == "Apex Polymers Ltd")
    assert apex["legal_name"] == "Apex Polymers Ltd"
    assert apex["late_fraction_L"] == pytest.approx(0.60, abs=0.1)
    assert apex["band"] == "high"


def test_materials_endpoints():
    res = client.get("/api/materials")
    assert res.status_code == 200
    materials = res.json()
    assert len(materials) >= 3

    resin = next(m for m in materials if m["material_name"] == "Polyethylene Resin HD-500")
    assert resin["coverage_days"] == pytest.approx(8.0, abs=0.1)
    assert resin["scenario_gap_days"] == pytest.approx(4.0, abs=0.1)


def test_alerts_and_acknowledgment():
    res = client.get("/api/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) >= 2

    alert_id = alerts[0]["id"]
    patch_res = client.patch(f"/api/alerts/{alert_id}", json={"status": "acknowledged"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "acknowledged"


def test_monitoring_run_202_accepted():
    res = client.post("/api/monitoring-runs")
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data


def test_replay_baselines():
    res = client.get("/api/replay/baselines")
    assert res.status_code == 200
    baselines = res.json()
    assert len(baselines) == 5
    system_ids = [b["system"] for b in baselines]
    assert system_ids == ["B0", "B1", "B2", "P1", "P2"]
