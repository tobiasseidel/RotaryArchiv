"""
OCR Vergleichs-Logik: Vergleich mehrerer OCR-Ergebnisse und Vorschlag des besten
"""

from difflib import SequenceMatcher
from typing import Any

from src.rotary_archiv.core.models import OCRResult, OCRSource


def compare_ocr_results(ocr_results: list[OCRResult]) -> dict[str, Any]:
    """
    Vergleiche mehrere OCRResult-Einträge

    Args:
        ocr_results: Liste von OCRResult-Objekten

    Returns:
        Dict mit Vergleichs-Metriken und Analyse
    """
    if not ocr_results:
        return {"error": "Keine OCR-Ergebnisse zum Vergleichen"}

    comparison = {
        "results": [],
        "metrics": {},
        "suggested_best": None,
    }

    for ocr_result in ocr_results:
        result_data = {
            "id": ocr_result.id,
            "source": ocr_result.source.value
            if isinstance(ocr_result.source, OCRSource)
            else ocr_result.source,
            "text_length": len(ocr_result.text) if ocr_result.text else 0,
            "confidence": ocr_result.confidence,
            "processing_time_ms": ocr_result.processing_time_ms,
            "has_error": ocr_result.error_message is not None,
            "engine_version": ocr_result.engine_version,
        }

        # Berechne zusätzliche Metriken
        if ocr_result.text:
            # Zeichen-Diversität (Anzahl eindeutiger Zeichen / Gesamtzeichen)
            unique_chars = len(set(ocr_result.text))
            total_chars = len(ocr_result.text)
            result_data["char_diversity"] = (
                unique_chars / total_chars if total_chars > 0 else 0
            )

            # Häufige OCR-Fehler-Indikatoren
            common_errors = _detect_common_ocr_errors(ocr_result.text)
            result_data["error_indicators"] = common_errors
        else:
            result_data["char_diversity"] = 0
            result_data["error_indicators"] = {}

        comparison["results"].append(result_data)

    # Berechne Gesamt-Metriken
    comparison["metrics"] = {
        "total_results": len(ocr_results),
        "results_with_text": sum(1 for r in ocr_results if r.text),
        "results_with_confidence": sum(
            1 for r in ocr_results if r.confidence is not None
        ),
        "average_confidence": _calculate_average_confidence(ocr_results),
        "average_processing_time": _calculate_average_processing_time(ocr_results),
    }

    # Vorschlag des besten Ergebnisses
    comparison["suggested_best"] = suggest_best_result(ocr_results)

    return comparison


def suggest_best_result(ocr_results: list[OCRResult]) -> int | None:
    """
    Schlägt bestes OCR-Ergebnis vor basierend auf Metriken

    Args:
        ocr_results: Liste von OCRResult-Objekten

    Returns:
        ID des vorgeschlagenen besten OCRResult oder None
    """
    if not ocr_results:
        return None

    # Filtere Ergebnisse mit Fehlern aus
    valid_results = [r for r in ocr_results if r.error_message is None and r.text]

    if not valid_results:
        # Falls alle Fehler haben, nimm das erste
        return ocr_results[0].id if ocr_results else None

    # Bewertungssystem
    scored_results = []
    for ocr_result in valid_results:
        score = 0.0

        # Confidence (0-1, Gewicht: 0.4)
        if ocr_result.confidence is not None:
            score += ocr_result.confidence * 0.4
        else:
            # Wenn keine Confidence, gebe mittlere Punktzahl
            score += 0.5 * 0.4

        # Textlänge (normalisiert, Gewicht: 0.2)
        max_length = max((len(r.text) for r in valid_results if r.text), default=1)
        if ocr_result.text:
            length_score = len(ocr_result.text) / max_length
            score += length_score * 0.2

        # Zeichen-Diversität (Gewicht: 0.1)
        if ocr_result.text:
            unique_chars = len(set(ocr_result.text))
            total_chars = len(ocr_result.text)
            diversity = unique_chars / total_chars if total_chars > 0 else 0
            score += diversity * 0.1

        # Fehler-Indikatoren (negativ, Gewicht: 0.2)
        error_indicators = _detect_common_ocr_errors(ocr_result.text)
        error_score = 1.0 - (
            sum(error_indicators.values()) / max(len(error_indicators), 1)
        )
        score += error_score * 0.2

        # Verarbeitungszeit (schneller ist besser, Gewicht: 0.1)
        if ocr_result.processing_time_ms:
            max_time = max(
                (r.processing_time_ms for r in valid_results if r.processing_time_ms),
                default=1,
            )
            time_score = 1.0 - (ocr_result.processing_time_ms / max_time)
            score += time_score * 0.1

        scored_results.append((ocr_result.id, score))

    # Sortiere nach Score (höchster zuerst)
    scored_results.sort(key=lambda x: x[1], reverse=True)

    return scored_results[0][0] if scored_results else None


def _detect_common_ocr_errors(text: str) -> dict[str, int]:
    """
    Erkenne häufige OCR-Fehler-Indikatoren

    Args:
        text: OCR-Text

    Returns:
        Dict mit Fehler-Indikatoren und deren Häufigkeit
    """
    errors = {
        "consecutive_spaces": text.count("  "),
        "isolated_chars": sum(
            1 for word in text.split() if len(word) == 1 and word.isalnum()
        ),
        "mixed_case_words": sum(
            1
            for word in text.split()
            if word and word[0].islower() and any(c.isupper() for c in word[1:])
        ),
        "numbers_in_words": sum(
            1
            for word in text.split()
            if any(c.isdigit() for c in word) and any(c.isalpha() for c in word)
        ),
    }
    return errors


def _calculate_average_confidence(ocr_results: list[OCRResult]) -> float | None:
    """Berechne durchschnittliche Confidence"""
    confidences = [r.confidence for r in ocr_results if r.confidence is not None]
    if not confidences:
        return None
    return sum(confidences) / len(confidences)


def _calculate_average_processing_time(ocr_results: list[OCRResult]) -> float | None:
    """Berechne durchschnittliche Verarbeitungszeit"""
    times = [
        r.processing_time_ms for r in ocr_results if r.processing_time_ms is not None
    ]
    if not times:
        return None
    return sum(times) / len(times)


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Berechne Text-Similarity zwischen zwei Texten

    Args:
        text1: Erster Text
        text2: Zweiter Text

    Returns:
        Similarity als Float 0.0-1.0 (1.0 = identisch)
    """
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0

    # Nutze SequenceMatcher für Similarity-Berechnung
    matcher = SequenceMatcher(None, text1, text2)
    return matcher.ratio()


def check_auto_review(
    ocr_results: list[OCRResult], similarity_threshold: float = 0.95
) -> bool:
    """
    Prüfe ob automatisches Review erstellt werden kann

    Args:
        ocr_results: Liste von OCRResult-Objekten
        similarity_threshold: Ähnlichkeits-Schwelle für automatisches Review (Standard: 0.95)

    Returns:
        True wenn automatisches Review erstellt werden kann, sonst False
    """
    if not ocr_results or len(ocr_results) < 2:
        return False

    # Filtere Ergebnisse mit Fehlern oder leerem Text
    valid_results = [
        r
        for r in ocr_results
        if r.error_message is None and r.text and len(r.text.strip()) > 0
    ]

    if len(valid_results) < 2:
        return False

    # Prüfe ob GPT-kombiniertes Ergebnis vorhanden und Confidence hoch
    gpt_result = next(
        (
            r
            for r in valid_results
            if r.source == OCRSource.COMBINED or r.source == OCRSource.GPT_CORRECTED
        ),
        None,
    )
    if gpt_result and gpt_result.confidence and gpt_result.confidence > 0.9:
        return True

    # Prüfe Text-Similarity zwischen allen gültigen Ergebnissen
    similarities = []
    for i, result1 in enumerate(valid_results):
        for result2 in valid_results[i + 1 :]:
            similarity = calculate_text_similarity(result1.text, result2.text)
            similarities.append(similarity)

    if not similarities:
        return False

    # Wenn durchschnittliche Similarity über Schwelle: Auto-Review
    avg_similarity = sum(similarities) / len(similarities)
    if avg_similarity >= similarity_threshold:
        return True

    # Wenn mindestens zwei Ergebnisse sehr ähnlich sind (> 95%)
    high_similarity_count = sum(1 for s in similarities if s >= similarity_threshold)
    if high_similarity_count >= len(valid_results) - 1:
        return True

    return False
