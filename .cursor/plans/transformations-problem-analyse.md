# Problem-Analyse: Boxen sind nach links und unten verschoben

## Logs-Analyse

**Region**: `[70, 737, 983, 976]` (913x239 Pixel)
**Crop-Bild**: `639x239` Pixel (913 * 0.7 = 639.1 ≈ 639) ✓

**Box 0**:
- OCR gibt zurück: `[72, 20, 972, 131]` (relativ zum Crop-Bild)
- Normalisiert: `[0.1127, 0.0837, 1.5211, 0.5481]`
- Transformation: `x1=172 (=70 + 0.1127*639/0.7=172.9)`
- **Problem**: Box beginnt bei `x1=172`, aber sollte bei `x1≈72` beginnen (relativ zur Region)

## Das Problem

Die Transformation ist falsch! Schauen wir uns die Transformationskette an:

1. **Crop-Bild-Erstellung**:
   - Region: `[70, 737, 983, 976]`
   - Crop-Koordinaten: `[70*0.7, 737, 983*0.7, 976]` = `[49, 737, 688, 976]`
   - Crop-Bild-Größe: `639x239` Pixel ✓

2. **OCR gibt zurück**: `[72, 20, 972, 131]` (relativ zum Crop-Bild)
   - Das bedeutet: `x1=72` Pixel vom **Anfang des Crop-Bildes** (bei x=49 im vollständigen Bild)

3. **Aktuelle Transformation**:
   ```python
   x1_original = x1_region + int((x1_crop_norm * crop_image_width) / 0.7)
   x1_original = 70 + int((0.1127 * 639) / 0.7)
   x1_original = 70 + int(102.9)
   x1_original = 70 + 102 = 172
   ```

4. **Aber**: Das Crop-Bild beginnt bei `x1_region * 0.7 = 70 * 0.7 = 49` im vollständigen Bild!
   - OCR gibt `x1=72` zurück (relativ zum Crop-Bild)
   - Das sollte sein: `x1_original = 49 + (72 / 0.7) = 49 + 102.9 = 151.9` → `151`
   - **ODER**: `x1_original = x1_region + (x1_crop_pixel / 0.7) = 70 + (72 / 0.7) = 70 + 102.9 = 172.9` → `172`

**Warte**: Die aktuelle Transformation ist `x1_original = x1_region + (x1_crop_pixel / 0.7)`, was `172` ergibt. Das ist korrekt!

**Aber warum ist die Box dann nach links verschoben?**

Lass mich nochmal nachdenken:
- Region beginnt bei `x1_region=70`
- Crop-Bild beginnt bei `x1_region * 0.7 = 49` im vollständigen Bild
- OCR gibt `x1=72` zurück (relativ zum Crop-Bild)
- `x1_original = 49 + (72 / 0.7) = 49 + 102.9 = 151.9` → `151`

**Das Problem**: Die aktuelle Transformation verwendet `x1_region` statt `x1_region * 0.7`!

## Lösung

Die Transformation sollte sein:
```python
# Crop-Bild beginnt bei x1_region * 0.7 im vollständigen Bild
x1_crop_start = x1_region * 0.7
x1_original = x1_crop_start + (x1_crop_pixel / 0.7)
# Oder vereinfacht:
x1_original = (x1_region * 0.7) + (x1_crop_pixel / 0.7)
x1_original = x1_region + (x1_crop_pixel / 0.7) - (x1_region * 0.7) + (x1_region * 0.7)
# Das ist kompliziert...

# Einfacher: Verwende die normalisierten Koordinaten direkt
x1_original = x1_region + (x1_crop_norm * crop_image_width / 0.7)
# Das ist was wir haben, aber es ist falsch!

# Richtig sollte sein:
x1_crop_pixel = x1_crop_norm * crop_image_width
x1_original = (x1_region * 0.7) + (x1_crop_pixel / 0.7)
x1_original = x1_region + (x1_crop_pixel / 0.7) - (x1_region * 0.3)
# Das ist immer noch kompliziert...

# Lass mich nochmal nachdenken:
# Crop-Bild beginnt bei: x1_region * 0.7
# OCR gibt x1_crop_pixel zurück (relativ zum Crop-Bild)
# x1_original = (x1_region * 0.7) + (x1_crop_pixel / 0.7)
# x1_original = x1_region * 0.7 + x1_crop_pixel / 0.7
# x1_original = (x1_region * 0.7 * 0.7 + x1_crop_pixel) / 0.7
# x1_original = (x1_region * 0.49 + x1_crop_pixel) / 0.7

# Oder einfacher:
# x1_original = x1_region + (x1_crop_pixel - x1_region * 0.7) / 0.7
# x1_original = x1_region + x1_crop_pixel / 0.7 - x1_region
# x1_original = x1_crop_pixel / 0.7

# Das kann nicht stimmen...

# Lass mich die ursprüngliche Logik nochmal prüfen:
# Crop-Bild wird erstellt mit: bbox_pixel_adjusted = [int(x1_original * 0.7), ...]
# Das bedeutet: Crop beginnt bei x1_original * 0.7 im vollständigen Bild
# OCR gibt x1_crop_pixel zurück (relativ zum Crop-Bild, das bei x1_original * 0.7 beginnt)
# x1_original = (x1_original * 0.7) + (x1_crop_pixel / 0.7)
# Das ist eine Gleichung mit x1_original auf beiden Seiten!

# Ich glaube, das Problem ist anders:
# Die OCR gibt Koordinaten zurück, die relativ zum Crop-Bild sind
# Aber das Crop-Bild wurde mit * 0.7 erstellt
# Um zurück zu transformieren: x1_original = x1_region + (x1_crop_pixel / 0.7)
# Das ist was wir haben!

# Aber warum ist die Box dann verschoben?
# Vielleicht ist das Problem, dass die OCR-Koordinaten nicht relativ zum Crop-Bild sind, sondern relativ zum vollständigen Bild?
