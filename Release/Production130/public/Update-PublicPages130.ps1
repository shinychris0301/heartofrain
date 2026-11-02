<# Update only the existing three static pages. -Check performs no filesystem writes. #>
# The named lease serializes this updater. Other administrators' edits are observed
# by hash/DACL checks; those checks do not atomically exclude arbitrary foreign writes.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$SourceDirectory,[switch]$Check)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Assert-PagesPlain122([string]$Path) {
    if ($Path -notmatch '^[A-Za-z]:\\' -or $Path -match '["\x00-\x1f]' -or [IO.Path]::GetFullPath($Path) -cne $Path) { throw 'PagesCanonicalPathRequired' }
    $cursor122=$Path
    while ($cursor122) {
        if ((Test-Path -LiteralPath $cursor122) -and (((Get-Item -LiteralPath $cursor122 -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) { throw 'PagesLinkedPathRejected' }
        $cursor122=[IO.Path]::GetDirectoryName($cursor122)
    }
}
function Read-PagesBytes122([string]$Path,[int]$Maximum=262144) {
    Assert-PagesPlain122 $Path
    if (-not(Test-Path -LiteralPath $Path -PathType Leaf) -or (Get-Item -LiteralPath $Path).Length -gt $Maximum) { throw 'PagesBoundedFileRequired' }
    $bytes122=[IO.File]::ReadAllBytes($Path)
    if ($bytes122.Length -gt $Maximum) { throw 'PagesBoundedFileRequired' }
    return ,$bytes122
}
function Get-PagesHash122([byte[]]$Bytes) {
    $sha122=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha122.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() } finally { $sha122.Dispose() }
}
function Write-PagesNew122([string]$Path,[byte[]]$Bytes) {
    Assert-PagesPlain122 $Path
    $stream122=[IO.FileStream]::new($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None,4096,[IO.FileOptions]::WriteThrough)
    try { $stream122.Write($Bytes,0,$Bytes.Length);$stream122.Flush($true) } finally { $stream122.Dispose() }
}
function Assert-PagesServiceAcl122($Acl) {
    $allow122=[int64]0;$deny122=[int64]0
    foreach($rule122 in $Acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
        if ($rule122.IdentityReference.Value -ne 'S-1-5-19') { continue }
        if ($rule122.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow) { $allow122=$allow122 -bor [int64]$rule122.FileSystemRights }
        else { $deny122=$deny122 -bor [int64]$rule122.FileSystemRights }
    }
    $read122=[int64][Security.AccessControl.FileSystemRights]::ReadAndExecute
    $write122=[int64][Security.AccessControl.FileSystemRights]::Write -bor [int64][Security.AccessControl.FileSystemRights]::Delete -bor [int64][Security.AccessControl.FileSystemRights]::ChangePermissions -bor [int64][Security.AccessControl.FileSystemRights]::TakeOwnership
    if (($allow122 -band $read122) -ne $read122 -or ($deny122 -band $read122) -ne 0 -or ($allow122 -band $write122) -ne 0) { throw 'PagesLocalServiceReadOnlyAclRequired' }
}
function Get-PagesAccess122($Acl) { return $Acl.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Access) }
function Set-PagesFileAccess122([string]$Path,$Acl) {
    $access122=[Security.AccessControl.FileSecurity]::new()
    $access122.SetSecurityDescriptorSddlForm((Get-PagesAccess122 $Acl),[Security.AccessControl.AccessControlSections]::Access)
    [IO.File]::SetAccessControl($Path,$access122)
}
function Protect-PagesBackup122([string]$Path) {
    $acl122=[Security.AccessControl.DirectorySecurity]::new();$acl122.SetAccessRuleProtection($true,$false)
    foreach($sid122 in @('S-1-5-18','S-1-5-32-544')) {
        $acl122.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid122),[Security.AccessControl.FileSystemRights]::FullControl,[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit',[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow))
    }
    [IO.Directory]::SetAccessControl($Path,$acl122)
}
function Enter-PagesLease122 {
    $mutex122=[Threading.Mutex]::new($false,'Global\HOTR122_PublicPagesUpdate')
    $taken122=$false
    try {
        try { $taken122=$mutex122.WaitOne(0) } catch [Threading.AbandonedMutexException] { $taken122=$true }
        if (-not$taken122) { throw 'PagesUpdaterBusy' }
        return $mutex122
    } catch { $mutex122.Dispose();throw }
}
function Get-PagesAttribute122([string]$Tag,[string]$Name) {
    $pattern122='(?is)(?:^|\s)'+[Regex]::Escape($Name)+'\s*=\s*["''](?<value>[^"'']*)["'']'
    $matches122=[Regex]::Matches($Tag,$pattern122)
    if ($matches122.Count -ne 1) { return $null }
    return [Net.WebUtility]::HtmlDecode($matches122[0].Groups['value'].Value)
}
function Assert-PagesCoherence122([string]$Html,$Publication) {
    $clean122=[Regex]::Replace($Html,'(?is)<!--.*?-->|<script\b[^>]*>.*?</script\s*>|<style\b[^>]*>.*?</style\s*>',' ')
    $visible122=[Net.WebUtility]::HtmlDecode([Regex]::Replace($clean122,'<[^>]*>',' '))
    $visible122=[Regex]::Replace($visible122,'\s+',' ')
    foreach($value122 in @($Publication.operatorName,$Publication.country)) {
        if ($visible122.IndexOf($value122,[StringComparison]::Ordinal) -lt 0) { throw 'PagesConfirmedIdentityMissingFromHtml' }
    }
    $complete122=@([Regex]::Matches($clean122,'(?is)<meta\b[^>]*>')|Where-Object{(Get-PagesAttribute122 $_.Value 'name') -ceq 'publication-status'})
    if ($complete122.Count -ne 1 -or (Get-PagesAttribute122 $complete122[0].Value 'content') -cne 'complete') { throw 'PagesCompletePublicationMetaRequired' }
    $contact122=$false
    foreach($tag122 in [Regex]::Matches($clean122,'(?is)<a\b[^>]*>')) {
        $href122=Get-PagesAttribute122 $tag122.Value 'href'
        if ($null -eq $href122 -or -not$href122.StartsWith('mailto:',[StringComparison]::OrdinalIgnoreCase)) { continue }
        $address122=[Uri]::UnescapeDataString($href122.Substring(7).Split('?')[0])
        if ($address122 -ceq $Publication.supportEmail) { $contact122=$true }
    }
    if (-not$contact122) { throw 'PagesConfirmedSupportMailtoRequired' }
}
function Get-PagesPublic122([string]$Name) {
    if ($Name -notin @('privacy.html','support.html','terms.html')) { throw 'PagesUnknownPublicPath' }
    if ($null -ne [Net.ServicePointManager]::ServerCertificateValidationCallback) { throw 'PagesTlsOverrideRejected' }
    $request122=[Net.HttpWebRequest]::Create('https://api.novamind-it.ru/'+[IO.Path]::GetFileNameWithoutExtension($Name))
    $request122.Method='GET';$request122.AllowAutoRedirect=$false;$request122.Timeout=5000;$request122.ReadWriteTimeout=5000
    $request122.UserAgent='HOTR-PublicPages-Verification/1';$request122.Proxy=$null
    # The normal OS TLS/certificate validation remains enabled; there is no bypass callback.
    $watch122=[Diagnostics.Stopwatch]::StartNew()
    try { $response122=$request122.GetResponse() } catch { throw 'PagesPublicRequestFailed' }
    try {
        if ([int]$response122.StatusCode -ne 200 -or $response122.ContentType -notlike 'text/html*') { throw 'PagesPublicStatusInvalid' }
        $body122=[IO.MemoryStream]::new();$input122=$response122.GetResponseStream()
        try {
            $buffer122=New-Object byte[] 4096
            while(($count122=$input122.Read($buffer122,0,$buffer122.Length)) -gt 0) {
                if ($watch122.ElapsedMilliseconds -gt 10000) { throw 'PagesPublicReadDeadline' }
                if ($body122.Length+$count122 -gt 262144) { throw 'PagesPublicBodyTooLarge' }
                $body122.Write($buffer122,0,$count122)
            }
            if ($watch122.ElapsedMilliseconds -gt 10000) { throw 'PagesPublicReadDeadline' }
            return [ordered]@{status=200;sha256=(Get-PagesHash122 $body122.ToArray())}
        } finally { $input122.Dispose();$body122.Dispose() }
    } finally { $response122.Close() }
}
function Invoke-PagesUpdate122([string]$Source,[string]$Root,[string]$Caddy,[bool]$CheckOnly) {
    $names122=@('privacy.html','support.html','terms.html')
    # Only the exact published 31 October edition or this approved revision may be replaced.
    $old122=@{'privacy.html'='324cf228c8b129ef1c930033c295b09cd505b97b852f98bae6f0e13b800be247';'support.html'='7958442598840152ebc5f516aaa7843bac5f5ca6258d0d75e00ea619e8da0849';'terms.html'='46f86a5d0d48847ab9453c891518e48e5d01b36f2bedf8e2b63f8450f5f951a4'}
    $result122=[ordered]@{status='blocked';ok=$false;checkOnly=$CheckOnly;changedPages=@();rolledBackPages=@();concurrentPagesPreserved=@();caddyUnchanged=$false;publicChecks=@();backendMutationRequested=$false;caddyReloaded=$false;concurrencyScope='named_mutex_for_this_updater; observed_hash_guards_for_other_writers'}
    $original122=@{};$next122=@{};$acl122=@{};$pending122=@{};$applied122=[Collections.Generic.List[string]]::new();$caddyHash122=$null;$lease122=$null
    try {
        $lease122=Enter-PagesLease122
        foreach($path122 in @($Source,$Root,$Caddy)) { Assert-PagesPlain122 $path122 }
        if ($Source.TrimEnd('\') -ieq $Root.TrimEnd('\') -or -not(Test-Path -LiteralPath $Source -PathType Container) -or -not(Test-Path -LiteralPath $Root -PathType Container)) { throw 'PagesExistingSeparateDirectoriesRequired' }
        Assert-PagesServiceAcl122 (Get-Acl -LiteralPath $Root)
        $caddyHash122=(Get-FileHash -LiteralPath $Caddy -Algorithm SHA256).Hash.ToLowerInvariant();$result122.caddySHA256=$caddyHash122
        $utf8122=[Text.UTF8Encoding]::new($false,$true)
        $manifestBytes122=Read-PagesBytes122 (Join-Path $Source 'pages.sha256.json') 8192
        $publicationBytes122=Read-PagesBytes122 (Join-Path $Source 'publication.json') 8192
        $manifest122=$utf8122.GetString($manifestBytes122).TrimStart([char]0xfeff)|ConvertFrom-Json;$publication122=$utf8122.GetString($publicationBytes122).TrimStart([char]0xfeff)|ConvertFrom-Json
        $result122.sourceManifestSHA256=Get-PagesHash122 $manifestBytes122;$result122.publicationSHA256=Get-PagesHash122 $publicationBytes122
        if (@($manifest122.PSObject.Properties).Count -ne 3 -or (@($manifest122.PSObject.Properties.Name|Sort-Object)-join '|') -cne ($names122-join '|')) { throw 'PagesExactManifestRequired' }
        if ($publication122.schemaVersion -isnot [int] -or $publication122.schemaVersion -ne 1 -or $publication122.finalPublicationReady -isnot [bool] -or $publication122.finalPublicationReady -ne $true) { throw 'PagesFinalPublicationNotReady' }
        foreach($field122 in @('operatorIdentityConfirmed','supportContactConfirmed')) { if($publication122.$field122 -isnot [bool] -or $publication122.$field122 -ne $true) { throw 'PagesOperatorOrContactPending' } }
        foreach($field122 in @('operatorName','country','supportEmail')) {
            $value122=$publication122.$field122
            if ($value122 -isnot [string] -or [string]::IsNullOrWhiteSpace($value122) -or $value122 -cne $value122.Trim() -or $value122.Length -gt 254 -or $value122 -match '(?i)\b(pending|draft|tbd|todo|unknown|placeholder|replace[_ -]?me)\b|not\s+(yet\s+)?provided|to\s+be\s+(confirmed|determined)|\u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a|\u043e\u0436\u0438\u0434\u0430.*\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d') { throw 'PagesOperatorOrContactPending' }
        }
        if ($publication122.supportEmail -cnotmatch '^[A-Za-z0-9._%+\-]+@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+$') { throw 'PagesAsciiEmailRequired' }
        $htmlNames122=@(Get-ChildItem -LiteralPath $Source -File -Filter '*.html'|ForEach-Object{$_.Name}|Sort-Object)
        if (($htmlNames122-join '|') -cne ($names122-join '|')) { throw 'PagesExactHtmlInventoryRequired' }
        foreach($name122 in $names122) {
            if ($manifest122.$name122 -isnot [string] -or $manifest122.$name122 -cnotmatch '^[a-f0-9]{64}$') { throw 'PagesSha256Required' }
            $next122[$name122]=Read-PagesBytes122 (Join-Path $Source $name122)
            $text122=$utf8122.GetString($next122[$name122])
            if ((Get-PagesHash122 $next122[$name122]) -cne $manifest122.$name122) { throw 'PagesSourceHashMismatch' }
            if ($text122.Contains([char]0) -or $text122 -match '(?i)\b(TBD|TODO|REPLACE_ME|DRAFT)\b|\u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a|\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u0430\u044f\s+\u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430|\u043e\u0436\u0438\u0434\u0430(?:\u0435\u0442|\u044e\u0442)\s+\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u044f') { throw 'PagesDraftContentRejected' }
            Assert-PagesCoherence122 $text122 $publication122
            $live122=Join-Path $Root $name122;$original122[$name122]=Read-PagesBytes122 $live122;$liveHash122=Get-PagesHash122 $original122[$name122]
            if ($liveHash122 -cne $old122[$name122] -and $liveHash122 -cne $manifest122.$name122) { throw 'PagesUnknownLiveContentPreserved' }
            $acl122[$name122]=Get-Acl -LiteralPath $live122;Assert-PagesServiceAcl122 $acl122[$name122]
        }
        $changes122=@($names122|Where-Object{(Get-PagesHash122 $original122[$_]) -cne $manifest122.$_})
        if (-not$CheckOnly -and $changes122.Count -gt 0) {
            $run122=[Guid]::NewGuid().ToString('N');$backup122=Join-Path ([IO.Path]::GetDirectoryName($Root)) ('public-pages-backup-'+$run122)
            Assert-PagesPlain122 $backup122;New-Item -ItemType Directory -Path $backup122 -ErrorAction Stop|Out-Null;Protect-PagesBackup122 $backup122;$result122.backupDirectory=$backup122
            foreach($name122 in $names122) { Write-PagesNew122 (Join-Path $backup122 $name122) $original122[$name122] }
            foreach($name122 in $changes122) {
                $live122=Join-Path $Root $name122;$stage122=Join-Path $Root ('.pages-'+$run122+'-'+$name122+'.pending');$pending122[$stage122]=$manifest122.$name122
                Write-PagesNew122 $stage122 $next122[$name122];Set-PagesFileAccess122 $stage122 $acl122[$name122]
                if ((Get-PagesHash122 (Read-PagesBytes122 $stage122)) -cne $manifest122.$name122 -or (Get-PagesAccess122 (Get-Acl -LiteralPath $stage122)) -cne (Get-PagesAccess122 $acl122[$name122])) { throw 'PagesStagedContentOrAclMismatch' }
                if ((Get-PagesHash122 (Read-PagesBytes122 $live122)) -cne (Get-PagesHash122 $original122[$name122]) -or (Get-PagesAccess122 (Get-Acl -LiteralPath $live122)) -cne (Get-PagesAccess122 $acl122[$name122])) { throw 'PagesConcurrentLiveChangePreserved' }
                if ((Get-FileHash -LiteralPath $Caddy -Algorithm SHA256).Hash.ToLowerInvariant() -cne $caddyHash122) { throw 'PagesConcurrentCaddyChangePreserved' }
                [IO.File]::Replace($stage122,$live122,[NullString]::Value);$applied122.Add($name122);$pending122.Remove($stage122)
                if ((Get-PagesHash122 (Read-PagesBytes122 $live122)) -cne $manifest122.$name122 -or (Get-PagesAccess122 (Get-Acl -LiteralPath $live122)) -cne (Get-PagesAccess122 $acl122[$name122])) { throw 'PagesAtomicReplacementOrAclMismatch' }
            }
        }
        foreach($name122 in $names122) {
            $expected122=if($CheckOnly){Get-PagesHash122 $original122[$name122]}else{$manifest122.$name122}
            $public122=Get-PagesPublic122 $name122;$result122.publicChecks+=@{page=$name122;status=$public122.status;sha256=$public122.sha256;matches=($public122.sha256 -ceq $expected122)}
            if ($public122.sha256 -cne $expected122) { throw 'PagesPublicBodyMismatch' }
        }
        if ((Get-FileHash -LiteralPath $Caddy -Algorithm SHA256).Hash.ToLowerInvariant() -cne $caddyHash122) { throw 'PagesConcurrentCaddyChangePreserved' }
        foreach($name122 in $names122) {
            $expected122=if($CheckOnly){Get-PagesHash122 $original122[$name122]}else{$manifest122.$name122}
            if ((Get-PagesHash122 (Read-PagesBytes122 (Join-Path $Root $name122))) -cne $expected122 -or (Get-PagesAccess122 (Get-Acl -LiteralPath (Join-Path $Root $name122))) -cne (Get-PagesAccess122 $acl122[$name122])) { throw 'PagesConcurrentLiveChangePreserved' }
        }
        if ((Get-FileHash -LiteralPath $Caddy -Algorithm SHA256).Hash.ToLowerInvariant() -cne $caddyHash122) { throw 'PagesConcurrentCaddyChangePreserved' }
        $result122.caddyUnchanged=$true
        $result122.ok=$true;$result122.status=if($CheckOnly){'preflight_passed'}elseif($applied122.Count){'pages_updated_and_verified'}else{'pages_already_current_and_verified'}
    } catch {
        $result122.errorCode=if($_.Exception.Message -cmatch '^Pages[A-Za-z0-9]+$'){$_.Exception.Message}else{'PagesUnexpectedError'}
        foreach($name122 in @($applied122.ToArray()|Sort-Object -Descending)) {
            try {
                $live122=Join-Path $Root $name122
                if ((Get-PagesHash122 (Read-PagesBytes122 $live122)) -cne (Get-PagesHash122 $next122[$name122]) -or (Get-PagesAccess122 (Get-Acl -LiteralPath $live122)) -cne (Get-PagesAccess122 $acl122[$name122])) { $result122.concurrentPagesPreserved+=,$name122;continue }
                $restore122=Join-Path $Root ('.pages-'+[Guid]::NewGuid().ToString('N')+'-'+$name122+'.rollback');$pending122[$restore122]=Get-PagesHash122 $original122[$name122]
                Write-PagesNew122 $restore122 $original122[$name122];Set-PagesFileAccess122 $restore122 $acl122[$name122]
                if ((Get-PagesHash122 (Read-PagesBytes122 $live122)) -cne (Get-PagesHash122 $next122[$name122]) -or (Get-PagesAccess122 (Get-Acl -LiteralPath $live122)) -cne (Get-PagesAccess122 $acl122[$name122])) { $result122.concurrentPagesPreserved+=,$name122;continue }
                [IO.File]::Replace($restore122,$live122,[NullString]::Value);$pending122.Remove($restore122)
                if ((Get-PagesHash122 (Read-PagesBytes122 $live122)) -cne (Get-PagesHash122 $original122[$name122]) -or (Get-PagesAccess122 (Get-Acl -LiteralPath $live122)) -cne (Get-PagesAccess122 $acl122[$name122])) { throw 'PagesRollbackVerificationFailed' }
                $result122.rolledBackPages+=,$name122
            } catch { $result122.concurrentPagesPreserved+=,$name122 }
        }
        if ($applied122.Count) { $result122.status=if($result122.rolledBackPages.Count -eq $applied122.Count){'failed_own_changes_rolled_back'}else{'failed_concurrent_content_preserved'} }
    } finally {
        $result122.changedPages=@($applied122.ToArray())
        if ($caddyHash122 -and -not$result122.ok) { try { Assert-PagesPlain122 $Caddy;$result122.caddyUnchanged=(Get-FileHash -LiteralPath $Caddy -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $caddyHash122 } catch { $result122.caddyUnchanged=$false } }
        foreach($stage122 in @($pending122.Keys)) { try { if ((Get-PagesHash122 (Read-PagesBytes122 $stage122)) -ceq $pending122[$stage122]) { Remove-Item -LiteralPath $stage122 -ErrorAction Stop } } catch {} }
        if ($null -ne $lease122) { try { $lease122.ReleaseMutex() } finally { $lease122.Dispose() } }
    }
    return [pscustomobject]$result122
}

$receipt122=Invoke-PagesUpdate122 $SourceDirectory 'C:\ProgramData\HeartOfTheRain\public-draft122' 'C:\ProgramData\HeartOfTheRain\services\Caddyfile' ([bool]$Check)
$receipt122|ConvertTo-Json -Depth 8 -Compress
if (-not$receipt122.ok) { exit 1 }
