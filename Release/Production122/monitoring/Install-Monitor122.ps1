<# Creates a NEW monitor directory and NEW LocalService task. It never changes the API/Caddy services. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$PythonSHA256,
    [Parameter(Mandatory=$true)][string]$MonitorSource,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$MonitorSHA256,
    [string]$MonitorRoot = 'C:\ProgramData\HeartOfTheRain\monitor122',
    [string]$Origin = 'https://api.novamind-it.ru',
    [ValidateRange(1024,65535)][int]$LoopbackPort = 8751,
    [string]$BackupManifest = '',
    [string]$TaskName = 'HOTRMonitor122'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-PlainAbsolutePath([string]$Value, [bool]$FileRequired) {
    if ($Value -notmatch '^[A-Za-z]:\\' -or $Value -match '["\x00-\x1F]' -or
        [IO.Path]::GetFullPath($Value) -ne $Value) { throw 'Absolute canonical local path required' }
    $cursor = $Value
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Linked path rejected' }
        }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
    if ($FileRequired -and -not (Test-Path -LiteralPath $Value -PathType Leaf)) { throw 'Required file missing' }
}

# Complete read-only preflight BEFORE creating the new monitor root/task.
foreach ($value in @($PythonExe, $MonitorSource, $MonitorRoot)) { Assert-PlainAbsolutePath $value ($value -ne $MonitorRoot) }
if ($BackupManifest) { Assert-PlainAbsolutePath $BackupManifest $true }
if ($TaskName -notmatch '^HOTRMonitor122(?:-[A-Za-z0-9-]{1,24})?$') { throw 'Scoped monitor task name required' }
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) { throw 'Task exists; existing task preserved' }
if (Test-Path -LiteralPath $MonitorRoot) { throw 'Monitor root exists; existing files preserved' }
if (-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($MonitorRoot)) -PathType Container)) { throw 'Existing private parent required' }
if ((Get-FileHash -LiteralPath $PythonExe -Algorithm SHA256).Hash -ne $PythonSHA256) { throw 'Python executable hash mismatch' }
if ((Get-FileHash -LiteralPath $MonitorSource -Algorithm SHA256).Hash -ne $MonitorSHA256) { throw 'Monitor source hash mismatch' }
$uri = [Uri]$Origin
if ($Origin.Length -gt 512 -or $uri.Scheme -ne 'https' -or $uri.Port -ne 443 -or $uri.AbsolutePath -ne '/' -or
    $uri.UserInfo -or $uri.Query -or $uri.Fragment -or $Origin -match '["\x00-\x20]') { throw 'Owned HTTPS origin required' }
$dnsHost = $uri.DnsSafeHost.ToLowerInvariant()
if ($dnsHost -notmatch '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$' -or -not $dnsHost.Contains('.') -or
    $dnsHost.Contains('..') -or $dnsHost -match '^[0-9.]+$' -or
    $dnsHost -match '(^|\.)(example\.com|example\.net|example\.org|example|invalid|test|local|localhost)$') {
    throw 'Owned public DNS HTTPS origin required'
}
$fixedDrive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($MonitorRoot))
if ($fixedDrive.DriveType -ne [IO.DriveType]::Fixed) { throw 'Fixed local monitor storage required' }

# The service account can execute the immutable monitor and modify only status/.
$null = New-Item -ItemType Directory -Path $MonitorRoot
& icacls.exe $MonitorRoot /inheritance:r | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Monitor ACL inheritance change failed; partial root preserved' }
& icacls.exe $MonitorRoot /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-19:(OI)(CI)RX' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Monitor ACL grant failed; partial root preserved' }
$destination = Join-Path $MonitorRoot 'monitoring122.py'
Copy-Item -LiteralPath $MonitorSource -Destination $destination -ErrorAction Stop
if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $MonitorSHA256) { throw 'Copied monitor hash mismatch' }
$statusDirectory = Join-Path $MonitorRoot 'status'
$null = New-Item -ItemType Directory -Path $statusDirectory
& icacls.exe $statusDirectory /grant:r '*S-1-5-19:(OI)(CI)M' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Status ACL grant failed; partial root preserved' }
$statusFile = Join-Path $statusDirectory 'latest.json'
$eventsFile = Join-Path $statusDirectory 'events.jsonl'
$arguments = '-I -B "' + $destination + '" check --origin "' + $Origin.TrimEnd('/') +
    '" --expected-mode staging --loopback-port ' + $LoopbackPort + ' --timeout 3 --latency-ms 2500 --report-file "' + $statusFile + '" --events-file "' + $eventsFile + '"'
if ($BackupManifest) {
    $arguments += ' --backup-manifest "' + $BackupManifest + '" --max-backup-age-hours 24 --min-free-mib 1024'
}
$action = New-ScheduledTaskAction -Execute $PythonExe -Argument $arguments -WorkingDirectory $MonitorRoot
$principal = New-ScheduledTaskPrincipal -UserId 'S-1-5-19' -LogonType ServiceAccount -RunLevel Limited
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Seconds 45)
$task = New-ScheduledTask -Action $action -Principal $principal -Trigger $trigger -Settings $settings -Description 'Heart of the Rain availability and optional backup metadata monitor; no production/provider approval.'
$null = Register-ScheduledTask -TaskName $TaskName -InputObject $task -ErrorAction Stop
Start-ScheduledTask -TaskName $TaskName
[ordered]@{status='monitor_task_registered'; task=$TaskName; statusFile=$statusFile; sourceSHA256=$MonitorSHA256.ToLowerInvariant();
    account='LocalService'; apiServiceChanged=$false; caddyChanged=$false; externalAlertDeliveryVerified=$false} | ConvertTo-Json -Compress
