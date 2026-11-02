"""Read-only checks of an actual, separately built Review116 Android APK.

No ADB operation. Raw Android-tool output stays in the ignored cache. A passing
static report never substitutes for a current passing build/source invocation.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = 'com.heartoftherain.review116'
APPROVED_CANONICAL_SHA256 = 'eeba5e5c026d7b125f466fd8df518ed0e0ea9375a33a55e2501c8c2df0812002'
ANDROID = Path(r'C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer')
KNOWN115_UI_PATHS = {
    'App/Leaderboard/Runtime/' + name for name in (
        'LeaderboardAssets.cs', 'LeaderboardLayout.cs', 'LeaderboardPage.cs',
        'LeaderboardSession.cs', 'LeaderboardMedals115.cs')
} | {
    'App/OnlineSocial/Runtime/' + name for name in (
        'OnlinePlayersLayout82.cs', 'OnlinePlayersPage82.cs', 'OnlineSocialSurface82.cs',
        'OnlineTeamsPage82.cs',
        'SocialContracts82.cs', 'SocialPageSession82.cs', 'SocialRanksRefresh115.cs',
        'LeaderboardRefresh115.cs', 'LeaderboardMotion115.cs')
} | {'Verification/Editor/' + name for name in (
    'Regional89Verification.cs', 'Regional89ControlledVerification.cs',
    'TeamsDiscovery103Verification.cs', 'LeaderboardRefresh115HttpVerification.cs',
    'LeaderboardRefresh115ProtocolVerification.cs', 'LeaderboardRefresh115Verification.cs')}
KNOWN115_UI_PATHS = {'Unity/Assets/HeartOfTheRain/' + name for name in KNOWN115_UI_PATHS}
KNOWN115_UI_PATHS |= {name + '.meta' for name in tuple(KNOWN115_UI_PATHS)}


def need(value, code):
    if not value:
        raise RuntimeError(code)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def bind(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), 'Review116ArtifactOutsideProject')
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def source_qualification(invocation):
    before, after = invocation.get('candidateBefore', {}), invocation.get('candidateAfter', {})
    frozen = {'Unity/' + name: value for name, value in before.items()
              if not name.startswith('Assets/Review116Editor/') and name not in ('Assets/Review116Editor.meta',)}
    current, read_issues = {}, []
    for part in ('Assets', 'Packages', 'ProjectSettings'):
        for path in (ROOT / 'Unity' / part).rglob('*'):
            if not path.is_file():
                continue
            name = path.relative_to(ROOT).as_posix()
            try:
                current[name] = sha(path)
            except OSError as error:
                read_issues.append(dict(path=name, type=type(error).__name__))
    delta = sorted(name for name in set(frozen) | set(current) if frozen.get(name) != current.get(name))
    stable = bool(before) and before == after and invocation.get('existingCandidateInputsPreserved') is True
    return dict(immutableCandidateInputs=stable, candidateInputCount=len(before), currentMainInputCount=len(current),
        currentMainDifferencePaths=delta, onlyKnown115UiDifferences=all(name in KNOWN115_UI_PATHS for name in delta),
        currentMainReadIssues=read_issues,
        unsupportedDifferencePaths=[name for name in delta if name not in KNOWN115_UI_PATHS],
        scope='Exact candidate before/after bytes preserved. Current main may differ only in individually listed Review115 leaderboard/social UI source/meta files; all other art, engine, levels, profile and gameplay inputs must match.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--immutable-snapshot', action='store_true',
        help='Explicit scoped qualification; never labels a drifted main tree as current passing.')
    parser.add_argument('--canonical-manifest', type=Path)
    parser.add_argument('--canonical-sha256')
    parser.add_argument('--package', choices=('com.heartoftherain.review116', 'com.heartoftherain.review116r2'), default=PACKAGE)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    need(build.is_relative_to(ROOT / 'Verification/Evidence/Review116/Android') and build.name == 'Build.json',
         'ActualReview116BuildReportRequired')
    need(out.is_relative_to(ROOT / 'Verification/Evidence/Review116/Android') and not out.exists(),
         'FreshReview116StaticOutputRequired')
    native, invocation = read(build), read(build.parent / 'Invocation.json')
    development = native.get('development') is True
    expected_package = args.package if development else 'com.heartoftherain.verification'
    need(native.get('status') == 'PASS_ANDROID116_' + ('Development' if development else 'NonDevelopment')
         and native.get('unity') == '2022.3.62f3' and native.get('actualBuild') is True
         and native.get('errors') == 0 and native.get('packageName') == expected_package,
         'PassingActualPinnedBuildRequired')
    apk = Path(native['apk']).resolve()
    need(apk.is_relative_to(ROOT / '.verification-cache/Review116') and apk.is_file()
         and native.get('bytes') == apk.stat().st_size and invocation.get('apkSHA256') == sha(apk),
         'ExactOwnedNativeArtifactRequired')
    spec = importlib.util.spec_from_file_location('review116_apk_primitives',
        ROOT / 'Verification/Tools/Unity6Migration94/check_apk94.py')
    primitive = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(primitive)
    raw = ROOT / '.verification-cache/Review116/Static' / out.name
    need(not raw.exists(), 'PreservePreviousStaticRawOutput')
    raw.mkdir(parents=True)
    out.mkdir(parents=True)
    result = dict(schemaVersion=1, status='FAIL_STATIC_APK116',
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), package=expected_package,
        development=development, apk=bind(apk), nativeBuild=bind(build),
        invocation=bind(build.parent / 'Invocation.json'), runner=bind(Path(__file__)),
        buildInvocationStatus=invocation.get('status'),
        currentPassingBuild=False,
        checks={}, errors=[], scope='Read-only signature, manifest, DEX, ZIP CRC/alignment and ARM64 ELF checks of this exact internal SDK-free artifact. No install, device, provider, release-signer or production approval.')
    main = invocation.get('mainBefore', {}).get('files', {})
    candidate = invocation.get('candidateBefore', {})
    mismatches = [name for name, row in main.items()
        if candidate.get(name.removeprefix('Unity/')) != row.get('sha256')]
    result['candidateSourceBinding'] = dict(mainInputs=len(main), matchesMainAtBuildStart=bool(main) and not mismatches,
        differingMainPaths=mismatches)
    result['currentPassingBuild'] = invocation.get('status') == 'PASS_ANDROID116_INVOCATION' and bool(main) and not mismatches
    result['sourceQualification'] = source_qualification(invocation)
    if args.canonical_manifest is not None:
        canonical = args.canonical_manifest.resolve()
        need(canonical.is_relative_to(ROOT / 'Verification/Evidence/Review116/App') and
             args.canonical_sha256 == APPROVED_CANONICAL_SHA256 and sha(canonical) == args.canonical_sha256,
             'ExactApprovedCanonicalManifestRequired')
        cut = read(canonical).get('files', {})
        expected = {name.removeprefix('Unity/'): row['sha256'] for name, row in cut.items()}
        actual = {name: value for name, value in candidate.items()
            if not name.startswith('Assets/Review116Editor/') and name != 'Assets/Review116Editor.meta'}
        need(expected and expected == actual and invocation.get('candidateMatchesCanonicalBefore') is True
             and invocation.get('canonicalInputsUnchanged') is True
             and invocation.get('canonicalSourceBefore', {}).get('files') == cut
             and invocation.get('canonicalSourceAfter', {}).get('files') == cut,
             'ExactCanonicalSnapshotAndBuildInputEqualityRequired')
        result['canonicalSnapshot'] = dict(manifest=bind(canonical), inputCount=len(cut),
            candidateMatchesApprovedCut=True, canonicalBeforeAfterMatchesApprovedCut=True,
            authorization='User explicitly chose: Commit the tested snapshot and leave newer edits uncommitted.',
            workingTreeDeltasInformational=True,
            scope='Independent hash equality to the user-approved source snapshot for commit; newer working-tree edits are outside this APK.')
    current_differences = result['sourceQualification']['currentMainDifferencePaths']
    if current_differences:
        result['currentPassingBuild'] = False
    result['immutableSnapshotMode'] = args.immutable_snapshot
    result['snapshotAcceptedForSeparateEmulator'] = False
    (out / 'SourceQualification116.json').write_text(json.dumps(result['sourceQualification'], indent=2) + '\n', encoding='utf-8')
    if args.immutable_snapshot:
        need(build.parent.name != 'Development', 'HistoricalDevelopment01NotAuthorizedForInstall')
        need(invocation.get('exitCode') == 0 and invocation.get('native', {}).get('unity') == '2022.3.62f3',
             'ActualPinnedNativeEngineRequiredForSnapshot')
        canonical_pinned = bool(result.get('canonicalSnapshot', {}).get('candidateMatchesApprovedCut'))
        need(result['sourceQualification']['immutableCandidateInputs'] and
             (canonical_pinned or result['sourceQualification']['onlyKnown115UiDifferences']),
             'ImmutableApprovedSnapshotOrKnownUiOnlyDriftRequired')
        result['snapshotAcceptedForSeparateEmulator'] = True
        result['qualification'] = 'USER_APPROVED_CANONICAL_SNAPSHOT' if canonical_pinned else 'IMMUTABLE_SNAPSHOT_KNOWN115_UI_DRIFT'
        if canonical_pinned:
            result['currentPassingBuild'] = False
        result['scope'] += ' Explicit immutable snapshot mode: current Review115 UI differences are untested by this APK. CurrentPassingBuild remains false when source drift exists.'
    unity_logs = [ROOT / row['path'] for row in invocation.get('rawLogs', [])
                  if Path(row['path']).name == 'Unity.log' and (ROOT / row['path']).is_file()
                  and sha(ROOT / row['path']) == row.get('sha256')]
    need(len(unity_logs) == 1 and re.search(r'(?m)^Initialize engine version: 2022\.3\.62f3\b',
         unity_logs[0].read_text('utf-8-sig', errors='strict')), 'BoundActualPinnedEditorLogRequired')
    result['nativeEngineProof'] = bind(unity_logs[0])
    tools = ANDROID / 'SDK/build-tools/34.0.0'

    def command(name, args):
        with (raw / (name + '.out')).open('xb') as stdout, (raw / (name + '.err')).open('xb') as stderr:
            process = subprocess.run([str(x) for x in args], stdout=stdout, stderr=stderr,
                timeout=240, creationflags=subprocess.CREATE_NO_WINDOW)
        need(process.returncode == 0, 'AndroidStaticToolFailed' + name)
        return (raw / (name + '.out')).read_text('utf-8', errors='strict')

    try:
        signature = command('Signature', [ANDROID / 'OpenJDK/bin/java.exe', '-jar',
            tools / 'lib/apksigner.jar', 'verify', '--verbose', '--print-certs', apk])
        result['checks']['actualSignatureVerifies'] = True
        cert = re.search(r'(?m)^Signer #1 certificate SHA-256 digest: ([0-9a-fA-F]{64})\s*$', signature)
        need(cert is not None and 'CN=Android Debug' in signature, 'ExpectedInternalDebugSignerRequired')
        result['publicCertificateSha256'] = cert.group(1).lower()
        result['checks']['internalDebugSigner'] = True
        command('Zipalign', [tools / 'zipalign.exe', '-c', '-v', '4', apk])
        result['checks']['zipalignFourByteCheck'] = True
        badging = command('Badging', [tools / 'aapt.exe', 'dump', 'badging', apk])
        manifest = command('Manifest', [tools / 'aapt.exe', 'dump', 'xmltree', apk, 'AndroidManifest.xml'])
        need("package: name='" + expected_package + "'" in badging and "versionCode='116'" in badging,
             'IsolatedPackageAndVersionRequired')
        need("application-label:'Сердце дождя'" in badging, 'ApprovedVisibleRussianNameRequired')
        need(("application-debuggable" in badging) is development, 'ActualDevelopmentModeMismatch')
        minimum = re.search(r"(?m)^sdkVersion:'([0-9]+)'$", badging)
        target = re.search(r"(?m)^targetSdkVersion:'([0-9]+)'$", badging)
        need(minimum is not None and int(minimum[1]) == 22 and target is not None and int(target[1]) >= 22,
             'MainPinnedApiBaselineRequired')
        need("native-code: 'arm64-v8a'" in badging, 'Arm64OnlyRequired')
        result['manifest'] = dict(minApi=int(minimum[1]), targetApi=int(target[1]),
            abi=['arm64-v8a'], versionCode=116)
        result['checks']['packageLabelVersionApiAndBuildMode'] = True
        nodes = primitive.parse_manifest(manifest)
        player = [node for node in nodes if node['tag'] == 'activity'
            and primitive.attribute_value(node['attributes'].get('android:name')) == 'com.unity3d.player.UnityPlayerActivity']
        need(len(player) == 1 and primitive.attribute_value(player[0]['attributes'].get('android:screenOrientation')) in (1, 'portrait'),
             'PortraitUnityPlayerActivityRequired')
        need("launchable-activity: name='com.unity3d.player.UnityPlayerActivity'" in badging,
             'ExpectedLaunchableActivityRequired')
        need(not any(x in manifest for x in ('RuStorePayContentProvider', 'heartoftherain-pay',
            'com.yandex.mobile.ads', 'io.appmetrica')), 'UnexpectedProviderManifest')
        result['checks'].update(portraitActivity=True, sdkFreeManifest=True)
        result['zip'] = primitive.zip_profile(apk)
        result['checks'].update(zipCrcAndNoDuplicateEntries=True, arm64ElfAnd16KiBAlignment=True,
            identityJavaBridgeInDex=True, sdkFreeDex=True)
        with zipfile.ZipFile(apk) as archive:
            metadata_names = [name for name in archive.namelist() if name.endswith('/Metadata/global-metadata.dat')]
            need(len(metadata_names) == 1, 'SingleIl2CppMetadataRequired')
            metadata = archive.read(metadata_names[0])
            need((b'PlayerRegressionSuite\0' in metadata) is development, 'DevelopmentRegressionCompilationGuardMismatch')
            result['checks']['developmentRegressionCompiledOnlyInDevelopment'] = True
        need(sha(apk) == result['apk']['sha256'], 'ApkChangedDuringChecks')
        result['checks']['artifactUnchanged'] = True
        result['status'] = 'PASS_STATIC_APK116'
    except Exception as error:
        code = str(error)
        result['errors'].append(dict(type=type(error).__name__,
            code=code if re.fullmatch('[A-Za-z0-9]{1,100}', code) else 'PrivateStaticOutputRequired'))
    (out / 'StaticApk116.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], checks=len(result['checks']),
        currentPassingBuild=result['currentPassingBuild'], report=(out / 'StaticApk116.json').relative_to(ROOT).as_posix())))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
