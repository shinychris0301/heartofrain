param(
    [ValidateSet('LoadingBarConfigure','LoadingBarReview','ProfileClarityBefore','ProfileClarityApply','ProfileClarityAfter','LaunchConfigure','LaunchReview','ProfileDesignKit','HomeHeaderBefore','HomeHeaderAvatar','HomeLevelButton','ProfileM71Play','ProfileM71Restart','ChapterBackground','BackendGiftLayout','BackendGiftPlay','BackendGiftRestart','BackendChecks','ProfileEventChecks','ProfileEventPlay','RainCupChecks','RainCupPlay','WellworksChecks','WellworksPlay','DailyGiftPlay','ProfileChecks','WarmupChecks','GameplayReplays','ModelPerfBaseline','ModelPerfChecks','MixedSwapChecks','GameplayAuditChecks','GameplayPerfBaseline','GameplayPerfChecks','M70R2Checks','IndividualFallChecks','FallBaseline','FallChecks','SwapChecks','M70Checks','Import','PrepareBindings','Checks','PortraitConfigure','PortraitChecks','GravityBaseline','GravityChecks','GravityReplays','TimingChecks','TimingPlaySmoke','TimingRender','FluidityChecks','PlaySmoke','AndroidBuild','AndroidReleaseBuild','EffectBatchChecks')]
    [string]$Mode = 'Checks',
    [string]$EditorPath = 'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe',
    [ValidateRange(1,120)][int]$TimeoutMinutes = 30
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$projectPath = Join-Path $repoPath 'Unity'
$outputPath = Join-Path $PSScriptRoot 'Evidence\Native'
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
if (-not (Test-Path -LiteralPath $EditorPath)) {
    throw 'Unity 2022.3.62f3 is missing. Install the pinned editor; do not substitute Unity 6.'
}
$actualVersion = (Get-Item -LiteralPath $EditorPath).VersionInfo.ProductVersion
if ($actualVersion -notlike '2022.3.62f3*') { throw "Unexpected editor version: $actualVersion" }
$lockPath = Join-Path $projectPath 'Temp\UnityLockfile'
if (Test-Path -LiteralPath $lockPath) {
    # A failed compile may leave an unlocked stale file behind.
    try {
        $probe = [System.IO.File]::Open($lockPath, 'Open', 'ReadWrite', 'None')
        $probe.Dispose()
    } catch {
        throw 'Close the Editor for this project before running batch verification.'
    }
}
$logPath = Join-Path $outputPath ($Mode + '.log')
$reportPath = Join-Path $outputPath ($Mode + '_Process.json')
$arguments = @('-batchmode', '-projectPath', ('"' + $projectPath + '"'), '-logFile', ('"' + $logPath + '"'))
if ($Mode -notin @('LoadingBarReview','ProfileClarityBefore','ProfileClarityAfter','LaunchReview','ProfileDesignKit','HomeHeaderBefore','HomeHeaderAvatar','HomeLevelButton','ProfileM71Play','ProfileM71Restart','ChapterBackground','BackendGiftPlay','BackendGiftRestart','BackendChecks','ProfileEventPlay','RainCupPlay','WellworksPlay','DailyGiftPlay','PlaySmoke','TimingPlaySmoke','WarmupChecks')) { $arguments += '-quit' }
switch ($Mode) {
    'LoadingBarConfigure' { $arguments += @('-executeMethod','HeartOfTheRain.App.Launch.Editor.LaunchSetup.ConfigureLoadingBar') }
    'LoadingBarReview' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.LaunchReview.LoadingBar') }
    'ProfileClarityBefore' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileClarityReview.Before') }
    'ProfileClarityApply' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileClarityReview.Apply') }
    'ProfileClarityAfter' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileClarityReview.After') }
    'LaunchConfigure' { $arguments += @('-executeMethod','HeartOfTheRain.App.Launch.Editor.LaunchSetup.Configure') }
    'LaunchReview' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.LaunchReview.Run') }
    'ProfileDesignKit' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileDesignKitReview.Run') }
    'HomeHeaderBefore' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.HomeHeaderAvatarReview.Before') }
    'HomeHeaderAvatar' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.HomeHeaderAvatarReview.After') }
    'HomeLevelButton' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.HomeLevelButtonReview.Run') }
    'ProfileM71Play' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileM71Verification.Play') }
    'ProfileM71Restart' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileM71Verification.Restart') }
    'ChapterBackground' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ChapterBackgroundReview.After') }
    'BackendGiftLayout' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.BackendGiftUIVerification.Checks') }
    'BackendGiftPlay' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.BackendGiftUIVerification.Play') }
    'BackendGiftRestart' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.BackendGiftUIVerification.Restart') }
    'BackendChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.BackendHttpVerification.Run') }
    'ProfileEventChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileEventVerification.Run') }
    'ProfileEventPlay' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileEventPlayVerification.Run') }
    'RainCupChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.RainCupVerification.Run') }
    'RainCupPlay' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.RainCupPlayVerification.Run') }
    'WellworksChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.WellworksVerification.Run') }
    'WellworksPlay' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.WellworksPlayVerification.Run') }
    'DailyGiftPlay' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.DailyGiftPlayVerification.Run') }
    'ProfileChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ProfileTransactionVerification.Run') }
    'WarmupChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.PresentationWarmupVerification.Run') }
    'GameplayReplays' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.MixedPowerSwapReplayRefresh.Run') }
    'ModelPerfBaseline' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.GameModelPerformanceVerification.Baseline') }
    'ModelPerfChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.GameModelPerformanceVerification.Run') }
    'MixedSwapChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.MixedPowerSwapVerification.Run') }
    'GameplayAuditChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.GameplayAuditVerification.Run') }
    'GameplayPerfBaseline' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.GameplayPerformanceVerification.Baseline') }
    'GameplayPerfChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.GameplayPerformanceVerification.Run') }
    'M70R2Checks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.M70R2Verification.Run') }
    'IndividualFallChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.IndividualFallVerification.Run') }
    'FallBaseline' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ObstacleFallVerification.Baseline') }
    'FallChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ObstacleFallVerification.Run') }
    'SwapChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.SwapCreationVerification.Run') }
    'M70Checks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.M70Verification.Run') }
    'PortraitConfigure' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.PortraitVerification.ConfigureAndRun') }
    'PortraitChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.PortraitVerification.Run') }
    'GravityBaseline' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ObstacleGravityVerification.Baseline') }
    'GravityChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.ObstacleGravityVerification.Run') }
    'GravityReplays' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.GravityReplayRefresh.Run') }
    'PrepareBindings' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.NativeVerification.PrepareBindings') }
    'Checks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.NativeVerification.Run') }
    'TimingChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.TimingVerification.Run') }
    'TimingPlaySmoke' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.TimingPlaySmoke.Run') }
    'TimingRender' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.TimingRenderProbe.Run') }
    'FluidityChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.FluidityVerification.Run') }
    'PlaySmoke' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.NativePlaySmoke.Run') }
    'AndroidBuild' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.NativeAndroidBuild.Run') }
    'AndroidReleaseBuild' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.NativeAndroidBuild.RunRelease') }
    'EffectBatchChecks' { $arguments += @('-executeMethod','HeartOfTheRain.Verification.EffectBatchVerification.Run') }
}
$started = [DateTime]::UtcNow
$process = Start-Process -FilePath $EditorPath -ArgumentList $arguments -PassThru -WindowStyle Hidden -WorkingDirectory $projectPath
Write-Output "Started $Mode with Unity $actualVersion (PID $($process.Id)); log: $logPath"
$deadline = $started.AddMinutes($TimeoutMinutes)
$timedOut = $false
while (-not $process.HasExited) {
    if ([DateTime]::UtcNow -gt $deadline) {
        $timedOut = $true
        Stop-Process -Id $process.Id
        break
    }
    Start-Sleep -Seconds 2
    $process.Refresh()
}
$process.WaitForExit()
$exitCode = $process.ExitCode
$result = [ordered]@{
    mode=$Mode; editor=$EditorPath; version=$actualVersion; startedUtc=$started.ToString('o')
    finishedUtc=[DateTime]::UtcNow.ToString('o'); exitCode=$exitCode; timedOut=$timedOut
    log=$logPath; scope='Native Windows Unity process; device verification is separate.'
}
$result | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output ($result | ConvertTo-Json -Compress)
if ($timedOut -or $exitCode -ne 0) { throw "$Mode failed; inspect $logPath and $reportPath" }
if ($Mode -eq 'LoadingBarReview') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\LoadingBar\Native\Native_Review.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_LAUNCH_INTEGRATION' -or $checks.error -or $checks.frames.Count -ne 19 -or $checks.routes.Count -ne 4 -or $checks.bars.Count -ne 25 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Loading bar review is failing or stale.' }
}
if ($Mode -in @('ProfileClarityBefore','ProfileClarityAfter')) {
    $clarityPhase = if ($Mode -eq 'ProfileClarityBefore') { 'Before' } else { 'After' }
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot ('Evidence\ProfileClarity\' + $clarityPhase + '\Native_Review.json')) -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_PROFILE_CLARITY' -or $checks.error -or $checks.phase -ne $clarityPhase -or $checks.frames.Count -ne 14 -or $checks.textures.Count -ne 13 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Profile clarity review is failing or stale.' }
}
if ($Mode -eq 'LaunchReview') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\LaunchIntegration\Native_Review.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_LAUNCH_INTEGRATION' -or $checks.error -or $checks.frames.Count -ne 14 -or $checks.routes.Count -ne 4 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Launch integration review is failing or stale.' }
}
if ($Mode -eq 'ProfileDesignKit') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\ProfileDesignKit\Native_Review.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_PROFILE_DESIGN_KIT' -or $checks.error -or $checks.frames.Count -ne 18 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Profile design review is failing or stale.' }
}
if ($Mode -in @('HomeHeaderBefore','HomeHeaderAvatar')) {
    $phase = if ($Mode -eq 'HomeHeaderBefore') { 'Before' } else { 'After' }
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot ('Evidence\HomeHeaderAvatar\' + $phase + '\Native_Review.json')) -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_HOME_HEADER' -or $checks.error -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Home header review is failing or stale.' }
    if ($Mode -eq 'HomeHeaderAvatar' -and ($checks.combinations -ne 54 -or $checks.fallbacks -ne 3 -or $checks.frames.Count -ne 12 -or -not $checks.stableWallet -or -not $checks.headerRoutes -or -not $checks.prelevel)) { throw 'Home header coverage is incomplete.' }
}
if ($Mode -in @('ProfileM71Play','ProfileM71Restart')) {
    $name = if ($Mode -eq 'ProfileM71Restart') { 'Native_Restart_Checks.json' } else { 'Native_Play_Checks.json' }
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot ('Evidence\ProfileM71\' + $name)) -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_M71_PROFILE' -or $checks.errors.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'M71 native verification is failing or stale.' }
}
if ($Mode -eq 'ChapterBackground') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\ChapterBackground\After\Report.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_HOME_RENDER' -or $checks.error -or $checks.frames.Count -ne 3 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Chapter background render is failing or stale.' }
}
if ($Mode -eq 'Import' -and -not (Test-Path -LiteralPath (Join-Path $projectPath 'Library\ScriptAssemblies\Assembly-CSharp.dll'))) {
    throw 'Import exited without the compiled game assembly; this is not a compile pass.'
}
if ($Mode -eq 'DailyGiftPlay') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\DailyGift\Native_Play_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_DAILY_GIFT' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Daily Gift Play Mode report is failing or stale.' }
}
if ($Mode -eq 'ProfileChecks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\DailyGift\Native_Profile_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_PROFILE_TRANSACTIONS' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Profile transaction report is failing or stale.' }
}
if ($Mode -eq 'WarmupChecks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\PowerWarmup\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_PRESENTATION_WARMUP' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Presentation warmup report is failing or stale.' }
}
if ($Mode -eq 'M70R2Checks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\M70R2\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_M70R2_CREATION' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'M70R2 creation report is failing or stale.' }
}
if ($Mode -eq 'IndividualFallChecks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\IndividualFall\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_INDIVIDUAL_FALL' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Individual refill report is failing or stale.' }
}
if ($Mode -eq 'FallChecks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\ObstacleFall\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_OBSTACLE_FALL' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Obstacle fall report is failing or stale.' }
}
if ($Mode -eq 'SwapChecks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\SwapCreation\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_SWAP_CREATION' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Swap creation report is failing or stale.' }
}
if ($Mode -eq 'M70Checks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\M70\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_M70_CHECKS' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'M70 report is failing or stale.' }
}
if ($Mode -eq 'Checks') {
    $checks = Get-Content -LiteralPath (Join-Path $outputPath 'Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_EDITOR_CHECKS' -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) {
        throw 'Native check report is failing or stale.'
    }
}
if ($Mode -eq 'TimingChecks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\Timing\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_TIMING_CHECKS' -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Timing check report is failing or stale.' }
}
if ($Mode -eq 'GravityChecks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\ObstacleGravity\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_OBSTACLE_GRAVITY' -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Obstacle gravity report is failing or stale.' }
}
if ($Mode -in @('PortraitConfigure','PortraitChecks')) {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence\Portrait\Native_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_PORTRAIT_CHECKS' -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Portrait check report is failing or stale.' }
}
if ($Mode -eq 'EffectBatchChecks') {
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence/EffectBatch/Native/Report.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_EFFECT_BATCH' -or $checks.error -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Effect batch report is failing or stale.' }
}
if ($Mode -in @('TimingPlaySmoke','TimingRender','FluidityChecks')) {
    $relative = if ($Mode -eq 'TimingPlaySmoke') { 'Evidence\Timing\Play_Smoke.json' } elseif ($Mode -eq 'TimingRender') { 'Evidence\Timing\Render\Report.json' } else { 'Evidence\Fluidity\Native_Checks.json' }
    $expected = if ($Mode -eq 'TimingPlaySmoke') { 'PASS_NATIVE_TIMING_PLAY_SMOKE' } elseif ($Mode -eq 'TimingRender') { 'PASS_NATIVE_PORTAL_RENDER' } else { 'PASS_NATIVE_FLUIDITY_CHECKS' }
    $checks = Get-Content -LiteralPath (Join-Path $PSScriptRoot $relative) -Raw | ConvertFrom-Json
    if ($checks.status -ne $expected -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw "$Mode report is failing or stale." }
}
if ($Mode -in @('PlaySmoke','AndroidBuild','AndroidReleaseBuild')) {
    $name = switch ($Mode) { 'PlaySmoke' { 'Play_Smoke.json' } 'AndroidBuild' { 'Android_Build.json' } 'AndroidReleaseBuild' { 'Android_Release_Build.json' } }
    $expectedStatus = switch ($Mode) { 'PlaySmoke' { 'PASS_NATIVE_PLAY_SMOKE' } 'AndroidBuild' { 'PASS_ANDROID_DEVELOPMENT_BUILD' } 'AndroidReleaseBuild' { 'PASS_ANDROID_RELEASE_COMPILE_BUILD' } }
    $report = Get-Content -LiteralPath (Join-Path $outputPath $name) -Raw | ConvertFrom-Json
    if ($report.status -ne $expectedStatus -or [DateTime]::Parse($report.utc).ToUniversalTime() -lt $started) {
        throw "$Mode report is failing or stale."
    }
    if ($Mode -in @('AndroidBuild','AndroidReleaseBuild')) {
        $artifact = Get-Item -LiteralPath $report.output
        if ($artifact.Length -eq 0 -or $artifact.LastWriteTimeUtc -lt $started) { throw 'Android build artifact is empty or stale.' }
    }
}

if ($Mode -in @('WellworksChecks','WellworksPlay')) {
    $name=if ($Mode -eq 'WellworksChecks') { 'Native_Checks.json' } else { 'Native_Play_Checks.json' }
    $checks=Get-Content -LiteralPath (Join-Path $PSScriptRoot ('Evidence\Wellworks\'+$name)) -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_WELLWORKS' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Wellworks report is failing or stale.' }
}

if ($Mode -in @('RainCupChecks','RainCupPlay')) {
    $name=if ($Mode -eq 'RainCupChecks') { 'Native_Checks.json' } else { 'Native_Play_Checks.json' }
    $checks=Get-Content -LiteralPath (Join-Path $PSScriptRoot ('Evidence/RainCup/'+$name)) -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_RAIN_CUP' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Rain Cup report is failing or stale.' }
}
if ($Mode -in @('ProfileEventChecks','ProfileEventPlay')) {
    $name=if($Mode -eq 'ProfileEventChecks'){'Native_Checks.json'}else{'Native_Play_Checks.json'}
    $checks=Get-Content -LiteralPath (Join-Path $PSScriptRoot ('Evidence/ProfileEvents/'+$name)) -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_PROFILE_EVENTS' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Profile event report is failing or stale.' }
}

if ($Mode -eq 'BackendChecks') {
    $checks=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Evidence/Backend/Native_HTTP_Checks.json') -Raw | ConvertFrom-Json
    if ($checks.status -ne 'PASS_NATIVE_BACKEND_HTTP' -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Backend HTTP report is failing or stale.' }
}

if ($Mode -in @('BackendGiftLayout','BackendGiftPlay','BackendGiftRestart')) {
    $name=if($Mode -eq 'BackendGiftLayout'){'Native_Layout_Checks.json'}elseif($Mode -eq 'BackendGiftPlay'){'Native_Play_Checks.json'}else{'Native_Restart_Checks.json'}
    $checks=Get-Content -LiteralPath (Join-Path $PSScriptRoot ('Evidence/BackendGiftUI/'+$name)) -Raw | ConvertFrom-Json
    if (-not $checks.status.StartsWith('PASS_NATIVE_BACKEND_GIFT_') -or $checks.failures.Count -ne 0 -or [DateTime]::Parse($checks.utc).ToUniversalTime() -lt $started) { throw 'Backend gift UI report is failing or stale.' }
}
