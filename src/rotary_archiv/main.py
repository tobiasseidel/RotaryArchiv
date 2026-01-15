"""
FastAPI Hauptanwendung
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.rotary_archiv.api import documents, entities, triples, search, wikidata, sparql

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

# Include Routers
app.include_router(documents.router)
app.include_router(entities.router)
app.include_router(triples.router)
app.include_router(search.router)
app.include_router(wikidata.router)
app.include_router(sparql.router)


@app.get("/")
async def root():
    """Root Endpoint"""
    return {
        "message": "RotaryArchiv API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "documents": "/api/documents",
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
