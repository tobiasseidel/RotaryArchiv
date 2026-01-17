# Backend Troubleshooting

## Problem: Mehrere Backend-Prozesse laufen gleichzeitig

### Ursache

Wenn `uvicorn` mit `--reload` gestartet wird, passiert folgendes:

1. **Hauptprozess**: Startet den Server und überwacht Dateiänderungen
2. **Worker-Prozesse**: Werden für die eigentliche Verarbeitung gestartet (multiprocessing)
3. **Reloader-Prozess**: Überwacht Code-Änderungen und startet den Server neu

Wenn mehrere Instanzen gestartet werden oder Prozesse nicht sauber beendet werden, bleiben alte Prozesse hängen und blockieren Port 8000.

### Lösung

**1. Alle Backend-Prozesse beenden:**

```powershell
# Verwende das Stop-Script:
.\stop-backend.ps1

# Oder manuell:
Get-Process | Where-Object { $_.ProcessName -like "*python*" } | Where-Object {
    (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*uvicorn*"
} | Stop-Process -Force
```

**2. Port 8000 freigeben:**

```powershell
# Finde Prozesse auf Port 8000:
netstat -ano | findstr :8000

# Beende Prozesse (ersetze PID mit der tatsächlichen Prozess-ID):
Stop-Process -Id <PID> -Force
```

**3. Sauberer Neustart:**

```powershell
# 1. Alle Prozesse beenden
.\stop-backend.ps1

# 2. Warten bis Port frei ist
Start-Sleep -Seconds 2

# 3. Backend neu starten
.\dev.ps1 run
```

### Prävention

**Immer das Stop-Script verwenden:**

```powershell
# Beenden: Ctrl+C im Terminal
# Falls das nicht funktioniert:
.\stop-backend.ps1
```

**Nur eine Instanz starten:**

- Prüfe vor dem Start, ob Port 8000 frei ist
- Verwende `.\dev.ps1 run` statt manueller uvicorn-Aufrufe

### Häufige Probleme

**Problem**: "Port 8000 already in use"
- **Lösung**: `.\stop-backend.ps1` ausführen

**Problem**: "404 Not Found" für neue Endpoints
- **Lösung**: Backend neu starten, damit Code-Änderungen geladen werden

**Problem**: Mehrere Prozesse blockieren Port 8000
- **Lösung**: Alle Prozesse beenden mit `.\stop-backend.ps1`
