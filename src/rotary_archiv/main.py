"""
FastAPI Hauptanwendung
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.rotary_archiv.api import documents, entities, triples, search, wikidata, sparql, pages

app = FastAPI(
    title="RotaryArchiv API",
    description="Digitales Archiv-System für Rotary Club Dokumente",
    version="0.1.0"
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
from src.rotary_archiv.config import settings
data_dir = Path(settings.documents_path)
if data_dir.exists():
    app.mount("/data", StaticFiles(directory=str(data_dir.resolve())), name="data")

# Include Routers
app.include_router(documents.router)
app.include_router(entities.router)
app.include_router(triples.router)
app.include_router(search.router)
app.include_router(wikidata.router)
app.include_router(sparql.router)
app.include_router(pages.router)


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
            "entities": "/api/entities",
            "triples": "/api/triples",
            "search": "/api/search",
            "wikidata": "/api/wikidata",
            "sparql": "/sparql"
        }
    }


@app.get("/health")
async def health_check():
    """Health Check Endpoint"""
    return {"status": "healthy"}
