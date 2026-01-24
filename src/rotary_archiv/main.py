"""
FastAPI Hauptanwendung
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.rotary_archiv.api import documents, ocr, pages, review

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
