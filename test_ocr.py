"""Test-Script für OCR-Anbindungen"""
import asyncio
from pathlib import Path
import sys
import time

import httpx

# Füge src zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from src.rotary_archiv.config import settings
from src.rotary_archiv.ocr.ollama_gpt import OllamaGPT
from src.rotary_archiv.ocr.ollama_vision import OllamaVisionOCR
from src.rotary_archiv.ocr.tesseract import TesseractOCR


async def test_tesseract():
    """Teste Tesseract OCR"""
    print("\n=== Tesseract OCR Test ===")
    print(f"Tesseract Command: {settings.tesseract_cmd}")

    try:
        tesseract = TesseractOCR()

        # Test mit einer vorhandenen Seite aus documents/pages (falls vorhanden)
        pages_dir = Path("data/documents/pages")
        test_files = list(pages_dir.glob("*.pdf"))[:1] if pages_dir.exists() else []

        if not test_files:
            # Fallback zu documents falls pages leer ist
            test_files = list(Path("data/documents").glob("*.pdf"))[:1]

        if not test_files:
            print("[WARN] Keine PDF-Dateien zum Testen gefunden")
            print("   Bitte lade zuerst ein Dokument hoch oder extrahiere Seiten")
            return False

        test_file = test_files[0]
        source_info = "pages" if "pages" in str(test_file) else "documents"
        print(f"Teste mit: {test_file.name} (aus {source_info}/)")

        result = tesseract.extract_text(str(test_file), language="deu+eng")

        if result.get("error"):
            print(f"[FEHLER] Fehler: {result['error']}")
            return False

        text = result.get("text", "")
        confidence = result.get("confidence", 0)
        processing_time = result.get("processing_time_ms", 0)

        print("[OK] Erfolgreich!")
        print(f"  Text-Länge: {len(text)} Zeichen")
        print(f"  Confidence: {confidence:.2f}%" if confidence else "  Confidence: N/A")
        print(f"  Verarbeitungszeit: {processing_time}ms")
        print("  Text-Ausschnitt (erste 200 Zeichen):")
        print(f"  {text[:200]}...")

        return True

    except Exception as e:
        print(f"[FEHLER] Fehler: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_ollama_vision():
    """Teste Ollama Vision OCR"""
    print("\n=== Ollama Vision OCR Test ===")
    print(f"Ollama Base URL: {settings.ollama_base_url}")
    print(f"Ollama Vision Model: {settings.ollama_vision_model}")

    try:
        ollama_vision = OllamaVisionOCR()

        # Test mit einer vorhandenen Seite aus documents/pages (falls vorhanden)
        pages_dir = Path("data/documents/pages")
        test_files = list(pages_dir.glob("*.pdf"))[:1] if pages_dir.exists() else []

        if not test_files:
            # Fallback zu documents falls pages leer ist
            test_files = list(Path("data/documents").glob("*.pdf"))[:1]

        if not test_files:
            print("[WARN] Keine PDF-Dateien zum Testen gefunden")
            print("   Bitte lade zuerst ein Dokument hoch oder extrahiere Seiten")
            return False

        test_file = test_files[0]
        source_info = "pages" if "pages" in str(test_file) else "documents"
        print(f"Teste mit: {test_file.name} (aus {source_info}/)")
        print("  (Dies kann einige Zeit dauern...)")

        result = ollama_vision.extract_text(str(test_file))

        if result.get("error"):
            error_msg = result["error"]
            if "timeout" in error_msg.lower() or "Timeout" in error_msg:
                print(f"[FEHLER] Timeout: {error_msg}")
                print(
                    f"  Hinweis: Ollama benötigt mehr Zeit. Timeout ist aktuell auf {settings.ollama_timeout_seconds}s gesetzt."
                )
                print(
                    "  Du kannst OLLAMA_TIMEOUT_SECONDS in .env erhöhen (z.B. 1200 für 20 Minuten)"
                )
            else:
                print(f"[FEHLER] Fehler: {error_msg}")
            return False

        text = result.get("text", "")
        processing_time = result.get("processing_time_ms", 0)

        print("[OK] Erfolgreich!")
        print(f"  Text-Länge: {len(text)} Zeichen")
        print(f"  Verarbeitungszeit: {processing_time}ms ({processing_time/1000:.1f}s)")
        print("  Text-Ausschnitt (erste 200 Zeichen):")
        print(f"  {text[:200]}...")

        return True

    except Exception as e:
        print(f"[FEHLER] Fehler: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_ollama_gpt():
    """Teste Ollama GPT für Text-Korrektur"""
    print("\n=== Ollama GPT Test ===")
    print(f"Ollama GPT Model: {settings.ollama_gpt_model}")

    try:
        ollama_gpt = OllamaGPT()

        # Test mit Beispieltext
        test_text = "Dies ist ein Test-Text mit möglichen OCR-Fehlern wie 'rn' statt 'm' oder '0' statt 'O'."

        print(f"Teste mit Beispieltext: {test_text}")
        print("  (Dies kann einige Zeit dauern...)")

        result = ollama_gpt.correct_ocr_errors(test_text)

        if result.get("error"):
            error_msg = result["error"]
            if "timeout" in error_msg.lower() or "Timeout" in error_msg:
                print(f"[FEHLER] Timeout: {error_msg}")
                print(
                    f"  Hinweis: Ollama benötigt mehr Zeit. Timeout ist aktuell auf {settings.ollama_timeout_seconds}s gesetzt."
                )
                print(
                    "  Du kannst OLLAMA_TIMEOUT_SECONDS in .env erhöhen (z.B. 1200 für 20 Minuten)"
                )
            else:
                print(f"[FEHLER] Fehler: {error_msg}")
            return False

        corrected_text = result.get("corrected_text", "")

        print("[OK] Erfolgreich!")
        print(f"  Original: {test_text}")
        print(f"  Korrigiert: {corrected_text}")

        return True

    except Exception as e:
        print(f"[FEHLER] Fehler: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_job_system():
    """Teste OCR-Job-System über API"""
    print("\n=== OCR Job-System Test ===")
    print("API Base URL: http://localhost:8000")

    try:
        # Prüfe ob Backend läuft
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get("http://localhost:8000/health")
                if response.status_code != 200:
                    print(
                        "[INFO] Backend läuft nicht oder nicht erreichbar - überspringe Job-Test"
                    )
                    return None
            except Exception:
                print(
                    "[INFO] Backend läuft nicht oder nicht erreichbar - überspringe Job-Test"
                )
                return None

            # Hole Liste der Dokumente
            response = await client.get("http://localhost:8000/api/documents/")
            if response.status_code != 200:
                print("[FEHLER] Konnte Dokumente nicht abrufen")
                return False

            documents = response.json()
            if not documents:
                print("[INFO] Keine Dokumente in der Datenbank - überspringe Job-Test")
                return None

            # Verwende erstes Dokument
            test_doc = documents[0]
            doc_id = test_doc["id"]
            print(
                f"Teste mit Dokument: {test_doc.get('filename', f'Doc #{doc_id}')} (ID: {doc_id})"
            )

            # Erstelle Job
            print("  Erstelle OCR-Job...")
            response = await client.post(
                f"http://localhost:8000/api/ocr/documents/{doc_id}/jobs",
                json={"language": "deu+eng", "use_correction": True},
            )

            if response.status_code != 200:
                error_detail = response.json().get(
                    "detail", f"HTTP {response.status_code}"
                )
                print(f"[FEHLER] Job-Erstellung fehlgeschlagen: {error_detail}")
                return False

            job_data = response.json()
            job_id = job_data["id"]
            print(f"  [OK] Job erstellt: ID {job_id}, Status: {job_data['status']}")

            # Polling für Job-Status
            print("  Warte auf Job-Abschluss (max. 5 Minuten)...")
            max_wait_time = 5 * 60  # 5 Minuten
            start_time = time.time()
            poll_interval = 2  # 2 Sekunden

            while time.time() - start_time < max_wait_time:
                await asyncio.sleep(poll_interval)

                response = await client.get(
                    f"http://localhost:8000/api/ocr/jobs/{job_id}"
                )
                if response.status_code != 200:
                    print(
                        f"[FEHLER] Konnte Job-Status nicht abrufen: HTTP {response.status_code}"
                    )
                    return False

                job_data = response.json()
                status = job_data["status"]
                progress = job_data.get("progress", 0)
                current_step = job_data.get("current_step", "")

                print(f"  Status: {status}, Fortschritt: {progress:.1f}%", end="")
                if current_step:
                    print(f", Schritt: {current_step}")
                else:
                    print()

                if status == "completed":
                    print("  [OK] Job erfolgreich abgeschlossen!")
                    print(f"  Verarbeitungszeit: {job_data.get('completed_at', 'N/A')}")
                    return True
                elif status == "failed":
                    error_msg = job_data.get("error_message", "Unbekannter Fehler")
                    print(f"  [FEHLER] Job fehlgeschlagen: {error_msg}")
                    return False

            print("  [WARN] Job hat Zeitlimit überschritten (5 Min)")
            print(
                f"  Aktueller Status: {job_data['status']}, Fortschritt: {job_data.get('progress', 0):.1f}%"
            )
            return False

    except Exception as e:
        print(f"[FEHLER] Fehler: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("OCR-Anbindungen Test")
    print("=" * 60)

    # Prüfe Konfiguration
    print("\nKonfiguration:")
    print(f"  Tesseract: {settings.tesseract_cmd}")
    print(f"  Ollama Base URL: {settings.ollama_base_url}")
    print(f"  Ollama Vision Model: {settings.ollama_vision_model}")
    print(f"  Ollama GPT Model: {settings.ollama_gpt_model}")

    results = []

    # Teste Tesseract
    results.append(("Tesseract", await test_tesseract()))

    # Teste Ollama Vision
    results.append(("Ollama Vision", await test_ollama_vision()))

    # Teste Ollama GPT
    results.append(("Ollama GPT", await test_ollama_gpt()))

    # Teste Job-System (optional, benötigt laufendes Backend und Dokument in DB)
    print("\n" + "=" * 60)
    print("Job-System Test (optional)")
    print("=" * 60)
    print(
        "Hinweis: Dieser Test benötigt ein laufendes Backend und ein Dokument in der Datenbank."
    )
    print("Falls Backend läuft, wird der Test ausgeführt, sonst übersprungen.")

    job_test_result = await test_job_system()
    if job_test_result is not None:
        results.append(("Job-System", job_test_result))

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("Zusammenfassung:")
    print("=" * 60)
    for name, success in results:
        status = "[OK]" if success else "[FEHLER]"
        print(f"  {name}: {status}")

    all_ok = all(success for _, success in results)
    return 0 if all_ok else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
