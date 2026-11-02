param([string[]]$Modes=@('ProfileChecks','DailyGiftPlay','Checks','PlaySmoke','M70Checks','M70R2Checks','WarmupChecks'))
$ErrorActionPreference='Stop'
$reports=@{ProfileChecks='DailyGift/Native_Profile_Checks.json';DailyGiftPlay='DailyGift/Native_Play_Checks.json';Checks='Native/Native_Checks.json';PlaySmoke='Native/Play_Smoke.json';M70Checks='M70/Native_Checks.json';M70R2Checks='M70R2/Native_Checks.json';WarmupChecks='PowerWarmup/Native_Checks.json'}
$destination=Join-Path $PSScriptRoot 'Evidence/DailyGift/Native_Checkpoints'
New-Item -ItemType Directory -Force -Path $destination | Out-Null
foreach($mode in $Modes){
 $source=Join-Path (Join-Path $PSScriptRoot 'Evidence') $reports[$mode]
 $previous=if(Test-Path -LiteralPath $source){[System.IO.File]::ReadAllBytes($source)}else{$null}
 try {
  & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $mode
  $result=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
  if($result.status -notlike 'PASS*' -or $result.failures.Count -gt 0){throw "Failed native check: $mode"}
  Copy-Item -LiteralPath $source -Destination (Join-Path $destination ($mode+'.json'))
 } finally {if($null -ne $previous -and $mode -notin @('ProfileChecks','DailyGiftPlay')){[System.IO.File]::WriteAllBytes($source,$previous)}}
}
