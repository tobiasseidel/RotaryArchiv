"""
SPARQL Endpoint

NOTE: Vorerst nicht verwendet - kann später wieder aktiviert werden
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.rotary_archiv.core.triplestore import get_triplestore

router = APIRouter(prefix="/sparql", tags=["sparql"])


class SPARQLQuery(BaseModel):
    """SPARQL Query Request"""

    query: str


@router.post("/")
def execute_sparql(query: SPARQLQuery):
    """
    Führe SPARQL Query aus
    """
    if not query.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SPARQL Query darf nicht leer sein",
        )

    try:
        triplestore = get_triplestore()
        results = triplestore.query(query.query)
        return {"results": results}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SPARQL Query Fehler: {e!s}",
        ) from e
