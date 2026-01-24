# Stop-Skript für OCR-Worker
# Verwendung: .\stop-worker.ps1

Write-Host "Suche nach laufenden OCR-Worker-Prozessen..." -ForegroundColor Yellow

# Finde Python-Prozesse, die den Worker ausführen
$processes = Get-Process | Where-Object {
    $_.ProcessName -like "*python*"
} | Where-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    $cmdLine -like "*ocr.worker*" -or $cmdLine -like "*worker.py*"
}

if ($processes) {
    foreach ($proc in $processes) {
        Write-Host "  Beende Worker-Prozess $($proc.Id)..." -ForegroundColor Gray
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[OK] Worker-Prozesse beendet" -ForegroundColor Green
} else {
    Write-Host "[INFO] Keine laufenden Worker-Prozesse gefunden" -ForegroundColor Cyan
}
