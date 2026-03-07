"""
API für globale App-Einstellungen (z. B. OCR-Sichtung / LLM-Sichtung).
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.rotary_archiv.config import settings as app_config
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import AppSetting, Document, DocumentUnit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

OCR_SIGHT_KEY = "ocr_sight"
CONTENT_ANALYSIS_KEY = "content_analysis"


def _default_ocr_sight() -> dict[str, Any]:
    """Defaults für OCR-Sichtung (Fallback wenn keine DB-Werte)."""
    return {
        "time_period": "",
        "language_style": "",
        "expected_names": "",
        "typical_phrases": "",
        "review_notes": "",
        "sight_context": "none",
        "black_pc_min": app_config.auto_sight_black_pc_min,
        "black_pc_max": app_config.auto_sight_black_pc_max,
        "auto_sight_enabled": True,
        "score_threshold": app_config.auto_sight_threshold,
    }


class OcrSightSettingsBody(BaseModel):
    """Request-Body für PUT /api/settings/ocr-sight."""

    time_period: str = Field(default="", description="z.B. 1900-1945, 1920er")
    language_style: str = Field(
        default="", description="z.B. Deutsch, Amtssprache 1920er"
    )
    expected_names: str = Field(
        default="",
        description="Namen, die im Bestand vorkommen können (komma- oder zeilengetrennt); hilft der KI, gute Erkennung zu erkennen",
    )
    typical_phrases: str = Field(
        default="",
        description="Typische Formulierungen/Floskeln (eine pro Zeile); wenn der Text solche enthält und sinnvoll wirkt, soll die Confidence höher ausfallen",
    )
    review_notes: str = Field(
        default="",
        description="Sonstige Anmerkungen und Wünsche des Nutzers zur KI-Review (freier Text)",
    )
    sight_context: str = Field(
        default="none",
        description="Kontext für KI-Review: none = nur Box-Text; neighbours = Nachbarboxen (Lesereihenfolge); full_page = ganze Seite",
    )
    black_pc_min: float = Field(
        default=18, ge=0, description="Untergrenze schwarze Pixel/Zeichen"
    )
    black_pc_max: float = Field(
        default=35, ge=0, description="Obergrenze schwarze Pixel/Zeichen"
    )
    auto_sight_enabled: bool = Field(
        default=True, description="KI-Review und Auto-Bestätigung ein/aus"
    )
    score_threshold: float = Field(
        default=0.85, ge=0, le=1, description="Score-Threshold für Auto-Sichtung"
    )


@router.get("/ocr-sight")
def get_ocr_sight_settings(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Liest die Einstellungen für OCR-Sichtung (LLM-Sichtung).
    Falls keine gespeichert: Defaults aus Config.
    """
    row = db.query(AppSetting).filter(AppSetting.key == OCR_SIGHT_KEY).first()
    if row and row.value_json:
        out = dict(_default_ocr_sight())
        out.update(row.value_json)
        return out
    return _default_ocr_sight()


def get_ocr_sight_settings_for_job(db: Session) -> dict[str, Any]:
    """
    Liest OCR-Sicht-Einstellungen aus der DB (für Job-Prozessor).
    Gleiche Logik wie get_ocr_sight_settings, aber mit übergebener Session.
    """
    row = db.query(AppSetting).filter(AppSetting.key == OCR_SIGHT_KEY).first()
    if row and row.value_json:
        out = dict(_default_ocr_sight())
        out.update(row.value_json)
        return out
    return _default_ocr_sight()


def _default_content_analysis() -> dict[str, Any]:
    """Defaults für Content-Analyse (Review-Quote)."""
    return {"review_threshold_pct": 100}


def get_content_analysis_settings(db: Session) -> dict[str, Any]:
    """
    Liest Content-Analyse-Einstellungen (für Job-Prozessor / Worker).
    review_threshold_pct: 0-100, Anteil bestätigter BBoxen pro Seite für automatische Erkennung.
    """
    row = db.query(AppSetting).filter(AppSetting.key == CONTENT_ANALYSIS_KEY).first()
    if row and row.value_json:
        out = dict(_default_content_analysis())
        out.update(row.value_json)
        return out
    return _default_content_analysis()


class ContentAnalysisSettingsBody(BaseModel):
    """Request-Body für PUT /api/settings/content-analysis."""

    review_threshold_pct: float = Field(
        default=100,
        ge=0,
        le=100,
        description="Review-Quote (%): Seiten mit mindestens so viel bestätigten BBoxen fließen in die automatische Erkennung ein (0-100).",
    )


@router.get("/content-analysis")
def get_content_analysis_settings_endpoint(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Liest die Einstellungen für Content-Analyse (Review-Quote)."""
    return get_content_analysis_settings(db)


@router.put("/content-analysis")
def put_content_analysis_settings(
    body: ContentAnalysisSettingsBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Speichert die Einstellungen für Content-Analyse."""
    row = db.query(AppSetting).filter(AppSetting.key == CONTENT_ANALYSIS_KEY).first()
    payload = body.model_dump()
    if row:
        row.value_json = payload
        db.commit()
    else:
        row = AppSetting(key=CONTENT_ANALYSIS_KEY, value_json=payload)
        db.add(row)
        db.commit()
    out = dict(_default_content_analysis())
    out.update(payload)
    return out


@router.put("/ocr-sight")
def put_ocr_sight_settings(
    body: OcrSightSettingsBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Speichert die Einstellungen für OCR-Sichtung.
    """
    row = db.query(AppSetting).filter(AppSetting.key == OCR_SIGHT_KEY).first()
    payload = body.model_dump()
    if row:
        row.value_json = payload
        db.commit()
    else:
        row = AppSetting(key=OCR_SIGHT_KEY, value_json=payload)
        db.add(row)
        db.commit()
    out = dict(_default_ocr_sight())
    out.update(payload)
    return out


class MergeFromUnitsBody(BaseModel):
    """Request-Body für POST /api/settings/ocr-sight/merge-from-units."""

    document_id: int = Field(
        description="Dokument-ID; alle document_units werden ausgelesen"
    )


def _parse_lines(s: str) -> list[str]:
    """Zeilen- und Komma-getrennte Einträge, bereinigt und ohne Leerzeilen."""
    if not s or not s.strip():
        return []
    parts = []
    for line in s.replace(",", "\n").split("\n"):
        t = line.strip()
        if t:
            parts.append(t)
    return parts


def _to_phrases_string(items: list[str]) -> str:
    """Eine Formulierung pro Zeile."""
    return "\n".join(sorted(set(items)))


def _to_names_string(items: list[str]) -> str:
    """Komma-getrennte Namen."""
    return ", ".join(sorted(set(items)))


@router.post("/ocr-sight/merge-from-units")
def merge_ocr_sight_from_units(
    body: MergeFromUnitsBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Übernimmt extracted_phrases und extracted_names aus den document_units eines
    Dokuments in die OCR-Sicht-Einstellungen (typical_phrases, expected_names).
    Bestehende Einträge werden um die neuen ergänzt, Duplikate entfernt.
    """
    doc = db.query(Document).filter(Document.id == body.document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokument nicht gefunden",
        )
    units = (
        db.query(DocumentUnit)
        .filter(DocumentUnit.document_id == body.document_id)
        .all()
    )
    all_phrases: list[str] = []
    all_names: list[str] = []
    for u in units:
        if u.extracted_phrases:
            for p in u.extracted_phrases:
                if isinstance(p, str) and p.strip():
                    all_phrases.append(p.strip())
        if u.extracted_names:
            for n in u.extracted_names:
                if isinstance(n, str) and n.strip():
                    all_names.append(n.strip())

    row = db.query(AppSetting).filter(AppSetting.key == OCR_SIGHT_KEY).first()
    current = dict(_default_ocr_sight())
    if row and row.value_json:
        current.update(row.value_json)

    existing_phrases = _parse_lines(current.get("typical_phrases") or "")
    existing_names = _parse_lines(
        (current.get("expected_names") or "").replace(",", "\n")
    )
    merged_phrases = _to_phrases_string(existing_phrases + all_phrases)
    merged_names = _to_names_string(existing_names + all_names)

    current["typical_phrases"] = merged_phrases
    current["expected_names"] = merged_names

    if row:
        row.value_json = current
        db.commit()
    else:
        row = AppSetting(key=OCR_SIGHT_KEY, value_json=current)
        db.add(row)
        db.commit()

    return {
        "merged": True,
        "units_count": len(units),
        "phrases_added": len(all_phrases),
        "names_added": len(all_names),
        "typical_phrases": merged_phrases,
        "expected_names": merged_names,
    }
