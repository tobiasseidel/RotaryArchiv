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
from src.rotary_archiv.core.models import (
    BBox,
    DocumentPage,
    DocumentUnit,
    OCRResult,
    Story,
)
from src.rotary_archiv.ocr.job_processor import get_unit_text_in_reading_order

router = APIRouter(prefix="/api/v1", tags=["public-api"])


# ─── Helper ────────────────────────────────────────────────────────────────

_EPOCH_RANGES: dict[str, tuple[int, int]] = {
    "30er": (1927, 1937),
    "90er": (1990, 2008),
}


def _extract_snippet(
    db: Session, unit: DocumentUnit, name: str, window: int = 120
) -> str:
    """Liest den Volltext der Unit und gibt einen Ausschnitt um die erste Nennung von `name` zurueck."""
    if not unit.page_ids:
        return unit.summary or ""
    try:
        text = get_unit_text_in_reading_order(db, unit.page_ids, page_separator="\n\n")
    except Exception:
        return unit.summary or ""
    if not text:
        return unit.summary or ""

    idx = text.lower().find(name.lower())
    if idx == -1:
        return unit.summary or text[: window * 2]

    start = max(0, idx - window)
    end = min(len(text), idx + len(name) + window)

    snippet = text[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"

    return snippet


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
    bbox: list[float] | None = None  # [x1, y1, x2, y2] relativ


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
        .filter(Story.is_published == True, Story.is_featured == True)
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
    q = db.query(Story).filter(Story.is_published == True)
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
        db.query(Story).filter(Story.slug == slug, Story.is_published == True).first()
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
        # Finde die erste passende DocumentUnit (auch nicht-öffentliche, der Link wird sonst nirgends angezeigt)
        unit = (
            db.query(DocumentUnit)
            .filter(DocumentUnit.document_id == page.document_id)
            .first()
        )
        if unit:
            info["document_unit_id"] = unit.id
        # BBox-Koordinaten (relativ)
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
    type: str  # "person" | "document"
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
    term = q.strip().lower()
    units = db.query(DocumentUnit).filter(DocumentUnit.is_public.is_(True)).all()

    if epoch:
        units = [u for u in units if _derive_epoch(u.date) == epoch]

    results: list[SearchResultItem] = []
    seen_persons: set[str] = set()
    seen_docs: set[int] = set()

    for unit in units:
        unit_epoch = _derive_epoch(unit.date)

        # Dokumente zuerst (vor Personen)
        doc_match = False
        doc_snippet = None
        for field, label in [
            (unit.title, "title"),
            (unit.summary, "summary"),
            (unit.topic, "topic"),
            (unit.place, "place"),
        ]:
            if field and term in field.lower():
                doc_match = True
                doc_snippet = field if label != "title" else None
                break

        if not doc_match and unit.page_ids:
            ocr_match = (
                db.query(OCRResult.text)
                .join(DocumentPage, OCRResult.document_page_id == DocumentPage.id)
                .filter(
                    DocumentPage.id.in_(unit.page_ids),
                    OCRResult.text.ilike(f"%{term}%"),
                )
                .limit(1)
                .first()
            )
            if ocr_match:
                doc_match = True
                full_text = get_unit_text_in_reading_order(
                    db, unit.page_ids, page_separator="\n\n"
                )
                if full_text and term in full_text.lower():
                    idx = full_text.lower().find(term)
                    start = max(0, idx - 60)
                    end = min(len(full_text), idx + len(term) + 60)
                    doc_snippet = (
                        ("…" if start > 0 else "")
                        + full_text[start:end]
                        + ("…" if end < len(full_text) else "")
                    )

        if doc_match and unit.id not in seen_docs:
            seen_docs.add(unit.id)
            results.append(
                SearchResultItem(
                    type="document",
                    id=unit.id,
                    slug=str(unit.id),
                    display_name=unit.title or f"Dokument #{unit.document_id}",
                    epoch=unit_epoch,
                    snippet=doc_snippet or unit.summary,
                    document_id=unit.document_id,
                )
            )

        # Personen im Unit-JSON durchsuchen
        for p in unit.persons or []:
            name = p.get("name", "")
            if not name:
                continue
            slug = _name_to_slug(name)
            if term in name.lower():
                if slug not in seen_persons:
                    seen_persons.add(slug)
                    results.append(
                        SearchResultItem(
                            type="person",
                            id=len(seen_persons),
                            slug=slug,
                            display_name=name,
                            epoch=unit_epoch,
                            snippet=p.get("role"),
                            portrait_url=None,
                        )
                    )
            # Unit-intern auch nach Namen in summary/title matchen
            elif term in (unit.summary or "").lower() and slug not in seen_persons:
                seen_persons.add(slug)
                results.append(
                    SearchResultItem(
                        type="person",
                        id=len(seen_persons),
                        slug=slug,
                        display_name=name,
                        epoch=unit_epoch,
                        snippet=p.get("role"),
                        portrait_url=None,
                    )
                )

    return results


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
                "snippet": _extract_snippet(db, unit, name),
                "document_id": unit.id,
                "highlight": name,
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

    transcription = (
        get_unit_text_in_reading_order(db, unit.page_ids, page_separator="\n\n")
        if unit.page_ids
        else None
    )

    return DocumentDetail(
        id=unit.id,
        document_id=unit.document_id,
        title=unit.title,
        date=unit.date,
        epoch=_derive_epoch(unit.date),
        document_type=doc_type,
        type=doc_type,
        summary=unit.summary,
        transcription=transcription,
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
