"""
Named Entity Recognition für Dokumente
"""

from typing import Any

import spacy

from src.rotary_archiv.core.models import EntityType


class NERProcessor:
    """Named Entity Recognition Processor"""

    def __init__(self, model_name: str = "de_core_news_sm"):
        """
        Initialisiere NER Processor

        Args:
            model_name: spaCy Modell-Name (z.B. "de_core_news_sm")
        """
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            # Fallback: Versuche deutsches Modell zu laden oder nutze leeres Modell
            try:
                self.nlp = spacy.load("de_core_news_sm")
            except OSError:
                # Warnung: Modell nicht gefunden, muss installiert werden
                print(
                    f"Warnung: spaCy Modell '{model_name}' nicht gefunden. Bitte installieren: python -m spacy download {model_name}"
                )
                self.nlp = None

    def extract_entities(
        self, text: str, entity_types: list[EntityType] | None = None
    ) -> list[dict[str, Any]]:
        """
        Extrahiere Entitäten aus Text

        Args:
            text: Text für NER
            entity_types: Optionale Filterung nach Entitäts-Typen

        Returns:
            Liste von erkannten Entitäten
        """
        if not self.nlp:
            return []

        doc = self.nlp(text)
        entities = []

        # Mapping von spaCy Labels zu unseren EntityTypes
        label_mapping = {
            "PER": EntityType.PERSON,
            "PERSON": EntityType.PERSON,
            "LOC": EntityType.PLACE,
            "GPE": EntityType.PLACE,  # Geopolitical Entity
            "ORG": EntityType.ORGANIZATION,
            "MISC": EntityType.TOPIC,
        }

        seen_entities = set()

        for ent in doc.ents:
            # Bestimme EntityType
            entity_type = label_mapping.get(ent.label_, EntityType.TOPIC)

            # Filterung nach gewünschten Typen
            if entity_types and entity_type not in entity_types:
                continue

            # Erstelle eindeutigen Key
            entity_key = (ent.text.lower(), entity_type)
            if entity_key in seen_entities:
                continue
            seen_entities.add(entity_key)

            entities.append(
                {
                    "text": ent.text,
                    "type": entity_type,
                    "label": ent.label_,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                    "confidence": None,  # spaCy gibt keine Confidence
                }
            )

        return entities

    def extract_persons(self, text: str) -> list[dict[str, Any]]:
        """Extrahiere nur Personen"""
        return self.extract_entities(text, [EntityType.PERSON])

    def extract_places(self, text: str) -> list[dict[str, Any]]:
        """Extrahiere nur Orte"""
        return self.extract_entities(text, [EntityType.PLACE])

    def extract_organizations(self, text: str) -> list[dict[str, Any]]:
        """Extrahiere nur Organisationen"""
        return self.extract_entities(text, [EntityType.ORGANIZATION])

    def suggest_entity_type(self, text: str) -> EntityType | None:
        """
        Vorschlage EntityType für einen Text

        Args:
            text: Text (z.B. Name einer Person)

        Returns:
            Vorgeschlagener EntityType oder None
        """
        if not self.nlp:
            return None

        doc = self.nlp(text)

        # Wenn nur eine Entität gefunden wird, nutze deren Typ
        if len(doc.ents) == 1:
            ent = doc.ents[0]
            label_mapping = {
                "PER": EntityType.PERSON,
                "PERSON": EntityType.PERSON,
                "LOC": EntityType.PLACE,
                "GPE": EntityType.PLACE,
                "ORG": EntityType.ORGANIZATION,
            }
            return label_mapping.get(ent.label_, None)

        return None
