"""
Ollama Vision OCR Implementation
"""

import base64
import io
import logging
from pathlib import Path
import re
import time
from typing import Any

import httpx
from PIL import Image

from src.rotary_archiv.config import settings

logger = logging.getLogger(__name__)


class OllamaVisionOCR:
    """Ollama Vision OCR Wrapper"""

    def __init__(self):
        """Initialisiere Ollama Vision OCR"""
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_vision_model

    def _image_to_base64(self, image_path: Path) -> str | None:
        """
        Konvertiere Bild zu Base64

        Args:
            image_path: Pfad zum Bild

        Returns:
            Base64-String oder None
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
                return base64.b64encode(image_data).decode("utf-8")
        except Exception:
            return None

    def _pdf_to_images(self, pdf_path: Path) -> list[Image.Image]:
        """
        Konvertiere PDF zu Bilder

        Args:
            pdf_path: Pfad zur PDF

        Returns:
            Liste von PIL Images
        """
        try:
            from pdf2image import convert_from_path

            # Verwende benutzerdefinierten Poppler-Pfad falls konfiguriert
            convert_kwargs = {}
            if settings.poppler_path:
                poppler_path = Path(settings.poppler_path)
                if poppler_path.exists():
                    convert_kwargs["poppler_path"] = str(poppler_path)

            return convert_from_path(str(pdf_path), **convert_kwargs)
        except Exception:
            return []

    def extract_text(
        self,
        file_path: str,
        prompt: str = "Extract all text from this image. Return only the text, no explanations.",
    ) -> dict[str, Any]:
        """
        Extrahiere Text aus Datei mit Ollama Vision

        Args:
            file_path: Pfad zur Datei
            prompt: Prompt für Vision Model

        Returns:
            Dict mit 'text', 'engine_version', 'processing_time_ms' und Metadaten
        """
        start_time = time.time()
        file_path_obj = Path(file_path)

        try:
            if file_path_obj.suffix.lower() == ".pdf":
                # PDF zu Bilder konvertieren
                images = self._pdf_to_images(file_path_obj)
                texts = []

                for image in images:
                    # Konvertiere PIL Image zu Base64
                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                    text = self._process_image(image_b64, prompt)
                    texts.append(text)

                full_text = "\n\n".join(texts)

            else:
                # Bild-Datei direkt verarbeiten
                image_b64 = self._image_to_base64(file_path_obj)
                if not image_b64:
                    raise Exception("Konnte Bild nicht laden")

                full_text = self._process_image(image_b64, prompt)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "text": full_text.strip(),
                "confidence": None,  # Ollama Vision gibt keine Confidence
                "engine": "ollama_vision",
                "engine_version": self.model,  # Model-Name als engine_version
                "processing_time_ms": processing_time_ms,
            }

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return {
                "text": "",
                "confidence": None,
                "engine": "ollama_vision",
                "error": str(e),
                "processing_time_ms": processing_time_ms,
            }

    def _process_image(self, image_b64: str, prompt: str) -> str:
        """
        Verarbeite einzelnes Bild mit Ollama Vision

        Args:
            image_b64: Base64-kodiertes Bild (ohne Newlines)
            prompt: Prompt für Vision Model

        Returns:
            Extrahierter Text
        """
        result = self._process_image_full(image_b64, prompt)
        return result.get("content", "")

    def _process_image_full(self, image_b64: str, prompt: str) -> dict[str, Any]:
        """
        Verarbeite einzelnes Bild mit Ollama Vision und gib vollständige Response zurück

        Args:
            image_b64: Base64-kodiertes Bild (ohne Newlines)
            prompt: Prompt für Vision Model

        Returns:
            Dict mit:
            - 'content': Extrahierter Text (message.content)
            - 'raw_response': Vollständige HTTP-Response als Dict
            - 'response_text': Roher Response-Text (falls JSON-Parsing fehlschlägt)
            - 'status_code': HTTP Status Code
            - 'headers': Response Headers als Dict
        """
        try:
            # Entferne Newlines aus Base64-String (laut Ollama-Dokumentation erforderlich)
            image_b64_clean = image_b64.replace("\n", "").replace("\r", "")

            # Timeout konfigurierbar: connect=10s, read/write=konfigurierbar (Standard: 10 Min)
            timeout = httpx.Timeout(
                connect=10.0,
                read=settings.ollama_timeout_seconds,
                write=settings.ollama_timeout_seconds,
                pool=10.0,
            )
            
            logger.info(
                f"[OCR-LLM] Starte HTTP-Request zu {self.base_url}/api/chat, "
                f"Model: {self.model}, Timeout: {settings.ollama_timeout_seconds}s, "
                f"Bildgröße (Base64): {len(image_b64_clean)} Zeichen"
            )
            request_start_time = time.time()
            
            with httpx.Client(timeout=timeout) as client:
                # Verwende /api/chat für Vision-Modelle (z.B. deepseek-ocr)
                # Laut Dokumentation: images Array gehört INSIDE das message-Objekt
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt,
                                "images": [image_b64_clean],
                            }
                        ],
                        "stream": False,
                    },
                )
                
                request_duration = time.time() - request_start_time
                logger.info(
                    f"[OCR-LLM] HTTP-Request abgeschlossen nach {request_duration:.2f}s, "
                    f"Status: {response.status_code}"
                )
                
                response.raise_for_status()

                # Versuche JSON zu parsen
                try:
                    data = response.json()
                    # Chat-API gibt Antwort in message.content zurück
                    message = data.get("message", {})
                    content = message.get("content", "")

                    return {
                        "content": content,
                        "raw_response": data,  # Vollständige Response-Struktur
                        "response_text": None,  # Nicht nötig wenn JSON erfolgreich
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                    }
                except Exception:
                    # Fallback: Wenn JSON-Parsing fehlschlägt, speichere rohen Text
                    return {
                        "content": response.text,
                        "raw_response": None,
                        "response_text": response.text,
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                    }
        except httpx.TimeoutException as e:
            elapsed_time = time.time() - request_start_time if 'request_start_time' in locals() else 0
            logger.error(
                f"[OCR-LLM] Ollama Vision Timeout nach {elapsed_time:.2f}s "
                f"(konfiguriert: {settings.ollama_timeout_seconds}s): {e}"
            )
            raise Exception(
                f"Ollama Vision Timeout nach {elapsed_time:.2f}s "
                f"(konfiguriert: {settings.ollama_timeout_seconds}s): {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            # Detaillierte Fehlerinformationen für HTTP-Fehler
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail += f": {error_body}"
            except Exception:
                error_detail += f": {e.response.text[:500]}"
            raise Exception(f"Ollama Vision Fehler: {error_detail}") from e
        except Exception as e:
            raise Exception(f"Ollama Vision Fehler: {e}") from e

    def _parse_grounding_format(
        self, response_text: str, image_width: int, image_height: int
    ) -> list[dict[str, Any]] | None:
        """
        Parse Bounding Boxes aus DeepSeek-OCR Grounding-Format

        Format: <|ref|>text<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>
                actual_text

        Args:
            response_text: Rohe Antwort von DeepSeek-OCR
            image_width: Bildbreite für Normalisierung
            image_height: Bildhöhe für Normalisierung

        Returns:
            Liste von BBox-Objekten oder None wenn Parsing fehlschlägt
        """
        if not response_text:
            logger.warning("[OCR-LLM] _parse_grounding_format: Leere Response")
            return None
            
        has_ref_tag = "<|ref|>" in response_text
        has_det_tag = "<|det|>" in response_text
        
        if not has_ref_tag or not has_det_tag:
            logger.warning(
                f"[OCR-LLM] _parse_grounding_format: Grounding-Format nicht gefunden. "
                f"<|ref|> vorhanden: {has_ref_tag}, <|det|> vorhanden: {has_det_tag}, "
                f"Response-Länge: {len(response_text)} Zeichen, "
                f"Erste 500 Zeichen: {response_text[:500]}"
            )
            return None

        bbox_data = []
        # Pattern: <|ref|>text<|/ref|><|det|>[[x1,y1,x2,y2]]<|/det|>\nactual_text
        pattern = r"<\|ref\|>([^<]*)<\|/ref\|><\|det\|>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]<\|/det\|>\s*\n?([^\n<]*)"
        matches = re.findall(pattern, response_text)
        
        logger.info(
            f"[OCR-LLM] _parse_grounding_format: Pattern-Matches gefunden: {len(matches)}"
        )
        
        # Warnung wenn sehr viele Matches (könnte auf OCR-Problem hinweisen)
        if len(matches) > 100:
            logger.warning(
                f"[OCR-LLM] _parse_grounding_format: Sehr viele Matches ({len(matches)}), "
                f"könnte auf OCR-Problem hinweisen. Bildgröße: {image_width}x{image_height}"
            )
        
        # Wenn keine Matches, versuche alternative Patterns
        if len(matches) == 0:
            # Versuche Pattern ohne Newline nach </det>
            pattern2 = r"<\|ref\|>([^<]*)<\|/ref\|><\|det\|>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]<\|/det\|>([^<]*)"
            matches2 = re.findall(pattern2, response_text)
            logger.info(
                f"[OCR-LLM] _parse_grounding_format: Alternative Pattern-Matches: {len(matches2)}"
            )
            if len(matches2) > 0:
                matches = matches2

        for idx, match in enumerate(matches):
            ref_text = match[0].strip()
            x1, y1, x2, y2 = int(match[1]), int(match[2]), int(match[3]), int(match[4])

            # Logge nur erste 10 Boxen im Detail, dann nur noch Warnungen
            if idx < 10:
                logger.info(
                    f"[OCR-LLM] Box {idx}: Rohe Pixel-Koordinaten vom LLM: "
                    f"[{x1}, {y1}, {x2}, {y2}], "
                    f"Bildgröße für Normalisierung: {image_width}x{image_height}, "
                    f"Text: '{ref_text[:50]}'"
                )

            # Filtere offensichtlich ungültige Boxen früh (alle Koordinaten = 0)
            if x1 == 0 and y1 == 0 and x2 == 0 and y2 == 0:
                if idx < 10:  # Logge nur erste 10
                    logger.warning(
                        f"[OCR-LLM] Box {idx}: Alle Koordinaten = 0, überspringe"
                    )
                continue

            # Versuche ungültige Boxen zu reparieren
            # Wenn y1=y2 (keine Höhe), versuche die Box zu reparieren
            if y1 == y2:
                if y1 == 0 and image_height > 0:
                    # OCR-LLM hat möglicherweise y2=0 zurückgegeben, obwohl Text vorhanden ist
                    # Versuche y2 auf die Bildhöhe zu setzen
                    if idx < 10:  # Logge nur erste 10
                        logger.warning(
                            f"[OCR-LLM] Box {idx}: Ungültige Y-Koordinaten (y1=y2=0), "
                            f"versuche zu reparieren: y2={image_height}"
                        )
                    y2 = image_height
                else:
                    # y1=y2 aber nicht 0 - kann nicht repariert werden
                    if idx < 10:  # Logge nur erste 10
                        logger.warning(
                            f"[OCR-LLM] Box {idx}: Ungültige Y-Koordinaten (y1=y2={y1}), überspringe"
                        )
                    continue
            
            # Wenn x1=x2 (keine Breite), versuche zu reparieren
            if x1 == x2:
                if x1 == 0 and image_width > 0:
                    # Versuche x2 auf die Bildbreite zu setzen
                    if idx < 10:  # Logge nur erste 10
                        logger.warning(
                            f"[OCR-LLM] Box {idx}: Ungültige X-Koordinaten (x1=x2=0), "
                            f"versuche zu reparieren: x2={image_width}"
                        )
                    x2 = image_width
                else:
                    # x1=x2 aber nicht 0 - kann nicht repariert werden
                    if idx < 10:  # Logge nur erste 10
                        logger.warning(
                            f"[OCR-LLM] Box {idx}: Ungültige X-Koordinaten (x1=x2={x1}), überspringe"
                        )
                    continue
            
            # Ungültige Boxen (x1>=x2 oder y1>=y2 nach Reparatur) vom Modell nicht speichern
            if x1 >= x2 or y1 >= y2:
                if idx < 10:  # Logge nur erste 10
                    logger.warning(
                        f"[OCR-LLM] Box {idx}: Ungültige Koordinaten (x1>=x2 oder y1>=y2), "
                        f"Box: [{x1}, {y1}, {x2}, {y2}], Bild: {image_width}x{image_height}, überspringe"
                    )
                continue

            # Prüfe ob Pixel-Koordinaten außerhalb Bildgröße liegen
            if x2 > image_width or y2 > image_height:
                logger.warning(
                    f"[OCR-LLM] Box {idx}: Pixel-Koordinaten außerhalb Bildgröße! "
                    f"Box: [{x1}, {y1}, {x2}, {y2}], Bild: {image_width}x{image_height}, "
                    f"Abweichungen: x2 um {x2 - image_width} Pixel, y2 um {y2 - image_height} Pixel"
                )

            actual_text = (
                match[5].strip() if len(match) > 5 and match[5].strip() else ref_text
            )

            # Verwende actual_text falls vorhanden, sonst ref_text
            text = actual_text if actual_text else ref_text

            # Normalisiere Koordinaten (0.0-1.0)
            if image_width > 0 and image_height > 0:
                bbox_normalized = [
                    x1 / image_width,  # x_min (relativ)
                    y1 / image_height,  # y_min (relativ)
                    x2 / image_width,  # x_max (relativ)
                    y2 / image_height,  # y_max (relativ)
                ]
                
                # Logge Normalisierung
                logger.info(
                    f"[OCR-LLM] Box {idx}: Normalisiert: "
                    f"Pixel=[{x1}, {y1}, {x2}, {y2}] → "
                    f"Normalized=[{bbox_normalized[0]:.4f}, {bbox_normalized[1]:.4f}, "
                    f"{bbox_normalized[2]:.4f}, {bbox_normalized[3]:.4f}], "
                    f"Werte > 1.0: x2={bbox_normalized[2] > 1.0}, y2={bbox_normalized[3] > 1.0}"
                )
            else:
                bbox_normalized = [x1, y1, x2, y2]  # Pixel-Koordinaten als Fallback
                logger.warning(
                    f"[OCR-LLM] Box {idx}: Keine Bildgröße verfügbar, verwende Pixel-Koordinaten"
                )

            bbox_data.append(
                {
                    "text": text,
                    "bbox": bbox_normalized,  # [x_min_rel, y_min_rel, x_max_rel, y_max_rel]
                    "bbox_pixel": [x1, y1, x2, y2],  # Original Pixel-Koordinaten
                }
            )

        return bbox_data if bbox_data else None

    def extract_text_with_bbox(
        self,
        file_path: str,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Extrahiere Text mit Bounding Boxes aus Datei (PoC)

        Args:
            file_path: Pfad zur Datei
            prompt: Optionaler Prompt (Standard-BBox-Prompt wird verwendet wenn None)

        Returns:
            Dict mit 'text', 'bbox_data' (rohe JSON-String),
            'image_width', 'image_height', 'processing_time_ms'
        """
        # Prompt basierend auf DeepSeek-OCR Dokumentation
        # Für BBox verwenden wir grounding-Tag mit einfacher Anweisung
        # WICHTIG: Prompt muss kurz sein, sonst wiederholt das OCR-LLM nur den Prompt
        default_bbox_prompt = "<|grounding|>Extract text with bounding boxes."

        start_time = time.time()
        file_path_obj = Path(file_path)

        try:
            # Lade Bild und ermittle Dimensionen
            if file_path_obj.suffix.lower() == ".pdf":
                # PDF zu Bild konvertieren (nur erste Seite)
                images = self._pdf_to_images(file_path_obj)
                if not images:
                    raise Exception("Konnte PDF nicht zu Bild konvertieren")
                image = images[0]
            else:
                # Bild-Datei direkt laden
                image = Image.open(file_path_obj)

            image_width, image_height = image.size
            
            # Verwende Standard-Prompt wenn keiner angegeben
            # WICHTIG: Prompt nicht erweitern, da lange Prompts dazu führen, dass OCR-LLM nur den Prompt wiederholt
            if prompt is None:
                prompt = default_bbox_prompt
            logger.info(
                f"[OCR-LLM] Bild geladen: {file_path}, "
                f"Original-Größe: {image_width}x{image_height} Pixel"
            )

            # Konvertiere PIL Image zu Base64
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            # Bildgröße prüfen und ggf. verkleinern
            # DeepSeek-OCR hat ein 8K Context-Window, große Bilder können Probleme verursachen
            # Aggressiveres Resizing für BBox-OCR um Context-Window-Fehler zu vermeiden
            image_size_mb = len(image_bytes) / (1024 * 1024)
            max_size = (
                1000  # Reduziert von 1500 auf 1000 für BBox-OCR (Context-Window-Limit)
            )
            max_size_mb = 2  # Reduziert von 5MB auf 2MB für BBox-OCR

            # Resize wenn Bild zu groß ist (Dimensionen oder Dateigröße)
            # WICHTIG: Resize IMMER für BBox-OCR, da Context-Window sehr begrenzt ist
            if (
                image_size_mb > max_size_mb
                or image_width > max_size
                or image_height > max_size
            ):
                ratio = min(max_size / image_width, max_size / image_height, 1.0)
                new_width = int(image_width * ratio)
                new_height = int(image_height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                image_width, image_height = image.size
                logger.info(
                    f"[OCR-LLM] Bild resized: {new_width}x{new_height} Pixel "
                    f"(Ratio: {ratio:.3f}, Dateigröße: {image_size_mb:.2f}MB → "
                    f"{len(image_bytes) / (1024 * 1024):.2f}MB nach Resize)"
                )
                # Neu kodieren nach Resize - verwende JPEG mit niedriger Qualität für kleinere Dateigröße
                buffer = io.BytesIO()
                # Konvertiere RGBA zu RGB falls nötig (JPEG unterstützt kein Alpha)
                if image.mode in ("RGBA", "LA", "P"):
                    rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "P":
                        image = image.convert("RGBA")
                    rgb_image.paste(
                        image, mask=image.split()[-1] if image.mode == "RGBA" else None
                    )
                    image = rgb_image
                # Speichere als JPEG mit 85% Qualität für kleinere Dateigröße
                image.save(buffer, format="JPEG", quality=85, optimize=True)
                image_bytes = buffer.getvalue()
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                image_size_mb = len(image_bytes) / (1024 * 1024)

            # Berechne Request-Metadaten vor dem Request
            base64_length = len(image_b64)
            request_body = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [
                            "<BASE64_STRING>"
                        ],  # Platzhalter für Größenberechnung
                    }
                ],
                "stream": False,
            }
            import json as json_module

            request_body_size_estimate = (
                len(json_module.dumps(request_body).encode("utf-8")) + base64_length
            )

            # Verarbeite Bild mit Ollama (vollständige Response)
            response_data = self._process_image_full(image_b64, prompt)
            response_text = response_data.get("content", "")

            # Logge rohe OCR-Antwort (erste 1000 Zeichen für Debugging)
            logger.info(
                f"[OCR-LLM] Rohe OCR-Antwort (erste 1000 Zeichen): {response_text[:1000]}"
            )
            logger.info(
                f"[OCR-LLM] Rohe OCR-Antwort (letzte 1000 Zeichen): {response_text[-1000:]}"
            )
            
            # Prüfe, ob Grounding-Format vorhanden ist
            has_ref_tag = "<|ref|>" in response_text
            has_det_tag = "<|det|>" in response_text
            logger.info(
                f"[OCR-LLM] Grounding-Format-Check: <|ref|> vorhanden: {has_ref_tag}, "
                f"<|det|> vorhanden: {has_det_tag}"
            )
            
            logger.info(
                f"[OCR-LLM] Parse BBoxes: Bildgröße für Normalisierung: {image_width}x{image_height}, "
                f"Response-Länge: {len(response_text)} Zeichen"
            )
            bbox_list = self._parse_grounding_format(
                response_text, image_width, image_height
            )
            logger.info(
                f"[OCR-LLM] Parse Ergebnis: {len(bbox_list) if bbox_list else 0} Boxen erkannt"
            )

            # Extrahiere Text aus BBox-Daten oder verwende rohe Antwort
            if bbox_list:
                extracted_text = " ".join([item.get("text", "") for item in bbox_list])
            else:
                extracted_text = response_text.strip()

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "text": extracted_text,
                "bbox_data": response_text.strip(),  # Rohe Antwort (Grounding-Format)
                "bbox_list": bbox_list,  # Geparste BBox-Liste (None wenn Parsing fehlschlägt)
                "image_width": image_width,
                "image_height": image_height,
                "engine": "ollama_vision",
                "engine_version": self.model,
                "processing_time_ms": processing_time_ms,
                # Neue Felder für Debugging
                "raw_http_response": response_data.get(
                    "raw_response"
                ),  # Vollständige HTTP-Response
                "request_body_size": request_body_size_estimate,
                "base64_length": base64_length,
                "response_status_code": response_data.get("status_code"),
                "response_headers": response_data.get("headers"),
                "response_text": response_data.get(
                    "response_text"
                ),  # Fallback wenn JSON fehlschlägt
            }

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return {
                "text": "",
                "bbox_data": "",
                "image_width": 0,
                "image_height": 0,
                "engine": "ollama_vision",
                "error": str(e),
                "processing_time_ms": processing_time_ms,
            }
