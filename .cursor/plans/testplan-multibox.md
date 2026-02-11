# Testplan: Multibox-Region Transformation

## Phase 5: Implementierung und Tests

### Schritt 5.4: Teste mit echten Daten

#### Test 5.4.1: Einfacher Fall - Eine Box innerhalb Region
**Ziel**: Prüfe, ob eine einfache Box korrekt erkannt und transformiert wird

**Vorgehen**:
1. Öffne eine Seite im Inspect-View
2. Zeichne eine "+X" Region um einen einzelnen Absatz
3. Warte auf OCR-Verarbeitung
4. Prüfe Logs:
   - Wurde eine Box erstellt?
   - Sind die Koordinaten korrekt?
   - Ist die Box innerhalb der Region?

**Erwartetes Ergebnis**:
- Eine Box wird erstellt
- Box-Koordinaten sind innerhalb der Region
- Box-Text entspricht dem erkannten Text

**Zu prüfende Logs**:
```
[Multibox-Region] Crop-Bild-Größe (PIL): ...
[OCR-LLM] Bild geladen: ...
[OCR-LLM] Parse Ergebnis: X Boxen erkannt
Box 0: Transformation Details: ...
Box 0: Auf Region-Grenzen begrenzt: ... (falls nötig)
Box 0: ✓ Erfolgreich erstellt: ...
```

#### Test 5.4.2: Mehrere Boxen innerhalb Region
**Ziel**: Prüfe, ob mehrere Boxen korrekt erkannt werden

**Vorgehen**:
1. Zeichne eine "+X" Region um mehrere Absätze
2. Warte auf OCR-Verarbeitung
3. Prüfe Logs:
   - Wurden mehrere Boxen erstellt?
   - Sind alle Boxen korrekt positioniert?
   - Sind alle Boxen innerhalb der Region?

**Erwartetes Ergebnis**:
- Mehrere Boxen werden erstellt
- Alle Boxen sind korrekt positioniert
- Alle Boxen sind innerhalb der Region

#### Test 5.4.3: Boxen, die über Region-Rand hinausgehen
**Ziel**: Prüfe, ob Boxen korrekt begrenzt werden

**Vorgehen**:
1. Zeichne eine "+X" Region, die nur einen Teil eines langen Textes umfasst
2. Warte auf OCR-Verarbeitung
3. Prüfe Logs:
   - Werden Boxen erstellt, die ursprünglich über den Rand hinausgehen?
   - Werden diese Boxen korrekt begrenzt?
   - Ist die Begrenzung korrekt dokumentiert?

**Erwartetes Ergebnis**:
- Boxen werden erstellt, auch wenn sie ursprünglich über den Rand hinausgehen
- Boxen werden auf Region-Grenzen begrenzt
- Logs zeigen "Auf Region-Grenzen begrenzt"

**Zu prüfende Logs**:
```
Box X: Transformation Details: ...
Box X: Auf Region-Grenzen begrenzt: Vorher=[...], Nachher=[...]
Box X: ✓ Erfolgreich erstellt: ...
```

#### Test 5.4.4: Vergleich mit "+1" Box
**Ziel**: Prüfe, ob "+X" Boxen die gleiche Position wie "+1" Boxen haben

**Vorgehen**:
1. Erstelle eine "+1" Box für einen Textabsatz
2. Erstelle eine "+X" Region für den gleichen Textabsatz
3. Vergleiche die Koordinaten beider Boxen

**Erwartetes Ergebnis**:
- Beide Boxen haben ähnliche Koordinaten (kleine Abweichungen durch OCR sind OK)
- Normalisierte Koordinaten sind relativ zum vollständigen Bild

**Zu prüfende Werte**:
- `bbox_pixel` Koordinaten
- `bbox_normalized` Koordinaten
- Position in Leaflet-Anzeige

## Phase 6: Verifikation und Abschluss

### Schritt 6.1: Verifiziere die komplette Transformationskette

#### Test 6.1.1: Roundtrip-Test
**Ziel**: Prüfe, ob die Transformationskette korrekt funktioniert

**Vorgehen**:
1. Erstelle eine "+X" Box
2. Notiere die ursprünglichen Region-Koordinaten
3. Prüfe die erstellten Box-Koordinaten
4. Prüfe die normalisierten Koordinaten
5. Verifiziere die Anzeige in Leaflet

**Erwartetes Ergebnis**:
- Box wird korrekt angezeigt
- Koordinaten stimmen überein
- Normalisierte Koordinaten sind relativ zum vollständigen Bild

**Transformationskette zu prüfen**:
1. Frontend: Leaflet-Koordinaten → OCR-Koordinaten
2. Backend: OCR-Koordinaten → Crop-Bild (mit * 0.7)
3. OCR-LLM: Crop-Bild → Pixel-Koordinaten → Normalisiert
4. Worker: Normalisiert → OCR-Koordinaten (mit / 0.7)
5. Worker: OCR-Koordinaten → Normalisiert (relativ zum vollständigen Bild)
6. Frontend: Normalisiert → Leaflet-Koordinaten (Anzeige)

#### Test 6.1.2: Edge Cases
**Ziel**: Prüfe Edge Cases

**Test 6.1.2.1: Boxen am Rand der Region**
- Zeichne Region sehr nah am Bildrand
- Prüfe, ob Boxen korrekt erstellt werden

**Test 6.1.2.2: Sehr kleine Region**
- Zeichne eine sehr kleine Region (z.B. 50x50 Pixel)
- Prüfe, ob Boxen erstellt werden

**Test 6.1.2.3: Sehr große Region**
- Zeichne eine sehr große Region (fast ganze Seite)
- Prüfe, ob alle Boxen erstellt werden

**Test 6.1.2.4: Region mit vielen Boxen**
- Zeichne Region mit vielen Textabsätzen
- Prüfe, ob alle Boxen erstellt werden

### Schritt 6.2: Vergleich mit bestehenden Boxen

#### Test 6.2.1: Normalisierte Koordinaten vergleichen
**Ziel**: Prüfe, ob "+X" Boxen die gleiche Normalisierung wie bestehende Boxen haben

**Vorgehen**:
1. Prüfe bestehende Boxen aus ursprünglicher OCR
2. Prüfe neue Boxen aus "+X" Region
3. Vergleiche die normalisierten Koordinaten

**Erwartetes Ergebnis**:
- Beide verwenden die gleiche Normalisierung (relativ zum vollständigen Bild)
- Werte > 1.0 sind bei beiden erlaubt

## Checkliste für jeden Test

- [ ] Logs zeigen korrekte Crop-Bild-Größe
- [ ] Logs zeigen korrekte OCR-LLM Bildgröße
- [ ] Logs zeigen korrekte Transformation
- [ ] Boxen werden erstellt (nicht gefiltert)
- [ ] Boxen sind korrekt positioniert
- [ ] Normalisierte Koordinaten sind relativ zum vollständigen Bild
- [ ] Boxen werden in Leaflet korrekt angezeigt

## Logs zu sammeln

Für jeden Test sollten folgende Logs gesammelt werden:

1. **Crop-Bild-Erstellung**:
   ```
   [Multibox-Region] Crop-Bild-Größe (PIL): ...
   Add-Multiple-BBox: Original-Koordinaten=...
   ```

2. **OCR-LLM Output**:
   ```
   [OCR-LLM] Bild geladen: ...
   [OCR-LLM] Parse Ergebnis: X Boxen erkannt
   [OCR-LLM] Box X: Rohe Pixel-Koordinaten vom LLM: ...
   [OCR-LLM] Box X: Normalisiert: ...
   ```

3. **Transformation**:
   ```
   Box X: Transformation Details: ...
   Box X: Auf Region-Grenzen begrenzt: ... (falls nötig)
   Box X: ✓ Erfolgreich erstellt: ...
   ```

4. **Finale Box**:
   ```
   bbox_pixel=[...]
   bbox_normalized=[...]
   ```

## Nächste Schritte

1. **Sofort**: Test 5.4.1 durchführen (einfacher Fall)
2. **Dann**: Test 5.4.2 (mehrere Boxen)
3. **Dann**: Test 5.4.3 (Boxen über Rand hinaus)
4. **Dann**: Test 6.1.1 (Roundtrip-Test)
5. **Abschluss**: Test 6.2.1 (Vergleich mit bestehenden Boxen)

## Erfolgskriterien

✅ **Erfolgreich**, wenn:
- Alle Boxen werden erstellt (keine Filterung)
- Boxen sind korrekt positioniert
- Normalisierte Koordinaten sind relativ zum vollständigen Bild
- Boxen werden in Leaflet korrekt angezeigt
- Logs zeigen korrekte Transformation

❌ **Nicht erfolgreich**, wenn:
- Boxen werden gefiltert (außer bei ungültigen Koordinaten)
- Boxen sind falsch positioniert
- Normalisierte Koordinaten sind relativ zum Crop-Bild
- Boxen werden in Leaflet nicht korrekt angezeigt
- Logs zeigen falsche Transformation
