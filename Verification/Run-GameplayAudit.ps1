param([string[]]$Modes=@('ModelPerfChecks','GameplayAuditChecks','GameplayPerfChecks','MixedSwapChecks','TimingChecks','IndividualFallChecks','SwapChecks','M70R2Checks','Checks','PlaySmoke'))
$ErrorActionPreference='Stop'
$auditRoot=Join-Path $PSScriptRoot 'Evidence\GameplayAudit'
$auditReports=@{
 ModelPerfChecks='GameplayAudit\After\Model_Commands.json';GameplayAuditChecks='GameplayAudit\Audit_Checks.json';GameplayPerfChecks='GameplayAudit\After\Sampler_Atlas.json';MixedSwapChecks='GameplayAudit\Mixed_Swap_Checks.json';TimingChecks='Timing\Native_Checks.json';IndividualFallChecks='IndividualFall\Native_Checks.json';SwapChecks='SwapCreation\Native_Checks.json';M70R2Checks='M70R2\Native_Checks.json';Checks='Native\Native_Checks.json';PlaySmoke='Native\Play_Smoke.json'
}
$auditResults=@()
foreach($auditMode in $Modes) {
 $auditStarted=[DateTime]::UtcNow
 & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $auditMode
 $auditPath=Join-Path (Join-Path $PSScriptRoot 'Evidence') $auditReports[$auditMode]
 $auditReport=Get-Content -LiteralPath $auditPath -Raw | ConvertFrom-Json
 if($auditReport.status -notlike 'PASS*' -or $auditReport.failures.Count -gt 0) { throw "Failing audit report: $auditMode" }
 $auditResults+=@{mode=$auditMode;startedUtc=$auditStarted.ToString('o');report=$auditReport}
 $auditCheckpoint=Join-Path $auditRoot 'Native_Checkpoints'
 New-Item -ItemType Directory -Force -Path $auditCheckpoint | Out-Null
 Copy-Item -LiteralPath $auditPath -Destination (Join-Path $auditCheckpoint ($auditMode+'.json'))
}
$auditCollected=@()
foreach($auditMode in $auditReports.Keys) {
 $auditSaved=Join-Path (Join-Path $auditRoot 'Native_Checkpoints') ($auditMode+'.json')
 if(-not (Test-Path -LiteralPath $auditSaved)){throw "Missing native checkpoint: $auditMode"}
 $auditCheckpointReport=Get-Content -LiteralPath $auditSaved -Raw | ConvertFrom-Json
 if($auditCheckpointReport.status -notlike 'PASS*'){throw "Failing native checkpoint: $auditMode"}
 $auditCollected+=@{mode=$auditMode;report=$auditCheckpointReport}
}
@{status='PASS_NATIVE_GAMEPLAY_AUDIT_CHECKPOINTS';utc=[DateTime]::UtcNow.ToString('o');scope='Native Windows Unity custom checks; Android execution is separate. See each checkpoint UTC.';reports=$auditCollected} | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 (Join-Path $auditRoot 'Native_Runtime_Checks.json')
