# Erkenntnisse: Koordinaten-Transformation für Multibox-Regionen

## Aktueller Stand (2026-02-08)

### Problem-Beschreibung
Die "+X" Funktion erkennt Boxen im gezeichneten Bereich, aber:
1. **Keine Boxen werden erstellt** - alle werden als "außerhalb Region" gefiltert
2. **Transformation führt zu falschen Werten** - Boxen sind zu groß (x2_original > x2_region)
3. **Normalisierte Koordinaten > 1.0** - OCR-LLM gibt Werte wie 1.5164, 2.4667 zurück

### Letzte Logs-Analyse (2026-02-08 20:52:14)

**Region**: `[69, 743, 985, 968]` (916x225 Pixel)
**Crop-Bild**: `641x225` Pixel (916 * 0.7 = 641.2 ≈ 641)

**Box 0 Beispiel**:
- Normalized: `[0.1154, 0.0, 1.5164, 0.44]`
- Crop-Pixel: `[74, 0, 972, 99]` (berechnet: 1.5164 * 641 = 972)
- **Problem**: Crop-Bild ist nur 641 Pixel breit, aber Box geht bis 972 Pixel!
- Transformation: `x2_original = 69 + (1.5164 * 641 / 0.7) = 1457`
- Region endet bei: `x2_region = 985`
- **Ergebnis**: Box wird gefiltert (Abweichung: -289 Pixel rechts)

## Transformationskette (aktuell dokumentiert)

### 1. Leaflet → OCR-Koordinaten (Frontend)
**Datei**: `static/index.html` (Zeile 4502-4527)

```javascript
scaleX_display = (mapImageWidth / ocrImageWidth) * 0.7
x_ocr = x_map / scaleX_display
y_ocr = ocrImageHeight - (y_map / scaleY_display)
```

**Beispiel**: Wenn `mapImageWidth = ocrImageWidth = 694`:
- `scaleX_display = 0.7`
- `x_map = 100` → `x_ocr = 100 / 0.7 = 143`

### 2. OCR-Koordinaten → Crop-Bild (Backend)
**Datei**: `src/rotary_archiv/api/review.py` (Zeile 1888-1893)

```python
# Original-Koordinaten werden gespeichert
x1_original, y1_original, x2_original, y2_original = [69, 743, 985, 968]

# Für Cropping wird * 0.7 angewendet
bbox_pixel_adjusted = [
    int(x1_original * 0.7),  # 69 * 0.7 = 48
    y1_original,              # 743
    int(x2_original * 0.7),  # 985 * 0.7 = 689
    y2_original               # 968
]
```

**Crop-Bild-Größe**: `641x225` (Region: 916x225, also `916 * 0.7 = 641`)

### 3. OCR-LLM → Normalisierte Koordinaten
**Datei**: `src/rotary_archiv/ocr/ollama_vision.py` (Zeile 273-280)

**Aktuelle Logik**:
```python
# OCR gibt Pixel-Koordinaten zurück: [x1_pixel, y1_pixel, x2_pixel, y2_pixel]
# Normalisiert:
bbox_normalized = [
    x1_pixel / image_width,   # x_min (relativ)
    y1_pixel / image_height,  # y_min (relativ)
    x2_pixel / image_width,   # x_max (relativ)
    y2_pixel / image_height,  # y_max (relativ)
]
```

**PROBLEM**: Wenn `x2_pixel > image_width`, dann `x2_normalized > 1.0`

**Beispiel aus Logs**:
- OCR gibt zurück: Pixel `[74, 0, 972, 99]`
- Crop-Bild-Größe: `641x225`
- Normalisiert: `[74/641, 0/225, 972/641, 99/225]` = `[0.1154, 0.0, 1.5164, 0.44]`
- **Problem**: `x2_pixel = 972 > crop_image_width = 641` → `x2_normalized = 1.5164 > 1.0`

### 4. Normalisierte Koordinaten → OCR-Koordinaten (Worker)
**Datei**: `src/rotary_archiv/ocr/job_processor.py` (Zeile 784-789)

**Aktuelle Transformation**:
```python
x1_original = x1_region + int((x1_crop_norm * crop_image_width) / 0.7)
x2_original = x1_region + int((x2_crop_norm * crop_image_width) / 0.7)
y1_original = y1_region + int(y1_crop_norm * crop_image_height)
y2_original = y1_region + int(y2_crop_norm * crop_image_height)
```

**Beispiel**:
- `x1_crop_norm = 0.1154`, `crop_image_width = 641`, `x1_region = 69`
- `x1_original = 69 + (0.1154 * 641 / 0.7) = 69 + 105.7 = 174` ✓
- `x2_crop_norm = 1.5164`
- `x2_original = 69 + (1.5164 * 641 / 0.7) = 69 + 1388.6 = 1457`
- **Problem**: `x2_original = 1457 > x2_region = 985` → Box wird gefiltert

## Offene Fragen

### Frage 1: Warum gibt das OCR-LLM Pixel-Koordinaten > Crop-Bild-Größe zurück?
**Hypothesen**:
- Das OCR-LLM verwendet die originale Bildgröße statt der Crop-Bild-Größe?
- Das OCR-LLM sieht das gesamte Bild, nicht nur das Crop?
- Die Bildgröße wird falsch an das OCR-LLM übergeben?

**Zu prüfen**: Welche Bildgröße verwendet `extract_text_with_bbox`?

### Frage 2: Was bedeuten normalisierte Koordinaten > 1.0?
**Aktuelles Verständnis**:
- `x2_normalized = 1.5164` bedeutet, dass `x2_pixel = 1.5164 * crop_image_width`
- Das bedeutet, die Box geht über den Rand des Crop-Bildes hinaus
- **Aber**: Warum gibt das OCR-LLM solche Werte zurück?

**Mögliche Erklärungen**:
1. OCR-LLM verwendet originale Bildgröße für Normalisierung
2. OCR-LLM sieht mehr als das Crop-Bild
3. Normalisierung ist falsch implementiert

### Frage 3: Wie soll die Transformation funktionieren?
**Aktuelle Formel**: `x_original = x1_region + ((x_crop_norm * crop_image_width) / 0.7)`

**Mathematische Überprüfung**:
- Wenn `x_crop_norm = 1.0`, dann `x_crop_pixel = crop_image_width`
- Da `crop_image_width = region_width * 0.7`:
  - `x_original = x1_region + ((1.0 * region_width * 0.7) / 0.7) = x1_region + region_width = x2_region` ✓
- **Aber**: Wenn `x_crop_norm = 1.5164`, dann:
  - `x_original = x1_region + ((1.5164 * region_width * 0.7) / 0.7) = x1_region + (1.5164 * region_width)`
  - Das ist größer als `x2_region = x1_region + region_width`

**Frage**: Sollen wir Boxen, die über die Region hinausgehen, begrenzen statt filtern?

## Bisherige Versuche und warum sie nicht funktioniert haben

### Versuch 1: Entfernen der Begrenzung auf 1.0
**Was gemacht wurde**: Normalisierte Koordinaten werden nicht mehr auf 1.0 begrenzt
**Ergebnis**: Boxen haben jetzt korrekte Höhe, aber werden immer noch gefiltert

### Versuch 2: Direkte Division durch 0.7
**Was gemacht wurde**: `x_original = x1_region + (x_crop_pixel / 0.7)`
**Ergebnis**: Gleiche Werte wie mit normalisierten Koordinaten, immer noch zu groß

### Versuch 3: Relative Skalierung
**Was gemacht wurde**: `x_original = x1_region + ((x_crop_norm * crop_image_width) / 0.7)`
**Ergebnis**: Gleiche Werte, immer noch zu groß

### Versuch 4: Toleranz erhöhen
**Was gemacht wurde**: Toleranz von 5% auf 20% erhöht
**Ergebnis**: Boxen werden immer noch gefiltert (Abweichungen sind zu groß: 200-600 Pixel)

## Wichtige Erkenntnisse

### 1. Das Crop-Bild ist korrekt positioniert
**Bestätigt vom Benutzer**: "das gecroppte bild ins OCR richtig positioniert ist"

### 2. Bestehende Boxen haben auch Werte > 1.0
**Bestätigt vom Benutzer**: "die bestehenden Boxen haben auch werte bis 145% an der echten bildkante"

**Bedeutung**: Normalisierte Werte > 1.0 sind normal und erlaubt!

### 3. Die Transformation muss das 0.7-Faktor berücksichtigen
**Klar**: Das Crop-Bild wurde mit `* 0.7` erstellt, daher muss die Rücktransformation durch `0.7` teilen

### 4. Das Problem liegt wahrscheinlich bei der Bildgröße
**Hypothese**: Das OCR-LLM verwendet möglicherweise die originale Bildgröße statt der Crop-Bild-Größe

## Nächste Schritte (aus Plan)

### Sofort zu tun:
1. **Phase 1, Schritt 1.1**: Füge Debug-Logging hinzu, um zu sehen:
   - Welche Bildgröße wird an `extract_text_with_bbox` übergeben?
   - Was gibt das OCR-LLM zurück? (Pixel-Koordinaten vor Normalisierung)
   - Wie werden die Koordinaten normalisiert?

2. **Phase 3, Schritt 3.2**: Prüfe die Bildgröße:
   - Logge Crop-Bild-Größe (PIL)
   - Logge Bildgröße, die OCR-LLM zurückgibt
   - Vergleiche beide

3. **Phase 4, Schritt 4.3**: Implementiere Begrenzung statt Filterung:
   - Begrenze Boxen auf Region-Größe statt sie zu filtern
   - Das ist besser als keine Boxen zu haben

## Dateien, die geändert wurden

1. `src/rotary_archiv/api/review.py`:
   - `add_multiple_bboxes`: Erstellt temporäre Box, croppt Bild mit `* 0.7`

2. `src/rotary_archiv/ocr/job_processor.py`:
   - `process_multibox_region`: Transformiert Boxen zurück, filtert aktuell

3. `static/index.html`:
   - `convertMapCoordsToBBoxPixel`: Konvertiert Leaflet → OCR-Koordinaten
   - `addMultipleBBoxesFromDrawing`: Frontend-Logik für "+X"

## Wichtige Code-Stellen

### Transformation (aktuell):
```python
# src/rotary_archiv/ocr/job_processor.py, Zeile 784-789
x1_original = x1_region + int((x1_crop_norm * crop_image_width) / 0.7)
x2_original = x1_region + int((x2_crop_norm * crop_image_width) / 0.7)
y1_original = y1_region + int(y1_crop_norm * crop_image_height)
y2_original = y1_region + int(y2_crop_norm * crop_image_height)
```

### Filterung (aktuell):
```python
# src/rotary_archiv/ocr/job_processor.py, Zeile 811-829
tolerance_x = max(50, int(region_width * 0.20))
tolerance_y = max(50, int(region_height * 0.20))
if outside_left or outside_top or outside_right or outside_bottom:
    # Filtere Box
```

### Crop-Erstellung:
```python
# src/rotary_archiv/api/review.py, Zeile 1888-1893
bbox_pixel_adjusted = [
    int(x1_original * 0.7),  # x1
    y1_original,              # y1
    int(x2_original * 0.7),  # x2
    y2_original               # y2
]
```

## Offene Punkte für weitere Analyse

1. **Welche Bildgröße verwendet das OCR-LLM?**
   - Wird die Crop-Bild-Größe korrekt übergeben?
   - Verwendet das OCR-LLM die originale Bildgröße?

2. **Warum gibt das OCR-LLM Pixel-Koordinaten > Crop-Bild-Größe zurück?**
   - Ist das ein Bug im OCR-LLM?
   - Oder ein Problem mit der Bildgröße?

3. **Sollen wir Boxen begrenzen statt filtern?**
   - Empfehlung: Ja, da Boxen gültigen Text enthalten
   - Begrenzung kann später korrigiert werden

4. **Ist die Transformation mathematisch korrekt?**
   - Aktuelle Formel scheint korrekt zu sein
   - Problem liegt wahrscheinlich bei der Bildgröße
