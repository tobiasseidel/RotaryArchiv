# Start-Skript für OCR-Worker
# Verwendung: .\start-worker.ps1

Write-Host "Starte OCR-Worker..." -ForegroundColor Yellow
Write-Host "Der Worker verarbeitet OCR-Jobs aus der Datenbank." -ForegroundColor Cyan
Write-Host "Drücke Ctrl+C zum Beenden`n" -ForegroundColor Yellow

# Starte Worker
python -m src.rotary_archiv.ocr.worker
