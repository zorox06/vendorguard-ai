"""FastAPI application entrypoint for VendorGuard AI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.app.adapters.storage import init_db
from backend.app.api.routes_suppliers import router as suppliers_router
from backend.app.api.routes_materials import router as materials_router
from backend.app.api.routes_alerts import router as alerts_router
from backend.app.api.routes_monitoring import router as monitoring_router
from backend.app.api.routes_imports import router as imports_router
from backend.app.api.routes_replay import router as replay_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    init_db()
    import os
    if os.getenv("SEED_DEMO_DATA", "").lower() in ("true", "1"):
        from backend.app.adapters.seed_db import seed_database
        seed_database()
    yield


app = FastAPI(
    title="VendorGuard AI API",
    description="Explainable Supplier Monitoring and Production-Disruption Decision Support",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(suppliers_router)
app.include_router(materials_router)
app.include_router(alerts_router)
app.include_router(monitoring_router)
app.include_router(imports_router)
app.include_router(replay_router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "vendorguard-ai-backend"}


@app.get("/ready")
def readiness_check():
    return {"status": "ready", "database": "connected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
