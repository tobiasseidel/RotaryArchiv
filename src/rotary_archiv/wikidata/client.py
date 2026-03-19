"""
Wikidata API Client

NOTE: Vorerst nicht verwendet - kann später wieder aktiviert werden
"""

from typing import Any

import httpx

from src.rotary_archiv.config import settings


class WikidataClient:
    """Client für Wikidata API"""

    def __init__(self):
        """Initialisiere Wikidata Client"""
        self.api_url = settings.wikidata_api_url
        self.sparql_url = settings.wikidata_sparql_url

    def search_entity(
        self, query: str, language: str = "de", limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Suche Entität in Wikidata

        Args:
            query: Suchanfrage (z.B. "Max Müller")
            language: Sprache für Labels
            limit: Maximale Anzahl Ergebnisse

        Returns:
            Liste von Wikidata-Entitäten
        """
        try:
            headers = {
                "User-Agent": "RotaryArchiv/1.0 (https://github.com/rotary-archiv; contact via Wikidata)"
            }
            with httpx.Client(timeout=30.0, headers=headers) as client:
                params = {
                    "action": "wbsearchentities",
                    "search": query,
                    "language": language,
                    "format": "json",
                    "limit": limit,
                }

                response = client.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                if "search" in data:
                    for item in data["search"]:
                        # API kann label/description als String oder als Objekt {"value": "..."} liefern
                        label = item.get("label")
                        if isinstance(label, dict):
                            label = label.get("value") or ""
                        desc = item.get("description")
                        if isinstance(desc, dict):
                            desc = desc.get("value") or ""
                        if label is None:
                            label = ""
                        if desc is None:
                            desc = ""
                        results.append(
                            {
                                "id": item.get("id"),
                                "label": label,
                                "description": desc,
                                "url": f"https://www.wikidata.org/wiki/{item.get('id')}",
                                "match": (item.get("match") or {}).get("text", ""),
                            }
                        )

                # #region agent log
                import json

                _log = {
                    "sessionId": "983982",
                    "location": "WikidataClient.search_entity",
                    "message": "search result",
                    "data": {
                        "query": query,
                        "resultCount": len(results),
                        "hasError": any("error" in r for r in results),
                    },
                    "timestamp": __import__("time").time() * 1000,
                    "hypothesisId": "A",
                }
                try:
                    with open("debug-983982.log", "a", encoding="utf-8") as _f:
                        _f.write(json.dumps(_log, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                return results
        except Exception as e:
            # #region agent log
            import json

            _log = {
                "sessionId": "983982",
                "location": "WikidataClient.search_entity",
                "message": "search exception",
                "data": {"query": query, "error": str(e)},
                "timestamp": __import__("time").time() * 1000,
                "hypothesisId": "C",
            }
            try:
                with open("debug-983982.log", "a", encoding="utf-8") as _f:
                    _f.write(json.dumps(_log, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            return [{"error": str(e)}]

    def get_entity(self, entity_id: str, language: str = "de") -> dict[str, Any] | None:
        """
        Hole Details zu einer Wikidata-Entität

        Args:
            entity_id: Wikidata ID (z.B. "Q123456")
            language: Sprache für Labels

        Returns:
            Dict mit Entitäts-Details oder None
        """
        try:
            headers = {
                "User-Agent": "RotaryArchiv/1.0 (https://github.com/rotary-archiv; contact via Wikidata)"
            }
            with httpx.Client(timeout=30.0, headers=headers) as client:
                params = {
                    "action": "wbgetentities",
                    "ids": entity_id,
                    "languages": language,
                    "format": "json",
                    "props": "labels|descriptions|claims|sitelinks",
                }

                response = client.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()

                if "entities" in data and entity_id in data["entities"]:
                    entity = data["entities"][entity_id]
                    if entity.get("missing"):
                        return None
                    return {
                        "id": entity_id,
                        "label": entity.get("labels", {})
                        .get(language, {})
                        .get("value"),
                        "description": entity.get("descriptions", {})
                        .get(language, {})
                        .get("value"),
                        "claims": entity.get("claims", {}),
                        "sitelinks": entity.get("sitelinks", {}),
                        "url": f"https://www.wikidata.org/wiki/{entity_id}",
                    }

                return None
        except Exception as e:
            return {"error": str(e)}

    def get_labels(self, ids: list[str], language: str = "de") -> dict[str, str]:
        """
        Hole Labels für mehrere Wikidata-IDs (Properties wie P569 oder Items wie Q183).
        wbgetentities mit props=labels; max 50 IDs pro Request (Batching).

        Returns:
            Dict id -> Label-Text (z. B. {"P569": "Geburtsdatum", "Q183": "Deutschland"})
        """
        result: dict[str, str] = {}
        if not ids:
            return result
        ids = list(dict.fromkeys(ids))  # unique, order preserved
        chunk_size = 50
        try:
            headers = {
                "User-Agent": "RotaryArchiv/1.0 (https://github.com/rotary-archiv; contact via Wikidata)"
            }
            with httpx.Client(timeout=30.0, headers=headers) as client:
                for i in range(0, len(ids), chunk_size):
                    chunk = ids[i : i + chunk_size]
                    params = {
                        "action": "wbgetentities",
                        "ids": "|".join(chunk),
                        "languages": language,
                        "format": "json",
                        "props": "labels",
                    }
                    response = client.get(self.api_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    entities = data.get("entities") or {}
                    for eid in chunk:
                        ent = entities.get(eid)
                        if ent and not ent.get("missing"):
                            labels = ent.get("labels") or {}
                            lang_label = labels.get(language) or labels.get("en") or {}
                            if isinstance(lang_label, dict):
                                result[eid] = lang_label.get("value", eid)
                            else:
                                result[eid] = eid
        except Exception:
            pass
        return result

    def sparql_query(self, query: str) -> list[dict[str, Any]]:
        """
        Führe SPARQL Query auf Wikidata aus

        Args:
            query: SPARQL Query String

        Returns:
            Liste von Ergebnis-Dicts
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    self.sparql_url, params={"query": query, "format": "json"}
                )
                response.raise_for_status()
                data = response.json()

                results = []
                if "results" in data and "bindings" in data["results"]:
                    for binding in data["results"]["bindings"]:
                        result = {}
                        for key, value in binding.items():
                            result[key] = value.get("value", "")
                        results.append(result)

                return results
        except Exception as e:
            return [{"error": str(e)}]
