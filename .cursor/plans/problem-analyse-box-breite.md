# Problem-Analyse: Box-Breite zu gering

## Beobachtung aus Logs

**Region**: `[90, 778, 990, 958]` → Breite = 900 Pixel
**Crop-Bild**: `631x180` Pixel
**OCR gibt zurück**: `[53, 0, 978, 997]` → `x2=978` Pixel
**Problem**: `978 > 631` → OCR gibt Koordinaten zurück, die größer sind als das Crop-Bild!

**Transformation**:
- `x1_crop_start = 90 * 0.7 = 63.0`
- `x2_original = 63.0 + 978.0/0.7 = 1460`
- Nach Region-Begrenzung: `x2=990` (Region-Ende)
- Nach Bildgrenzen: `x2=694` (Bildbreite)

**Ergebnis**: Box hat Breite `694 - 138 = 556` Pixel statt erwarteter ~900 Pixel

## Root Cause

1. **OCR gibt falsche Koordinaten zurück**: `x2=978` für ein 631 Pixel breites Bild
   - OCR sollte maximal `x2=631` zurückgeben
   - Mögliche Ursachen:
     - OCR verwendet Original-Bild-Größe statt Crop-Bild-Größe
     - OCR hat einen Fehler bei der Koordinaten-Berechnung
     - OCR gibt normalisierte Koordinaten zurück, die falsch interpretiert werden

2. **Bildgrenzen-Beschnitt ist zu aggressiv**: 
   - Box wird auf `ocr_image_width=694` beschnitten
   - Aber die Region endet bei `x2_region=990`
   - Warum wird auf Bildbreite beschnitten, wenn Region größer ist?

## Lösung

### Option 1: OCR-Koordinaten begrenzen
- Begrenze OCR-Koordinaten auf Crop-Bild-Größe vor Transformation
- `x2_crop_pixel = min(x2_crop_pixel, crop_image_width)`

### Option 2: Bildgrenzen-Beschnitt anpassen
- Bescheide nur auf Region-Grenzen, nicht auf Bildgrenzen
- Oder: Bescheide auf `max(ocr_image_width, x2_region)`

### Option 3: Transformation korrigieren
- Prüfe, ob die Transformation korrekt ist
- Vielleicht sollte `x2_original` anders berechnet werden?

## Empfehlung

**Sofort**: Begrenze OCR-Koordinaten auf Crop-Bild-Größe vor Transformation
**Dann**: Prüfe, ob Bildgrenzen-Beschnitt notwendig ist oder entfernt werden kann
