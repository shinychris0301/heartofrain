<# Publish the owner's three explicitly temporary pages without changing the API authority. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$SourceDirectory,
    [string]$PublicRoot='C:\ProgramData\HeartOfTheRain\public-draft122',
    [string]$CaddyFile='C:\ProgramData\HeartOfTheRain\services\Caddyfile',
    [string]$CaddyExe='C:\Tools\Caddy\caddy.exe'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Assert-Plain122([string]$Value) {
    if ($Value -notmatch '^[A-Za-z]:\\' -or $Value -match '["\x00-\x1f]' -or [IO.Path]::GetFullPath($Value) -ne $Value) { throw 'Canonical local path required' }
    $cursor122=$Value
    while ($cursor122) {
        if (Test-Path -LiteralPath $cursor122) {
            if (((Get-Item -LiteralPath $cursor122 -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Linked path rejected' }
        }
        $cursor122=[IO.Path]::GetDirectoryName($cursor122)
    }
}

function Invoke-Caddy122([string]$Command,[string]$Configuration,[string]$Tag) {
    $stdout122=$CaddyFile+'.'+$Tag+'.stdout'
    $stderr122=$CaddyFile+'.'+$Tag+'.stderr'
    if ((Test-Path -LiteralPath $stdout122) -or (Test-Path -LiteralPath $stderr122)) { throw 'Existing private command logs preserved' }
    $process122=Start-Process -FilePath $CaddyExe -ArgumentList @($Command,'--config',('"'+$Configuration+'"'),'--adapter','caddyfile') -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $stdout122 -RedirectStandardError $stderr122
    return $process122.ExitCode
}

function Get-Candidate122([string]$Original,[string]$Root) {
    $expected122=@'
api.novamind-it.ru {
    # Operator-only routes stay available through a local management tunnel.
    @private path /internal /internal/* /docs* /redoc* /openapi.json*
    handle @private {
        respond 404
    }
    handle {
        reverse_proxy 127.0.0.1:8751
    }
}
'@
    $normal122=$Original.Replace("`r`n","`n").TrimEnd()+"`n"
    if ($normal122 -ne ($expected122.Replace("`r`n","`n").TrimEnd()+"`n")) { throw 'Unreviewed Caddy configuration preserved' }
    $slashRoot122=$Root.Replace('\','/')
    $routes122=@"
    # Temporary owner-requested pages; operator/contact details are pending.
    @draftPages122 path /privacy /support /terms
    handle @draftPages122 {
        root * "$slashRoot122"
        rewrite * {path}.html
        header Cache-Control "no-store"
        header X-Robots-Tag "noindex, nofollow"
        header X-Content-Type-Options "nosniff"
        header Referrer-Policy "no-referrer"
        header Content-Security-Policy "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        file_server
    }

"@
    return $normal122.Replace("api.novamind-it.ru {`n", "api.novamind-it.ru {`n"+$routes122)
}

foreach ($path122 in @($SourceDirectory,$PublicRoot,$CaddyFile,$CaddyExe)) { Assert-Plain122 $path122 }
if (Test-Path -LiteralPath $PublicRoot) { throw 'Existing public directory preserved' }
if (-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($PublicRoot)) -PathType Container)) { throw 'Existing private parent required' }
if ((Get-FileHash -LiteralPath $CaddyExe -Algorithm SHA256).Hash.ToLowerInvariant() -ne '5f93a9bd555f3aac9d33af2756ba14b3519d8cca4ffd55256bdaeab444c9db2a') { throw 'Reviewed Caddy executable required' }
$manifest122=Get-Content -LiteralPath (Join-Path $SourceDirectory 'pages.sha256.json') -Raw | ConvertFrom-Json
foreach ($name122 in @('privacy.html','support.html','terms.html')) {
    $source122=Join-Path $SourceDirectory $name122
    Assert-Plain122 $source122
    if ((Get-FileHash -LiteralPath $source122 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest122.$name122) { throw 'Page transfer hash mismatch' }
}
$before122=[IO.File]::ReadAllBytes($CaddyFile)
$original122=[Text.Encoding]::UTF8.GetString($before122)
$candidate122=Get-Candidate122 $original122 $PublicRoot
$pending122=$CaddyFile+'.pending-drafts122'
$backup122=$CaddyFile+'.before-drafts122'
if ((Test-Path -LiteralPath $pending122) -or (Test-Path -LiteralPath $backup122)) { throw 'Existing configuration artifacts preserved' }
$null=New-Item -ItemType Directory -Path $PublicRoot
& icacls.exe $PublicRoot /inheritance:r | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Public ACL preparation failed' }
& icacls.exe $PublicRoot /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-19:(OI)(CI)RX' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Public ACL grant failed' }
foreach ($name122 in @('privacy.html','support.html','terms.html')) {
    Copy-Item -LiteralPath (Join-Path $SourceDirectory $name122) -Destination (Join-Path $PublicRoot $name122)
    if ((Get-FileHash -LiteralPath (Join-Path $PublicRoot $name122) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest122.$name122) { throw 'Copied page mismatch' }
}
$encoding122=New-Object Text.UTF8Encoding($false)
$stream122=[IO.File]::Open($pending122,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $bytes122=$encoding122.GetBytes($candidate122); $stream122.Write($bytes122,0,$bytes122.Length); $stream122.Flush($true) } finally { $stream122.Dispose() }
$validation122=Invoke-Caddy122 'validate' $pending122 'drafts122-validate'
if ($validation122 -ne 0) { throw 'Caddy rejected candidate; existing configuration preserved' }
if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($CaddyFile)) -ne [Convert]::ToBase64String($before122)) { throw 'Concurrent Caddy change preserved' }
[IO.File]::Replace($pending122,$CaddyFile,$backup122)
$reload122=Invoke-Caddy122 'reload' $CaddyFile 'drafts122-reload'
if ($reload122 -ne 0) {
    if ([IO.File]::ReadAllText($CaddyFile) -eq $candidate122) {
        [IO.File]::WriteAllBytes($CaddyFile,$before122)
        $rollback122=Invoke-Caddy122 'reload' $CaddyFile 'drafts122-rollback'
    }
    throw 'Caddy reload failed; original rollback attempted'
}
$checks122=@()
foreach ($page122 in @('privacy','support','terms')) {
    $response122=Invoke-WebRequest -UseBasicParsing -Uri ('https://api.novamind-it.ru/'+$page122) -TimeoutSec 8
    $expectedBytes122=[IO.File]::ReadAllBytes((Join-Path $PublicRoot ($page122+'.html')))
    $body122=New-Object IO.MemoryStream
    if ($response122.RawContentStream.CanSeek) { $response122.RawContentStream.Position=0 }
    $response122.RawContentStream.CopyTo($body122)
    $matches122=[Convert]::ToBase64String($body122.ToArray()) -eq [Convert]::ToBase64String($expectedBytes122)
    $body122.Dispose()
    $checks122 += [ordered]@{page=$page122; status=[int]$response122.StatusCode; exactBody=$matches122; draft=$true}
}
$health122=Invoke-RestMethod -Uri 'https://api.novamind-it.ru/healthz' -TimeoutSec 8
if (@($checks122 | Where-Object {-not $_.exactBody -or $_.status -ne 200}).Count -or $health122.mode -ne 'staging' -or $health122.productionEnabled -ne $false) { throw 'Publication verification failed; inspect private candidate artifacts' }
[ordered]@{status='temporary_pages_published'; checks=$checks122; backendMode=$health122.mode; productionEnabled=$false;
    operatorDetailsPending=$true; legalContentApproved=$false; apiAuthorityChanged=$false; originalCaddyBackupPreserved=$true} | ConvertTo-Json -Depth 5 -Compress
