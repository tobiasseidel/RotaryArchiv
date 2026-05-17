"""
FastAPI Hauptanwendung
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from src.rotary_archiv.api import (
    documents,
    erschliessung,
    erschliessung_overview,
    ocr,
    pages,
    quality,
    review,
)
from src.rotary_archiv.api import settings as settings_api

logger = logging.getLogger(__name__)

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

app = FastAPI(
    title="RotaryArchiv API",
    description="Digitales Archiv-System für Rotary Club Dokumente",
    version="0.1.0",
)


@app.on_event("startup")
async def run_pending_migrations():
    """Prüft und führt ausstehende Alembic-Migrationen beim Start aus."""
    try:
        from alembic.command import upgrade
        from alembic.config import Config

        project_root = Path(__file__).parent.parent.parent
        alembic_cfg = project_root / "alembic.ini"
        if alembic_cfg.exists():
            cfg = Config(str(alembic_cfg))
            cfg.set_main_option("script_location", str(project_root / "alembic"))
            upgrade(cfg, "head")
            logger.info("Alembic-Migrationen erfolgreich ausgeführt")
    except Exception as e:
        logger.warning(f"Alembic-Migration übersprungen: {e}")
        import traceback

        logger.warning(f"Alembic-Fehler Details: {traceback.format_exc()}")


# Request Logging Middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(
            f"Response: {request.method} {request.url.path} -> {response.status_code}"
        )
        return response


app.add_middleware(RequestLoggingMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files für Frontend
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Routen
app.include_router(documents.router, tags=["documents"])
app.include_router(pages.router, tags=["pages"])
app.include_router(ocr.router, tags=["ocr"])
app.include_router(review.router, tags=["review"])
app.include_router(quality.router, tags=["quality"])
app.include_router(erschliessung.router, prefix="/api/pages", tags=["erschliessung"])
app.include_router(
    erschliessung_overview.router,
    prefix="/api/erschliessung-overview",
    tags=["erschliessung-overview"],
)
app.include_router(settings_api.router, tags=["settings"])


@app.get("/")
async def root():
    from fastapi.responses import FileResponse

    static_dir = Path(__file__).parent.parent.parent / "static"
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "RotaryArchiv API"}


@app.get("/health")
async def health():
    return {"status": "ok"}
