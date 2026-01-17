# RotaryArchiv - PowerShell Development Script
# Verwendung: .\dev.ps1 <command>
# Beispiel: .\dev.ps1 install-dev

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "RotaryArchiv - Verfügbare Commands:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  .\dev.ps1 install          - Installiere Production-Dependencies" -ForegroundColor Green
    Write-Host "  .\dev.ps1 install-dev      - Installiere Development-Dependencies" -ForegroundColor Green
    Write-Host "  .\dev.ps1 lint             - Führe Linting aus (Ruff)" -ForegroundColor Green
    Write-Host "  .\dev.ps1 format           - Formatiere Code (Ruff)" -ForegroundColor Green
    Write-Host "  .\dev.ps1 lint-fix        - Linting mit Auto-Fix" -ForegroundColor Green
    Write-Host "  .\dev.ps1 test             - Führe Tests aus" -ForegroundColor Green
    Write-Host "  .\dev.ps1 test-verbose     - Tests mit Verbose-Output" -ForegroundColor Green
    Write-Host "  .\dev.ps1 coverage        - Führe Tests mit Coverage-Report aus" -ForegroundColor Green
    Write-Host "  .\dev.ps1 run              - Starte FastAPI Server (ohne Auto-Reload, empfohlen)" -ForegroundColor Green
    Write-Host "  .\dev.ps1 run-reload       - Starte Server mit Auto-Reload (kann Probleme verursachen)" -ForegroundColor Yellow
    Write-Host "  .\dev.ps1 run-prod        - Starte Server (Production-Mode)" -ForegroundColor Green
    Write-Host "  .\dev.ps1 stop             - Beende alle Backend-Prozesse" -ForegroundColor Green
    Write-Host "  .\dev.ps1 migrate         - Führe Datenbank-Migrationen aus" -ForegroundColor Green
    Write-Host "  .\dev.ps1 migrate-create   - Erstelle neue Migration (MESSAGE='Beschreibung')" -ForegroundColor Green
    Write-Host "  .\dev.ps1 pre-commit-install - Installiere Pre-commit Hooks" -ForegroundColor Green
    Write-Host "  .\dev.ps1 pre-commit-run   - Führe Pre-commit Hooks aus" -ForegroundColor Green
    Write-Host "  .\dev.ps1 clean           - Entferne temporäre Dateien" -ForegroundColor Green
    Write-Host ""
}

function Install-Dependencies {
    Write-Host "Installiere Production-Dependencies..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    Write-Host "Fertig!" -ForegroundColor Green
}

function Install-DevDependencies {
    Write-Host "Installiere Development-Dependencies..." -ForegroundColor Yellow
    Install-Dependencies
    pip install -r requirements-dev.txt
    Write-Host "Fertig! Führe '.\dev.ps1 pre-commit-install' aus, um Pre-commit Hooks zu installieren." -ForegroundColor Green
}

function Invoke-Lint {
    Write-Host "Führe Linting aus..." -ForegroundColor Yellow
    ruff check src/ tests/
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Linting erfolgreich!" -ForegroundColor Green
    } else {
        Write-Host "Linting-Fehler gefunden!" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Invoke-Format {
    Write-Host "Formatiere Code..." -ForegroundColor Yellow
    ruff format src/ tests/
    Write-Host "Formatierung abgeschlossen!" -ForegroundColor Green
}

function Invoke-LintFix {
    Write-Host "Führe Linting mit Auto-Fix aus..." -ForegroundColor Yellow
    ruff check --fix src/ tests/
    Write-Host "Fertig!" -ForegroundColor Green
}

function Invoke-Test {
    Write-Host "Führe Tests aus..." -ForegroundColor Yellow
    pytest
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Invoke-TestVerbose {
    Write-Host "Führe Tests mit Verbose-Output aus..." -ForegroundColor Yellow
    pytest -v
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Invoke-Coverage {
    Write-Host "Führe Tests mit Coverage-Report aus..." -ForegroundColor Yellow
    pytest --cov=src.rotary_archiv --cov-report=html --cov-report=term
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Coverage-Report erstellt: htmlcov\index.html" -ForegroundColor Green
    } else {
        exit $LASTEXITCODE
    }
}

function Start-Server {
    param(
        [switch]$Reload
    )

    Write-Host "Starte FastAPI Server..." -ForegroundColor Yellow
    Write-Host "Server läuft auf: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "Drücke Ctrl+C zum Beenden" -ForegroundColor Yellow

    if ($Reload) {
        Write-Host "Hinweis: Auto-Reload aktiviert (kann auf Windows Probleme verursachen)" -ForegroundColor Yellow
        uvicorn src.rotary_archiv.main:app --reload --host 0.0.0.0 --port 8000
    } else {
        Write-Host "Hinweis: Auto-Reload deaktiviert (stabiler auf Windows)" -ForegroundColor Green
        Write-Host "Bei Code-Aenderungen: Ctrl+C und erneut starten" -ForegroundColor Gray
        uvicorn src.rotary_archiv.main:app --host 0.0.0.0 --port 8000
    }
}

function Start-ServerProd {
    Write-Host "Starte FastAPI Server (Production-Mode)..." -ForegroundColor Yellow
    Write-Host "Server läuft auf: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "Drücke Ctrl+C zum Beenden" -ForegroundColor Yellow
    uvicorn src.rotary_archiv.main:app --host 0.0.0.0 --port 8000
}

function Invoke-Migrate {
    Write-Host "Führe Datenbank-Migrationen aus..." -ForegroundColor Yellow
    alembic upgrade head
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Migrationen erfolgreich!" -ForegroundColor Green
    } else {
        Write-Host "Fehler bei Migrationen!" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function New-Migration {
    param([string]$Message)

    if ([string]::IsNullOrWhiteSpace($Message)) {
        Write-Host "Fehler: Bitte MESSAGE angeben!" -ForegroundColor Red
        Write-Host "Verwendung: .\dev.ps1 migrate-create -Message 'Beschreibung'" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Erstelle neue Migration: $Message" -ForegroundColor Yellow
    alembic revision --autogenerate -m $Message
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Migration erstellt!" -ForegroundColor Green
    } else {
        exit $LASTEXITCODE
    }
}

function Install-PreCommit {
    Write-Host "Installiere Pre-commit Hooks..." -ForegroundColor Yellow
    pre-commit install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pre-commit Hooks installiert!" -ForegroundColor Green
    } else {
        Write-Host "Fehler beim Installieren der Pre-commit Hooks!" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

function Invoke-PreCommit {
    Write-Host "Führe Pre-commit Hooks aus..." -ForegroundColor Yellow
    pre-commit run --all-files
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Clear-TempFiles {
    Write-Host "Entferne temporäre Dateien..." -ForegroundColor Yellow

    # Python Cache
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Filter "*.pyo" | Remove-Item -Force -ErrorAction SilentlyContinue

    # Build Artefakte
    Get-ChildItem -Path . -Recurse -Directory -Filter "*.egg-info" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    # Testing
    if (Test-Path ".pytest_cache") { Remove-Item -Path ".pytest_cache" -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path ".ruff_cache") { Remove-Item -Path ".ruff_cache" -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path "htmlcov") { Remove-Item -Path "htmlcov" -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path ".coverage") { Remove-Item -Path ".coverage" -Force -ErrorAction SilentlyContinue }
    Get-ChildItem -Path . -Filter ".coverage.*" | Remove-Item -Force -ErrorAction SilentlyContinue

    # Build
    if (Test-Path "dist") { Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path "build") { Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue }

    Write-Host "Temporäre Dateien entfernt!" -ForegroundColor Green
}

# Main Command Router
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "install-dev" { Install-DevDependencies }
    "lint" { Invoke-Lint }
    "format" { Invoke-Format }
    "lint-fix" { Invoke-LintFix }
    "test" { Invoke-Test }
    "test-verbose" { Invoke-TestVerbose }
    "coverage" { Invoke-Coverage }
    "run" { Start-Server }
    "run-reload" { Start-Server -Reload }
    "run-prod" { Start-ServerProd }
    "stop" {
        Write-Host "Beende alle Backend-Prozesse..." -ForegroundColor Yellow
        if (Test-Path ".\stop-backend.ps1") {
            .\stop-backend.ps1
        } else {
            Write-Host "[FEHLER] stop-backend.ps1 nicht gefunden!" -ForegroundColor Red
        }
    }
    "migrate" { Invoke-Migrate }
    "migrate-create" {
        if ($args.Count -gt 0) {
            $message = $args -join " "
            New-Migration -Message $message
        } else {
            Write-Host "Fehler: Bitte MESSAGE angeben!" -ForegroundColor Red
            Write-Host "Verwendung: .\dev.ps1 migrate-create 'Beschreibung'" -ForegroundColor Yellow
            exit 1
        }
    }
    "pre-commit-install" { Install-PreCommit }
    "pre-commit-run" { Invoke-PreCommit }
    "clean" { Clear-TempFiles }
    default {
        Write-Host "Unbekannter Command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
