"""
API für Erschließungs-Boxen: Box auf der Seite ↔ Triple Store.
CRUD für ErschliessungsBox; entity-suggestions, wikidata-matches, wikidata-preview, assign, beleg.
"""

import json
from pathlib import Path
import re
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.rotary_archiv.content.entities import EntityType
from src.rotary_archiv.content.wikidata_sync import (
    extract_all_claim_values,
    extract_image_claims,
    extract_syncable_claim_values,
    get_property_label,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import DocumentPage, ErschliessungsBox
from src.rotary_archiv.core.triplestore import ROTARY, get_triplestore
from src.rotary_archiv.wikidata.matcher import WikidataMatcher

router = APIRouter(prefix="/{page_id}/erschliessung", tags=["erschliessung"])

# #region agent log
DEBUG_LOG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "debug-983982.log"
)


def _debug_log(location: str, message: str, data: dict, hypothesis_id: str) -> None:
    try:
        payload = {
            "sessionId": "983982",
            "location": location,
            "message": message,
            "data": data,
            "hypothesisId": hypothesis_id,
            "timestamp": __import__("time").time() * 1000,
        }
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


# #endregion


# --- Schemas ---


class ErschliessungsBoxCreate(BaseModel):
    """Body zum Anlegen einer Erschließungs-Box."""

    bbox: list[float] = Field(..., min_length=4, max_length=4)
    box_type: str = Field(..., pattern="^(entity|beleg)$")
    entity_type: str | None = Field(None, pattern="^(person|place|event)$")
    name: str | None = None


class ErschliessungsBoxUpdate(BaseModel):
    """Body zum Aktualisieren (partiell)."""

    bbox: list[float] | None = Field(None, min_length=4, max_length=4)
    name: str | None = None
    entity_uri: str | None = None
    subject_uri: str | None = None
    predicate_uri: str | None = None
    object_uri: str | None = None


class ErschliessungsBoxResponse(BaseModel):
    """Response für eine Erschließungs-Box."""

    id: int
    document_page_id: int
    bbox: list[float]
    box_type: str
    entity_type: str | None
    entity_uri: str | None
    name: str | None
    subject_uri: str | None
    predicate_uri: str | None
    object_uri: str | None
    main_image_url: str | None = None

    class Config:
        from_attributes = True


class AssignBody(BaseModel):
    """Body für Zuordnung einer Entity-Box: entity_uri (intern), wikidata_id, oder name (nur intern). Optional claim_values bei wikidata_id."""

    entity_uri: str | None = None
    wikidata_id: str | None = None
    name: str | None = None  # bei "nur intern": Person mit diesem Namen anlegen
    claim_values: dict[
        str, Any
    ] | None = (
        None  # bei wikidata_id: vom Nutzer ausgewählte Properties (z. B. P569, P570)
    )


class BelegBody(BaseModel):
    """Body für Beleg-Box: Aussage (Subjekt, Prädikat, Objekt)."""

    subject_uri: str
    predicate_uri: str
    object_uri: str


class PlaceCoordinatesBody(BaseModel):
    """Body für „Ort auf Karte setzen“: Koordinaten des Orts."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PlaceLinkBody(BaseModel):
    """Body für inhaltliche Ort-Anbindung: Objekt --Eigenschaft--> Ort."""

    subject_uri: str
    property_id: str = Field(..., pattern=r"^P\d+$")


PLACE_LINK_OPTIONS: list[dict[str, Any]] = [
    {"property_id": "P551", "label": "Wohnort", "target_entity_type": "person"},
    {"property_id": "P937", "label": "Arbeitsort", "target_entity_type": "person"},
    {
        "property_id": "P276",
        "label": "Veranstaltungsort",
        "target_entity_type": "event",
    },
]


def _get_page_or_404(db: Session, page_id: int) -> DocumentPage:
    page = db.query(DocumentPage).filter(DocumentPage.id == page_id).first()
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Seite {page_id} nicht gefunden",
        )
    return page


def _get_box_or_404(db: Session, page_id: int, box_id: int) -> ErschliessungsBox:
    _get_page_or_404(db, page_id)
    box = (
        db.query(ErschliessungsBox)
        .filter(
            ErschliessungsBox.id == box_id,
            ErschliessungsBox.document_page_id == page_id,
        )
        .first()
    )
    if not box:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Erschließungs-Box {box_id} auf Seite {page_id} nicht gefunden",
        )
    return box


# --- CRUD ---


@router.post(
    "/boxes",
    response_model=ErschliessungsBoxResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_erschliessungs_box(
    page_id: int,
    body: ErschliessungsBoxCreate,
    db: Session = Depends(get_db),
):
    """Erschließungs-Box auf der Seite anlegen (entity oder beleg)."""
    page = _get_page_or_404(db, page_id)
    box = ErschliessungsBox(
        document_page_id=page.id,
        bbox=body.bbox,
        box_type=body.box_type,
        entity_type=body.entity_type if body.box_type == "entity" else None,
        name=body.name,
    )
    db.add(box)
    db.commit()
    db.refresh(box)
    return box


@router.get("/boxes", response_model=list[ErschliessungsBoxResponse])
def list_erschliessungs_boxes(
    page_id: int,
    db: Session = Depends(get_db),
):
    """Alle Erschließungs-Boxen einer Seite liefern."""
    _get_page_or_404(db, page_id)
    boxes = (
        db.query(ErschliessungsBox)
        .filter(ErschliessungsBox.document_page_id == page_id)
        .order_by(ErschliessungsBox.id)
        .all()
    )
    # #region agent log
    for b in boxes:
        _debug_log(
            "erschliessung.py:list_boxes",
            "box returned",
            {
                "box_id": b.id,
                "entity_uri": getattr(b, "entity_uri", None),
                "name": getattr(b, "name", None),
            },
            "H3",
        )
    # #endregion
    ts = get_triplestore()
    result = []
    for b in boxes:
        data = {
            "id": b.id,
            "document_page_id": b.document_page_id,
            "bbox": b.bbox,
            "box_type": b.box_type,
            "entity_type": b.entity_type,
            "entity_uri": b.entity_uri,
            "name": b.name,
            "subject_uri": b.subject_uri,
            "predicate_uri": b.predicate_uri,
            "object_uri": b.object_uri,
        }
        data["main_image_url"] = (
            (ts.get_person_details(b.entity_uri) or {}).get("main_image_url")
            if b.entity_uri
            else None
        )
        result.append(ErschliessungsBoxResponse(**data))
    return result


@router.get("/boxes/{box_id}", response_model=ErschliessungsBoxResponse)
def get_erschliessungs_box(
    page_id: int,
    box_id: int,
    db: Session = Depends(get_db),
):
    """Eine Erschließungs-Box abrufen."""
    box = _get_box_or_404(db, page_id, box_id)
    return box


@router.patch(
    "/boxes/{box_id}",
    response_model=ErschliessungsBoxResponse,
)
def update_erschliessungs_box(
    page_id: int,
    box_id: int,
    body: ErschliessungsBoxUpdate,
    db: Session = Depends(get_db),
):
    """Erschließungs-Box aktualisieren (partiell)."""
    box = _get_box_or_404(db, page_id, box_id)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(box, key, value)
    db.commit()
    db.refresh(box)
    return box


@router.delete("/boxes/{box_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_erschliessungs_box(
    page_id: int,
    box_id: int,
    db: Session = Depends(get_db),
):
    """Erschließungs-Box löschen."""
    box = _get_box_or_404(db, page_id, box_id)
    db.delete(box)
    db.commit()
    return None


# --- Vorschläge und Zuordnung ---


@router.get("/entity-suggestions")
def get_entity_suggestions(
    page_id: int,
    name: str = Query(..., min_length=1),
    entity_type: str = Query("person", pattern="^(person|place|event)$"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top-N Vorschläge aus dem internen Triple Store (für Erschließungs-Box Typ entity)."""
    _get_page_or_404(db, page_id)
    ts = get_triplestore()
    results = ts.search_entities(name=name, entity_type=entity_type, limit=limit)
    return {"suggestions": results}


@router.get("/boxes/{box_id}/place-link-options")
def get_place_link_options(
    page_id: int,
    box_id: int,
    db: Session = Depends(get_db),
):
    """Optionen für Property-Dropdown im Ort-Dialog."""
    box = _get_box_or_404(db, page_id, box_id)
    if box.box_type != "entity" or (box.entity_type or "").strip().lower() != "place":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur Ort-Boxen unterstützen inhaltliche Anbindungen",
        )
    return {"options": PLACE_LINK_OPTIONS}


@router.get("/entity-preview")
def get_entity_preview(
    page_id: int,
    entity_uri: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Vorschau einer internen Entität (Name, Typ, Wikidata, Bild, Claims)."""
    _get_page_or_404(db, page_id)
    ts = get_triplestore()
    preview = ts.get_entity_preview(entity_uri)
    if not preview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Objekt nicht gefunden"
        )
    return preview


@router.get("/boxes/{box_id}/place-link")
def get_place_link(
    page_id: int,
    box_id: int,
    db: Session = Depends(get_db),
):
    """
    Bestehende inhaltliche Ort-Anbindung dieser Box (falls vorhanden).
    Statement-Pattern: subject --wdt:Pxxx--> place, belegtIn = ErschliessungsBox.
    """
    box = _get_box_or_404(db, page_id, box_id)
    if (
        box.box_type != "entity"
        or (box.entity_type or "").strip().lower() != "place"
        or not box.entity_uri
    ):
        return {"link": None}
    box_uri = str(ROTARY[f"ErschliessungsBox_{box.id}"])
    ts = get_triplestore()
    stmt = ts.get_statement_by_beleg(box_uri)
    if not stmt:
        return {"link": None}
    pred_uri = stmt.get("predicate_uri") or ""
    prop_id = (
        pred_uri.split("/prop/direct/")[-1] if "/prop/direct/" in pred_uri else None
    )
    subject_preview = ts.get_entity_preview(stmt.get("subject_uri") or "")
    return {
        "link": {
            "statement_uri": stmt.get("statement_uri"),
            "subject_uri": stmt.get("subject_uri"),
            "property_id": prop_id,
            "predicate_uri": pred_uri,
            "place_uri": stmt.get("object_uri"),
            "subject_preview": subject_preview,
            "source": {"page_id": page_id, "box_id": box_id},
        }
    }


@router.post("/boxes/{box_id}/place-link")
def save_place_link(
    page_id: int,
    box_id: int,
    body: PlaceLinkBody,
    db: Session = Depends(get_db),
):
    """Ort-Relation speichern: subject --wdt:Pxxx--> place inkl. Box/Seite als Beleg."""
    box = _get_box_or_404(db, page_id, box_id)
    if (
        box.box_type != "entity"
        or (box.entity_type or "").strip().lower() != "place"
        or not box.entity_uri
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur verknüpfte Ort-Boxen unterstützen place-link",
        )
    selected = next(
        (o for o in PLACE_LINK_OPTIONS if o["property_id"] == body.property_id), None
    )
    if not selected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unbekannte Eigenschaft"
        )
    if selected["target_entity_type"] == "person" and "Person_" not in body.subject_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Für diese Eigenschaft ist ein Person-Objekt erforderlich",
        )
    if selected["target_entity_type"] == "event" and "Event_" not in body.subject_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Für diese Eigenschaft ist ein Event-Objekt erforderlich",
        )

    ts = get_triplestore()
    pred_uri = f"http://www.wikidata.org/prop/direct/{body.property_id}"
    box_uri = str(ROTARY[f"ErschliessungsBox_{box.id}"])
    page_uri = str(ROTARY[f"DocumentPage_{page_id}"])
    ts.remove_statements_by_beleg(box_uri)
    stmt_uri = str(ROTARY[f"Statement_{uuid.uuid4().hex}"])
    ts.add_statement_with_beleg(
        stmt_uri,
        body.subject_uri,
        pred_uri,
        box.entity_uri,
        box_uri,
        page_uri=page_uri,
    )
    return {
        "ok": True,
        "statement_uri": stmt_uri,
        "subject_uri": body.subject_uri,
        "property_id": body.property_id,
        "place_uri": box.entity_uri,
        "source": {"page_id": page_id, "box_id": box_id},
    }


@router.delete("/boxes/{box_id}/place-link")
def delete_place_link(
    page_id: int,
    box_id: int,
    db: Session = Depends(get_db),
):
    """Ort-Relation an dieser Box löschen (Statement(s) über belegtIn der Box entfernen)."""
    box = _get_box_or_404(db, page_id, box_id)
    if box.box_type != "entity" or (box.entity_type or "").strip().lower() != "place":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur Ort-Boxen unterstützen place-link",
        )
    ts = get_triplestore()
    box_uri = str(ROTARY[f"ErschliessungsBox_{box.id}"])
    removed_count = ts.remove_statements_by_beleg(box_uri)
    return {
        "ok": True,
        "removed_count": removed_count,
        "source": {"page_id": page_id, "box_id": box_id},
    }


@router.get("/wikidata-matches")
def get_wikidata_matches(
    page_id: int,
    name: str = Query(..., min_length=1),
    entity_type: str = Query("person", pattern="^(person|place)$"),
    db: Session = Depends(get_db),
):
    """Top-5 Wikidata-Treffer zum Übernehmen (für Erschließungs-Box Typ entity)."""
    _get_page_or_404(db, page_id)
    et = EntityType.PERSON if entity_type == "person" else EntityType.PLACE
    matcher = WikidataMatcher()
    matches = matcher.find_matches(name, et)
    return {"matches": matches[:5]}


@router.get("/wikidata-preview")
def get_wikidata_preview(
    page_id: int,
    wikidata_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Wikidata-Entität für Import-Dialog: Objekt-Infos + vorgeschlagene Eigenschaften (suggested_claims)."""
    _get_page_or_404(db, page_id)
    matcher = WikidataMatcher()
    entity_data = matcher.get_entity_details(wikidata_id)
    if not entity_data or "error" in entity_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wikidata-Entität {wikidata_id} nicht gefunden",
        )
    suggested_claims: dict[str, Any] = extract_syncable_claim_values(
        entity_data.get("claims") or {}
    )
    return {
        "entity": {
            "id": entity_data.get("id"),
            "label": entity_data.get("label"),
            "description": entity_data.get("description"),
            "url": entity_data.get("url"),
        },
        "suggested_claims": suggested_claims,
    }


@router.get("/wikidata-sync-preview")
def get_wikidata_sync_preview(
    page_id: int,
    wikidata_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Wikidata-Entität für Sync-Dialog: entity + alle Properties (mit Label) + verknüpfte Bilder."""
    _get_page_or_404(db, page_id)
    matcher = WikidataMatcher()
    entity_data = matcher.get_entity_details(wikidata_id)
    if not entity_data or "error" in entity_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wikidata-Entität {wikidata_id} nicht gefunden",
        )
    claims = entity_data.get("claims") or {}
    all_props = extract_all_claim_values(claims)
    # IDs für Label-Abruf: alle Property-IDs + alle Werte die Q-IDs sind
    id_for_labels = list(dict.fromkeys(p["prop_id"] for p in all_props))
    for p in all_props:
        v = p.get("value")
        if isinstance(v, str) and re.match(r"^Q\d+$", v.strip()):
            id_for_labels.append(v.strip())
    labels_map: dict[str, str] = {}
    if id_for_labels:
        labels_map = matcher.client.get_labels(id_for_labels, language="de")
    properties = []
    for p in all_props:
        prop_id = p["prop_id"]
        value = p.get("value")
        value_str = str(value) if value is not None else ""
        is_entity = isinstance(value, str) and bool(
            re.match(r"^Q\d+$", value_str.strip())
        )
        prop_label = labels_map.get(prop_id) or get_property_label(prop_id)
        value_label = labels_map.get(value_str.strip()) if is_entity else None
        value_type = "entity" if is_entity else "literal"
        value_url = f"https://www.wikidata.org/wiki/{value_str}" if is_entity else None
        properties.append(
            {
                "prop_id": prop_id,
                "label": prop_label,
                "value": value_str,
                "datatype": p.get("datatype", ""),
                "value_type": value_type,
                "value_label": value_label,
                "value_url": value_url,
            }
        )
    images = extract_image_claims(claims)
    return {
        "entity": {
            "id": entity_data.get("id"),
            "label": entity_data.get("label"),
            "description": entity_data.get("description"),
            "url": entity_data.get("url"),
        },
        "properties": properties,
        "images": images,
    }


@router.get("/boxes/{box_id}/entity-details")
def get_box_entity_details(
    page_id: int,
    box_id: int,
    db: Session = Depends(get_db),
):
    """Interne Entity-Daten der verknüpften Person oder Ort für Edit-Dialog und Tooltip."""
    box = _get_box_or_404(db, page_id, box_id)
    if box.box_type != "entity" or not box.entity_uri:
        return {
            "entity_type": None,
            "entity_uri": None,
            "name": None,
            "wikidata_id": None,
            "claim_values": {},
            "claim_value_labels": {},
            "property_labels": {},
            "main_image_url": None,
            "lat": None,
            "lon": None,
        }
    ts = get_triplestore()
    if "Place_" in box.entity_uri:
        details = ts.get_place_details(box.entity_uri)
        if not details:
            return {
                "entity_type": "place",
                "entity_uri": box.entity_uri,
                "name": box.name,
                "wikidata_id": None,
                "main_image_url": None,
                "lat": None,
                "lon": None,
            }
        return {
            "entity_type": "place",
            "entity_uri": box.entity_uri,
            "name": details.get("name") or box.name,
            "wikidata_id": details.get("wikidata_id"),
            "claim_values": {},
            "claim_value_labels": {},
            "property_labels": {},
            "main_image_url": details.get("main_image_url"),
            "lat": details.get("lat"),
            "lon": details.get("lon"),
        }
    if "Event_" in box.entity_uri:
        preview = ts.get_entity_preview(box.entity_uri) or {}
        return {
            "entity_type": "event",
            "entity_uri": box.entity_uri,
            "name": preview.get("name") or box.name,
            "wikidata_id": preview.get("wikidata_id"),
            "claim_values": preview.get("claim_values") or {},
            "claim_value_labels": {},
            "property_labels": {},
            "main_image_url": preview.get("main_image_url"),
            "lat": None,
            "lon": None,
        }
    details = ts.get_person_details(box.entity_uri)
    if not details:
        return {
            "entity_type": "person",
            "entity_uri": box.entity_uri,
            "name": box.name,
            "wikidata_id": None,
            "claim_values": {},
            "claim_value_labels": {},
            "property_labels": {},
            "main_image_url": None,
        }
    claim_values = details.get("claim_values") or {}
    claim_value_labels = details.get("claim_value_labels") or {}
    prop_ids = list(claim_values.keys())
    property_labels: dict[str, str] = {}
    if prop_ids:
        matcher = WikidataMatcher()
        property_labels = matcher.client.get_labels(prop_ids, language="de")
    return {
        "entity_type": "person",
        "entity_uri": box.entity_uri,
        "name": details.get("name") or box.name,
        "wikidata_id": details.get("wikidata_id"),
        "claim_values": claim_values,
        "claim_value_labels": claim_value_labels,
        "property_labels": property_labels,
        "main_image_url": details.get("main_image_url"),
    }


class UpdateEntityDetailsBody(BaseModel):
    """Body zum Aktualisieren der internen Entity-Daten (Name, Properties als Listen, Anzeigenamen pro Wert, optional Hauptbild)."""

    name: str
    claim_values: dict[str, list[str]] | None = None
    claim_value_labels: dict[str, dict[str, str]] | None = None
    main_image_url: str | None = None


@router.patch("/boxes/{box_id}/entity-details")
def update_box_entity_details(
    page_id: int,
    box_id: int,
    body: UpdateEntityDetailsBody,
    db: Session = Depends(get_db),
):
    """Interne Entity-Daten der verknüpften Person oder Ort aktualisieren."""
    box = _get_box_or_404(db, page_id, box_id)
    if box.box_type != "entity" or not box.entity_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur verknüpfte Entity-Boxen können bearbeitet werden",
        )
    ts = get_triplestore()
    if "Place_" in box.entity_uri:
        ts.update_place(box.entity_uri, body.name.strip())
    else:
        ts.update_person(
            box.entity_uri,
            body.name.strip(),
            claim_values=body.claim_values or None,
            claim_value_labels=body.claim_value_labels or None,
            main_image_url=body.main_image_url,
            update_main_image=body.main_image_url is not None,
        )
    box.name = body.name.strip()
    db.commit()
    db.refresh(box)
    return {"ok": True, "box": box}


class SyncClaimItem(BaseModel):
    """Eine ausgewählte (Property, Wert)-Kombination für den Sync."""

    prop_id: str
    value: str


class SyncFromWikidataBody(BaseModel):
    """Body für Sync: Wikidata-Daten in verknüpfte Person übernehmen."""

    wikidata_id: str
    selected_property_ids: list[str] | None = None
    selected_claims: list[SyncClaimItem] | None = None


@router.post(
    "/boxes/{box_id}/sync-from-wikidata",
    response_model=ErschliessungsBoxResponse,
)
def sync_box_entity_from_wikidata(
    page_id: int,
    box_id: int,
    body: SyncFromWikidataBody,
    db: Session = Depends(get_db),
):
    """Verknüpfte Entity-Box: Person aus Wikidata laden und im internen Store aktualisieren."""
    box = _get_box_or_404(db, page_id, box_id)
    if box.box_type != "entity" or not box.entity_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur verknüpfte Entity-Boxen können synchronisiert werden",
        )
    matcher = WikidataMatcher()
    entity_data = matcher.get_entity_details(body.wikidata_id)
    if not entity_data or "error" in entity_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wikidata-Entität {body.wikidata_id} nicht gefunden",
        )
    label = entity_data.get("label") or box.name or body.wikidata_id
    claims = entity_data.get("claims") or {}
    all_props = extract_all_claim_values(claims)
    claim_values: dict[str, list[str]] = {}
    if body.selected_claims and len(body.selected_claims) > 0:
        for item in body.selected_claims:
            if item.prop_id and item.value is not None:
                claim_values.setdefault(item.prop_id, []).append(
                    str(item.value).strip()
                )
    elif body.selected_property_ids and len(body.selected_property_ids) > 0:
        for p in all_props:
            if p["prop_id"] in body.selected_property_ids:
                claim_values.setdefault(p["prop_id"], []).append(str(p["value"]))
    else:
        syncable = extract_syncable_claim_values(claims)
        for prop_id, val in syncable.items():
            if val is not None and str(val).strip():
                claim_values.setdefault(prop_id, []).append(str(val).strip())
    # Anzeigenamen für Objekt-Werte (Q-IDs) von Wikidata holen
    claim_value_labels: dict[str, dict[str, str]] = {}
    if claim_values:
        q_ids = [
            v.strip()
            for vals in claim_values.values()
            for v in (vals if isinstance(vals, list) else [vals])
            if isinstance(v, str) and re.match(r"^Q\d+$", v.strip())
        ]
        if q_ids:
            labels_map = matcher.client.get_labels(q_ids, language="de")
            for prop_id, vals in claim_values.items():
                for v in vals if isinstance(vals, list) else [vals]:
                    if isinstance(v, str) and v.strip() in labels_map:
                        claim_value_labels.setdefault(prop_id, {})[
                            v.strip()
                        ] = labels_map[v.strip()]
    ts = get_triplestore()
    ts.update_person(
        box.entity_uri,
        label,
        wikidata_id=body.wikidata_id,
        claim_values=claim_values or None,
        claim_value_labels=claim_value_labels or None,
    )
    if box.name != label:
        box.name = label
        db.commit()
        db.refresh(box)
    return box


@router.post(
    "/boxes/{box_id}/assign",
    response_model=ErschliessungsBoxResponse,
)
def assign_entity_to_box(
    page_id: int,
    box_id: int,
    body: AssignBody,
    db: Session = Depends(get_db),
):
    """
    Entity-Box zuordnen: entweder entity_uri (aus internem Store) oder wikidata_id.
    Bei wikidata_id: Person mit Wikidata-Daten im Store anlegen, dann Box verknüpfen.
    """
    # #region agent log
    _debug_log(
        "erschliessung.py:assign_entity_to_box",
        "assign called",
        {
            "page_id": page_id,
            "box_id": box_id,
            "body_entity_uri": getattr(body, "entity_uri", None),
            "body_wikidata_id": getattr(body, "wikidata_id", None),
            "body_name": getattr(body, "name", None),
        },
        "H1",
    )
    # #endregion
    box = _get_box_or_404(db, page_id, box_id)
    if box.box_type != "entity":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur Entity-Boxen können zugeordnet werden",
        )
    if body.entity_uri and body.wikidata_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur entity_uri oder wikidata_id angeben, nicht beides",
        )
    has_choice = bool(
        body.entity_uri or body.wikidata_id or (body.name and body.name.strip())
    )
    if not has_choice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_uri, wikidata_id oder name (nur intern) erforderlich",
        )

    ts = get_triplestore()
    box_uri = str(ROTARY[f"ErschliessungsBox_{box.id}"])
    entity_type = (box.entity_type or "").strip().lower()
    is_place = entity_type == "place"
    is_event = entity_type == "event"

    if is_place:
        # Ort (Place) zuordnen
        if body.entity_uri:
            entity_uri = body.entity_uri
            if "Place_" not in entity_uri and "/Place_" not in entity_uri:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="entity_uri muss eine Place-URI sein",
                )
        elif body.name and body.name.strip() and not body.wikidata_id:
            name = body.name.strip()
            entity_uri = ts.get_place_uri_by_name(name)
            if not entity_uri:
                entity_uri = str(ROTARY[f"Place_{uuid.uuid4().hex}"])
                ts.add_place(entity_uri, name)
        elif body.wikidata_id:
            from src.rotary_archiv.content.wikidata_sync import (
                extract_place_coordinates,
                extract_place_image_url,
            )

            matcher = WikidataMatcher()
            entity_data = matcher.get_entity_details(body.wikidata_id)
            if not entity_data or "error" in entity_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Wikidata-Entität {body.wikidata_id} nicht gefunden",
                )
            label = entity_data.get("label") or box.name or body.wikidata_id
            claims = entity_data.get("claims") or {}
            main_image_url = extract_place_image_url(claims)
            lat, lon = extract_place_coordinates(claims)
            entity_uri = str(ROTARY[f"Place_{uuid.uuid4().hex}"])
            ts.add_place(
                entity_uri,
                label,
                wikidata_id=body.wikidata_id,
                main_image_url=main_image_url,
                lat=lat,
                lon=lon,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entity_uri, wikidata_id oder name erforderlich",
            )
    elif is_event:
        # Ereignis zuordnen (intern / optional Wikidata)
        if body.entity_uri:
            entity_uri = body.entity_uri
            if "Event_" not in entity_uri and "/Event_" not in entity_uri:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="entity_uri muss eine Event-URI sein",
                )
        elif body.name and body.name.strip() and not body.wikidata_id:
            name = body.name.strip()
            entity_uri = ts.get_event_uri_by_name(name)
            if not entity_uri:
                entity_uri = str(ROTARY[f"Event_{uuid.uuid4().hex}"])
                ts.add_event(entity_uri, name)
        elif body.wikidata_id:
            matcher = WikidataMatcher()
            entity_data = matcher.get_entity_details(body.wikidata_id)
            if not entity_data or "error" in entity_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Wikidata-Entität {body.wikidata_id} nicht gefunden",
                )
            label = entity_data.get("label") or box.name or body.wikidata_id
            entity_uri = str(ROTARY[f"Event_{uuid.uuid4().hex}"])
            ts.add_event(entity_uri, label, wikidata_id=body.wikidata_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entity_uri, wikidata_id oder name erforderlich",
            )
    else:
        # Person zuordnen
        if body.entity_uri:
            entity_uri = body.entity_uri
        elif body.name and body.name.strip() and not body.wikidata_id:
            name = body.name.strip()
            entity_uri = ts.get_person_uri_by_name(name)
            if not entity_uri:
                entity_uri = str(ROTARY[f"Person_{uuid.uuid4().hex}"])
                ts.add_person(entity_uri, name)
        elif body.wikidata_id:
            matcher = WikidataMatcher()
            entity_data = matcher.get_entity_details(body.wikidata_id)
            if not entity_data or "error" in entity_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Wikidata-Entität {body.wikidata_id} nicht gefunden",
                )
            label = entity_data.get("label") or box.name or body.wikidata_id
            if body.claim_values is not None:
                claim_values = body.claim_values
            else:
                claim_values = extract_syncable_claim_values(
                    entity_data.get("claims") or {}
                )
            entity_uri = str(ROTARY[f"Person_{uuid.uuid4().hex}"])
            ts.add_person(
                entity_uri,
                label,
                wikidata_id=body.wikidata_id,
                claim_values=claim_values or None,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entity_uri, wikidata_id oder name erforderlich",
            )

    mention_uri = str(ROTARY[f"Mention_{uuid.uuid4().hex}"])
    ts.add_mention(mention_uri, entity_uri, box_uri)

    box.entity_uri = entity_uri
    # #region agent log
    _debug_log(
        "erschliessung.py:assign_entity_to_box",
        "before commit",
        {"box_id": box.id, "entity_uri_set": box.entity_uri},
        "H1",
    )
    # #endregion
    db.commit()
    db.refresh(box)
    # #region agent log
    _debug_log(
        "erschliessung.py:assign_entity_to_box",
        "after commit",
        {"box_id": box.id, "entity_uri": box.entity_uri},
        "H1",
    )
    # #endregion
    return box


@router.patch(
    "/boxes/{box_id}/place-coordinates",
    response_model=ErschliessungsBoxResponse,
)
def set_place_coordinates(
    page_id: int,
    box_id: int,
    body: PlaceCoordinatesBody,
    db: Session = Depends(get_db),
):
    """
    Koordinaten eines Orts setzen (nach „Zur Karte“ und Marker setzen).
    Nur für Entity-Boxen mit entity_type=place und gesetzter entity_uri.
    """
    box = _get_box_or_404(db, page_id, box_id)
    if box.box_type != "entity" or (box.entity_type or "").strip().lower() != "place":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur Ort-Boxen können Koordinaten erhalten",
        )
    if not box.entity_uri or "Place_" not in box.entity_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Box ist keinem Ort zugeordnet",
        )
    ts = get_triplestore()
    details = ts.get_place_details(box.entity_uri)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ort im Triple Store nicht gefunden",
        )
    ts.update_place(
        box.entity_uri,
        details["name"] or "",
        lat=body.lat,
        lon=body.lon,
    )
    db.commit()
    db.refresh(box)
    return box


@router.get("/debug/triples")
def debug_list_all_triples(
    page_id: int,
    db: Session = Depends(get_db),
):
    """Alle Einträge aus dem Triple-Store auslesen (für Debug: Verknüpfung sichtbar?)."""
    _get_page_or_404(db, page_id)
    ts = get_triplestore()
    triples = ts.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
    return {
        "store": "memory" if not getattr(ts, "use_fuseki", False) else "fuseki",
        "count": len(triples),
        "triples": triples,
    }


@router.post(
    "/boxes/{box_id}/beleg",
    response_model=ErschliessungsBoxResponse,
)
def set_beleg_for_box(
    page_id: int,
    box_id: int,
    body: BelegBody,
    db: Session = Depends(get_db),
):
    """Beleg-Box: Aussage (Subjekt, Prädikat, Objekt) mit dieser Box als Quelle speichern."""
    box = _get_box_or_404(db, page_id, box_id)
    if box.box_type != "beleg":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur Beleg-Boxen können eine Aussage erhalten",
        )

    ts = get_triplestore()
    box_uri = str(ROTARY[f"ErschliessungsBox_{box.id}"])
    beleg_uri = str(ROTARY[f"Beleg_{uuid.uuid4().hex}"])
    ts.add_beleg(
        beleg_uri,
        box_uri,
        body.subject_uri,
        body.predicate_uri,
        body.object_uri,
    )

    box.subject_uri = body.subject_uri
    box.predicate_uri = body.predicate_uri
    box.object_uri = body.object_uri
    db.commit()
    db.refresh(box)
    return box
