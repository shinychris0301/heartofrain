"""Prepare-only full-game Yandex8.6 build profile in a fresh ignored clone.

No Unity/Gradle/SDK/app process, downloads, publisher configuration, save files
or credentials are involved. Source Assets/Packages/ProjectSettings are copied
and hash checked. The main project's bytes are never written by this tool.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import uuid
import xml.etree.ElementTree as ET

import prepare_yandex85_sdk as sdk

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = ROOT / '.verification-cache/Ads85'
GAME_PACKAGE = 'com.heartoftherain.ads85review'
EXTENDED = chr(92) * 2 + '?' + chr(92)
SYMBOLS = 'HOTR_YANDEX_ADS;APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED;APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED'
TEMPLATE_PATHS = ('Assets/Plugins/Android/AndroidManifest.xml', 'Assets/Plugins/Android/mainTemplate.gradle',
                  'Assets/Plugins/Android/settingsTemplate.gradle', 'Assets/Plugins/Android/gradleTemplate.properties')


def require(value, code):
    if not value:
        raise ValueError(code)


def io(path):
    value = str(Path(path).resolve())
    return EXTENDED + value if os.name == 'nt' and not value.startswith(EXTENDED) else value


def sha(path):
    digest = hashlib.sha256()
    with open(io(path), 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def files(root):
    for directory, _, names in os.walk(io(root)):
        for name in names:
            yield Path(str(Path(directory) / name).removeprefix(EXTENDED))


def manifest():
    return {p.relative_to(ROOT / 'Unity').as_posix(): {'sha256': sha(p), 'bytes': os.stat(io(p)).st_size}
            for category in ('Assets', 'Packages', 'ProjectSettings') for p in sorted(files(ROOT / 'Unity' / category))}


def put(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(io(path), 'xb') as stream:
        stream.write(data)


def replace_clone(path, data):
    # Caller has already established this is a generated overlay inside a new
    # GameProject cache clone; the original project is never passed here.
    with open(io(path), 'wb') as stream:
        stream.write(data)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def templates():
    """Read the existing reviewed fixture's literal templates as data only."""
    source = HERE / 'prepare_yandex85_sdk.py'
    tree = ast.parse(source.read_text('utf-8'))
    found = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'write'
                and len(node.args) >= 2 and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in TEMPLATE_PATHS and isinstance(node.args[1], ast.Constant)):
            require(node.args[0].value not in found and isinstance(node.args[1].value, str), 'TEMPLATE_LITERAL_AMBIGUOUS')
            found[node.args[0].value] = node.args[1].value
    require(set(found) == set(TEMPLATE_PATHS), 'REVIEWED_TEMPLATE_SET_CHANGED')
    require("com.yandex.android:mobileads:8.6.0" in found[TEMPLATE_PATHS[1]]
            and "io.appmetrica.analytics:analytics:8.6.0" in found[TEMPLATE_PATHS[1]], 'PINNED_DIRECT_DEPENDENCIES_REQUIRED')
    value = found[TEMPLATE_PATHS[0]]
    old = '<activity android:name="com.unity3d.player.UnityPlayerActivity" android:exported="true">'
    require(value.count(old) == 1, 'REVIEWED_ACTIVITY_TEMPLATE_CHANGED')
    # Match the installed Unity default theme and the ordinary game's strict
    # PortraitBuildPolicy. These are the only full-game manifest additions.
    found[TEMPLATE_PATHS[0]] = value.replace(old, '<activity android:name="com.unity3d.player.UnityPlayerActivity" android:exported="true" android:theme="@style/UnityThemeSelector" android:screenOrientation="portrait">')
    return found


def enabled_scenes(data):
    text = data.decode('utf-8-sig')
    records = re.findall(r'(?m)^  - enabled: ([01])\r?\n    path: ([^\r\n]+)\r?\n    guid: ([0-9a-f]{32})', text)
    result = [path for active, path, _ in records if active == '1']
    require(result and len(result) == len(set(result)) and all(path.startswith('Assets/') and '..' not in Path(path).parts for path in result), 'ACTUAL_ENABLED_SCENES_REQUIRED')
    return result


def keep_vendor(logical):
    keep = logical.startswith('Assets/YandexMobileAds/') and not any(logical.startswith(prefix) for prefix in
        ('Assets/YandexMobileAds/Editor', 'Assets/YandexMobileAds/Inspector', 'Assets/YandexMobileAds/Platforms/iOS'))
    keep |= logical.startswith('Assets/AdRevenue/Runtime') and '/iOS' not in logical
    keep |= logical == 'Assets/Plugins/Android/yandex-ads-unity-plugin.aar'
    return keep


def prepare(project, package):
    project = project.resolve()
    require(project.parent == CACHE.resolve() and re.fullmatch(r'(?:GameProject_[0-9a-f]{32}|G85_[0-9a-f]{8})', project.name), 'NEW_GAMEPROJECT_CACHE_NAME_REQUIRED')
    require(not project.exists(), 'PRESERVE_EXISTING_GAME_PROJECT')
    require('m_EditorVersion: 2022.3.62f3' in (ROOT / 'Unity/ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig'), 'PINNED_ENGINE_REQUIRED')
    vendor = sdk.asset_entries(package)  # exact official package SHA/inventory/link/path/size validation
    source = manifest(); require(source, 'CURRENT_SOURCE_REQUIRED')
    project.mkdir(parents=True, exist_ok=False)
    report_path = project.parent / (project.name + '_Preparation.json')
    result = {'status': 'FAIL_PREPARE_ISOLATED_YANDEX85_FULL_GAME', 'project': project.relative_to(ROOT).as_posix(),
              'package': GAME_PACKAGE, 'unity': '2022.3.62f3', 'configurationProvisioned': False, 'apkLaunched': False,
              'vendorPackageSHA256': sdk.PACKAGE_SHA256, 'sourceInputCount': len(source), 'sourceInputs': source,
              'copiedMainSHA256': {}, 'copiedVendorSHA256': {}, 'omittedVendorLogicalPaths': [], 'generatedSHA256': {}, 'overlayBeforeSHA256': {},
              'helperSHA256': sha(Path(__file__)), 'sharedSdkPreparationSHA256': sha(HERE / 'prepare_yandex85_sdk.py'),
              'gameExportHelperSHA256': sha(HERE / 'Yandex85GameExport.cs'),
              'scope': 'Preparation-only full current game clone, unmodified official vendor Android subset, no vendor Editor hooks, explicit disabled-autoinit/no-location/no-ADID manifest. All source artwork/meta/GUID bytes preserved. No Library/Temp/Builds/UserSettings/saves copied. No executable/build/SDK/ad/network/credential/config activation or full-game compatibility success inferred.'}
    try:
        guids = {}
        for relative, record in source.items():
            original = ROOT / 'Unity' / relative; target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(io(original), 'rb') as src, open(io(target), 'xb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            require(sha(target) == record['sha256'], 'SOURCE_CHANGED_DURING_COPY')
            result['copiedMainSHA256'][relative] = record['sha256']
            if relative.endswith('.meta'):
                with open(io(target), 'rb') as stream:
                    match = re.search(rb'(?m)^guid: ([0-9a-f]{32})\r?$', stream.read())
                if match:
                    require(match[1] not in guids, 'MAIN_SOURCE_GUID_COLLISION')
                    guids[match[1]] = relative
        for logical, guid, asset, metadata in vendor:
            if not keep_vendor(logical):
                result['omittedVendorLogicalPaths'].append(logical); continue
            if metadata is not None:
                require(guid.encode('ascii') not in guids, 'VENDOR_GUID_COLLIDES_WITH_MAIN')
                require(re.search(rb'(?m)^guid: ' + guid.encode('ascii') + rb'\r?$', metadata) is not None, 'VENDOR_GUID_METADATA_MISMATCH')
                guids[guid.encode('ascii')] = logical + '.meta'
            for suffix, data in (('', asset), ('.meta', metadata)):
                if data is None:
                    continue
                relative = logical + suffix; target = project / relative
                require(not target.exists(), 'VENDOR_PATH_COLLIDES_WITH_MAIN')
                put(target, data); result['copiedVendorSHA256'][relative] = hashlib.sha256(data).hexdigest()

        def overlay(relative, data, meta=False):
            target = project / relative
            if target.exists():
                result['overlayBeforeSHA256'][relative] = sha(target); replace_clone(target, data)
            else:
                put(target, data)
            result['generatedSHA256'][relative] = hashlib.sha256(data).hexdigest()
            if meta and not (project / (relative + '.meta')).exists():
                overlay(relative + '.meta', ('fileFormatVersion: 2\nguid: ' + uuid.uuid5(uuid.NAMESPACE_URL, 'hotr-ads85-full-game/' + relative).hex + '\n').encode('ascii'))

        for relative, value in templates().items():
            overlay(relative, value.encode('utf-8'), True)
        response_path = project / 'Assets/csc.rsp'
        response = response_path.read_bytes() if response_path.exists() else b''
        require(b'HOTR_YANDEX_ADS_ISOLATED_FIXTURE' not in response, 'NO_DEMO_FIXTURE_DEFINE_IN_GAME')
        overlay('Assets/csc.rsp', response.rstrip() + b'\n-define:' + SYMBOLS.encode('ascii') + b'\n', True)
        settings_path = project / 'ProjectSettings/ProjectSettings.asset'
        settings = settings_path.read_text('utf-8-sig')
        require('HOTR_YANDEX_ADS_ISOLATED_FIXTURE' not in settings, 'NO_GAME_FIXTURE_SYMBOLS')
        for key in ('useCustomMainManifest', 'useCustomMainGradleTemplate', 'useCustomGradlePropertiesTemplate', 'useCustomGradleSettingsTemplate'):
            settings, count = re.subn(r'(?m)^(  ' + key + r':) [01]\r?$', r'\g<1> 1', settings)
            require(count == 1, 'EXPLICIT_GAME_TEMPLATE_SETTING_MISSING')
        overlay('ProjectSettings/ProjectSettings.asset', settings.encode('utf-8'))
        overlay('Assets/Editor/Yandex85GameExport.cs', (HERE / 'Yandex85GameExport.cs').read_bytes(), True)
        scene_bytes = (project / 'ProjectSettings/EditorBuildSettings.asset').read_bytes(); scenes = enabled_scenes(scene_bytes)
        require(all((project / scene).is_file() for scene in scenes), 'ENABLED_SCENE_NOT_COPIED')
        profile = {'version': 1, 'package': GAME_PACKAGE, 'configurationProvisioned': False, 'enabledScenes': scenes}
        overlay('GameAds85Profile.json', json_bytes(profile))
        put(project / 'SourceInputs.json', json_bytes(source))
        result['sourceManifestSHA256'] = sha(project / 'SourceInputs.json'); result['enabledScenes'] = scenes
        result['mainSourceUnchanged'] = manifest() == source
        require(result['mainSourceUnchanged'], 'MAIN_CHANGED_DURING_PREPARATION')
        for relative, expected in result['copiedMainSHA256'].items():
            if relative not in result['generatedSHA256']:
                require(sha(project / relative) == expected, 'ORIGINAL_CLONE_BYTES_CHANGED')
        adapter = 'Assets/HeartOfTheRain/App/Advertising/Runtime/YandexRewardedAdsProvider85.cs'
        require(adapter in result['copiedMainSHA256'], 'ACTUAL_GAME_ADAPTER_REQUIRED')
        result['actualGameAdapterSourceSHA256'] = sha(project / adapter)
        result['originalMetaGUIDBytesPreserved'] = all(sha(project / relative) == record['sha256'] for relative, record in source.items() if relative.endswith('.meta'))
        require(result['originalMetaGUIDBytesPreserved'], 'ORIGINAL_META_BYTES_CHANGED')
        result['profile'] = {'minSdk': 26, 'targetSdk': 35, 'compileSdk': 35, 'architecture': 'ARM64', 'scriptingBackend': 'IL2CPP', 'developmentOnly': True,
                             'publisherUnitProvisioned': False, 'sdkAutoInit': False, 'locationPermissionsRemoved': True, 'adIdPermissionRemoved': True,
                             'defines': SYMBOLS.split(';'), 'embeddedEditorJava': '11', 'externalAgp': '8.7.0', 'externalGradle': '8.9', 'externalJava': '17', 'appMetrica': '8.6.0'}
        put(project / 'ROOT_BUILD_INSTRUCTIONS.txt', instructions(project).encode('utf-8'))
        result['instructionsSHA256'] = sha(project / 'ROOT_BUILD_INSTRUCTIONS.txt')
        result['status'] = 'PREPARED_ISOLATED_YANDEX85_FULL_GAME_NOT_BUILT'
    except Exception as error:
        result['errorCode'] = str(error) if isinstance(error, ValueError) else type(error).__name__
        raise
    finally:
        put(report_path, json_bytes(result))
    return result


def prepare_modern(project):
    """Derive files only; root separately invokes the explicit Java17 tools."""
    import run_yandex85_sdk_build as build
    project = project.resolve()
    require(project.parent == CACHE.resolve() and re.fullmatch(r'(?:GameProject_[0-9a-f]{32}|G85_[0-9a-f]{8})', project.name), 'ISOLATED_GAME_PROJECT_REQUIRED')
    prepared = json.loads((project.parent / (project.name + '_Preparation.json')).read_text('utf-8'))
    require(prepared['status'] == 'PREPARED_ISOLATED_YANDEX85_FULL_GAME_NOT_BUILT', 'GAME_PREPARATION_REQUIRED')
    report_path = project / 'GameAndroidExport.json'; exported = json.loads(report_path.read_text('utf-8'))
    require(exported['status'] == 'PASS_ISOLATED_YANDEX85_GAME_GRADLE_EXPORT' and exported['jdkSettingsUnchanged'] and exported['actualAdapterSdkBranchCompiled'] and exported['enabledScenesUnchanged'], 'ACTUAL_FULL_GAME_EXPORT_REQUIRED')
    export = project / 'Build/GameGradleExport'; target = project / 'Build/GameGradleModern'
    expected = {row['path']: row['sha256'] for row in exported['exportBindings']}
    require({p.relative_to(export).as_posix(): sha(p) for p in files(export)} == expected, 'GAME_EXPORT_INPUT_CHANGED')
    changes = build.modern_profile(export, target)
    modules = []
    for gradle in sorted(files(target)):
        relative = gradle.relative_to(target).as_posix()
        if gradle.name != 'build.gradle' or '/build/' in '/' + relative or '/.gradle/' in '/' + relative:
            continue
        text = gradle.read_text('utf-8')
        if not re.search(r"(?:apply plugin:\s*|id\s*)['\"](?:com\.android\.(?:library|application)|android-library)['\"]", text) or not re.search(r'\bandroid\s*\{', text):
            continue
        candidates = [path for path in (gradle.parent / 'src/main/AndroidManifest.xml', gradle.parent / 'AndroidManifest.xml') if path.is_file()]
        namespace = re.search(r'\bnamespace\s+["\']([A-Za-z_][A-Za-z0-9_.]*)["\']', text)
        packages = {ET.fromstring(path.read_bytes()).attrib.get('package') for path in candidates} - {None}
        require(len(packages) <= 1, 'ANDROID_MODULE_MANIFEST_PACKAGE_AMBIGUOUS')
        package = namespace[1] if namespace else next(iter(packages), None)
        require(package and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+', package), 'EXISTING_ANDROID_MODULE_NAMESPACE_REQUIRED')
        if not namespace:
            before = sha(gradle); text, count = re.subn(r'\bandroid\s*\{', 'android {\n    namespace "' + package + '"', text, count=1)
            require(count == 1, 'ONE_ANDROID_MODULE_BLOCK_REQUIRED'); replace_clone(gradle, text.encode('utf-8'))
            changes.append({'path': relative, 'beforeSHA256': before, 'afterSHA256': sha(gradle), 'reason': 'Namespace derived from existing plugin manifest package'})
        for path in candidates:
            declared = ET.fromstring(path.read_bytes()).attrib.get('package')
            if declared is None:
                continue
            require(declared == package, 'ANDROID_NAMESPACE_PACKAGE_MISMATCH')
            before = sha(path); value, count = re.subn(r'\s+package\s*=\s*["\']' + re.escape(declared) + r'["\']', '', path.read_text('utf-8'), count=1)
            require(count == 1, 'ONE_MANIFEST_PACKAGE_REQUIRED'); replace_clone(path, value.encode('utf-8'))
            changes.append({'path': path.relative_to(target).as_posix(), 'beforeSHA256': before, 'afterSHA256': sha(path), 'reason': 'AGP8 namespace already explicitly matches original manifest package'})
        modules.append({'module': gradle.parent.relative_to(target).as_posix(), 'namespace': package})
    require(any('HeartOfTheRainIdentity82.androidlib' in row['module'] for row in modules), 'FULL_GAME_IDENTITY_ANDROID_MODULE_REQUIRED')
    result = {'status': 'PREPARED_FULL_GAME_MODERN_GRADLE_NOT_ASSEMBLED', 'package': GAME_PACKAGE, 'exportReportSHA256': sha(report_path),
              'preparationSHA256': sha(project.parent / (project.name + '_Preparation.json')), 'helperSHA256': sha(Path(__file__)),
              'sharedModernHelperSHA256': sha(HERE / 'run_yandex85_sdk_build.py'), 'changes': changes, 'modules': modules,
              'derivedProfileSHA256': {p.relative_to(target).as_posix(): sha(p) for p in sorted(files(target))},
              'scope': 'File derivation only: AGP7.4.2→8.7.0, old AAPT2 override removed, existing package→explicit namespace for every actual Android module. No Gradle/JDK invocation, download, build or compatibility success inferred.'}
    put(project / 'GameModernPreparation.json', json_bytes(result))
    return result


def instructions(project):
    return f'''ROOT-ONLY PREPARATION; NOTHING HAS BEEN BUILT OR LAUNCHED.
Project: {project}
Default clone name is short G85_<8 lowercase hex> to avoid Windows MAX_PATH;
the longer GameProject_<32 lowercase hex> format remains accepted for existing profiles.
Internal package: {GAME_PACKAGE}; product name/art/scenes remain the current game.
No publisher unit, advertising config, server config, consent or payment identity is provisioned.
Never install this profile over the ordinary package. Do not use fixture/demo unit defines.

1. Wait for all source owners to HOLD and no other Unity process. Validate the sibling
   {project.name}_Preparation.json plus SourceInputs.json and all vendor/generated hashes.
2. Run the pinned Editor with its embedded Java11 (do NOT set JDK17 in Unity):
   Unity.exe -batchmode -projectPath "{project}" -buildTarget Android -executeMethod Yandex85GameExport.Run -logFile "<fresh owned export log>"
   No -quit or -nographics. Root must enforce a hidden owned-process timeout and capture PID/log/exit.
   Bound SDKMANAGER_OPTS remote-query timeouts/proxies as in the reviewed isolated SDK runner;
   restore the prior process environment afterward. Do not alter global JAVA_HOME or Editor JDK settings.
   Require GameAndroidExport.json PASS_ISOLATED_YANDEX85_GAME_GRADLE_EXPORT, unchanged JDK,
   real enabled scenes, portrait, unchanged Russian product name and actual SDK adapter compile flag.
3. PREPARE ONLY the separate modern export after that real PASS:
   Backend/.venv/Scripts/python.exe Verification/Tools/Ads85/prepare_yandex85_game.py --project "{project}" --prepare-modern-profile
   This uses the reviewed stock→modern derivation plus explicit namespaces for actual .androidlib modules
   and the shared modern helper's legacy android.ndkDirectory→explicit android.ndkPath replacement.
   The installed NDK is preserved; no engine/NDK/SDK upgrade is performed.
   It writes GameModernPreparation.json and Build/GameGradleModern; never reuses an existing export.
4. Root separately runs explicit external Temurin17 and Gradle8.9 with AGP8.7.0 against that derived
   profile using the reviewed GradleDependencyLocking85.gradle init script, --no-daemon, --write-locks
   and bounded hidden processes. Pin/hash JDK release, Gradle launcher, resolved dependency locks,
   all process logs, merged manifests, native libraries and final APK. Do not invoke the SDK-fixture
   run_yandex85_sdk_build.py CLI directly: its package/status checks intentionally reject a full game.
5. Build-only success does not verify an ad impression, publisher revenue, reward-provider callback,
   account lifecycle, game rendering, configured ordinary startup or production readiness. Those need
   separately authorized tests. No app launch/install/ad request is part of this preparation recipe.
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--package', type=Path, default=sdk.PACKAGE)
    parser.add_argument('--prepare-modern-profile', action='store_true')
    args = parser.parse_args()
    project = args.project or CACHE / ('G85_' + uuid.uuid4().hex[:8])
    result = prepare_modern(project) if args.prepare_modern_profile else prepare(project, args.package)
    print(json.dumps({'status': result['status'], 'project': project.resolve().relative_to(ROOT).as_posix()}))


if __name__ == '__main__':
    main()
