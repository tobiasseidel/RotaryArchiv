"""
API Endpoints für Suche
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.rotary_archiv.api.schemas import (
    DocumentResponse,
    EntityResponse,
    SearchResponse,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import Document, Entity

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/", response_model=SearchResponse)
def search(
    q: str = Query(..., description="Suchanfrage"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Volltextsuche in Dokumenten und Entitäten
    """
    # Suche in Dokumenten (OCR-Text, Titel, Filename)
    documents = (
        db.query(Document)
        .filter(
            or_(
                Document.ocr_text.ilike(f"%{q}%"),
                Document.title.ilike(f"%{q}%"),
                Document.filename.ilike(f"%{q}%"),
            )
        )
        .limit(limit)
        .all()
    )

    # Suche in Entitäten
    entities = (
        db.query(Entity)
        .filter(or_(Entity.name.ilike(f"%{q}%"), Entity.description.ilike(f"%{q}%")))
        .limit(limit)
        .all()
    )

    return SearchResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        entities=[EntityResponse.model_validate(e) for e in entities],
        total=len(documents) + len(entities),
    )
