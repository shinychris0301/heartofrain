"""Read-only SDK36 badging revalidation of the actual successful sixth Unity build.

The original frozen runner/FAIL receipt remains immutable. This performs no Unity
execution and cannot turn a failed native build into a successful build.
"""
import argparse
import json
import re
import subprocess
import uuid
from pathlib import Path

import smoke95

ROOT, EVIDENCE = smoke95.ROOT, smoke95.EVIDENCE
ORIGINAL = EVIDENCE/'SmokeRuns/0a8cfaa4089148eb952594404777fa4d/Invocation.json'
ORIGINAL_SHA = 'a713a28b273e417a64804e858c8808fa3060f66d5c95c353ddc8b304663bdd35'
FLAGS = ('mainInputsUnchanged', 'candidate66InputsUnchanged',
         'externalToolPrefFingerprintsUnchanged', 'embeddedToolMarkersUnchanged')


def need(value, code):
    smoke95.need(value, code)


def checked(item):
    path = Path(item['path']).resolve()
    need(path.is_relative_to(ROOT) and smoke95.binding(path) == item, 'Revalidate97BoundArtifactChanged')
    return path


def validate_original(value):
    need(value.get('status') == 'FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE'
         and value.get('error') == 'Smoke95ActualAPKPackageAndAPIValidationFailed'
         and value.get('exitCode') == 0 and not value.get('timedOut')
         and value.get('actualEngineVersionFromLog') == smoke95.VERSION
         and value.get('nativeStatus') == 'PASS_ACTUAL_LTS95_EMPTY_ANDROID_BUILD'
         and all(value.get(flag) is True for flag in FLAGS)
         and value.get('unityPidsAfter') == [], 'Revalidate97OnlyDemonstratedStaticAliasFailurePermitted')


def validate_manifest(badging, tree):
    packages = re.findall(r"^package: name='([^']+)'", badging, re.M)
    minimum = re.findall(r"^(?:minSdkVersion|sdkVersion):'(\d+)'\s*$", badging, re.M)
    target = re.findall(r"^targetSdkVersion:'(\d+)'\s*$", badging, re.M)
    need(packages == ['com.heartoftherain.toolchain95'] and minimum == ['26'] and target == ['36'],
         'Revalidate97ExactBadgingPackageAndAPIsRequired')
    need(re.findall(r'^\s+A: package="([^"]+)"', tree, re.M) == ['com.heartoftherain.toolchain95']
         and re.findall(r':minSdkVersion\(0x0101020c\)=(\d+)\s*$', tree, re.M) == ['26']
         and re.findall(r':targetSdkVersion\(0x01010270\)=(\d+)\s*$', tree, re.M) == ['36'],
         'Revalidate97IndependentBinaryManifestPackageAndAPIsRequired')
    return {'package': packages[0], 'minSdk': 26, 'targetSdk': 36,
            'sdk36MinSdkVersionAliasAccepted': True, 'independentBinaryManifestCorroborates': True}


def run():
    api, candidate, processes, _, guards = smoke95.readers()
    need(not processes.unity_pids(), 'Revalidate97IdleNativeOwnerRequired')
    need(smoke95.sha(ORIGINAL) == ORIGINAL_SHA, 'Revalidate97ExactOriginalFailureReceiptRequired')
    original = smoke95.read(ORIGINAL); validate_original(original)
    native_path = checked(original['nativeReport']); native = smoke95.read(native_path)
    log_path = checked(original['unityLog']); prepared = checked(original['preparation'])
    need(native.get('status') == 'PASS_ACTUAL_LTS95_EMPTY_ANDROID_BUILD' and not native.get('error')
         and native.get('unity') == smoke95.VERSION and native.get('buildResult') == 'Succeeded'
         and native.get('buildErrors') == 0 and native.get('buildWarnings') == 0
         and native.get('package') == 'com.heartoftherain.toolchain95'
         and native.get('architecture') == 'ARM64' and native.get('backend') == 'IL2CPP'
         and native.get('minSdk') == 26 and native.get('targetSdk') == 36
         and native.get('splash') is False and native.get('unityLogo') is False
         and native.get('preferencesReadOnly') is True and native.get('development') is True,
         'Revalidate97SuccessfulActualNativeBuildAndSettingsRequired')
    need(re.search(r'Initialize engine version:\s*'+re.escape(smoke95.VERSION),
                   log_path.read_text('utf-8-sig', errors='replace')), 'Revalidate97ActualEngineLogRequired')
    apk = Path(native['apk']).resolve(); guards.reject_links(apk)
    need(apk == (smoke95.PRIVATE/'SmokeOutputs'/ORIGINAL.parent.name/'ToolchainSmoke95.apk').resolve(),
         'Revalidate97ExactActualBuildAPKRequired')
    container = smoke95.validate_apk(apk)
    need(container['sha256'] == native['apkSHA256'] and container['bytes'] == native['apkBytes'],
         'Revalidate97ActualBuildAPKBindingRequired')
    main, current66 = smoke95.protected_sources(api, candidate)
    for prefix, current in (('Main', main), ('Candidate66', current66)):
        need(smoke95.read(ORIGINAL.parent/(prefix+'Sources_before.json')) == current
             == smoke95.read(ORIGINAL.parent/(prefix+'Sources_after.json')), 'Revalidate97OriginalAndCurrentSourcesMustMatch')
    prefs = smoke95.external_pref_fingerprints(); tools = smoke95.tool_markers(smoke95.EDITOR)
    need(prefs == smoke95.read(ORIGINAL.parent/'ExternalToolsPrefFingerprints_before.json')
         == smoke95.read(ORIGINAL.parent/'ExternalToolsPrefFingerprints_after.json')
         and tools == original['tools'], 'Revalidate97OriginalAndCurrentPreferencesAndToolBytesMustMatch')
    out = EVIDENCE/'SmokeRuns'/uuid.uuid4().hex; guards.reject_links(out); out.mkdir(exist_ok=False)
    report = {'schemaVersion': 1, 'status': 'RUNNING_READ_ONLY_STATIC_REVALIDATION97', 'startedUtc': api.utc(),
              'runnerSHA256': smoke95.sha(Path(__file__)), 'runner': smoke95.binding(Path(__file__)),
              'kind': 'READ_ONLY_POSTBUILD_SDK36_MINIMUM_API_ALIAS_REVALIDATION',
              'originalFailedInvocation': smoke95.binding(ORIGINAL), 'originalFailurePreserved': True,
              'nativeReport': smoke95.binding(native_path), 'unityLog': smoke95.binding(log_path),
              'preparation': smoke95.binding(prepared), 'nativeBuildReusedWithoutReexecution': True,
              'scope': 'Actual sixth native Unity build succeeded. Fresh stock AAPT2 badging and binary manifest checks repair only the legacy sdkVersion versus SDK36 minSdkVersion text alias. No native rebuild, test waiver, project/tool/preference mutation, installation, game or production acceptance.'}
    api.write(out/'Authorization.json', report)
    try:
        outputs = []
        for name, args in (('Badging.txt', ['dump', 'badging', str(apk)]),
                           ('ManifestTree.txt', ['dump', 'xmltree', str(apk), '--file', 'AndroidManifest.xml'])):
            result = subprocess.run([tools['aapt2']['path'], *args], capture_output=True, text=True,
                                    encoding='utf-8', errors='strict', timeout=45,
                                    creationflags=subprocess.CREATE_NO_WINDOW, check=False)
            need(result.returncode == 0 and not result.stderr.strip(), 'Revalidate97ActualAAPT2MustSucceed')
            (out/name).write_text(result.stdout, encoding='utf-8'); outputs.append(result.stdout)
        validation = validate_manifest(*outputs)
        need(smoke95.binding(ORIGINAL) == report['originalFailedInvocation']
             and smoke95.binding(native_path) == report['nativeReport'] and smoke95.binding(log_path) == report['unityLog']
             and smoke95.validate_apk(apk) == container, 'Revalidate97ActualBuildInputsChanged')
        need((main, current66) == smoke95.protected_sources(api, candidate)
             and prefs == smoke95.external_pref_fingerprints() and tools == smoke95.tool_markers(smoke95.EDITOR)
             and not processes.unity_pids(), 'Revalidate97FinalProtectedInvariantsRequired')
        report.update(status='PASS_ACTUAL_LTS95_TOOLCHAIN_SMOKE_WITH_NO_GAME_ACCEPTANCE', exitCode=0,
                      actualEngineVersionFromLog=smoke95.VERSION, nativeStatus=native['status'],
                      apk=container, apkPath=apk.relative_to(ROOT).as_posix(), badging=smoke95.binding(out/'Badging.txt'),
                      manifestTree=smoke95.binding(out/'ManifestTree.txt'), manifestValidation=validation,
                      smokeAPKNeverInstalled=True, gameAssetsImported=False, externalToolsPreferenceSettersUsed=False,
                      unityPidsAfter=[], **{flag: True for flag in FLAGS})
    except Exception as error:
        report.update(status='FAIL_READ_ONLY_STATIC_REVALIDATION97', errorType=type(error).__name__, error=str(error))
    finally:
        report['finishedUtc'] = api.utc(); api.write(out/'Invocation.json', report)
        print(json.dumps({'status': report['status'], 'report': str(out/'Invocation.json')}), flush=True)
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute or smoke95.os.name != 'nt': parser.error('Explicit Windows read-only revalidation required')
    raise SystemExit(run())
