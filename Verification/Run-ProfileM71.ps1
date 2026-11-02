param([string[]]$Modes=@('ProfileM71Play','ProfileM71Restart','ProfileChecks','DailyGiftPlay','WellworksPlay','RainCupPlay','PlaySmoke','Checks'))
$ErrorActionPreference='Stop'
$out=Join-Path $PSScriptRoot 'Evidence/ProfileM71/Native_Checkpoints'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$reports=@{
    ProfileM71Play='ProfileM71/Native_Play_Checks.json';ProfileM71Restart='ProfileM71/Native_Restart_Checks.json'
    ProfileChecks='DailyGift/Native_Profile_Checks.json';DailyGiftPlay='DailyGift/Native_Play_Checks.json'
    WellworksPlay='Wellworks/Native_Play_Checks.json';RainCupPlay='RainCup/Native_Play_Checks.json'
    PlaySmoke='Native/Play_Smoke.json';Checks='Native/Native_Checks.json'
}
foreach($mode in $Modes){
    if(-not $reports.ContainsKey($mode)){throw "Unsupported M71 compatibility mode: $mode"}
    $report=Join-Path $PSScriptRoot ('Evidence/'+$reports[$mode])
    $process=Join-Path $PSScriptRoot ('Evidence/Native/'+$mode+'_Process.json')
    $oldReport=$null;$oldProcess=$null
    $oldFrames=@{}
    if($mode -eq 'PlaySmoke'){
        Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'Evidence/Native') -Filter '*.png' | ForEach-Object { $oldFrames[$_.FullName]=[IO.File]::ReadAllBytes($_.FullName) }
    }
    if($mode -notin @('ProfileM71Play','ProfileM71Restart')){
        if(Test-Path -LiteralPath $report){$oldReport=[IO.File]::ReadAllBytes($report)}
        if(Test-Path -LiteralPath $process){$oldProcess=[IO.File]::ReadAllBytes($process)}
    }
    try{
        & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $mode -TimeoutMinutes 6
        Copy-Item -LiteralPath $report -Destination (Join-Path $out ($mode+'.json')) -Force
        Copy-Item -LiteralPath $process -Destination (Join-Path $out ($mode+'_Process.json')) -Force
        if($mode -eq 'PlaySmoke'){
            $frameOut=Join-Path $out 'PlaySmokeFrames';New-Item -ItemType Directory -Force -Path $frameOut | Out-Null
            Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'Evidence/Native') -Filter 'Connected_*.png' | Copy-Item -Destination $frameOut -Force
        }
    }finally{
        if($null -ne $oldReport){[IO.File]::WriteAllBytes($report,$oldReport)}
        if($null -ne $oldProcess){[IO.File]::WriteAllBytes($process,$oldProcess)}
        foreach($path in $oldFrames.Keys){[IO.File]::WriteAllBytes($path,$oldFrames[$path])}
    }
}
