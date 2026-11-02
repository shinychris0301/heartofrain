param([string[]]$Modes=@('WellworksChecks','WellworksPlay','ProfileChecks','DailyGiftPlay','Checks'))
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$out=Join-Path $PSScriptRoot 'Evidence/Wellworks/Native_Checkpoints'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$reports=@{'WellworksChecks'='Wellworks/Native_Checks.json';'WellworksPlay'='Wellworks/Native_Play_Checks.json';'ProfileChecks'='DailyGift/Native_Profile_Checks.json';'DailyGiftPlay'='DailyGift/Native_Play_Checks.json';'Checks'='Native/Native_Checks.json'}
foreach($mode in $Modes){
    $path=Join-Path $PSScriptRoot ('Evidence/'+$reports[$mode])
    $historical=$null
    if($mode -notin @('WellworksChecks','WellworksPlay') -and (Test-Path -LiteralPath $path)){$historical=[IO.File]::ReadAllBytes($path)}
    try { & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $mode
        Copy-Item -LiteralPath $path -Destination (Join-Path $out ($mode+'.json')) -Force
    } finally { if($null -ne $historical){[IO.File]::WriteAllBytes($path,$historical)} }
}
