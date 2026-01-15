"""
Wikidata Entity Matcher
"""
from typing import Dict, Any, List, Optional
from src.rotary_archiv.core.models import EntityType
from src.rotary_archiv.wikidata.client import WikidataClient


class WikidataMatcher:
    """Matcht interne Entitäten mit Wikidata"""
    
    def __init__(self):
        """Initialisiere Wikidata Matcher"""
        self.client = WikidataClient()
    
    def find_matches(
        self,
        name: str,
        entity_type: EntityType,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Finde Wikidata-Matches für eine Entität
        
        Args:
            name: Name der Entität
            entity_type: Typ der Entität
            context: Optional: Kontext (z.B. "Berlin", "Rotary Club")
            
        Returns:
            Liste von Wikidata-Matches mit Scores
        """
        # Erstelle Suchanfrage mit Kontext
        if context:
            query = f"{name} {context}"
        else:
            query = name
        
        # Suche in Wikidata
        results = self.client.search_entity(query, limit=20)
        
        # Filtere und score Ergebnisse
        scored_results = []
        for result in results:
            if "error" in result:
                continue
            
            score = self._calculate_match_score(
                name,
                entity_type,
                result,
                context
            )
            
            if score > 0.3:  # Mindest-Score
                result["match_score"] = score
                scored_results.append(result)
        
        # Sortiere nach Score
        scored_results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return scored_results[:10]  # Top 10
    
    def _calculate_match_score(
        self,
        name: str,
        entity_type: EntityType,
        wikidata_result: Dict[str, Any],
        context: Optional[str] = None
    ) -> float:
        """
        Berechne Match-Score für Wikidata-Ergebnis
        
        Args:
            name: Name der Entität
            entity_type: Typ der Entität
            wikidata_result: Wikidata-Suchergebnis
            context: Optional: Kontext
            
        Returns:
            Score zwischen 0 und 1
        """
        score = 0.0
        
        # Name-Match
        label = wikidata_result.get("label", "").lower()
        name_lower = name.lower()
        
        if name_lower == label:
            score += 0.5  # Exakter Match
        elif name_lower in label or label in name_lower:
            score += 0.3  # Teil-Match
        
        # Description-Match (für Kontext)
        description = wikidata_result.get("description", "").lower()
        if context:
            context_lower = context.lower()
            if context_lower in description:
                score += 0.2
        
        # Entity-Type-Hints (vereinfacht)
        # In Produktion könnte man Wikidata-Properties prüfen
        description_lower = description.lower()
        type_keywords = {
            EntityType.PERSON: ["person", "mensch", "politiker", "schriftsteller"],
            EntityType.PLACE: ["stadt", "ort", "stadtteil", "place"],
            EntityType.ORGANIZATION: ["organisation", "verein", "club", "gesellschaft"],
        }
        
        keywords = type_keywords.get(entity_type, [])
        for keyword in keywords:
            if keyword in description_lower:
                score += 0.1
                break
        
        return min(score, 1.0)
    
    def get_entity_details(self, wikidata_id: str) -> Optional[Dict[str, Any]]:
        """
        Hole Details zu einer Wikidata-Entität
        
        Args:
            wikidata_id: Wikidata ID (z.B. "Q123456")
            
        Returns:
            Dict mit Details oder None
        """
        return self.client.get_entity(wikidata_id)
    
    def suggest_import_data(
        self,
        wikidata_id: str
    ) -> Dict[str, Any]:
        """
        Vorschlage Daten zum Import von Wikidata
        
        Args:
            wikidata_id: Wikidata ID
            
        Returns:
            Dict mit vorgeschlagenen Import-Daten
        """
        entity = self.client.get_entity(wikidata_id)
        if not entity or "error" in entity:
            return {"error": "Entität nicht gefunden"}
        
        # Extrahiere relevante Properties
        import_data = {
            "wikidata_id": wikidata_id,
            "label": entity.get("label"),
            "description": entity.get("description"),
            "url": entity.get("url"),
            "claims": entity.get("claims", {}),
            "sitelinks": entity.get("sitelinks", {})
        }
        
        return import_data
