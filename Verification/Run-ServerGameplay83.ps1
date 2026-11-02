param(
    [ValidateRange(1,120)][int]$TimeoutMinutes=30,
    [ValidateSet('SocialExpiry','AccountContracts','AccountHttp','ServerCore','ServerHttp','RewardsHttp','Identity','IdentityHttp','SocialHttp','Guard','Http','Preflight','Checks','ProfileChecks','PlaySmoke','PortraitChecks','AndroidReleaseBuild','AndroidBuild')]
    [string[]]$Only=@(),
    [string]$EditorPath='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$project=Join-Path $root 'Unity'
$evidence=Join-Path $PSScriptRoot 'Evidence'
$output=Join-Path $evidence 'ServerGameplay83'
$native=Join-Path $output 'Native'
$cache=Join-Path $root ('.verification-cache/ServerGameplay83/RunnerBackups/'+[Guid]::NewGuid().ToString('N'))
if(-not (Test-Path -LiteralPath $EditorPath)){throw 'Pinned Unity 2022.3.62f3 is missing.'}
$version=(Get-Item -LiteralPath $EditorPath).VersionInfo.ProductVersion
if($version -notlike '2022.3.62f3*'){throw ('Unexpected editor: '+$version)}
function AssertEditorUnlocked {
    $lock=Join-Path $project 'Temp/UnityLockfile'
    if(Test-Path -LiteralPath $lock){
        try{$probe=[IO.File]::Open($lock,'Open','ReadWrite','None');$probe.Dispose()}
        catch{throw 'Close the Editor for this project before batch verification.'}
    }
}
function WorkspacePath([string]$path){
    $absolute=[IO.Path]::GetFullPath($path)
    if(-not $absolute.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
        throw ('Path leaves the workspace: '+$absolute)
    }
    return $absolute
}
function WriteJson([object]$value,[string]$path){
    New-Item -ItemType Directory -Force -Path (Split-Path $path -Parent) | Out-Null
    $value | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $path -Encoding UTF8
}
function Sha([string]$path){return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
function HasErrors([object]$value){
    if($null -eq $value){return $false}
    if($value -is [ValueType]){return [double]$value -ne 0}
    if($value -is [string]){return -not [string]::IsNullOrEmpty($value)}
    return @($value).Count -gt 0
}
function FreezeInputs([string]$path){
    $files=[ordered]@{}
    foreach($folder in @('Assets','Packages','ProjectSettings')){
        foreach($file in Get-ChildItem -LiteralPath (Join-Path $project $folder) -Recurse -File | Sort-Object FullName){
            $relative=$file.FullName.Substring($root.Length+1).Replace('\','/')
            $files[$relative]=Sha $file.FullName
        }
    }
    WriteJson ([ordered]@{utc=[DateTime]::UtcNow.ToString('o');files=$files}) $path
    return [pscustomobject]@{path=$path;sha256=(Sha $path);count=$files.Count;files=$files}
}
function SourceDelta($before,$after){
    $changed=@();$added=@();$removed=@()
    foreach($name in $before.Keys){
        if(-not $after.Contains($name)){$removed+=$name}
        elseif($before[$name] -ne $after[$name]){$changed+=$name}
    }
    foreach($name in $after.Keys){if(-not $before.Contains($name)){$added+=$name}}
    return [pscustomobject]@{changed_existing=@($changed|Sort-Object);added=@($added|Sort-Object);removed=@($removed|Sort-Object)}
}
function SnapshotFolders([string[]]$folders,[string]$destination){
    $snapshot=@{}
    foreach($folder in $folders){
        $checked=WorkspacePath $folder
        if(-not (Test-Path -LiteralPath $checked)){continue}
        foreach($file in Get-ChildItem -LiteralPath $checked -Recurse -File){
            if($snapshot.ContainsKey($file.FullName)){continue}
            $backup=Join-Path $destination ($file.FullName.Substring($root.Length+1))
            New-Item -ItemType Directory -Force -Path (Split-Path $backup -Parent) | Out-Null
            Copy-Item -LiteralPath $file.FullName -Destination $backup -Force
            $snapshot[$file.FullName]=$backup
        }
    }
    return ,$snapshot
}
function RestoreFolders([string[]]$folders,$snapshot){
    foreach($folder in $folders){
        $checked=WorkspacePath $folder
        if(-not (Test-Path -LiteralPath $checked)){continue}
        foreach($file in Get-ChildItem -LiteralPath $checked -Recurse -File){
            if(-not $snapshot.ContainsKey($file.FullName)){Remove-Item -LiteralPath (WorkspacePath $file.FullName) -Force}
        }
    }
    foreach($path in $snapshot.Keys){
        New-Item -ItemType Directory -Force -Path (Split-Path $path -Parent) | Out-Null
        Copy-Item -LiteralPath $snapshot[$path] -Destination $path -Force
        if((Sha $path) -ne (Sha $snapshot[$path])){throw ('Restoration hash mismatch: '+$path)}
    }
}
function CopyFreshArtifacts([string[]]$folders,[DateTime]$started,[string]$destination){
    foreach($folder in $folders){
        if(-not (Test-Path -LiteralPath $folder)){continue}
        foreach($file in Get-ChildItem -LiteralPath $folder -Recurse -File){
            if($file.LastWriteTimeUtc -lt $started){continue}
            $relative=$file.FullName.Substring($evidence.Length+1)
            $target=Join-Path $destination $relative
            New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
            Copy-Item -LiteralPath $file.FullName -Destination $target -Force
        }
    }
}
$entries=@(
    @{name='SocialExpiry';method='HeartOfTheRain.Verification.SocialExpiry83Verification.Run';report='Native/SocialExpiry83_HTTP.json';statuses=@('PASS_NATIVE_SOCIAL_EXPIRY83_HTTP');play=$true},
    @{name='AccountContracts';method='HeartOfTheRain.Verification.ServerAccount83Verification.Run';report='Native/AccountContracts.json';statuses=@('PASS_NATIVE_SERVER_ACCOUNT83_CONTRACTS');play=$true},
    @{name='AccountHttp';method='HeartOfTheRain.Verification.ServerAccount83HttpVerification.Run';report='Native/AccountHTTP.json';statuses=@('PASS_NATIVE_SERVER_ACCOUNT83_CONNECTED_HTTP');play=$true},
    @{name='ServerHttp';method='HeartOfTheRain.Verification.ServerGameplay83HttpVerification.Run';report='Native/ConnectedHTTP.json';statuses=@('PASS_NATIVE_SERVER_GAMEPLAY83_CONNECTED_HTTP');play=$true},
    @{name='RewardsHttp';method='HeartOfTheRain.App.ServerRewards.Editor.ServerRewards83Verification.Run';report='Rewards/NativeHTTP.json';statuses=@('PASS_NATIVE_SERVER_REWARDS_HTTP83');play=$true},
    @{name='ServerCore';method='HeartOfTheRain.Verification.ServerGameplay83Verification.Run';report='Native/ServerGameplay.json';statuses=@('PASS_NATIVE_SERVER_GAMEPLAY83_CORE')},
    @{name='Identity';method='HeartOfTheRain.Verification.Identity82Verification.Run';report='Native/Identity82.json';statuses=@('PASS_NATIVE_IDENTITY82')},
    @{name='SocialHttp';method='HeartOfTheRain.Verification.Social82Verification.RunHttp';report='Native/Social82_HTTP.json';statuses=@('PASS_NATIVE_SOCIAL82_HTTP');play=$true},
    @{name='IdentityHttp';method='HeartOfTheRain.Verification.Identity82Verification.RunHttp';report='Native/Identity82_HTTP.json';statuses=@('PASS_NATIVE_IDENTITY82_HTTP');play=$true},
    @{name='Guard';method='HeartOfTheRain.Verification.RuStore81Verification.Run';report='Native/RuStore81.json';statuses=@('PASS_NATIVE_RUSTORE81_RELEASE_GUARD')},
    @{name='Http';method='HeartOfTheRain.Verification.RuStore81Verification.RunHttp';report='Native/HTTP.json';statuses=@('PASS_NATIVE_RUSTORE81_HTTP_STAGING_CLIENT');play=$true},
    @{name='Preflight';method='HeartOfTheRain.App.RuStore.Editor.RuStoreReleasePreflight.Run';externalReport='RuStore81/Native/Release_Preflight.json';folder='RuStore81/Native';report='Native/Release_Preflight.json';statuses=@('BLOCKED_RUSTORE_EXTERNAL_CONFIGURATION_AND_INTEGRATION')},
    @{name='Checks';legacyReport='Native/Native_Checks.json';report='Native/Checks.json';statuses=@('PASS_NATIVE_EDITOR_CHECKS')},
    @{name='ProfileChecks';legacyReport='DailyGift/Native_Profile_Checks.json';report='Native/ProfileChecks.json';folder='DailyGift';statuses=@('PASS_NATIVE_PROFILE_TRANSACTIONS')},
    @{name='PlaySmoke';legacyReport='Native/Play_Smoke.json';report='Native/PlaySmoke.json';statuses=@('PASS_NATIVE_PLAY_SMOKE')},
    @{name='PortraitChecks';legacyReport='Portrait/Native_Checks.json';report='Native/PortraitChecks.json';folder='Portrait';statuses=@('PASS_NATIVE_PORTRAIT_CHECKS')},
    @{name='AndroidReleaseBuild';legacyReport='Native/Android_Release_Build.json';report='Android_Release_Build.json';statuses=@('PASS_ANDROID_RELEASE_COMPILE_BUILD');build=$true;source='Release_Source_SHA256.json'},
    @{name='AndroidBuild';legacyReport='Native/Android_Build.json';report='Android_Build.json';statuses=@('PASS_ANDROID_DEVELOPMENT_BUILD');build=$true;source='Build_Source_SHA256.json'}
)
AssertEditorUnlocked
New-Item -ItemType Directory -Force -Path $native,$cache | Out-Null
$environmentBefore=@{}
foreach($name in @('HOTR_RUSTORE81_OUTPUT','HOTR_IDENTITY82_OUTPUT','HOTR_SOCIAL82_OUTPUT','HOTR_SERVER_GAMEPLAY_OUTPUT','HOTR_SERVER_REWARDS_OUTPUT','SDKMANAGER_OPTS')){$environmentBefore[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
$runs=@()
try{
    foreach($entry in $entries){
        if($Only.Count -gt 0 -and $entry.name -notin $Only){continue}
        AssertEditorUnlocked
        $suite=$entry.name
        $suiteCache=Join-Path $cache $suite
        New-Item -ItemType Directory -Force -Path $suiteCache | Out-Null
        $sourcePath=Join-Path $native ('SuiteSources/'+$suite+'.json')
        $before=FreezeInputs $sourcePath
        # The parent-created current-input freeze is authoritative when present.
        $sealed=Join-Path $output 'Source_SHA256.json'
        if(-not $entry.mutates -and (Test-Path -LiteralPath $sealed)){
            $expected=Get-Content -LiteralPath $sealed -Raw -Encoding UTF8 | ConvertFrom-Json
            $expectedFiles=[ordered]@{}
            foreach($p in $expected.files.PSObject.Properties){$expectedFiles[$p.Name]=[string]$p.Value}
            $delta=SourceDelta $expectedFiles $before.files
            if($delta.changed_existing.Count+$delta.added.Count+$delta.removed.Count -ne 0){throw ('Frozen inputs changed before '+$suite)}
        }
        if($entry.build){
            if(Test-Path -LiteralPath $sealed){Copy-Item -LiteralPath $sealed -Destination (Join-Path $output $entry.source) -Force}
            else{Copy-Item -LiteralPath $sourcePath -Destination (Join-Path $output $entry.source) -Force}
        }
        $folders=@()
        if(-not $entry.method){$folders+=Join-Path $evidence 'Native'}
        if($entry.folder){$folders+=Join-Path $evidence $entry.folder}
        $snapshot=SnapshotFolders $folders (Join-Path $suiteCache 'Reports')
        $settingsFolders=@(Join-Path $project 'ProjectSettings')
        $settingsSnapshot=@{}
        if($entry.build){$settingsSnapshot=SnapshotFolders $settingsFolders (Join-Path $suiteCache 'ApprovedPreBuildSettings')}
        $reportPath=Join-Path $output $entry.report
        if(Test-Path -LiteralPath $reportPath){
            Copy-Item -LiteralPath $reportPath -Destination (Join-Path $suiteCache 'Previous_Current_Report.json') -Force
            Remove-Item -LiteralPath (WorkspacePath $reportPath) -Force
        }
        $env:HOTR_RUSTORE81_OUTPUT=$output
        $env:HOTR_IDENTITY82_OUTPUT=$output
        $env:HOTR_SOCIAL82_OUTPUT=$output
        $env:HOTR_SERVER_GAMEPLAY_OUTPUT=$output
        $env:HOTR_SERVER_REWARDS_OUTPUT=Join-Path $output 'Rewards'
        if($entry.build){$env:SDKMANAGER_OPTS='-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9 -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=9 -Dsun.net.client.defaultConnectTimeout=3000 -Dsun.net.client.defaultReadTimeout=3000'}
        $started=[DateTime]::UtcNow
        $timedOut=$false;$exitCode=1;$caught=$null;$pidValue=$null;$delegated=$null;$after=$null;$sourceDelta=$null
        $log=Join-Path $native ($suite+'.log')
        try{
            if($entry.method){
                $arguments=@('-batchmode','-projectPath',('"'+$project+'"'),'-executeMethod',$entry.method,'-logFile',('"'+$log+'"'))
                if(-not $entry.play){$arguments+='-quit'}
                $process=Start-Process -FilePath $EditorPath -ArgumentList $arguments -WindowStyle Hidden -WorkingDirectory $project -PassThru
                $pidValue=$process.Id
                while(-not $process.HasExited){
                    if([DateTime]::UtcNow -gt $started.AddMinutes($TimeoutMinutes)){$timedOut=$true;Stop-Process -Id $process.Id;break}
                    Start-Sleep -Seconds 1;$process.Refresh()
                }
                $process.WaitForExit();$exitCode=$process.ExitCode
            }else{
                & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $suite -EditorPath $EditorPath -TimeoutMinutes $TimeoutMinutes
            }
        }catch{$caught=$_}
        finally{
            try{
              if($entry.externalReport){
                # The older preflight method owns a fixed output path. Copy its
                # fresh result into this run, then restore that historical folder
                # in the shared finally below, exactly like delegated suites.
                $externalReport=Join-Path $evidence $entry.externalReport
                if(Test-Path -LiteralPath $externalReport){
                    $externalResult=Get-Content -LiteralPath $externalReport -Raw -Encoding UTF8 | ConvertFrom-Json
                    if([DateTime]::Parse($externalResult.utc).ToUniversalTime() -ge $started){Copy-Item -LiteralPath $externalReport -Destination $reportPath -Force}
                }
              }
              if(-not $entry.method){
                $legacyProcess=Join-Path $evidence ('Native/'+$suite+'_Process.json')
                if(Test-Path -LiteralPath $legacyProcess){
                    $candidate=Get-Content -LiteralPath $legacyProcess -Raw -Encoding UTF8 | ConvertFrom-Json
                    if([DateTime]::Parse($candidate.startedUtc).ToUniversalTime() -ge $started){$delegated=$candidate;$exitCode=$candidate.exitCode;$timedOut=$candidate.timedOut}
                }
                $legacyReport=Join-Path $evidence $entry.legacyReport
                if(Test-Path -LiteralPath $legacyReport){Copy-Item -LiteralPath $legacyReport -Destination $reportPath -Force}
                CopyFreshArtifacts $folders $started (Join-Path $native ($suite+'/Artifacts'))
                foreach($name in @(($suite+'.log'),($suite+'_Process.json'))){
                    $legacy=Join-Path $evidence ('Native/'+$name)
                    if(Test-Path -LiteralPath $legacy){
                        $destination=if($entry.build){Join-Path $output $name}else{Join-Path $native ($suite+'/Delegated/'+$name)}
                        New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
                        Copy-Item -LiteralPath $legacy -Destination $destination -Force
                    }
                }
                $legacyLog=Join-Path $evidence ('Native/'+$suite+'.log')
                if(Test-Path -LiteralPath $legacyLog){Copy-Item -LiteralPath $legacyLog -Destination $log -Force}
              }
              if($entry.build){
                # Restore ONLY temporary build settings to this suite's approved pre-build snapshot.
                # Approved Russian branding and retained license-required splash settings are preserved.
                $temporary=FreezeInputs (Join-Path $native ('SuiteSources/'+$suite+'_BeforeSettingsRestore.json'))
                WriteJson (SourceDelta $before.files $temporary.files) (Join-Path $native ($suite+'_Temporary_Input_Delta.json'))
                $import=Join-Path $project 'UIClarityReports/Build_Import_Audit.txt'
                if(Test-Path -LiteralPath $import){
                    $importName=if($suite -eq 'AndroidReleaseBuild'){'Release_Build_Import_Audit.txt'}else{'Build_Import_Audit.txt'}
                    Copy-Item -LiteralPath $import -Destination (Join-Path $output $importName) -Force
                }
              }
            }finally{
                # Even copying a malformed/failed report must not leave historical evidence
                # or the approved pre-build settings replaced by this run's temporary output.
                try{if($entry.build){RestoreFolders $settingsFolders $settingsSnapshot}}
                finally{RestoreFolders $folders $snapshot}
            }
            $after=FreezeInputs (Join-Path $native ('SuiteSources/'+$suite+'_After.json'))
            $sourceDelta=SourceDelta $before.files $after.files
            WriteJson $sourceDelta (Join-Path $native ($suite+'_Input_Delta.json'))
            $run=[ordered]@{mode=$suite;method=$entry.method;editor=$EditorPath;version=$version;pid=$pidValue;startedUtc=$started.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$exitCode;timedOut=$timedOut;sourceManifest=('Native/SuiteSources/'+$suite+'.json');sourceSHA256=$before.sha256;inputCount=$before.count;afterSourceManifest=('Native/SuiteSources/'+$suite+'_After.json');afterSourceSHA256=$after.sha256;report=$entry.report;intentionalConfigurationMutation=[bool]$entry.mutates;temporaryBuildSettingsRestored=[bool]$entry.build;historicalReportsRestored=$true;delegatedProcess=$delegated;scope='Fresh pinned Unity process and exact input manifests. Configuration may apply approved settings; other suites retain inputs after temporary build settings restore. Device, visual approval and store publishing are separate.'}
            if(Test-Path -LiteralPath $reportPath){$run.reportSHA256=Sha $reportPath}
            if(Test-Path -LiteralPath $log){$run.log=('Native/'+$suite+'.log');$run.logSHA256=Sha $log}
            WriteJson $run (Join-Path $native ($suite+'_Process.json'))
            $runs+=$run
        }
        if($caught){throw $caught}
        if($timedOut -or $exitCode -ne 0){throw ('Native suite failed: '+$suite)}
        if(-not $entry.method -and -not $delegated){throw ('Missing fresh delegated process report: '+$suite)}
        if(-not $entry.mutates -and $sourceDelta.changed_existing.Count+$sourceDelta.added.Count+$sourceDelta.removed.Count -ne 0){throw ('Inputs changed during '+$suite)}
        if(-not (Test-Path -LiteralPath $reportPath)){throw ('Missing report: '+$suite)}
        $result=Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $stamp=[DateTime]::Parse($result.utc).ToUniversalTime()
        if($result.status -notin $entry.statuses -or $result.error -or (HasErrors $result.errors) -or (HasErrors $result.failures) -or $stamp -lt $started -or $stamp -gt [DateTime]::UtcNow.AddSeconds(2)){throw ('Failing or stale report: '+$suite)}
        if($result.unity -and $result.unity -ne '2022.3.62f3'){throw ('Wrong report editor: '+$suite)}
        if($suite -eq 'Launch' -and ($result.frames.Count -ne 19 -or $result.bars.Count -ne 25 -or $result.routes.Count -ne 4)){throw 'Launch capture/bar/route coverage is incomplete.'}
        if($suite -eq 'Locale' -and $result.captures.Count -ne 6){throw 'Russian locale capture coverage is incomplete.'}
        Write-Output ($suite+': '+$result.status)
    }
    WriteJson ([ordered]@{status='PASS_SELECTED_CONNECTED84_NATIVE_SUITES_WITH_RELEASE_BLOCKED';utc=[DateTime]::UtcNow.ToString('o');runs=$runs;scope='Selected pinned native, release-guard and internal-build checks only. Each report retains its own scope. Deployed production operation, actual store sandbox payments, bank return and release signing remain separate. No live payment or store publication.'}) (Join-Path $output 'Native_Runner.json')
}finally{
    foreach($name in $environmentBefore.Keys){[Environment]::SetEnvironmentVariable($name,$environmentBefore[$name],'Process')}
}
