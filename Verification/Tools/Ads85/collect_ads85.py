"""Read-only checkpoint85 validator; --publish explicitly writes its gallery.

Selected suite passes are not an overall PASS for the earlier failed invocation.
No Unity, service, SDK, ADB, installation, payment or advertising request is run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[3]
DEFAULT = ROOT / 'Verification/Evidence/ShopAds85'
CORE = '9b92deb5835b4a6fbe2fba4602cac2d2'
UI = 'ec3e507dd06148629d7e9cefdcf533b5'
BUILD = 'eb97d86f265544508d772b56bbb7b729'
PINNED = '2022.3.62f3'
STATUS = 'PASS_TARGETED_SHOP_RUB_REWARDED_ADS85_WITH_RELEASE_GATES'
NATIVE = {
    'Journal': ('RewardedAdsJournal85.json', 'PASS_NATIVE_REWARDED_ADS_JOURNAL85', 96, False),
    'Parser': ('RewardedAdsParser85.json', 'PASS_NATIVE_REWARDED_ADS85_PARSER', 87, False),
    'Http': ('RewardedAds85_HTTP.json', 'PASS_NATIVE_REWARDED_ADS85_HTTP', 31, False),
    'Flow': ('RewardedAdsFlow85.json', 'PASS_NATIVE_REWARDED_ADS_FLOW85', 64, False),
    'Rubles': ('ShopRuble85.json', 'PASS_NATIVE_SHOP_RUBLE85_PREVIEW', 2212, True),
    'Ui': ('RewardedAdsUi85.json', 'PASS_NATIVE_REWARDED_ADS85_UI', 676, True),
}
CORE_FIXTURES = {
    'Unity/Assets/HeartOfTheRain/Verification/Editor/ShopRuble85Verification.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/RewardedAdsUi85Verification.cs',
}
REVIEWED = {
    'Native/ShopRuble85/Shop_Coins_Russian_Phone.png',
    'Native/ShopRuble85/Coin100000_ru_320x480.png',
    'Native/ShopRuble85/Coin100000_ru_768x1024.png',
    'Native/ShopRuble85/NoMoves_StoreUnavailable_Russian_Phone.png',
    'Native/RewardedAdsUi85/Unavailable_Russian_393x852.png',
    'Native/RewardedAdsUi85/ConsentLayoutFixture_Russian_320x480.png',
    'Native/RewardedAdsUi85/ConsentLayoutFixture_Russian_768x1024.png',
}


def require(value, code):
    if not value:
        raise RuntimeError(code)


def disk(path):
    value = str(Path(path).resolve())
    return '\\\\?\\' + value if os.name == 'nt' and not value.startswith('\\\\?\\') else value


def sha(path):
    digest = hashlib.sha256()
    with open(disk(path), 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def when(value):
    require(isinstance(value, str), 'MissingTimestamp')
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DuplicateEvidenceKey')
            result[key] = value
        return result
    with open(disk(path), encoding='utf-8-sig') as stream:
        return json.load(stream, object_pairs_hook=pairs,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError('NonFiniteEvidenceNumber')))


class Evidence:
    def __init__(self, out):
        self.out = Path(out).resolve()
        self.local, self.external = {}, {}

    def path(self, relative):
        path = (self.out / relative).resolve()
        require(path.is_relative_to(self.out), 'EvidencePathOutsideRoot')
        return path

    def bind(self, path, expected=None):
        path = Path(path).resolve()
        require(path.is_file(), 'RequiredEvidenceFileMissing')
        digest = sha(path)
        require(expected is None or digest == expected, 'EvidenceDigestMismatch')
        if path.is_relative_to(self.out):
            self.local[path.relative_to(self.out).as_posix()] = digest
        else:
            require(path.is_relative_to(ROOT), 'ExternalBindingOutsideWorkspace')
            self.external[path.relative_to(ROOT).as_posix()] = digest
        return digest

    def read(self, relative):
        path = self.path(relative)
        self.bind(path)
        return strict_json(path)

    def source(self, relative, expected):
        path = (ROOT / relative).resolve()
        require(path.is_relative_to(ROOT), 'SourceBindingOutsideWorkspace')
        return self.bind(path, expected)


def source_map(document):
    require(document.get('schemaVersion') == 1 and document.get('inputCount') == len(document.get('files', {})), 'InvalidFrozenSourceManifest')
    files = document['files']
    require(files and all(name.startswith(('Unity/Assets/', 'Unity/Packages/', 'Unity/ProjectSettings/')) for name in files), 'UnexpectedUnityInputScope')
    for record in files.values():
        require(set(record) == {'sha256', 'bytes'} and re.fullmatch('[0-9a-f]{64}', record['sha256'])
                and type(record['bytes']) is int and record['bytes'] >= 0, 'InvalidFrozenSourceRecord')
    return files


def current_inputs():
    files = {}
    for category in ('Assets', 'Packages', 'ProjectSettings'):
        base = ROOT / 'Unity' / category
        for folder, _, names in os.walk(disk(base)):
            for name in names:
                path = Path(str(Path(folder) / name).removeprefix('\\\\?\\'))
                files[path.relative_to(ROOT).as_posix()] = {'sha256': sha(path), 'bytes': os.stat(disk(path)).st_size}
    return files


def invocation(e, run_id):
    require(re.fullmatch('[0-9a-f]{32}', run_id) is not None, 'InvalidNativeRunId')
    base = 'Runs/' + run_id
    record = e.read(base + '/Invocation.json')
    frozen = e.read(base + '/FrozenSources.json')
    final = e.read(base + '/Sources_final.json')
    require(record['runId'] == run_id and record['unityVersion'] == PINNED and record['inputCount'] == frozen['inputCount'], 'NativeInvocationIdentityMismatch')
    require(record['sourceSHA256'] == sha(e.path(base + '/FrozenSources.json'))
            and record['sourcesFinalSHA256'] == sha(e.path(base + '/Sources_final.json')), 'NativeInvocationSourceBindingMismatch')
    require(source_map(frozen) == source_map(final) and record['inputsUnchanged'] is True
            and record['unityPidsAfter'] == [] and record['servicesLaunchedByRunner'] is False, 'NativeInvocationFinalGuardFailed')
    e.source('Verification/Tools/Ads85/run_ads85_native.py', record['runnerSHA256'])
    require(when(record['startedUtc']) < when(record['finishedUtc']), 'NativeInvocationChronologyInvalid')
    return record, frozen


def suite(e, run_id, inv, frozen, name, passed=True):
    filename, status, checks, play = NATIVE[name]
    prefix = 'Runs/' + run_id
    selected = [row for row in inv['runs'] if row['suite'] == name]
    require(len(selected) == 1, 'SelectedNativeSuiteMissingOrDuplicated')
    row = selected[0]
    process = e.read(prefix + '/Suites/' + name + '/Process.json')
    report = e.read(prefix + '/Native/' + filename)
    require(row == process, 'InvocationProcessRecordMismatch')
    require(type(row.get('pid')) is int and row['pid'] > 0 and row['processStopped'] is True
            and row['ownedKillOnCloseJobAssigned'] is True and row['timedOut'] is False
            and row['playMode'] is play and row['quitFlag'] is False, 'NativeActualProcessGuardFailed')
    require(when(inv['startedUtc']) <= when(row['startedUtc']) <= when(report['utc']) <= when(row['finishedUtc']) <= when(inv['finishedUtc']), 'NativeSuiteChronologyInvalid')
    require(row['reportSHA256'] == sha(e.path(prefix + '/Native/' + filename)), 'NativeReportDigestMismatch')
    e.bind(e.path(prefix + '/Suites/' + name + '/Unity.log'), row['unityLogSHA256'])
    e.bind(e.path(prefix + '/Suites/' + name + '/Console.log'), row['consoleSHA256'])
    before = e.read(prefix + '/Suites/' + name + '/Sources_before.json')
    after = e.read(prefix + '/Suites/' + name + '/Sources_after.json')
    delta = e.read(prefix + '/Suites/' + name + '/Source_Delta.json')
    require(source_map(before) == source_map(frozen) == source_map(after)
            and delta == {'added': [], 'removed': [], 'changed': []} and row['inputsUnchanged'] is True, 'NativeSuiteInputDrift')
    require(row['sourcesBeforeSHA256'] == sha(e.path(prefix + '/Suites/' + name + '/Sources_before.json'))
            and row['sourcesAfterSHA256'] == sha(e.path(prefix + '/Suites/' + name + '/Sources_after.json'))
            and row['sourceDeltaSHA256'] == sha(e.path(prefix + '/Suites/' + name + '/Source_Delta.json')), 'NativeSuiteManifestBindingMismatch')
    require(report['unity'] == PINNED, 'NativeEditorPinMismatch')
    captures = report.get('captures', [])
    require(isinstance(captures, list) and len(captures) == len(set(captures))
            and set(captures) == set(row['captures']), 'NativeCaptureManifestMismatch')
    for path in captures:
        e.bind(e.path(prefix + '/' + path), row['captures'][path])
        with open(disk(e.path(prefix + '/' + path)), 'rb') as image:
            header = image.read(24)
        require(len(header) == 24 and header[:8] == b'\x89PNG\r\n\x1a\n'
                and all(1 <= dimension <= 16384 for dimension in struct.unpack('>II', header[16:24])), 'NativeCaptureIsNotBoundedPng')
    if passed:
        require(row['status'] == 'PASS' and row['exitCode'] == 0 and row['nativeErrorsEmpty'] is True
                and report['status'] == row['nativeStatus'] == status and report.get('errors') == []
                and report['checks'] == checks, 'SelectedNativeSuiteNotPassed')
    else:
        require(row['status'] != 'PASS' and row['exitCode'] != 0 and report.get('errors'), 'PreservedFailureWasNotActuallyFailed')
    return {'suite': name, 'runId': run_id, 'processId': row['pid'], 'report': prefix + '/Native/' + filename,
            'checks': report['checks'], 'scope': report['scope'], 'status': report['status'],
            'captures': [prefix + '/' + path for path in captures]}, report


def backend(e):
    value = e.read('Backend/Service_Tests.json')
    require(value['status'] == 'PASS_BACKEND_SERVICE_TESTS' and value['tests'] == value['executedTests'] == 357
            and value['skipped'] == [] and value['actualPinnedWorkerIntegration'] is True
            and all(value[key] == [] for key in ('failures', 'errors', 'failureLocations', 'sourceInputsChangedDuringRun')), 'BackendActualSuiteNotPassed')
    require(when(value['startedUtc']) < when(value['utc']) and len(value['passed']) == len(set(value['passed'])) == 357
            and 'tests.test_replay_native_integration.NativeReplayBrokerIntegration.test_authenticated_native_full_history_continue_win_recovery' in value['passed'], 'BackendWorkerOrChronologyProofMissing')
    sources = value['sourceSHA256']
    require(len(sources) == 79 and sources == value['sourceSHA256After'], 'BackendSourceRunBindingFailed')
    archive = e.path('Backend/Inputs')
    archived = {p.relative_to(archive).as_posix() for p in archive.rglob('*') if p.is_file()}
    require(archived == set(sources), 'BackendCopiedInputSetMismatch')
    documentation = []
    for name, digest in sources.items():
        require(name.startswith('Backend/'), 'BackendInputOutsideScope')
        e.bind(e.path('Backend/Inputs/' + name), digest)
        current = sha(ROOT / name)
        if current != digest:
            require(name == 'Backend/README.md', 'BackendExecutableConfigOrTestDrift')
            documentation.append({'path': name, 'testedSHA256': digest, 'currentSHA256': current, 'scope': 'Documentation-only update after tests; not retested executable bytes'})
        e.bind(ROOT / name)
    # Reject newly added executable/config/test files after the authoritative run.
    actual = set()
    for category in ('hotr_backend', 'tests', 'tools', 'config'):
        actual.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'Backend' / category).rglob('*') if p.is_file() and p.suffix in ('.py', '.json'))
    actual.update('Backend/' + name for name in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1'))
    require(actual == set(sources), 'UntestedBackendExecutableOrConfigurationAdded')
    config = strict_json(ROOT / 'Backend/config/ads.json')
    require(config['enabled'] is False and config['completionMode'] == 'sdk_client_reported_capped'
            and (config['rewardCoins'], config['dailyLimit'], config['utcOffsetSeconds'], config['cooldownSeconds']) == (400, 3, 36000, 600), 'ApprovedAdPolicyOrDefaultGateChanged')
    return {'tests': 357, 'skipped': 0, 'actualPinnedWorkerIntegration': True, 'archivedInputCount': 79,
            'scope': value['scope'], 'documentationOnlyDrift': documentation}


def internal_builds(e, run_id, current):
    require(re.fullmatch('[0-9a-f]{32}', run_id) is not None, 'InvalidBuildRunId')
    base = 'Builds/' + run_id
    value = e.read(base + '/Invocation.json')
    require(value['status'] == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85' and value['runId'] == run_id
            and value['inputCount'] == len(current) and value['allHistoricalNativeRestored'] is True
            and all(value['historicalNativeRestored'].values()) and value['inputsUnchangedAfterSettingsRestore'] is True
            and value['unityPidsAfter'] == [] and value['apkInstalledOrLaunched'] is False and value['servicesStarted'] is False, 'BothFreshInternalBuildsRequired')
    frozen = e.read(base + '/FrozenSources.json'); final = e.read(base + '/Sources_final.json')
    require(source_map(frozen) == source_map(final) == current
            and value['sourceSHA256'] == sha(e.path(base + '/FrozenSources.json'))
            and value['sourcesFinalSHA256'] == sha(e.path(base + '/Sources_final.json')), 'BuildCurrentSourceBindingMismatch')
    e.source('Verification/Tools/Ads85/run_ads85_internal_build.py', value['runnerSHA256'])
    e.source('Verification/Tools/Ads85/run_ads85_native.py', value['sharedNativeRunnerSHA256'])
    require([row['build'] for row in value['runs']] == ['Development', 'NonDevelopment'], 'BothBuildVariantsMissing')
    builds = []
    for row in value['runs']:
        label = row['build']; prefix = base + '/' + label
        process = e.read(prefix + '/Process.json')
        require(process == row, 'BuildInvocationProcessMismatch')
        require(row['status'] == 'PASS_INTERNAL_BUILD85' and type(row.get('pid')) is int and row['pid'] > 0
                and row['exitCode'] == 0 and row['timedOut'] is False and row['processStopped'] is True
                and row['ownedKillOnCloseJobAssigned'] is True and row['exactSettingsRestored'] is True
                and row['inputsUnchangedAfterRestoration'] is True, 'BuildActualProcessGuardFailed')
        filename = 'Android_Build.json' if label == 'Development' else 'Android_Release_Build.json'
        native = e.read(prefix + '/' + filename)
        require(native['status'] == ('PASS_ANDROID_DEVELOPMENT_BUILD' if label == 'Development' else 'PASS_ANDROID_RELEASE_COMPILE_BUILD')
                and native['unity'] == PINNED and native['errors'] == 0 and not native.get('error'), 'NativeBuildReportNotPassed')
        require(row['nativeReportSHA256'] == sha(e.path(prefix + '/' + filename))
                and when(value['startedUtc']) <= when(row['startedUtc']) <= when(native['utc']) <= when(row['finishedUtc']) <= when(value['finishedUtc']), 'BuildReportDigestOrChronologyMismatch')
        e.bind(e.path(prefix + '/Unity.log'), row['unityLogSHA256']); e.bind(e.path(prefix + '/Console.log'), row['consoleSHA256'])
        require(source_map(e.read(prefix + '/Sources_before.json')) == source_map(e.read(prefix + '/Sources_after_restore.json')) == current
                and e.read(prefix + '/Source_Delta.json') == {'added': [], 'removed': [], 'changed': []}, 'BuildSourceRestorationMismatch')
        apk = row['apk']; path = ROOT / apk['path']; e.bind(path, apk['sha256'])
        require(path.stat().st_size == apk['bytes'] > 0 and Path(native['output']).resolve() == path.resolve(), 'BuildArtifactIdentityMismatch')
        # Unity BuildSummary.totalSize can include intermediates/symbols; do not
        # equate it with APK length. The fresh owned-process output is hashed.
        require(native['bytes'] > 0, 'MissingUnityReportedTotalBytes')
        with zipfile.ZipFile(disk(path)) as package:
            require(package.testzip() is None, 'InternalApkCrcFailure')
            names = set(package.namelist())
            require({'AndroidManifest.xml', 'lib/arm64-v8a/libil2cpp.so', 'lib/arm64-v8a/libunity.so'} <= names
                    and not any(name.startswith(('lib/armeabi-v7a/', 'lib/x86/', 'lib/x86_64/')) for name in names), 'InternalApkArm64Il2CppShapeMismatch')
        proof = row['sdkFreeInputProof']
        require(all(proof[key] is True for key in ('vendorTreeAbsent', 'matchingVendorBinariesAbsent', 'providerSdkDefineAbsent')), 'OrdinaryBuildSdkDormancyNotProven')
        builds.append({'variant': label, 'processId': row['pid'], 'apk': apk,
                       'unityReportedTotalBytes': native['bytes'], 'zipCRC': 'PASS', 'scope': native['scope']})
    return {'runId': run_id, 'status': value['status'], 'variants': builds, 'installedOrLaunched': False, 'scope': value['scope']}


def sdk(e):
    audit = e.read('SDK/Provider_Privacy_Audit.json')
    require(audit['status'] == 'REVIEWED_STATIC_YANDEX85_PRIVACY_WITH_RUNTIME_GATES'
            and audit['apkLaunched'] is False and audit['runtimeNetworkObserved'] is False
            and audit['realAdImpressionVerified'] is False and audit['checkCount'] == len(audit['checks']) >= 28
            and all(row['passed'] is True for row in audit['checks']) and audit['remainingGates'], 'SdkStaticAuditInvalid')
    for name, digest in audit['artifactSHA256'].items():
        e.bind(e.path('SDK/' + name), digest)
    for name, digest in audit['externalEvidenceSHA256'].items():
        e.source(name, digest)
    current = 'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/YandexRewardedAdsProvider85.cs'
    require(audit['compiledProviderSHA256'] == audit['currentProviderSHA256'] == sha(ROOT / current), 'SdkCompiledProviderSourceStale')
    assembly = strict_json(ROOT / audit['assembly_report'])
    require(assembly['status'] == 'PASS_ROOT_ISOLATED_YANDEX85_BUILD_PHASE' and assembly['apkLaunched'] is False
            and assembly['mainSettingsUnchanged'] is True and assembly['apk']['sha256'] == audit['apk_sha256']
            and all(row['exitCode'] == 0 and type(row['pid']) is int and row['pid'] > 0 for row in assembly['steps']), 'ActualSdkAssemblyProofMissing')
    path = ROOT / audit['apk_path']; e.bind(path, audit['apk_sha256'])
    require(path.stat().st_size == audit['apk_bytes'], 'SdkApkSizeMismatch')
    return {'status': audit['status'], 'apkSHA256': audit['apk_sha256'], 'apkBytes': audit['apk_bytes'],
            'staticChecks': audit['checkCount'], 'scope': audit['scope'], 'remainingGates': audit['remainingGates'],
            'ordinaryFullGameSdk': False, 'apkLaunched': False}


def static_apks(e, builds):
    value = e.read('Android/APK_Profile.json')
    require(value['status'] == 'PASS_ADS85_SDK_FREE_INTERNAL_APKS_STATIC' and len(value['artifacts']) == 2, 'ActualInternalApkStaticProofMissing')
    expected = {row['apk']['path']: row['apk'] for row in builds['variants']}
    require({row['path'] for row in value['artifacts']} == set(expected), 'ApkStaticProfileVariantMismatch')
    for row in value['artifacts']:
        target = expected[row['path']]
        require(row['sha256'] == target['sha256'] and row['bytes'] == target['bytes']
                and row['package'] == 'com.heartoftherain.verification'
                and row['nativePaymentAndAdvertisingSdkAbsent'] is True and row['deviceIdentityClassPresent'] is True, 'ApkStaticProfileIdentityMismatch')
        artifact = e.read('Android/' + row['staticArtifactReport'])
        require(artifact['sha256'] == row['sha256'] and artifact['bytes'] == row['bytes']
                and Path(artifact['path']).resolve() == (ROOT / row['path']).resolve()
                and artifact['zipalign4KiBPass'] is True and artifact['developmentSignatureVerifies'] is True
                and artifact['elf16KiBLoadSegmentsPass'] is True, 'ApkActualSignatureAlignmentReportInvalid')
        folder = Path(row['staticArtifactReport']).parent.as_posix()
        badging = e.path('Android/' + folder + '/Badging.txt')
        manifest = e.path('Android/' + folder + '/Manifest.txt')
        e.bind(badging); e.bind(manifest)
        text = badging.read_text('utf-8-sig')
        require("package: name='com.heartoftherain.verification'" in text, 'ActualApkBadgingPackageMismatch')
        xml = manifest.read_text('utf-8-sig')
        require(not any(name in xml for name in ('YandexAdsInitializeProvider', 'AppMetricaService', 'RuStorePayContentProvider')), 'NativeSdkInitializerInOrdinaryApk')
        with zipfile.ZipFile(disk(ROOT / row['path'])) as package:
            dex_names = [name for name in package.namelist() if re.fullmatch(r'classes[0-9]*\.dex', name)]
            require(dex_names, 'InternalApkDexMissing')
            for name in dex_names:
                data = package.read(name)
                require(not any(prefix in data for prefix in (b'Lcom/yandex/mobile/ads/', b'Lio/appmetrica/', b'Lru/rustore/sdk/')), 'NativeStoreOrAdSdkDexInOrdinaryApk')
    return value


def preserved_failures(e):
    rows = []
    for folder in sorted(e.path('Runs').iterdir()):
        if not (folder / 'Invocation.json').is_file():
            continue
        value = e.read('Runs/' + folder.name + '/Invocation.json')
        if not value['status'].startswith('FAIL_'):
            continue
        # Keep each original report/process/log/source snapshot verbatim. No
        # failed suite is counted as a pass or silently erased by later runs.
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                e.bind(path)
        rows.append({'runId': folder.name, 'status': value['status'],
                     'failedSuites': [{'suite': row['suite'], 'status': row['status'], 'exitCode': row.get('exitCode')} for row in value.get('runs', []) if row['status'] != 'PASS']})
    for folder in sorted(e.path('Builds').iterdir()):
        path = folder / 'Invocation.json'
        if path.is_file():
            value = strict_json(path)
            if value['status'].startswith('FAIL_'):
                for child in folder.rglob('*'):
                    if child.is_file():
                        e.bind(child)
                rows.append({'buildRunId': folder.name, 'status': value['status'], 'scope': 'Preserved failure; no accepted build from this invocation'})
    require(any(row.get('runId') == CORE for row in rows), 'EarlierFailedNativeInvocationWasNotPreserved')
    return rows


def build(out=DEFAULT, core_run=CORE, ui_run=UI, build_run=BUILD):
    e = Evidence(out)
    core, core_sources = invocation(e, core_run)
    ui, ui_sources = invocation(e, ui_run)
    require(core['status'] == 'FAIL_TARGETED_NATIVE_SHOP_ADS85' and ui['status'] == 'PASS_TARGETED_NATIVE_SHOP_ADS85', 'SelectedInvocationScopeMismatch')
    older, final = source_map(core_sources), source_map(ui_sources)
    require(set(older) == set(final), 'CoreUiInputSetMismatch')
    changed = {name for name in older if older[name] != final[name]}
    require(changed and changed <= CORE_FIXTURES, 'CoreCurrentRuntimeOrNonfixtureDrift')
    current = current_inputs()
    require(current == final, 'MainUnityInputsDifferFromVerifiedUiFreeze')
    suites, reports, captures = [], {}, []
    for name in ('Journal', 'Parser', 'Http', 'Flow', 'Rubles', 'Ui'):
        inv, frozen, selected = (core, core_sources, core_run) if name in ('Journal', 'Parser', 'Http', 'Flow') else (ui, ui_sources, ui_run)
        row, report = suite(e, selected, inv, frozen, name)
        suites.append(row); reports[name] = report; captures.extend(row['captures'])
    suite(e, core_run, core, core_sources, 'Rubles', False)
    require(reports['Journal']['credentialsAbsent'] and reports['Journal']['ownerBound'] and reports['Journal']['completionDurable'], 'JournalProofMissing')
    require((reports['Parser']['positiveCases'], reports['Parser']['negativeCases']) == (12, 39), 'ParserControlsIncomplete')
    require(reports['Http']['actualHttp'] is True and reports['Http']['signedIdentityCalls'] == 4 and reports['Http']['walletReads'] == 4
            and reports['Http']['creditedCoins'] == 400 and reports['Http']['creditedGrants'] == 1
            and reports['Http']['ordinaryProfilesBefore'] == reports['Http']['ordinaryProfilesAfter']
            and reports['Http']['ordinaryProfilesUnchanged'] and reports['Http']['languagePreferenceUnchanged']
            and not reports['Http']['localProfileMutated'] and not reports['Http']['realAdImpressionVerified'], 'ActualAdHttpScopeOrWalletProofInvalid')
    require(reports['Flow']['cases'] == 16 and reports['Flow']['scriptedApi'] and reports['Flow']['scriptedProvider'] and reports['Flow']['actualDiskJournal'], 'FlowScriptedScopeMissing')
    require((reports['Rubles']['layoutCases'], reports['Rubles']['detailCases'], reports['Rubles']['coinMappings'], reports['Rubles']['bundlePricesRemoved']) == (15, 180, 6, 6)
            and all(reports['Rubles'][key] is True for key in ('previewOnly', 'checkoutUnavailable', 'noMovesCheckoutDisabled', 'previewHomeUnchanged', 'languagePreferenceUnchanged'))
            and reports['Ui']['cases'] == 15 and len(captures) == len(set(captures)) == 13, 'UiPriceOrCaptureCoverageIncomplete')
    review = e.read('Visual_Review.json')
    require(review['status'] == 'REVIEWED_NATIVE_SHOP_ADS85_TARGETED' and review['sourceSHA256'] == ui['sourceSHA256']
            and review.get('scope') and review.get('findings'), 'ActualRootVisualReviewMissing')
    inspected = {'Runs/' + ui_run + '/' + path for path in REVIEWED}
    require(set(review['inspectedArtifactSHA256']) == inspected and inspected <= set(captures), 'RootReviewScopeDoesNotMatchSevenInspectedImages')
    for name, digest in review['inspectedArtifactSHA256'].items():
        e.bind(e.path(name), digest)
    correction = e.read('Editor_Fixture_Isolation_Correction.json')
    require(correction['status'] == 'RESTORED_ORIGINAL_ABSENT_EDITOR_PROFILES' and correction['profilesAbsent'] is True
            and correction['quarantinedInIgnoredCache'] is True and correction['deviceMutated'] is False
            and correction['baselineHash'] == reports['Http']['ordinaryProfilesBefore'], 'PreservedEditorFixtureIsolationCorrectionMissing')
    result_backend = backend(e)
    result_build = internal_builds(e, build_run, current)
    result_apks = static_apks(e, result_build)
    result_sdk = sdk(e)
    history = preserved_failures(e)
    e.bind(ROOT / 'Release/Advertising/README.md'); e.bind(ROOT / 'Release/Advertising/advertising.example.json')
    e.bind(ROOT / 'Release/RuStore/pricing.proposal.json'); e.bind(Path(__file__))
    remaining = [
        'No advertising publisher/ad-block registration, actual SDK video/no-fill/cancel/background/return, impression, revenue or provider-authenticated completion is certified.',
        'The capped SDK-client report is forgeable by a modified client: fixed400 coins, three credits per UTC+10 day and600-second cooldown are authoritative; impression completion is not.',
        'Default rollout is disabled. Factual privacy/operator/audience settings, account/payout configuration and hosted service activation remain owner steps in Release/Advertising/README.md.',
        'RUB values are approved launch-proposal previews; real checkout must use the actual store SDK product quotation. Neither purchases nor live coin prices are activated by these captures.',
        'Both ordinary internal Android builds are SDK-free compile/ZIP evidence, not installation, touch, real advertising, store signing or production/payment acceptance.',
        'The separate SDK APK proves static compilation/assembly/privacy footprint only. Native AppMetrica/identifier/referrer components remain; zero pre-consent traffic and complete vendor/device compatibility are unproven.',
        'Only seven of13 current PNGs have the root-authored direct visual review. The other six are bound native captures without a copied approval verdict.',
    ]
    return {'status': STATUS, 'utc': datetime.now(timezone.utc).isoformat(), 'source_checkpoint': 85,
            'sourceSHA256': ui['sourceSHA256'], 'unityInputCount': len(current), 'unityVersion': PINNED,
            'scope': 'Targeted RUB preview and optional Shop rewarded-ad foundation. Backend, native parser/journal/scripted flow, actual managed HTTP and selected UGUI evidence are separate scopes. No device installation, real advertising revenue, live purchases or production readiness.',
            'approvedPolicy': {'placement': 'shop_rewarded', 'coins': 400, 'maxCreditsPerDay': 3, 'utcOffsetSeconds': 36000, 'cooldownSeconds': 600, 'completionMode': 'sdk_client_reported_capped', 'defaultEnabled': False},
            'selectedCoreInvocationStatus': core['status'], 'selectedUiInvocationStatus': ui['status'],
            'coreToUiFixtureOnlyChanges': sorted(changed), 'backend': result_backend,
            'native': {'suites': suites, 'checks': sum(row['checks'] for row in suites), 'capturedPngs': captures, 'rootInspectedPngs': sorted(inspected)},
            'internalBuilds': result_build, 'internalApkStatic': result_apks, 'isolatedSdkFixture': result_sdk, 'preservedFailures': history,
            'editorFixtureCorrection': correction['status'], 'ownerSteps': 'Release/Advertising/README.md',
            'remainingGates': remaining, 'artifactSHA256': dict(sorted(e.local.items())), 'externalEvidenceSHA256': dict(sorted(e.external.items()))}


def gallery(value):
    escape = html.escape
    reviewed = set(value['native']['rootInspectedPngs'])
    cards = []
    for path in value['native']['capturedPngs']:
        label = Path(path).name.replace('_', ' ')
        verdict = 'Directly inspected by root' if path in reviewed else 'Bound native capture; no direct-review verdict'
        cards.append('<figure><a href="' + escape(path, quote=True) + '"><img loading="lazy" src="' + escape(path, quote=True) + '" alt="' + escape(label, quote=True) + '"></a><figcaption>' + escape(label) + '<br><small>' + verdict + '</small></figcaption></figure>')
    rows = ''.join('<tr><td>' + escape(row['suite']) + '</td><td>' + str(row['checks']) + '</td><td>' + escape(row['scope']) + '</td></tr>' for row in value['native']['suites'])
    gates = ''.join('<li>' + escape(text) + '</li>' for text in value['remainingGates'])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Shop RUB and optional video85</title><style>body{font:16px system-ui;max-width:1400px;margin:auto;padding:24px;background:#102c40;color:#f4ecd9}a{color:#b9ddff}h1{font-size:28px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}figure{margin:0;background:#173e57;padding:12px}img{width:100%;height:420px;object-fit:contain}small{color:#c3d9e5}table{border-collapse:collapse;width:100%}td,th{padding:10px;border:1px solid #577489;text-align:left}li{margin:12px 0}</style><h1>Shop RUB and optional rewarded video</h1><p>400 coins · three daily credits · fixed UTC+10 ·600-second cooldown. Targeted foundation evidence; default rollout remains disabled.</p><p>Backend357 tests; six selected native suites/' + str(value['native']['checks']) + ' checks;13 current UGUI captures. The earlier core invocation remains failed because its original RUB fixture failed; only its four separately passed core suites are selected.</p><p>SDK-client reports are deliberately lower trust. No real ad impression, revenue, live purchase, production or device-install claim.</p><table><tr><th>Suite</th><th>Checks</th><th>Actual scope</th></tr>' + rows + '</table><h2>Current native captures</h2><div class="grid">' + ''.join(cards) + '</div><h2>Remaining gates</h2><ul>' + gates + '</ul><p><a href="Summary.json">Bound validation summary</a> · <a href="SDK/Provider_Privacy_Audit.json">Static SDK privacy audit</a> · <a href="../../../Release/Advertising/README.md">Owner setup steps</a></p></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-run', default=CORE)
    parser.add_argument('--ui-run', default=UI)
    parser.add_argument('--build-run', default=BUILD)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    value = build(core_run=args.core_run, ui_run=args.ui_run, build_run=args.build_run)
    if args.publish:
        # Publishing is deliberately separate from read-only validation and
        # never overwrites an already accepted evidence summary/gallery.
        require(not (DEFAULT / 'Summary.json').exists() and not (DEFAULT / 'Comparison.html').exists(), 'PublishedReviewAlreadyExists')
        (DEFAULT / 'Comparison.html').write_text(gallery(value), encoding='utf-8')
        (DEFAULT / 'Summary.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': value['status'], 'published': args.publish, 'nativeChecks': value['native']['checks'],
                      'backendTests': value['backend']['tests'], 'captures': len(value['native']['capturedPngs'])}))


if __name__ == '__main__':
    main()
