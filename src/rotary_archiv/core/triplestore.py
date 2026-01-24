"""
Triple Store Interface für RDF-Relationen

NOTE: Vorerst nicht verwendet - kann später wieder aktiviert werden
"""

from typing import Any

import httpx
from rdflib import Graph, Literal, Namespace, URIRef

from src.rotary_archiv.config import settings

# Namespace für RotaryArchiv
ROTARY = Namespace("http://rotaryarchiv.local/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
SCHEMA = Namespace("http://schema.org/")


class TripleStore:
    """
    Interface für Triple Store (RDF)
    Unterstützt sowohl lokalen RDFLib Graph als auch Fuseki
    """

    def __init__(self, use_fuseki: bool = False):
        """
        Initialisiere Triple Store

        Args:
            use_fuseki: Wenn True, verwende Fuseki SPARQL Endpoint
        """
        self.use_fuseki = use_fuseki
        self.graph = Graph()

        # Bind Namespaces
        self.graph.bind("rotary", ROTARY)
        self.graph.bind("wikidata", WIKIDATA)
        self.graph.bind("schema", SCHEMA)

        if use_fuseki:
            self.fuseki_url = settings.fuseki_url
            self.sparql_endpoint = f"{self.fuseki_url}/sparql"
        else:
            self.sparql_endpoint = None

    def add_triple(
        self, subject: str, predicate: str, object_value: str, object_type: str = "uri"
    ) -> None:
        """
        Füge ein Triple hinzu

        Args:
            subject: Subjekt URI (z.B. "rotary:Document_123")
            predicate: Prädikat URI (z.B. "rotary:erwaehnt")
            object_value: Objekt (URI oder Literal)
            object_type: "uri" oder "literal"
        """
        subj = URIRef(subject)
        pred = URIRef(predicate)

        obj = URIRef(object_value) if object_type == "uri" else Literal(object_value)

        self.graph.add((subj, pred, obj))

        if self.use_fuseki:
            self._sync_to_fuseki()

    def add_triples(self, triples: list[dict[str, Any]]) -> None:
        """
        Füge mehrere Triples hinzu

        Args:
            triples: Liste von Triple-Dicts mit keys: subject, predicate, object, object_type
        """
        for triple in triples:
            self.add_triple(
                triple["subject"],
                triple["predicate"],
                triple["object"],
                triple.get("object_type", "uri"),
            )

    def query(self, sparql_query: str) -> list[dict[str, Any]]:
        """
        Führe SPARQL Query aus

        Args:
            sparql_query: SPARQL Query String

        Returns:
            Liste von Ergebnis-Dicts
        """
        if self.use_fuseki and self.sparql_endpoint:
            return self._query_fuseki(sparql_query)
        else:
            return self._query_local(sparql_query)

    def _query_local(self, sparql_query: str) -> list[dict[str, Any]]:
        """Führe Query auf lokalem Graph aus"""
        results = []
        for row in self.graph.query(sparql_query):
            result = {}
            for key, value in row.asdict().items():
                result[key] = str(value)
            results.append(result)
        return results

    def _query_fuseki(self, sparql_query: str) -> list[dict[str, Any]]:
        """Führe Query auf Fuseki aus"""
        try:
            response = httpx.post(
                self.sparql_endpoint,
                data={"query": sparql_query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            # Parse SPARQL JSON Results
            results = []
            if "results" in data and "bindings" in data["results"]:
                for binding in data["results"]["bindings"]:
                    result = {}
                    for key, value in binding.items():
                        result[key] = value.get("value", "")
                    results.append(result)
            return results
        except Exception as e:
            raise Exception(f"Fuseki Query fehlgeschlagen: {e}") from e

    def _sync_to_fuseki(self) -> None:
        """Synchronisiere lokalen Graph zu Fuseki"""
        if not self.use_fuseki or not self.sparql_endpoint:
            return

        try:
            # Serialisiere Graph als Turtle
            ttl_data = self.graph.serialize(format="turtle")

            # Update Endpoint für Fuseki
            update_endpoint = f"{self.fuseki_url}/update"
            response = httpx.post(
                update_endpoint,
                data={"update": f"INSERT DATA {{ {ttl_data} }}"},
                headers={"Content-Type": "application/sparql-update"},
                timeout=30.0,
            )
            response.raise_for_status()
        except Exception as e:
            # Log error, aber nicht abbrechen
            print(f"Warnung: Fuseki Sync fehlgeschlagen: {e}")

    def get_document_entities(self, document_id: int) -> list[dict[str, Any]]:
        """
        Hole alle Entitäten für ein Dokument

        Args:
            document_id: Dokument-ID

        Returns:
            Liste von Entitäten mit Typen
        """
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?entity ?type WHERE {{
            rotary:Document_{document_id} rotary:erwaehnt ?entity .
            ?entity rotary:entityType ?type .
        }}
        """
        return self.query(query)

    def get_entity_documents(self, entity_id: int) -> list[dict[str, Any]]:
        """
        Hole alle Dokumente für eine Entität

        Args:
            entity_id: Entitäts-ID

        Returns:
            Liste von Dokumenten
        """
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?document WHERE {{
            ?document rotary:erwaehnt rotary:Entity_{entity_id} .
        }}
        """
        return self.query(query)

    def save_to_file(self, filepath: str, format: str = "turtle") -> None:
        """
        Speichere Graph in Datei

        Args:
            filepath: Pfad zur Datei
            format: Format (turtle, xml, json-ld, etc.)
        """
        self.graph.serialize(destination=filepath, format=format)

    def load_from_file(self, filepath: str, format: str = "turtle") -> None:
        """
        Lade Graph aus Datei

        Args:
            filepath: Pfad zur Datei
            format: Format (turtle, xml, json-ld, etc.)
        """
        self.graph.parse(filepath, format=format)


# Singleton-Instanz
_triple_store: TripleStore | None = None


def get_triplestore(use_fuseki: bool = False) -> TripleStore:
    """
    Hole Triple Store Instanz (Singleton)

    Args:
        use_fuseki: Verwende Fuseki statt lokalem Graph

    Returns:
        TripleStore Instanz
    """
    global _triple_store
    if _triple_store is None:
        _triple_store = TripleStore(use_fuseki=use_fuseki)
    return _triple_store
