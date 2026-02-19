"""
LLM-gestützte OCR-Sichtung: Text-Korrektur und Bewertung via Ollama GPT (text-only).
"""

import json
import logging
import re
import time
from typing import Any

import httpx

from src.rotary_archiv.config import settings as app_config

logger = logging.getLogger(__name__)


def build_sight_prompts(
    ocr_text: str,
    *,
    time_period: str = "",
    language_style: str = "",
    black_pixels_per_char: float | None = None,
    expected_names: str = "",
    typical_phrases: str = "",
    review_notes: str = "",
    variants: list[str] | None = None,
    context_before: str = "",
    context_after: str = "",
) -> tuple[str, str]:
    """
    Baut System- und User-Prompt für die LLM-Sichtung.

    - variants: Wenn 2+ unterschiedliche OCR-Varianten, werden diese als A/B/C
      übergeben; das LLM wählt die richtige oder korrigierte Fassung.
    - context_before/context_after: Optionale Kontexttexte (Nachbarboxen oder
      Seitentext); corrected_text darf nur den Inhalt der einen Box enthalten.

    Returns:
        (system_prompt, user_prompt)
    """
    time_ctx = time_period.strip() if time_period else "nicht angegeben"
    lang_ctx = language_style.strip() if language_style else "nicht angegeben"
    black_pc_str = (
        str(round(black_pixels_per_char, 1))
        if black_pixels_per_char is not None
        else "unbekannt"
    )

    # Anzeichen für gute Erkennung: Namen und typische Formulierungen (eine pro Zeile oder Komma)
    names_line = ""
    if expected_names and expected_names.strip():
        names_line = (
            "\n- Erwartete Namen in diesem Bestand (Vorkommen spricht für gute Erkennung): "
            + ", ".join(
                s.strip()
                for s in expected_names.replace("\n", ",").split(",")
                if s.strip()
            )
        )
    phrases_block = ""
    if typical_phrases and typical_phrases.strip():
        phrases_list = [
            s.strip()
            for s in typical_phrases.replace(",", "\n").split("\n")
            if s.strip()
        ]
        if phrases_list:
            phrases_block = (
                "\n\nAnzeichen für gute OCR-Qualität: Typische Formulierungen in diesem Bestand sind z. B.: "
                + "; ".join(
                    phrases_list[:20]
                )  # max. 20, damit Prompt nicht zu lang wird
                + ". Wenn der Text solche Formulierungen enthält, sinnvoll und fehlerfrei wirkt, "
                "bewerte die Confidence hoch (0.95-1.0) und setze auto_confirm auf true."
            )

    use_variants = variants and len(variants) > 1
    has_context = bool(context_before.strip() or context_after.strip())

    if use_variants:
        variant_instruction = (
            " Wenn mehrere Varianten (A, B, …) gegeben sind: Wähle die richtige Lesart oder gib eine "
            "korrigierte Fassung. Gib in corrected_text nur diesen einen Text - keine Variantenbezeichnung."
        )
    else:
        variant_instruction = ""

    if has_context:
        context_instruction = (
            " Der User-Prompt kann Kontext (Nachbarboxen/Seite) enthalten. "
            "corrected_text enthält ausschließlich den bereinigten Inhalt der markierten Box, keinen Kontexttext."
        )
    else:
        context_instruction = ""

    review_notes_block = ""
    if review_notes and review_notes.strip():
        review_notes_block = (
            "\n\nAnmerkungen und Wünsche des Nutzers zur Review (bitte beachten):\n"
            + review_notes.strip()
        )

    system_prompt = (
        "Du bist ein Experte für OCR-Qualität historischer Drucke.\n\n"
        "Kontext dieses Bestands:\n"
        f"- Zeitraum: {time_ctx}\n"
        f"- Sprache/Sprachstil: {lang_ctx}\n"
        f"- Qualitätshinweis (schwarze Pixel pro Zeichen, nur zur Einordnung): {black_pc_str}"
        f"{names_line}\n"
        "Deine Aufgabe:\n"
        "(1) Den OCR-Text bereinigen (Zeilenumbrüche und überflüssige Leerzeichen entfernen).\n"
        "(2) Offensichtliche OCR-Fehler korrigieren (z. B. O/C, 0/O, e/c/o, l/1, rn/m).\n"
        "(3) Jahreszahlen und Daten prüfen - wenn der Zeitraum bekannt ist, unglaubwürdige Zahlen anpassen "
        "(z. B. 1531 in einem Dokument aus dem 20. Jh. → 1931).\n"
        "(4) Nur sichere Korrekturen vornehmen; bei Unsicherheit Original belassen.\n"
        f"{phrases_block}"
        f"{review_notes_block}\n\n"
        "WICHTIG: Die nächste Nachricht (User) enthält den zu prüfenden Text (ggf. mit Kontext oder mehreren "
        "OCR-Varianten). Gib in corrected_text nur den bereinigten bzw. korrigierten Inhalt der einen Box zurück - "
        "nichts anderes."
        f"{variant_instruction}{context_instruction}\n\n"
        "Antworte ausschließlich mit einem JSON-Objekt in dieser Form (kein anderer Text):\n"
        '{"corrected_text": "...", "confidence": 0.0-1.0, "auto_confirm": true oder false, "reason": "kurze Begründung"}\n'
        "Hinweis zu confidence (Zahl 0.0-1.0): Deine Sicherheit, dass der ausgegebene corrected_text inhaltlich "
        "korrekt ist. Bei gutem Text mit nur kleinen Bereinigungen/Korrekturen: 0.85-1.0. Nur bei unsicheren oder "
        "fragwürdigen Korrekturen niedriger setzen; nie 0, wenn der Text insgesamt gut und verständlich ist."
    )

    # User-Prompt
    if use_variants:
        letters = ["A", "B", "C", "D", "E"][: len(variants)]
        parts = ["Varianten (OCR-Erkennungen derselben Region):"]
        for let, var in zip(letters, variants):
            parts.append(f"  {let}: {var}")
        parts.append(
            "Welche Lesart ist korrekt? Gib in corrected_text die richtige oder eine korrigierte Fassung (nur diesen einen Text)."
        )
        user_content = "\n".join(parts)
    else:
        user_content = ocr_text

    if has_context:
        before_block = (
            ("[Kontext vorher]\n" + context_before.strip() + "\n")
            if context_before.strip()
            else ""
        )
        after_block = (
            ("\n[Kontext nachher]\n" + context_after.strip())
            if context_after.strip()
            else ""
        )
        user_prompt = before_block + "[Zu prüfende Box]\n" + user_content + after_block
    else:
        user_prompt = user_content

    return system_prompt, user_prompt


def parse_sight_response(response_text: str) -> dict[str, Any] | None:
    """
    Parst die LLM-Antwort auf strukturierte Felder.

    Sucht nach JSON mit corrected_text, confidence, auto_confirm, reason.
    Versucht zuerst reines JSON, dann JSON in ```-Blöcken.

    Returns:
        Dict mit corrected_text, confidence (float), auto_confirm (bool), reason (str)
        oder None bei Parse-Fehler.
    """
    if not response_text or not response_text.strip():
        return None
    text = response_text.strip()

    # Versuch 1: Direktes JSON
    for raw in (text, text.split("\n")[0]):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "corrected_text" in obj:
                return _normalize_sight_response(obj)
        except json.JSONDecodeError:
            continue

    # Versuch 2: JSON in ```json ... ``` oder ``` ... ```
    for pattern in (r"```(?:json)?\s*([\s\S]*?)```", r"\{[\s\S]*\}"):
        match = re.search(pattern, text)
        if match:
            try:
                json_str = match.group(1) if "```" in pattern else match.group(0)
                obj = json.loads(json_str.strip())
                if isinstance(obj, dict) and "corrected_text" in obj:
                    return _normalize_sight_response(obj)
            except (json.JSONDecodeError, IndexError):
                continue

    return None


def _parse_confidence(value: Any) -> float:
    """
    Parst confidence aus LLM-Response (Zahl, String wie '0.9'/'85%'/'hoch').
    Returns float 0.0-1.0; bei Fehlern 0.5 als sinnvollen Default (nicht 0).
    """
    if value is None:
        return 0.5
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    s = str(value).strip().lower()
    if not s:
        return 0.5
    # Prozent-String z.B. "85%" oder "85"
    if "%" in s:
        try:
            return max(0.0, min(1.0, float(s.replace("%", "").strip()) / 100.0))
        except ValueError:
            pass
    # Dezimal-String z.B. "0.85"
    try:
        return max(0.0, min(1.0, float(s)))
    except ValueError:
        pass
    # Sprachliche Angaben
    if s in ("hoch", "high", "gut", "good", "sehr gut", "sehr hoch"):
        return 0.9
    if s in ("mittel", "medium", "mäßig"):
        return 0.6
    if s in ("niedrig", "low", "unsicher"):
        return 0.3
    return 0.5


def _normalize_sight_response(obj: dict[str, Any]) -> dict[str, Any]:
    """Setzt Typen und Defaults für die Response."""
    corrected = str(obj.get("corrected_text", "")).strip()
    conf = _parse_confidence(obj.get("confidence"))
    auto_confirm = bool(obj.get("auto_confirm", False))
    reason = str(obj.get("reason", "")).strip()
    return {
        "corrected_text": corrected,
        "confidence": conf,
        "auto_confirm": auto_confirm,
        "reason": reason,
    }


def call_ollama_sight(
    ocr_text: str,
    *,
    time_period: str = "",
    language_style: str = "",
    black_pixels_per_char: float | None = None,
    expected_names: str = "",
    typical_phrases: str = "",
    review_notes: str = "",
    variants: list[str] | None = None,
    context_before: str = "",
    context_after: str = "",
) -> dict[str, Any]:
    """
    Ruft das Ollama GPT-Modell (text-only) für OCR-Sichtung auf.

    Args:
        ocr_text: BBox-OCR-Text (wird bei variants ignoriert für den Prompt, aber als Fallback genutzt)
        time_period: Kontext Zeitraum (aus Settings)
        language_style: Kontext Sprache/Sprachstil (aus Settings)
        black_pixels_per_char: Qualitätshinweis (optional)
        expected_names: Namen, die im Bestand vorkommen (hilft bei höherer Confidence)
        typical_phrases: Typische Formulierungen (hilft bei höherer Confidence)
        review_notes: Sonstige User-Anmerkungen und Wünsche zur Review
        variants: Bei 2+ Einträgen: LLM wählt/korrigiert aus diesen OCR-Varianten
        context_before: Optionaler Kontexttext vor der Box (Nachbarboxen/Seite)
        context_after: Optionaler Kontexttext nach der Box

    Returns:
        Dict mit:
        - corrected_text, confidence, auto_confirm, reason (wenn Parsing ok)
        - success: bool
        - error: str (falls Fehler/Timeout)
        - raw_content: str (Antwort des Modells)
    """
    base_url = app_config.ollama_base_url
    model = app_config.ollama_gpt_model
    timeout_sec = getattr(app_config, "ollama_timeout_seconds", 300)

    system_prompt, user_prompt = build_sight_prompts(
        ocr_text,
        time_period=time_period,
        language_style=language_style,
        black_pixels_per_char=black_pixels_per_char,
        expected_names=expected_names or "",
        typical_phrases=typical_phrases or "",
        review_notes=review_notes or "",
        variants=variants,
        context_before=context_before or "",
        context_after=context_after or "",
    )

    timeout = httpx.Timeout(
        connect=10.0,
        read=timeout_sec,
        write=timeout_sec,
        pool=10.0,
    )
    result: dict[str, Any] = {
        "success": False,
        "corrected_text": ocr_text,
        "confidence": 0.0,
        "auto_confirm": False,
        "reason": "",
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

        parsed = parse_sight_response(content)
        if parsed:
            result["corrected_text"] = parsed["corrected_text"]
            result["confidence"] = parsed["confidence"]
            result["auto_confirm"] = parsed["auto_confirm"]
            result["reason"] = parsed["reason"]
            result["success"] = True
        else:
            result["error"] = "LLM-Antwort konnte nicht als JSON gelesen werden"
            result["corrected_text"] = ocr_text

        logger.debug(
            "Ollama sight call %.1fs, confidence=%.2f, auto_confirm=%s",
            time.time() - start,
            result["confidence"],
            result["auto_confirm"],
        )
        return result

    except httpx.TimeoutException as e:
        result["error"] = f"Timeout: {e}"
        logger.warning("Ollama sight timeout: %s", e)
        return result
    except httpx.HTTPStatusError as e:
        result["error"] = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        logger.warning("Ollama sight HTTP error: %s", result["error"])
        return result
    except Exception as e:
        result["error"] = str(e)
        logger.exception("Ollama sight error")
        return result


def compute_combined_sight_score(
    metric_score: float,
    confusion_score: float,
    llm_confidence: float,
    *,
    weight_metric: float = 0.4,
    weight_text: float = 0.2,
    weight_llm: float = 0.4,
) -> float:
    """
    Kombinierter Score 0-1 aus Metrik, Text-Heuristik und LLM-Bewertung.

    - metric_score: 0-1 (z. B. aus black_pixels_per_char)
    - confusion_score: 0-1 (ocr_confusion_score; hoher Wert = viele Verdachtsstellen)
    - llm_confidence: 0-1 aus LLM-Response

    Text-Anteil: (1 - confusion_score), damit wenig Verwechslungsverdacht gut ist.
    """
    text_part = 1.0 - min(1.0, max(0.0, confusion_score))
    total = (
        weight_metric * min(1.0, max(0.0, metric_score))
        + weight_text * text_part
        + weight_llm * min(1.0, max(0.0, llm_confidence))
    )
    return min(1.0, max(0.0, total))


def should_auto_confirm(
    llm_confidence: float,
    score_threshold: float,
    llm_auto_confirm: bool,
    *,
    black_pixels_per_char: float | None = None,
    black_pc_min: float | None = None,
    black_pc_max: float | None = None,
) -> bool:
    """
    Entscheidet, ob die Box automatisch bestätigt werden soll.

    Der Schwellwert wird mit der LLM-Confidence verglichen (derselbe Wert,
    der in der UI als „Einschätzung“ angezeigt wird).

    Bedingungen (alle erfüllt):
    - llm_confidence >= score_threshold
    - llm_auto_confirm == True
    - Optional: black_pixels_per_char im Bereich [black_pc_min, black_pc_max]
    """
    if llm_confidence < score_threshold or not llm_auto_confirm:
        return False
    if (
        black_pixels_per_char is not None
        and black_pc_min is not None
        and black_pc_max is not None
        and not (black_pc_min <= black_pixels_per_char <= black_pc_max)
    ):
        return False
    return True
