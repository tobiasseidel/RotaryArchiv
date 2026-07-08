"""Search Service - Business-Logic für Volltextsuche, Personen-Aggregation, Document-Detail."""

from datetime import datetime
import re

from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session

from src.rotary_archiv.core.models import (
    DocumentPage,
    DocumentUnit,
    OCRResult,
)
from src.rotary_archiv.ocr.job_processor import get_unit_text_in_reading_order

# ─── Constants ───────────────────────────────────────────────────────────────

_EPOCH_RANGES: dict[str, tuple[int, int]] = {
    "30er": (1927, 1937),
    "90er": (1990, 2008),
}


# ─── Exceptions ──────────────────────────────────────────────────────────────


class SearchServiceError(Exception):
    """Basis-Exception für Search-Service."""


class PersonNotFoundError(SearchServiceError):
    def __init__(self, slug: str):
        self.slug = slug
        super().__init__(f"Person '{slug}' nicht gefunden")


class DocumentNotFoundError(SearchServiceError):
    def __init__(self, unit_id: int):
        self.unit_id = unit_id
        super().__init__(f"Dokument {unit_id} nicht gefunden")


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _derive_epoch(dt: datetime | None) -> str | None:
    """Ordnet ein Datum einer Epoche zu."""
    if dt is None:
        return None
    for epoch, (lo, hi) in _EPOCH_RANGES.items():
        if lo <= dt.year <= hi:
            return epoch
    return None


def _name_to_slug(name: str) -> str:
    """Konvertiert einen Namen in einen URL-freundlichen Slug."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")


def _extract_snippet(
    db: Session, unit: DocumentUnit, name: str, window: int = 120
) -> str:
    """Liest den Volltext der Unit und gibt einen Ausschnitt um die erste Nennung von `name` zurück."""
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


def _build_page_list(unit: DocumentUnit, db: Session) -> list[dict]:
    """Baut eine Seitenliste mit image_url."""
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


# ─── Service Functions ───────────────────────────────────────────────────────


def search(
    db: Session,
    query: str,
    epoch: str | None = None,
) -> list[dict]:
    """Volltextsuche über Personen und Dokumente."""
    term = query.strip().lower()
    units = db.query(DocumentUnit).filter(DocumentUnit.is_public.is_(True)).all()

    if epoch:
        units = [u for u in units if _derive_epoch(u.date) == epoch]

    results: list[dict] = []
    seen_persons: set[str] = set()
    seen_docs: set[int] = set()

    for unit in units:
        unit_epoch = _derive_epoch(unit.date)

        # Dokumente zuerst
        doc_match = False
        doc_snippet = None
        for field in [unit.title, unit.summary, unit.topic, unit.place]:
            if field and term in field.lower():
                doc_match = True
                doc_snippet = field
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
                {
                    "type": "document",
                    "id": unit.id,
                    "slug": str(unit.id),
                    "display_name": unit.title or f"Dokument #{unit.document_id}",
                    "epoch": unit_epoch,
                    "snippet": doc_snippet or unit.summary,
                    "document_id": unit.document_id,
                    "portrait_url": None,
                }
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
                        {
                            "type": "person",
                            "id": len(seen_persons),
                            "slug": slug,
                            "display_name": name,
                            "epoch": unit_epoch,
                            "snippet": p.get("role"),
                            "portrait_url": None,
                        }
                    )
            elif term in (unit.summary or "").lower() and slug not in seen_persons:
                seen_persons.add(slug)
                results.append(
                    {
                        "type": "person",
                        "id": len(seen_persons),
                        "slug": slug,
                        "display_name": name,
                        "epoch": unit_epoch,
                        "snippet": p.get("role"),
                        "portrait_url": None,
                    }
                )

    return results


def list_persons(
    db: Session,
    epoch: str | None = None,
    query: str | None = None,
) -> list[dict]:
    """Aggregierte Personenliste aus öffentlichen DocumentUnits."""
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
            if query and query.lower() not in name.lower():
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


def get_person(db: Session, slug: str) -> dict:
    """Personendetail - aggregiert aus DocumentUnits."""
    units = db.query(DocumentUnit).filter(DocumentUnit.is_public.is_(True)).all()
    matches = []
    for unit in units:
        for p in unit.persons or []:
            name = p.get("name", "")
            if not name:
                continue
            if _name_to_slug(name) == slug or name == slug:
                matches.append((unit, p))

    if not matches:
        raise PersonNotFoundError(slug)

    first_person = matches[0][1]
    first_unit = matches[0][0]
    name = first_person.get("name", slug)

    return {
        "id": hash(name) % 100000,
        "slug": slug,
        "display_name": name,
        "epoch": _derive_epoch(first_unit.date),
        "is_public": True,
        "notes": first_person.get("role"),
        "portrait_url": None,
        "born_year": None,
        "died_year": None,
        "membership": {"role": first_person.get("role")},
        "timeline": [
            {
                "date": str(unit.date.date()) if unit.date else None,
                "snippet": _extract_snippet(db, unit, name),
                "document_id": unit.id,
                "highlight": name,
            }
            for unit, _ in matches
            if unit.date or unit.summary
        ],
        "attendance": None,
        "network": {"nodes": [], "edges": []},
    }


def list_documents(
    db: Session,
    epoch: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Öffentliche DocumentUnits, sortiert nach Datum absteigend."""
    query = db.query(DocumentUnit).filter(DocumentUnit.is_public.is_(True))
    query = query.order_by(nullslast(desc(DocumentUnit.date)))
    units = query.all()

    if epoch:
        units = [u for u in units if _derive_epoch(u.date) == epoch]

    units = units[offset : offset + limit]

    return [
        {
            "id": u.id,
            "document_id": u.document_id,
            "title": u.title,
            "date": u.date,
            "epoch": _derive_epoch(u.date),
            "document_type": u.document_type.value if u.document_type else None,
            "summary": u.summary,
        }
        for u in units
    ]


def get_document(db: Session, unit_id: int) -> dict:
    """Einzelne öffentliche DocumentUnit inkl. Seiten und Bilder."""
    unit = (
        db.query(DocumentUnit)
        .filter(
            DocumentUnit.id == unit_id,
            DocumentUnit.is_public.is_(True),
        )
        .first()
    )
    if not unit:
        raise DocumentNotFoundError(unit_id)

    pages = _build_page_list(unit, db)
    doc_type = unit.document_type.value if unit.document_type else None

    transcription = (
        get_unit_text_in_reading_order(db, unit.page_ids, page_separator="\n\n")
        if unit.page_ids
        else None
    )

    return {
        "id": unit.id,
        "document_id": unit.document_id,
        "title": unit.title,
        "date": unit.date,
        "epoch": _derive_epoch(unit.date),
        "document_type": doc_type,
        "type": doc_type,
        "summary": unit.summary,
        "transcription": transcription,
        "pages": pages,
        "persons": unit.persons or [],
        "topic": unit.topic,
        "place": unit.place,
    }
