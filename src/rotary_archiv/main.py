"""
FastAPI Hauptanwendung
"""

from pathlib import Path

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from src.rotary_archiv.api import documents, ocr, pages, quality, review

logger = logging.getLogger(__name__)

# NOTE: Folgende APIs sind vorerst nicht verwendet:
# - entities (gelöscht)
# - search (gelöscht)
# - triples (markiert als ungenutzt)
# - wikidata (markiert als ungenutzt)
# - sparql (markiert als ungenutzt)
from src.rotary_archiv.config import settings

app = FastAPI(
    title="RotaryArchiv API",
    description="Digitales Archiv-System für Rotary Club Dokumente",
    version="0.1.0",
)

# Request Logging Middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Response: {request.method} {request.url.path} -> {response.status_code}")
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

# Include Routers
app.include_router(documents.router)
app.include_router(ocr.router)
app.include_router(pages.router)
app.include_router(review.router)
app.include_router(quality.router)

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
