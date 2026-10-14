# GitHub-Token verdeckt in der Windows-Anmeldeinformationsverwaltung hinterlegen.
# Der Token erscheint nirgends auf dem Schirm, landet in keiner Datei und nicht im Chat.
# Aufruf (im CEO-GPT-Ordner):  powershell -ExecutionPolicy Bypass -File scripts\github_token_hinterlegen.ps1

param([string]$Benutzer = "Arberoo")

Set-Location (Split-Path -Parent $PSScriptRoot)

$sicher = Read-Host "GitHub-Token einfuegen (Rechtsklick oder Strg+V, dann Enter; es erscheinen nur Sternchen)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sicher)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim()
    if (-not $token.StartsWith("github_pat_")) {
        Write-Host "Das sieht nicht nach einem fine-grained Token aus (der beginnt mit github_pat_). Nichts gespeichert." -ForegroundColor Yellow
        exit 1
    }
    # Alten Eintrag fuer github.com entfernen, dann den neuen ablegen
    "protocol=https`nhost=github.com`n" | git credential reject
    "protocol=https`nhost=github.com`nusername=$Benutzer`npassword=$token`n" | git credential approve
    Write-Host "Token ist in der Windows-Anmeldeinformationsverwaltung hinterlegt." -ForegroundColor Green
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    Remove-Variable token, sicher -ErrorAction SilentlyContinue
}

# Pruefen, ob der Zugriff auf das Repo klappt (zeigt keine Geheimnisse an)
if (git remote 2>$null | Select-String -Quiet "origin") {
    git ls-remote origin *> $null
    if ($LASTEXITCODE -eq 0) { Write-Host "Test: Zugriff auf das Repo klappt." -ForegroundColor Green }
    else { Write-Host "Test: Zugriff klappt noch nicht. Repo-Name oder Token-Rechte pruefen." -ForegroundColor Yellow }
}
