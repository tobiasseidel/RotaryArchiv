"""
Public API v1 - unabhaengige Endpoints fuer das Frontend.
Zugriff auf dieselbe DB wie das Admin-Backend, aber eigene Logik + eigenes Routing.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session

from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import (
    BBox,
    DocumentPage,
    DocumentUnit,
    OCRResult,
    Story,
)
from src.rotary_archiv.services import search_service
from src.rotary_archiv.services.search_service import (
    DocumentNotFoundError,
    PersonNotFoundError,
)

router = APIRouter(prefix="/api/v1", tags=["public-api"])


# ─── Helpers (used by stories + featured) ───────────────────────────────────

_EPOCH_RANGES: dict[str, tuple[int, int]] = {
    "30er": (1927, 1937),
    "90er": (1990, 2008),
}


def _derive_epoch(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    for epoch, (lo, hi) in _EPOCH_RANGES.items():
        if lo <= dt.year <= hi:
            return epoch
    return None


def _name_to_slug(name: str) -> str:
    import re

    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")


# ─── Schemas ───────────────────────────────────────────────────────────────


class PersonSummary(BaseModel):
    id: int
    slug: str
    display_name: str
    epoch: str | None = None
    is_public: bool = True
    notes: str | None = None
    portrait_url: str | None = None
    born_year: int | None = None
    died_year: int | None = None


class MembershipInfo(BaseModel):
    joined: str | None = None
    joined_document_id: int | None = None
    joined_quote: str | None = None
    left: str | None = None
    left_document_id: int | None = None
    left_quote: str | None = None
    role: str | None = None


class AttendanceInfo(BaseModel):
    total: int = 0
    present: int = 0
    period: str | None = None


class PersonDetail(BaseModel):
    id: int
    slug: str
    display_name: str
    epoch: str | None = None
    is_public: bool = True
    notes: str | None = None
    portrait_url: str | None = None
    born_year: int | None = None
    died_year: int | None = None
    membership: MembershipInfo | None = None
    timeline: list = Field(default_factory=list)
    attendance: AttendanceInfo | None = None
    network: dict = Field(default_factory=lambda: {"nodes": [], "edges": []})


class DocumentSummary(BaseModel):
    id: int
    document_id: int
    title: str | None = None
    date: datetime | None = None
    epoch: str | None = None
    document_type: str | None = None
    summary: str | None = None


class DocumentDetail(BaseModel):
    id: int
    document_id: int
    title: str | None = None
    date: datetime | None = None
    epoch: str | None = None
    document_type: str | None = None
    type: str | None = None
    summary: str | None = None
    transcription: str | None = None
    pages: list[dict] = Field(default_factory=list)
    persons: list[dict] = Field(default_factory=list)
    topic: str | None = None
    place: str | None = None


class FeaturedResponse(BaseModel):
    date: str | None = None
    quote_text: str | None = None
    quote_source: str | None = None
    document_id: int | None = None
    person_slug: str | None = None


# ─── Stories ────────────────────────────────────────────────────────────────


class StoryPublicSummary(BaseModel):
    id: int
    slug: str
    title: str
    teaser: str | None = None
    epoch: str | None = None
    image_url: str | None = None
    created_at: datetime


class SourceNote(BaseModel):
    id: int
    note_text: str | None = None
    note_author: str | None = None
    document_id: int | None = None
    document_unit_id: int | None = None
    page_number: int | None = None
    bbox: list[float] | None = None


class StoryPublicDetail(BaseModel):
    id: int
    slug: str
    title: str
    teaser: str | None = None
    body: str | None = None
    epoch: str | None = None
    image_url: str | None = None
    created_at: datetime
    sources: list[SourceNote] = []


@router.get("/stories/featured", response_model=StoryPublicSummary | None)
def get_featured_story(db: Session = Depends(get_db)):
    """Die eine gefeaturete Story für die Homepage."""
    story = (
        db.query(Story)
        .filter(Story.is_published == True, Story.is_featured == True)  # noqa: E712
        .order_by(Story.updated_at.desc())
        .first()
    )
    if not story:
        return None
    return StoryPublicSummary(
        id=story.id,
        slug=story.slug,
        title=story.title,
        teaser=story.teaser,
        epoch=story.epoch,
        image_url=story.image_url,
        created_at=story.created_at,
    )


@router.get("/stories", response_model=list[StoryPublicSummary])
def list_public_stories(
    epoch: str | None = Query(None, description="Filter: 30er | 90er"),
    db: Session = Depends(get_db),
):
    """Publizierte Stories (Liste), sortiert nach updated_at."""
    q = db.query(Story).filter(Story.is_published == True)  # noqa: E712
    if epoch:
        q = q.filter(Story.epoch == epoch)
    stories = q.order_by(Story.updated_at.desc()).all()
    return [
        StoryPublicSummary(
            id=s.id,
            slug=s.slug,
            title=s.title,
            teaser=s.teaser,
            epoch=s.epoch,
            image_url=s.image_url,
            created_at=s.created_at,
        )
        for s in stories
    ]


@router.get("/stories/{slug}", response_model=StoryPublicDetail)
def get_public_story(slug: str, db: Session = Depends(get_db)):
    """Story-Detail inkl. Quellen (verknüpfte Notes)."""
    story = (
        db.query(Story).filter(Story.slug == slug, Story.is_published == True).first()  # noqa: E712
    )
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story nicht gefunden"
        )

    def _resolve_note_source(bbox: BBox) -> dict:
        """Ermittelt Document-/Page-Info für eine als Quelle verknüpfte BBox."""
        info = {
            "id": bbox.id,
            "note_text": bbox.note_text,
            "note_author": bbox.note_author,
        }
        ocr_result = (
            db.query(OCRResult).filter(OCRResult.id == bbox.ocr_result_id).first()
        )
        if not ocr_result or not ocr_result.document_page_id:
            return info
        page = (
            db.query(DocumentPage)
            .filter(DocumentPage.id == ocr_result.document_page_id)
            .first()
        )
        if not page:
            return info
        info["document_id"] = page.document_id
        info["page_number"] = page.page_number
        unit = (
            db.query(DocumentUnit)
            .filter(DocumentUnit.document_id == page.document_id)
            .first()
        )
        if unit:
            info["document_unit_id"] = unit.id
        if bbox.bbox:
            info["bbox"] = bbox.bbox
        return info

    sources = [
        SourceNote(**_resolve_note_source(bbox))
        for bbox in (story.notes or [])
        if bbox.note_text
    ]

    return StoryPublicDetail(
        id=story.id,
        slug=story.slug,
        title=story.title,
        teaser=story.teaser,
        body=story.body,
        epoch=story.epoch,
        image_url=story.image_url,
        created_at=story.created_at,
        sources=sources,
    )


# ─── Search ─────────────────────────────────────────────────────────────────


class SearchResultItem(BaseModel):
    type: str
    id: int
    slug: str
    display_name: str
    epoch: str | None = None
    snippet: str | None = None
    document_id: int | None = None
    portrait_url: str | None = None


@router.get("/search", response_model=list[SearchResultItem])
def search(
    q: str = Query(..., min_length=1, description="Suchbegriff"),
    epoch: str | None = Query(None, description="Filter: 30er | 90er"),
    db: Session = Depends(get_db),
):
    """
    Volltextsuche über Personen und Dokumente.
    Durchsucht display_name, title, summary, topic, place.
    """
    raw = search_service.search(db, query=q, epoch=epoch)
    return [SearchResultItem(**item) for item in raw]


# ─── Endpoints ─────────────────────────────────────────────────────────────


@router.get("/persons", response_model=list[PersonSummary])
def list_persons(
    epoch: str | None = Query(None, description="Filter: 30er | 90er"),
    q: str | None = Query(None, description="Volltextsuche über display_name"),
    db: Session = Depends(get_db),
):
    """
    Aggregierte Personenliste aus öffentlichen DocumentUnits.
    Jede Person ist ein Eintrag aus dem `persons`-JSON einer public Unit.
    """
    raw = search_service.list_persons(db, epoch=epoch, query=q)
    return [PersonSummary(**p) for p in raw]


@router.get("/persons/{slug}", response_model=PersonDetail)
def get_person(
    slug: str,
    db: Session = Depends(get_db),
):
    """
    Personendetail - aggregiert aus DocumentUnits + Wikidata.
    """
    try:
        raw = search_service.get_person(db, slug)
        return PersonDetail(
            id=raw["id"],
            slug=raw["slug"],
            display_name=raw["display_name"],
            epoch=raw.get("epoch"),
            is_public=raw.get("is_public", True),
            notes=raw.get("notes"),
            portrait_url=raw.get("portrait_url"),
            born_year=raw.get("born_year"),
            died_year=raw.get("died_year"),
            membership=MembershipInfo(**raw["membership"])
            if raw.get("membership")
            else None,
            timeline=raw.get("timeline", []),
            attendance=None,
            network=raw.get("network", {"nodes": [], "edges": []}),
        )
    except PersonNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(
    epoch: str | None = Query(None, description="Filter: 30er | 90er"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Öffentliche DocumentUnits, sortiert nach Datum absteigend."""
    raw = search_service.list_documents(db, epoch=epoch, limit=limit, offset=offset)
    return [DocumentSummary(**d) for d in raw]


@router.get("/documents/{unit_id}", response_model=DocumentDetail)
def get_document(
    unit_id: int,
    db: Session = Depends(get_db),
):
    """
    Einzelne öffentliche DocumentUnit inkl. Seiten und Bilder.
    """
    try:
        raw = search_service.get_document(db, unit_id)
        return DocumentDetail(**raw)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/featured", response_model=FeaturedResponse)
def get_featured(
    db: Session = Depends(get_db),
):
    """
    Neueste öffentliche DocumentUnit als Startseiten-Highlight.
    """
    unit = (
        db.query(DocumentUnit)
        .filter(
            DocumentUnit.is_public == True,  # noqa: E712
            DocumentUnit.summary.isnot(None),
        )
        .order_by(nullslast(desc(DocumentUnit.date)))
        .first()
    )
    if not unit:
        unit = (
            db.query(DocumentUnit)
            .filter(DocumentUnit.is_public == True)  # noqa: E712
            .order_by(desc(DocumentUnit.id))
            .first()
        )
    if not unit:
        return FeaturedResponse(
            date=None,
            quote_text="Willkommen im RotaryArchiv - digitale Sammlung historischer Dokumente.",
            quote_source="RotaryArchiv",
            document_id=None,
            person_slug=None,
        )

    first_person = (unit.persons or [{}])[0]
    person_name = first_person.get("name", "")

    return FeaturedResponse(
        date=str(unit.date.date()) if unit.date else None,
        quote_text=unit.summary or "",
        quote_source=unit.title or f"Dokument #{unit.document_id}",
        document_id=unit.id,
        person_slug=_name_to_slug(person_name) if person_name else None,
    )
