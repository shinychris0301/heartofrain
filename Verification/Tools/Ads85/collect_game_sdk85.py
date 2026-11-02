"""Collect the isolated full-game SDK85 compile/static supplement.

Default mode is read-only. --execute-static runs only local APK inspection tools
and writes this supplement; it never builds, installs, launches or requests ads.
The published SDK-free checkpoint85 Summary is neither read as a test result nor
modified. An Android manifest is evidence of packaged configuration, not proof of
the SDK's runtime privacy behavior.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[3]
DEFAULT = ROOT / 'Verification/Evidence/ShopAds85/SDK/FullGameBuild'
CACHE = ROOT / '.verification-cache/Ads85'
EXPORT = CACHE / 'GameBuildAttempts/04a070b728f0468abf8c346985ba160a/Report.json'
ASSEMBLY = CACHE / 'GameBuildAttempts/1249497a0ce74f68a8e4862cf9aeef13/Report.json'
FROZEN = ROOT / 'Verification/Evidence/ShopAds85/Runs/ec3e507dd06148629d7e9cefdcf533b5/FrozenSources.json'
SDK_PROOF = CACHE / 'BuildAttempts/3a90322d9fe24dd6af7c05fd8e8ea2fb/Report.json'
PLAYER = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer')
PACKAGE = 'com.heartoftherain.ads85review'
STATUS = 'PASS_STATIC_UNLAUNCHED_YANDEX85_FULL_GAME_WITH_RELEASE_GATES'
SCENES = ['Assets/HeartOfTheRain/App/Launch/Scenes/Launch.unity',
          'Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity']
ANDROID = '{http://schemas.android.com/apk/res/android}'
AUTO_INIT = 'com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION'
FORBIDDEN_PERMISSIONS = {'com.google.android.gms.permission.AD_ID',
                         'android.permission.ACCESS_FINE_LOCATION',
                         'android.permission.ACCESS_COARSE_LOCATION',
                         'android.permission.ACCESS_BACKGROUND_LOCATION'}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def disk(path):
    value = str(Path(path).resolve())
    return '\\\\?\\' + value if os.name == 'nt' and not value.startswith('\\\\?\\') else value


def sha(path):
    h = hashlib.sha256()
    with open(disk(path), 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'DuplicateEvidenceKey')
            result[key] = value
        return result
    with open(disk(path), encoding='utf-8-sig') as stream:
        return json.load(stream, object_pairs_hook=unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NonFiniteNumber')))


def text(path):
    with open(disk(path), encoding='utf-8-sig') as stream:
        return stream.read()


def when(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def child(base, relative):
    result = (Path(base) / relative).resolve()
    require(result.is_relative_to(Path(base).resolve()), 'PathEscapesBoundRoot')
    return result


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Evidence:
    def __init__(self, out, execute):
        self.out, self.execute = Path(out).resolve(), execute
        require(self.out.is_relative_to((ROOT / 'Verification/Evidence/ShopAds85/SDK').resolve()),
                'SupplementMustRemainUnderSdkEvidence')
        self.artifacts, self.external, self.copies = {}, {}, {}
        self.checked = []

    def check(self, value, reason):
        require(value, reason)
        self.checked.append(reason)

    def bind(self, path, expected=None):
        path = Path(path).resolve()
        require(path.is_file(), 'MissingEvidenceFile:' + path.name)
        value = sha(path)
        require(expected is None or expected == value, 'EvidenceDigestMismatch:' + path.name)
        if path.is_relative_to(self.out):
            self.artifacts[path.relative_to(self.out).as_posix()] = value
        elif path.is_relative_to(ROOT):
            self.external[path.relative_to(ROOT).as_posix()] = value
        else:
            # Installed static tool inputs are deliberately outside the project.
            self.external['absolute:' + path.as_posix()] = value
        return value

    def copy(self, source, relative, expected=None):
        source = Path(source).resolve()
        digest = self.bind(source, expected)
        destination = child(self.out / 'Inputs', relative)
        require(os.stat(disk(source)).st_size <= 8 * 1024 * 1024,
                'RefuseLargeRawEvidenceCopy:' + source.name)
        require(source.suffix.lower() not in {'.apk', '.so', '.a', '.cpp'}, 'RefuseBinaryOrCppCopy')
        if self.execute:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                require(sha(destination) == digest, 'DoNotOverwriteDifferentEvidence')
            else:
                shutil.copyfile(disk(source), disk(destination))
        self.bind(destination, digest)
        self.copies[destination.relative_to(self.out).as_posix()] = {
            'source': source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else source.as_posix(),
            'sha256': digest, 'bytes': os.stat(disk(source)).st_size}
        return destination


def source_snapshot():
    result = {}
    for category in ('Assets', 'Packages', 'ProjectSettings'):
        for folder, _, names in os.walk(disk(ROOT / 'Unity' / category)):
            for name in names:
                p = Path(str(Path(folder) / name).removeprefix('\\\\?\\'))
                result[p.relative_to(ROOT / 'Unity').as_posix()] = sha(p)
    return result


def validate_process(e, path, phase, expected_steps):
    report = read(path)
    e.check(report['status'] == 'PASS_ROOT_YANDEX85_GAME_BUILD_PHASE' and report['phase'] == phase,
            'Actual' + phase.title() + 'Pass')
    e.check(report['package'] == PACKAGE and report['sourceInputCount'] == 5349
            and report['mainSourceUnchanged'] is True and report['unityPidsAfter'] == [],
            'Actual' + phase.title() + 'IsolatedGameScope')
    for key in ('apkLaunched', 'sdkAdRequested', 'configurationProvisioned', 'demoFixtureEnabled'):
        e.check(report[key] is False, phase + ':' + key + ':false')
    e.check([s['name'] for s in report['steps']] == expected_steps, phase + ':ExactOwnedSteps')
    previous = when(report['startedUtc'])
    for step in report['steps']:
        e.check(type(step['pid']) is int and step['pid'] > 0 and step['exitCode'] == 0
                and step['timedOut'] is False and step['processStopped'] is True
                and step['hidden'] is True and step['ownedKillOnCloseJobAssigned'] is True,
                phase + ':' + step['name'] + ':OwnedPidExitZero')
        start, end = when(step['startedUtc']), when(step['finishedUtc'])
        e.check(previous <= start <= end <= when(report['finishedUtc']),
                phase + ':' + step['name'] + ':Chronology')
        previous = end
        log = child(ROOT, step['log'])
        e.copy(log, phase + '/' + log.name, step['logSHA256'])
    for name in ('Main_before.json', 'Main_after.json'):
        p = path.parent / name
        e.copy(p, phase + '/' + name, report['mainSourceManifestSHA256'])
        e.check(read(p) == read(path.parent / 'Main_before.json'), phase + ':' + name + ':ExactMap')
    e.check(report['mainAfterSHA256'] == report['mainSourceManifestSHA256'], phase + ':AfterEqualsBefore')
    e.copy(path, phase + '/Report.json')
    return report


def verify_map(e, root, values, label):
    require(isinstance(values, dict) and values, label + ':MissingMap')
    for rel, value in values.items():
        p = child(root, rel)
        require(re.fullmatch('[0-9a-f]{64}', value) is not None and sha(p) == value,
                label + ':FileDigestMismatch:' + rel)
    e.check(True, label + ':All' + str(len(values)) + 'FilesExact')


def dex_classes(body):
    """Read class_defs, not mere strings/references, from a bounded APK DEX."""
    require(body[:4] == b'dex\n' and len(body) >= 112, 'InvalidDexHeader')
    def u32(offset):
        require(0 <= offset <= len(body) - 4, 'DexOffsetOutsideBody')
        return struct.unpack_from('<I', body, offset)[0]
    string_count, string_off = u32(56), u32(60)
    type_count, type_off = u32(64), u32(68)
    count, offset = u32(96), u32(100)
    require(string_off + string_count * 4 <= len(body) and type_off + type_count * 4 <= len(body)
            and offset + count * 32 <= len(body), 'DexTableOutsideBody')
    def string(index):
        require(index < string_count, 'DexStringIndex')
        p = u32(string_off + index * 4)
        for _ in range(5):
            require(p < len(body), 'DexStringOffset')
            n = body[p]; p += 1
            if n < 128:
                break
        else:
            raise RuntimeError('DexInvalidUleb')
        end = body.find(b'\0', p)
        require(end >= p, 'DexUnterminatedString')
        return body[p:end].decode('utf-8', errors='strict')
    result = set()
    for i in range(count):
        index = u32(offset + i * 32)
        require(index < type_count, 'DexTypeIndex')
        result.add(string(u32(type_off + index * 4)))
    return result


def static_command(e, name, args):
    output = child(e.out / 'Inputs', 'Static/' + name + '.txt')
    process = child(e.out / 'Inputs', 'Static/' + name + '_Process.json')
    if e.execute:
        output.parent.mkdir(parents=True, exist_ok=True)
        require(not output.exists() and not process.exists(), 'StaticOutputAlreadyExists')
        start = datetime.now(timezone.utc).isoformat()
        with open(disk(output), 'wb') as stream:
            p = subprocess.Popen([str(x) for x in args], stdout=stream, stderr=subprocess.STDOUT,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                code = p.wait(timeout=180)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
                write_json(process, {'status': 'FAIL_STATIC_TOOL_TIMEOUT', 'pid': p.pid, 'startedUtc': start,
                                     'finishedUtc': datetime.now(timezone.utc).isoformat()})
                raise
        write_json(process, {'status': 'PASS_STATIC_TOOL' if code == 0 else 'FAIL_STATIC_TOOL',
                             'pid': p.pid, 'exitCode': code, 'startedUtc': start,
                             'finishedUtc': datetime.now(timezone.utc).isoformat(),
                             'executable': str(args[0]), 'executableSHA256': sha(args[0]),
                             'outputSHA256': sha(output), 'scope': 'Static APK inspection only; no app execution.'})
    record = read(process)
    e.check(record['status'] == 'PASS_STATIC_TOOL' and record['exitCode'] == 0
            and record['pid'] > 0 and when(record['startedUtc']) <= when(record['finishedUtc']),
            name + ':ActualStaticProcessPass')
    e.bind(process); e.bind(output, record['outputSHA256']); e.bind(args[0], record['executableSHA256'])
    return text(output)


def static_apk(e, apk, expected, merged):
    e.check(sha(apk) == expected['sha256'] and os.stat(disk(apk)).st_size == expected['bytes'], 'ActualApkMatchesOwnedAssembly')
    checker_path = ROOT / 'Verification/Tools/check_apk.py'
    e.copy(checker_path, 'Tools/check_apk.py')
    if e.execute:
        require(not (e.out / 'APK_Artifact.json').exists(), 'StaticArtifactAlreadyExists')
        checker = import_file('fullgame85_apk_checker', checker_path)
        checker.APK, checker.OUT = apk, e.out
        checker.OUT.mkdir(parents=True, exist_ok=True)
        checker.run()
    artifact = read(e.out / 'APK_Artifact.json')
    e.bind(e.out / 'APK_Artifact.json')
    e.check(artifact['sha256'] == expected['sha256'] and artifact['bytes'] == expected['bytes']
            and artifact['zipalign4KiBPass'] is True and artifact['developmentSignatureVerifies'] is True
            and artifact['elf16KiBLoadSegmentsPass'] is True, 'ActualApkSignatureCrcAlignmentAndElf16KiBPass')
    e.check({x['file'] for x in artifact['libraries']} == {
        'lib/arm64-v8a/libil2cpp.so', 'lib/arm64-v8a/libmain.so', 'lib/arm64-v8a/libunity.so'}, 'ActualApkArm64Il2CppOnly')
    tools = PLAYER / 'SDK/build-tools/34.0.0'
    aapt = tools / 'aapt.exe'
    badging = static_command(e, 'APK_Badging', [aapt, 'dump', 'badging', apk])
    binary = static_command(e, 'APK_Manifest', [aapt, 'dump', 'xmltree', apk, 'AndroidManifest.xml'])
    permissions = static_command(e, 'APK_Permissions', [aapt, 'dump', 'permissions', apk])
    e.check("package: name='" + PACKAGE + "'" in badging and "sdkVersion:'26'" in badging
            and "targetSdkVersion:'35'" in badging, 'BinaryApkPackageMin26Target35')
    e.check("application-label:'Сердце дождя'" in badging, 'BinaryApkRussianLabel')
    e.check(all(x not in permissions and x not in binary for x in FORBIDDEN_PERMISSIONS), 'BinaryApkNoAdIdOrLocationPermissions')
    e.check(AUTO_INIT in binary and re.search(re.escape(AUTO_INIT) + r'.{0,350}?android:value[^\n]*\(type 0x12\)0x0', binary, re.S),
            'BinaryApkYandexAutoInitFalse')
    e.check('PayContentProvider' not in binary and 'heartoftherain-pay' not in binary
            and 'ru.rustore.sdk' not in binary, 'BinaryApkNoRuStorePayProviderOrScheme')
    root = ET.parse(disk(merged)).getroot()
    app = root.find('application')
    e.check(root.attrib.get('package') == PACKAGE and app is not None, 'MergedManifestPackageMatchesBinary')
    meta = {x.get(ANDROID + 'name'): x.get(ANDROID + 'value') for x in app.findall('meta-data')}
    e.check(meta.get(AUTO_INIT) == 'false', 'MergedManifestYandexAutoInitFalse')
    main = [x for x in app.findall('activity') if x.get(ANDROID + 'name') == 'com.unity3d.player.UnityPlayerActivity']
    e.check(len(main) == 1 and main[0].get(ANDROID + 'screenOrientation') == 'portrait'
            and re.search(r'android:screenOrientation[^\n]*\(type 0x10\)0x1', binary), 'MergedAndBinaryUnityActivityPortrait')
    provider = [x for x in app.findall('provider') if x.get(ANDROID + 'name') == 'com.yandex.mobile.ads.core.initializer.YandexAdsInitializeProvider']
    e.check(len(provider) == 1 and provider[0].get(ANDROID + 'exported') == 'false', 'PackagedYandexInitializerProviderNonExported')
    components = [{'kind': x.tag, 'name': x.get(ANDROID + 'name'), 'exported': x.get(ANDROID + 'exported'),
                   'enabled': x.get(ANDROID + 'enabled', 'true (Android default)')}
                  for x in app if x.tag in ('provider', 'service')]
    with zipfile.ZipFile(apk) as archive:
        e.check(archive.testzip() is None, 'ActualApkCrcIndependentRead')
        names = archive.namelist()
        e.check(all('assets/bin/Data/level' + str(i) in names for i in (0, 1)), 'ActualApkContainsTwoCompiledSceneDataFiles')
        classes = set()
        dex = []
        for name in names:
            if re.fullmatch(r'classes(?:[2-9][0-9]*)?\.dex', name):
                body = archive.read(name)
                require(len(body) <= 64 * 1024 * 1024, 'UnexpectedLargeDex')
                defined = dex_classes(body); classes.update(defined)
                dex.append({'file': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'definedClassCount': len(defined)})
        required = {'Lcom/heartoftherain/identity/DeviceIdentity82;', 'Lcom/yandex/mobile/ads/rewarded/RewardedAd;',
                    'Lcom/yandex/mobile/ads/rewarded/RewardedAdLoader;', 'Lio/appmetrica/analytics/AppMetrica;'}
        e.check(required <= classes, 'ActualDexDefinesNativeIdentityAndYandexRewardedAndAppMetrica')
        e.check(not any(x.startswith('Lru/rustore/sdk/') for x in classes), 'ActualDexNoRuStoreSdkClasses')
    return {'package': PACKAGE, 'label': 'Сердце дождя', 'minApi': 26, 'targetApi': 35, 'portraitOnly': True,
            'sdkAutoInit': False, 'adIdPermission': False, 'locationPermissions': False, 'dex': dex,
            'requiredDefinedClasses': sorted(required), 'packagedProvidersAndServices': components,
            'apkSHA256': expected['sha256'], 'apkBytes': expected['bytes']}


def build(out=DEFAULT, export_report=EXPORT, assembly_report=ASSEMBLY, execute_static=False):
    e = Evidence(out, execute_static)
    e.bind(Path(__file__))
    for p in (export_report, assembly_report):
        require(Path(p).resolve().is_relative_to((CACHE / 'GameBuildAttempts').resolve()), 'ActualGameAttemptPathRequired')
    export = validate_process(e, Path(export_report).resolve(), 'export', ['UnityExportProcess'])
    assembly = validate_process(e, Path(assembly_report).resolve(), 'assemble', ['GradleVersion', 'Dependencies', 'Assemble'])
    e.check(when(export['finishedUtc']) <= when(assembly['startedUtc']), 'ActualExportPrecedesAssembly')
    project = child(ROOT, assembly['project'])
    e.check(project == child(ROOT, export['project']) and project.is_relative_to(CACHE), 'SameOwnedCacheClone')
    preparation_path = project.with_name(project.name + '_Preparation.json')
    prep = read(preparation_path)
    e.copy(preparation_path, 'Preparation.json', assembly['preparationSHA256'])
    e.check(export['preparationSHA256'] == assembly['preparationSHA256'] and prep['package'] == PACKAGE
            and prep['unity'] == '2022.3.62f3' and prep['sourceInputCount'] == 5349
            and prep['originalMetaGUIDBytesPreserved'] is True and prep['mainSourceUnchanged'] is True
            and prep['configurationProvisioned'] is False and prep['apkLaunched'] is False,
            'PreparationActualIsolatedCloneScope')
    e.copy(FROZEN, 'AcceptedMain_FrozenSources.json')
    frozen = read(FROZEN)
    source_records = {k.removeprefix('Unity/'): v for k, v in frozen['files'].items()}
    source = {k: v['sha256'] for k, v in source_records.items()}
    e.check(frozen['inputCount'] == 5349 and len(source) == 5349 and source_records == prep['sourceInputs']
            and source == prep['copiedMainSHA256'] == source_snapshot(), 'All5349CurrentMainInputsExactlyAcceptedAndCopied')
    e.check(all(os.stat(disk(ROOT / 'Unity' / k)).st_size == v['bytes'] for k, v in source_records.items()),
            'All5349CurrentMainInputSizesMatchFrozenRecords')
    e.copy(project / 'SourceInputs.json', 'SourceInputs.json', prep['sourceManifestSHA256'])
    e.check(read(project / 'SourceInputs.json') == source_records == read(Path(export_report).parent / 'Main_before.json')
            == read(Path(assembly_report).parent / 'Main_before.json'), 'SourceManifestsUseIdenticalExact5349Map')
    for report in (export, assembly):
        e.check(report['mainSourceManifestSHA256'] == prep['sourceManifestSHA256'], 'ActualProcessBoundToPreparedMainMap:' + report['phase'])
    generated = prep['generatedSHA256']
    unchanged = {k: v for k, v in source.items() if k not in generated}
    verify_map(e, project, unchanged, 'CloneAllOriginalNonOverlayInputs')
    original_metas = {k: v for k, v in source.items() if k.endswith('.meta')}
    verify_map(e, project, original_metas, 'CloneAllOriginalMetaGuidBytes')
    verify_map(e, project, prep['copiedVendorSHA256'], 'CopiedOfficialVendorSubset')
    verify_map(e, project, {k: v for k, v in generated.items() if k != 'ProjectSettings/ProjectSettings.asset'}, 'GeneratedCompileProfileInputs')
    profile = prep['profile']
    e.check(profile['minSdk'] == 26 and profile['targetSdk'] == 35 and profile['compileSdk'] == 35
            and profile['architecture'] == 'ARM64' and profile['scriptingBackend'] == 'IL2CPP'
            and profile['developmentOnly'] is True and profile['publisherUnitProvisioned'] is False
            and profile['sdkAutoInit'] is False and profile['locationPermissionsRemoved'] is True
            and profile['adIdPermissionRemoved'] is True and profile['appMetrica'] == '8.6.0', 'ExplicitIsolatedAndroidProfile')
    csc = text(project / 'Assets/csc.rsp')
    e.check('HOTR_YANDEX_ADS' in csc and 'HOTR_YANDEX_ADS_ISOLATED_FIXTURE' not in csc
            and 'APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED' in csc
            and 'APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED' in csc, 'RealAdapterBranchAndRevenueHookCompileDefines')
    adapter_rel = 'Assets/HeartOfTheRain/App/Advertising/Runtime/YandexRewardedAdsProvider85.cs'
    e.copy(project / adapter_rel, 'CompiledGame/YandexRewardedAdsProvider85.cs', prep['actualGameAdapterSourceSHA256'])
    e.check(sha(ROOT / 'Unity' / adapter_rel) == prep['actualGameAdapterSourceSHA256'], 'CompiledAdapterIsCurrentActualMainAdapter')
    native_path = project / 'GameAndroidExport.json'
    native = read(native_path)
    e.copy(native_path, 'GameAndroidExport.json', export['exportReportSHA256'])
    e.check(assembly['exportReportSHA256'] == export['exportReportSHA256'] and native['errors'] == 0
            and not native['error'] and native['status'] == 'PASS_ISOLATED_YANDEX85_GAME_GRADLE_EXPORT'
            and native['unity'] == '2022.3.62f3' and native['minApi'] == 26 and native['targetApi'] == 35
            and native['productNameBefore'] == native['productNameAfter'] == 'Сердце дождя'
            and native['enabledScenes'] == SCENES == prep['enabledScenes'], 'ActualFullGameNativeExportMetadata')
    for key in ('fullGame', 'development', 'jdkSettingsUnchanged', 'actualAdapterSdkBranchCompiled',
                'portraitOnly', 'enabledScenesUnchanged', 'noSdkInitializationOrAdRequests'):
        e.check(native[key] is True, 'ActualNativeExport:' + key)
    e.check(native['configurationProvisioned'] is False and native['apkLaunched'] is False
            and when(export['steps'][0]['startedUtc']) <= when(native['utc']) <= when(export['steps'][0]['finishedUtc']),
            'NativeExportFreshAndUnprovisioned')
    export_root = project / 'Build/GameGradleExport'
    require(Path(native['output']).resolve() == export_root.resolve(), 'NativeExportOutputMismatch')
    native_sources = {x['path']: x['sha256'] for x in native['sourceBindings']}
    settings_rel = 'ProjectSettings/ProjectSettings.asset'
    e.check(native_sources[settings_rel] == generated[settings_rel], 'NativeExportCapturedPreparedCloneSettingsBeforeBuildFlush')
    verify_map(e, project, {k: v for k, v in native_sources.items() if k != settings_rel}, 'NativeExportAllNonSettingsSourceBindings')
    # PlayerSettings calls in the recorded export helper serialize this one
    # cache-clone file during BuildPlayer, after sourceBindings was captured.
    # This exception never applies to any main-project source or original meta.
    e.copy(project / settings_rel, 'CompiledGame/ProjectSettings_AfterExport.asset')
    settings_after = {'capturedBeforeExportSHA256': native_sources[settings_rel],
                      'actualAfterExportSHA256': sha(project / settings_rel),
                      'mainUnchangedSHA256': source[settings_rel],
                      'scope': 'One explicit cache-clone PlayerSettings serialization; native report and actual binary validate resulting profile. Main settings remain byte-exact.'}
    verify_map(e, export_root, {x['path']: x['sha256'] for x in native['exportBindings']}, 'NativeExportGeneratedArtifactBindings')
    modern_path = project / 'GameModernPreparation.json'
    modern = read(modern_path)
    e.copy(modern_path, 'GameModernPreparation.json', assembly['modernPreparationSHA256'])
    e.check(modern['preparationSHA256'] == assembly['preparationSHA256']
            and modern['exportReportSHA256'] == export['exportReportSHA256']
            and modern['package'] == PACKAGE, 'ModernDerivationBoundToActualGameExport')
    modern_root = project / 'Build/GameGradleModern'
    verify_map(e, modern_root, modern['derivedProfileSHA256'], 'ModernDerivedOriginalInputs')
    e.check([x['path'] for x in modern['changes']] == ['build.gradle', 'gradle.properties', 'unityLibrary/build.gradle',
              'unityLibrary/HeartOfTheRainIdentity82.androidlib/AndroidManifest.xml'], 'ExactlyFourDocumentedModernDerivations')
    for change in modern['changes']:
        e.check(sha(export_root / change['path']) == change['beforeSHA256']
                and sha(modern_root / change['path']) == change['afterSHA256'], 'ModernDerivationBeforeAfter:' + change['path'])
    for rel in ('build.gradle', 'gradle.properties', 'launcher/build.gradle', 'unityLibrary/build.gradle',
                'unityLibrary/HeartOfTheRainIdentity82.androidlib/build.gradle',
                'gradle/wrapper/gradle-wrapper.properties', 'launcher/src/main/res/values/strings.xml'):
        e.copy(modern_root / rel, 'Gradle/' + rel)
    library_build = text(modern_root / 'unityLibrary/build.gradle')
    e.check("version '8.7.0'" in text(modern_root / 'build.gradle')
            and 'ndkPath "' + (PLAYER / 'NDK').as_posix() + '"' in library_build
            and 'android.ndkPath' in library_build and 'android.ndkDirectory' not in library_build,
            'ExplicitAgp87AndPinnedUnityNdkToolchain')
    e.copy(SDK_PROOF, 'ProvenSdkAssembly.json', assembly['sdkAssemblyProofSHA256'])
    proof = read(SDK_PROOF)
    e.check(proof['status'] == 'PASS_ROOT_ISOLATED_YANDEX85_BUILD_PHASE'
            and proof['phase'] == 'assemble-modern' and proof['apkLaunched'] is False
            and assembly['jdkReleaseSHA256'] == proof['jdkReleaseSHA256']
            and assembly['gradleLauncherSHA256'] == proof['gradleLauncherSHA256']
            and assembly['gradleVersion'] == '8.9' and assembly['javaVersion'] == '17'
            and assembly['agpVersion'] == '8.7.0', 'MatchedPreviouslyProvenExternalTools')
    java_release = ROOT / '.verification-cache/RuStore81/Toolchain/jdk-17.0.20.1+1/release'
    gradle_launcher = CACHE / 'Toolchain/gradle-8.9/lib/gradle-launcher-8.9.jar'
    e.bind(java_release, assembly['jdkReleaseSHA256']); e.bind(gradle_launcher, assembly['gradleLauncherSHA256'])
    e.check(re.search(r'^JAVA_VERSION="17\.', text(java_release), re.M), 'ActualPinnedExternalJava17Release')
    version_log = text(child(ROOT, assembly['steps'][0]['log']))
    e.check('Gradle 8.9' in version_log and 'Launcher JVM:  17.' in version_log, 'ActualGradleVersionProcessReports89AndJava17')
    assemble_log = text(child(ROOT, assembly['steps'][-1]['log']))
    e.check('BUILD SUCCESSFUL' in assemble_log and '117 actionable tasks' in assemble_log, 'ActualFullGameGradleAssemblySuccessful117Tasks')
    locking_path = ROOT / 'Verification/Tools/Ads85/GradleDependencyLocking85.gradle'
    e.copy(locking_path, 'Tools/GradleDependencyLocking85.gradle', assembly['dependencyLockingScriptSHA256'])
    lock_text = ''
    for rel, digest in assembly['dependencyLockSHA256'].items():
        p = modern_root / rel
        e.copy(p, 'Gradle/' + rel, digest); lock_text += text(p) + '\n'
    e.check('com.yandex.android:mobileads:8.6.0=releaseRuntimeClasspath' in lock_text
            and 'io.appmetrica.analytics:analytics:8.6.0=releaseRuntimeClasspath' in lock_text
            and ':rustore' not in lock_text.lower(), 'ActualLockedYandex86AppMetrica86AndNoRuStore')
    verify_map(e, modern_root, assembly['mergedManifestSHA256'], 'ActualMergedManifestBindings')
    for rel, digest in assembly['mergedManifestSHA256'].items():
        e.copy(modern_root / rel, 'MergedManifests/' + rel, digest)
    native_libs = assembly['nativeLibrarySHA256']
    e.check(any(x.endswith('/libil2cpp.so') for x in native_libs), 'ActualAssemblyRecordsGameIl2CppLibrary')
    verify_map(e, modern_root, native_libs, 'ActualNativeAssemblyLibraryBindings')
    # Preserve original helper identities. The export runner legitimately predates
    # the later assembly runner; neither digest is invented as current source.
    current_helpers = {}
    for name in ('run_yandex85_game_build.py', 'prepare_yandex85_game.py', 'run_yandex85_sdk_build.py',
                 'Yandex85GameExport.cs', 'prepare_yandex85_sdk.py'):
        p = Path(__file__).with_name(name)
        current_helpers[name] = e.bind(p)
        e.copy(p, 'Tools/' + name)
    e.check(current_helpers['run_yandex85_game_build.py'] == assembly['runnerSHA256']
            and current_helpers['prepare_yandex85_game.py'] == assembly['gamePreparationHelperSHA256'] == modern['helperSHA256']
            and current_helpers['run_yandex85_sdk_build.py'] == assembly['sharedSdkBuildHelperSHA256'] == modern['sharedModernHelperSHA256']
            and prep['helperSHA256'] == assembly['preparedGamePreparationHelperSHA256'] == export['preparedGamePreparationHelperSHA256']
            and prep['gameExportHelperSHA256'] == current_helpers['Yandex85GameExport.cs'], 'ActualCurrentAndHistoricalHelperProvenance')
    apk = child(ROOT, assembly['apk']['path'])
    merged_rel = next(x for x in assembly['mergedManifestSHA256'] if x.startswith('launcher/build/intermediates/merged_manifest/'))
    inspection = static_apk(e, apk, assembly['apk'], modern_root / merged_rel)
    # Final main check fences static inspection too; no main input may drift.
    e.check(source_snapshot() == source, 'All5349MainInputsStillExactAfterStaticInspection')
    return {
        'status': STATUS, 'utc': datetime.now(timezone.utc).isoformat(), 'error': None,
        'scope': 'Current full game ARM64 IL2CPP development clone: actual two-scene Unity export, external modern Gradle assembly and static APK inspection only. No app, SDK or ad execution.',
        'mainSourceInputCount': 5349, 'mainSourceUnchanged': True, 'mainAcceptedFrozenManifestSHA256': sha(FROZEN),
        'sourceManifestSHA256': prep['sourceManifestSHA256'], 'apk': assembly['apk'],
        'apkLaunched': False, 'sdkAdRequested': False, 'configurationProvisioned': False,
        'fullGame': True, 'development': True, 'enabledScenes': SCENES,
        'unity': '2022.3.62f3', 'embeddedExportJava': '11',
        'externalToolchain': {'java': '17', 'gradle': '8.9', 'agp': '8.7.0', 'ndk': str(PLAYER / 'NDK'),
                              'jdkReleaseSHA256': assembly['jdkReleaseSHA256'], 'gradleLauncherSHA256': assembly['gradleLauncherSHA256']},
        'nativeExportWarnings': native['warnings'], 'staticInspection': inspection,
        'checks': e.checked, 'checkCount': len(e.checked),
        'helperProvenance': {'preparedHelperSHA256': prep['helperSHA256'],
                             'exportRunnerRecordedSHA256': export['runnerSHA256'],
                             'assemblyRunnerRecordedSHA256': assembly['runnerSHA256'], 'currentHelpers': current_helpers},
        'cloneSettingsSerialization': settings_after,
        'copiedInputs': e.copies, 'artifactSHA256': e.artifacts, 'externalEvidenceSHA256': e.external,
        'remainingGates': [
            'Publisher account/unit IDs, public HTTPS backend/configuration, privacy/consent policy and actual provider rollout remain unprovisioned; ordinary main APKs remain SDK-free.',
            'This clone APK was not installed or launched. SDK initialization, ad loading/showing/closing, account recovery, reward delivery, lifecycle and physical-device acceptance remain untested with the SDK.',
            'Auto-initialization metadata is false and AD_ID/location permissions are absent. Initializer providers, AppMetrica services/providers, AndroidX startup, identifier/referrer queries and analytics modules remain packaged; zero pre-consent traffic or data collection is not established.',
            'Client-reported/capped rewarded completion is not provider impression verification. No impression, production revenue, payout, payment or purchase acceptance is inferred.',
            'The external Java17/Gradle8.9/AGP8.7 profile is an explicit isolated derivation, not an upgrade of the pinned main Unity engine or its SDK/toolchain.',
            'Required Unity splash entitlement and existing RuStore, signing, hosting, moderation/legal and broader gameplay performance release gates remain open.'
        ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT)
    parser.add_argument('--export-report', type=Path, default=EXPORT)
    parser.add_argument('--assembly-report', type=Path, default=ASSEMBLY)
    parser.add_argument('--execute-static', action='store_true', help='Run only static APK tools and write the separate supplement.')
    args = parser.parse_args()
    report = build(args.out, args.export_report, args.assembly_report, args.execute_static)
    if args.execute_static:
        write_json(args.out / 'Report.json', report)
    print(json.dumps({'status': report['status'], 'checks': report['checkCount'],
                      'apk': report['apk'], 'report': str(args.out / 'Report.json'),
                      'scope': report['scope']}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
