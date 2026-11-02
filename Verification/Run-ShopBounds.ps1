param([int]$TimeoutMinutes=8,[ValidatePattern("^[A-Za-z0-9]+$")][string]$EvidenceFolder="ShopBounds")
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$out=Join-Path $PSScriptRoot ('Evidence/'+$EvidenceFolder)
$env:HOTR_NO_MOVES_OUTPUT=$out
New-Item -ItemType Directory -Force -Path $out | Out-Null
$unity='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe'
$entries=@(@('HeartOfTheRain.NoMovesEditor.NoMovesPrefabValidator.Validate','Prefab'),@('HeartOfTheRain.Verification.NoMovesPlayReview.Run','NativePlay'))
foreach($entry in $entries){
 $start=[DateTime]::UtcNow
 $args=@('-batchmode','-projectPath',('"'+(Join-Path $root 'Unity')+'"'),'-executeMethod',$entry[0],'-logFile',('"'+(Join-Path $out ($entry[1]+'.log'))+'"'))
 if($entry[1] -ne 'NativePlay'){$args+='-quit'}
 $p=Start-Process -FilePath $unity -ArgumentList $args -PassThru -WindowStyle Hidden
 while(-not $p.HasExited){if([DateTime]::UtcNow -gt $start.AddMinutes($TimeoutMinutes)){Stop-Process -Id $p.Id;throw 'No Moves native review timeout'};Start-Sleep -Seconds 1;$p.Refresh()}
 $p.WaitForExit()
 @{startedUtc=$start.ToString('o');finishedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$p.ExitCode} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out ($entry[1]+'_Process.json')) -Encoding UTF8
 if($p.ExitCode -ne 0){throw ('Native No Moves review failed: '+$entry[1])}
}
