"""
API für übergreifende Erschließungs-Übersicht (Listen ohne page_id).
Endpoints: entities (Personen), pages (Seiten mit Boxen), boxes (alle Boxen).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import Document, DocumentPage, ErschliessungsBox
from src.rotary_archiv.core.triplestore import ROTARY, get_triplestore
from src.rotary_archiv.wikidata.matcher import WikidataMatcher

router = APIRouter(
    prefix="/api/erschliessung-overview", tags=["erschliessung-overview"]
)

RELATION_BY_PROPERTY = {
    "P551": "residence",
    "P937": "work",
    "P276": "event",
}


class PlaceCoordinatesBody(BaseModel):
    """Body für Koordinaten-Update eines Orts."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


def _person_uri_from_id(entity_id: str) -> str:
    """Aus lokalem Teil (z. B. Person_abc) die volle Person-URI bauen."""
    if not entity_id or not entity_id.strip():
        raise ValueError("entity_id leer")
    local = entity_id.strip()
    if local.startswith("http://") or local.startswith("https://"):
        return local
    return str(ROTARY[local])


@router.get("/entities")
def list_entities(
    document_id: int | None = Query(
        None, description="Nur Entities aus diesem Dokument"
    ),
    page_id: int | None = Query(None, description="Nur Entities auf dieser Seite"),
    db: Session = Depends(get_db),
):
    """
    Alle verknüpften Personen (distinct entity_uri) aus Erschließungs-Boxen.
    Optional gefiltert nach document_id und/oder page_id.
    """
    q = (
        db.query(
            ErschliessungsBox.entity_uri,
            ErschliessungsBox.document_page_id,
            ErschliessungsBox.name,
        )
        .filter(
            ErschliessungsBox.box_type == "entity",
            ErschliessungsBox.entity_uri.isnot(None),
        )
        .filter(ErschliessungsBox.entity_uri != "")
    )
    if page_id is not None:
        q = q.filter(ErschliessungsBox.document_page_id == page_id)
    elif document_id is not None:
        q = q.join(DocumentPage).filter(DocumentPage.document_id == document_id)
    rows = q.all()

    # Nur Person-URIs (Orte haben Place_ im URI und werden in /places gelistet)
    by_uri: dict[str, dict] = {}
    for entity_uri, doc_page_id, name in rows:
        if not entity_uri or "Person_" not in entity_uri:
            continue
        if entity_uri not in by_uri:
            by_uri[entity_uri] = {
                "entity_uri": entity_uri,
                "name": name,
                "page_ids": [],
            }
        by_uri[entity_uri]["page_ids"].append(doc_page_id)

    # Distinct page_ids
    for ent in by_uri.values():
        ent["page_ids"] = list(dict.fromkeys(ent["page_ids"]))

    ts = get_triplestore()
    result = []
    for uri, data in by_uri.items():
        details = ts.get_person_details(uri)
        if details:
            data["name"] = details.get("name") or data["name"]
            data["main_image_url"] = details.get("main_image_url")
        else:
            data["main_image_url"] = None
        # Lokaler Teil der URI für Detail-Link (z. B. Person_abc)
        data["entity_id"] = uri.split("/")[-1].split("#")[0] if uri else ""
        result.append(data)

    return {"entities": result}


@router.get("/entities/{entity_id}")
def get_entity_details(
    entity_id: str,
    db: Session = Depends(get_db),
):
    """
    Details einer Person oder eines Orts (für Aufklappen / Zur Karte).
    entity_id: lokaler Teil der URI (z. B. Person_abc oder Place_abc).
    Bei Person: claim_values, claim_value_labels, property_labels.
    Bei Place: lat, lon, main_image_url.
    """
    try:
        entity_uri = _person_uri_from_id(entity_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    ts = get_triplestore()
    if "Place_" in entity_uri:
        details = ts.get_place_details(entity_uri)
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ort nicht gefunden"
            )
        return {
            "entity_uri": entity_uri,
            "entity_type": "place",
            "name": details.get("name"),
            "wikidata_id": details.get("wikidata_id"),
            "main_image_url": details.get("main_image_url"),
            "lat": details.get("lat"),
            "lon": details.get("lon"),
        }
    details = ts.get_person_details(entity_uri)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person nicht gefunden"
        )

    claim_values = details.get("claim_values") or {}
    claim_value_labels = details.get("claim_value_labels") or {}
    prop_ids = list(claim_values.keys())
    property_labels: dict[str, str] = {}
    if prop_ids:
        matcher = WikidataMatcher()
        property_labels = matcher.client.get_labels(prop_ids, language="de")

    return {
        "entity_uri": entity_uri,
        "entity_type": "person",
        "name": details.get("name"),
        "wikidata_id": details.get("wikidata_id"),
        "claim_values": claim_values,
        "claim_value_labels": claim_value_labels,
        "property_labels": property_labels,
        "main_image_url": details.get("main_image_url"),
    }


@router.get("/pages")
def list_pages_with_boxes(
    document_id: int | None = Query(None, description="Nur Seiten dieses Dokuments"),
    db: Session = Depends(get_db),
):
    """Alle Seiten, die mindestens eine Erschließungs-Box haben. Optional Filter nach document_id."""
    q = (
        db.query(
            DocumentPage.id.label("page_id"),
            DocumentPage.document_id,
            DocumentPage.page_number,
            Document.title.label("document_title"),
            func.count(ErschliessungsBox.id).label("box_count"),
        )
        .join(ErschliessungsBox, ErschliessungsBox.document_page_id == DocumentPage.id)
        .join(Document, Document.id == DocumentPage.document_id)
        .group_by(
            DocumentPage.id,
            DocumentPage.document_id,
            DocumentPage.page_number,
            Document.title,
        )
    )
    if document_id is not None:
        q = q.filter(DocumentPage.document_id == document_id)
    rows = q.all()

    return {
        "pages": [
            {
                "page_id": r.page_id,
                "document_id": r.document_id,
                "page_number": r.page_number,
                "document_title": r.document_title or "",
                "box_count": r.box_count,
            }
            for r in rows
        ]
    }


@router.get("/boxes")
def list_boxes(
    document_id: int | None = Query(None, description="Nur Boxen aus diesem Dokument"),
    page_id: int | None = Query(None, description="Nur Boxen auf dieser Seite"),
    db: Session = Depends(get_db),
):
    """Alle Erschließungs-Boxen, optional gefiltert nach document_id und/oder page_id."""
    q = (
        db.query(
            ErschliessungsBox,
            DocumentPage.document_id,
            Document.title.label("document_title"),
        )
        .join(DocumentPage, DocumentPage.id == ErschliessungsBox.document_page_id)
        .join(Document, Document.id == DocumentPage.document_id)
    )
    if page_id is not None:
        q = q.filter(ErschliessungsBox.document_page_id == page_id)
    if document_id is not None:
        q = q.filter(DocumentPage.document_id == document_id)
    rows = q.all()

    ts = get_triplestore()
    result = []
    for box, doc_id, doc_title in rows:
        main_image_url = None
        if box.entity_uri:
            if "Place_" in box.entity_uri:
                details = ts.get_place_details(box.entity_uri)
            else:
                details = ts.get_person_details(box.entity_uri)
            if details:
                main_image_url = details.get("main_image_url")
        result.append(
            {
                "id": box.id,
                "page_id": box.document_page_id,
                "document_id": doc_id,
                "document_title": doc_title or "",
                "bbox": box.bbox,
                "box_type": box.box_type,
                "entity_uri": box.entity_uri,
                "name": box.name,
                "main_image_url": main_image_url,
            }
        )

    return {"boxes": result}


@router.get("/places")
def list_places(
    document_id: int | None = Query(None, description="Nur Orten aus diesem Dokument"),
    page_id: int | None = Query(None, description="Nur Orten auf dieser Seite"),
    db: Session = Depends(get_db),
):
    """
    Alle erschlossenen Orten mit Koordinaten (für Erschließungskarte).
    Nur Orten, die mindestens lat/lon im Triplestore haben.
    """
    q = (
        db.query(
            ErschliessungsBox.entity_uri,
            ErschliessungsBox.document_page_id,
            ErschliessungsBox.name,
        )
        .filter(ErschliessungsBox.box_type == "entity")
        .filter(ErschliessungsBox.entity_type == "place")
        .filter(ErschliessungsBox.entity_uri.isnot(None))
        .filter(ErschliessungsBox.entity_uri != "")
    )
    if page_id is not None:
        q = q.filter(ErschliessungsBox.document_page_id == page_id)
    elif document_id is not None:
        q = q.join(DocumentPage).filter(DocumentPage.document_id == document_id)
    rows = q.all()

    by_uri: dict[str, list[int]] = {}
    for entity_uri, doc_page_id, _name in rows:
        if "Place_" not in entity_uri:
            continue
        if entity_uri not in by_uri:
            by_uri[entity_uri] = []
        by_uri[entity_uri].append(doc_page_id)

    ts = get_triplestore()
    result = []
    for uri, page_ids in by_uri.items():
        details = ts.get_place_details(uri)
        if not details or details.get("lat") is None or details.get("lon") is None:
            continue
        stmt_rows = ts.list_statements_for_object(uri)
        relation_types: set[str] = set()
        linked_persons_by_uri: dict[str, dict] = {}
        for row in stmt_rows:
            subject_uri = row.get("subject") or ""
            predicate_uri = row.get("predicate") or ""
            prop_id = (
                predicate_uri.split("/prop/direct/")[-1]
                if "/prop/direct/" in predicate_uri
                else None
            )
            relation_type = RELATION_BY_PROPERTY.get(prop_id or "")
            if relation_type:
                relation_types.add(relation_type)
            if relation_type in {"residence", "work"} and "Person_" in subject_uri:
                p = linked_persons_by_uri.get(subject_uri)
                if not p:
                    person_details = ts.get_person_details(subject_uri) or {}
                    p = {
                        "entity_uri": subject_uri,
                        "name": person_details.get("name")
                        or subject_uri.split("/")[-1],
                        "main_image_url": person_details.get("main_image_url"),
                        "relation_types": [],
                    }
                    linked_persons_by_uri[subject_uri] = p
                if relation_type not in p["relation_types"]:
                    p["relation_types"].append(relation_type)
        place_id = uri.split("/")[-1].split("#")[0] if uri else ""
        result.append(
            {
                "place_uri": uri,
                "place_id": place_id,
                "name": details.get("name") or "",
                "lat": details["lat"],
                "lon": details["lon"],
                "main_image_url": details.get("main_image_url"),
                "page_ids": list(dict.fromkeys(page_ids)),
                "relation_types": sorted(relation_types),
                "linked_persons": list(linked_persons_by_uri.values()),
            }
        )
    return {"places": result}


@router.patch("/places/{place_id}")
def update_place_coordinates(
    place_id: str,
    body: PlaceCoordinatesBody,
):
    """
    Koordinaten eines Orts setzen (z. B. aus Erschließungskarte oder „Zur Karte“).
    place_id: lokaler Teil der URI (z. B. Place_abc).
    """
    try:
        place_uri = _person_uri_from_id(place_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    if "Place_" not in place_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Keine Place-URI"
        )
    ts = get_triplestore()
    details = ts.get_place_details(place_uri)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ort nicht gefunden"
        )
    ts.update_place(
        place_uri,
        details["name"] or "",
        lat=body.lat,
        lon=body.lon,
    )
    return {"place_uri": place_uri, "lat": body.lat, "lon": body.lon}
