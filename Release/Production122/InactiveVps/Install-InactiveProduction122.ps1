<# Install NEW inactive production source/templates only. No DB, keys, service or proxy activation. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ArchiveSHA256,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ManifestSHA256,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$TestReportSHA256,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$PythonSHA256,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$BasePythonSHA256,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$VenvConfigSHA256,
    [ValidatePattern('^3\.[0-9]+\.[0-9]+$')][string]$ExpectedPythonVersion='3.14.10'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.IO.Compression.FileSystem

$sourceRoot122='C:\Apps\HeartOfTheRain\Production122'
$backendRoot122=Join-Path $sourceRoot122 'Backend'
$servicesRoot122='C:\ProgramData\HeartOfTheRain\production-services'
$secretsRoot122='C:\ProgramData\HeartOfTheRain\production-secrets'
$authorityRoot122='C:\ProgramData\HeartOfTheRain\production-authority'
$python122='C:\Apps\HeartOfTheRain\Backend\.venv-service\Scripts\python.exe'
$basePython122='C:\Program Files\Python314\python.exe'
$venvConfig122='C:\Apps\HeartOfTheRain\Backend\.venv-service\pyvenv.cfg'
$existingLock122='C:\Apps\HeartOfTheRain\Backend\requirements.lock'
$stagingBackend122='C:\Apps\HeartOfTheRain\Backend\hotr_backend'
$stagingManifest122='C:\ProgramData\HeartOfTheRain\services\staging-manifest.json'
$stagingOwner122='C:\ProgramData\HeartOfTheRain\staging-data\.hotr-staging105-owner.json'
$stagingProxy122='C:\ProgramData\HeartOfTheRain\services\Caddyfile'

function Assert-Plain122([string]$Value) {
    if ($Value -notmatch '^[A-Za-z]:\\' -or $Value -match '["\x00-\x1f]' -or [IO.Path]::GetFullPath($Value) -ne $Value) {throw 'Canonical local path required'}
    $cursor122=$Value
    while ($cursor122) {
        if (Test-Path -LiteralPath $cursor122) {
            if (((Get-Item -LiteralPath $cursor122 -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'Linked path rejected'}
        }
        $cursor122=[IO.Path]::GetDirectoryName($cursor122)
    }
}

function Hash-Bytes122([byte[]]$Bytes) {
    $sha122=[Security.Cryptography.SHA256]::Create()
    try {return ([BitConverter]::ToString($sha122.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()} finally {$sha122.Dispose()}
}

function Read-Entry122($Entry) {
    if ($Entry.Length -lt 0 -or $Entry.Length -gt 1048576) {throw 'Bounded archive entry required'}
    $stream122=$Entry.Open()
    $memory122=New-Object IO.MemoryStream
    try {
        $buffer122=New-Object byte[] 65536
        while (($read122=$stream122.Read($buffer122,0,$buffer122.Length)) -gt 0) {
            if ($memory122.Length+$read122 -gt 1048576) {throw 'Expanded archive entry exceeds bounded size'}
            $memory122.Write($buffer122,0,$read122)
        }
        if ($memory122.Length -ne $Entry.Length) {throw 'Archive entry declared size mismatch'}
        return ,$memory122.ToArray()
    } finally {$memory122.Dispose();$stream122.Dispose()}
}

function Restricted-Directory122([string]$Directory) {
    $null=New-Item -ItemType Directory -Path $Directory -ErrorAction Stop
    & icacls.exe $Directory /inheritance:r | Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'Private ACL inheritance change failed'}
    & icacls.exe $Directory /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-19:(OI)(CI)RX' | Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'Private ACL grant failed'}
}

function Assert-ReadOnlyService122([string]$Directory) {
    $acl122=Get-Acl -LiteralPath $Directory
    $allowed122=@('S-1-5-18','S-1-5-32-544','S-1-5-19')
    $serviceRead122=$false
    foreach ($entry122 in $acl122.Access) {
        $sid122=$entry122.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
        if ($entry122.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or $sid122 -notin $allowed122) {throw 'Unexpected private ACL entry'}
        if ($sid122 -eq 'S-1-5-19') {
            $writeMask122=2 -bor 4 -bor 16 -bor 64 -bor 256 -bor 65536 -bor 262144 -bor 524288
            if (([int64]$entry122.FileSystemRights -band $writeMask122) -ne 0) {throw 'LocalService write access rejected outside logs'}
            $serviceRead122=$true
        }
    }
    if (-not $serviceRead122) {throw 'LocalService read access missing'}
}

function Stage-Pins122 {
    $pins122=@{}
    foreach ($file122 in @(Get-ChildItem -LiteralPath $stagingBackend122 -Filter '*.py' -File -Recurse)) {
        $pins122[$file122.FullName]=(Get-FileHash -LiteralPath $file122.FullName -Algorithm SHA256).Hash
    }
    foreach ($file122 in @($stagingManifest122,$stagingOwner122,$stagingProxy122)) {
        $pins122[$file122]=(Get-FileHash -LiteralPath $file122 -Algorithm SHA256).Hash
    }
    return $pins122
}

foreach ($path122 in @($Archive,$sourceRoot122,$servicesRoot122,$secretsRoot122,$authorityRoot122,$python122,$basePython122,$venvConfig122,$existingLock122)) {Assert-Plain122 $path122}
foreach ($path122 in @($sourceRoot122,$servicesRoot122,$secretsRoot122,$authorityRoot122)) {
    if (Test-Path -LiteralPath $path122) {throw 'Existing production target preserved; no initialization or adoption allowed'}
    if (-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($path122)) -PathType Container)) {throw 'Existing private parent required'}
    $drive122=New-Object IO.DriveInfo([IO.Path]::GetPathRoot($path122))
    if ($drive122.DriveType -ne [IO.DriveType]::Fixed) {throw 'Fixed local production storage required'}
}
if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ArchiveSHA256.ToLowerInvariant()) {throw 'Archive hash mismatch'}
if ((Get-FileHash -LiteralPath $python122 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PythonSHA256.ToLowerInvariant()) {throw 'Installed interpreter hash mismatch'}
if ((Get-FileHash -LiteralPath $basePython122 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $BasePythonSHA256.ToLowerInvariant()) {throw 'Installed base interpreter hash mismatch'}
if ((Get-FileHash -LiteralPath $venvConfig122 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $VenvConfigSHA256.ToLowerInvariant()) {throw 'Installed virtual environment configuration hash mismatch'}
$zip122=[IO.Compression.ZipFile]::OpenRead($Archive)
try {
    if ($zip122.Entries.Count -lt 2 -or $zip122.Entries.Count -gt 513) {throw 'Bounded reviewed archive required'}
    $manifestEntries122=@($zip122.Entries | Where-Object {$_.FullName -ceq 'ProductionFiles122.json'})
    if ($manifestEntries122.Count -ne 1) {throw 'One exact production file manifest required'}
    $manifestBytes122=Read-Entry122 $manifestEntries122[0]
    if ((Hash-Bytes122 $manifestBytes122) -ne $ManifestSHA256.ToLowerInvariant()) {throw 'Bundle manifest hash mismatch'}
    $manifest122=[Text.Encoding]::UTF8.GetString($manifestBytes122) | ConvertFrom-Json
    if ($manifest122.version -ne 1 -or $manifest122.kind -ne 'HeartOfTheRainInactiveProductionFiles122' -or
        $manifest122.state -ne 'InactiveFilesOnly' -or $manifest122.authorityInitializationAllowed -or
        $manifest122.serviceInstallationAllowed -or $manifest122.providerActivationAllowed -or
        $manifest122.sourceRoot -cne $sourceRoot122 -or $manifest122.backendRoot -cne $backendRoot122 -or
        $manifest122.servicesRoot -cne $servicesRoot122 -or $manifest122.secretsRoot -cne $secretsRoot122 -or
        $manifest122.authorityRoot -cne $authorityRoot122 -or $manifest122.pythonExecutable -cne $python122 -or
        $manifest122.basePythonExecutable -cne $basePython122 -or $manifest122.venvConfiguration -cne $venvConfig122 -or
        $manifest122.onHostPythonVersionRequired -cne $ExpectedPythonVersion -or
        $manifest122.testReport.sha256 -ne $TestReportSHA256.ToLowerInvariant()) {throw 'Exact inactive bundle contract required'}
    if ((Get-FileHash -LiteralPath $existingLock122 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest122.requirementsLockSHA256) {throw 'Existing interpreter dependency lock differs'}
    $entries122=@{}
    $payload122=@{}
    $total122=0
    foreach ($entry122 in $zip122.Entries) {
        $name122=$entry122.FullName
        if ($entries122.ContainsKey($name122)) {throw 'Duplicate or case-colliding archive entry'}
        $entries122[$name122]=$true
        if ($name122 -ceq 'ProductionFiles122.json') {continue}
        if ($name122 -notmatch '^(Source|Services)/[A-Za-z0-9_./-]+$' -or $name122.Split('/') -contains '..' -or $name122.EndsWith('/')) {throw 'Unexpected archive entry path'}
        $property122=$manifest122.files.PSObject.Properties[$name122]
        if ($null -eq $property122) {throw 'Unlisted archive entry preserved'}
        $bytes122=Read-Entry122 $entry122
        if ($property122.Value.bytes -ne $bytes122.Length -or $property122.Value.sha256 -notmatch '^[a-f0-9]{64}$' -or
            (Hash-Bytes122 $bytes122) -ne $property122.Value.sha256) {throw 'Payload hash or size mismatch'}
        $total122+=$bytes122.Length
        if ($total122 -gt 16777216) {throw 'Archive payload exceeds bounded size'}
        $payload122[$name122]=$bytes122
    }
    if (@($manifest122.files.PSObject.Properties).Count -ne $payload122.Count) {throw 'Missing manifest payload files'}
    if (-not $payload122.ContainsKey('Source/Backend/requirements.lock') -or
        (Hash-Bytes122 $payload122['Source/Backend/requirements.lock']) -ne $manifest122.requirementsLockSHA256) {throw 'Pinned dependency payload required'}

    # Read the existing installed environment only. No pip install/update or user
    # site is used; public package versions are compared with the exact old lock.
    $dependencyCode122=@'
import importlib.metadata as m,json,pathlib,sys
try:
 rows=[line.strip().split('==') for line in pathlib.Path(sys.argv[1]).read_text('utf-8').splitlines() if line.strip() and not line.startswith('#')]
 ok=all(len(row)==2 and m.version(row[0])==row[1] for row in rows)
 print(json.dumps(dict(status='dependencies_match' if ok else 'dependencies_differ',packages=len(rows),python=sys.version.split()[0],baseExecutable=sys._base_executable)))
 sys.exit(0 if ok else 1)
except Exception:
 print(json.dumps(dict(status='dependency_check_failed')));sys.exit(1)
'@
    $dependencyOutput122=& $python122 -I -B -c $dependencyCode122 $existingLock122
    if ($LASTEXITCODE -ne 0) {throw 'Installed dependency compatibility check failed'}
    $dependencies122=$dependencyOutput122 | ConvertFrom-Json
    if ($dependencies122.python -cne $ExpectedPythonVersion -or
        -not [string]::Equals($dependencies122.baseExecutable,$basePython122,[StringComparison]::OrdinalIgnoreCase)) {throw 'Reviewed interpreter version and base executable required'}
    $syntaxCode122=@'
import ast,json,sys,zipfile
try:
 z=zipfile.ZipFile(sys.argv[1]);names=[n for n in z.namelist() if n.startswith('Source/Backend/hotr_backend/') and n.endswith('.py')]
 for name in names:ast.parse(z.read(name),filename=name)
 print(json.dumps(dict(status='syntax_accepted',modules=len(names),python=sys.version.split()[0])))
except Exception:
 print(json.dumps(dict(status='source_syntax_rejected')));sys.exit(1)
'@
    $syntaxOutput122=& $python122 -I -B -c $syntaxCode122 $Archive
    if ($LASTEXITCODE -ne 0) {throw 'Existing interpreter source syntax check failed'}
    $syntax122=$syntaxOutput122 | ConvertFrom-Json
    $stageBefore122=Stage-Pins122

    # All read-only validation above precedes creation of any production root.
    Restricted-Directory122 $sourceRoot122
    Restricted-Directory122 $servicesRoot122
    Restricted-Directory122 $secretsRoot122
    foreach ($name122 in @($payload122.Keys | Sort-Object)) {
        if ($name122.StartsWith('Source/')) {$base122=$sourceRoot122;$relative122=$name122.Substring(7)}
        else {$base122=$servicesRoot122;$relative122=$name122.Substring(9)}
        $target122=[IO.Path]::GetFullPath((Join-Path $base122 $relative122.Replace('/','\')))
        if (-not $target122.StartsWith($base122+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Resolved target escaped new production root'}
        $parent122=[IO.Path]::GetDirectoryName($target122)
        if (-not (Test-Path -LiteralPath $parent122)) {$null=New-Item -ItemType Directory -Path $parent122 -Force}
        $stream122=[IO.File]::Open($target122,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {$stream122.Write($payload122[$name122],0,$payload122[$name122].Length);$stream122.Flush($true)} finally {$stream122.Dispose()}
        if ((Get-FileHash -LiteralPath $target122 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest122.files.PSObject.Properties[$name122].Value.sha256) {throw 'Installed file digest mismatch'}
    }
    foreach ($path122 in @($sourceRoot122,$backendRoot122,$servicesRoot122,$secretsRoot122)) {Assert-ReadOnlyService122 $path122}
    $logs122=Join-Path $servicesRoot122 'logs'
    $null=New-Item -ItemType Directory -Path $logs122
    & icacls.exe $logs122 /grant:r '*S-1-5-19:(OI)(CI)M' | Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'Future log ACL grant failed'}
    if (@(Get-ChildItem -LiteralPath $secretsRoot122 -Force).Count -ne 0 -or (Test-Path -LiteralPath $authorityRoot122)) {throw 'Keys or authority unexpectedly present'}
    $stageAfter122=Stage-Pins122
    if ($stageBefore122.Count -ne $stageAfter122.Count) {throw 'Existing staging source inventory changed'}
    foreach ($path122 in $stageBefore122.Keys) {if (-not $stageAfter122.ContainsKey($path122) -or $stageBefore122[$path122] -ne $stageAfter122[$path122]) {throw 'Existing staging source or authority configuration changed'}}
    $manifestTarget122=Join-Path $servicesRoot122 'inactive-files122.manifest.json'
    $stream122=[IO.File]::Open($manifestTarget122,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$stream122.Write($manifestBytes122,0,$manifestBytes122.Length);$stream122.Flush($true)} finally {$stream122.Dispose()}
    $result122=[ordered]@{status='inactive_production_files_staged';sourceRoot=$sourceRoot122;backendRoot=$backendRoot122;servicesRoot=$servicesRoot122;secretsRoot=$secretsRoot122;
        files=$payload122.Count;bytes=$total122;archiveSHA256=$ArchiveSHA256.ToLowerInvariant();manifestSHA256=$ManifestSHA256.ToLowerInvariant();testReportSHA256=$TestReportSHA256.ToLowerInvariant();
        python=$dependencies122;syntax=$syntax122;pythonLauncherSHA256=$PythonSHA256.ToLowerInvariant();basePythonSHA256=$BasePythonSHA256.ToLowerInvariant();venvConfigSHA256=$VenvConfigSHA256.ToLowerInvariant();existingStagingPinsUnchanged=$true;localServiceCodeConfigSecretsReadOnly=$true;localServiceModifyOnlyFutureLogs=$true;
        authorityInitialized=$false;authorityDirectoryCreated=$false;keysCreated=$false;placeholderKeyFilesCreated=$false;servicesInstalled=$false;servicesStarted=$false;proxyChanged=$false;productionActivated=$false}
    $receiptTarget122=Join-Path $servicesRoot122 'inactive-install122.receipt.json'
    $resultBytes122=(New-Object Text.UTF8Encoding($false)).GetBytes(($result122 | ConvertTo-Json -Depth 8 -Compress)+"`n")
    $stream122=[IO.File]::Open($receiptTarget122,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$stream122.Write($resultBytes122,0,$resultBytes122.Length);$stream122.Flush($true)} finally {$stream122.Dispose()}
    $result122 | ConvertTo-Json -Depth 8 -Compress
} finally {$zip122.Dispose()}
