param([switch]$SkipImport,[switch]$SkipReview,[int]$TimeoutMinutes=6)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$output=Join-Path $PSScriptRoot 'Evidence/WellworksR1'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$unity='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
$steps=@()
if(-not $SkipImport){$steps+=@{name='Import';method='WellworksR1Review.Prepare';quit=$true;report='Import.json';status='PASS_NATIVE_WELLWORKS_BINDINGS'}}
if(-not $SkipReview){$steps+=@{name='Native';method='WellworksR1Review.Run';quit=$false;report='Native_Review.json';status='PASS_NATIVE_WELLWORKS_R1'}}
foreach($step in $steps){
    $started=[DateTime]::UtcNow
    $log=Join-Path $output ($step.name+'.log')
    $arguments=@('-batchmode','-projectPath',('"'+(Join-Path $root 'Unity')+'"'),'-executeMethod',('HeartOfTheRain.Verification.'+$step.method),'-logFile',('"'+$log+'"'))
    if($step.quit){$arguments+='-quit'}
    $p=Start-Process -FilePath $unity -ArgumentList $arguments -PassThru -WindowStyle Hidden
    Write-Output ('Started '+$step.name+' PID '+$p.Id)
    $timedOut=$false
    while(-not $p.HasExited){if([DateTime]::UtcNow -gt $started.AddMinutes($TimeoutMinutes)){$timedOut=$true;Stop-Process -Id $p.Id;break};Start-Sleep -Seconds 1;$p.Refresh()}
    $p.WaitForExit()
    @{name=$step.name;startedUtc=$started.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$p.ExitCode;timedOut=$timedOut;log=$log;editor=$unity} | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $output ($step.name+'_Process.json'))
    if($timedOut -or $p.ExitCode -ne 0){throw ($step.name+' failed: '+$log)}
    $report=Get-Content -Raw -LiteralPath (Join-Path $output $step.report) | ConvertFrom-Json
    if($report.status -ne $step.status -or $report.error){throw ($step.name+' report failed')}
    if($step.name -eq 'Native' -and [DateTime]::Parse($report.utc).ToUniversalTime() -lt $started){throw 'Native report is stale'}
    Write-Output ('Passed '+$step.name)
}
$backups=@{}
foreach($name in @('Native_Checks.json','Checks_Process.json','Checks.log')){
    $path=Join-Path $PSScriptRoot ('Evidence/Native/'+$name)
    if(Test-Path -LiteralPath $path){$backups[$path]=[IO.File]::ReadAllBytes($path)}
}
try{
    & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode Checks -TimeoutMinutes $TimeoutMinutes
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Evidence/Native/Native_Checks.json') -Destination (Join-Path $output 'General_Checks.json')
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Evidence/Native/Checks_Process.json') -Destination (Join-Path $output 'General_Process.json')
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Evidence/Native/Checks.log') -Destination (Join-Path $output 'General.log')
    $report=Get-Content -Raw -LiteralPath (Join-Path $output 'General_Checks.json') | ConvertFrom-Json
    if($report.failed -ne 0 -or $report.status -ne 'PASS_NATIVE_EDITOR_CHECKS'){throw 'General checks failed'}
}finally{foreach($path in $backups.Keys){[IO.File]::WriteAllBytes($path,$backups[$path])}}


