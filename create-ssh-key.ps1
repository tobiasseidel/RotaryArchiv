$keyPath = "$env:USERPROFILE\.ssh\id_ed25519"
$comment = "tobias.seidel@posteo.de"

# Generate SSH key (empty passphrase)
$process = Start-Process -FilePath "ssh-keygen" -ArgumentList "-t","ed25519","-C",$comment,"-f",$keyPath,"-N",'',"-q" -Wait -NoNewWindow -PassThru

if ($process.ExitCode -eq 0) {
    Write-Host "SSH-Key erfolgreich erstellt: $keyPath"
} else {
    Write-Host "Fehler beim Erstellen des SSH-Keys. Exit code: $($process.ExitCode)"
}