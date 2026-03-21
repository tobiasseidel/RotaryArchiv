"""
Wikidata-Property-Sync: Liste der Properties, die wir 1:1 wie Wikidata speichern.
Extraktion von Werten aus Wikidata-claims für PERSON_SYNC_PROPERTIES.
Alle Properties (extract_all_claim_values), Bilder (extract_image_claims).
"""

import re
from typing import Any

# Eigene Liste: welche Wikidata-Properties für Personen synchronisiert werden
# P569 = Geburtsdatum, P570 = Sterbedatum
PERSON_SYNC_PROPERTIES = ["P569", "P570"]

# Bild-Properties (Commons-Dateiname)
IMAGE_PROPERTY_IDS = ["P18"]

# Property-Labels für Anzeige (häufige Personen-Properties)
PROPERTY_LABELS: dict[str, str] = {
    "P569": "Geburtsdatum",
    "P570": "Sterbedatum",
    "P27": "Staatsangehörigkeit",
    "P106": "Beruf",
    "P18": "Bild",
    "P21": "Geschlecht",
    "P19": "Geburtsort",
    "P20": "Sterbeort",
    "P22": "Vater",
    "P25": "Mutter",
}
COMMONS_FILEPATH_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/"


def normalize_commons_filename(value: str) -> str:
    """Normiert Commons-Dateinamen für stabile Speicherung/Keys."""
    name = (value or "").strip()
    if name.startswith("File:"):
        name = name[5:].strip()
    return name.replace("_", " ")


def _normalize_time_value(time_str: str) -> str | None:
    """
    Normalisiere Wikidata-Zeit (z.B. '+1952-03-11T00:00:00Z') zu Datum 'YYYY-MM-DD'.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    # Entferne führendes +/-, Zeitzone, Zeitanteil
    m = re.match(r"([+-]?\d{4}-\d{2}-\d{2})", time_str.strip())
    if m:
        return m.group(1).lstrip("+")
    return None


def _extract_value_from_statement(statement: dict, prop_id: str) -> Any | None:
    """
    Extrahiere einen einzelnen Wert aus einem Wikidata-Statement.
    Unterstützt: time (P569, P570), string, quantity; andere Typen → str wenn möglich.
    """
    mainsnak = statement.get("mainsnak") or {}
    if mainsnak.get("snaktype") != "value":
        return None
    dv = mainsnak.get("datavalue") or {}
    val = dv.get("value")
    if val is None:
        return None
    dt = mainsnak.get("datatype", "")
    if dt == "time" and isinstance(val, dict) and "time" in val:
        return _normalize_time_value(val["time"])
    if dt == "string" and isinstance(val, str):
        return val
    if dt == "commonsMedia" and isinstance(val, str):
        return val
    if dt == "commonsMedia" and isinstance(val, dict) and "value" in val:
        return val.get("value", "")
    if isinstance(val, dict) and "amount" in val:
        return val.get("amount", "").replace("+", "").strip()
    if isinstance(val, dict) and "id" in val:
        return val.get("id")  # entity (z.B. Q...)
    if isinstance(val, (str, int, float)):
        return val
    return str(val)


def extract_syncable_claim_values(claims: dict[str, Any]) -> dict[str, Any]:
    """
    Liest aus Wikidata-claims nur die in PERSON_SYNC_PROPERTIES gelisteten
    Properties aus und liefert sie als Dict P-ID -> normalisierter Wert.
    Pro Property wird das erste Statement verwendet.

    Args:
        claims: entity.get("claims", {}) von get_entity()

    Returns:
        z.B. {"P569": "1952-03-11", "P570": "2020-01-15"}
    """
    result: dict[str, Any] = {}
    if not isinstance(claims, dict):
        return result
    for prop_id in PERSON_SYNC_PROPERTIES:
        statements = claims.get(prop_id)
        if not statements or not isinstance(statements, list):
            continue
        for st in statements:
            v = _extract_value_from_statement(st, prop_id)
            if v is not None:
                result[prop_id] = v
                break
    return result


def extract_all_claim_values(claims: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Alle Properties aus Wikidata-claims auslesen (für Sync-Dialog).
    Pro Property erstes Statement, Wert wie _extract_value_from_statement.
    Returns: [{"prop_id": "P569", "value": "...", "datatype": "time"}, ...]
    """
    result: list[dict[str, Any]] = []
    if not isinstance(claims, dict):
        return result
    for prop_id, statements in claims.items():
        if not statements or not isinstance(statements, list):
            continue
        for st in statements:
            mainsnak = st.get("mainsnak") or {}
            dt = mainsnak.get("datatype", "")
            v = _extract_value_from_statement(st, prop_id)
            if v is not None:
                result.append({"prop_id": prop_id, "value": v, "datatype": dt})
    return result


def get_property_label(prop_id: str) -> str:
    """Lesbares Label für Property-ID (aus PROPERTY_LABELS oder prop_id)."""
    return PROPERTY_LABELS.get(prop_id, prop_id)


def commons_thumb_url(commons_filename: str, width: int = 200) -> str:
    """Commons-Dateiname zu Thumbnail-URL (Special:FilePath)."""
    if not commons_filename or not isinstance(commons_filename, str):
        return ""
    name = normalize_commons_filename(commons_filename)
    from urllib.parse import quote

    encoded = quote(name.replace(" ", "_"))
    return f"{COMMONS_FILEPATH_URL}{encoded}?width={width}"


# P625 = coordinate location (globe coordinate: latitude, longitude)
def extract_place_image_url(claims: dict[str, Any]) -> str | None:
    """
    Erstes Bild (P18) eines Ortes aus Wikidata-claims.
    Returns: Voll-URL für Bild (Commons Special:FilePath) oder None.
    """
    extracted = extract_image_claims(claims)
    if not extracted:
        return None
    val = extracted[0].get("value")
    if not val:
        return None
    if val.startswith("File:"):
        val = val[5:].strip()
    from urllib.parse import quote

    encoded = quote(val.replace(" ", "_"))
    return f"{COMMONS_FILEPATH_URL}{encoded}"


def extract_place_coordinates(
    claims: dict[str, Any],
) -> tuple[float | None, float | None]:
    """
    Koordinaten (P625) eines Ortes aus Wikidata-claims.
    P625 = globe coordinate: latitude, longitude.
    Returns: (lat, lon) oder (None, None).
    """
    statements = (claims or {}).get("P625")
    if not statements or not isinstance(statements, list):
        return (None, None)
    for st in statements:
        mainsnak = st.get("mainsnak") or {}
        if mainsnak.get("snaktype") != "value":
            continue
        dv = mainsnak.get("datavalue") or {}
        val = dv.get("value")
        if not isinstance(val, dict):
            continue
        try:
            lat = float(val.get("latitude"))
            lon = float(val.get("longitude"))
            return (lat, lon)
        except (TypeError, ValueError):
            continue
    return (None, None)


def extract_image_claims(claims: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Bild-Properties (z. B. P18) aus claims extrahieren.
    Returns: [{"prop_id": "P18", "value": "Filename.jpg", "thumb_url": "https://..."}, ...]
    """
    result: list[dict[str, Any]] = []
    if not isinstance(claims, dict):
        return result
    for prop_id in IMAGE_PROPERTY_IDS:
        statements = claims.get(prop_id)
        if not statements or not isinstance(statements, list):
            continue
        for st in statements:
            mainsnak = st.get("mainsnak") or {}
            if mainsnak.get("snaktype") != "value":
                continue
            dv = mainsnak.get("datavalue") or {}
            val = dv.get("value")
            if val is None:
                continue
            if isinstance(val, dict) and "value" in val:
                val = val["value"]
            if not isinstance(val, str) or not val.strip():
                continue
            filename = normalize_commons_filename(val)
            thumb_url = commons_thumb_url(filename, 200)
            result.append(
                {
                    "prop_id": prop_id,
                    "value": filename,
                    "thumb_url": thumb_url,
                    "source_url": commons_thumb_url(filename, 1024),
                }
            )
            break
    return result
