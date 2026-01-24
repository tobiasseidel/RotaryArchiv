# Worker-Architektur

## Übersicht

Die Anwendung verwendet eine **getrennte Architektur** mit zwei unabhängigen Prozessen:

1. **API-Server** (`main.py`): Verarbeitet HTTP-Requests, erstellt OCR-Jobs
2. **Worker-Prozess** (`ocr/worker.py`): Verarbeitet OCR-Jobs aus der Datenbank

## Vorteile

- ✅ **Sauberes Shutdown**: API-Server kann beendet werden, ohne laufende OCR-Jobs abzubrechen
- ✅ **Unabhängige Skalierung**: Worker kann separat gestartet/gestoppt werden
- ✅ **Bessere Stabilität**: Keine `CancelledError` beim Server-Shutdown
- ✅ **Skalierbarkeit**: Mehrere Worker-Instanzen möglich (später)

## Start

### API-Server starten
```powershell
.\start-backend.ps1
```

### Worker starten
```powershell
.\start-worker.ps1
```

**Wichtig**: Beide Prozesse müssen laufen:
- Der API-Server erstellt Jobs (Status: `PENDING`)
- Der Worker verarbeitet diese Jobs automatisch

## Funktionsweise

1. **Job-Erstellung**: API-Endpoints erstellen OCR-Jobs mit Status `PENDING` in der Datenbank
2. **Job-Verarbeitung**: Worker prüft kontinuierlich (alle 5 Sekunden) auf neue `PENDING`-Jobs
3. **Status-Updates**: Worker aktualisiert Job-Status (`RUNNING` → `COMPLETED` / `FAILED`)

## Shutdown

### API-Server beenden
- `Ctrl+C` im Terminal
- Oder: `.\stop-backend.ps1`

### Worker beenden
- `Ctrl+C` im Terminal (wartet auf Abschluss des aktuellen Jobs)
- Oder: `.\stop-worker.ps1`

**Hinweis**: Beim Worker-Shutdown wird der aktuelle Job zurückgesetzt (`PENDING`), damit er beim nächsten Start erneut verarbeitet werden kann.

## Fehlerbehandlung

- **Worker-Fehler**: Werden geloggt, Job-Status wird auf `FAILED` gesetzt
- **Server-Fehler**: Betreffen nur HTTP-Requests, laufende Jobs im Worker werden nicht beeinflusst
- **Datenbank-Fehler**: Werden vom Worker abgefangen und geloggt

## Monitoring

- Worker-Logs zeigen alle verarbeiteten Jobs
- Job-Status kann über API-Endpoints abgefragt werden
- Frontend zeigt Job-Status in Echtzeit
