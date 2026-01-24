"""
Separater Background-Worker für OCR-Job-Verarbeitung

Dieser Worker läuft unabhängig vom API-Server und verarbeitet OCR-Jobs
aus der Datenbank. Er kann unabhängig gestartet/gestoppt werden.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from src.rotary_archiv.core.database import SessionLocal
from src.rotary_archiv.core.models import OCRJob, OCRJobStatus
from src.rotary_archiv.ocr.job_processor import process_bbox_review_job, process_ocr_job

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Globaler Flag für sauberes Shutdown
shutdown_requested = False
current_job_id: Optional[int] = None


def signal_handler(signum, frame):
    """Handler für Shutdown-Signale (SIGINT, SIGTERM)"""
    global shutdown_requested
    logger.info(
        f"Shutdown-Signal empfangen ({signum}). Warte auf Abschluss des aktuellen Jobs..."
    )
    shutdown_requested = True


async def worker_loop(poll_interval: int = 5):
    """
    Haupt-Worker-Loop: Prüft kontinuierlich auf neue PENDING-Jobs

    Args:
        poll_interval: Sekunden zwischen Polling-Zyklen
    """
    global shutdown_requested, current_job_id

    logger.info("OCR-Worker gestartet. Warte auf Jobs...")

    while not shutdown_requested:
        db = SessionLocal()
        try:
            # Hole nächsten PENDING-Job (sortiert nach Priorität, dann nach Erstellungsdatum)
            job = (
                db.query(OCRJob)
                .filter(OCRJob.status == OCRJobStatus.PENDING)
                .order_by(OCRJob.priority.asc(), OCRJob.created_at.asc())
                .first()
            )

            if job:
                current_job_id = job.id
                job_type = job.job_type or "ocr"  # Fallback zu "ocr" für alte Jobs
                logger.info(
                    f"Verarbeite {job_type}-Job {job.id} (Dokument {job.document_id})"
                )
                try:
                    # Unterscheide nach Job-Typ
                    if job_type == "bbox_review":
                        await process_bbox_review_job(job.id)
                        logger.info(
                            f"BBox-Review-Job {job.id} erfolgreich abgeschlossen"
                        )
                    else:
                        await process_ocr_job(job.id)
                        logger.info(f"OCR-Job {job.id} erfolgreich abgeschlossen")
                except asyncio.CancelledError:
                    logger.warning(f"{job_type}-Job {job.id} wurde abgebrochen")
                    # Setze Job zurück auf PENDING für erneute Verarbeitung
                    job.status = OCRJobStatus.PENDING
                    job.error_message = "Job wurde abgebrochen (Worker-Shutdown)"
                    db.commit()
                    raise
                except Exception as e:
                    logger.error(
                        f"Fehler beim Verarbeiten von {job_type}-Job {job.id}: {e}",
                        exc_info=True,
                    )
                finally:
                    current_job_id = None
            else:
                # Keine Jobs vorhanden, warte
                await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Fehler im Worker-Loop: {e}", exc_info=True)
            await asyncio.sleep(poll_interval)
        finally:
            db.close()

    logger.info("Worker-Loop beendet")


async def main():
    """Hauptfunktion für Worker-Prozess"""
    # Signal-Handler registrieren
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await worker_loop(poll_interval=5)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt empfangen. Beende Worker...")
    except Exception as e:
        logger.error(f"Kritischer Fehler im Worker: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Worker beendet")


if __name__ == "__main__":
    asyncio.run(main())
