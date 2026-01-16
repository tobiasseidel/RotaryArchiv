"""
API Endpoints für Triples
"""

from fastapi import APIRouter, status

from src.rotary_archiv.api.schemas import TripleCreate, TripleResponse
from src.rotary_archiv.core.triplestore import ROTARY, get_triplestore

router = APIRouter(prefix="/api/triples", tags=["triples"])


@router.post("/", response_model=TripleResponse, status_code=status.HTTP_201_CREATED)
def create_triple(triple: TripleCreate):
    """
    Erstelle neues Triple
    """
    triplestore = get_triplestore()

    # Erstelle vollständige URIs
    subject_uri = (
        f"{ROTARY}{triple.subject}"
        if not triple.subject.startswith("http")
        else triple.subject
    )
    predicate_uri = (
        f"{ROTARY}{triple.predicate}"
        if not triple.predicate.startswith("http")
        else triple.predicate
    )

    triplestore.add_triple(
        subject_uri, predicate_uri, triple.object_value, triple.object_type
    )

    return TripleResponse(
        subject=subject_uri,
        predicate=predicate_uri,
        object_value=triple.object_value,
        object_type=triple.object_type,
    )


@router.get("/", response_model=list[TripleResponse])
def list_triples(
    subject: str | None = None, predicate: str | None = None, limit: int = 100
):
    """
    Liste Triples (mit optionalen Filtern)
    """
    triplestore = get_triplestore()

    # Baue SPARQL Query
    query = f"""
    PREFIX rotary: <{ROTARY}>
    SELECT ?subject ?predicate ?object WHERE {{
        ?subject ?predicate ?object .
        {"FILTER(?subject = rotary:" + subject + ")" if subject else ""}
        {"FILTER(?predicate = rotary:" + predicate + ")" if predicate else ""}
    }}
    LIMIT {limit}
    """

    results = triplestore.query(query)

    triples = []
    for result in results:
        triples.append(
            TripleResponse(
                subject=result.get("subject", ""),
                predicate=result.get("predicate", ""),
                object_value=result.get("object", ""),
                object_type="uri"
                if result.get("object", "").startswith("http")
                else "literal",
            )
        )

    return triples


@router.get("/document/{document_id}")
def get_document_triples(document_id: int):
    """
    Hole alle Triples für ein Dokument
    """
    triplestore = get_triplestore()
    return triplestore.get_document_entities(document_id)


@router.get("/entity/{entity_id}")
def get_entity_triples(entity_id: int):
    """
    Hole alle Triples für eine Entität
    """
    triplestore = get_triplestore()
    return triplestore.get_entity_documents(entity_id)
