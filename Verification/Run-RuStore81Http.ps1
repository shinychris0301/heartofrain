param([ValidateRange(1,30)][int]$TimeoutMinutes=10)
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$python=Join-Path $repo 'Backend/.venv/Scripts/python.exe'
$runId=[Guid]::NewGuid().ToString('N')
$cache=Join-Path $repo ('.verification-cache/RuStore81/HTTP-'+$runId)
$connection=Join-Path $cache 'connection.json'
$fixture=Join-Path $PSScriptRoot 'Tools/serve_rustore81_fixture.py'
$probe=Join-Path $PSScriptRoot 'Tools/probe_rustore81_restart.py'
$output=Join-Path $PSScriptRoot 'Evidence/RuStore81/Backend'
$oldConfig=$env:HOTR_RUSTORE81_HTTP_CONFIG
New-Item -ItemType Directory -Force -Path $cache,$output|Out-Null
$started=[DateTime]::UtcNow
$server=$null;$stages=@();$errorCode=$null;$stage='startup';$firstPid=$null
function Hash([string]$path){return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
function StartFixture([bool]$resume){
    $stageStarted=[DateTime]::UtcNow
    $arguments=@(('"'+$fixture+'"'),'--directory',('"'+$cache+'"'),'--run-id',$runId)
    if($resume){$arguments+='--resume'}
    $child=Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cache ('server-'+$resume+'.out')) -RedirectStandardError (Join-Path $cache ('server-'+$resume+'.err'))
    $script:server=$child
    $script:stages+=@([ordered]@{resume=$resume;pid=$child.Id;startedUtc=$stageStarted.ToString('o')})
    $deadline=$stageStarted.AddSeconds(40)
    while([DateTime]::UtcNow -lt $deadline){
        $child.Refresh();if($child.HasExited){throw 'Fixture startup failed'}
        if((Test-Path -LiteralPath $connection) -and (Get-Item -LiteralPath $connection).LastWriteTimeUtc -ge $stageStarted){
            try {
                $private=Get-Content -LiteralPath $connection -Raw -Encoding UTF8|ConvertFrom-Json
                $ready=Invoke-WebRequest -UseBasicParsing -Uri ($private.origin+'readyz') -TimeoutSec 1
                if($ready.StatusCode -eq 200){return $child}
            }catch{}
        }
        Start-Sleep -Milliseconds 150
    }
    throw 'Fixture startup timeout'
}
function StopFixture {
    if($null -eq $script:server){return}
    $script:server.Refresh()
    if(-not $script:server.HasExited){Stop-Process -Id $script:server.Id;$script:server.WaitForExit()}
    $script:stages[-1]['stoppedUtc']=[DateTime]::UtcNow.ToString('o')
    $script:server.Dispose();$script:server=$null
}
try {
    $server=StartFixture $false;$firstPid=$server.Id
    $stage='native_http';$env:HOTR_RUSTORE81_HTTP_CONFIG=$connection
    & (Join-Path $PSScriptRoot 'Run-RuStore81.ps1') -Only Http -TimeoutMinutes $TimeoutMinutes
    $stage='before_restart'
    & $python $probe --connection $connection --phase before
    if($LASTEXITCODE -ne 0){throw 'Before-restart readback failed'}
    StopFixture
    $stage='restart';$server=StartFixture $true
    if($server.Id -eq $firstPid){throw 'Expected distinct restarted process'}
    $stage='after_restart'
    & $python $probe --connection $connection --phase after
    if($LASTEXITCODE -ne 0){throw 'After-restart readback failed'}
    $stage='complete'
}catch{$errorCode='rustore81_http_'+$stage+'_failed';throw}
finally {
    StopFixture
    $env:HOTR_RUSTORE81_HTTP_CONFIG=$oldConfig
    $report=[ordered]@{status=$(if($errorCode){'FAIL_RUSTORE81_NATIVE_HTTP_AND_PROCESS_RESTART'}else{'PASS_RUSTORE81_NATIVE_HTTP_AND_PROCESS_RESTART'});startedUtc=$started.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');runId=$runId;error=$errorCode;stages=$stages;fixtureSource='Verification/Tools/serve_rustore81_fixture.py';fixtureSHA256=(Hash $fixture);probeSource='Verification/Tools/probe_rustore81_restart.py';probeSHA256=(Hash $probe);backendTestReportSHA256=(Hash (Join-Path $output 'Service_Tests.json'));scope='Actual separate loopback FastAPI process, native UnityWebRequest transport and SQLite process restart; synthetic CONFIRMED store provider, no SDK purchase/real RuStore/deployed HTTPS or ordinary-profile integration.'}
    $native=Join-Path $PSScriptRoot 'Evidence/RuStore81/Native/HTTP.json'
    $restart=Join-Path $output 'HTTP_Restart.json'
    if(Test-Path -LiteralPath $native){$report.nativeReportSHA256=Hash $native}
    if(Test-Path -LiteralPath $restart){$report.restartReportSHA256=Hash $restart}
    $report|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $output 'HTTP_Process.json') -Encoding UTF8
}
