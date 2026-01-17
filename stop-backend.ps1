# Script zum sauberen Beenden aller Backend-Prozesse
# Verwendung: .\stop-backend.ps1

Write-Host "Suche nach uvicorn/Backend-Prozessen..." -ForegroundColor Yellow

# Finde alle Python-Prozesse, die uvicorn ausführen
$uvicornProcesses = Get-Process | Where-Object {
    $_.ProcessName -like "*python*" -and
    (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*uvicorn*"
}

if ($uvicornProcesses.Count -eq 0) {
    Write-Host "Keine uvicorn-Prozesse gefunden." -ForegroundColor Green
    exit 0
}

Write-Host "Gefundene Prozesse:" -ForegroundColor Cyan
foreach ($proc in $uvicornProcesses) {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
    Write-Host "  PID $($proc.Id): $cmdLine" -ForegroundColor Gray
}

# Beende alle Prozesse
Write-Host "`nBeende Prozesse..." -ForegroundColor Yellow
foreach ($proc in $uvicornProcesses) {
    try {
        Stop-Process -Id $proc.Id -Force -ErrorAction Stop
        Write-Host "  [OK] Prozess $($proc.Id) beendet" -ForegroundColor Green
    } catch {
        Write-Host "  [FEHLER] Konnte Prozess $($proc.Id) nicht beenden: $_" -ForegroundColor Red
    }
}

# Warte kurz, damit Prozesse Zeit haben zu beenden
Start-Sleep -Seconds 2

# Prüfe ob Port 8000 noch belegt ist
$port8000 = netstat -ano | findstr :8000
if ($port8000) {
    Write-Host "`nWarnung: Port 8000 ist noch belegt!" -ForegroundColor Yellow
    Write-Host "Möglicherweise gibt es noch hängengebliebene Prozesse." -ForegroundColor Yellow
    Write-Host "Versuche alle Prozesse auf Port 8000 zu beenden..." -ForegroundColor Yellow

    # Extrahiere PIDs von Port 8000
    $pids = $port8000 | ForEach-Object {
        if ($_ -match '\s+(\d+)$') {
            $matches[1]
        }
    } | Select-Object -Unique

    foreach ($processId in $pids) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host "  [OK] Prozess $processId beendet" -ForegroundColor Green
        } catch {
            Write-Host "  [FEHLER] Konnte Prozess $processId nicht beenden: $_" -ForegroundColor Red
        }
    }
} else {
    Write-Host "`nPort 8000 ist frei." -ForegroundColor Green
}

Write-Host "`nFertig!" -ForegroundColor Green
