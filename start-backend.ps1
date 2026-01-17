# Sauberer Backend-Start mit Port-Prüfung
# Verwendung: .\start-backend.ps1

param(
    [int]$Port = 8000
)

Write-Host "Prüfe Port $Port..." -ForegroundColor Yellow

# Prüfe ob Port belegt ist
$portInUse = netstat -ano | findstr ":$Port " | findstr "LISTENING"
if ($portInUse) {
    Write-Host "[FEHLER] Port $Port ist bereits belegt!" -ForegroundColor Red
    Write-Host "`nBeende alte Prozesse..." -ForegroundColor Yellow

    # Versuche alte Prozesse zu finden und zu beenden
    $processes = Get-Process | Where-Object {
        $_.ProcessName -like "*python*"
    } | Where-Object {
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*uvicorn*" -or $cmdLine -like "*port $Port*"
    }

    if ($processes) {
        foreach ($proc in $processes) {
            Write-Host "  Beende Prozess $($proc.Id)..." -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }

    # Prüfe nochmal
    $portInUse = netstat -ano | findstr ":$Port " | findstr "LISTENING"
    if ($portInUse) {
        Write-Host "[FEHLER] Port $Port ist immer noch belegt!" -ForegroundColor Red
        Write-Host "Bitte beende die Prozesse manuell oder verwende einen anderen Port:" -ForegroundColor Yellow
        Write-Host "  .\start-backend.ps1 -Port 8001" -ForegroundColor Cyan
        exit 1
    }
}

Write-Host "[OK] Port $Port ist frei" -ForegroundColor Green
Write-Host "`nStarte Backend auf Port $Port..." -ForegroundColor Yellow
Write-Host "Server läuft auf: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Drücke Ctrl+C zum Beenden`n" -ForegroundColor Yellow

# Starte uvicorn OHNE --reload für stabileren Betrieb
# Mit --reload nur wenn explizit gewünscht
$useReload = $false
if ($env:UVICORN_RELOAD -eq "true") {
    $useReload = $true
    Write-Host "Hinweis: Auto-Reload ist aktiviert (langsamer, kann Probleme verursachen)" -ForegroundColor Yellow
}

if ($useReload) {
    uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port $Port
} else {
    uvicorn src.rotary_archiv.main:app --host 0.0.0.0 --port $Port
}
