param(
    [ValidateRange(1,120)][int]$TimeoutMinutes=12,
    [string[]]$Only=@(),
    [string]$EditorPath='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$project=Join-Path $root 'Unity'
$evidence=Join-Path $PSScriptRoot 'Evidence'
$output=Join-Path $evidence 'Gameplay76'
$native=Join-Path $output 'Native'
$cache=Join-Path $root ('.verification-cache/Gameplay76/ReportBackups/'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $native,$cache | Out-Null
if(-not (Test-Path -LiteralPath $EditorPath)){throw 'Pinned Unity 2022.3.62f3 is missing.'}
$version=(Get-Item -LiteralPath $EditorPath).VersionInfo.ProductVersion
if($version -notlike '2022.3.62f3*'){throw ('Unexpected editor: '+$version)}
$lock=Join-Path $project 'Temp/UnityLockfile'
if(Test-Path -LiteralPath $lock){
    try{$probe=[IO.File]::Open($lock,'Open','ReadWrite','None');$probe.Dispose()}
    catch{throw 'Close the Editor for this project before batch verification.'}
}
function WorkspacePath([string]$path){
    $absolute=[IO.Path]::GetFullPath($path)
    if(-not $absolute.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
        throw ('Path leaves the workspace: '+$absolute)
    }
    return $absolute
}
function FreezeInputs([string]$path){
    $files=[ordered]@{}
    foreach($folder in @('Assets','Packages','ProjectSettings')){
        foreach($file in Get-ChildItem -LiteralPath (Join-Path $project $folder) -Recurse -File | Sort-Object FullName){
            $relative=$file.FullName.Substring($root.Length+1).Replace('\','/')
            $files[$relative]=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    @{utc=[DateTime]::UtcNow.ToString('o');files=$files} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $path -Encoding UTF8
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
$entries=@(
    @{name='EffectBatchChecks';report='EffectBatch/Native/Report.json';folder='EffectBatch/Native';status='PASS_NATIVE_EFFECT_BATCH'},
    @{name='SmoothnessCommand';method='SmoothnessCommandVerification.Run';ownReport='Native/SmoothnessCommand.json';status='PASS_NATIVE_SMOOTHNESS_COMMAND76'},
    @{name='PlaybackConstruction';method='PlaybackConstructionVerification.Run';ownReport='Native/PlaybackConstruction.json';status='PASS_NATIVE_PLAYBACK_CONSTRUCTION75'},
    @{name='FrameLookup';method='FrameLookupVerification.Run';ownReport='Native/FrameLookup.json';status='PASS_NATIVE_FRAME_LOOKUP75'},
    @{name='ModelCommands';method='ModelCommandPerformanceVerification.RunBaseline';ownReport='Native/ModelCommands.json';status='PASS_NATIVE_MODEL_COMMANDS75'},
    @{name='MixedSwapChecks';report='GameplayAudit/Mixed_Swap_Checks.json';folder='GameplayAudit';status='PASS_NATIVE_MIXED_POWER_SWAP'},
    @{name='ResourceScan';method='ResourceScanVerification.Run';ownReport='ResourceScan.json';status='PASS_NATIVE_RESOURCE_SCAN'},
    @{name='PlaybackOnset';method='PlaybackOnsetVerification.Run';play=$true;ownReport='PlaybackOnset.json';status='PASS_NATIVE_PLAYBACK_ONSET'},
    @{name='LegalSwapExistence';method='LegalSwapExistenceVerification.Run';ownReport='Native/LegalSwapExistence.json';status='PASS_NATIVE_LEGAL_SWAP_EXISTENCE74'},
    @{name='LocalContinuation';method='LocalContinuationVerification.Run';ownReport='Native/LocalContinuation.json';status='PASS_NATIVE_LOCAL_CONTINUATION75'},
    @{name='LocalCascade';method='LocalCascadeVerification.Run';play=$true;ownReport='LocalCascade.json';status='PASS_NATIVE_LOCAL_CASCADE73'},
    @{name='CascadeTiming';method='CascadeTimingVerification.Run';report='CascadeResponsiveness/After.json';folder='CascadeResponsiveness';status='PASS_NATIVE_CASCADE_TIMING'},
    @{name='ProfileChecks';report='DailyGift/Native_Profile_Checks.json';folder='DailyGift';status='PASS_NATIVE_PROFILE_TRANSACTIONS'},
    @{name='Checks';report='Native/Native_Checks.json';status='PASS_NATIVE_EDITOR_CHECKS'},
    @{name='TimingChecks';report='Timing/Native_Checks.json';folder='Timing';status='PASS_NATIVE_TIMING_CHECKS'},
    @{name='IndividualFallChecks';report='IndividualFall/Native_Checks.json';folder='IndividualFall';status='PASS_NATIVE_INDIVIDUAL_FALL'},
    @{name='FallChecks';report='ObstacleFall/Native_Checks.json';folder='ObstacleFall';status='PASS_NATIVE_OBSTACLE_FALL'},
    @{name='SwapChecks';report='SwapCreation/Native_Checks.json';folder='SwapCreation';status='PASS_NATIVE_SWAP_CREATION'},
    @{name='M70R2Checks';report='M70R2/Native_Checks.json';folder='M70R2';status='PASS_NATIVE_M70R2_CREATION'},
    @{name='M70Checks';report='M70/Native_Checks.json';folder='M70';status='PASS_NATIVE_M70_CHECKS'},
    @{name='GameplayAuditChecks';report='GameplayAudit/Audit_Checks.json';folder='GameplayAudit';status='PASS_NATIVE_GAMEPLAY_AUDIT_WITH_DIAGNOSTICS'},
    @{name='GameplayPerfChecks';report='GameplayAudit/After/Sampler_Atlas.json';folder='GameplayAudit';status='PASS_NATIVE_GAMEPLAY_PERFORMANCE'},
    @{name='ModelPerfChecks';report='GameplayAudit/After/Model_Commands.json';folder='GameplayAudit';status='PASS_NATIVE_MODEL_COMMANDS'},
    @{name='WarmupChecks';report='PowerWarmup/Native_Checks.json';folder='PowerWarmup';status='PASS_NATIVE_PRESENTATION_WARMUP'},
    @{name='PlaySmoke';report='Native/Play_Smoke.json';status='PASS_NATIVE_PLAY_SMOKE'},
    @{name='HomeLivesUI';method='HomeLivesR1Review.Run';play=$true;report='HomeLivesR1/Native_Review.json';folder='HomeLivesR1';status='PASS_NATIVE_HOME_LIVES_R1'}
)
foreach($name in $Only){if($name -notin $entries.name){throw ('Unknown suite: '+$name)}}
$environmentBefore=@{}
foreach($name in @('HOTR_GAMEPLAY72_OUTPUT','HOTR_LOCAL_CASCADE73_OUTPUT','HOTR_GAMEPLAY74_OUTPUT','HOTR_GAMEPLAY75_OUTPUT','HOTR_GAMEPLAY76_OUTPUT')){
    $environmentBefore[$name]=[Environment]::GetEnvironmentVariable($name,'Process')
    [Environment]::SetEnvironmentVariable($name,$output,'Process')
}
$runs=@()
try{
    foreach($entry in $entries){
        if($Only.Count -gt 0 -and $entry.name -notin $Only){continue}
        $suite=$entry.name
        $suiteCache=Join-Path $cache $suite
        New-Item -ItemType Directory -Force -Path $suiteCache | Out-Null
        $sourceDir=Join-Path $native 'SuiteSources'
        New-Item -ItemType Directory -Force -Path $sourceDir | Out-Null
        $sourcePath=Join-Path $sourceDir ($suite+'.json')
        $sourceHash=FreezeInputs $sourcePath
        $started=[DateTime]::UtcNow
        $folders=@()
        if(-not $entry.method){$folders+=Join-Path $evidence 'Native'}
        if($entry.folder){$folders+=Join-Path $evidence $entry.folder}
        $folders=@($folders | Select-Object -Unique)
        $snapshot=@{}
        foreach($folder in $folders){
            $folder=WorkspacePath $folder
            if(-not (Test-Path -LiteralPath $folder)){continue}
            foreach($file in Get-ChildItem -LiteralPath $folder -File -Recurse){
                if($snapshot.ContainsKey($file.FullName)){continue}
                $backup=Join-Path $suiteCache ($file.FullName.Substring($root.Length+1))
                New-Item -ItemType Directory -Force -Path (Split-Path $backup -Parent) | Out-Null
                Copy-Item -LiteralPath $file.FullName -Destination $backup
                $snapshot[$file.FullName]=$backup
            }
        }
        $timedOut=$false;$exitCode=1;$caught=$null
        try{
            if($entry.method){
                $log=Join-Path $native ($suite+'.log')
                $arguments=@('-batchmode','-projectPath',('"'+$project+'"'),'-executeMethod',('HeartOfTheRain.Verification.'+$entry.method),'-logFile',('"'+$log+'"'))
                if(-not $entry.play){$arguments+='-quit'}
                $process=Start-Process -FilePath $EditorPath -ArgumentList $arguments -WindowStyle Hidden -WorkingDirectory $project -PassThru
                while(-not $process.HasExited){
                    if([DateTime]::UtcNow -gt $started.AddMinutes($TimeoutMinutes)){$timedOut=$true;Stop-Process -Id $process.Id;break}
                    Start-Sleep -Seconds 1;$process.Refresh()
                }
                $process.WaitForExit();$exitCode=$process.ExitCode
                if($timedOut -or $exitCode -ne 0){throw ('Native suite failed: '+$suite)}
            }else{
                & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $suite -EditorPath $EditorPath -TimeoutMinutes $TimeoutMinutes
                $processResult=Get-Content -LiteralPath (Join-Path $evidence ('Native/'+$suite+'_Process.json')) -Raw | ConvertFrom-Json
                $exitCode=$processResult.exitCode;$timedOut=$processResult.timedOut
            }
        }catch{$caught=$_}
        finally{
            if($entry.ownReport){$reportPath=Join-Path $output $entry.ownReport}else{$reportPath=Join-Path $evidence $entry.report}
            if((Test-Path -LiteralPath $reportPath) -and [IO.Path]::GetFullPath($reportPath) -ne [IO.Path]::GetFullPath((Join-Path $native ($suite+'.json')))){Copy-Item -LiteralPath $reportPath -Destination (Join-Path $native ($suite+'.json')) -Force}
            foreach($folder in $folders){
                if(-not (Test-Path -LiteralPath $folder)){continue}
                foreach($file in Get-ChildItem -LiteralPath $folder -File -Recurse){
                    if($file.LastWriteTimeUtc -ge $started){
                        $relative=$file.FullName.Substring($evidence.Length+1)
                        $destination=Join-Path $native ($suite+'/Artifacts/'+$relative)
                        New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
                        Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
                    }
                    # Restore old branches exactly. Only newly created report files
                    # within checked report folders are removed, never directories.
                    if(-not $snapshot.ContainsKey($file.FullName)){
                        $checked=WorkspacePath $file.FullName
                        Remove-Item -LiteralPath $checked -Force
                    }
                }
            }
            foreach($path in $snapshot.Keys){Copy-Item -LiteralPath $snapshot[$path] -Destination $path -Force}
            if(-not $entry.method){
                $genericLog=Join-Path $native ($suite+'/Artifacts/Native/'+$suite+'.log')
                if(Test-Path -LiteralPath $genericLog){Copy-Item -LiteralPath $genericLog -Destination (Join-Path $native ($suite+'.log')) -Force}
            }
            $run=[ordered]@{mode=$suite;method=$entry.method;editor=$EditorPath;version=$version;startedUtc=$started.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$exitCode;timedOut=$timedOut;sourceManifest=('Native/SuiteSources/'+$suite+'.json');sourceSHA256=$sourceHash;scope='Fresh pinned Unity process and exact input manifest; Android execution and visible review are separate.'}
            $run | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $native ($suite+'_Process.json')) -Encoding UTF8
            $runs+=$run
        }
        if($caught){throw $caught}
        $result=Get-Content -LiteralPath (Join-Path $native ($suite+'.json')) -Raw | ConvertFrom-Json
        if($result.status -ne $entry.status -or $result.error -or $result.errors.Count -gt 0 -or $result.failures.Count -gt 0 -or [DateTime]::Parse($result.utc).ToUniversalTime() -lt $started){throw ('Failing or stale report: '+$suite)}
        Write-Output ($suite+': '+$result.status)
    }
    @{status='PASS_SELECTED_NATIVE_GAMEPLAY76_SUITES';utc=[DateTime]::UtcNow.ToString('o');runs=$runs;scope='Native suite runner only. No build, Android execution, visual approval or project-completion claim.'} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $output 'Native_Runner.json') -Encoding UTF8
}finally{
    foreach($name in $environmentBefore.Keys){[Environment]::SetEnvironmentVariable($name,$environmentBefore[$name],'Process')}
}
