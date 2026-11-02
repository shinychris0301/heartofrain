param([string[]]$Modes=@('BackendChecks','ProfileEventChecks','ProfileEventPlay','ProfileChecks','RainCupChecks','RainCupPlay','DailyGiftPlay','WellworksChecks','WellworksPlay','Checks'))
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$backend=Join-Path $repo 'Backend'
$python=Join-Path $backend '.venv/Scripts/python.exe'
$out=Join-Path $PSScriptRoot 'Evidence/Backend/Native_Checkpoints'
New-Item -ItemType Directory -Force -Path $out | Out-Null
& $python (Join-Path $backend 'tools/run_tests.py')
if($LASTEXITCODE -ne 0){throw 'Backend service tests failed.'}
$id=[Guid]::NewGuid().ToString('N')
$cache=Join-Path $repo ('.verification-cache/Backend/HTTP-'+$id)
New-Item -ItemType Directory -Force -Path $cache | Out-Null
$connection=Join-Path $cache 'connection.json'
$previousConfig=$env:HOTR_BACKEND_VERIFICATION_CONFIG
$reports=@{'BackendChecks'='Backend/Native_HTTP_Checks.json';'ProfileEventChecks'='ProfileEvents/Native_Checks.json';'ProfileEventPlay'='ProfileEvents/Native_Play_Checks.json';'RainCupChecks'='RainCup/Native_Checks.json';'RainCupPlay'='RainCup/Native_Play_Checks.json';'WellworksChecks'='Wellworks/Native_Checks.json';'WellworksPlay'='Wellworks/Native_Play_Checks.json';'ProfileChecks'='DailyGift/Native_Profile_Checks.json';'DailyGiftPlay'='DailyGift/Native_Play_Checks.json';'Checks'='Native/Native_Checks.json'}
function Start-Fixture([bool]$Resume){
    $arguments=@('"'+(Join-Path $backend 'tools/serve_fixture.py')+'"','--directory','"'+$cache+'"','--run-id',$id)
    if($Resume){$arguments+='--resume'}
    $child=Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $backend -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cache ('server-'+$Resume+'.out')) -RedirectStandardError (Join-Path $cache ('server-'+$Resume+'.err'))
    $deadline=[DateTime]::UtcNow.AddSeconds(45)
    while([DateTime]::UtcNow -lt $deadline){
        if($child.HasExited){throw 'Isolated backend process exited during startup; inspect ignored fixture logs.'}
        if(Test-Path -LiteralPath $connection){
            try{$private=Get-Content -LiteralPath $connection -Raw -Encoding utf8 | ConvertFrom-Json
                $response=Invoke-WebRequest -UseBasicParsing -Uri ($private.origin+'readyz') -TimeoutSec 1
                if($response.StatusCode -eq 200){return $child}
            }catch{}
        }
        Start-Sleep -Milliseconds 200
    }
    if(-not $child.HasExited){$child.Kill();$child.WaitForExit()}
    throw 'Isolated backend startup timed out.'
}
$server=$null
try{
    $server=Start-Fixture $false
    $env:HOTR_BACKEND_VERIFICATION_CONFIG=$connection
    foreach($mode in $Modes){
        if(-not $reports.ContainsKey($mode)){throw "Unsupported backend compatibility mode: $mode"}
        $path=Join-Path $PSScriptRoot ('Evidence/'+$reports[$mode]);$historical=$null
        if($mode -ne 'BackendChecks' -and(Test-Path -LiteralPath $path)){$historical=[IO.File]::ReadAllBytes($path)}
        try{ & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $mode
            Copy-Item -LiteralPath $path -Destination (Join-Path $out ($mode+'.json')) -Force
            Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('Evidence/Native/'+$mode+'_Process.json')) -Destination (Join-Path $out ($mode+'_Process.json')) -Force
        }finally{if($null -ne $historical){[IO.File]::WriteAllBytes($path,$historical)}}
    }
    if($Modes -contains 'BackendChecks'){
        if(-not $server.HasExited){$server.Kill();$server.WaitForExit()};$server=Start-Fixture $true
        & $python (Join-Path $backend 'tools/check_restart.py') --connection $connection
        if($LASTEXITCODE -ne 0){throw 'Actual backend process restart checks failed.'}
    }
}finally{
    $env:HOTR_BACKEND_VERIFICATION_CONFIG=$previousConfig
    if($null -ne $server){if(-not $server.HasExited){$server.Kill();$server.WaitForExit()};$server.Dispose()}
}
