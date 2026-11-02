param([int]$TimeoutMinutes=6)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$out=Join-Path $PSScriptRoot 'Evidence/IndependentReview66'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$unity='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
$began=[DateTime]::UtcNow
$args=@('-batchmode','-projectPath',('"'+(Join-Path $root 'Unity')+'"'),'-executeMethod','HeartOfTheRain.Verification.IndependentPageCorrectionsReview.Run','-logFile',('"'+(Join-Path $out 'Loading_Art_Lifetime.log')+'"'))
$p=Start-Process -FilePath $unity -ArgumentList $args -PassThru -WindowStyle Hidden
while(-not $p.HasExited){if([DateTime]::UtcNow -gt $began.AddMinutes($TimeoutMinutes)){Stop-Process -Id $p.Id;throw 'Native correction review timed out'};Start-Sleep -Seconds 1;$p.Refresh()}
$p.WaitForExit()
@{startedUtc=$began.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$p.ExitCode} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'Native_Process.json') -Encoding UTF8
if($p.ExitCode -ne 0){throw 'Native corrections failed'}
$steps=@(
 @{mode='Checks';report='Evidence/Native/Native_Checks.json'},
 @{mode='ProfileChecks';report='Evidence/DailyGift/Native_Profile_Checks.json'},
 @{mode='PlaySmoke';report='Evidence/Native/Play_Smoke.json'}
)
foreach($step in $steps){
 $paths=@($step.report,('Evidence/Native/'+$step.mode+'_Process.json'),('Evidence/Native/'+$step.mode+'.log'))
 if($step.mode -eq 'PlaySmoke'){$paths+=@('Evidence/Native/Connected_BoardOnly.png','Evidence/Native/Connected_Gameplay.png')}
 $before=@{}
 foreach($n in $paths){$path=Join-Path $PSScriptRoot $n;if(Test-Path -LiteralPath $path){$before[$path]=[IO.File]::ReadAllBytes($path)}}
 try{
  & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $step.mode -TimeoutMinutes $TimeoutMinutes
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot $step.report) -Destination (Join-Path $out ($step.mode+'.json'))
  foreach($n in $paths | Select-Object -Skip 1){Copy-Item -LiteralPath (Join-Path $PSScriptRoot $n) -Destination (Join-Path $out (Split-Path $n -Leaf))}
 }finally{foreach($path in $before.Keys){[IO.File]::WriteAllBytes($path,$before[$path])}}
}
