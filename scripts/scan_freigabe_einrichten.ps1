# Scan-Eingang fuer den Brother im Netz freigeben (Scan to Network / SMB).
# Legt ein eigenes Windows-Konto "scanner" an (darf nur in den Scan-Eingang schreiben),
# gibt den Ordner als \\<PC>\Scan-Eingang frei und oeffnet die Freigabe in der Firewall
# nur fuer den Brother. Das Passwort tippst du selbst, es erscheinen nur Sternchen.
# Aufruf (PowerShell als Administrator, im CEO-GPT-Ordner):
#   powershell -ExecutionPolicy Bypass -File scripts\scan_freigabe_einrichten.ps1
# Bekommt der Brother eine neue IP: Skript mit -BrotherIP <neue IP> erneut starten.

param(
    [string]$BrotherIP = "172.17.1.134",
    [string]$Ordner    = "C:\PrimaerBau-Belege\Scan-Eingang",
    [string]$Konto     = "scanner",
    [string]$Freigabe  = "Scan-Eingang"
)

$ErrorActionPreference = "Stop"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Host "Bitte PowerShell als Administrator starten." -ForegroundColor Yellow; exit 1 }
if (-not (Test-Path $Ordner)) { New-Item -ItemType Directory -Path $Ordner | Out-Null }

# 1. Konto "scanner" (kein Admin, Passwort laeuft nicht ab, nicht auf dem Anmeldebildschirm)
$benutzer = Get-LocalUser -Name $Konto -ErrorAction SilentlyContinue
$pw = Read-Host "Passwort fuer das Konto '$Konto' (wird gleich auch im Brother eingetragen)" -AsSecureString
if ($benutzer) {
    Set-LocalUser -Name $Konto -Password $pw -PasswordNeverExpires $true
    Write-Host "Konto '$Konto' gab es schon, Passwort neu gesetzt." -ForegroundColor Green
} else {
    New-LocalUser -Name $Konto -Password $pw -PasswordNeverExpires -UserMayNotChangePassword `
        -Description "Nur fuer Scans vom Brother in den Scan-Eingang" | Out-Null
    Write-Host "Konto '$Konto' angelegt." -ForegroundColor Green
}
Remove-Variable pw
$liste = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
if (-not (Test-Path $liste)) { New-Item -Path $liste -Force | Out-Null }
New-ItemProperty -Path $liste -Name $Konto -Value 0 -PropertyType DWord -Force | Out-Null

# 2. Ordnerrechte: scanner darf im Scan-Eingang schreiben, sonst nirgends
$acl = Get-Acl $Ordner
$regel = New-Object Security.AccessControl.FileSystemAccessRule("$env:COMPUTERNAME\$Konto", "Modify", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.AddAccessRule($regel)
Set-Acl -Path $Ordner -AclObject $acl
Write-Host "Ordnerrechte gesetzt." -ForegroundColor Green

# 3. Freigabe \\PC\Scan-Eingang (nur scanner und das eigene Konto)
if (Get-SmbShare -Name $Freigabe -ErrorAction SilentlyContinue) { Remove-SmbShare -Name $Freigabe -Force }
New-SmbShare -Name $Freigabe -Path $Ordner -ChangeAccess "$env:COMPUTERNAME\$Konto" -FullAccess "$env:USERDOMAIN\$env:USERNAME" `
    -Description "Scans vom Brother fuer das CEO-GPT" | Out-Null
Write-Host "Freigabe \\$env:COMPUTERNAME\$Freigabe eingerichtet." -ForegroundColor Green

# 4. Firewall: Datei-Freigabe (TCP 445) nur fuer den Brother oeffnen, das Netz bleibt "oeffentlich"
$name = "CEO-GPT Scan-Eingang vom Brother"
Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $name -Direction Inbound -Protocol TCP -LocalPort 445 `
    -RemoteAddress $BrotherIP -Profile Any -Action Allow | Out-Null
Write-Host "Firewall: Zugriff nur vom Brother ($BrotherIP) erlaubt." -ForegroundColor Green

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like ($BrotherIP.Substring(0, $BrotherIP.LastIndexOf('.')) + ".*") }).IPAddress
Write-Host ""
Write-Host "Im Brother eintragen (Scan to Network Profil):" -ForegroundColor Cyan
Write-Host "  Host-Adresse:   $env:COMPUTERNAME   (falls das nicht klappt: $ip)"
Write-Host "  Zielordner:     $Freigabe"
Write-Host "  Benutzername:   $env:COMPUTERNAME\$Konto"
Write-Host "  Passwort:       das eben gewaehlte"
