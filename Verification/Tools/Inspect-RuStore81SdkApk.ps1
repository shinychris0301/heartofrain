param([string]$RepositoryRoot='E:\Projects\Heart_of_the_Rain')
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath($RepositoryRoot)
$spike=Join-Path $repo '.verification-cache/RuStore81/Spike'
$output=Join-Path $repo 'Verification/Evidence/RuStore81/SDK_Android/Assembly'
$aapt='C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\build-tools\34.0.0\aapt.exe'
New-Item -ItemType Directory -Force -Path $output|Out-Null
function Hash([string]$path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
$report=[ordered]@{status='FAIL_STATIC_UNLAUNCHED_RUSTORE81_SDK_APK_INSPECTION';utc=[DateTime]::UtcNow.ToString('o');error=$null;toolSHA256=(Hash $PSCommandPath);aapt=$aapt;aaptSHA256=$null;apk=$null;apkSHA256=$null;apkBytes=0;packageId='com.heartoftherain.sdkspike';minApi=26;targetApi=34;payVersion='11.1.0';coreVersion='10.5.0';apkLaunched=$false;syntheticConfiguration=$true;checks=@();bindings=@();resources=@();scope='Static inspection of the exact isolated Java17/Gradle7.5.1 SDK fixture APK and actual successful export/assembly evidence. No APK launch, SDK initialization, purchase, payment recovery, vendor support certification or production activation.'}
function Check([bool]$value,[string]$name){if(!$value){throw $name};$script:report.checks+=,$name}
function Bind([string]$path,[string]$name){$script:report.bindings+=,[ordered]@{path=$name;sha256=(Hash $path)}}
function Dump-Aapt([string]$name,[string[]]$arguments){
    $path=Join-Path $output $name
    $lines=& $aapt @arguments 2>&1;$code=$LASTEXITCODE
    $lines|Set-Content -LiteralPath $path -Encoding UTF8
    Check ($null -ne $code -and $code -eq 0) ('AAPT completed: '+$name)
    Bind $path $name
    return [IO.File]::ReadAllText($path)
}
function Resource([string]$name,[string]$expected,[string]$dump){
    $lines=$dump -split '\r?\n';$ids=@();$values=@()
    for($i=0;$i -lt $lines.Count;$i++){
        if($lines[$i] -notmatch (':string/'+[regex]::Escape($name)+':')){continue}
        if($lines[$i] -match 'resource\s+(0x[0-9a-fA-F]+)'){$ids+=,$Matches[1].ToLowerInvariant()}
        for($j=$i;$j -le [Math]::Min($i+8,$lines.Count-1);$j++){
            if($j -gt $i -and $lines[$j] -match '\bresource\s+0x'){break}
            if($lines[$j] -match '\(string(?:8|16)\)\s+"([^"\r\n]*)"'){$values+=,$Matches[1]}
        }
    }
    $ids=@($ids|Select-Object -Unique);$values=@($values|Select-Object -Unique)
    Check ($ids.Count -eq 1 -and $values.Count -eq 1 -and $values[0] -ceq $expected) ('APK resource exact: '+$name)
    $script:report.resources+=,[ordered]@{name=$name;id=$ids[0];value=$values[0]}
    return $ids[0]
}
try {
    $assemblyPath=Join-Path $spike 'AndroidAssembly.json';$assembly=Get-Content -LiteralPath $assemblyPath -Raw -Encoding UTF8|ConvertFrom-Json
    Check ($assembly.status -ceq 'PASS_ISOLATED_ANDROID_RUSTORE81_STANDALONE_ASSEMBLY' -and !$assembly.apkLaunched -and $assembly.syntheticConfiguration) 'Actual standalone assembly PASS and explicitly unlaunched'
    Check (@($assembly.steps).Count -eq 3 -and @($assembly.steps|Where-Object {$_.exitCode -ne 0 -or $null -eq $_.exitCode -or $_.pid -le 0 -or !$_.handleRetained -or $_.timedOut}).Count -eq 0) 'All three actual Gradle processes succeeded with retained handles'
    $exportPath=Join-Path $spike 'AndroidExport.json';$export=Get-Content -LiteralPath $exportPath -Raw -Encoding UTF8|ConvertFrom-Json
    Check ((Hash $exportPath) -ceq $assembly.exportReportSHA256) 'Assembly binds exact Unity export report'
    Check ($export.status -ceq 'PASS_ISOLATED_ANDROID_RUSTORE81_GRADLE_EXPORT' -and $export.jdkSettingsUnchanged -and $export.actualAdapterSdkBranchCompiled -and $export.output.EndsWith('GradleExportR2')) 'Fresh R2 export uses unchanged embedded JDK and actual adapter SDK branch'
    $processPath=Join-Path $spike 'AndroidExportProcess.json';$process=Get-Content -LiteralPath $processPath -Raw -Encoding UTF8|ConvertFrom-Json
    Check ((Hash $processPath) -ceq $assembly.exportProcessSHA256 -and $process.exitCode -eq 0 -and $process.pid -gt 0 -and !$process.timedOut -and $process.sdkManagerOptionsRestored) 'Actual Unity export process and environment restoration'
    foreach($binding in $export.sourceBindings){Check ((Hash (Join-Path $spike $binding.path)) -ceq $binding.sha256) ('Exact export source: '+$binding.path)}
    foreach($binding in $export.sourceBindings|Where-Object {$_.path.StartsWith('Assets/Integration/')}){
        $main=Join-Path $repo ('Unity/Assets/HeartOfTheRain/App/RuStore/Runtime/'+[IO.Path]::GetFileName($binding.path))
        Check ((Hash $main) -ceq $binding.sha256) ('Actual main adapter/contracts source matches compiled copy: '+[IO.Path]::GetFileName($main))
    }
    foreach($binding in $export.exportBindings){Check ((Hash (Join-Path $export.output $binding.path)) -ceq $binding.sha256) ('Exact exported Gradle/native/manifest input: '+$binding.path)}
    foreach($step in $assembly.steps){foreach($kind in @('stdout','stderr')){$path=$step.$kind;$field=$kind+'SHA256';Check ((Hash $path) -ceq $step.$field) ('Actual Gradle log binding: '+[IO.Path]::GetFileName($path));Copy-Item -LiteralPath $path -Destination (Join-Path $output ([IO.Path]::GetFileName($path)));Bind (Join-Path $output ([IO.Path]::GetFileName($path))) ([IO.Path]::GetFileName($path))}}
    Copy-Item -LiteralPath $assemblyPath -Destination (Join-Path $output 'AndroidAssembly.json');Bind (Join-Path $output 'AndroidAssembly.json') 'AndroidAssembly.json'
    $apk=[IO.Path]::GetFullPath($assembly.apk);$allowed=[IO.Path]::GetFullPath((Join-Path $spike 'Build/GradleExportR2/launcher/build/outputs/apk/release')).TrimEnd('\')+'\'
    Check ($apk.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)) 'APK resides in the bound fresh R2 export'
    Check ((Hash $apk) -ceq $assembly.apkSHA256 -and (Get-Item -LiteralPath $apk).Length -eq $assembly.apkBytes) 'Actual APK SHA256 and bytes match successful assembly'
    $report.apk=$apk;$report.apkSHA256=Hash $apk;$report.apkBytes=(Get-Item -LiteralPath $apk).Length;$report.aaptSHA256=Hash $aapt
    $graph=[IO.File]::ReadAllText((Join-Path $output 'GradleDependencies17.stdout.log'))
    foreach($pair in @(@('pay','11.1.0'),@('core','10.5.0'))){$matches=[regex]::Matches($graph,('ru\.rustore\.sdk:'+ $pair[0]+':([^\s]+)(?:\s+->\s+([^\s]+))?'));Check ($matches.Count -gt 0) ('Resolved native dependency exists: '+$pair[0]);foreach($match in $matches){$resolved=if($match.Groups[2].Success){$match.Groups[2].Value}else{$match.Groups[1].Value};Check ($resolved -ceq $pair[1]) ('Exact native dependency version: '+$pair[0]+' '+$resolved)}}
    $badging=Dump-Aapt 'APK_Badging.txt' @('dump','badging',$apk)
    Check ($badging -match "(?m)^package: name='com\.heartoftherain\.sdkspike'") 'APK has synthetic fixture package ID'
    Check ($badging -match "(?m)^sdkVersion:'26'" -and $badging -match "(?m)^targetSdkVersion:'34'") 'APK minimum26 and explicit fixture target34'
    Check ($badging -match "(?m)^native-code: 'arm64-v8a'\s*$") 'APK native architecture is exactly ARM64'
    $tree=Dump-Aapt 'APK_Manifest.xmltree.txt' @('dump','xmltree',$apk,'AndroidManifest.xml')
    $resources=Dump-Aapt 'APK_Resources.txt' @('dump','--values','resources',$apk)
    $console=Resource 'rustore_PayClientSettings_consoleApplicationId' '123456' $resources
    $scheme=Resource 'rustore_PayClientSettings_deeplinkScheme' 'hotr-spike-build-only' $resources
    $internal=Resource 'rustore_PayClientSettings_internalConfigKey' 'unity' $resources
    Check ($tree.Contains('ru.rustore.sdk.pay.RuStorePayContentProvider') -and $tree.Contains('com.heartoftherain.sdkspike.sdk.pay')) 'Actual binary manifest includes native Pay provider and fixture authority'
    Check ($tree.Contains('ru.rustore.unitysdk.RuStoreDeeplinkActivityDefault') -and $tree -match ('android:scheme[^\r\n]*=@'+[regex]::Escape($scheme))) 'Actual binary manifest deep link resolves to synthetic scheme resource'
    foreach($pair in @(@('console_app_id_value',$console),@('sdk_pay_scheme_value',$scheme),@('internal_config_key',$internal))){Check ($tree -match ('android:name[^\r\n]*"'+[regex]::Escape($pair[0])+'"[^\r\n]*\r?\n\s+A: android:value[^\r\n]*=@'+[regex]::Escape($pair[1]))) ('Actual binary SDK metadata resource: '+$pair[0])}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($apk)
    try {Check ($null -ne $zip.GetEntry('lib/arm64-v8a/libil2cpp.so') -and $null -ne $zip.GetEntry('lib/arm64-v8a/libunity.so') -and $null -ne $zip.GetEntry('classes.dex')) 'Actual APK includes ARM64 IL2CPP/Unity and Android bytecode'}finally{$zip.Dispose()}
    foreach($binding in $assembly.generatedManifestBindings){$path=Join-Path $export.output $binding.path;Check ((Hash $path) -ceq $binding.sha256) ('Actual merged manifest binding: '+$binding.path);$destination=Join-Path $output ('MergedManifests/'+$binding.path);New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination)|Out-Null;Copy-Item -LiteralPath $path -Destination $destination;Bind $destination ('MergedManifests/'+$binding.path)}
    $report.status='PASS_STATIC_UNLAUNCHED_RUSTORE81_SDK_APK_INSPECTION'
}catch {$report.error=$_.Exception.Message}
finally {$report|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $output 'APK_Inspection.json') -Encoding UTF8}
$report|Select-Object status,error,apkSHA256,apkBytes|ConvertTo-Json -Compress|Write-Output
if($report.status -eq 'PASS_STATIC_UNLAUNCHED_RUSTORE81_SDK_APK_INSPECTION'){exit 0}else{exit 1}
