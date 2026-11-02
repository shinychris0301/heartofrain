param([int]$TimeoutMinutes=12,[string[]]$Only=@())
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$out=Join-Path $PSScriptRoot 'Evidence/Gameplay72/Native'
$env:HOTR_GAMEPLAY72_OUTPUT=Split-Path $out -Parent
New-Item -ItemType Directory -Force -Path $out | Out-Null
$entries=@(
 @{name='MixedSwapChecks';report='GameplayAudit/Mixed_Swap_Checks.json'},
 @{name='ResourceScan';method='ResourceScanVerification.Run';report='Gameplay72/ResourceScan.json'},
 @{name='PlaybackOnset';method='PlaybackOnsetVerification.Run';play=$true;report='Gameplay72/PlaybackOnset.json'},
 @{name='ProfileChecks';report='DailyGift/Native_Profile_Checks.json'},
 @{name='Checks';report='Native/Native_Checks.json'},
 @{name='TimingChecks';report='Timing/Native_Checks.json'},
 @{name='IndividualFallChecks';report='IndividualFall/Native_Checks.json'},
 @{name='FallChecks';report='ObstacleFall/Native_Checks.json'},
 @{name='SwapChecks';report='SwapCreation/Native_Checks.json'},
 @{name='M70R2Checks';report='M70R2/Native_Checks.json'},
 @{name='M70Checks';report='M70/Native_Checks.json';folder='M70'},
 @{name='GameplayAuditChecks';report='GameplayAudit/Audit_Checks.json'},
 @{name='GameplayPerfChecks';report='GameplayAudit/After/Sampler_Atlas.json'},
 @{name='ModelPerfChecks';report='GameplayAudit/After/Model_Commands.json'},
 @{name='EffectBatchChecks';report='EffectBatch/Native/Report.json';folder='EffectBatch/Native'},
 @{name='WarmupChecks';report='PowerWarmup/Native_Checks.json'},
 @{name='PlaySmoke';report='Native/Play_Smoke.json';extra=@('Native/Connected_BoardOnly.png','Native/Connected_Gameplay.png')},
 @{name='HomeLivesUI';method='HomeLivesR1Review.Run';play=$true;report='HomeLivesR1/Native_Review.json';folder='HomeLivesR1'}
)
foreach($entry in $entries){
 if($Only.Count -gt 0 -and $entry.name -notin $Only){continue}
 $started=[DateTime]::UtcNow
 $paths=@($entry.report,('Native/'+$entry.name+'.log'),('Native/'+$entry.name+'_Process.json'))+@($entry.extra | Where-Object {$_})
 if($entry.folder){$paths+=@(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot ('Evidence/'+$entry.folder)) -File | ForEach-Object {$entry.folder+'/'+$_.Name})}
 $before=@{}
 foreach($name in ($paths | Select-Object -Unique)){$path=Join-Path $PSScriptRoot ('Evidence/'+$name);if(Test-Path -LiteralPath $path){$before[$path]=[IO.File]::ReadAllBytes($path)}}
 try{
  if($entry.method){
   $unity='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
   $log=Join-Path $out ($entry.name+'.log')
   $argv=@('-batchmode','-projectPath',('"'+(Join-Path $root 'Unity')+'"'),'-executeMethod',('HeartOfTheRain.Verification.'+$entry.method),'-logFile',('"'+$log+'"'))
   if(-not $entry.play){$argv+='-quit'}
   $proc=Start-Process -FilePath $unity -ArgumentList $argv -WindowStyle Hidden -PassThru
   while(-not $proc.HasExited){if([DateTime]::UtcNow -gt $started.AddMinutes($TimeoutMinutes)){Stop-Process -Id $proc.Id;throw ('Timeout: '+$entry.name)};Start-Sleep -Seconds 1;$proc.Refresh()}
   $proc.WaitForExit()
   @{startedUtc=$started.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$proc.ExitCode} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out ($entry.name+'_Process.json')) -Encoding UTF8
   if($proc.ExitCode -ne 0){throw ('Native suite failed: '+$entry.name)}
  }else{& (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $entry.name -TimeoutMinutes $TimeoutMinutes}
 }finally{
  $report=Join-Path $PSScriptRoot ('Evidence/'+$entry.report)
  if(Test-Path -LiteralPath $report){Copy-Item -LiteralPath $report -Destination (Join-Path $out ($entry.name+'.json'))}
  foreach($name in @($paths | Select-Object -Skip 1)){$path=Join-Path $PSScriptRoot ('Evidence/'+$name);if(Test-Path -LiteralPath $path){Copy-Item -LiteralPath $path -Destination (Join-Path $out (Split-Path $name -Leaf))}}
  if($entry.folder){$dest=Join-Path $out $entry.name;New-Item -ItemType Directory -Force -Path $dest | Out-Null;foreach($file in Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot ('Evidence/'+$entry.folder)) -File){if($file.LastWriteTimeUtc -ge $started){Copy-Item -LiteralPath $file.FullName -Destination $dest}}}
  foreach($path in $before.Keys){[IO.File]::WriteAllBytes($path,$before[$path])}
 }
 $result=Get-Content -LiteralPath (Join-Path $out ($entry.name+'.json')) -Raw | ConvertFrom-Json
 if($result.status -notlike 'PASS*' -or $result.failures.Count -gt 0 -or $result.errors.Count -gt 0 -or $result.error){throw ('Failing report: '+$entry.name)}
 Write-Output ($entry.name+': '+$result.status)
}
