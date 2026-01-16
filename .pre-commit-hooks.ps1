# Pre-commit Hooks für PowerShell-Skripte
# Diese Datei wird von .pre-commit-config.yaml verwendet
# Pre-commit übergibt Dateinamen als Argumente

$hasErrors = $false

# Dateien aus Argumenten lesen (pre-commit übergibt sie als separate Argumente)
$Files = $args

if ($Files.Count -eq 0) {
    Write-Host "Keine Dateien zum Prüfen übergeben." -ForegroundColor Yellow
    exit 0
}

foreach ($file in $Files) {
    if (-not (Test-Path $file)) {
        Write-Warning "Datei nicht gefunden: $file"
        continue
    }

    Write-Host "Prüfe PowerShell-Skript: $file" -ForegroundColor Cyan

    # 1. Syntax-Check
    try {
        $content = Get-Content $file -Raw -ErrorAction Stop
        $errors = $null
        $null = [System.Management.Automation.PSParser]::Tokenize($content, [ref]$errors)

        if ($errors) {
            Write-Host "  Syntax-Fehler gefunden:" -ForegroundColor Red
            foreach ($error in $errors) {
                Write-Host "    Zeile $($error.Token.StartLine): $($error.Message)" -ForegroundColor Red
            }
            $hasErrors = $true
        } else {
            Write-Host "  Syntax-Check: OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Fehler beim Syntax-Check: $_" -ForegroundColor Red
        $hasErrors = $true
    }

    # 2. PSScriptAnalyzer (falls verfügbar)
    if (Get-Module -ListAvailable -Name PSScriptAnalyzer) {
        try {
            Import-Module PSScriptAnalyzer -ErrorAction Stop
            $results = Invoke-ScriptAnalyzer -Path $file -ErrorAction SilentlyContinue

            if ($results) {
                Write-Host "  PSScriptAnalyzer-Findings:" -ForegroundColor Yellow
                foreach ($result in $results) {
                    $severity = switch ($result.Severity) {
                        "Error" { "Red" }
                        "Warning" { "Yellow" }
                        "Information" { "Cyan" }
                        default { "White" }
                    }
                    Write-Host "    [$($result.RuleName)] Zeile $($result.Line): $($result.Message)" -ForegroundColor $severity
                }
                # Nur Errors als Fehler behandeln
                if ($results | Where-Object { $_.Severity -eq "Error" }) {
                    $hasErrors = $true
                }
            } else {
                Write-Host "  PSScriptAnalyzer: OK" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Fehler beim PSScriptAnalyzer: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  PSScriptAnalyzer nicht installiert (optional)" -ForegroundColor Gray
    }

    # 3. Basis-Checks
    $content = Get-Content $file -Raw

    # Prüfe auf hardcodierte Pfade (Warnung)
    if ($content -match 'C:\\Users\\|C:\\Windows\\|/home/|/usr/') {
        Write-Host "  Warnung: Hardcodierte Pfade gefunden (sollten vermieden werden)" -ForegroundColor Yellow
    }

    # Prüfe auf ExecutionPolicy Bypass (Warnung)
    if ($content -match 'ExecutionPolicy\s+Bypass') {
        Write-Host "  Warnung: ExecutionPolicy Bypass gefunden (Sicherheitsrisiko)" -ForegroundColor Yellow
    }

    Write-Host ""
}

if ($hasErrors) {
    Write-Host "PowerShell-Skripte haben Fehler. Bitte beheben vor dem Commit." -ForegroundColor Red
    exit 1
} else {
    Write-Host "Alle PowerShell-Skripte sind OK!" -ForegroundColor Green
    exit 0
}
