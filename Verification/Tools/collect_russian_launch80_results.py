"""Validate current Russian launch R3 evidence; read-only unless --publish is explicit.

This collector checks actual source/build/native/device/reviewer records. It
does not run Unity, a packaging tool, ADB, or infer visual approval from tests.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/LaunchRuStoreR3'
PRIOR = ROOT / 'Verification/Evidence/Gameplay79'
NAME = '\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f'
STATUS = 'PASS_RUSSIAN_BRANDING_WITH_UNITY_SPLASH_LICENSE_GATE'
PREFIX = 'Unity/Assets/HeartOfTheRain/'
CHANGED = {PREFIX + p for p in (
    'App/AppSettings/Runtime/AppSettingsLayout.cs',
    'App/AppSettings/Runtime/AppSettingsSession.cs',
    'App/FirstStart/Runtime/FirstStartLayout.cs',
    'App/Launch/Editor/LaunchSetup.cs', 'App/Launch/Scenes/Launch.unity',
    'App/Localization/Runtime/GameLocale.cs', 'App/Localization/Runtime/LocaleBootstrap.cs',
    'App/UIClarity/Editor/UIClarityRegistry.json',
    'Verification/Editor/LaunchReview.cs', 'Verification/Editor/NativeAndroidBuild.cs',
)} | {'Unity/ProjectSettings/ProjectSettings.asset'}
ADDED = {PREFIX + p + suffix for p in (
    'App/Launch/Art/Title_Logo_RU_R1.png',
    'Verification/Editor/RussianLaunch80Configuration.cs',
    'Verification/Editor/RussianLocale80Verification.cs',
) for suffix in ('', '.meta')}
SUITES = {
    'Locale': ('Native/Locale80.json', 'PASS_NATIVE_RUSSIAN_LOCALE80', 580),
    'Launch': ('Native/Launch/Native_Review.json', 'PASS_NATIVE_LAUNCH_INTEGRATION', 409),
    'Checks': ('Native/Checks.json', 'PASS_NATIVE_EDITOR_CHECKS', 534),
    'ProfileChecks': ('Native/ProfileChecks.json', 'PASS_NATIVE_PROFILE_TRANSACTIONS', 13584),
    'PlaySmoke': ('Native/PlaySmoke.json', 'PASS_NATIVE_PLAY_SMOKE', 18),
    'PortraitChecks': ('Native/PortraitChecks.json', 'PASS_NATIVE_PORTRAIT_CHECKS', 18),
}


def need(value, message):
    if not value:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def clean(value, label):
    need(not any(value.get(k) for k in ('error', 'errors', 'failures', 'failed')), label + ' contains failures')


class Proof:
    def __init__(self):
        self.artifacts = {}
        self.external = {}

    def file(self, name):
        p = (OUT / name).resolve()
        need(p.is_relative_to(OUT.resolve()) and p.is_file(), 'Missing/unsafe current proof: ' + name)
        self.artifacts[p.relative_to(OUT).as_posix()] = sha(p)
        return p

    def read(self, name):
        return json.loads(self.file(name).read_text('utf-8-sig'))

    def external_file(self, name, expected=None):
        p = (ROOT / name).resolve()
        need(p.is_relative_to(ROOT.resolve()) and p.is_file(), 'Missing/unsafe external proof: ' + name)
        digest = sha(p)
        need(expected is None or expected == digest, 'Changed external proof: ' + name)
        self.external[p.relative_to(ROOT).as_posix()] = digest
        return p


def count_checks(report):
    if 'passed' in report:
        return report['passed']
    value = report['checks']
    return len(value) if isinstance(value, list) else value


def validate_process(proof, name, report_name, current, frozen_utc, configure=False, build=False):
    run = proof.read('Native/' + name + '_Process.json')
    report = proof.read(report_name)
    clean(report, name)
    before = proof.read(run['sourceManifest'])
    after = proof.read(run['afterSourceManifest'])
    need(run['mode'] == name and run['exitCode'] == 0 and run['timedOut'] is False
         and run['version'].startswith('2022.3.62f3'), name + ' did not pass pinned Unity')
    need(run['inputCount'] == 5165 and before['files'] == after['files'] == current,
         name + ' source files differ from the final freeze')
    need(sha(proof.file(run['sourceManifest'])) == run['sourceSHA256']
         and sha(proof.file(run['afterSourceManifest'])) == run['afterSourceSHA256'],
         name + ' manifest hash mismatch')
    need(utc(before['utc']) <= utc(run['startedUtc']) <= utc(report['utc'])
         <= utc(after['utc']) <= utc(run['finishedUtc']), name + ' source/report chronology differs')
    need((utc(run['finishedUtc']) <= frozen_utc) if configure else (frozen_utc <= utc(run['startedUtc'])),
         name + ' ran on the wrong side of the final post-Configure freeze')
    need(run['report'] == report_name and run['reportSHA256'] == sha(proof.file(report_name)),
         name + ' report hash binding differs')
    need(run['logSHA256'] == sha(proof.file(run['log'])), name + ' log hash binding differs')
    need(run['intentionalConfigurationMutation'] is configure
         and run['temporaryBuildSettingsRestored'] is build
         and run['historicalReportsRestored'] is True, name + ' restoration scope differs')
    delta = proof.read('Native/' + name + '_Input_Delta.json')
    need(not any(delta.values()), name + ' changed frozen inputs')
    delegated = run['delegatedProcess']
    if delegated:
        need(delegated['mode'] == name and delegated['exitCode'] == 0 and delegated['timedOut'] is False
             and delegated['version'].startswith('2022.3.62f3')
             and utc(run['startedUtc']) <= utc(delegated['startedUtc']) <= utc(report['utc'])
             <= utc(delegated['finishedUtc']) <= utc(run['finishedUtc']), name + ' delegated chronology differs')
        # These are original files copied before historical reports were restored.
        # The first runner had a PowerShell array-expression bug in its optional
        # root-mirror copy; the correctly captured originals remain authoritative.
        captured = 'Native/' + name + '/Artifacts/Native/' + name
        need(proof.read(captured + '_Process.json') == delegated,
             name + ' captured original delegated process differs')
        need(sha(proof.file(captured + '.log')) == run['logSHA256'],
             name + ' captured original log differs')
    need(configure or name in ('Locale', 'Launch') or delegated is not None,
         name + ' missing delegated native process')
    if report.get('unity'):
        need(report['unity'] == '2022.3.62f3', name + ' report editor differs')
    return report, run


def validate_review(proof, name, source_digest, required, apk_digest=None):
    value = proof.read(name)
    status = value.get('status', '')
    need('REVIEW' in status and not status.startswith('FAIL') and value.get('scope')
         and value.get('limitations'), 'Missing actual bounded reviewer scope: ' + name)
    need(value['source_sha256'] == source_digest, 'Reviewer source mismatch: ' + name)
    if apk_digest is not None:
        need(value['apk_sha256'] == apk_digest, 'Reviewer APK mismatch: ' + name)
    bindings = value['artifactSHA256']
    need(bindings and set(required) <= bindings.keys(), 'Reviewer omitted required actual captures: ' + name)
    for path, digest in bindings.items():
        need(sha(proof.file(path)) == digest, 'Reviewer artifact changed: ' + name + '/' + path)
    for path, digest in value.get('externalEvidenceSHA256', {}).items():
        proof.external_file(path, digest)
    inspected = value.get('inspected', value.get('actualInspected', []))
    need(inspected and set(required) <= set(inspected), 'Reviewer did not record inspection of required captures: ' + name)
    return value


def build():
    proof = Proof()
    source = proof.read('Source_SHA256.json')
    current = {p.relative_to(ROOT).as_posix(): sha(p) for folder in ('Assets', 'Packages', 'ProjectSettings')
               for p in (ROOT / 'Unity' / folder).rglob('*') if p.is_file()}
    need(source['files'] == current and len(current) == 5165, 'Final frozen inputs changed')
    source_digest = sha(proof.file('Source_SHA256.json'))
    baseline = proof.read('Baseline79.json')
    old_source = proof.read('Baseline79_Source_SHA256.json')
    old_summary = proof.read('Baseline79_Summary.json')
    old_artifact = proof.read('Baseline79_APK_Artifact.json')
    need(baseline['checkpoint'] == old_summary['source_checkpoint'] == 79
         and old_summary['status'] == 'PASS_TARGETED_STARTUP79_WITH_REMAINING_PERFORMANCE_GATES'
         and old_summary['native_checks'] == 976622 and len(old_source['files']) == 5159,
         'Sealed79 baseline scope differs')
    need(baseline['sourceSHA256'] == sha(proof.file('Baseline79_Source_SHA256.json'))
         == sha(proof.external_file('Verification/Evidence/Gameplay79/Source_SHA256.json')),
         'Sealed79 source changed')
    need(baseline['summarySHA256'] == sha(proof.file('Baseline79_Summary.json'))
         == sha(proof.external_file('Verification/Evidence/Gameplay79/Summary.json')),
         'Sealed79 summary changed')
    need(old_summary['source_sha256'] == baseline['sourceSHA256']
         and old_summary['evidence_sha256']['APK_Artifact.json'] == sha(proof.file('Baseline79_APK_Artifact.json')),
         'Sealed79 summary/source/artifact bindings differ')
    need(baseline['apkSHA256'] == old_summary['apk_sha256'] == old_artifact['sha256']
         == sha(proof.external_file(baseline['archive'])), 'Sealed79 APK archive changed')
    old = old_source['files']
    changed = sorted(p for p in old.keys() & current.keys() if old[p] != current[p])
    added = sorted(current.keys() - old.keys())
    delta = proof.read('Source_Delta.json')
    need(set(changed) == CHANGED and set(added) == ADDED and not old.keys() - current.keys()
         and delta == {'baseline': 79, 'changed_existing': changed, 'added': added, 'removed': []},
         'Source delta exceeds approved11 existing/6 new launch/localization changes')
    # Old artwork, asset GUIDs, boards, services, dependencies and gameplay bytes remain sealed79.
    need(not any(p.endswith('.meta') or '/Resources/' in p or '/M46/' in p or '/M47/' in p
                 or '/M48/' in p or '/Packages/' in p for p in changed), 'Protected gameplay/art/metadata changed')
    origin = proof.read('Implementation_Diff_Origin_Review.json')
    need(origin['status'] == 'READ_ONLY_BASELINE79_DIFF_ORIGIN_CHECK'
         and {r['path'] for r in origin['rows']} == CHANGED and len(origin['rows']) == 11
         and all(r['baseline79RecoveredExact'] is True and r['sealed79SHA256'] == old[r['path']]
                 and r['matchingRepresentation'] for r in origin['rows']),
         'Independent sealed79 implementation-diff origin proof differs')
    correction = proof.read('Archive_Branding_Correction.json')
    need(correction['status'] == 'CORRECTED_AUDIT_PROSE_ENCODING_NOT_RUNTIME_REGRESSION'
         and correction['source_sha256'] == source_digest and correction['runtimeChanged'] is False
         and correction['originalAuditsRewritten'] is False and correction['displayTitle'] == NAME
         and correction['logoGuid'] == 'dbf14ca73e245a739834a16d7faa3b82'
         and correction['logoSHA256'] == current[PREFIX + 'App/Launch/Art/Title_Logo_RU_R1.png'],
         'Append-only archive branding/prose correction differs')
    for record in correction['originalRecords'].values():
        proof.external_file(record['path'], record['sha256'])
    for path, digest in correction['sourceRecords'].items():
        proof.external_file(path, digest)
    guids = {}
    for path in current:
        if path.endswith('.meta'):
            m = re.search(r'^guid: ([0-9a-f]{32})$', (ROOT / path).read_text('utf-8-sig'), re.M)
            if m:
                guids.setdefault(m[1], []).append(path)
    for path in ADDED:
        if path.endswith('.meta'):
            m = re.search(r'^guid: ([0-9a-f]{32})$', (ROOT / path).read_text('utf-8-sig'), re.M)
            need(m and guids[m[1]] == [path], 'New metadata GUID is malformed or duplicated: ' + path)
    historical = 'Attempts/001_invalid_new_script_guid/'
    failed = proof.read(historical + 'Native/Configure_Process.json')
    failed_source = proof.read(historical + failed['sourceManifest'])
    failed_after = proof.read(historical + failed['afterSourceManifest'])
    need(failed['exitCode'] == 1 and failed['timedOut'] is False
         and failed['method'] == 'RussianLaunch80Configuration.Configure'
         and failed['version'].startswith('2022.3.62f3') and failed_source['files'] == failed_after['files']
         and sha(proof.file(historical + failed['sourceManifest'])) == failed['sourceSHA256']
         and sha(proof.file(historical + failed['afterSourceManifest'])) == failed['afterSourceSHA256'],
         'Preserved failed Configure source/process changed')
    need(sha(proof.file(historical + failed['log'])) == failed['logSHA256']
         and not (OUT / historical / 'Native/Configuration.json').exists(),
         'Failed Configure was overwritten or falsely given a passing report')
    reason = proof.file(historical + 'Reason.txt').read_text('utf-8-sig')
    need('GUID' in reason and 'failed' in reason.lower(), 'Failed Configure reason missing')
    archived_changes = [p for p in failed_source['files'] if old.get(p) != failed_source['files'][p]]
    for path in archived_changes:
        need(sha(proof.file(historical + 'SourceFiles/' + path)) == failed_source['files'][path],
             'Failed Configure source bytes changed: ' + path)
    bad_meta = PREFIX + 'Verification/Editor/RussianLaunch80Configuration.cs.meta'
    bad_guid = re.search(r'^guid: ([0-9a-f]+)$', proof.file(historical + 'SourceFiles/' + bad_meta).read_text('utf-8-sig'), re.M)
    need(bad_guid and len(bad_guid[1]) == 33
         and {p for p in current if current[p] != failed_source['files'].get(p)} == {bad_meta},
         'Failed33-character GUID/final correction scope differs')
    frozen_utc = utc(source['utc'])
    configuration, config_run = validate_process(proof, 'Configure', 'Native/Configuration.json', current, frozen_utc, configure=True)
    need(utc(failed['finishedUtc']) < utc(config_run['startedUtc']), 'Failed attempt does not precede final Configure')
    need(configuration['status'] == 'PASS_RUSSIAN_LAUNCH80_BRANDING_SPLASH_ENTITLEMENT_REQUIRED'
         and configuration['productName'] == NAME and configuration['logoGuid'] == 'dbf14ca73e245a739834a16d7faa3b82'
         and configuration['hasProLicense'] is False and configuration['splashRemovalSupported'] is False
         and configuration['showSplashScreen'] is True and configuration['showUnityLogo'] is True
         and configuration['importErrors'] == 0, 'Sanitized license/splash capability readback differs')
    need('Errors: 0' in proof.file('Native/Import_Audit.txt').read_text('utf-8-sig'), 'Configuration import audit failed')
    native = {}
    for name, (path, status, expected_count) in SUITES.items():
        report, run = validate_process(proof, name, path, current, frozen_utc)
        need(report['status'] == status and count_checks(report) == expected_count,
             name + ' status/assertion count differs')
        native[name] = {'status': status, 'checks': expected_count, 'process': run}
    general = proof.read('Native/Checks.json')
    need(len(general['checks']) == general['passed'] == 534
         and all(c['status'] == 'PASS' and not c['error'] for c in general['checks']),
         'General534 individual check results differ')
    smoke = proof.read('Native/PlaySmoke.json')
    trace = smoke['startupTrace']
    need(smoke['startupWitnessed'] is True and trace['eligible'] is True and trace['pending'] is False
         and trace['workerFailed'] is False and trace['cancelled'] is False and trace['tailInstalledFrame'] > 0
         and 0 < trace['cameraWitnessTicks'] <= trace['jobStartedTicks'] <= trace['workerStartedTicks'] <= trace['workerFinishedTicks'],
         'Connected smoke omitted completed camera-witnessed default79 startup')
    locale = proof.read('Native/Locale80.json')
    need(locale['persistedIndices'] == [0, 1, 2, 3, 4] and locale['visualOrder'] == [4, 0, 1, 2, 3]
         and locale['preferenceCases'] == 20 and locale['layoutCases'] == 15 and locale['liveCases'] == 10
         and all(locale[k] is True for k in ('validStoredSelectionsPreserved', 'preferenceRestored', 'ordinaryTutorialPreserved')),
         'Native locale selection/default/preservation coverage differs')
    locale_images = locale['captures']
    need(set(locale_images) == {'Native/Locale80/' + name + '.png' for name in (
        'FirstStart_Russian', 'FirstStart_Languages_ru', 'FirstStart_Languages_en',
        'Settings_Languages_ru', 'Settings_Languages_en', 'Settings_Russian')},
        'Required Russian/English FirstStart/Settings capture cases differ')
    launch = proof.read('Native/Launch/Native_Review.json')
    launch_images = ['Native/Launch/' + name for name in launch['frames']]
    need(len(locale_images) == 6 and len(set(locale_images)) == 6 and len(launch_images) == 19
         and len(set(launch_images)) == 19 and len(launch['bars']) == 25 and len(launch['routes']) == 4,
         'Native capture/bar/route coverage incomplete')
    need({r['name'] for r in launch['routes']} == {'Fresh', 'ResumeRocket', 'ReturningProgress', 'CompletedTutorial'}
         and all(all(r[k] for k in ('launchReleased', 'artUnloaded', 'logoUnloaded', 'loadingSkinsUnloaded', 'settingsUnchanged', 'walletUnchanged'))
                 for r in launch['routes']), 'First-start/returning routing or transient cleanup regressed')
    for image in locale_images + launch_images:
        proof.file(image)
    builds = {}
    for mode, path, status, source_name in (
        ('AndroidReleaseBuild', 'Android_Release_Build.json', 'PASS_ANDROID_RELEASE_COMPILE_BUILD', 'Release_Source_SHA256.json'),
        ('AndroidBuild', 'Android_Build.json', 'PASS_ANDROID_DEVELOPMENT_BUILD', 'Build_Source_SHA256.json'),
    ):
        report, run = validate_process(proof, mode, path, current, frozen_utc, build=True)
        need(report['status'] == status and report['errors'] == 0 and report['productName'] == NAME
             and report['hasProLicense'] is False and report['showSplashScreen'] is True and report['showUnityLogo'] is True,
             mode + ' branding/splash/build result differs')
        need(proof.read(source_name)['files'] == current and sha(proof.file(source_name)) == source_digest,
             mode + ' source binding differs')
        # Validate original captured records above; an optional convenience mirror
        # is neither reconstructed nor substituted for missing native execution.
        if (OUT / (mode + '_Process.json')).exists():
            need(proof.read(mode + '_Process.json') == run['delegatedProcess'],
                 mode + ' optional root process mirror differs')
        if (OUT / (mode + '.log')).exists():
            need(sha(proof.file(mode + '.log')) == run['logSHA256'], mode + ' optional root log mirror differs')
        temporary = proof.read('Native/' + mode + '_Temporary_Input_Delta.json')
        need(not temporary['added'] and not temporary['removed']
             and all(p.startswith('Unity/ProjectSettings/') for p in temporary['changed_existing']),
             mode + ' temporarily changed non-settings inputs')
        builds[mode] = run
    need(max(utc(v['process']['finishedUtc']) for v in native.values()) <= utc(builds['AndroidReleaseBuild']['startedUtc'])
         <= utc(builds['AndroidReleaseBuild']['finishedUtc']) <= utc(builds['AndroidBuild']['startedUtc']),
         'Native/release/development chronology differs')
    for path in ('Build_Import_Audit.txt', 'Release_Build_Import_Audit.txt'):
        need('Errors: 0' in proof.file(path).read_text('utf-8-sig'), path + ' import guard failed')
    artifact = proof.read('APK_Artifact.json')
    packaging = proof.read('APK_Packaging.json')
    apk = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    digest = sha(apk)
    need(digest == artifact['sha256'] == packaging['afterSHA256']
         and apk.stat().st_size == artifact['bytes'] == packaging['afterBytes']
         and all(artifact[k] is True for k in ('zipalign4KiBPass', 'developmentSignatureVerifies', 'elf16KiBLoadSegmentsPass'))
         and packaging['status'] == 'PASS_CLEAN_GRADLE_APK_PACKAGING' and packaging['sameSignerCertificate'] is True
         and not packaging['changedNonSignatureEntries'], 'Final development APK packaging/integrity differs')
    proof.external_file('.verification-cache/LaunchRuStoreR3/Unity_Incremental.apk', packaging['beforeSHA256'])
    proof.file('Gradle_Clean.log')
    need(utc(builds['AndroidBuild']['finishedUtc']) <= utc(packaging['utc']), 'Packaging predates development build')
    branding = proof.read('APK_Branding.json')
    need(branding['status'] == 'PASS_RUSSIAN_LAUNCH80_APK_NAMES_AND_IDENTITY'
         and len(branding['artifacts']) == 2, 'APK Cyrillic label/identity proof missing')
    for row in branding['artifacts']:
        path = proof.external_file(row['path'], row['sha256'])
        need(path.name in ('HeartOfTheRain_Development.apk', 'HeartOfTheRain_ReleaseCompile.apk')
             and row['bytes'] == path.stat().st_size and row['package'] == 'com.heartoftherain.verification'
             and row['displayName'] == NAME, 'APK branding/path metadata differs')
        badging = proof.file(path.name + '.Badging.txt').read_text('utf-8-sig')
        need("package: name='com.heartoftherain.verification'" in badging
             and "application-label:'" + NAME + "'" in badging, 'Actual aapt badging differs')
    need({Path(r['path']).name for r in branding['artifacts']} == {'HeartOfTheRain_Development.apk', 'HeartOfTheRain_ReleaseCompile.apk'},
         'APK branding omitted one build branch')
    manifest = proof.file('Android_Manifest.txt').read_text('utf-8-sig')
    need('android:screenOrientation' in manifest and 'com.heartoftherain.verification' in manifest,
         'Final Android manifest identity/orientation proof missing')
    target = proof.read('QA_Target.json')
    prior_target = json.loads(proof.external_file('Verification/Evidence/Gameplay79/QA_Target.json').read_text('utf-8-sig'))
    need(target['status'] == 'AUTHORIZED_ISOLATED_RUSSIAN_LAUNCH80_QA' and target['serial'] == 'emulator-5558'
         and target['index'] == 2 and target['name'] == 'Heart of the Rain QA79 isolated'
         and target['activeAttempts'] == 0 and target['mainAndOriginalQAStopped'] is True
         and target['priorTargetSHA256'] == sha(ROOT / 'Verification/Evidence/Gameplay79/QA_Target.json')
         and prior_target['target'] == {'index': 2, 'serial': 'emulator-5558', 'name': target['name']},
         'Isolated QA2 authorization/save guard differs')
    lines = target['list2'].splitlines()
    need(lines[0].startswith('0,LDPlayer,0,0,0,-1,-1,')
         and lines[1].startswith('1,Heart of the Rain QA,0,0,0,-1,-1,')
         and lines[2].startswith('2,Heart of the Rain QA79 isolated,'), 'Main/original QA isolation evidence differs')
    device = proof.read('Android/Installation.json')
    clean(device, 'Android')
    need(device['status'] == 'PASS_RUSSIAN_LAUNCH80_DEVICE_AUDIT' and device['serial'] == 'emulator-5558'
         and device['activeAttempts'] == 0 and device['installedBeforeSHA256'] == baseline['apkSHA256']
         and device['apk_sha256'] == device['installed_apk_sha256'] == digest
         and device['source_sha256'] == source_digest and device['targetSHA256'] == sha(proof.file('QA_Target.json'))
         and device['data_unchanged'] is True and device['before'] == device['after']
         and device['before']['preferences'] and device['before']['saves']
         and device['portrait'] is True and device['runtime_errors'] == 0
         and 'Success' in device['install'], 'Android install/runtime/save/portrait audit failed')
    need(utc(packaging['utc']) <= utc(target['utc']) <= utc(device['utc']) <= utc(device['finishedUtc']),
         'Device target/install/build chronology differs')
    logs = proof.file('Android/Runtime.log').read_text('utf-8-sig')
    need(not re.search(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException', logs),
         'Runtime fatal/exception evidence differs from zero-error audit')
    device_media = ['Android/Cold_Start.mp4', 'Android/FirstStart_Russian.png', 'Android/FirstStart_Language_Menu.png']
    for name in device_media:
        proof.file(name)
    locale_review = validate_review(proof, 'Locale_Visual_Notes.json', source_digest, locale_images)
    launch_review = validate_review(proof, 'Launch_Visual_Notes.json', source_digest, launch_images)
    native_review = validate_review(proof, 'Native_Visual_Notes.json', source_digest, locale_images + launch_images)
    for child in ('Locale_Visual_Notes.json', 'Launch_Visual_Notes.json'):
        need(native_review['artifactSHA256'].get(child) == sha(proof.file(child)),
             'Native aggregate omitted its actual independent reviewer record: ' + child)
    device_review = validate_review(proof, 'Device_Visual_Notes.json', source_digest, device_media, digest)
    need(utc(native_review['utc']) >= max(utc(native['Locale']['process']['finishedUtc']), utc(native['Launch']['process']['finishedUtc']))
         and utc(device_review['utc']) >= utc(device['finishedUtc']), 'Actual visual review predates its captures')
    for path in ('Verification/Run-LaunchRuStoreR3.ps1', 'Verification/Tools/run_russian_launch80_device.py',
                 'Verification/Tools/collect_russian_launch80_results.py'):
        proof.external_file(path)
    gates = [
        'User confirmed no eligible Unity license is available. Required Unity engine splash and Unity logo remain enabled on pinned2022.3.62f3; splash removal is not complete. No engine or license change is authorized.',
        'Internal development and release-compile APKs use the unchanged verification identifier/signing. RuStore signing, AAB/store publication and store compliance are not established.',
        'Native camera review covers25 captures and four isolated routes. Device review covers one isolated QA2 startup/menu flow; physical-device/notch/full-translation/long-session acceptance is open.',
        'Gameplay runtime/assets and prior79 proof remain unchanged; the later359.614ms Update/366.029ms interval and dense rendering limitations remain open, without a new smoothness claim.',
    ]
    return {
        'status': STATUS, 'utc': datetime.now(timezone.utc).isoformat(), 'source_checkpoint': 80,
        'source_sha256': source_digest, 'source_inputs': len(current), 'apk_sha256': digest, 'apk_bytes': apk.stat().st_size,
        'baseline_source_checkpoint': 79, 'baseline_source_sha256': baseline['sourceSHA256'], 'baseline_apk_sha256': baseline['apkSHA256'],
        'source_delta': delta, 'native_suites': {n: {'status': v['status'], 'checks': v['checks']} for n, v in native.items()},
        'native_suite_count': 6, 'native_checks': sum(v['checks'] for v in native.values()),
        'native_captures': 25, 'native_launch_routes': 4, 'configuration': configuration,
        'preserved_failed_attempts': [{'attempt': '001_invalid_new_script_guid', 'exit_code': 1,
                                       'source_sha256': failed['sourceSHA256'], 'counted_as_pass': False}],
        'android': {'serial': device['serial'], 'qa_index': 2, 'data_unchanged': True, 'runtime_errors': 0,
                    'portrait': True, 'installed_checkpoint': 80, 'original_qa_checkpoint': 78, 'main_checkpoint': 64},
        'native_review': native_review['status'], 'device_review': device_review['status'],
        'remainingGates': gates, 'evidence_sha256': dict(sorted(proof.artifacts.items())),
        'external_evidence_sha256': dict(sorted(proof.external.items())),
        'scope': 'Targeted Russian launch/default locale/menu-order integration on pinned Unity and isolated QA2. Native configuration, six suites, two internal APK builds, packaging, save-preserving installation and actual bounded visual reviews pass. Required Unity splash remains because the current license is ineligible; no splash-removal, store-release or whole-game completion claim.',
    }


def main(publish=False):
    result = build()
    if publish:
        text = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
        for path in (OUT / 'Summary.json', OUT.parent / 'Verification_Summary.json'):
            path.write_text(text, encoding='utf-8')
        checkpoint = {
            'utc': result['utc'], 'status': result['status'], 'source_checkpoint': 80,
            'last_verified_source_checkpoint': 80, 'installed_checkpoint': 64, 'qa_installed_checkpoint': 78,
            'isolated_qa_installed_checkpoint': 80, 'isolated_qa_serial': 'emulator-5558',
            'original_qa_active_attempt_preserved': True, 'source_sha256': result['source_sha256'],
            'android_apk_sha256': result['apk_sha256'], 'android_apk_matches_current_source': True,
            'main_installed_apk_matches_current_source': False, 'unity_splash_removal_complete': False,
            'review': 'Codex_Handoff/Documentation/80_RUSSIAN_LAUNCH_RUSTORE_R3_REVIEW.md',
            'summary': 'Verification/Evidence/LaunchRuStoreR3/Summary.json', 'scope': result['scope'],
        }
        (OUT.parent / 'Native_Source_Checkpoint.json').write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'source_inputs', 'native_checks', 'apk_sha256')}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    main(parser.parse_args().publish)
