"""Explicit root-only side-by-side Unity 6 phone checks; imports never call ADB.

The installed owner package is only read through the unchanged Review93 helper.
No owner stop, launch, replacement, uninstall, data clear or save transfer exists.
Each command needs --execute; startup observation and regression are separate.
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
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
PACKAGE = 'com.heartoftherain.unity6review94'
OWNER = ROOT / 'Verification/Evidence/Review93/Phone/Device01'
MARKER = 'HOTR_RunRegression'
SELECTED_ERRORS = r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException|DllNotFoundException'
SELECTED = (
    ('Gameplay HUD', ('Gameplay_English_HUD.png',)),
    ('Rocket effect', ('Power_4_Effect_0.png', 'Power_4_Effect_1.png', 'Power_4_Effect_2.png')),
    ('Stacked obstacle refill', ('Stacked_Stones_Diagonal_0.png', 'Stacked_Stones_Diagonal_1.png', 'Stacked_Stones_Diagonal_2.png')),
    ('Chapter completion Home', ('Home_Reward_L50.png',)),
)


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


phone = module('unity6_94_unchanged_owner_reader', 'Verification/Tools/Review93/phone.py')
legacy_scope = module('unity6_94_unchanged_regression_reader', 'Verification/Tools/Review93/phone_regression_proof.py')


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def when(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(parsed.tzinfo is not None, 'Phone94TimezoneRequired')
    return parsed


def save(path, value):
    phone.write(path, value)


def binding(path):
    return phone.public_binding(path)


def stable(value):
    need(value.get('activeAttempts') == 0, 'Phone94ActiveAttemptPreserved')
    return {key: value[key] for key in ('profiles', 'preferences', 'profileSummaries', 'installedSHA256')}


def native_scope(report, unity):
    """94 engine adaptation; never rewrites an old native report or old proof.

    The earlier proof hard-pins Unity 2022, so its coverage rules are retained
    here while the actual report must match the passed Unity 6 build exactly.
    """
    need(isinstance(report, dict) and report.get('status') == 'PASS_NATIVE_REGRESSION'
         and report.get('failures') == [] and report.get('unity') == unity and unity.startswith('6000.')
         and report.get('platform') == 'Android' and report.get('boards') == 50
         and report.get('actions') == 408 and report.get('clips') == 354
         and type(report.get('checks')) is int and report['checks'] == len(report.get('passed', [])) > 0
         and report.get('labels', 0) > 0 and set(report.get('damageFamilies', [])) == legacy_scope.EXPECTED_FAMILIES,
         'Phone94NativeCoverageNotPassed')
    passed = set(report['passed'])
    for level in range(1, 51):
        need('L' + str(level) + ' accepts natural move' in passed, 'Phone94NaturalMoveMissing')
        for tool in range(4):
            need('L' + str(level) + ' tool ' + str(tool) + ' spends one stock' in passed
                 and 'L' + str(level) + ' tool ' + str(tool) + ' preserves moves' in passed, 'Phone94ToolCoverageMissing')
    for key in ('Practice Match solved through page commands and real animation playback',
                'Practice Rocket solved through page commands and real animation playback',
                'Practice Clear solved through page commands and real animation playback',
                'Exactly 900 coins shows the enabled native refill button and price',
                'Repeated native refill callback charges exactly once',
                'Connected Continue exposes the approved five-move/900-coin offer',
                'Confirmed decline charges exactly one life, no coins, and opens retry pre-level',
                'Celebration completion cannot grant a duplicate reward L50',
                'Celebration returns Home without next-level modal L50'):
        need(key in passed, 'Phone94LifecycleCoverageMissing')


def validate_build(path, *, require_static=True):
    path = Path(path).resolve()
    need(path.is_relative_to(OUT) and path.name == 'BuildDevelopment.json', 'Phone94DevelopmentNativeBuildRequired')
    native = phone._read_record(path)
    invocation_path = path.parent / 'Invocation.json'
    invocation = phone._read_record(invocation_path)
    need(native.get('status') == 'PASS_ISOLATED_UNITY6_94_BUILDDEVELOPMENT'
         and native.get('operation') == 'BuildDevelopment' and native.get('exitCode') == 0
         and native.get('errors') == 0 and not native.get('error') and native.get('buildResult') == 'Succeeded'
         and native.get('nonDevelopmentCompileOnly') is False and native.get('buildPackageName') == PACKAGE,
         'Phone94PassedSideBySideDevelopmentBuildRequired')
    settings = native.get('after', {})
    need(settings.get('packageName') == PACKAGE and settings.get('showSplashScreen') is False
         and settings.get('showUnityLogo') is False and settings.get('portraitOnly') is True
         and settings.get('applicationEntry') == 'Activity' and settings.get('backend') == 'IL2CPP'
         and settings.get('architectures') == 'ARM64' and settings.get('minApi') == 26,
         'Phone94NativeSplashPackageOrAndroidSettingsInvalid')
    need(invocation.get('status') == 'PASS_ISOLATED_UNITY6_94_NATIVE' and invocation.get('exitCode') == 0
         and invocation.get('entry') == 'HeartOfTheRain.Verification.Unity6Migration94.BuildDevelopment'
         and invocation.get('mainInputsUnchanged') is True and invocation.get('unityPidsAfter') == []
         and invocation.get('nativeReportSHA256') == phone.sha(path)
         and invocation.get('nativeReport') == path.relative_to(ROOT).as_posix()
         and invocation.get('actualEngineVersionFromProcessLog') == native.get('unity') == native.get('expectedUnity')
         and native.get('unity', '').startswith('6000.'), 'Phone94RealCompletedUnity6ProcessRequired')
    apk = Path(native['output']).resolve()
    need(apk.is_relative_to(PROJECT / 'Builds') and apk.suffix == '.apk' and apk.is_file()
         and phone.sha(apk) == native.get('apkSHA256') and apk.stat().st_size == native.get('bytes'), 'Phone94CurrentCandidateApkChanged')
    result = {'native': native, 'nativePath': path, 'invocationPath': invocation_path, 'apk': apk,
              'candidateSources': path.parent / 'CandidateSources_after.json', 'unity': native['unity']}
    if require_static:
        result['staticReport'] = validate_static(result)
    return result


def validate_static(build):
    """Actual static APK evidence is mandatory before any candidate operation."""
    path = build['nativePath'].parent / 'StaticApk94.json'
    report = phone._read_record(path)
    required = ('zipCrcPass', 'signatureVerifies', 'zipAlignFourBytePass', 'elf16KiBLoadSegmentsPass', 'storedNative16KiBAligned',
                'abiArm64Only', 'packageMatchesNativeBuild', 'portraitActivity', 'minApi26',
                'developmentFlagMatches', 'sdkFreeDex', 'identityBridgePresent', 'sourcesUnchanged', 'apkUnchanged')
    need(report.get('status') == 'PASS_INTERNAL_UNITY6_94_APK' and report.get('errors') == []
         and report.get('package') == PACKAGE and report.get('development') is True
         and report.get('nonDevelopmentCompileOnly') is False
         and report.get('apk') == binding(build['apk']) and report.get('nativeReport') == binding(build['nativePath'])
         and report.get('buildInvocation') == binding(build['invocationPath'])
         and report.get('candidateSources') == binding(build['candidateSources'])
         and report.get('runner') == binding(ROOT / 'Verification/Tools/Unity6Migration94/check_apk94.py')
         and all(report.get('checks', {}).get(key) is True for key in required), 'Phone94PassedCurrentStaticApkRequired')
    artifacts = report.get('artifacts', [])
    expected_raw = {name + '_' + stream + '.txt' for name in ('Signature', 'Zipalign', 'Badging', 'Manifest') for stream in ('stdout', 'stderr')}
    need(isinstance(artifacts, list) and len(artifacts) == len(expected_raw)
         and {Path(item['path']).name for item in artifacts} == expected_raw, 'Phone94StaticRawArtifactsRequired')
    for item in artifacts:
        artifact = (ROOT / item['path']).resolve()
        need(artifact.is_relative_to(path.parent / 'AndroidStatic94') and artifact.is_file()
             and binding(artifact) == item, 'Phone94StaticRawArtifactChanged')
    return binding(path)


class Candidate:
    def __init__(self, build, *, out=OUT / 'Phone/Device01'):
        self.out = Path(out).resolve()
        need(self.out == (OUT / 'Phone/Device01').resolve(), 'Phone94FixedEvidenceDirectoryRequired')
        self.build = validate_build(build)
        self.owner = phone.Phone(OWNER)
        self.owner.assert_installed()
        self.base = '/sdcard/Android/data/' + PACKAGE + '/files'
        self.out.mkdir(parents=True, exist_ok=True)
        self.source_guard()

    def source_guard(self):
        api = module('unity6_94_phone_source_reader', 'Verification/Tools/Ads85/run_ads85_native.py')
        runner = module('unity6_94_phone_candidate_reader', 'Verification/Tools/Unity6Migration94/run_native.py')
        need(api.freeze() == phone._read_record(OUT / 'MainSources_Before.json'), 'Phone94ProtectedMainInputsChanged')
        # Candidate manifests exceed the bounded small phone-report reader.
        expected = json.loads(self.build['candidateSources'].read_text('utf-8'))
        need(runner.candidate_sources(api) == expected, 'Phone94CandidateInputsChangedSinceBuild')
        return {'mainManifest': binding(OUT / 'MainSources_Before.json'), 'candidateSources': binding(self.build['candidateSources'])}

    def owner_snapshot(self):
        self.owner.assert_installed()
        value = self.owner.require_idle()
        need(self.owner.pending_markers() == [], 'Phone94OwnerProbeRequestPreserved')
        return value

    def installed_path(self):
        reply = self.owner.adb('shell', 'pm', 'path', PACKAGE)
        if not reply:
            return None
        need(re.fullmatch(r'package:/data/app/[^\r\n]+/base\.apk', reply) is not None, 'Phone94SingleCandidateApkRequired')
        return reply[len('package:'):]

    def assert_installed(self):
        remote = self.installed_path()
        need(remote is not None, 'Phone94CandidateNotInstalled')
        reply = self.owner.adb('shell', 'sha256sum', remote)
        need(re.fullmatch(r'[0-9a-fA-F]{64}\s+[^\r\n]+', reply) is not None
             and reply.split()[0].lower() == self.build['native']['apkSHA256'], 'Phone94InstalledCandidateHashMismatch')

    def pending_markers(self):
        if not self.owner.exists(self.base):
            return []
        rows = self.owner.adb('shell', 'find', self.base, '-maxdepth', '1', '-type', 'f').splitlines()
        need(len(rows) <= 4096 and all(row.startswith(self.base + '/') for row in rows), 'Phone94CandidateRootInventoryInvalid')
        return [row for row in rows if row.removeprefix(self.base + '/').startswith('HOTR_Run')]

    def inventory(self):
        self.assert_installed()
        directory = self.base + '/Profiles'
        hashes, summaries, active = {}, [], 0
        if self.owner.exists(directory):
            for remote in self.owner.adb('shell', 'find', directory, '-type', 'f').splitlines():
                need(re.fullmatch(re.escape(directory) + r'/[A-Za-z0-9_./-]+', remote) is not None, 'Phone94CandidateProfilePathInvalid')
                relative = remote.removeprefix(self.base + '/')
                hashes[relative] = self.owner.adb('shell', 'sha256sum', remote).split()[0]
                if re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json', relative):
                    envelope = json.loads(self.owner.adb('exec-out', 'cat', remote))
                    profile = json.loads(envelope['payload'])
                    states = [attempt['state'] for attempt in profile['attempts']]
                    need(all(state in ('Reserved', 'Started', 'Won', 'Lost', 'Interrupted', 'Cancelled', 'Released') for state in states), 'Phone94UnknownCandidateAttemptState')
                    count = sum(state in ('Reserved', 'Started') for state in states)
                    active += count
                    summaries.append({'profile': relative, 'revision': profile['revision'], 'activeAttempts': count,
                        'coins': profile.get('coins'), 'lives': profile.get('lives'), 'currentLevel': profile.get('currentLevel'), 'completed': profile.get('completed')})
        # Fixed literal command, no user content or credential interpolation.
        state = self.owner.adb('shell', 'run-as', PACKAGE, 'sh', '-c', '"if test -d shared_prefs; then echo PRESENT; else echo ABSENT; fi"')
        need(state in ('PRESENT', 'ABSENT'), 'Phone94CandidatePreferencesDirectoryUnknown')
        preferences = {}
        if state == 'PRESENT':
            for name in self.owner.adb('shell', 'run-as', PACKAGE, 'ls', 'shared_prefs').split():
                need(re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', name) is not None, 'Phone94CandidatePreferencesPathInvalid')
                preferences[name] = hashlib.sha256(self.owner.adb('exec-out', 'run-as', PACKAGE, 'cat', 'shared_prefs/' + name, binary=True)).hexdigest()
        need(not self.owner.exists(self.base + '/ServerReview/configuration.json'), 'Phone94CandidateConfiguredBackendNotApproved')
        return {'utc': phone.utc(), 'profiles': hashes, 'preferences': preferences, 'profileSummaries': summaries,
                'activeAttempts': active, 'installedSHA256': self.build['native']['apkSHA256']}

    def idle(self, *, initialized=True):
        value = self.inventory()
        need(value['activeAttempts'] == 0, 'Phone94CandidateActiveAttemptPreserved')
        if initialized:
            need(value['profileSummaries'], 'Phone94CandidateStartupProfileNotReady')
        need(self.pending_markers() == [], 'Phone94CandidateProbeRequestPreserved')
        return value

    def header(self, action):
        return {'schemaVersion': 1, 'checkpoint': 94, 'action': action, 'startedUtc': phone.utc(),
            'runner': binding(Path(__file__)), 'ownerHelper': binding(Path(phone.__file__)),
            'ownerTarget': binding(OWNER / 'Target.json'), 'ownerInstallation': binding(OWNER / 'Installation.json'),
            'serialSHA256': self.owner.serial_sha, 'model': self.owner.target['model'], 'package': PACKAGE,
            'buildReport': binding(self.build['nativePath']), 'buildInvocation': binding(self.build['invocationPath']),
            'staticReport': self.build['staticReport'],
            'apk': binding(self.build['apk']), 'unity': self.build['unity'], 'sources': self.source_guard(),
            'ownerMutation': False, 'scope': 'Side-by-side isolated Unity6 SDK-free development package on the same owner phone. Owner package is read-only; no data migration, keys, profile copying, provider/backend activation or production approval.'}

    def preflight(self):
        need(not (self.out / 'Preflight.json').exists(), 'Phone94ExistingPreflightPreserved')
        record = self.header('preflight')
        record['ownerBefore'] = self.owner_snapshot()
        need(self.installed_path() is None, 'Phone94ExistingCandidatePreservedNoReplacement')
        need(not self.owner.exists(self.base), 'Phone94OldCandidateExternalDataPreserved')
        record.update(status='PASS_READ_ONLY_SIDE_BY_SIDE_PREFLIGHT94', candidateAbsent=True, completedUtc=phone.utc())
        save(self.out / 'Preflight.json', record)
        return record

    def install(self):
        need(not (self.out / 'Installation.json').exists(), 'Phone94ExistingInstallationPreserved')
        previous = phone._read_record(self.out / 'Preflight.json')
        record = self.header('install')
        need(previous.get('status') == 'PASS_READ_ONLY_SIDE_BY_SIDE_PREFLIGHT94'
             and previous.get('apk') == record['apk'], 'Phone94MatchingPreflightRequired')
        before = self.owner_snapshot()
        need(stable(before) == stable(previous['ownerBefore']), 'Phone94OwnerChangedSincePreflight')
        need(self.installed_path() is None and not self.owner.exists(self.base), 'Phone94ExistingCandidatePreservedNoReplacement')
        save(self.out / 'Install_OwnerBefore.json', before)
        # Fresh install only: no -r, uninstall, clear, or owner stop.
        result = self.owner.adb('install', self.build['apk'])
        need(result == 'Success' or result.endswith('\nSuccess'), 'Phone94FreshCandidateInstallFailed')
        self.assert_installed()
        after = self.owner_snapshot()
        need(stable(before) == stable(after), 'Phone94OwnerChangedDuringCandidateInstall')
        record.update(status='PASS_FRESH_SIDE_BY_SIDE_INSTALL94', ownerDataUnchanged=True, ownerAfter=after,
                      installResult='Success', candidateAfter=self.idle(initialized=False), completedUtc=phone.utc())
        save(self.out / 'Installation.json', record)
        return record

    def stop_candidate(self):
        self.assert_installed()
        self.owner.adb('shell', 'am', 'force-stop', PACKAGE)
        need(not self.owner.adb('shell', 'pidof', PACKAGE, check=False), 'Phone94CandidateDidNotStop')

    def start_candidate(self):
        result = self.owner.adb('shell', 'am', 'start', '-W', '-n', PACKAGE + '/com.unity3d.player.UnityPlayerActivity')
        need(re.search(r'(?m)^Status:\s*ok\s*$', result) is not None, 'Phone94CandidateStartFailed')
        return result

    def launch(self):
        need(not (self.out / 'Launch.json').exists(), 'Phone94ExistingStartupObservationPreserved')
        record = self.header('launch')
        record['ownerBefore'] = self.owner_snapshot()
        need(phone._read_record(self.out / 'Installation.json').get('status') == 'PASS_FRESH_SIDE_BY_SIDE_INSTALL94', 'Phone94CompletedFreshInstallRequired')
        self.idle(initialized=False)
        record['nativeLaunchUtc'] = phone.utc()
        record['launchResult'] = self.start_candidate()
        time.sleep(8)
        record['candidateAfter'] = self.idle(initialized=False)
        record['ownerAfter'] = self.owner_snapshot()
        need(stable(record['ownerBefore']) == stable(record['ownerAfter']), 'Phone94OwnerChangedDuringCandidateLaunch')
        record.update(status='RECORDED_ORDINARY_CANDIDATE_LAUNCH94_REQUIRES_VISUAL_REVIEW', fixedObservationWaitSeconds=8,
                      ownerDataUnchanged=True, completedUtc=phone.utc())
        save(self.out / 'Launch.json', record)
        return record

    def capture(self, name):
        need(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name) is not None, 'Phone94SimpleCaptureNameRequired')
        before = self.owner_snapshot()
        self.idle(initialized=False)
        activities = self.owner.adb('shell', 'dumpsys', 'activity', 'activities')
        need(any(PACKAGE + '/' in row for row in activities.splitlines()
                 if 'topResumedActivity=' in row or 'mResumedActivity:' in row), 'Phone94CandidateForegroundRequired')
        keyguard = self.owner.adb('shell', 'dumpsys', 'window', 'policy').split('KeyguardServiceDelegate', 1)[-1]
        need(re.search(r'(?m)^\s*showing=false\s*$', keyguard) is not None, 'Phone94UnlockedCandidateRequired')
        path = self.out / 'Screens' / (name + '.png')
        need(not path.exists() and not path.with_suffix('.json').exists(), 'Phone94FreshCaptureRequired')
        data = self.owner.adb('exec-out', 'screencap', '-p', binary=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        width, height = phone.validate_png(data)
        after = self.owner_snapshot()
        need(stable(before) == stable(after), 'Phone94OwnerChangedDuringCapture')
        record = self.header('capture')
        record.update(status='RECORDED_ACTUAL_CANDIDATE_OS_FRAME94_REQUIRES_VISUAL_REVIEW',
            kind='ACTUAL_ANDROID_OS_FRAMEBUFFER', png=binding(path), width=width, height=height,
            ownerDataUnchanged=True, ownerBefore=before, ownerAfter=after, completedUtc=phone.utc())
        save(path.with_suffix('.json'), record)
        return record

    def app_log(self, destination):
        pid = self.owner.adb('shell', 'pidof', PACKAGE)
        need(re.fullmatch(r'\d+', pid) is not None, 'Phone94SingleCandidateProcessRequired')
        body = self.owner.adb('logcat', '-d', '--pid=' + pid, '-v', 'brief').replace(self.owner.serial, 'physical-phone-1')
        body = re.sub(r'Bearer\s+[A-Za-z0-9_./+=-]+', 'Bearer [REDACTED]', body, flags=re.IGNORECASE)
        body = re.sub(r'-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----.*?-----END (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----', '[REDACTED PRIVATE KEY]', body, flags=re.DOTALL)
        credential = r'''(?i)(["']?\b(?:authorization|token|access[ _-]?token|refresh[ _-]?token|recovery[ _-]?code|api[ _-]?key|password|secret)\b["']?\s*[=:]\s*)(?:"[^"\r\n]*"|'[^'\r\n]*'|[^\s,;]+)'''
        body = re.sub(credential, lambda match: match.group(1) + '[REDACTED]', body)
        with Path(destination).open('x', encoding='utf-8') as stream:
            stream.write(body)
        return {'pid': pid, 'log': binding(destination), 'selectedErrorCount': len(re.findall(SELECTED_ERRORS, body)),
                'scope': 'Candidate-PID-only redacted log; selected signatures do not establish whole-app acceptance.'}

    def collect_regression(self, directory, raw, began):
        report = json.loads(raw)
        native_scope(report, self.build['unity'])
        need(when(report['utc']) >= began and self.owner.target['model'] in report.get('device', ''), 'Phone94FreshPhysicalNativeReportRequired')
        names = report.get('frames', [])
        need(isinstance(names, list) and names and len(names) <= 1000 and len(names) == len(set(names))
             and all(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]+\.png', name) for name in names), 'Phone94DeclaredFramesInvalid')
        selected = {}
        for label, choices in SELECTED:
            found = next((name for name in choices if name in names), None)
            need(found is not None, 'Phone94RepresentativeCaptureMissing')
            selected[found] = label
        native = directory / 'Native'
        native.mkdir(exist_ok=False)
        (native / 'Regression.json').write_bytes(raw)
        remote = self.base + '/Regression'
        raw_atlas = self.owner.adb('exec-out', 'cat', remote + '/M70_Device.json', binary=True)
        (native / 'M70_Device.json').write_bytes(raw_atlas)
        atlas = json.loads(raw_atlas)
        need(atlas.get('status') == 'PASS_NATIVE_M70_DEVICE' and not atlas.get('failures') and when(atlas['utc']) >= began
             and len(atlas.get('textures', [])) == 7 and len(atlas.get('idleAdvancement', [])) == 3
             and all(row.get('passed') is True for row in atlas['idleAdvancement']), 'Phone94NativeAtlasNotPassed')
        hashes, sizes = {}, {}
        for offset in range(0, len(names), 32):
            paths = [remote + '/' + name for name in names[offset:offset + 32]]
            for line in self.owner.adb('shell', 'sha256sum', *paths).splitlines():
                match = re.fullmatch(r'([0-9a-fA-F]{64})\s+(.+)', line)
                need(match is not None and match.group(2) in paths, 'Phone94RemoteCaptureHashInvalid')
                hashes[match.group(2).removeprefix(remote + '/')] = match.group(1).lower()
            for line in self.owner.adb('shell', 'stat', '-c', '%s:%n', *paths).splitlines():
                match = re.fullmatch(r'([0-9]+):(.+)', line)
                need(match is not None and match.group(2) in paths, 'Phone94RemoteCaptureSizeInvalid')
                sizes[match.group(2).removeprefix(remote + '/')] = int(match.group(1))
        need(set(hashes) == set(sizes) == set(names), 'Phone94RemoteCaptureInventoryIncomplete')
        rows = []
        for name in sorted(names):
            retained = name in selected
            destination = native / name
            if retained:
                data = self.owner.adb('exec-out', 'cat', remote + '/' + name, binary=True)
                destination.write_bytes(data)
                need(phone.sha(destination) == hashes[name] and len(data) == sizes[name]
                     and phone.validate_png(data) == (report['width'], report['height']), 'Phone94RetainedNativeCaptureChanged')
            rows.append({'file': name, 'sha256': hashes[name], 'bytes': sizes[name], 'retained': retained,
                         'retainedEvidence': destination.relative_to(ROOT).as_posix() if retained else None, 'selection': selected.get(name)})
        save(directory / 'CaptureInventory.json', {'status': 'RECORDED_NATIVE_REGRESSION_CAPTURE_RETENTION94',
             'capturedPngCount': len(rows), 'retainedPngCount': len(selected), 'files': rows,
             'scope': 'Only current report-declared native camera/UGUI frames. Four original PNGs retained, all declared PNGs hashed remotely. Not OS screenshots or visual approval.'})
        need(self.owner.adb('exec-out', 'cat', remote + '/Regression.json', binary=True) == raw, 'Phone94NativeReportChangedDuringCollection')
        return {'nativeReport': binding(native / 'Regression.json'), 'atlasReport': binding(native / 'M70_Device.json'),
                'captureInventory': binding(directory / 'CaptureInventory.json'), 'checks': report['checks'],
                'boards': report['boards'], 'actions': report['actions'], 'clips': report['clips']}

    def regression(self):
        directory = self.out / 'Regression' / uuid.uuid4().hex
        directory.mkdir(parents=True, exist_ok=False)
        record = self.header('regression')
        record['status'] = 'RUNNING_ISOLATED_PHYSICAL_REGRESSION94'
        owner_before, candidate_before = self.owner_snapshot(), self.idle()
        save(directory / 'OwnerBefore.json', owner_before)
        save(directory / 'CandidateBefore.json', candidate_before)
        save(directory / 'Authorization.json', record)
        try:
            self.stop_candidate()
            need(stable(self.idle()) == stable(candidate_before), 'Phone94CandidateChangedBeforeFixture')
            marker = ROOT / '.verification-cache/Unity6Migration94/PhoneMarkers' / directory.name / MARKER
            marker.parent.mkdir(parents=True, exist_ok=False)
            marker.write_text(phone.utc(), encoding='ascii')
            # Only this audited BeforeSceneLoad memory fixture is authorized.
            self.owner.adb('push', marker, self.base + '/' + MARKER)
            began = datetime.now(timezone.utc)
            record['nativeLaunchUtc'] = began.isoformat()
            self.start_candidate()
            deadline = time.monotonic() + 2100
            while time.monotonic() < deadline:
                raw = self.owner.adb('exec-out', 'cat', self.base + '/Regression/Regression.json', binary=True, check=False)
                try:
                    report = json.loads(raw)
                    fresh = isinstance(report, dict) and when(report.get('utc', '')) >= began
                except (ValueError, TypeError, RuntimeError, AttributeError):
                    report, fresh = {}, False
                if fresh and report.get('status') != 'RUNNING':
                    (directory / 'Latest.json').write_bytes(raw)
                    record.update(self.collect_regression(directory, raw, began))
                    break
                time.sleep(10)
            else:
                raise TimeoutError('Phone94NativeRegressionDeadline')
            record['fixtureAppLog'] = self.app_log(directory / 'Runtime.log')
            need(record['fixtureAppLog']['selectedErrorCount'] == 0, 'Phone94SelectedRuntimeErrorPresent')
            candidate_after, owner_after = self.idle(), self.owner_snapshot()
            save(directory / 'CandidateAfter.json', candidate_after)
            save(directory / 'OwnerAfter.json', owner_after)
            need(stable(candidate_before) == stable(candidate_after), 'Phone94CandidateFixtureChangedOrdinarySave')
            need(stable(owner_before) == stable(owner_after), 'Phone94OwnerChangedDuringCandidateFixture')
            self.stop_candidate()
            record['normalRelaunch'] = self.start_candidate()
            time.sleep(8)
            final_candidate, final_owner = self.idle(), self.owner_snapshot()
            save(directory / 'CandidateAfterRelaunch.json', final_candidate)
            save(directory / 'OwnerAfterRelaunch.json', final_owner)
            need(stable(final_candidate) == stable(candidate_before), 'Phone94CandidateChangedAfterNormalRelaunch')
            need(stable(final_owner) == stable(owner_before), 'Phone94OwnerChangedAfterCandidateRelaunch')
            record.update(status='PASS_ISOLATED_PHYSICAL_TRANSIENT_REGRESSION94', candidateDataUnchanged=True,
                          ownerDataUnchanged=True, dataUnchangedAfterNormalRelaunch=True, finalMarkers=self.pending_markers())
        except Exception as error:
            record.update(status='FAIL_ISOLATED_PHYSICAL_TRANSIENT_REGRESSION94', failureType=type(error).__name__)
            if isinstance(error, (RuntimeError, TimeoutError)) and re.fullmatch(r'[A-Za-z0-9]+', str(error)):
                record['failureCategory'] = str(error)
        finally:
            try:
                record['sourcesAfter'] = self.source_guard()
                record['ownerFinal'] = self.owner_snapshot()
                record['ownerPreservedAtExit'] = stable(record['ownerFinal']) == stable(owner_before)
                need(record['ownerPreservedAtExit'], 'Phone94OwnerChangedAtExit')
            except Exception as error:
                record.update(status='FAIL_ISOLATED_PHYSICAL_TRANSIENT_REGRESSION94', finalGuardErrorType=type(error).__name__)
            record['completedUtc'] = phone.utc()
            save(directory / 'Invocation.json', record)
        return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'install', 'launch', 'capture', 'regression'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--name', help='Explicit capture basename; capture action only')
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows device execution required')
    if args.action == 'capture' and not args.name:
        parser.error('Capture requires an explicit simple --name')
    try:
        candidate = Candidate(args.build)
        record = candidate.capture(args.name) if args.action == 'capture' else getattr(candidate, args.action)()
        print(json.dumps({'status': record['status'], 'ownerMutation': False, 'package': PACKAGE}), flush=True)
        return 1 if record['status'].startswith('FAIL_') else 0
    except Exception as error:
        # subprocess exceptions can embed the private -s selector. Never print
        # their repr/traceback or command; retain only bounded safe categories.
        record = {'status': 'FAIL_ROOT_PHONE94_ACTION', 'utc': phone.utc(), 'action': args.action,
                  'failureType': type(error).__name__, 'ownerMutation': False, 'package': PACKAGE}
        if isinstance(error, RuntimeError) and re.fullmatch(r'[A-Za-z0-9]+', str(error)):
            record['failureCategory'] = str(error)
        save(OUT / 'Phone/Device01/Failures' / (uuid.uuid4().hex + '.json'), record)
        print(json.dumps(record), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
