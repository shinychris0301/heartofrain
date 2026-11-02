param(
    [string]$InterfaceAlias = 'Ethernet',
    [ValidateRange(1024, 65535)][int]$LocalPort = 13389,
    [switch]$NoClient
)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$python = Join-Path $project 'Backend\.venv\Scripts\python.exe'
$relay = Join-Path $PSScriptRoot 'rdp_ethernet_relay.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Project Python environment is missing.' }

$addresses = @(Get-NetIPAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4 |
    Where-Object { $_.AddressState -eq 'Preferred' -and -not $_.SkipAsSource })
if ($addresses.Count -ne 1) { throw 'Select an interface with exactly one preferred IPv4 address.' }
if (Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue) {
    throw "Local port $LocalPort is already in use; verify its owner before connecting."
}

$process = Start-Process -FilePath $python -ArgumentList @($relay, '--source-ip', $addresses[0].IPAddress,
    '--listen-port', [string]$LocalPort) -WorkingDirectory $project -WindowStyle Hidden -PassThru
$listener = $null
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 250
    $listener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
    if ($listener) { break }
    if ($process.HasExited) { throw 'The local RDP relay exited before listening.' }
}
if (-not $listener) { throw 'The local RDP relay did not start.' }
Write-Output "RDP relay ready at 127.0.0.1:$LocalPort via $($addresses[0].IPAddress)."
if (-not $NoClient) {
    Start-Process -FilePath "$env:WINDIR\System32\mstsc.exe" -ArgumentList @(
        "/v:127.0.0.1:$LocalPort", '/prompt', '/admin', '/public') -WindowStyle Normal
}
