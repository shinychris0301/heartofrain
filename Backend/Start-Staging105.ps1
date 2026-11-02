param(
    [Parameter(Mandatory=$true)][string]$Manifest,
    [ValidateSet('preflight','initialize','start','export-app-config','configure-rewarded-ads')][string]$Action='preflight',
    [string]$Out,
    [switch]$RestorePending
)
$ErrorActionPreference='Stop'
$python=Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if(-not (Test-Path -LiteralPath $python -PathType Leaf)){throw 'Create the existing Python3.12 environment with requirements.lock first.'}
$manifestPath=[IO.Path]::GetFullPath($Manifest)
# Isolated Python ignores ambient PYTHONPATH/user startup configuration. Only
# this explicit repository Backend path is added before importing our entry.
$bootstrap='import sys;sys.path.insert(0,sys.argv.pop(1));from hotr_backend.staging105 import main;raise SystemExit(main())'
$arguments=@('-I','-B','-c',$bootstrap,$PSScriptRoot,$Action,'--manifest',$manifestPath)
if($RestorePending){if($Action -ne 'initialize'){throw 'RestorePending is only valid for initialization.'};$arguments+='--restore-pending'}
if($Out){if($Action -ne 'export-app-config'){throw 'Out is only valid for app configuration export.'};$arguments+=@('--out',[IO.Path]::GetFullPath($Out))}
Push-Location $PSScriptRoot
try{
    & $python @arguments
    if($LASTEXITCODE -ne 0){throw 'Staging operation blocked; inspect the fixed public error code.'}
}finally{Pop-Location}
