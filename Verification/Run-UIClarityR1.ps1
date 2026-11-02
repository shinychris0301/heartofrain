param([ValidateSet('Before','Apply','Checks','After')][string]$Mode='After',[int]$TimeoutMinutes=6)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$output=Join-Path $PSScriptRoot 'Evidence/UIClarityR1'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$unity='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
$method=if($Mode -in @('Before','After')){'UIClarityR1Review.'+$Mode}else{'UIClarityPreparation.'+$Mode}
$log=Join-Path $output ($Mode+'.log')
$arguments=@('-batchmode','-projectPath',('"'+(Join-Path $root 'Unity')+'"'),'-executeMethod',('HeartOfTheRain.Verification.'+$method),'-logFile',('"'+$log+'"'))
if($Mode -in @('Apply','Checks')){$arguments+='-quit'}
$began=[DateTime]::UtcNow
$p=Start-Process -FilePath $unity -ArgumentList $arguments -PassThru -WindowStyle Hidden
Write-Output ('Started '+$Mode+' PID '+$p.Id)
$timedOut=$false
while(-not $p.HasExited){if([DateTime]::UtcNow -gt $began.AddMinutes($TimeoutMinutes)){$timedOut=$true;Stop-Process -Id $p.Id;break};Start-Sleep -Seconds 1;$p.Refresh()}
$p.WaitForExit()
@{mode=$Mode;startedUtc=$began.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$p.ExitCode;timedOut=$timedOut;editor=$unity;log=$log} | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $output ($Mode+'_Process.json'))
if($timedOut -or $p.ExitCode -ne 0){throw ($Mode+' failed: '+$log)}
$reportPath=if($Mode -in @('Before','After')){Join-Path $output ($Mode+'/Report.json')}else{Join-Path $output ($Mode+'.json')}
$report=Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
if(-not $report.status.StartsWith('PASS_') -or $report.error){throw ($Mode+' report failed')}
if([DateTime]::Parse($report.utc).ToUniversalTime() -lt $began){throw 'Stale clarity report'}
Write-Output ('Passed '+$Mode)
