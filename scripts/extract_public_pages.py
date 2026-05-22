"""
Einmaliges Skript zum Extrahieren von Seiten-PNGs für alle veröffentlichten
DocumentUnits. Befüllt DocumentPage.file_path nach der Extraktion.

Usage: python scripts/extract_public_pages.py
"""

import os
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from pathlib import Path

from sqlalchemy.orm import Session
from src.rotary_archiv.core.database import SessionLocal  # noqa: E402
from src.rotary_archiv.core.models import Document, DocumentPage, DocumentUnit  # noqa: E402
from src.rotary_archiv.config import settings  # noqa: E402
from src.rotary_archiv.utils.pdf_utils import extract_page_as_image  # noqa: E402
from src.rotary_archiv.utils.file_handler import get_file_path  # noqa: E402
from src.rotary_archiv.utils.pdf_utils import extract_page_as_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def extract_page_to_png(
    document: Document,
    page: DocumentPage,
    scans_dir: Path,
) -> str | None:
    """Extrahiere eine einzelne Seite als PNG und gib den Pfad zurueck."""
    if page.is_extracted and page.file_path:
        return page.file_path

    doc_scans_dir = scans_dir / str(document.id)
    doc_scans_dir.mkdir(parents=True, exist_ok=True)

    png_path = doc_scans_dir / f"{page.page_number}.png"
    pdf_path = get_file_path(document.file_path)

    if not pdf_path.exists():
        logger.error(f"PDF nicht gefunden: {pdf_path}")
        return None

    img = extract_page_as_image(
        str(pdf_path), page.page_number, dpi=settings.pdf_extraction_dpi
    )
    img.save(str(png_path), "PNG")
    return str(png_path)


def main():
    db: Session = SessionLocal()
    scans_dir = Path(settings.scans_path)

    try:
        public_units = (
            db.query(DocumentUnit)
            .filter(DocumentUnit.is_public == True)  # noqa: E712
            .all()
        )

        if not public_units:
            logger.info("Keine veroeffentlichten DocumentUnits gefunden.")
            return

        all_page_ids: set[int] = set()
        for unit in public_units:
            if unit.page_ids:
                all_page_ids.update(unit.page_ids)

        if not all_page_ids:
            logger.info("Keine Seiten in den veroeffentlichten Units gefunden.")
            return

        pages = db.query(DocumentPage).filter(DocumentPage.id.in_(all_page_ids)).all()
        pages_by_id = {p.id: p for p in pages}

        success = 0
        skipped = 0
        errors = 0

        for unit in public_units:
            doc_id = unit.document_id
            document = db.query(Document).filter(Document.id == doc_id).first()
            if not document:
                logger.warning(f"Dokument {doc_id} nicht gefunden (Unit {unit.id})")
                errors += 1
                continue

            for page_id in unit.page_ids or []:
                page = pages_by_id.get(page_id)
                if not page:
                    logger.warning(
                        f"DocumentPage {page_id} nicht gefunden (Unit {unit.id})"
                    )
                    errors += 1
                    continue

                if page.file_path and page.is_extracted:
                    logger.info(
                        f"Dokument {doc_id} Seite {page.page_number}: "
                        f"bereits vorhanden ({page.file_path})"
                    )
                    skipped += 1
                    continue

                try:
                    file_path = extract_page_to_png(document, page, scans_dir)
                    if file_path is None:
                        errors += 1
                        continue
                    page.file_path = file_path
                    page.file_type = "image/png"
                    page.is_extracted = True
                    db.add(page)
                    db.commit()
                    logger.info(
                        f"Dokument {doc_id} Seite {page.page_number}: OK ({file_path})"
                    )
                    success += 1
                except Exception as e:
                    db.rollback()
                    logger.error(
                        f"Dokument {doc_id} Seite {page.page_number}: " f"Fehler - {e}"
                    )
                    errors += 1

        logger.info(
            f"Fertig: {success} extrahiert, {skipped} bereits vorhanden, "
            f"{errors} Fehler"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
