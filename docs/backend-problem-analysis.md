# Backend-Problem Analyse

## Das Problem

**Symptom**: Mehrere Backend-Prozesse laufen gleichzeitig, Port 8000 bleibt blockiert, Prozesse können nicht sauber beendet werden.

## Ursache

### 1. uvicorn mit --reload

`uvicorn --reload` startet einen **Reloader-Prozess**, der:
- Den eigentlichen Server-Prozess startet
- Dateiänderungen überwacht
- Bei Änderungen den Server neu startet

**Problem auf Windows**:
- Prozess-Hierarchien werden nicht immer sauber beendet
- Worker-Prozesse bleiben als "Zombie"-Prozesse hängen
- Port bleibt blockiert, auch wenn der Hauptprozess beendet wurde

### 2. Mehrfaches Starten

Wenn man das Backend mehrfach startet (z.B. aus verschiedenen Terminals), laufen mehrere Instanzen parallel.

### 3. Windows-spezifische Probleme

- PowerShell vs. CMD: Beide haben ähnliche Probleme
- Prozess-Management auf Windows ist weniger robust als auf Linux
- Multiprocessing auf Windows funktioniert anders (spawn statt fork)

## Lösungen

### Option 1: uvicorn OHNE --reload (Empfohlen)

**Vorteile**:
- Stabiler Betrieb
- Keine Zombie-Prozesse
- Einfacher zu beenden

**Nachteile**:
- Kein Auto-Reload bei Code-Änderungen
- Manueller Neustart nötig

**Verwendung**:
```powershell
.\start-backend.ps1
# Oder:
uvicorn src.rotary_archiv.main:app --host 0.0.0.0 --port 8000
```

### Option 2: Anderen Port verwenden

Wenn Port 8000 blockiert ist:
```powershell
.\start-backend.ps1 -Port 8001
```

### Option 3: WSL Ubuntu (Langfristig)

**Vorteile**:
- Linux-Prozess-Management (stabiler)
- Bessere Multiprocessing-Unterstützung
- Keine Zombie-Prozesse

**Nachteile**:
- Zusätzliche Setup-Schritte
- Windows-Pfade müssen angepasst werden

**Setup**:
```bash
# In WSL:
cd /mnt/c/Users/Seidel/OneDrive/CODING/RotaryArchiv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 4: Process Manager (Advanced)

**Supervisor** oder **PM2** können Prozesse besser verwalten, aber das ist Overkill für Development.

## Empfehlung

**Für Development**:
- `uvicorn` **OHNE** `--reload` verwenden
- Bei Code-Änderungen: Backend manuell neu starten (Ctrl+C, dann wieder starten)
- `.\start-backend.ps1` verwenden (prüft Port, beendet alte Prozesse)

**Für Production**:
- `uvicorn` OHNE `--reload` (oder mit Gunicorn)
- Process Manager verwenden (systemd, supervisor, etc.)

## Workflow

```powershell
# 1. Backend starten
.\start-backend.ps1

# 2. Code ändern...

# 3. Backend neu starten:
#    - Ctrl+C im Terminal
#    - .\start-backend.ps1 erneut ausführen

# 4. Falls Port blockiert:
.\stop-backend.ps1
.\start-backend.ps1
```

## PowerShell vs. CMD vs. WSL

- **PowerShell**: Gut für Windows, aber Prozess-Management ist gleich
- **CMD**: Ähnliche Probleme wie PowerShell
- **WSL**: Besser für Development, aber Setup-Aufwand

**Fazit**: Das Problem liegt nicht an PowerShell, sondern an `uvicorn --reload` auf Windows. Lösung: `--reload` weglassen oder WSL verwenden.
