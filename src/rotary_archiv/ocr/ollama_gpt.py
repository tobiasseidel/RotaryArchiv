"""
Ollama GPT für OCR-Korrektur und Annotation-Support
"""

from typing import Any

import httpx

from src.rotary_archiv.config import settings


class OllamaGPT:
    """Ollama GPT Wrapper für Text-Korrektur und Annotation"""

    def __init__(self):
        """Initialisiere Ollama GPT"""
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_gpt_model

    def correct_ocr_errors(
        self, text: str, context: str | None = None
    ) -> dict[str, Any]:
        """
        Korrigiere OCR-Fehler mit GPT

        Args:
            text: OCR-Text mit möglichen Fehlern
            context: Optional: Kontext (z.B. Dokument-Typ, Datum)

        Returns:
            Dict mit korrigiertem Text und Änderungen
        """
        prompt = f"""Du bist ein Experte für OCR-Fehlerkorrektur.
Korrigiere den folgenden OCR-Text. Behalte die ursprüngliche Struktur und Formatierung bei.
Gib nur den korrigierten Text zurück, keine Erklärungen.

{f"Kontext: {context}" if context else ""}

OCR-Text:
{text}"""

        try:
            corrected_text = self._generate(prompt)
            return {
                "corrected_text": corrected_text,
                "original_text": text,
                "model": self.model,
            }
        except Exception as e:
            return {
                "corrected_text": text,  # Fallback: Original
                "original_text": text,
                "error": str(e),
            }

    def compare_ocr_results(
        self, tesseract_text: str, ollama_text: str
    ) -> dict[str, Any]:
        """
        Vergleiche zwei OCR-Ergebnisse und erstelle bestes Ergebnis

        Args:
            tesseract_text: Tesseract OCR Ergebnis
            ollama_text: Ollama Vision OCR Ergebnis

        Returns:
            Dict mit kombiniertem/korrigiertem Text und Analyse
        """
        prompt = f"""Du bist ein Experte für OCR-Ergebnisse.
Ich habe zwei OCR-Ergebnisse für dasselbe Dokument:
1. Tesseract OCR
2. Ollama Vision OCR

Analysiere beide Texte und erstelle einen kombinierten, korrigierten Text der die besten Teile beider Ergebnisse nutzt.
Gib nur den finalen Text zurück, keine Erklärungen.

Tesseract OCR:
{tesseract_text}

Ollama Vision OCR:
{ollama_text}"""

        try:
            combined_text = self._generate(prompt)
            return {
                "combined_text": combined_text,
                "tesseract_text": tesseract_text,
                "ollama_text": ollama_text,
                "model": self.model,
            }
        except Exception as e:
            # Fallback: Nutze längeren Text
            best_text = (
                tesseract_text
                if len(tesseract_text) > len(ollama_text)
                else ollama_text
            )
            return {
                "combined_text": best_text,
                "tesseract_text": tesseract_text,
                "ollama_text": ollama_text,
                "error": str(e),
            }

    def find_annotations(self, text: str, query: str) -> list[dict[str, Any]]:
        """
        Finde relevante Stellen im Text für Annotationen

        Args:
            text: Dokument-Text
            query: Suchanfrage

        Returns:
            Liste von relevanten Textstellen mit Positionen
        """
        prompt = f"""Finde alle Stellen im folgenden Text, die relevant für die Suchanfrage sind.
Gib für jede relevante Stelle an:
- Den Text-Ausschnitt (ca. 100-200 Zeichen)
- Warum es relevant ist

Suchanfrage: {query}

Text:
{text}"""

        try:
            result = self._generate(prompt)
            # Parse Ergebnis (einfache Implementierung)
            # In Produktion könnte man strukturierte Ausgabe verwenden
            return [{"text": result, "query": query, "model": self.model}]
        except Exception as e:
            return [{"error": str(e)}]

    def _generate(self, prompt: str) -> str:
        """
        Generiere Text mit Ollama GPT

        Args:
            prompt: Prompt für GPT

        Returns:
            Generierter Text
        """
        try:
            # Timeout konfigurierbar: connect=10s, read/write=konfigurierbar (Standard: 10 Min)
            timeout = httpx.Timeout(
                connect=10.0,
                read=settings.ollama_timeout_seconds,
                write=settings.ollama_timeout_seconds,
                pool=10.0,
            )
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.TimeoutException as e:
            raise Exception(
                f"Ollama GPT Timeout nach {settings.ollama_timeout_seconds}s: {e}"
            ) from e
        except Exception as e:
            raise Exception(f"Ollama GPT Fehler: {e}") from e
