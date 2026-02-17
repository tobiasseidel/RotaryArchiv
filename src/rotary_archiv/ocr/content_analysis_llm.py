"""
LLM-gestützte Content-Analyse: Seitenpaar-Zusammengehörigkeit, Zusammenfassung,
Personen mit Rollen, Thema, Ort/Datum, Extraktion von Floskeln und Namen.
"""

import json
import logging
import re
import time
from typing import Any

import httpx

from src.rotary_archiv.config import settings as app_config

logger = logging.getLogger(__name__)

# Feste Rollen für Personen (laut Plan)
PERSON_ROLES = [
    "Clubvorstand",
    "anwesendes Clubmitglied",
    "abwesendes Clubmitglied",
    "Referent",
    "rotarischer Gast",
    "nicht-rotarischer Gast",
    "andere",
]


def build_content_analysis_prompts(
    page_a_text: str,
    page_b_text: str | None,
) -> tuple[str, str]:
    """
    Baut System- und User-Prompt für die Content-Analyse (Seitenpaar).

    Seite B wird nur zur Prüfung der Verbindung mitgegeben; die inhaltliche
    Analyse (Zusammenfassung, Personen, Thema, Ort/Datum) bezieht sich nur auf
    den Inhalt, der zur Einheit gehört (nur A wenn nicht zusammengehörig, A+B wenn ja).

    Returns:
        (system_prompt, user_prompt)
    """
    roles_str = ", ".join(PERSON_ROLES)

    system_prompt = (
        "Du bist ein Experte für die Auswertung von Club-Protokollen und Sitzungsberichten.\n\n"
        "Aufgabe:\n"
        "1. ZUERST entscheide: Gehören Seite A und Seite B inhaltlich zusammen "
        "(ein und dasselbe Protokoll / dieselbe Veranstaltung)? Antworte mit belongs_with_next: true oder false.\n"
        "2. FALLS belongs_with_next = true: Analysiere den KOMBINIERTEN Inhalt von Seite A und B. "
        "Zusammenfassung, Personen, Thema, Ort und Datum beziehen sich auf A+B. "
        "Extrahiere typische Formulierungen (Floskeln) und alle erwähnten Personennamen aus A+B.\n"
        "3. FALLS belongs_with_next = false: Analysiere NUR den Inhalt von SEITE A. "
        "Der Inhalt von Seite B darf in Zusammenfassung, Personen, Thema, Ort und Datum NICHT vorkommen. "
        "Extrahiere Floskeln und Namen NUR aus Seite A.\n\n"
        "Personen: Jede erwähnte Person mit ihrer Rolle. Rolle MUSS eine der folgenden sein (genau so schreiben): "
        f"{roles_str}.\n\n"
        "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (kein anderer Text, kein Markdown):\n"
        '{"belongs_with_next": true oder false, '
        '"summary": "Zusammenfassung des Inhalts", '
        '"persons": [{"name": "Name", "role": "Rolle aus der Liste"}], '
        '"topic": "Thema falls erkennbar oder leer", '
        '"place": "Ort falls erkennbar oder leer", '
        '"event_date": "Datum der Veranstaltung falls erkennbar oder leer", '
        '"extracted_phrases": ["Formulierung 1", "..."], '
        '"extracted_names": ["Name1", "Name2", "..."]}'
    )

    user_prompt = "=== SEITE A (aktuell) ===\n" + (page_a_text or "(leer)")
    if page_b_text is not None:
        user_prompt += "\n\n=== SEITE B (nur zur Prüfung der Verbindung - nicht in Analyse einbeziehen wenn belongs_with_next = false) ===\n"
        user_prompt += page_b_text

    return system_prompt, user_prompt


def parse_content_analysis_response(response_text: str) -> dict[str, Any] | None:
    """
    Parst die LLM-Antwort auf strukturierte Felder für Content-Analyse.

    Sucht nach JSON mit belongs_with_next, summary, persons, topic, place,
    event_date, extracted_phrases, extracted_names.

    Returns:
        Dict mit den Feldern oder None bei Parse-Fehler.
    """
    if not response_text or not response_text.strip():
        return None

    text = response_text.strip()

    # Versuch: JSON in ```-Blöcken
    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if code_match:
        text = code_match.group(1).strip()

    # Versuch: erstes {...} finden
    brace = text.find("{")
    if brace >= 0:
        depth = 0
        end = -1
        for i in range(brace, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end >= 0:
            text = text[brace : end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.debug("Content-Analyse: JSON parse failed for: %s", text[:300])
        return None

    if not isinstance(data, dict):
        return None

    # Normalisiere Felder
    result: dict[str, Any] = {
        "belongs_with_next": bool(data.get("belongs_with_next", False)),
        "summary": (data.get("summary") or "").strip() or None,
        "persons": data.get("persons"),
        "topic": (data.get("topic") or "").strip() or None,
        "place": (data.get("place") or "").strip() or None,
        "event_date": (data.get("event_date") or "").strip() or None,
        "extracted_phrases": data.get("extracted_phrases"),
        "extracted_names": data.get("extracted_names"),
    }

    if not isinstance(result["persons"], list):
        result["persons"] = []
    if not isinstance(result["extracted_phrases"], list):
        result["extracted_phrases"] = []
    if not isinstance(result["extracted_names"], list):
        result["extracted_names"] = []

    # persons: Liste von {name, role}; Rolle auf erlaubte Werte prüfen
    normalized_persons = []
    for p in result["persons"]:
        if isinstance(p, dict) and p.get("name"):
            role = (p.get("role") or "").strip()
            if role not in PERSON_ROLES:
                role = "andere"
            normalized_persons.append({"name": str(p["name"]).strip(), "role": role})
    result["persons"] = normalized_persons

    return result


def call_ollama_content_analysis(
    page_a_text: str,
    page_b_text: str | None = None,
) -> dict[str, Any]:
    """
    Ruft das Ollama-Modell für Content-Analyse auf (Seitenpaar).

    Args:
        page_a_text: Volltext der aktuellen Seite (in Lesereihenfolge).
        page_b_text: Volltext der nächsten Seite (nur für Verbindungsprüfung); optional.

    Returns:
        Dict mit:
        - success: bool
        - belongs_with_next, summary, persons, topic, place, event_date,
          extracted_phrases, extracted_names (bei Erfolg)
        - error: str (bei Fehler)
        - raw_content: str
    """
    base_url = app_config.ollama_base_url
    model = app_config.ollama_gpt_model
    timeout_sec = getattr(app_config, "ollama_timeout_seconds", 300)

    system_prompt, user_prompt = build_content_analysis_prompts(
        page_a_text, page_b_text
    )

    timeout = httpx.Timeout(
        connect=10.0,
        read=timeout_sec,
        write=timeout_sec,
        pool=10.0,
    )

    result: dict[str, Any] = {
        "success": False,
        "belongs_with_next": False,
        "summary": None,
        "persons": [],
        "topic": None,
        "place": None,
        "event_date": None,
        "extracted_phrases": [],
        "extracted_names": [],
        "raw_content": "",
        "error": None,
    }

    try:
        start = time.time()
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
            )
        response.raise_for_status()
        data = response.json()
        content = (data.get("message") or {}).get("content") or ""
        result["raw_content"] = content

        parsed = parse_content_analysis_response(content)
        if parsed:
            result["success"] = True
            result["belongs_with_next"] = parsed["belongs_with_next"]
            result["summary"] = parsed["summary"]
            result["persons"] = parsed["persons"]
            result["topic"] = parsed["topic"]
            result["place"] = parsed["place"]
            result["event_date"] = parsed["event_date"]
            result["extracted_phrases"] = parsed["extracted_phrases"]
            result["extracted_names"] = parsed["extracted_names"]
        else:
            result["error"] = "LLM-Antwort konnte nicht als JSON gelesen werden"

        logger.info(
            "Ollama content_analysis %.1fs, belongs_with_next=%s",
            time.time() - start,
            result["belongs_with_next"],
        )
        return result

    except httpx.TimeoutException as e:
        result["error"] = f"Timeout: {e}"
        logger.warning("Ollama content_analysis timeout: %s", e)
        return result
    except httpx.HTTPStatusError as e:
        result["error"] = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        logger.warning("Ollama content_analysis HTTP error: %s", result["error"])
        return result
    except Exception as e:
        result["error"] = str(e)
        logger.exception("Ollama content_analysis error")
        return result
