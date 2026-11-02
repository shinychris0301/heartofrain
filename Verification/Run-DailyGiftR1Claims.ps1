param([string[]]$Modes=@('BackendGiftLayout','BackendGiftPlay','BackendGiftRestart','ProfileChecks','DailyGiftPlay'))
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$output=Join-Path $PSScriptRoot 'Evidence/DailyGiftR1/Claims'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$backups=@{}
$legacy=Join-Path $PSScriptRoot 'Evidence/BackendGiftUI'
foreach($file in Get-ChildItem -LiteralPath $legacy -Recurse -File){$backups[$file.FullName]=[IO.File]::ReadAllBytes($file.FullName)}
foreach($mode in $Modes){foreach($suffix in @('.log','_Process.json')){$path=Join-Path $PSScriptRoot ('Evidence/Native/'+$mode+$suffix);if(Test-Path -LiteralPath $path){$backups[$path]=[IO.File]::ReadAllBytes($path)}}}
try{
    & (Join-Path $PSScriptRoot 'Run-BackendGiftUI.ps1') -Modes $Modes
    if($LASTEXITCODE -ne 0){throw 'Claim compatibility runner failed'}
    foreach($mode in $Modes){
        Copy-Item -LiteralPath (Join-Path $legacy ('Native_Checkpoints/'+$mode+'.json')) -Destination (Join-Path $output ($mode+'.json'))
        Copy-Item -LiteralPath (Join-Path $legacy ('Native_Checkpoints/'+$mode+'_Process.json')) -Destination (Join-Path $output ($mode+'_Process.json'))
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('Evidence/Native/'+$mode+'.log')) -Destination (Join-Path $output ($mode+'.log'))
    }
    Copy-Item -LiteralPath (Join-Path $legacy 'Service_Tests.json') -Destination (Join-Path $output 'Service_Tests.json')
    foreach($file in Get-ChildItem -LiteralPath $legacy -Filter '*.png'){Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $output $file.Name)}
}finally{
    foreach($mode in $Modes){foreach($suffix in @('.log','_Process.json')){$path=Join-Path $PSScriptRoot ('Evidence/Native/'+$mode+$suffix);if(Test-Path -LiteralPath $path){Copy-Item -LiteralPath $path -Destination (Join-Path $output ($mode+$suffix))}}}
    foreach($file in Get-ChildItem -LiteralPath (Join-Path $legacy 'Native_Checkpoints') -File){if($Modes -contains ($file.BaseName -replace '_Process$','')){Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $output $file.Name)}}
    foreach($file in Get-ChildItem -LiteralPath $legacy -Filter '*.png'){Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $output $file.Name)}
    if(Test-Path -LiteralPath (Join-Path $legacy 'Service_Tests.json')){Copy-Item -LiteralPath (Join-Path $legacy 'Service_Tests.json') -Destination (Join-Path $output 'Service_Tests.json')}
    # Preserve earlier reviewed evidence, including when a new verification fails.
    foreach($path in $backups.Keys){[IO.File]::WriteAllBytes($path,$backups[$path])}
}
