param([ValidateRange(1,30)][int]$TimeoutMinutes=15)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$project=Join-Path $root '.verification-cache/Launch82/AndroidIdentityProject'
$output=Join-Path $root 'Verification/Evidence/Launch82/Android/Assembly'
$editor='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
if(-not $project.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Fixture outside workspace'}
New-Item -ItemType Directory -Force -Path $output | Out-Null
$report=Join-Path $project 'Build/Build.json'
if(Test-Path -LiteralPath $report){Remove-Item -LiteralPath $report}
$log=Join-Path $output 'Unity.log'
$before=(Get-FileHash -LiteralPath (Join-Path $project 'Preparation.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$oldSdk=[Environment]::GetEnvironmentVariable('SDKMANAGER_OPTS','Process')
$started=[DateTime]::UtcNow
$code=$null;$timedOut=$false;$pidValue=$null
try{
    $env:SDKMANAGER_OPTS='-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9 -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=9 -Dsun.net.client.defaultConnectTimeout=3000 -Dsun.net.client.defaultReadTimeout=3000'
    $arguments=@('-batchmode','-quit','-projectPath',('"'+$project+'"'),'-executeMethod','Identity82FixtureBuild.Build','-logFile',('"'+$log+'"'))
    $process=Start-Process -FilePath $editor -ArgumentList $arguments -WorkingDirectory $project -WindowStyle Hidden -PassThru
    $pidValue=$process.Id
    while(-not $process.HasExited){
        if([DateTime]::UtcNow -gt $started.AddMinutes($TimeoutMinutes)){$timedOut=$true;Stop-Process -Id $process.Id;break}
        Start-Sleep -Seconds 1
        $process.Refresh()
    }
    $process.WaitForExit();$code=$process.ExitCode
}finally{
    [Environment]::SetEnvironmentVariable('SDKMANAGER_OPTS',$oldSdk,'Process')
    $result=[ordered]@{startedUtc=$started.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');pid=$pidValue;exitCode=$code;timedOut=$timedOut;editor=$editor;preparationSHA256=$before;scope='Actual isolated fixture assembly only; no ordinary Android build or real payment'}
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'Process.json') -Encoding UTF8
    Copy-Item -LiteralPath (Join-Path $project 'Preparation.json') -Destination (Join-Path $output 'Preparation.json') -Force
    if(Test-Path -LiteralPath $report){Copy-Item -LiteralPath $report -Destination (Join-Path $output 'Build.json') -Force}
}
if($timedOut -or $null -eq $code -or $code -ne 0){throw 'Isolated Android fixture assembly process failed'}
if(-not (Test-Path -LiteralPath $report) -or (Get-Item -LiteralPath $report).LastWriteTimeUtc -lt $started){throw 'Missing fresh assembly report'}
$value=Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
if($value.status -ne 'PASS_ISOLATED_IDENTITY82_ANDROID_ASSEMBLY' -or $value.errors -ne 0){throw 'Isolated Android fixture build failed'}
Write-Output $value.status
