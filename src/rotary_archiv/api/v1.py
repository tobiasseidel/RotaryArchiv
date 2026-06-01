"""
Public API v1 - unabhaengige Endpoints fuer das Frontend.
Zugriff auf dieselbe DB wie das Admin-Backend, aber eigene Logik + eigenes Routing.
"""

from datetime import datetime
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session

from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import DocumentPage, DocumentUnit

router = APIRouter(prefix="/api/v1", tags=["public-api"])


# ─── Helper ────────────────────────────────────────────────────────────────

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
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")


def _build_page_list(unit: DocumentUnit, db: Session) -> list[dict]:
    pages: list[dict] = []
    if not unit.page_ids:
        return pages
    db_pages = db.query(DocumentPage).filter(DocumentPage.id.in_(unit.page_ids)).all()
    by_id = {p.id: p for p in db_pages}
    for pid in unit.page_ids:
        page = by_id.get(pid)
        if page is None:
            continue
        image_url = None
        if page.file_path and page.is_extracted:
            image_url = f"/scans/{page.document_id}/{page.page_number}.png"
        pages.append(
            {"id": page.id, "page_number": page.page_number, "image_url": image_url}
        )
    return pages


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
    units = db.query(DocumentUnit).filter(DocumentUnit.is_public.is_(True)).all()

    seen: dict[str, dict] = {}
    for unit in units:
        unit_epoch = _derive_epoch(unit.date)
        if epoch and unit_epoch != epoch:
            continue
        for p in unit.persons or []:
            name = p.get("name", "")
            if not name:
                continue
            if q and q.lower() not in name.lower():
                continue
            if name not in seen:
                seen[name] = {
                    "id": len(seen) + 1,
                    "slug": _name_to_slug(name),
                    "display_name": name,
                    "epoch": unit_epoch,
                    "is_public": True,
                    "notes": p.get("role"),
                    "portrait_url": None,
                    "born_year": None,
                    "died_year": None,
                }
            if seen[name]["epoch"] is None:
                seen[name]["epoch"] = unit_epoch
    return list(seen.values())


@router.get("/persons/{slug}", response_model=PersonDetail)
def get_person(
    slug: str,
    db: Session = Depends(get_db),
):
    """
    Personendetail - aggregiert aus DocumentUnits + Wikidata.
    """
    units = db.query(DocumentUnit).filter(DocumentUnit.is_public == True).all()  # noqa: E712
    matches = []
    for unit in units:
        for p in unit.persons or []:
            name = p.get("name", "")
            if not name:
                continue
            if _name_to_slug(name) == slug or name == slug:
                matches.append((unit, p))

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person nicht gefunden"
        )

    first_person = matches[0][1]
    first_unit = matches[0][0]
    name = first_person.get("name", slug)

    doc_links = []
    for unit, p in matches:
        doc_links.append(
            {
                "document_id": unit.document_id,
                "unit_id": unit.id,
                "title": unit.title or f"Dokument #{unit.document_id}",
                "role": p.get("role"),
            }
        )

    return PersonDetail(
        id=hash(name) % 100000,
        slug=slug,
        display_name=name,
        epoch=_derive_epoch(first_unit.date),
        is_public=True,
        notes=first_person.get("role"),
        portrait_url=None,
        born_year=None,
        died_year=None,
        membership=MembershipInfo(role=first_person.get("role")),
        timeline=[
            {
                "date": str(unit.date.date()) if unit.date else None,
                "snippet": unit.summary or "",
                "document_id": unit.document_id,
            }
            for unit, _ in matches
            if unit.date or unit.summary
        ],
        attendance=None,
        network={"nodes": [], "edges": []},
    )


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(
    epoch: str | None = Query(None, description="Filter: 30er | 90er"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Öffentliche DocumentUnits, sortiert nach Datum absteigend."""
    query = db.query(DocumentUnit).filter(DocumentUnit.is_public == True)  # noqa: E712
    query = query.order_by(nullslast(desc(DocumentUnit.date)))
    units = query.all()

    if epoch:
        units = [u for u in units if _derive_epoch(u.date) == epoch]

    units = units[offset : offset + limit]

    result = []
    for u in units:
        result.append(
            DocumentSummary(
                id=u.id,
                document_id=u.document_id,
                title=u.title,
                date=u.date,
                epoch=_derive_epoch(u.date),
                document_type=u.document_type.value if u.document_type else None,
                summary=u.summary,
            )
        )
    return result


@router.get("/documents/{unit_id}", response_model=DocumentDetail)
def get_document(
    unit_id: int,
    db: Session = Depends(get_db),
):
    """
    Einzelne öffentliche DocumentUnit inkl. Seiten und Bilder.
    """
    unit = (
        db.query(DocumentUnit)
        .filter(
            DocumentUnit.id == unit_id,
            DocumentUnit.is_public.is_(True),
        )
        .first()
    )
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden"
        )

    pages = _build_page_list(unit, db)
    doc_type = unit.document_type.value if unit.document_type else None
    return DocumentDetail(
        id=unit.id,
        document_id=unit.document_id,
        title=unit.title,
        date=unit.date,
        epoch=_derive_epoch(unit.date),
        document_type=doc_type,
        type=doc_type,
        summary=unit.summary,
        pages=pages,
        persons=unit.persons or [],
        topic=unit.topic,
        place=unit.place,
    )


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
