"""
BBox OCR Proof of Concept - Test-Script

Testet BBox-Extraktion mit DeepSeek-OCR für eine einzelne Seite aus der Datenbank.
"""

import argparse
import base64
import json
from pathlib import Path
import re
import sys
import tempfile

from PIL import Image

# Füge src zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from src.rotary_archiv.config import settings  # noqa: E402
from src.rotary_archiv.core.database import SessionLocal  # noqa: E402
from src.rotary_archiv.core.models import Document, DocumentPage  # noqa: E402
from src.rotary_archiv.ocr.ollama_vision import OllamaVisionOCR  # noqa: E402
from src.rotary_archiv.utils.file_handler import get_file_path  # noqa: E402
from src.rotary_archiv.utils.pdf_utils import extract_page_as_image  # noqa: E402


def parse_bbox_json(
    response_text: str, image_width: int = 0, image_height: int = 0
) -> list[dict] | None:
    """
    Parse BBox-Daten aus DeepSeek-OCR Antwort

    Unterstützt verschiedene Formate:
    1. Grounding-Format: <|ref|>text<|/ref|><|det|>[[x1,y1,x2,y2]]<|/det|>
    2. JSON-Format: [{"text": "...", "bbox": [...]}]
    3. JSON in Markdown-Code-Blöcken

    Args:
        response_text: Rohe Antwort von DeepSeek-OCR
        image_width: Bildbreite für Normalisierung (wenn 0, werden Pixel-Koordinaten zurückgegeben)
        image_height: Bildhöhe für Normalisierung (wenn 0, werden Pixel-Koordinaten zurückgegeben)

    Returns:
        Liste von BBox-Objekten oder None wenn Parsing fehlschlägt
    """
    # Format 1: Grounding-Format (<|ref|>text<|/ref|><|det|>[[x1,y1,x2,y2]]<|/det|>)
    if "<|ref|>" in response_text and "<|det|>" in response_text:
        bbox_data = []
        # Pattern: <|ref|>text<|/ref|><|det|>[[x1,y1,x2,y2]]<|/det|>\nactual_text
        pattern = r"<\|ref\|>([^<]*)<\|/ref\|><\|det\|>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]<\|/det\|>\s*\n?([^\n<]*)"
        matches = re.findall(pattern, response_text)

        for match in matches:
            ref_text = match[0].strip()
            x1, y1, x2, y2 = int(match[1]), int(match[2]), int(match[3]), int(match[4])
            actual_text = match[5].strip() if len(match) > 5 else ref_text

            # Verwende actual_text falls vorhanden, sonst ref_text
            text = actual_text if actual_text else ref_text

            # Normalisiere Koordinaten wenn Bild-Dimensionen gegeben
            if image_width > 0 and image_height > 0:
                bbox_normalized = [
                    x1 / image_width,  # x_min (relativ)
                    y1 / image_height,  # y_min (relativ)
                    x2 / image_width,  # x_max (relativ)
                    y2 / image_height,  # y_max (relativ)
                ]
            else:
                bbox_normalized = [x1, y1, x2, y2]  # Pixel-Koordinaten

            bbox_data.append(
                {
                    "text": text,
                    "bbox": bbox_normalized,
                    "bbox_pixel": [x1, y1, x2, y2],  # Original Pixel-Koordinaten
                }
            )

        if bbox_data:
            return bbox_data

    # Format 2: JSON direkt
    try:
        data = json.loads(response_text.strip())
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Format 3: JSON aus Markdown-Code-Blöcken
    code_block_pattern = r"```(?:json)?\s*\n?(.*?)```"
    matches = re.findall(code_block_pattern, response_text, re.DOTALL)
    for match in matches:
        try:
            data = json.loads(match.strip())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            continue

    # Format 4: JSON-Array direkt im Text
    json_array_pattern = r'\[[\s\S]*?\{[\s\S]*?"text"[\s\S]*?\}[\s\S]*?\]'
    matches = re.findall(json_array_pattern, response_text)
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            continue

    return None


def validate_bbox_data(
    bbox_data: list[dict], image_width: int, image_height: int
) -> bool:
    """
    Validiere BBox-Daten

    Args:
        bbox_data: Liste von BBox-Objekten
        image_width: Breite des Bildes
        image_height: Höhe des Bildes

    Returns:
        True wenn Daten valide sind
    """
    if not isinstance(bbox_data, list):
        return False

    for item in bbox_data:
        if not isinstance(item, dict):
            return False
        if "text" not in item or "bbox" not in item:
            return False
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            return False
        # Prüfe ob Koordinaten normalisiert sind (0-1) oder Pixel
        # Beides ist OK
        if not all(isinstance(coord, (int, float)) for coord in bbox):
            return False

    return True


def load_page_image(page: DocumentPage) -> tuple[Image.Image, Path]:
    """
    Lade Bild einer Seite (PDF → Image oder direkt laden)

    Args:
        page: DocumentPage Objekt

    Returns:
        Tuple von (PIL Image, temp_file_path)
    """
    # Hole Dokument für PDF-Pfad falls nötig
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == page.document_id).first()
        if not document:
            raise Exception(f"Dokument {page.document_id} nicht gefunden")
    finally:
        db.close()

    # Wenn Seite bereits ein Bild ist (PNG/JPG)
    if page.file_path and page.file_type in ["png", "jpg", "jpeg"]:
        file_path = get_file_path(page.file_path)
        if file_path.exists():
            image = Image.open(file_path)
            # Erstelle temporäre Kopie für OCR
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            image.save(temp_file.name, "PNG")
            return image, Path(temp_file.name)

    # Wenn Seite ein PDF ist oder file_path None ist, extrahiere aus Dokument-PDF
    pdf_path = get_file_path(document.file_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")

    # Extrahiere Seite als Bild
    image = extract_page_as_image(str(pdf_path), page.page_number)

    # Speichere temporär für OCR
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    image.save(temp_file.name, "PNG")
    return image, Path(temp_file.name)


def main():
    """Hauptfunktion"""
    parser = argparse.ArgumentParser(description="BBox OCR Proof of Concept")
    parser.add_argument(
        "--page-id",
        type=int,
        help="ID der Seite (wenn nicht angegeben, wird erste verfügbare Seite verwendet)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("BBox OCR Proof of Concept")
    print("=" * 60)
    print()

    # Konfiguration anzeigen
    print("Konfiguration:")
    print(f"  Ollama Base URL: {settings.ollama_base_url}")
    print(f"  Ollama Vision Model: {settings.ollama_vision_model}")
    print()

    # Datenbank-Session öffnen
    db = SessionLocal()
    try:
        # Lade Seite
        if args.page_id:
            page = (
                db.query(DocumentPage).filter(DocumentPage.id == args.page_id).first()
            )
            if not page:
                print(f"[FEHLER] Seite mit ID {args.page_id} nicht gefunden")
                return 1
        else:
            # Erste verfügbare Seite laden
            page = db.query(DocumentPage).order_by(DocumentPage.id).first()
            if not page:
                print("[FEHLER] Keine Seiten in der Datenbank gefunden")
                print("  Bitte lade zuerst ein Dokument hoch und extrahiere Seiten")
                return 1

        # Lade Dokument-Info
        document = db.query(Document).filter(Document.id == page.document_id).first()
        if not document:
            print(f"[FEHLER] Dokument {page.document_id} nicht gefunden")
            return 1

        print("Seite geladen:")
        print(f"  ID: {page.id}")
        print(f"  Dokument: {document.filename}")
        print(f"  Seitenzahl: {page.page_number}")
        if page.file_path:
            print(f"  Datei: {page.file_path}")
        print()

        # Lade Bild
        print("Bild wird geladen...")
        try:
            image, temp_image_path = load_page_image(page)
            original_width, original_height = image.size
            print(
                f"Original Bild-Dimensionen: {original_width} x {original_height} Pixel"
            )

            # Reduziere Bildhöhe um 80% (behalte nur obere 20%) für schnelleres Processing
            # Dies reduziert die Anzahl der Tokens und beschleunigt die Verarbeitung
            crop_height = int(original_height * 0.2)  # Behalte nur obere 20% der Höhe
            image = image.crop((0, 0, original_width, crop_height))
            image_width, image_height = image.size
            print(
                f"Gecroppte Bild-Dimensionen: {image_width} x {image_height} Pixel (nur obere 20% behalten)"
            )

            # Speichere gecropptes Bild temporär
            import tempfile

            cropped_temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            image.save(cropped_temp_file.name, "PNG")
            temp_image_path = Path(cropped_temp_file.name)

            # Schritt 1: Speichere Bild-Informationen
            import io

            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            image_size_bytes = len(image_bytes)
            image_size_mb = image_size_bytes / (1024 * 1024)

            step1_file = Path("bbox_ocr_poc_step1_image_info.json")
            step1_data = {
                "page_id": page.id,
                "document_id": document.id,
                "page_number": page.page_number,
                "original_dimensions": {
                    "width": original_width,
                    "height": original_height,
                },
                "cropped_dimensions": {"width": image_width, "height": image_height},
                "image_size_bytes": image_size_bytes,
                "image_size_mb": round(image_size_mb, 2),
                "crop_info": "Nur obere 20% behalten",
            }
            with open(step1_file, "w", encoding="utf-8") as f:
                json.dump(step1_data, f, indent=2, ensure_ascii=False)
            print(f"Schritt 1: Bild-Informationen gespeichert in: {step1_file}")
            print()
        except Exception as e:
            print(f"[FEHLER] Konnte Bild nicht laden: {e}")
            return 1

        # Schritt 2: Bereite Request-Informationen vor
        # Vereinfachter Prompt basierend auf DeepSeek-OCR Dokumentation
        default_bbox_prompt = """<|grounding|>Extract text with bounding boxes."""
        prompt = default_bbox_prompt

        # Lade Bild für Base64-Kodierung
        with open(temp_image_path, "rb") as f:
            image_data = f.read()
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            base64_length = len(image_b64)

        # Berechne Request-Body-Größe (ohne Base64-String für Lesbarkeit)
        request_body_metadata = {
            "model": settings.ollama_vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": ["<BASE64_STRING_PLACEHOLDER>"],
                }
            ],
            "stream": False,
        }
        request_body_size_estimate = (
            len(json.dumps(request_body_metadata).encode("utf-8")) + base64_length
        )

        step2_file = Path("bbox_ocr_poc_step2_request_info.json")
        step2_data = {
            "model": settings.ollama_vision_model,
            "base_url": settings.ollama_base_url,
            "prompt": prompt,
            "prompt_length": len(prompt),
            "base64_length": base64_length,
            "base64_size_mb": round(base64_length / (1024 * 1024), 2),
            "request_body_size_estimate_bytes": request_body_size_estimate,
            "request_body_size_estimate_mb": round(
                request_body_size_estimate / (1024 * 1024), 2
            ),
            "endpoint": "/api/chat",
        }
        with open(step2_file, "w", encoding="utf-8") as f:
            json.dump(step2_data, f, indent=2, ensure_ascii=False)
        print(f"Schritt 2: Request-Informationen gespeichert in: {step2_file}")
        print()

        # OCR mit BBox
        print("OCR mit DeepSeek-OCR...")
        print(f"  Modell: {settings.ollama_vision_model}")
        print("  Prompt: Extract all text with bounding boxes...")
        print("  (Dies kann einige Zeit dauern...)")
        print()

        ollama_vision = OllamaVisionOCR()
        result = ollama_vision.extract_text_with_bbox(str(temp_image_path))

        # Prüfe auf Fehler
        if result.get("error"):
            print(f"[FEHLER] OCR-Fehler: {result['error']}")
            # Speichere auch bei Fehler alle verfügbaren Daten
            step3_file = Path("bbox_ocr_poc_step3_raw_http_response.json")
            step3_data = {
                "error": result.get("error"),
                "status_code": result.get("response_status_code"),
                "headers": result.get("response_headers"),
                "raw_response": result.get("raw_http_response"),
            }
            with open(step3_file, "w", encoding="utf-8") as f:
                json.dump(step3_data, f, indent=2, ensure_ascii=False)
            print(f"Fehler-Daten gespeichert in: {step3_file}")
            return 1

        response_text = result.get("bbox_data", "")
        processing_time_ms = result.get("processing_time_ms", 0)
        result_image_width = result.get("image_width", image_width)
        result_image_height = result.get("image_height", image_height)

        print("[OK] OCR erfolgreich!")
        print(
            f"  Verarbeitungszeit: {processing_time_ms}ms ({processing_time_ms/1000:.1f}s)"
        )
        print()

        # Schritt 3: Speichere vollständige HTTP-Response
        step3_file = Path("bbox_ocr_poc_step3_raw_http_response.json")
        step3_data = {
            "status_code": result.get("response_status_code"),
            "headers": result.get("response_headers"),
            "raw_response": result.get(
                "raw_http_response"
            ),  # Vollständige JSON-Response von Ollama
            "response_text": result.get(
                "response_text"
            ),  # Fallback wenn JSON fehlschlägt
        }
        with open(step3_file, "w", encoding="utf-8") as f:
            json.dump(step3_data, f, indent=2, ensure_ascii=False)
        print(f"Schritt 3: Vollständige HTTP-Response gespeichert in: {step3_file}")
        print()

        # Schritt 4: Speichere extrahierten Content (message.content)
        step4_file = Path("bbox_ocr_poc_step4_parsed_content.txt")
        with open(step4_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("Extrahierter Content (message.content)\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Länge: {len(response_text)} Zeichen\n")
            f.write("\n" + "-" * 60 + "\n")
            f.write("Content:\n")
            f.write("-" * 60 + "\n\n")
            f.write(response_text)
            f.write("\n\n" + "=" * 60 + "\n")
        print(f"Schritt 4: Extrahierter Content gespeichert in: {step4_file}")
        print()

        # Schritt 5: Parse BBox-Daten
        print("Parse BBox-Daten...")
        bbox_data = parse_bbox_json(
            response_text, result_image_width, result_image_height
        )

        step5_file = Path("bbox_ocr_poc_step5_bbox_parsed.json")
        if bbox_data and validate_bbox_data(
            bbox_data, result_image_width, result_image_height
        ):
            print(f"[OK] {len(bbox_data)} BBoxes erfolgreich geparst")
            step5_data = {
                "success": True,
                "bbox_count": len(bbox_data),
                "bbox_data": bbox_data,
            }
        else:
            print("[WARN] BBox-Parsing fehlgeschlagen oder ungültige Daten")
            print("  Rohe Antwort:")
            print("  " + "-" * 56)
            print("  " + "\n  ".join(response_text[:500].split("\n")))
            if len(response_text) > 500:
                print("  ... (gekürzt)")
            print("  " + "-" * 56)
            print()
            bbox_data = None
            step5_data = {
                "success": False,
                "bbox_count": 0,
                "bbox_data": None,
                "parsing_error": "BBox-Parsing fehlgeschlagen",
                "raw_content_preview": response_text[
                    :1000
                ],  # Erste 1000 Zeichen für Analyse
            }

        with open(step5_file, "w", encoding="utf-8") as f:
            json.dump(step5_data, f, indent=2, ensure_ascii=False)
        print(f"Schritt 5: BBox-Parsing-Ergebnis gespeichert in: {step5_file}")
        print()

        # Extrahiere Text aus BBox-Daten oder verwende rohe Antwort
        if bbox_data:
            extracted_text = " ".join([item.get("text", "") for item in bbox_data])
        else:
            # Versuche Text aus roher Antwort zu extrahieren
            extracted_text = response_text

        # Ergebnisse anzeigen
        print("Ergebnisse:")
        print("  " + "-" * 56)
        print(f"  Text-Länge: {len(extracted_text)} Zeichen")
        if bbox_data:
            print(f"  Erkannte BBoxes: {len(bbox_data)}")
        print()

        # Text-Ausschnitt
        print("Text-Ausschnitt (erste 300 Zeichen):")
        print("  " + "-" * 56)
        text_preview = extracted_text[:300].replace("\n", " ")
        print(f"  {text_preview}")
        if len(extracted_text) > 300:
            print("  ...")
        print("  " + "-" * 56)
        print()

        # Beispiel-BBoxes
        if bbox_data:
            print("Beispiel-BBoxes (erste 10):")
            print("  " + "-" * 56)
            for i, item in enumerate(bbox_data[:10], 1):
                text = item.get("text", "")
                bbox = item.get("bbox", [])
                confidence = item.get("confidence")
                bbox_str = ", ".join([f"{coord:.4f}" for coord in bbox])
                conf_str = f" | Confidence: {confidence:.2f}" if confidence else ""
                print(
                    f"  {i}. Text: \"{text[:30]}{'...' if len(text) > 30 else ''}\" | BBox: [{bbox_str}]{conf_str}"
                )
            if len(bbox_data) > 10:
                print(f"  ... ({len(bbox_data) - 10} weitere)")
            print("  " + "-" * 56)
            print()

        # Speichere vollständige Antwort in Datei (optional)
        output_file = Path("bbox_ocr_poc_result.json")
        output_data = {
            "page_id": page.id,
            "document_id": document.id,
            "page_number": page.page_number,
            "image_width": result_image_width,
            "image_height": result_image_height,
            "processing_time_ms": processing_time_ms,
            "text": extracted_text,
            "bbox_count": len(bbox_data) if bbox_data else 0,
            "bbox_data": bbox_data if bbox_data else None,
            "raw_response": response_text,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Vollständige Ergebnisse gespeichert in: {output_file}")
        print()

    except KeyboardInterrupt:
        print("\n[ABGEBROCHEN] Durch Benutzer abgebrochen")
        return 1
    except Exception as e:
        print(f"[FEHLER] Unerwarteter Fehler: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()
        # Lösche temporäre Datei
        try:
            if "temp_image_path" in locals() and temp_image_path.exists():
                temp_image_path.unlink()
        except Exception:
            pass

    print("[OK] Test abgeschlossen!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
