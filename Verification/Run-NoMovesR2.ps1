param([int]$TimeoutMinutes=8,[ValidatePattern("^[A-Za-z0-9]+$")][string]$EvidenceFolder="RepeatMoves")
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$out=Join-Path $PSScriptRoot ('Evidence/'+$EvidenceFolder)
$env:HOTR_NO_MOVES_OUTPUT=$out
New-Item -ItemType Directory -Force -Path $out | Out-Null
$unity='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
$entries=@(@('NoMovesVerification.Run','Transactions'),@('NoMovesPlayReview.Run','NativePlay'))
if($EvidenceFolder -in @('RepeatMoves','NoMovesR3')){$entries=@(@('NoMovesVerification.Run','Transactions'),@('RepeatMovesVerification.Run','RepeatTransactions'),@('NoMovesPlayReview.Run','NativePlay'))}
foreach($entry in $entries){
 $start=[DateTime]::UtcNow
 $args=@('-batchmode','-projectPath',('"'+(Join-Path $root 'Unity')+'"'),'-executeMethod',('HeartOfTheRain.Verification.'+$entry[0]),'-logFile',('"'+(Join-Path $out ($entry[1]+'.log'))+'"'))
 if($entry[1] -ne 'NativePlay'){$args+='-quit'}
 $p=Start-Process -FilePath $unity -ArgumentList $args -PassThru -WindowStyle Hidden
 while(-not $p.HasExited){if([DateTime]::UtcNow -gt $start.AddMinutes($TimeoutMinutes)){Stop-Process -Id $p.Id;throw 'No Moves native review timeout'};Start-Sleep -Seconds 1;$p.Refresh()}
 $p.WaitForExit()
 @{startedUtc=$start.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$p.ExitCode} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out ($entry[1]+'_Process.json')) -Encoding UTF8
 if($p.ExitCode -ne 0){throw ('Native No Moves review failed: '+$entry[1])}
}
$steps=@(
 @{mode='Checks';report='Native/Native_Checks.json'},
 @{mode='ProfileChecks';report='DailyGift/Native_Profile_Checks.json'},
 @{mode='PlaySmoke';report='Native/Play_Smoke.json';extra=@('Native/Connected_BoardOnly.png','Native/Connected_Gameplay.png')},
 @{mode='TimingChecks';report='Timing/Native_Checks.json'},
 @{mode='IndividualFallChecks';report='IndividualFall/Native_Checks.json'}
)
foreach($step in $steps){
 $paths=@($step.report,('Native/'+$step.mode+'.log'),('Native/'+$step.mode+'_Process.json'))+@($step.extra | Where-Object {$_})
 $before=@{}
 foreach($name in $paths){$path=Join-Path $PSScriptRoot ('Evidence/'+$name);if(Test-Path -LiteralPath $path){$before[$path]=[IO.File]::ReadAllBytes($path)}}
 try{
  & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $step.mode -TimeoutMinutes $TimeoutMinutes
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('Evidence/'+$step.report)) -Destination (Join-Path $out ($step.mode+'.json'))
  foreach($name in $paths | Select-Object -Skip 1){$path=Join-Path $PSScriptRoot ('Evidence/'+$name);if(Test-Path -LiteralPath $path){Copy-Item -LiteralPath $path -Destination (Join-Path $out (Split-Path $name -Leaf))}}
 }finally{foreach($path in $before.Keys){[IO.File]::WriteAllBytes($path,$before[$path])}}
}
