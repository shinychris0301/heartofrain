param(
    [ValidateSet('Prepare','Native','Build')][string]$Mode='Prepare',
    [ValidateRange(1,40)][int]$TimeoutMinutes=20
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$main=Join-Path $root 'Unity'
$fixture=Join-Path $root '.verification-cache/PinnedReplay83/Project'
$output=Join-Path $root 'Verification/Evidence/ServerReplay83/Native'
$editor='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
New-Item -ItemType Directory -Force -Path $output | Out-Null
function Freeze([string]$name){
    $files=[ordered]@{}
    foreach($folder in @('Assets','Packages','ProjectSettings')){
        foreach($file in Get-ChildItem -LiteralPath (Join-Path $main $folder) -Recurse -File | Sort-Object FullName){
            $files[$file.FullName.Substring($root.Length+1).Replace('\','/')]=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    [ordered]@{utc=[DateTime]::UtcNow.ToString('o');files=$files} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output $name) -Encoding UTF8
    return $files
}
$project=$main
$method='HeartOfTheRain.App.ServerVerification.Editor.PinnedReplayBuild.Prepare'
$report=Join-Path (Split-Path $fixture -Parent) 'Preparation.json'
$expected='PASS_PREPARED_PINNED_REPLAY_PROJECT'
if($Mode -eq 'Native'){$method='HeartOfTheRain.App.ServerVerification.Editor.PinnedReplayVerification.Run';$report=Join-Path $output 'ReplayNative.json';$expected='PASS_PINNED_NATIVE_REPLAY_CORPUS'}
if($Mode -eq 'Build'){$project=$fixture;$method='HeartOfTheRain.App.ServerVerification.Editor.PinnedReplayBuild.Build';$report=Join-Path (Split-Path $fixture -Parent) 'Build.json';$expected='PASS_PINNED_WINDOWS_REPLAY_BUILD'}
$before=Freeze ($Mode+'_Before.json')
$started=[DateTime]::UtcNow;$pidValue=$null;$code=$null;$timedOut=$false
$oldProject=[Environment]::GetEnvironmentVariable('HOTR_REPLAY_PROJECT','Process')
$oldOutput=[Environment]::GetEnvironmentVariable('HOTR_REPLAY_OUTPUT','Process')
try{
    $env:HOTR_REPLAY_PROJECT=$fixture;$env:HOTR_REPLAY_OUTPUT=$output
    $log=Join-Path $output ($Mode+'.log')
    $arguments=@('-batchmode','-quit','-projectPath',('"'+$project+'"'),'-executeMethod',$method,'-logFile',('"'+$log+'"'))
    $process=Start-Process -FilePath $editor -ArgumentList $arguments -WorkingDirectory $project -WindowStyle Hidden -PassThru
    $pidValue=$process.Id
    while(-not $process.HasExited){
        if([DateTime]::UtcNow -gt $started.AddMinutes($TimeoutMinutes)){$timedOut=$true;Stop-Process -Id $process.Id;break}
        Start-Sleep -Seconds 1;$process.Refresh()
    }
    $process.WaitForExit();$code=$process.ExitCode
}finally{
    [Environment]::SetEnvironmentVariable('HOTR_REPLAY_PROJECT',$oldProject,'Process')
    [Environment]::SetEnvironmentVariable('HOTR_REPLAY_OUTPUT',$oldOutput,'Process')
    $after=Freeze ($Mode+'_After.json')
    $changed=@($before.Keys | Where-Object {-not $after.Contains($_) -or $before[$_] -ne $after[$_]})
    $added=@($after.Keys | Where-Object {-not $before.Contains($_)})
    $record=[ordered]@{mode=$Mode;method=$method;startedUtc=$started.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');pid=$pidValue;exitCode=$code;timedOut=$timedOut;changedExisting=$changed;added=$added;mainInputCount=$before.Count;scope='Actual pinned native/isolated model worker preparation, compilation or Editor corpus; actual standalone execution is separate'}
    $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output ($Mode+'_Process.json')) -Encoding UTF8
    if($Mode -ne 'Native' -and (Test-Path -LiteralPath $report)){Copy-Item -LiteralPath $report -Destination (Join-Path $output ($Mode+'.json')) -Force}
}
if($timedOut -or $null -eq $code -or $code -ne 0){throw 'Pinned replay process failed'}
if($Mode -ne 'Build' -and $changed.Count+$added.Count -ne 0){throw 'Main source changed during isolated replay work'}
if(-not (Test-Path -LiteralPath $report) -or (Get-Item -LiteralPath $report).LastWriteTimeUtc -lt $started){throw 'Missing fresh replay report'}
$value=Get-Content -LiteralPath $report -Raw -Encoding UTF8 | ConvertFrom-Json
if($value.status -ne $expected -or $value.error -or $value.code){throw 'Replay report failed'}
Write-Output $value.status
