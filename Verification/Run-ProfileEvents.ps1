param([string[]]$Modes=@('ProfileEventChecks','ProfileEventPlay','ProfileChecks','RainCupChecks','RainCupPlay','DailyGiftPlay','WellworksChecks','WellworksPlay','Checks'))
$ErrorActionPreference='Stop'
$out=Join-Path $PSScriptRoot 'Evidence/ProfileEvents/Native_Checkpoints'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$reports=@{'ProfileEventChecks'='ProfileEvents/Native_Checks.json';'ProfileEventPlay'='ProfileEvents/Native_Play_Checks.json';'RainCupChecks'='RainCup/Native_Checks.json';'RainCupPlay'='RainCup/Native_Play_Checks.json';'WellworksChecks'='Wellworks/Native_Checks.json';'WellworksPlay'='Wellworks/Native_Play_Checks.json';'ProfileChecks'='DailyGift/Native_Profile_Checks.json';'DailyGiftPlay'='DailyGift/Native_Play_Checks.json';'Checks'='Native/Native_Checks.json'}
foreach($mode in $Modes){
    if(-not $reports.ContainsKey($mode)){throw "Unsupported event compatibility mode: $mode"}
    $path=Join-Path $PSScriptRoot ('Evidence/'+$reports[$mode]);$historical=$null
    if($mode -notin @('ProfileEventChecks','ProfileEventPlay') -and (Test-Path -LiteralPath $path)){$historical=[IO.File]::ReadAllBytes($path)}
    try { & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $mode
        Copy-Item -LiteralPath $path -Destination (Join-Path $out ($mode+'.json')) -Force
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('Evidence/Native/'+$mode+'_Process.json')) -Destination (Join-Path $out ($mode+'_Process.json')) -Force
    } finally { if($null -ne $historical){[IO.File]::WriteAllBytes($path,$historical)} }
}
