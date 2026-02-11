# Tests mit venv311 ausführen (ohne Coverage, da pytest.ini --cov verlangt).
# Nutzung: .\run-tests.ps1 [pytest-args]
# Beispiele:
#   .\run-tests.ps1
#   .\run-tests.ps1 tests\test_ocr\test_multibox_region.py
#   .\run-tests.ps1 tests\test_ocr\ -v

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$py = Join-Path $root "venv311\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "venv311 nicht gefunden. Bitte zuerst: python -m venv venv311"
    exit 1
}

& $py -m pytest -o addopts= -v --tb=short @args
