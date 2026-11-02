"""Prepare an isolated, never-auto-loading Yandex 8.6.0 SDK build project.

This reads a hash-pinned official unitypackage as data. It never imports the
package into the ordinary project, executes vendor scripts, runs Unity/Gradle,
downloads tools, launches an app or requests an advertisement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = ROOT / '.verification-cache/Ads85'
PACKAGE_SHA256 = '0d0a2546dd752d6b02864df5833767703ae88d5b292da0e0b8eec815d7f066c3'
PACKAGE = CACHE / 'Vendor/yandex-mobileads-lite-8.6.0.unitypackage'
FIXTURE_PACKAGE = 'com.heartoftherain.yandex85sdkfixture'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def require(condition, code):
    if not condition:
        raise ValueError(code)


def asset_entries(package):
    """Bounded extraction plan, not tarfile.extract: reject links/collisions."""
    require(file_sha(package) == PACKAGE_SHA256, 'VENDOR_PACKAGE_HASH_MISMATCH')
    records, total = {}, 0
    with tarfile.open(package, 'r:gz') as archive:
        for member in archive.getmembers():
            relative = PurePosixPath(member.name)
            require(not relative.is_absolute() and '..' not in relative.parts and '\\' not in member.name, 'VENDOR_TAR_PATH_REJECTED')
            require(member.isdir() or member.isfile(), 'VENDOR_LINK_OR_SPECIAL_FILE_REJECTED')
            if member.isdir():
                continue
            require(0 <= member.size <= 16 * 1024 * 1024, 'VENDOR_MEMBER_TOO_LARGE')
            total += member.size
            require(total <= 128 * 1024 * 1024, 'VENDOR_UNPACKED_LIMIT')
            key = relative.as_posix()
            require(key not in records, 'VENDOR_TAR_DUPLICATE')
            records[key] = archive.extractfile(member).read()
    entries, used = [], set()
    for key, value in records.items():
        if not key.endswith('/pathname'):
            continue
        guid = key.split('/')[0]
        require(re.fullmatch('[0-9a-f]{32}', guid) is not None, 'VENDOR_GUID_INVALID')
        logical = value.decode('utf-8-sig').rstrip('\r\n\0')
        relative = PurePosixPath(logical)
        require(relative.parts and relative.parts[0] == 'Assets' and not relative.is_absolute() and '..' not in relative.parts and '\\' not in logical and ':' not in logical, 'VENDOR_ASSET_PATH_REJECTED')
        require(logical.casefold() not in used, 'VENDOR_CASE_COLLISION')
        used.add(logical.casefold())
        entries.append((logical, guid, records.get(guid + '/asset'), records.get(guid + '/asset.meta')))
    require(len(entries) == 256, 'PINNED_VENDOR_INVENTORY_CHANGED')
    return entries


def generated_meta(relative):
    guid = uuid.uuid5(uuid.NAMESPACE_URL, 'hotr-ads85-sdk-fixture/' + relative).hex
    return ('fileFormatVersion: 2\nguid: ' + guid + '\n').encode('ascii')


def prepare(project, package=PACKAGE, integration=()):
    project = project.resolve()
    require(project.is_relative_to(CACHE.resolve()) and project != CACHE.resolve(), 'ISOLATED_CACHE_PROJECT_REQUIRED')
    require(not project.exists(), 'PRESERVE_EXISTING_FIXTURE_PROJECT')
    entries = asset_entries(package)
    project.mkdir(parents=True)
    copied, omitted, generated, main_sources = {}, [], {}, {}
    for logical, guid, asset, metadata in entries:
        # Android runtime subset: no vendor Editor hooks/resolver/auto-define
        # mutation, inspector components or iOS implementation is needed.
        keep = (logical.startswith('Assets/YandexMobileAds/') and not any(
            logical.startswith(prefix) for prefix in ('Assets/YandexMobileAds/Editor', 'Assets/YandexMobileAds/Inspector', 'Assets/YandexMobileAds/Platforms/iOS')))
        keep |= logical.startswith('Assets/AdRevenue/Runtime') and '/iOS' not in logical
        keep |= logical == 'Assets/Plugins/Android/yandex-ads-unity-plugin.aar'
        if not keep:
            omitted.append(logical)
            continue
        for suffix, value in (('', asset), ('.meta', metadata)):
            if value is None:
                continue
            relative = logical + suffix
            target = project / relative
            require(target.resolve().is_relative_to(project), 'FIXTURE_COPY_ESCAPED')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value)
            copied[relative] = sha(value)

    def write(relative, text, metadata=False):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data = text.encode('utf-8') if isinstance(text, str) else text
        path.write_bytes(data)
        generated[relative] = sha(data)
        if metadata:
            write(relative + '.meta', generated_meta(relative))

    for source in integration:
        source = source.resolve()
        require(source.is_relative_to((ROOT / 'Unity/Assets/HeartOfTheRain/App/Advertising').resolve()) and source.is_file() and source.suffix == '.cs', 'ONLY_EXPLICIT_ADVERTISING_SOURCE_ALLOWED')
        relative = 'Assets/Integration/' + source.name
        require(relative not in generated, 'INTEGRATION_FILENAME_COLLISION')
        write(relative, source.read_bytes(), True)
        main_sources[source.relative_to(ROOT).as_posix()] = file_sha(source)
    write('Assets/Editor/Yandex85SdkExport.cs', (HERE / 'Yandex85SdkExport.cs').read_bytes(), True)
    write('Assets/Fixture/Yandex85ApiReference.cs', (HERE / 'Yandex85ApiReference.cs').read_bytes(), True)
    write('Assets/csc.rsp', '-define:HOTR_YANDEX_ADS;HOTR_YANDEX_ADS_ISOLATED_FIXTURE;APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED;APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED\n')
    version_source = ROOT / 'Unity/ProjectSettings/ProjectVersion.txt'
    require('m_EditorVersion: 2022.3.62f3' in version_source.read_text('utf-8'), 'PINNED_PROJECT_VERSION_REQUIRED')
    write('ProjectSettings/ProjectVersion.txt', version_source.read_bytes())
    settings_source = ROOT / 'Unity/ProjectSettings/ProjectSettings.asset'
    settings = settings_source.read_text('utf-8')
    for key in ('useCustomMainManifest', 'useCustomMainGradleTemplate', 'useCustomGradlePropertiesTemplate', 'useCustomGradleSettingsTemplate'):
        settings, count = re.subn(r'(?m)^(  ' + key + r':) [01]$', r'\g<1> 1', settings)
        require(count == 1, 'EXPLICIT_ISOLATED_TEMPLATE_SETTING_MISSING')
    symbols = 'HOTR_YANDEX_ADS;HOTR_YANDEX_ADS_ISOLATED_FIXTURE;APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED;APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED'
    settings, count = re.subn(r'(?m)^  scriptingDefineSymbols: \{\}$', '  scriptingDefineSymbols:\n    Android: ' + symbols, settings)
    require(count == 1, 'REVIEW_ISOLATED_DEFINE_BASELINE_BEFORE_COPY')
    write('ProjectSettings/ProjectSettings.asset', settings)
    manifest = {'dependencies': {'com.unity.modules.androidjni': '1.0.0', 'com.unity.modules.jsonserialize': '1.0.0'}}
    write('Packages/manifest.json', json.dumps(manifest, indent=2) + '\n')
    write('Assets/Plugins/Android/AndroidManifest.xml', '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" xmlns:tools="http://schemas.android.com/tools">
  <uses-permission android:name="android.permission.INTERNET" />
  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" tools:node="remove" />
  <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" tools:node="remove" />
  <uses-permission android:name="com.google.android.gms.permission.AD_ID" tools:node="remove" />
  <application android:usesCleartextTraffic="false">
    <meta-data android:name="com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION" android:value="false" tools:replace="android:value" />
    <activity android:name="com.unity3d.player.UnityPlayerActivity" android:exported="true">
      <intent-filter><action android:name="android.intent.action.MAIN" /><category android:name="android.intent.category.LAUNCHER" /></intent-filter>
      <meta-data android:name="unityplayer.UnityActivity" android:value="true" />
    </activity>
  </application>
</manifest>
''', True)
    write('Assets/Plugins/Android/mainTemplate.gradle', '''apply plugin: 'com.android.library'
**APPLY_PLUGINS**
dependencies {
    implementation fileTree(dir: 'libs', include: ['*.jar'])
    implementation 'com.yandex.android:mobileads:8.6.0'
    implementation 'androidx.lifecycle:lifecycle-process:2.4.1'
    implementation 'io.appmetrica.analytics:analytics:8.6.0'
**DEPS**}
dependencyLocking { lockAllConfigurations() }
android {
    namespace "com.unity3d.player"
    ndkPath "**NDKPATH**"
    compileSdkVersion **APIVERSION**
    buildToolsVersion '**BUILDTOOLS**'
    compileOptions { sourceCompatibility JavaVersion.VERSION_11; targetCompatibility JavaVersion.VERSION_11 }
    defaultConfig {
        minSdkVersion **MINSDKVERSION**
        targetSdkVersion **TARGETSDKVERSION**
        ndk { abiFilters **ABIFILTERS** }
        versionCode **VERSIONCODE**
        versionName '**VERSIONNAME**'
        consumerProguardFiles 'proguard-unity.txt'**USER_PROGUARD**
    }
    lintOptions { abortOnError false }
    aaptOptions {
        noCompress = **BUILTIN_NOCOMPRESS** + unityStreamingAssets.tokenize(', ')
        ignoreAssetsPattern = "!.svn:!.git:!.ds_store:!*.scc:!CVS:!thumbs.db:!picasa.ini:!*~"
    }**PACKAGING_OPTIONS**
}
**IL_CPP_BUILD_SETUP**
**SOURCE_BUILD_SETUP**
**EXTERNAL_SOURCES**
''', True)
    write('Assets/Plugins/Android/settingsTemplate.gradle', '''pluginManagement {
    repositories { **ARTIFACTORYREPOSITORY**
        gradlePluginPortal(); google(); mavenCentral()
    }
}
include ':launcher', ':unityLibrary'
**INCLUDES**
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories { **ARTIFACTORYREPOSITORY**
        google(); mavenCentral()
        flatDir { dirs "${project(':unityLibrary').projectDir}/libs" }
    }
}
''', True)
    write('Assets/Plugins/Android/gradleTemplate.properties', 'org.gradle.jvmargs=-Xmx**JVM_HEAP_SIZE**M\norg.gradle.parallel=false\nunityStreamingAssets=**STREAMING_ASSETS**\n**ADDITIONAL_PROPERTIES**\nandroid.useAndroidX=true\nandroid.enableJetifier=true\n', True)
    report = {'status': 'PREPARED_ISOLATED_YANDEX85_SDK_NOT_BUILT', 'unity': '2022.3.62f3', 'package': FIXTURE_PACKAGE,
              'vendorPackageSHA256': PACKAGE_SHA256, 'vendorVersion': '8.6.0', 'project': project.relative_to(ROOT).as_posix(),
              'copiedVendorSHA256': copied, 'omittedVendorLogicalPaths': omitted, 'generatedSHA256': generated,
              'copiedMainIntegrationSHA256': main_sources,
              'mainSettingsSourceSHA256': file_sha(settings_source), 'projectVersionSourceSHA256': file_sha(version_source),
              'profile': {'minSdk': 26, 'targetSdk': 35, 'compileSdk': 35, 'stockAgp': '7.4.2', 'stockGradle': '7.5.1', 'modernAgp': '8.7.0', 'modernGradle': '8.9', 'modernJava': '17', 'appMetricaPin': '8.6.0'},
              'scope': 'Exact official Android runtime/plugin bytes, explicit dependencies replacing omitted vendor Editor resolver/hooks. No SDK initialization/load/show, no main project import, no rewards, no app launch, no build or compatibility success inferred.'}
    path = project.parent / (project.name + '_Preparation.json')
    path.write_text(json.dumps(report, indent=2) + '\n', 'utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=CACHE / 'SdkProject')
    parser.add_argument('--package', type=Path, default=PACKAGE)
    parser.add_argument('--integration', type=Path, action='append', default=[])
    args = parser.parse_args()
    result = prepare(args.project, args.package, args.integration)
    print(json.dumps({key: result[key] for key in ('status', 'project', 'vendorPackageSHA256')}))


if __name__ == '__main__':
    main()
