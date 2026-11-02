# Review 136 Level 17 cutover. Run once in an elevated PowerShell on the VPS, AFTER Deploy136.ps1
# and when the app build that carries the new Level 17 is the one players use.
#   Check only, changes nothing:  powershell -ExecutionPolicy Bypass -File .\CutoverLevel17.ps1 -Check
#   Cut over:                     powershell -ExecutionPolicy Bypass -File .\CutoverLevel17.ps1
# Older app builds, including 130, answer "Could not start" on Level 17 after this. Other levels are unaffected.
# An unfinished attempt already on Level 17 can no longer verify and ends through the normal exit.
# The catalog, the worker's level file, its pins, its approval and the manifest's approval hash
# must change together, because the service refuses to start if they disagree. Any failed
# health check restores all of them. No credentials are embedded or printed.
param([switch]$Check)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$OldLevel='9b196ae5a76366a1f9c9ba1ac2b6c7ec882ad690524471f2c07ea057f0b8323a'
$Here=Split-Path -Parent $MyInvocation.MyCommand.Path
$NewLevelFile=Join-Path $Here 'Level17Cutover136\C01_L017.json'
$NewCatalogFile=Join-Path $Here 'Level17Cutover136\levels.json'
$Backend='C:\Apps\HeartOfTheRain\Monetization126\Backend'
$Catalog=Join-Path $Backend 'config\levels.json'
$Services='C:\ProgramData\HeartOfTheRain\services'
$Manifest=Join-Path $Services 'staging-manifest.json'
$Stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddHHmmss')
$Backup='C:\ProgramData\HeartOfTheRain\Level17Backup\'+$Stamp
$Utf8=New-Object Text.UTF8Encoding($false)
function Sha([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function ShaBytes([byte[]]$Raw){$a=[Security.Cryptography.SHA256]::Create();try{-join($a.ComputeHash($Raw)|ForEach-Object{$_.ToString('x2')})}finally{$a.Dispose()}}
function Up([string]$Url){try{(Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8).StatusCode -eq 200}catch{$false}}
function WaitUp([string]$Url,[int]$Seconds){$end=(Get-Date).AddSeconds($Seconds);while((Get-Date) -lt $end){if(Up $Url){return $true};Start-Sleep -Seconds 2};return $false}
function Swap([string]$Text,[string]$Old,[string]$New,[string]$Name){
    $count=([regex]::Matches($Text,[regex]::Escape($Old))).Count
    if($count -lt 1){throw 'Expected hash not found in '+$Name}
    return $Text.Replace($Old,$New)
}
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Run this in an elevated PowerShell.'}
foreach($path in @($NewLevelFile,$NewCatalogFile,$Catalog,$Manifest)){if(-not (Test-Path -LiteralPath $path)){throw 'Missing: '+$path}}
$manifestText=[IO.File]::ReadAllText($Manifest)
$m=$manifestText | ConvertFrom-Json
$Bundle=$m.replay.bundle;$ApprovalFile=$m.replay.approvalFile;$OldApproval=$m.replay.approvalSHA256
if(-not $m.replay.enabled){throw 'Replay is not enabled in the staging manifest.'}
$PinsFile=Join-Path $Bundle 'ReplayPins\manifest.json'
$LevelFile=Join-Path $Bundle 'ReplayPins\Levels\C01_L017.json'
foreach($path in @($Bundle,$ApprovalFile,$PinsFile,$LevelFile)){if(-not (Test-Path -LiteralPath $path)){throw 'Missing: '+$path}}
$NewLevel=Sha $NewLevelFile
if((Sha $LevelFile) -eq $NewLevel){Write-Output 'Level 17 is already cut over.';return}
if((Sha $LevelFile) -ne $OldLevel){throw 'Unexpected Level 17 in the worker bundle.'}
if((Sha $ApprovalFile) -ne $OldApproval){throw 'The worker approval does not match the manifest.'}
if((Get-Service 'HOTRStaging').Status -ne 'Running'){throw 'HOTRStaging is not running'}
if(-not (Up 'http://127.0.0.1:8751/readyz')){throw 'The API is not ready before cutover.'}
$OldPins=Sha $PinsFile
$pinsNew=Swap ([IO.File]::ReadAllText($PinsFile)) $OldLevel $NewLevel 'the worker pins'
$NewPins=ShaBytes ($Utf8.GetBytes($pinsNew))
$approvalNew=Swap ([IO.File]::ReadAllText($ApprovalFile)) $OldLevel $NewLevel 'the worker approval'
$approvalNew=Swap $approvalNew $OldPins $NewPins 'the worker approval'
$NewApproval=ShaBytes ($Utf8.GetBytes($approvalNew))
$manifestNew=Swap $manifestText $OldApproval $NewApproval 'the staging manifest'
Write-Output ('Preflight OK. Level {0} to {1}.' -f $OldLevel.Substring(0,12),$NewLevel.Substring(0,12))
if($Check){Write-Output 'Check only: nothing was changed.';return}

New-Item -ItemType Directory -Force -Path $Backup | Out-Null
$saved=@(@($Catalog,'levels.json'),@($LevelFile,'C01_L017.json'),@($PinsFile,'pins.json'),@($ApprovalFile,'approval.json'),@($Manifest,'staging-manifest.json'))
foreach($item in $saved){Copy-Item -LiteralPath $item[0] -Destination (Join-Path $Backup $item[1]) -Force}
Write-Output ('Backup: '+$Backup)
Stop-Service 'HOTRStaging'
$restored=$false
try{
    Copy-Item -LiteralPath $NewCatalogFile -Destination $Catalog -Force
    Copy-Item -LiteralPath $NewLevelFile -Destination $LevelFile -Force
    [IO.File]::WriteAllBytes($PinsFile,$Utf8.GetBytes($pinsNew))
    [IO.File]::WriteAllBytes($ApprovalFile,$Utf8.GetBytes($approvalNew))
    [IO.File]::WriteAllBytes($Manifest,$Utf8.GetBytes($manifestNew))
    Start-Service 'HOTRStaging'
    if(-not (WaitUp 'http://127.0.0.1:8751/readyz' 180)){throw 'The API did not become ready.'}
    if(-not (WaitUp 'https://api.novamind-it.ru/readyz' 60)){throw 'The public API did not become ready.'}
}catch{
    Write-Output ('Restoring the previous version: '+$_.Exception.Message)
    try{Stop-Service 'HOTRStaging'}catch{}
    foreach($item in $saved){Copy-Item -LiteralPath (Join-Path $Backup $item[1]) -Destination $item[0] -Force}
    Start-Service 'HOTRStaging'
    if(WaitUp 'http://127.0.0.1:8751/readyz' 180){Write-Output 'Previous version restored and healthy.'}else{Write-Output 'RESTORE DID NOT BECOME READY. Check the HOTRStaging service.'}
    $restored=$true
}
if($restored){exit 1}
Write-Output 'Level 17 cutover complete and healthy.'
