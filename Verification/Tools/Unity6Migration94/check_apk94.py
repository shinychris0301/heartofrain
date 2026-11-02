"""Root-only static inspection of actual isolated Unity 6 APKs; never use ADB.

Writes only fresh StaticApk94.json and AndroidStatic94/ beside the native build
report. Does not invoke a historical collector or edit an APK/project/settings.
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
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
ANDROID6 = Path('E:/HeartRainUnity6_94/6000.6.6f1/Editor/Data/PlaybackEngines/AndroidPlayer')
ANDROID22 = Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer')
ISOLATED = 'com.heartoftherain.unity6review94'
INTERNAL = 'com.heartoftherain.verification'
SDK_PREFIXES = (b'Lru/rustore/sdk/pay/', b'Lru/rustore/sdk/core/', b'Lcom/yandex/mobile/ads/', b'Lio/appmetrica/')


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def binding(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), 'Apk94PublicArtifactOutsideProject')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def imported(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def load_build(path):
    path = Path(path).resolve()
    need(path.is_relative_to(OUT) and path.name in ('BuildDevelopment.json', 'BuildNonDevelopment.json'), 'Apk94ActualNativeBuildPathRequired')
    native, invocation = read(path), read(path.parent / 'Invocation.json')
    development = path.name == 'BuildDevelopment.json'
    operation = 'BuildDevelopment' if development else 'BuildNonDevelopment'
    package = ISOLATED if development else INTERNAL
    need(native.get('operation') == operation and native.get('status') == 'PASS_ISOLATED_UNITY6_94_' + operation.upper()
         and native.get('exitCode') == 0 and native.get('errors') == 0 and not native.get('error')
         and native.get('buildResult') == 'Succeeded' and native.get('buildPackageName') == package
         and native.get('nonDevelopmentCompileOnly') is (not development), 'Apk94PassedCorrectNativeBuildRequired')
    need(invocation.get('status') == 'PASS_ISOLATED_UNITY6_94_NATIVE' and invocation.get('exitCode') == 0
         and invocation.get('entry') == 'HeartOfTheRain.Verification.Unity6Migration94.' + operation
         and invocation.get('mainInputsUnchanged') is True and invocation.get('unityPidsAfter') == []
         and invocation.get('nativeReportSHA256') == sha(path) and invocation.get('nativeReport') == path.relative_to(ROOT).as_posix()
         and invocation.get('actualEngineVersionFromProcessLog') == native.get('unity') == native.get('expectedUnity')
         and native.get('unity', '').startswith('6000.'), 'Apk94RealCompletedUnity6BuildRequired')
    after = native.get('after', {})
    need(after.get('packageName') == ISOLATED and after.get('showSplashScreen') is False and after.get('showUnityLogo') is False
         and after.get('portraitOnly') is True and after.get('applicationEntry') == 'Activity'
         and after.get('backend') == 'IL2CPP' and after.get('architectures') == 'ARM64'
         and after.get('minApi') == 26 and after.get('sdkFreeDefines') is True, 'Apk94NativeSettingsAndRestorationRequired')
    apk = Path(native['output']).resolve()
    need(apk.is_relative_to(PROJECT / 'Builds') and apk.suffix == '.apk' and apk.is_file()
         and sha(apk) == native.get('apkSHA256') and apk.stat().st_size == native.get('bytes'), 'Apk94NativeArtifactChanged')
    return {'native': native, 'path': path, 'invocation': path.parent / 'Invocation.json', 'apk': apk,
            'candidateSources': path.parent / 'CandidateSources_after.json', 'package': package, 'development': development}


def tools():
    for android in (ANDROID6, ANDROID22):
        java = android / 'OpenJDK/bin/java.exe'
        base = android / 'SDK/build-tools'
        if not java.is_file() or not base.is_dir():
            continue
        for directory in sorted(base.iterdir(), key=lambda p: tuple(int(v) for v in re.findall(r'\d+', p.name)), reverse=True):
            paths = {'aapt': directory / 'aapt.exe', 'zipalign': directory / 'zipalign.exe',
                     'apksignerJar': directory / 'lib/apksigner.jar', 'java': java}
            if all(path.is_file() for path in paths.values()):
                return paths
    raise RuntimeError('Apk94SupportedReadOnlyAndroidToolsUnavailable')


def parse_manifest(text):
    """Parse only actual aapt xmltree element boundaries and attribute values."""
    nodes, stack = [], []
    for line in text.splitlines():
        element = re.match(r'^(\s*)E:\s+([A-Za-z0-9_.:-]+)\b', line)
        if element:
            depth = len(element.group(1))
            while stack and stack[-1]['depth'] >= depth:
                stack.pop()
            node = {'tag': element.group(2), 'depth': depth, 'attributes': {}, 'parent': stack[-1]['tag'] if stack else None}
            nodes.append(node)
            stack.append(node)
        else:
            attribute = re.match(r'^\s*A:\s+([^\s(=]+)(?:\([^)]*\))?=(.*)$', line)
            if attribute and stack:
                stack[-1]['attributes'][attribute.group(1)] = attribute.group(2).strip()
    need(nodes and nodes[0]['tag'] == 'manifest', 'Apk94ManifestTreeMissing')
    return nodes


def attribute_value(raw):
    if raw is None:
        return None
    text = re.match(r'^"([^\"]*)"', raw)
    if text:
        return text.group(1)
    integer = re.match(r'^\(type 0x[0-9a-fA-F]+\)0x([0-9a-fA-F]+)\s*$', raw)
    return int(integer.group(1), 16) if integer else raw


def manifest_profile(badging, manifest, package, development):
    need("package: name='" + package + "'" in badging, 'Apk94ActualPackageMismatch')
    need("application-label:'Сердце дождя'" in badging, 'Apk94RussianVisibleNameMismatch')
    need("sdkVersion:'26'" in badging, 'Apk94ActualMinimumApiMismatch')
    target = re.search(r"(?m)^targetSdkVersion:'([0-9]+)'$", badging)
    need(target is not None and int(target.group(1)) >= 26, 'Apk94ActualTargetApiInvalid')
    abi = re.search(r"(?m)^native-code:\s*(.+)$", badging)
    need(abi is not None and re.findall(r"'([^']+)'", abi.group(1)) == ['arm64-v8a'], 'Apk94ActualAbiMismatch')
    nodes = parse_manifest(manifest)
    applications = [node for node in nodes if node['tag'] == 'application']
    need(len(applications) == 1, 'Apk94SingleApplicationRequired')
    debug_value = attribute_value(applications[0]['attributes'].get('android:debuggable'))
    need(debug_value in (None, 0, 1, 0xffffffff), 'Apk94UnknownDevelopmentFlagEncoding')
    debuggable = bool(debug_value)
    need(debuggable is development and ('application-debuggable' in badging) is development, 'Apk94DevelopmentFlagMismatch')
    activities = [node for node in nodes if node['tag'] == 'activity']
    player = [node for node in activities if attribute_value(node['attributes'].get('android:name')) == 'com.unity3d.player.UnityPlayerActivity']
    need(len(player) == 1 and attribute_value(player[0]['attributes'].get('android:screenOrientation')) in (1, 'portrait'), 'Apk94ActualPortraitActivityRequired')
    need(not any('GameActivity' in str(attribute_value(node['attributes'].get('android:name'))) for node in activities), 'Apk94UnexpectedGameActivity')
    need("launchable-activity: name='com.unity3d.player.UnityPlayerActivity'" in badging, 'Apk94ActualActivityNotLaunchable')
    minimum = [attribute_value(node['attributes'].get('android:minSdkVersion')) for node in nodes if node['tag'] == 'uses-sdk']
    need(minimum == [26], 'Apk94ManifestMinimumApiMismatch')
    need(not any(value in manifest for value in ('RuStorePayContentProvider', 'heartoftherain-pay', 'com.yandex.mobile.ads', 'io.appmetrica')), 'Apk94UnexpectedPaymentOrAdManifest')
    return {'package': package, 'development': development, 'minApi': 26, 'targetApi': int(target.group(1)),
            'activity': 'com.unity3d.player.UnityPlayerActivity', 'orientation': 'portrait', 'abi': ['arm64-v8a']}


def elf_segments(body):
    need(len(body) >= 64 and body[:6] == b'\x7fELF\x02\x01', 'Apk94ExpectedLittleEndianElf64')
    need(struct.unpack_from('<H', body, 18)[0] == 183, 'Apk94ExpectedAarch64Machine')
    offset = struct.unpack_from('<Q', body, 32)[0]
    size, count = struct.unpack_from('<HH', body, 54)
    need(size >= 56 and 0 < count <= 1024 and offset + size * count <= len(body), 'Apk94ElfProgramHeaderBoundsInvalid')
    rows = []
    for index in range(count):
        kind, flags, file_offset, address, physical, file_size, memory_size, alignment = struct.unpack_from('<IIQQQQQQ', body, offset + index * size)
        if kind != 1:
            continue
        need(file_offset + file_size <= len(body) and memory_size >= file_size, 'Apk94ElfLoadSegmentBoundsInvalid')
        need(alignment >= 16384 and alignment & (alignment - 1) == 0 and (file_offset - address) % 16384 == 0, 'Apk94Elf16KiBAlignmentFailed')
        rows.append({'offset': file_offset, 'address': address, 'alignment': alignment, 'fileSize': file_size, 'memorySize': memory_size})
    need(rows, 'Apk94ElfHasNoLoadSegments')
    return rows


def zip_profile(apk):
    libraries, dexes, stored = [], [], []
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        need(len(names) == len(set(names)) and archive.testzip() is None, 'Apk94ZipDuplicatesOrCrcFailure')
        for entry in archive.infolist():
            if entry.filename.endswith('.dex'):
                dexes.append(archive.read(entry))
            if not (entry.filename.startswith('lib/') and entry.filename.endswith('.so')):
                continue
            need(re.fullmatch(r'lib/arm64-v8a/[A-Za-z0-9_.+-]+\.so', entry.filename) is not None, 'Apk94UnexpectedNativeAbiOrPath')
            body = archive.read(entry)
            archive.fp.seek(entry.header_offset)
            header = archive.fp.read(30)
            need(len(header) == 30 and header[:4] == b'PK\x03\x04', 'Apk94ZipLocalHeaderInvalid')
            name_length, extra_length = struct.unpack_from('<HH', header, 26)
            data_offset = entry.header_offset + 30 + name_length + extra_length
            is_stored = entry.compress_type == zipfile.ZIP_STORED
            if is_stored:
                need(data_offset % 16384 == 0, 'Apk94StoredNativeLibraryNot16KiBAligned')
                stored.append(entry.filename)
            libraries.append({'file': entry.filename, 'compression': entry.compress_type,
                              'dataOffset': data_offset, 'loadSegments': elf_segments(body)})
    need(libraries and dexes, 'Apk94NativeLibrariesAndDexRequired')
    need(any(b'Lcom/heartoftherain/identity/DeviceIdentity82;' in data for data in dexes), 'Apk94IdentityBridgeMissing')
    need(all(not any(prefix in data for prefix in SDK_PREFIXES) for data in dexes), 'Apk94UnexpectedPaymentOrAdDex')
    return {'libraries': libraries, 'dexCount': len(dexes), 'storedNativeLibraries': stored,
            'compressedNativeLibraryCount': sum(row['compression'] != zipfile.ZIP_STORED for row in libraries)}


def inspect(build_path):
    build = load_build(build_path)
    report_path, raw = build['path'].parent / 'StaticApk94.json', build['path'].parent / 'AndroidStatic94'
    need(not report_path.exists() and not raw.exists(), 'Apk94ExistingStaticEvidencePreserved')
    raw.mkdir()
    report = {'schemaVersion': 1, 'checkpoint': 94, 'status': 'FAIL_INTERNAL_UNITY6_94_APK',
        'startedUtc': datetime.now(timezone.utc).isoformat(), 'runner': binding(Path(__file__)),
        'apk': binding(build['apk']), 'nativeReport': binding(build['path']), 'buildInvocation': binding(build['invocation']),
        'candidateSources': binding(build['candidateSources']), 'package': build['package'],
        'development': build['development'], 'nonDevelopmentCompileOnly': not build['development'],
        'checks': {}, 'errors': [], 'warnings': [],
        'scope': 'Read-only actual internal SDK-free APK package/label/API/Activity/development/DEX, ZIP CRC/four-byte zipalign, signature and AArch64 16KiB ELF/stored-library-offset checks. Native getters bind splash configuration; no static claim that visual startup was observed. No device/provider/backend acceptance, release signing, store publication or general performance certification. Non-development artifact is compile-only and must never be installed.'}
    api = imported('unity6_94_static_source_reader', 'Verification/Tools/Ads85/run_ads85_native.py')
    runner = imported('unity6_94_static_candidate_reader', 'Verification/Tools/Unity6Migration94/run_native.py')
    before_main, before_candidate = api.freeze(), runner.candidate_sources(api)
    try:
        need(before_main == read(OUT / 'MainSources_Before.json') and before_candidate == read(build['candidateSources']), 'Apk94InputsChangedSinceBuild')
        selected = tools()
        report['tools'] = {name: {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size} for name, path in selected.items()}

        def command(name, arguments):
            result = subprocess.run([str(value) for value in arguments], capture_output=True, timeout=180)
            stdout = result.stdout.decode('utf-8', 'replace')
            stderr = result.stderr.decode('utf-8', 'replace')
            (raw / (name + '_stdout.txt')).write_text(stdout, encoding='utf-8')
            (raw / (name + '_stderr.txt')).write_text(stderr, encoding='utf-8')
            need(result.returncode == 0, 'Apk94' + name + 'CommandFailed')
            if stderr.strip():
                report['warnings'].append(name + ' returned stderr; inspect its bound raw output.')
            return stdout

        command('Signature', [selected['java'], '-jar', selected['apksignerJar'], 'verify', '--verbose', '--print-certs', build['apk']])
        report['checks']['signatureVerifies'] = True
        command('Zipalign', [selected['zipalign'], '-c', '-v', '4', build['apk']])
        report['checks']['zipAlignFourBytePass'] = True
        badging = command('Badging', [selected['aapt'], 'dump', 'badging', build['apk']])
        manifest = command('Manifest', [selected['aapt'], 'dump', 'xmltree', build['apk'], 'AndroidManifest.xml'])
        report['manifestProfile'] = manifest_profile(badging, manifest, build['package'], build['development'])
        report['checks'].update(packageMatchesNativeBuild=True, portraitActivity=True, minApi26=True,
                                developmentFlagMatches=True, abiArm64Only=True)
        report['zipProfile'] = zip_profile(build['apk'])
        report['checks'].update(zipCrcPass=True, elf16KiBLoadSegmentsPass=True, storedNative16KiBAligned=True,
                                sdkFreeDex=True, identityBridgePresent=True)
        if report['zipProfile']['compressedNativeLibraryCount']:
            report['warnings'].append('Some native libraries are compressed; stored-library mmap alignment applies only to the recorded uncompressed subset.')
        report['status'] = 'PASS_INTERNAL_UNITY6_94_APK'
    except Exception as error:
        category = str(error) if isinstance(error, RuntimeError) and re.fullmatch(r'[A-Za-z0-9]+', str(error)) else type(error).__name__
        report['errors'].append(category)
    finally:
        report['checks']['sourcesUnchanged'] = api.freeze() == before_main and runner.candidate_sources(api) == before_candidate
        report['checks']['apkUnchanged'] = binding(build['apk']) == report['apk']
        if not report['checks']['sourcesUnchanged'] or not report['checks']['apkUnchanged']:
            report['status'] = 'FAIL_INTERNAL_UNITY6_94_APK'
            report['errors'].append('Apk94ProtectedInputsOrArtifactChangedDuringInspection')
        report['artifacts'] = [binding(path) for path in sorted(raw.iterdir()) if path.is_file()]
        report['completedUtc'] = datetime.now(timezone.utc).isoformat()
        write(report_path, report)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--execute', action='store_true')
    cli.add_argument('--build', type=Path, required=True)
    args = cli.parse_args()
    if not args.execute or os.name != 'nt':
        cli.error('Explicit root Windows static inspection required; no device or Unity invocation')
    report = inspect(args.build)
    print(json.dumps({'status': report['status'], 'package': report['package'], 'errors': report['errors'], 'warnings': report['warnings']}), flush=True)
    return 0 if report['status'] == 'PASS_INTERNAL_UNITY6_94_APK' else 1


if __name__ == '__main__':
    raise SystemExit(main())
