param([string[]]$Modes=@('WarmupChecks','GameplayPerfChecks','M70Checks','M70R2Checks','Checks','PlaySmoke'))
$ErrorActionPreference='Stop'
$reports=@{WarmupChecks='PowerWarmup/Native_Checks.json';GameplayPerfChecks='GameplayAudit/After/Sampler_Atlas.json';M70Checks='M70/Native_Checks.json';M70R2Checks='M70R2/Native_Checks.json';Checks='Native/Native_Checks.json';PlaySmoke='Native/Play_Smoke.json'}
$destination=Join-Path $PSScriptRoot 'Evidence/PowerWarmup/Native_Checkpoints'
New-Item -ItemType Directory -Force -Path $destination | Out-Null
foreach($mode in $Modes){
 $source=Join-Path (Join-Path $PSScriptRoot 'Evidence') $reports[$mode]
 $previous=if(Test-Path -LiteralPath $source){[System.IO.File]::ReadAllBytes($source)}else{$null}
 try {
  & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $mode
  $result=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
  if($result.status -notlike 'PASS*' -or $result.failures.Count -gt 0){throw "Failed native check: $mode"}
  Copy-Item -LiteralPath $source -Destination (Join-Path $destination ($mode+'.json'))
 } finally {if($null -ne $previous -and $mode -ne 'WarmupChecks'){[System.IO.File]::WriteAllBytes($source,$previous)}}
}
