"""
Oeffentliche Read-Endpoints fuer veroeffentlichte DocumentUnits.
Vorstufe fuer Phase 2 — nur is_public=true Units, keine Auth.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session

from src.rotary_archiv.api.schemas import DocumentPagePublic
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import DocumentPage, DocumentType, DocumentUnit

router = APIRouter(prefix="/api/public", tags=["public"])


class DocumentUnitPublicResponse(BaseModel):
    """Schlankes oeffentliches Schema fuer eine veroeffentlichte Unit."""

    id: int
    document_id: int
    title: str | None = None
    date: datetime | None = None
    document_type: DocumentType | None = None
    page_ids: list[int]
    pages: list[DocumentPagePublic] = []
    summary: str | None = None
    persons: list[dict] = Field(default_factory=list)
    topic: str | None = None
    place: str | None = None

    @field_validator("persons", mode="before")
    @classmethod
    def default_list(cls, v: Any) -> list:
        return v if isinstance(v, list) else []

    class Config:
        from_attributes = True


@router.get("/units", response_model=list[DocumentUnitPublicResponse])
def list_public_units(
    document_type: DocumentType | None = Query(
        None, description="Optional filter on document type"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Listet alle veroeffentlichten DocumentUnits (is_public=true).
    Sortiert nach date DESC, NULL-Dates am Ende.
    """
    query = db.query(DocumentUnit).filter(DocumentUnit.is_public == True)  # noqa: E712

    if document_type is not None:
        query = query.filter(DocumentUnit.document_type == document_type)

    query = query.order_by(nullslast(desc(DocumentUnit.date)))
    units = query.offset(skip).limit(limit).all()

    result = []
    for u in units:
        data = DocumentUnitPublicResponse.model_validate(u)
        data.pages = _build_page_list(u, db)
        result.append(data)
    return result


@router.get("/units/{unit_id}", response_model=DocumentUnitPublicResponse)
def get_public_unit(
    unit_id: int,
    db: Session = Depends(get_db),
):
    """
    Liefert eine einzelne veroeffentlichte Unit.
    404 wenn nicht vorhanden oder nicht public.
    """
    unit = (
        db.query(DocumentUnit)
        .filter(
            DocumentUnit.id == unit_id,
            DocumentUnit.is_public == True,  # noqa: E712
        )
        .first()
    )
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found or not public",
        )
    data = DocumentUnitPublicResponse.model_validate(unit)
    data.pages = _build_page_list(unit, db)
    return data


def _build_page_list(unit: DocumentUnit, db: Session) -> list[DocumentPagePublic]:
    """Erzeuge Liste von DocumentPagePublic aus den page_ids einer Unit."""
    pages: list[DocumentPagePublic] = []
    if not unit.page_ids:
        return pages

    db_pages = db.query(DocumentPage).filter(DocumentPage.id.in_(unit.page_ids)).all()
    pages_by_id = {p.id: p for p in db_pages}

    for page_id in unit.page_ids:
        page = pages_by_id.get(page_id)
        if page is None:
            continue
        if page.file_path and page.is_extracted:
            image_url = f"/scans/{page.document_id}/{page.page_number}.png"
        else:
            image_url = None
        pages.append(
            DocumentPagePublic(page_number=page.page_number, image_url=image_url)
        )
    return pages
