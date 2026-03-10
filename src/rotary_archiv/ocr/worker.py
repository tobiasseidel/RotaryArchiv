"""
Separater Background-Worker für OCR-Job-Verarbeitung

Dieser Worker läuft unabhängig vom API-Server und verarbeitet OCR-Jobs
aus der Datenbank. Er kann unabhängig gestartet/gestoppt werden.
"""

import asyncio
import contextlib
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
    process_boundary_analysis_job,
    process_content_analysis_job,
    process_llm_sight_job,
    process_ocr_job,
    process_pdf_export_job,
    process_persistent_region_quality_job,
    process_persistent_region_re_recognize_job,
    process_quality_job,
    process_unit_content_analysis_job,
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
    if shutdown_requested:
        # Shutdown wurde bereits angefordert, beende Prozess sofort
        logger.warning("Shutdown bereits angefordert, beende Prozess sofort...")
        sys.exit(0)
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

                # Abhängigkeitsprüfung: Quality-, Persistent-Region-Quality- und Re-Recognize-Jobs
                # warten, bis kein PENDING BBox-Review-Job für dieselbe Seite existiert
                if (
                    job_type
                    in (
                        "quality",
                        "persistent_region_quality",
                        "persistent_region_re_recognize",
                    )
                    and job.document_page_id
                ):
                    pending_review_job = (
                        db.query(OCRJob)
                        .filter(
                            OCRJob.document_page_id == job.document_page_id,
                            OCRJob.job_type == "bbox_review",
                            OCRJob.status == OCRJobStatus.PENDING,
                            OCRJob.id != job.id,  # Nicht der aktuelle Job
                        )
                        .first()
                    )
                    if pending_review_job:
                        logger.debug(
                            f"[{job_type.upper()}] Überspringe Job {job.id} für Seite {job.document_page_id}: "
                            f"BBox-Review-Job {pending_review_job.id} ist noch PENDING"
                        )
                        # Job bleibt PENDING und wird beim nächsten Durchlauf erneut geprüft
                        # (Session wird im finally-Block geschlossen)
                        await asyncio.sleep(1)  # Kurze Pause vor erneutem Polling
                        continue

                logger.info(
                    f"[{job_type.upper()}] Starte Job {job.id} (Dokument {job.document_id}, Seite {job.document_page_id or 'N/A'})"
                )
                try:
                    # Erstelle Task für Job-Verarbeitung, damit wir ihn abbrechen können
                    if job_type == "bbox_review":
                        task = asyncio.create_task(process_bbox_review_job(job.id))  # noqa: RUF006
                    elif job_type == "llm_sight":
                        task = asyncio.create_task(process_llm_sight_job(job.id))  # noqa: RUF006
                    elif job_type == "quality":
                        task = asyncio.create_task(process_quality_job(job.id))  # noqa: RUF006
                    elif job_type == "persistent_region_quality":
                        task = asyncio.create_task(  # noqa: RUF006
                            process_persistent_region_quality_job(job.id)
                        )
                    elif job_type == "persistent_region_re_recognize":
                        task = asyncio.create_task(  # noqa: RUF006
                            process_persistent_region_re_recognize_job(job.id)
                        )
                    elif job_type == "content_analysis":
                        task = asyncio.create_task(  # noqa: RUF006
                            process_content_analysis_job(job.id)
                        )
                    elif job_type == "boundary_analysis":
                        task = asyncio.create_task(  # noqa: RUF006
                            process_boundary_analysis_job(job.id)
                        )
                    elif job_type == "unit_content_analysis":
                        task = asyncio.create_task(  # noqa: RUF006
                            process_unit_content_analysis_job(job.id)
                        )
                    elif job_type == "pdf_export":
                        task = asyncio.create_task(  # noqa: RUF006
                            process_pdf_export_job(job.id)
                        )
                    else:
                        task = asyncio.create_task(process_ocr_job(job.id))

                    # Warte auf Task-Abschluss, prüfe aber regelmäßig auf Shutdown
                    while not task.done():
                        if shutdown_requested:
                            logger.warning(
                                f"Shutdown während Job-Verarbeitung angefordert. Breche Job {job.id} ab..."
                            )
                            task.cancel()
                            # Warte auf Task-Abbruch mit Timeout
                            with contextlib.suppress(
                                asyncio.CancelledError, asyncio.TimeoutError
                            ):
                                await asyncio.wait_for(task, timeout=3.0)
                            # Setze Job zurück auf PENDING für erneute Verarbeitung
                            try:
                                db.refresh(job)
                                job.status = OCRJobStatus.PENDING
                                job.error_message = (
                                    "Job wurde abgebrochen (Worker-Shutdown)"
                                )
                                db.commit()
                            except Exception as e:
                                logger.warning(
                                    f"Fehler beim Zurücksetzen des Jobs: {e}"
                                )
                            raise asyncio.CancelledError(
                                f"Job {job.id} wurde abgebrochen"
                            )
                        await asyncio.sleep(0.1)  # Kurze Pause zwischen Checks

                    # Task ist fertig, hole Ergebnis (kann CancelledError auslösen)
                    try:
                        await task
                    except asyncio.CancelledError:
                        # Task wurde abgebrochen - das ist OK
                        raise
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

    # Stelle sicher, dass alle Tasks abgebrochen werden
    try:
        loop = asyncio.get_running_loop()
        tasks = [
            task
            for task in asyncio.all_tasks(loop)
            if not task.done() and task != asyncio.current_task(loop)
        ]
        if tasks:
            logger.debug(f"Breche {len(tasks)} laufende Tasks ab...")
            for task in tasks:
                task.cancel()
            # Warte kurz auf Abbruch (mit Timeout)
            with contextlib.suppress(asyncio.TimeoutError, Exception):
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=2.0
                )
    except RuntimeError:
        # Keine laufende Loop mehr - das ist OK
        pass
    except Exception as e:
        logger.debug(f"Fehler beim Beenden von Tasks: {e}")


async def main():
    """Hauptfunktion für Worker-Prozess"""
    # Signal-Handler registrieren
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await worker_loop(poll_interval=5)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt empfangen. Beende Worker...")
    except asyncio.CancelledError:
        logger.info("Worker wurde abgebrochen")
    except Exception as e:
        logger.error(f"Kritischer Fehler im Worker: {e}", exc_info=True)
        raise  # Re-raise, damit der Fehler im Hauptprozess behandelt wird
    finally:
        logger.info("Worker beendet")


if __name__ == "__main__":
    exit_code = 0
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt im Hauptprozess. Beende...")
        exit_code = 0
    except Exception as e:
        logger.error(f"Kritischer Fehler: {e}", exc_info=True)
        exit_code = 1
    finally:
        # Stelle sicher, dass der Prozess wirklich beendet wird
        logger.info("Beende Prozess...")
        sys.exit(exit_code)
