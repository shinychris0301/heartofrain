param([int]$TimeoutMinutes=5)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$unity='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
$output=Join-Path $PSScriptRoot 'Evidence\CrateBurst'
New-Item -ItemType Directory -Force -Path $output | Out-Null
foreach($step in @(
    @{name='After';method='CrateBurstVerification.After';quit=$true},
    @{name='NativePlay';method='CrateBurstPlayVerification.Run';quit=$false},
    @{name='Warmup';method='PresentationWarmupVerification.Run';quit=$false},
    @{name='Checks';method='NativeVerification.Run';quit=$true}
)) {
    $started=[DateTime]::UtcNow
    $log=Join-Path $output ($step.name+'.log')
    $arguments=@('-batchmode','-projectPath',('"'+(Join-Path $root 'Unity')+'"'),'-executeMethod',('HeartOfTheRain.Verification.'+$step.method),'-logFile',('"'+$log+'"'))
    if($step.quit){$arguments+='-quit'}
    $process=Start-Process -FilePath $unity -ArgumentList $arguments -PassThru -WindowStyle Hidden
    Write-Output ('Started '+$step.name+' PID '+$process.Id)
    $timedOut=$false
    while(-not $process.HasExited){
        if([DateTime]::UtcNow -gt $started.AddMinutes($TimeoutMinutes)){$timedOut=$true;Stop-Process -Id $process.Id;break}
        Start-Sleep -Seconds 1
        $process.Refresh()
    }
    $process.WaitForExit()
    $result=[ordered]@{name=$step.name;editor=$unity;startedUtc=$started.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$process.ExitCode;timedOut=$timedOut;log=$log}
    $result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output ($step.name+'_Process.json')) -Encoding UTF8
    if($timedOut -or $process.ExitCode -ne 0){throw ($step.name+' failed; inspect '+$log)}
    switch($step.name){
        'After' {$report=Get-Content -Raw (Join-Path $output 'After\Report.json') | ConvertFrom-Json;if($report.status -ne 'PASS_NATIVE_CRATE_BURST' -or $report.error){throw 'Crate sampler failed'}}
        'NativePlay' {$report=Get-Content -Raw (Join-Path $output 'NativePlay.json') | ConvertFrom-Json;if($report.status -ne 'PASS_CRATE_BURST_PLAYBACK' -or $report.rows.Count -ne 6 -or $report.errors.Count){throw 'Crate playback failed'}}
        'Warmup' {Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Evidence\PowerWarmup\Native_Checks.json') -Destination (Join-Path $output 'Warmup_Checks.json');$report=Get-Content -Raw (Join-Path $output 'Warmup_Checks.json') | ConvertFrom-Json;if($report.status -ne 'PASS_NATIVE_PRESENTATION_WARMUP' -or $report.failures.Count){throw 'Warmup lifecycle failed'}}
        'Checks' {Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Evidence\Native\Native_Checks.json') -Destination (Join-Path $output 'General_Checks.json');$report=Get-Content -Raw (Join-Path $output 'General_Checks.json') | ConvertFrom-Json;if($report.status -ne 'PASS_NATIVE_EDITOR_CHECKS' -or $report.failed){throw 'General checks failed'}}
    }
    if([DateTime]::Parse($report.utc).ToUniversalTime() -lt $started){throw ($step.name+' report is stale')}
    Write-Output ('Passed '+$step.name)
}
