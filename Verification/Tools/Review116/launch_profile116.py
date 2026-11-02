"""Explicit launch selection: approved LTS no-splash or labelled2022 diagnostic.

This policy is not visual splash evidence. A real process-cold recording and
frame review remain necessary before accepting the final ordinary launch.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[3]
PROFILE = Path(__file__).with_name('ApprovedLtsProfile116.json')
PROFILE_SHA256 = '30f601ccffabeaf63af8d6987d0bf161917a523b7008ec7c9768f6ed501e9495'
PACKAGE = 'com.heartoftherain.review116lts'
CANONICAL_SOURCE_SHA256 = 'b0bc2b91f3a22b9b8bcc6ab230ffa28a7a8f9a8f4972038fd9eeb3c66dfbe28d'


def need(value, code):
    if not value:
        raise ValueError(code)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(data)
    return value.hexdigest()


def approved_profile():
    """Return verified public profile metadata and exact decoded file bytes."""
    need(sha(PROFILE) == PROFILE_SHA256, 'ExactApprovedPublicLtsProfileRequired')
    profile = json.loads(PROFILE.read_text('utf-8'))
    need(profile['profile'] == 'APPROVED_UNPROMOTED_LTS_NOSPLASH116_V1'
         and profile['unity'] == '6000.3.27f1' and profile['noEnginePromotion'] is True
         and profile['debugInternalOnly'] is True and profile['publicOnlyConfiguration'] is True
         and profile['signingPolicy'] == 'internal-debug-only',
         'ApprovedUnpromotedLtsProfileRequired')
    files = {}
    technical = {'Assets/Review98Editor.meta', 'Assets/Review98Editor/TransparentIconForeground98.png',
                 'Assets/Review98Editor/TransparentIconForeground98.png.meta'}
    for name, row in profile['files'].items():
        path = PurePosixPath(name)
        need(not path.is_absolute() and all(part not in ('', '.', '..') for part in path.parts), 'ContainedProfileFileRequired')
        allowed = name.startswith(('Packages/', 'ProjectSettings/')) or name.startswith('Assets/') and name.endswith('.meta') or name in technical
        need(allowed and not name.endswith(('.cs', '.java', '.aar', '.dll', '.exe', '.keystore', '.jks')), 'ProfileCannotContainOldSourceOrPrivateArtifact')
        data = base64.b64decode(row['dataBase64'], validate=True)
        need(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'ProfileDecodedFileHashMismatch')
        files[name] = data
    need(len(files) == profile['fileCount'] and sum(map(len, files.values())) == profile['decodedBytes'], 'ProfileFileCountsMismatch')
    settings = files['ProjectSettings/ProjectSettings.asset']
    need(re.search(rb'(?m)^  m_ShowUnitySplashScreen: 0\r?$', settings)
         and re.search(rb'(?m)^  m_ShowUnitySplashLogo: 0\r?$', settings), 'ProfileSerializedSplashFlagsMustBeFalse')
    need(b'6000.3.27f1' in files['ProjectSettings/ProjectVersion.txt'], 'ProfileEngineMismatch')
    return profile, files


def preparation_profile_binding(preparation):
    profile, files = approved_profile()
    expected = profile['files']
    settings = preparation['approvedLtsSettingsInputs']
    need(settings and all(name in expected and row['sha256'] == expected[name]['sha256']
                          for name, row in settings.items()), 'PreparationSettingsDoNotMatchDurableProfile')
    migrated = preparation['migratedMetaPaths']
    need(all(name in files and preparation['copiedInputs'][name]['sha256'] == expected[name]['sha256']
             for name in migrated), 'PreparationMigratedMetasDoNotMatchDurableProfile')
    technical = [name for name, origin in preparation['provenance'].items()
                 if origin == 'approved98-technical-icon-foreground-only']
    need(all(name in files and preparation['copiedInputs'][name]['sha256'] == expected[name]['sha256']
             for name in technical), 'PreparationTechnicalIconDoesNotMatchDurableProfile')
    return dict(profile=PROFILE.relative_to(ROOT).as_posix(), profileSHA256=PROFILE_SHA256,
                unity=profile['unity'], approvedSettingsFiles=len(settings),
                migratedMetaFiles=len(migrated), technicalIconFiles=len(technical),
                settingsAndMigratedMetaMatch=True, noOldGameplaySourceBundled=True,
                mainEnginePromotion=False)


def profile_policy(native, invocation, diagnostic_branded2022=False):
    """Pure positive/negative launch-selection policy; no process or device I/O."""
    need(native.get('actualBuild') is True and type(native.get('errors')) is int
         and native.get('errors') == 0, 'ActualSuccessfulBuildRequired')
    engine = native.get('unity')
    if engine == '2022.3.62f3':
        need(diagnostic_branded2022 is True, 'Branded2022ProfileIsDiagnosticOnly')
        need(native.get('status') == 'PASS_ANDROID116_Development'
             and invocation.get('status') == 'PASS_ANDROID116_INVOCATION'
             and native.get('development') is True
             and native.get('packageName') in ('com.heartoftherain.review116', 'com.heartoftherain.review116r2'),
             'Owned2022DiagnosticBuildRequired')
        return dict(profile='EXPLICIT_DIAGNOSTIC_BRANDED_2022', engine=engine,
                    packageName=native['packageName'], ordinaryUserVisibleLaunchAllowed=False,
                    diagnosticOnly=True, unityBrandingMayAppear=True)
    need(engine == '6000.3.27f1' and invocation.get('actualEngine') == engine, 'ApprovedLtsLaunchEngineRequired')
    need(native.get('status') == 'PASS_LTS_NOSPLASH116_BUILD'
         and invocation.get('status') == 'PASS_LTS_NOSPLASH116_INVOCATION', 'PassingLtsBuildInvocationRequired')
    need(native.get('packageName') == PACKAGE and native.get('development') is True, 'OwnedLtsTestPackageRequired')
    need(all(native.get(key) is False for key in ('showSplashBefore', 'showLogoBefore', 'showSplashAfter', 'showLogoAfter')),
         'BothActualSplashGettersMustBeFalseBeforeAndAfterBuild')
    need(all(native.get(key) is True for key in ('sourcePinsPreserved', 'metaGuidsPreserved', 'sdkFree'))
         and invocation.get('originalCandidateAssetsAndSourcePreserved') is True
         and invocation.get('originalCandidateGuidsPreserved') is True
         and invocation.get('packageChangedPaths') == [], 'PreservedSdkFreeLtsSourceRequired')
    return dict(profile='USER_VISIBLE_APPROVED_LTS_NOSPLASH116', engine=engine,
                packageName=PACKAGE, ordinaryUserVisibleLaunchAllowed=True,
                diagnosticOnly=False, serializedAndActualBuildSplashDisabled=True,
                actualColdStartFrameReviewStillRequired=True, mainEnginePromotion=False)


def _qualify(build_path, invocation_path=None, diagnostic_branded2022=False):
    """Verify actual build/artifact and profile binding before a launch command."""
    build = Path(build_path).resolve()
    invocation_path = Path(invocation_path).resolve() if invocation_path else build.with_name('Invocation.json')
    need(build.is_relative_to(ROOT / 'Verification/Evidence/Review116') and build.name == 'Build.json'
         and invocation_path.parent == build.parent and invocation_path.name == 'Invocation.json', 'OwnedActualBuildEvidenceRequired')
    need(build.is_file() and invocation_path.is_file() and not build.is_symlink()
         and not invocation_path.is_symlink(), 'ActualBuildAndInvocationProofRequired')
    native = json.loads(build.read_text('utf-8-sig'))
    invocation = json.loads(invocation_path.read_text('utf-8-sig'))
    result = profile_policy(native, invocation, diagnostic_branded2022)
    apk = Path(native['apk']).resolve()
    need(apk.is_relative_to(ROOT / '.verification-cache/Review116') and apk.is_file()
         and native['bytes'] == apk.stat().st_size, 'ExactOwnedLaunchArtifactRequired')
    digest = sha(apk)
    expected = native.get('apkSHA256') or invocation.get('apkSHA256')
    need(digest == expected, 'LaunchArtifactHashMismatch')
    if not result['diagnosticOnly']:
        need(invocation.get('artifact', {}).get('sha256') == digest, 'InvocationArtifactBindingRequired')
        prep_ref = invocation['preparation']
        prep_path = (ROOT / prep_ref['path']).resolve()
        need(prep_path.is_relative_to(ROOT / '.verification-cache/Review116')
             and sha(prep_path) == prep_ref['sha256'], 'BoundPreparedCandidateRequired')
        preparation = json.loads(prep_path.read_text('utf-8-sig'))
        result['durableProfileBinding'] = preparation_profile_binding(preparation)
        source = preparation['canonicalManifest']
        source_path = (ROOT / source['path']).resolve()
        requested_source_sha = preparation.get('requestedCanonicalSHA256', CANONICAL_SOURCE_SHA256)
        need(source_path.is_relative_to(ROOT / 'Verification/Evidence/Review116/App')
             and source_path.name.startswith('NativeSnapshotSourceCut116')
             and re.fullmatch(r'[0-9a-f]{64}', requested_source_sha)
             and source['sha256'] == requested_source_sha
             and sha(source_path) == requested_source_sha, 'ExactCanonicalSourceProvenanceRequired')
        canonical = json.loads(source_path.read_text('utf-8-sig'))['files']
        assets = {name.removeprefix('Unity/'): row for name, row in canonical.items()
                  if name.startswith('Unity/Assets/') and not name.endswith('.meta')}
        need(assets and all(invocation['candidateBefore'].get(name) == row
                            and invocation['candidateAfter'].get(name) == row for name, row in assets.items()),
             'CanonicalRuntimeArtAndSourceBytesRequired')
        expected_guids = dict(zip(preparation['metaPaths'], preparation['metaGuids'], strict=True))
        need(expected_guids and all(invocation['candidateGuidBefore'].get(name) == value
                                   and invocation['candidateGuidAfter'].get(name) == value
                                   for name, value in expected_guids.items()), 'ActualGuidBeforeAfterProvenanceRequired')
        result['canonicalSourceProvenance'] = dict(manifest=source['path'], sha256=requested_source_sha,
            nonMetaAssetAndSourceFiles=len(assets), assetGuidPins=len(expected_guids),
            runtimeAndArtBeforeAfterMatch=True, guardSourcesUnpatched=True)
    result.update(buildReport=dict(path=build.relative_to(ROOT).as_posix(), sha256=sha(build)),
                  invocation=dict(path=invocation_path.relative_to(ROOT).as_posix(), sha256=sha(invocation_path)),
                  apk=dict(path=apk.relative_to(ROOT).as_posix(), sha256=digest, bytes=apk.stat().st_size))
    return result


def qualify(build_path, invocation_path=None, diagnostic_branded2022=False):
    try:
        return _qualify(build_path, invocation_path, diagnostic_branded2022)
    except (KeyError, TypeError, OSError) as error:
        raise ValueError('IncompleteActualBuildProvenance') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--invocation', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--diagnostic-branded2022', action='store_true')
    args = parser.parse_args()
    output = args.out.resolve()
    need(output.is_relative_to(ROOT / 'Verification/Evidence/Review116') and not output.exists(), 'FreshOwnedLaunchQualificationRequired')
    result = qualify(args.build, args.invocation, args.diagnostic_branded2022)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(profile=result['profile'], packageName=result['packageName'], report=output.relative_to(ROOT).as_posix())))


if __name__ == '__main__':
    main()
