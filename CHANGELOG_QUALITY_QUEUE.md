# Changelog: Quality Metrics & Queue Improvements

## Datum: 2026-01-26

### Job-Queue Verbesserungen

#### Mehrfachauswahl
- **Shift-Klick**: Wählt alle Zeilen zwischen der zuletzt geklickten und der aktuellen Zeile aus
- **Strg-Klick**: Toggle für einzelne Zeilen
- **"Alle auswählen" Button**: Wählt alle Jobs in der aktuellen Tabelle aus
- **Checkbox-Behandlung**: Verbesserte Behandlung von Shift- und Strg-Klicks bei Checkboxen

#### Status-Filter
- **Dropdown-Filter**: Filtert Jobs nach Status (Alle, Wartend, Läuft, Abgeschlossen, Fehler, Pausiert, Abgebrochen)
- **Persistenz**: Filter-Wert bleibt beim automatischen Polling erhalten

#### Archiv-Funktion
- **Archiv-Button**: Neuer Button mit Archivsymbol (📦) zum Archivieren ausgewählter Jobs
- **Bestätigungsdialog**: Sicherheitsabfrage vor dem Archivieren

### Quality Metrics Verbesserungen

#### Batch-Job-Erstellung
- **Verbesserte Logik**:
  - Findet Seiten ohne Quality-Metriken korrekt
  - Setzt fehlgeschlagene Jobs auf PENDING zurück statt neue zu erstellen
  - Prüft COMPLETED-Jobs auf tatsächlich vorhandene Metriken
- **Bugfix**: `db.flush()` hinzugefügt, damit Job-IDs vor dem Commit verfügbar sind

#### Dichte-Metrik
- **Min/Max statt Median**: Zeigt jetzt Min und Max Dichte-Werte statt Median
- **Farbcodierung**:
  - Grün: 3.5 - 6.0 Zeichen/1000px (optimal)
  - Orange: 2.0 - 3.5 und 6.0 - 10.0 Zeichen/1000px (akzeptabel)
  - Rot: < 2.0 oder > 10.0 Zeichen/1000px (problematisch)
- **Konfigurierbar**: Schwellenwerte in `config.py` und über `.env` Datei anpassbar
- **Anwendung**: Farben werden angezeigt in:
  - Min/Max Dichte in der Haupttabelle
  - Dichte-Werte in der ausklappbaren BBox-Liste
  - Min/Max Dichte in der Detailansicht
  - Dichte-Werte in der Detail-Tabelle

#### Ausklappbare BBox-Liste
- **+/- Symbol**: Vor dem Dokumenttitel, klickbar zum Ein-/Ausklappen
- **BBox-Details**: Zeigt für jede Box:
  - Index
  - Text (Vorschau)
  - Zeichenanzahl
  - Fläche in Pixeln
  - Dichte (Zeichen/1000px) mit Farbcodierung
  - Bearbeiten-Button (öffnet den Bearbeiten-Dialog wie im Inspect-View)

#### Dokument-Anzeige
- **Verbesserte Dokument-Abfrage**:
  - Verwendet `document.title` oder `document.filename` als Fallback
  - Zeigt `Dokument #${page.document_id}` falls Dokument nicht gefunden wird
  - Frontend-Fallback für fehlende Dokument-Titel

### Bugfixes

#### Worker-Fehler
- **Image Import**: `from PIL import Image` wurde außerhalb des try-Blocks verschoben, damit `Image` immer verfügbar ist

#### Job-Erstellung
- **Job-IDs**: `db.flush()` hinzugefügt, damit Job-IDs vor dem Commit verfügbar sind und nicht `None` zurückgegeben werden

#### Frontend
- **densityConfig Initialisierung**: Variable wurde zu den globalen Variablen am Anfang verschoben, um "can't access lexical declaration" Fehler zu vermeiden

### Neue Config-Werte

```python
# Quality Metrics - Dichte-Schwellenwerte (Zeichen/1000px)
density_green_min: float = 3.5  # Ab diesem Wert: grün (optimal)
density_green_max: float = 6.0  # Bis zu diesem Wert: grün (optimal)
density_orange_min: float = 2.0  # Ab diesem Wert: orange (akzeptabel)
density_orange_max: float = 10.0  # Bis zu diesem Wert: orange (akzeptabel)
```

Konfigurierbar über `.env`:
```
DENSITY_GREEN_MIN=3.5
DENSITY_GREEN_MAX=6.0
DENSITY_ORANGE_MIN=2.0
DENSITY_ORANGE_MAX=10.0
```

### Neue API-Endpoints

- `GET /api/quality/config`: Gibt die konfigurierten Schwellenwerte für Dichte-Farben zurück

### Geänderte Dateien

1. **`src/rotary_archiv/config.py`**
   - Dichte-Schwellenwerte hinzugefügt

2. **`src/rotary_archiv/api/quality.py`**
   - `GET /api/quality/config` Endpoint hinzugefügt
   - `batch_create_quality_jobs`: Verbesserte Logik für Job-Erstellung
   - `get_quality_pages`: BBox-Daten mit Dichte-Metriken zurückgeben

3. **`src/rotary_archiv/ocr/job_processor.py`**
   - `process_quality_job`: Image Import außerhalb try-Block verschoben

4. **`src/rotary_archiv/utils/quality_metrics.py`**
   - Keine Änderungen (Rückgängig gemacht)

5. **`static/index.html`**
   - Job-Queue: Mehrfachauswahl mit Shift/Strg, "Alle auswählen" Button
   - Job-Queue: Status-Filter hinzugefügt
   - Job-Queue: Archiv-Button hinzugefügt
   - Quality: Min/Max statt Median
   - Quality: Farbcodierung für Dichte-Werte
   - Quality: Ausklappbare BBox-Liste mit Bearbeiten-Button
   - Quality: Verbesserte Dokument-Anzeige
   - Quality: `densityConfig` als globale Variable
