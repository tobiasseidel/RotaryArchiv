"""
API Endpoints für Wikidata-Integration
"""

from fastapi import APIRouter, HTTPException, status

from src.rotary_archiv.api.schemas import WikidataMatchRequest, WikidataSearchRequest
from src.rotary_archiv.wikidata.client import WikidataClient
from src.rotary_archiv.wikidata.matcher import WikidataMatcher

router = APIRouter(prefix="/api/wikidata", tags=["wikidata"])


@router.post("/search")
def search_wikidata(request: WikidataSearchRequest):
    """
    Suche in Wikidata
    """
    client = WikidataClient()
    results = client.search_entity(request.query, limit=request.limit)
    return {"results": results}


@router.post("/match")
def match_entity(request: WikidataMatchRequest):
    """
    Finde Wikidata-Matches für eine Entität
    """
    matcher = WikidataMatcher()
    matches = matcher.find_matches(request.name, request.entity_type, request.context)
    return {"matches": matches}


@router.get("/entity/{wikidata_id}")
def get_wikidata_entity(wikidata_id: str):
    """
    Hole Wikidata-Entität Details
    """
    client = WikidataClient()
    entity = client.get_entity(wikidata_id)

    if not entity or "error" in entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wikidata-Entität nicht gefunden",
        )

    return entity


@router.get("/entity/{wikidata_id}/import")
def get_import_suggestions(wikidata_id: str):
    """
    Hole Import-Vorschläge für Wikidata-Entität
    """
    matcher = WikidataMatcher()
    suggestions = matcher.suggest_import_data(wikidata_id)
    return suggestions
