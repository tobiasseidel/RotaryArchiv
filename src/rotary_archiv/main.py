"""
FastAPI Hauptanwendung
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/")
async def root():
    """Root Endpoint"""
    return {
        "message": "RotaryArchiv API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health Check Endpoint"""
    return {"status": "healthy"}
