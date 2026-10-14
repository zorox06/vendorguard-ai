"""Unit tests for Bounded Search Adapter and Entity Resolution."""

from datetime import datetime
from backend.app.adapters.search_adapter import BoundedSearchAdapter
from backend.app.domain.models_domain import ExternalEvidenceStatus


def test_entity_resolution_verified():
    adapter = BoundedSearchAdapter()
    records, status, err = adapter.check_supplier_signals(
        supplier_id="sup-apex",
        legal_name="Apex Polymers Ltd",
        aliases=["Apex Poly"],
        domain="apexpolymers.local",
        location="Houston, TX",
        as_of_dt=datetime(2026, 10, 10),
    )
    assert status == ExternalEvidenceStatus.RELIABLE_EVIDENCE
    assert len(records) >= 1
    assert any("cracker" in r.supporting_excerpt.lower() for r in records)


def test_same_name_unrelated_company_rejected():
    adapter = BoundedSearchAdapter()
    records, status, err = adapter.check_supplier_signals(
        supplier_id="sup-pure",
        legal_name="PurePolymer Fine Chem",
        aliases=["PurePolymer Specialty"],
        domain="purepolymerchem.local",
        location="Freeport, TX",
        as_of_dt=datetime(2026, 10, 10),
    )
    # PurePolymer BioPharma Inc has ambiguous entity match in catalog
    assert status == ExternalEvidenceStatus.AMBIGUOUS_ENTITY
    assert len(records) == 0
    assert "ambiguity" in err.lower()


def test_syndicated_articles_deduplication():
    adapter = BoundedSearchAdapter()
    records, status, _ = adapter.check_supplier_signals(
        supplier_id="sup-apex",
        legal_name="Apex Polymers Ltd",
        as_of_dt=datetime(2026, 10, 10),
    )
    # Catalog has ev-apex-001 and ev-apex-002-syndicated
    # Deduplication ensures only 1 event is counted
    assert len(records) == 1
    assert records[0].severity == 0.80


def test_simulated_search_failure():
    adapter = BoundedSearchAdapter()
    records, status, err = adapter.check_supplier_signals(
        supplier_id="sup-apex",
        legal_name="Apex Polymers Ltd",
        simulated_failure=True,
    )
    assert status == ExternalEvidenceStatus.UNAVAILABLE
    assert len(records) == 0
    assert "timeout" in err.lower() or "limit" in err.lower()


def test_future_evidence_leakage_prevention():
    adapter = BoundedSearchAdapter()
    # Evidence published in September 2026 should not be accessible if as_of is August 2026
    records, status, _ = adapter.check_supplier_signals(
        supplier_id="sup-apex",
        legal_name="Apex Polymers Ltd",
        as_of_dt=datetime(2026, 8, 1),
    )
    assert status == ExternalEvidenceStatus.NO_RELEVANT_EVIDENCE
    assert len(records) == 0
