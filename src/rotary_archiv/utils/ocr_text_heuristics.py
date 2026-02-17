"""
OCR-Text-Heuristik: typische Zeichenverwechslungen (Confusion-Paare)
für die Bewertung von OCR-Qualität und LLM-Sichtung.
"""

import re
from typing import Any

# Typische OCR-Verwechslungspaare (Zeichen die oft verwechselt werden)
# Jedes Tupel: (Zeichen im Text, mögliche Alternativen)
OCR_CONFUSION_PAIRS: list[tuple[str, str]] = [
    ("O", "C0Q"),
    ("C", "OQG"),
    ("0", "OQ"),
    ("Q", "O0"),
    ("e", "co"),
    ("c", "eo"),
    ("o", "ce"),
    ("l", "1I|"),
    ("1", "lI"),
    ("I", "l1|"),
    ("rn", "m"),
    ("m", "rn"),
    ("cl", "d"),
    ("d", "cl"),
    ("ii", "u"),
    ("u", "ii"),
    ("n", "ri"),
    ("v", "u"),
    ("s", "ſ"),  # Lang-s  # noqa: RUF001
    ("ſ", "s"),  # noqa: RUF001
    ("a", "o"),
    ("r", "n"),
    ("5", "S"),
    ("S", "5"),
]

# Kompiliere: für jedes Zeichen die Menge der Alternativen
_CONFUSION_MAP: dict[str, set[str]] = {}
for char, alts in OCR_CONFUSION_PAIRS:
    for c in char + alts:
        if c not in _CONFUSION_MAP:
            _CONFUSION_MAP[c] = set()
        _CONFUSION_MAP[c].update(char + alts)
        _CONFUSION_MAP[c].discard(c)  # sich selbst nicht als Alternative


def get_ocr_confusion_indicators(text: str) -> list[dict[str, Any]]:
    """
    Durchsucht den Text nach Stellen, die typische OCR-Verwechslungen
    sein könnten (Zeichen aus Confusion-Paaren).

    Args:
        text: OCR-Text (einzeilig oder mehrzeilig)

    Returns:
        Liste von Dicts: position (int), char (str), alternatives (str),
        word_context (str)
    """
    if not text:
        return []
    indicators = []
    for i, c in enumerate(text):
        if c in _CONFUSION_MAP and _CONFUSION_MAP[c]:
            word_start = max(0, i - 10)
            word_end = min(len(text), i + 11)
            word_context = text[word_start:word_end]
            indicators.append(
                {
                    "position": i,
                    "char": c,
                    "alternatives": "".join(sorted(_CONFUSION_MAP[c])),
                    "word_context": word_context,
                }
            )
    return indicators


def ocr_confusion_score(text: str) -> float:
    """
    Liefert einen Score 0 (unauffällig) bis 1 (viele Verdachtsstellen).

    Basis: Anteil der Zeichen, die in Confusion-Paaren vorkommen,
    gewichtet optional nach Kontext (z. B. mehr Gewicht bei Zahlen).

    Args:
        text: OCR-Text

    Returns:
        Float 0.0-1.0
    """
    if not text or not text.strip():
        return 0.0
    indicators = get_ocr_confusion_indicators(text)
    if not indicators:
        return 0.0
    # Einfach: Anteil der „verdächtigen“ Zeichen an der Gesamtlänge
    # (ohne Leerzeichen/Zeilenumbrüche für Nenner)
    meaningful_len = len(re.sub(r"[\s\n\r]+", "", text))
    if meaningful_len == 0:
        return 0.0
    # Jede Verdachtsposition zählt einmal
    count = len(indicators)
    ratio = count / meaningful_len
    # Auf 0-1 begrenzen (z. B. ab 30 % verdächtig = 1)
    return min(1.0, ratio * 3.0)
