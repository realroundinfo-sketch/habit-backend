"""Entry point for deployment. Platform runs uvicorn main:app — expose app here."""
from app.main import app

__all__ = ["app"]
