"""
Entitäten-Typen und Stub für den Entitäten-Katalog der Erschließungsschicht.

Geplant: Entitäten-Katalog (Person, Place, Event, Topic) und Verknüpfung zu
DocumentUnits/Mentions. Die Quelle (Dokument, DocumentUnit) wird im Triple Store
nur als Referenz verwendet (Prädikat z. B. rotary:belegtIn), nicht als Subjekt
oder Objekt der Faktentriples. Siehe docs/erschliessung.md.
"""

from enum import Enum


class EntityType(str, Enum):
    """Typ einer Entität für den Erschließungs-Katalog und Wikidata-Matching."""

    PERSON = "person"
    PLACE = "place"
    EVENT = "event"
    ORGANISATION = "organisation"
    TOPIC = "topic"
