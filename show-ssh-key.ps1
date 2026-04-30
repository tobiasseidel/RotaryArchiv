$keyPath = "$env:USERPROFILE\.ssh\id_ed25519.pub"
if (Test-Path $keyPath) {
    Write-Host "Dein öffentlicher SSH-Key (kopiere dies nach GitHub unter Settings → SSH Keys):"
    Write-Host "---"
    Get-Content $keyPath
    Write-Host "---"
} else {
    Write-Host "Noch kein SSH-Key vorhanden. Erstell ihn mit:"
    Write-Host "ssh-keygen -t ed25519 -C 'tobias.seidel@posteo.de' -f `"`$env:USERPROFILE\.ssh\id_ed25519`""
}