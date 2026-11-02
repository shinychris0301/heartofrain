param([int]$TimeoutMinutes=6)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$output=Join-Path $PSScriptRoot 'Evidence/RainCupR1'
foreach($mode in @('RainCupChecks','RainCupPlay')){
 [string[]]$names=@(if($mode -eq 'RainCupChecks'){'Evidence/RainCup/Native_Checks.json'}else{'Evidence/RainCup/Native_Play_Checks.json'})
 $names+=@(('Evidence/Native/'+$mode+'_Process.json'),('Evidence/Native/'+$mode+'.log'))
 $backups=@{}
 foreach($name in $names){$path=Join-Path $PSScriptRoot $name;if(Test-Path -LiteralPath $path){$backups[$path]=[IO.File]::ReadAllBytes($path)}}
 try{
  & (Join-Path $PSScriptRoot 'Run-UnityVerification.ps1') -Mode $mode -TimeoutMinutes $TimeoutMinutes
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot $names[0]) -Destination (Join-Path $output ($mode+'.json'))
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('Evidence/Native/'+$mode+'_Process.json')) -Destination (Join-Path $output ($mode+'_Process.json'))
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('Evidence/Native/'+$mode+'.log')) -Destination (Join-Path $output ($mode+'.log'))
 }finally{foreach($path in $backups.Keys){[IO.File]::WriteAllBytes($path,$backups[$path])}}
}
