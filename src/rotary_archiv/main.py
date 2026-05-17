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
from src.rotary_archiv.config import settings

logger = logging.getLogger(__name__)

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

# Static Files für Dokumente und Seiten (für Vorschau)
data_dir = Path(settings.documents_path)
if data_dir.exists():
    app.mount("/data", StaticFiles(directory=str(data_dir.resolve())), name="data")

# Static Files für gecachte Bilder (Wikidata/Commons/Fotothek)
image_cache_dir = Path(settings.image_cache_path)
image_cache_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media-cache",
    StaticFiles(directory=str(image_cache_dir.resolve())),
    name="media-cache",
)

# Include Routers
app.include_router(documents.router)
app.include_router(ocr.router)
app.include_router(pages.router)
app.include_router(erschliessung.router, prefix="/api/pages")
app.include_router(erschliessung_overview.router)
app.include_router(review.router)
app.include_router(quality.router)
app.include_router(settings_api.router)

# NOTE: Folgende Router sind vorerst nicht aktiviert:
# - triples.router (markiert als ungenutzt)
# - wikidata.router (markiert als ungenutzt)
# - sparql.router (markiert als ungenutzt)


@app.get("/")
async def root():
    """Root Endpoint - Redirect zu Frontend"""
    from fastapi.responses import FileResponse

    static_file = static_dir / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file))
    return {
        "message": "RotaryArchiv API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "documents": "/api/documents",
            "pages": "/api/pages",
            "ocr": "/api/ocr",
        },
    }


@app.get("/health")
async def health_check():
    """Health Check Endpoint"""
    return {"status": "healthy"}
