"""Re-export FastAPI app for backend.app.main compatibility."""
from backend.main import app

__all__ = ["app"]
