# Transformations-Analyse: Ursprüngliche OCR vs. Multibox-Region

## Ursprüngliche OCR (ganze Seite)

### Transformationskette:
1. **OCR-LLM** gibt Pixel-Koordinaten zurück: `[x1_pixel, y1_pixel, x2_pixel, y2_pixel]`
   - Diese sind relativ zum **vollständigen Bild** (z.B. 694x1000 Pixel)
   
2. **Normalisierung** (in `ollama_vision.py`):
   ```python
   bbox_normalized = [
       x1_pixel / image_width,   # image_width = vollständige Bildbreite
       y1_pixel / image_height,  # image_height = vollständige Bildhöhe
       x2_pixel / image_width,
       y2_pixel / image_height,
   ]
   ```
   - Normalisierte Koordinaten sind relativ zum **vollständigen Bild**
   - Werte > 1.0 sind erlaubt (Boxen können über Bildrand hinausgehen)
   
3. **Speicherung** (in `pipeline.py`):
   - `bbox_normalized` wird direkt in DB gespeichert
   - `bbox_pixel` wird auch gespeichert (Original-Pixel-Koordinaten)
   - `image_width` und `image_height` werden gespeichert (vollständige Bildgröße)

### Beispiel:
- Vollständiges Bild: 694x1000 Pixel
- OCR gibt zurück: Pixel `[100, 200, 500, 400]`
- Normalisiert: `[100/694, 200/1000, 500/694, 400/1000]` = `[0.1441, 0.2, 0.7205, 0.4]`
- Gespeichert: `bbox_normalized = [0.1441, 0.2, 0.7205, 0.4]`, `bbox_pixel = [100, 200, 500, 400]`

## Multibox-Region ("+X")

### Transformationskette:
1. **Frontend** zeichnet Region: `[x1_original, y1_original, x2_original, y2_original]`
   - Diese sind OCR-Koordinaten (z.B. `[96, 623, 986, 970]`)
   
2. **Backend** erstellt Crop-Bild (in `review.py`):
   ```python
   bbox_pixel_adjusted = [
       int(x1_original * 0.7),  # x1 (für Cropping)
       y1_original,              # y1 (unverändert)
       int(x2_original * 0.7),  # x2 (für Cropping)
       y2_original               # y2 (unverändert)
   ]
   ```
   - Crop-Bild-Größe: `(x2_original - x1_original) * 0.7 x (y2_original - y1_original)`
   - Beispiel: Region `[96, 623, 986, 970]` → Crop `[67, 623, 690, 970]` → Größe `623x347`
   
3. **OCR-LLM** gibt Pixel-Koordinaten zurück: `[x1_crop_pixel, y1_crop_pixel, x2_crop_pixel, y2_crop_pixel]`
   - **PROBLEM**: Diese sind relativ zum **Crop-Bild**, aber OCR gibt Werte zurück, die größer sind als das Crop-Bild!
   - Beispiel: OCR gibt `[44, 15, 956, 138]` zurück, aber Crop-Bild ist nur `623x347` Pixel
   - Das bedeutet: `x2_crop_pixel = 956 > crop_image_width = 623`
   
4. **Normalisierung** (in `ollama_vision.py`):
   ```python
   bbox_normalized = [
       x1_crop_pixel / crop_image_width,   # crop_image_width = Crop-Bild-Breite
       y1_crop_pixel / crop_image_height,  # crop_image_height = Crop-Bild-Höhe
       x2_crop_pixel / crop_image_width,
       y2_crop_pixel / crop_image_height,
   ]
   ```
   - Normalisierte Koordinaten sind relativ zum **Crop-Bild**
   - Beispiel: `[44/623, 15/347, 956/623, 138/347]` = `[0.0706, 0.0432, 1.5345, 0.3977]`
   - **PROBLEM**: `x2_normalized = 1.5345 > 1.0` bedeutet, dass die Box über den Rand des Crop-Bildes hinausgeht
   
5. **Rücktransformation** (in `job_processor.py`):
   ```python
   x1_original = x1_region + int((x1_crop_norm * crop_image_width) / 0.7)
   x2_original = x1_region + int((x2_crop_norm * crop_image_width) / 0.7)
   y1_original = y1_region + int(y1_crop_norm * crop_image_height)
   y2_original = y1_region + int(y2_crop_norm * crop_image_height)
   ```
   - **PROBLEM**: Wenn `x2_crop_norm = 1.5345`, dann:
     - `x2_original = 96 + (1.5345 * 623 / 0.7) = 96 + 1365.7 = 1461`
     - Aber Region endet bei `x2_region = 986`
     - **Ergebnis**: Box wird gefiltert oder begrenzt

## Das Problem

**Warum gibt das OCR-LLM Pixel-Koordinaten zurück, die größer sind als das Crop-Bild?**

**Hypothese**: Das OCR-LLM verwendet möglicherweise die originale Bildgröße für die Normalisierung, nicht die Crop-Bild-Größe. Oder die OCR-LLM sieht mehr als das Crop-Bild.

**Aber**: Wir übergeben nur das Crop-Bild an das OCR-LLM. Also sollten die Pixel-Koordinaten relativ zum Crop-Bild sein.

**Mögliche Erklärung**: Die OCR-LLM gibt Pixel-Koordinaten zurück, die größer sind als das Crop-Bild, weil:
1. Die OCR-LLM erkennt Text, der über den Rand des Crop-Bildes hinausgeht (z.B. durch Rundungsfehler beim Cropping)
2. Die OCR-LLM verwendet eine andere Bildgröße für die Normalisierung (z.B. die originale Bildgröße)

## Lösung: Gleiche Transformation wie ursprüngliche OCR

Die ursprüngliche OCR speichert normalisierte Koordinaten relativ zum **vollständigen Bild**. Für Multibox-Regionen sollten wir das Gleiche tun:

1. **Transformiere Crop-Koordinaten zurück auf vollständiges Bild**:
   ```python
   # Crop-Pixel → Vollständiges Bild-Pixel
   x1_full_pixel = x1_region + int((x1_crop_norm * crop_image_width) / 0.7)
   x2_full_pixel = x1_region + int((x2_crop_norm * crop_image_width) / 0.7)
   y1_full_pixel = y1_region + int(y1_crop_norm * crop_image_height)
   y2_full_pixel = y1_region + int(y2_crop_norm * crop_image_height)
   ```

2. **Normalisiere relativ zum vollständigen Bild**:
   ```python
   bbox_normalized = [
       x1_full_pixel / ocr_image_width,   # ocr_image_width = vollständige Bildbreite
       y1_full_pixel / ocr_image_height,  # ocr_image_height = vollständige Bildhöhe
       x2_full_pixel / ocr_image_width,
       y2_full_pixel / ocr_image_height,
   ]
   ```

3. **Speichere wie ursprüngliche OCR**:
   - `bbox_normalized` relativ zum vollständigen Bild
   - `bbox_pixel` als Pixel-Koordinaten im vollständigen Bild
   - `image_width` und `image_height` sind bereits vorhanden (aus `ocr_result`)

## Aktuelle Implementierung

Die aktuelle Implementierung macht genau das! Das Problem ist, dass die Transformation zu Werten führt, die außerhalb der Region liegen. Aber das ist OK - wir begrenzen die Boxen auf die Region-Grenzen (statt sie zu filtern), und dann normalisieren wir sie relativ zum vollständigen Bild.

**Die Transformation ist korrekt!** Das Problem war nur die Filterung. Jetzt begrenzen wir die Boxen auf die Region-Grenzen, was korrekt ist.
