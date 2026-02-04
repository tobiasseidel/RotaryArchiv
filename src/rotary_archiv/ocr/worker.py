"""
Separater Background-Worker für OCR-Job-Verarbeitung

Dieser Worker läuft unabhängig vom API-Server und verarbeitet OCR-Jobs
aus der Datenbank. Er kann unabhängig gestartet/gestoppt werden.
"""

import asyncio
from contextlib import suppress
import logging
import signal
import sys
from typing import Optional

# SQLAlchemy SQL-Query-Logging DEAKTIVIEREN, bevor die Engine importiert wird
# Das verhindert, dass echo=True in database.py SQL-Queries loggt
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

from src.rotary_archiv.core.database import SessionLocal  # noqa: E402
from src.rotary_archiv.core.models import OCRJob, OCRJobStatus  # noqa: E402
from src.rotary_archiv.ocr.job_processor import (  # noqa: E402
    process_bbox_review_job,
    process_ocr_job,
    process_quality_job,
)

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Deaktiviere SQLAlchemy SQL-Query-Logging komplett
# echo=True in SQLAlchemy schreibt direkt an stdout/stderr, daher müssen wir
# die Logger-Handler entfernen oder einen Null-Handler hinzufügen
sqlalchemy_loggers = [
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "sqlalchemy.dialects",
    "sqlalchemy.engine.Engine",
]
for logger_name in sqlalchemy_loggers:
    sql_logger = logging.getLogger(logger_name)
    sql_logger.setLevel(logging.CRITICAL)  # Setze auf höchstes Level
    sql_logger.propagate = False  # Verhindere Weiterleitung an Root-Logger
    # Entferne alle Handler
    for handler in sql_logger.handlers[:]:
        sql_logger.removeHandler(handler)
    # Füge Null-Handler hinzu, der alle Logs verschluckt
    sql_logger.addHandler(logging.NullHandler())

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
                # Prüfe Shutdown vor Job-Start
                if shutdown_requested:
                    logger.info("Shutdown angefordert, beende Worker-Loop")
                    break

                current_job_id = job.id
                job_type = job.job_type or "ocr"  # Fallback zu "ocr" für alte Jobs
                logger.info(
                    f"[{job_type.upper()}] Starte Job {job.id} (Dokument {job.document_id}, Seite {job.document_page_id or 'N/A'})"
                )
                try:
                    # Erstelle Task für Job-Verarbeitung, damit wir ihn abbrechen können
                    if job_type == "bbox_review":
                        task = asyncio.create_task(process_bbox_review_job(job.id))  # noqa: RUF006
                    elif job_type == "quality":
                        task = asyncio.create_task(process_quality_job(job.id))  # noqa: RUF006
                    else:
                        task = asyncio.create_task(process_ocr_job(job.id))

                    # Warte auf Task-Abschluss, prüfe aber regelmäßig auf Shutdown
                    while not task.done():
                        if shutdown_requested:
                            logger.warning(
                                f"Shutdown während Job-Verarbeitung angefordert. Breche Job {job.id} ab..."
                            )
                            task.cancel()
                            # Warte kurz auf Task-Abbruch
                            with suppress(asyncio.CancelledError, asyncio.TimeoutError):
                                await asyncio.wait_for(task, timeout=2.0)
                            # Setze Job zurück auf PENDING für erneute Verarbeitung
                            db.refresh(job)
                            job.status = OCRJobStatus.PENDING
                            job.error_message = (
                                "Job wurde abgebrochen (Worker-Shutdown)"
                            )
                            db.commit()
                            raise asyncio.CancelledError(
                                f"Job {job.id} wurde abgebrochen"
                            )
                        await asyncio.sleep(0.1)  # Kurze Pause zwischen Checks

                    # Task ist fertig, hole Ergebnis
                    await task
                    logger.info(
                        f"[{job_type.upper()}] Job {job.id} erfolgreich abgeschlossen"
                    )
                except asyncio.CancelledError:
                    logger.warning(f"{job_type}-Job {job.id} wurde abgebrochen")
                    # Setze Job zurück auf PENDING für erneute Verarbeitung
                    db.refresh(job)
                    job.status = OCRJobStatus.PENDING
                    job.error_message = "Job wurde abgebrochen (Worker-Shutdown)"
                    db.commit()
                    break  # Verlasse Loop bei Shutdown
                except Exception as e:
                    logger.error(
                        f"[{job_type.upper()}] FEHLER bei Job {job.id}: {e}",
                        exc_info=True,
                    )
                finally:
                    current_job_id = None
            else:
                # Keine Jobs vorhanden, warte (mit Shutdown-Check)
                if shutdown_requested:
                    logger.info("Shutdown angefordert, beende Worker-Loop")
                    break
                # Warte in kleinen Schritten, um auf Shutdown reagieren zu können
                for _ in range(poll_interval * 10):  # 10 Checks pro Sekunde
                    if shutdown_requested:
                        break
                    await asyncio.sleep(0.1)

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
