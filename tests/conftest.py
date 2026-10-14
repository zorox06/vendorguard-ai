import os
import uuid
import pytest
from backend.app.adapters.storage import init_db, SyncSessionLocal
from backend.app.adapters.seed_db import seed_database
from backend.worker import process_monitoring_run
from backend.app.models.schema import MonitoringRun

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure database schema and test fixtures exist during test suite execution."""
    init_db()
    seed_database()
    
    # Run initial monitoring cycle so assessments and alerts exist for test assertions
    db = SyncSessionLocal()
    try:
        run = MonitoringRun(
            id=str(uuid.uuid4()),
            tenant_id="tenant-default",
            status="pending",
            idempotency_key=str(uuid.uuid4()),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        process_monitoring_run(run.id, db)
    finally:
        db.close()

    yield

    # Cleanup test db created during testing so repo stays free of demo data
    db_path = "vendorguard.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
