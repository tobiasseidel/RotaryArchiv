"""
Wikidata API Client
"""
import httpx
from typing import Dict, Any, List, Optional
import json

from src.rotary_archiv.config import settings


class WikidataClient:
    """Client für Wikidata API"""
    
    def __init__(self):
        """Initialisiere Wikidata Client"""
        self.api_url = settings.wikidata_api_url
        self.sparql_url = settings.wikidata_sparql_url
    
    def search_entity(
        self,
        query: str,
        language: str = "de",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
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
            with httpx.Client(timeout=30.0) as client:
                params = {
                    "action": "wbsearchentities",
                    "search": query,
                    "language": language,
                    "format": "json",
                    "limit": limit
                }
                
                response = client.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = []
                if "search" in data:
                    for item in data["search"]:
                        results.append({
                            "id": item.get("id"),  # z.B. "Q123456"
                            "label": item.get("label"),
                            "description": item.get("description"),
                            "url": f"https://www.wikidata.org/wiki/{item.get('id')}",
                            "match": item.get("match", {}).get("text", "")
                        })
                
                return results
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_entity(
        self,
        entity_id: str,
        language: str = "de"
    ) -> Optional[Dict[str, Any]]:
        """
        Hole Details zu einer Wikidata-Entität
        
        Args:
            entity_id: Wikidata ID (z.B. "Q123456")
            language: Sprache für Labels
            
        Returns:
            Dict mit Entitäts-Details oder None
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                params = {
                    "action": "wbgetentities",
                    "ids": entity_id,
                    "languages": language,
                    "format": "json",
                    "props": "labels|descriptions|claims|sitelinks"
                }
                
                response = client.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if "entities" in data and entity_id in data["entities"]:
                    entity = data["entities"][entity_id]
                    return {
                        "id": entity_id,
                        "label": entity.get("labels", {}).get(language, {}).get("value"),
                        "description": entity.get("descriptions", {}).get(language, {}).get("value"),
                        "claims": entity.get("claims", {}),
                        "sitelinks": entity.get("sitelinks", {}),
                        "url": f"https://www.wikidata.org/wiki/{entity_id}"
                    }
                
                return None
        except Exception as e:
            return {"error": str(e)}
    
    def sparql_query(self, query: str) -> List[Dict[str, Any]]:
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
                    self.sparql_url,
                    params={"query": query, "format": "json"}
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
