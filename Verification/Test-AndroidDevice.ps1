param(
    [string]$DeviceSerial = '',
    [switch]$Install,
    [switch]$Launch
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$adbPath = 'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe'
$apkPath = Join-Path $repoPath 'Unity\Builds\Verification\HeartOfTheRain_Development.apk'
if (-not (Test-Path -LiteralPath $adbPath)) { throw 'The pinned Unity Android platform tools are missing.' }
$listing = & $adbPath devices
if ($LASTEXITCODE -ne 0) { throw 'ADB device discovery failed.' }
$devices = @($listing | Where-Object { $_ -match '^\S+\s+device$' } | ForEach-Object { ($_ -split '\s+')[0] })
if ($devices.Count -eq 0) { throw 'No authorized Android device. Connect a phone with USB debugging enabled and authorize this computer on the phone.' }
if ($DeviceSerial -eq '') {
    if ($devices.Count -ne 1) { throw 'Multiple authorized devices are connected; supply -DeviceSerial.' }
    $DeviceSerial = $devices[0]
}
if ($devices -notcontains $DeviceSerial) { throw 'The selected device is missing or unauthorized.' }
$model = & $adbPath -s $DeviceSerial shell getprop ro.product.model
$androidVersion = & $adbPath -s $DeviceSerial shell getprop ro.build.version.release
$abis = & $adbPath -s $DeviceSerial shell getprop ro.product.cpu.abilist
if ($abis -notmatch 'arm64-v8a') { throw 'The prepared APK requires an ARM64 Android device.' }
Write-Output "Authorized device: $model; Android $androidVersion; ABI $abis"
if ($Install) {
    if (-not (Test-Path -LiteralPath $apkPath)) { throw 'Build the development APK first.' }
    & $adbPath -s $DeviceSerial install -r $apkPath
    if ($LASTEXITCODE -ne 0) { throw 'APK installation failed. No uninstall or data-clear fallback was attempted.' }
}
if ($Launch) {
    & $adbPath -s $DeviceSerial shell monkey -p com.heartoftherain.verification -c android.intent.category.LAUNCHER 1
    if ($LASTEXITCODE -ne 0) { throw 'Launching the verification app failed.' }
}
Write-Output 'Record results in Verification/Device_Test_Matrix.csv and Campaign_Playtest.csv; launch alone is not a device pass.'
