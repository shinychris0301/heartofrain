param([int]$TimeoutMinutes=6)
$ErrorActionPreference='Stop'
$output=Join-Path $PSScriptRoot 'Evidence/GameplayLoadingR1'
[string[]]$paths=@('Evidence/Native/Play_Smoke.json','Evidence/Native/PlaySmoke_Process.json','Evidence/Native/PlaySmoke.log')
$before=@{}
foreach($name in $paths){$path=Join-Path $PSScriptRoot $name;if(Test-Path -LiteralPath $path){$before[$path]=[IO.File]::ReadAllBytes($path)}}
try{
 & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode PlaySmoke -TimeoutMinutes $TimeoutMinutes
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot $paths[0]) -Destination (Join-Path $output 'Connected_Flow.json')
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot $paths[1]) -Destination (Join-Path $output 'Connected_Process.json')
 Copy-Item -LiteralPath (Join-Path $PSScriptRoot $paths[2]) -Destination (Join-Path $output 'Connected.log')
}finally{foreach($path in $before.Keys){[IO.File]::WriteAllBytes($path,$before[$path])}}
