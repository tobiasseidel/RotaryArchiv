"""
Einmaliges Skript zum Migrieren bestehender BBox-Daten mit Metriken.
Füllt die neuen Spalten (char_count, chars_per_1k_px, etc.) für alle bestehenden Boxen.

Usage: python scripts/migrate_bbox_metrics.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from src.rotary_archiv.core.database import SessionLocal
from src.rotary_archiv.core.models import BBox, OCRResult
from src.rotary_archiv.core.bbox import update_bbox_with_metrics


def migrate_bbox_metrics():
    """Migriert alle bestehenden BBoxen mit berechneten Metriken."""
    db: Session = SessionLocal()
    
    try:
        # Alle Boxen laden
        total = db.query(BBox).count()
        print(f"Gesamt Boxen zu migrieren: {total}")
        
        # Batch-Verarbeitung
        batch_size = 500
        migrated = 0
        errors = 0
        
        for offset in range(0, total, batch_size):
            bboxes = (
                db.query(BBox, OCRResult)
                .join(OCRResult, OCRResult.id == BBox.ocr_result_id)
                .offset(offset)
                .limit(batch_size)
                .all()
            )
            
            for bbox, ocr_result in bboxes:
                try:
                    # bbox_item aus bbox重建 (für Metrik-Berechnung)
                    bbox_item = {
                        "text": bbox.text,
                        "bbox_pixel": bbox.bbox_pixel,
                        "reviewed_text": bbox.text,
                    }
                    
                    # Metriken berechnen
                    update_bbox_with_metrics(bbox, bbox_item, ocr_result.image_width)
                    
                    # black_pixels aus quality_metrics übernehmen (falls vorhanden)
                    if ocr_result.quality_metrics:
                        bp_data = ocr_result.quality_metrics.get("black_pixels_per_char", {})
                        bp_bboxes = bp_data.get("bboxes", [])
                        if bp_bboxes and bbox.bbox_pixel:
                            # Finde das passende bbox-black_pixels Eintrag
                            for idx, bp_bbox in enumerate(bp_bboxes):
                                if idx < len(bp_bboxes):
                                    bbox.black_pixels = bp_bbox.get("black_pixels")
                                    bbox.black_pixels_per_char = bp_bbox.get("black_pixels_per_char")
                                    break
                    
                    migrated += 1
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"  Fehler bei BBox {bbox.id}: {e}")
            
            db.commit()
            print(f"  Fortschritt: {min(offset + batch_size, total)}/{total}")
        
        print(f"\nMigration abgeschlossen: {migrated} erfolgreich, {errors} Fehler")
        
    finally:
        db.close()


if __name__ == "__main__":
    migrate_bbox_metrics()
