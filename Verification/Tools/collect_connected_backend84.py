"""Validate checkpoint84 frozen connected-app evidence; publish explicitly.

Reads hashes and reports only. Never runs Unity, a worker, a service, ADB or a
payment request. Internal Android compilation is not installation acceptance.
"""
import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/ServerGameplay83'
APP = 'VerifiedAppWithJNI'
STATUS = 'PASS_CONNECTED_BACKEND84_TARGETED_NATIVE_AND_INTERNAL_COMPILE_WITH_EXTERNAL_GATES'
MAIN = {
    'AccountContracts': ('Native/AccountContracts.json', 'PASS_NATIVE_SERVER_ACCOUNT83_CONTRACTS', 91, 8),
    'AccountHttp': ('Native/AccountHTTP.json', 'PASS_NATIVE_SERVER_ACCOUNT83_CONNECTED_HTTP', 54, 12),
    'ServerCore': ('Native/ServerGameplay.json', 'PASS_NATIVE_SERVER_GAMEPLAY83_CORE', 55, 14),
    'SocialHttp': ('Native/Social82_HTTP.json', 'PASS_NATIVE_SOCIAL82_HTTP', 17896, 19),
    'ServerHttp': ('Native/ConnectedHTTP.json', 'PASS_NATIVE_SERVER_GAMEPLAY83_CONNECTED_HTTP', 302, 8),
    'SocialExpiry': ('Native/SocialExpiry83_HTTP.json', 'PASS_NATIVE_SOCIAL_EXPIRY83_HTTP', None, 3),
}
EXPIRY_INPUTS = {
    'Unity/Assets/HeartOfTheRain/App/OnlineSocial/Runtime/OnlinePlayersPage82.cs',
    'Unity/Assets/HeartOfTheRain/App/OnlineSocial/Runtime/OnlineTeamsPage82.cs',
    'Unity/Assets/HeartOfTheRain/App/ServerRewards/Runtime/ServerRewardsSession.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/SocialPaging83Verification.cs',
}
COMPAT = {
    'Identity': ('Native/Identity82.json', 'PASS_NATIVE_IDENTITY82'),
    'Checks': ('Native/Checks.json', 'PASS_NATIVE_EDITOR_CHECKS'),
    'ProfileChecks': ('Native/ProfileChecks.json', 'PASS_NATIVE_PROFILE_TRANSACTIONS'),
    'PlaySmoke': ('Native/PlaySmoke.json', 'PASS_NATIVE_PLAY_SMOKE'),
    'PortraitChecks': ('Native/PortraitChecks.json', 'PASS_NATIVE_PORTRAIT_CHECKS'),
    'Guard': ('Native/RuStore81.json', 'PASS_NATIVE_RUSTORE81_RELEASE_GUARD'),
    'Preflight': ('Native/Release_Preflight.json', 'BLOCKED_RUSTORE_EXTERNAL_CONFIGURATION_AND_INTEGRATION'),
    'AndroidBuild': ('Android_Build.json', 'PASS_ANDROID_DEVELOPMENT_BUILD'),
    'AndroidReleaseBuild': ('Android_Release_Build.json', 'PASS_ANDROID_RELEASE_COMPILE_BUILD'),
}
REVIEWED_SOCIAL = {
    'Native/SocialPlayers82/Players_Russian.png',
    'Native/SocialPlayers82/DirectUnread_Russian.png',
    'Native/SocialPlayers82/BlockedPlayers_Russian.png',
    'Native/SocialPlayers82/UnblockPlayer_Russian.png',
    'Native/SocialTeams82/OlderMessages_Russian.png',
}
REMAINING = [
    'Current ordinary-app Android startup, touch/visual/payment and physical-device acceptance; ordinary installed QA app remains81. Separate-package lifecycle evidence has its own explicit scope.',
    'Explicit deployment/HTTPS, operations monitoring and recovery drills on the actual host.',
    'Real RuStore Console IDs, signing and SDK build profile; sandbox checkout, bank return, lost-reply, refund and fulfillment acceptance.',
    'No automatic local-profile migration; server mode requires explicit configuration and starts a separate managed account.',
    'Rain Cup remains practice with simulated rivals; no live competition or moderation staffing certification.',
    'Natural approved model-fault occurrence, wider long-session/gameplay performance and physical-device coverage.',
]


def need(value, message):
    if not value:
        raise AssertionError(message)


def digest(path):
    with io_path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def io_path(path):
    """Long frozen Android Java paths retain their normal public identity."""
    value = Path(path).resolve()
    raw = str(value)
    if os.name == 'nt' and not raw.startswith('\\\\?\\'):
        return Path('\\\\?\\UNC\\' + raw[2:] if raw.startswith('\\\\') else '\\\\?\\' + raw)
    return value


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def clean(report, label):
    need(not any(report.get(key) for key in ('error', 'errors', 'failures', 'failed')), label + ': reported failure')


class Proof:
    def __init__(self, root=ROOT, output=OUT):
        self.root, self.output = root.resolve(), output.resolve()
        self.artifacts, self.external = {}, {}
        self.cached = {}

    @staticmethod
    def safe(base, name):
        need(isinstance(name, str) and name and '\\' not in name, 'Invalid evidence path')
        value = (base / name).resolve()
        need(value.is_relative_to(base) and io_path(value).is_file(), 'Missing/unsafe evidence: ' + name)
        return value

    def sha(self, path):
        if path not in self.cached:
            self.cached[path] = digest(path)
        return self.cached[path]

    def file(self, name, expected=None):
        path = self.safe(self.output, name)
        value = self.sha(path)
        need(expected is None or value == expected, 'Evidence hash mismatch: ' + name)
        self.artifacts[path.relative_to(self.output).as_posix()] = value
        return path

    def ext(self, name, expected=None):
        path = self.safe(self.root, name)
        value = self.sha(path)
        need(expected is None or value == expected, 'Input hash mismatch: ' + name)
        self.external[path.relative_to(self.root).as_posix()] = value
        return path

    def read(self, name, expected=None):
        return json.loads(self.file(name, expected).read_text('utf-8-sig'))


def source_proof(proof):
    source = proof.read('VerifiedAppWithJNI/Sources.json')
    files, changed = source['files'], source['changedOrNewInputs']
    baseline_path = proof.ext('Verification/Evidence/RuStore81/Source_SHA256.json')
    baseline = json.loads(baseline_path.read_text('utf-8-sig'))['files']
    need(len(files) == 5321 and len(baseline) == 5182 and len(changed) == 155, 'Unexpected frozen input counts')
    need(set(baseline) <= set(files), 'Baseline Unity inputs removed')
    actual_changed = {name: value for name, value in files.items() if baseline.get(name) != value}
    need(changed == actual_changed and source['unchangedBaselineInputs'] == len(files) - len(changed) == 5166,
         'Changed/new and unchanged baseline partition differs')
    prior = proof.read('VerifiedApp/Sources.json')['files']
    repaired = {name for name in files if prior.get(name) != files[name]}
    need(set(files) == set(prior) and repaired == {'Unity/Packages/manifest.json', 'Unity/Packages/packages-lock.json'} | EXPIRY_INPUTS,
         'Final repair changed inputs beyond two package files and four approved access-expiry inputs')
    manifest = proof.read('VerifiedAppWithJNI/Inputs/Unity/Packages/manifest.json')
    lock = proof.read('VerifiedAppWithJNI/Inputs/Unity/Packages/packages-lock.json')
    need(manifest['dependencies']['com.unity.modules.androidjni'] == '1.0.0'
         and lock['dependencies']['com.unity.modules.androidjni']['version'] == '1.0.0'
         and lock['dependencies']['com.unity.modules.androidjni']['source'] == 'builtin', 'AndroidJNI must remain the pinned built-in module')
    archive_base = io_path(proof.output / 'VerifiedAppWithJNI/Inputs')
    archived = {p.relative_to(archive_base).as_posix() for p in archive_base.rglob('*') if p.is_file()}
    need(archived == set(changed), 'Frozen changed/new archive membership differs')
    for name, value in files.items():
        need(re.fullmatch(r'[0-9a-f]{64}', value) and name.startswith('Unity/'), 'Invalid input binding')
        if name in changed:
            proof.file('VerifiedAppWithJNI/Inputs/' + name, value)
        else:
            need(baseline[name] == value, 'Unbound baseline fallback: ' + name)
        # Unchanged art is deliberately resolved against its exact baseline hash;
        # this is not a claim that all assets were duplicated into the archive.
        proof.ext(name, value)
    return files


def invocation(proof, folder, expected):
    report = proof.read(folder + '/Invocation.json')
    need(len(report['runs']) == len(expected) and {row['suite'] for row in report['runs']} == set(expected)
         and all(row['exitCode'] == 0 for row in report['runs']), folder + ': suite invocation differs')
    if folder == 'VerifiedAppWithJNI':
        need(report.get('servicesStopped') is True, folder + ': fixture processes not confirmed stopped')
        need({s['kind'] for s in report['services']} == {'Gateway', 'Social'}, 'Missing isolated HTTP fixture')
        scripts = {'Gateway': 'serve_server_gameplay83_fixture.py', 'Social': 'serve_identity82_fixture.py'}
        for service in report['services']:
            metadata = service['connection']; uri = urlsplit(metadata['origin'])
            need(uri.scheme == 'http' and uri.hostname == '127.0.0.1' and uri.port and metadata['pid'] > 0,
                 'Connected proof must use explicit isolated loopback fixture')
            proof.ext('Verification/Tools/' + scripts[service['kind']], service['scriptSHA256'])
            if service['kind'] == 'Gateway':
                proof.ext('Verification/Evidence/ServerReplay83/Native/Fixtures/L08_Continue1.job.json', metadata['continueJobSHA256'])
                proof.ext('Verification/Evidence/ServerReplay83/Standalone/27891d602a644d7b9afb15cf6af28074/Local_Approval.json', metadata['approvalSHA256'])
    elif report.get('services'):
        need(report.get('servicesStopped') is True, folder + ': declared fixture processes not confirmed stopped')
    return report


def suite(proof, folder, mode, report_path, status, files):
    process = proof.read(folder + '/Native/' + mode + '_Process.json')
    need(process['mode'] == mode and process['exitCode'] == 0 and process['timedOut'] is False
         and process['version'].startswith('2022.3.62f3_')
         and utc(process['startedUtc']) < utc(process['finishedUtc']), mode + ': process/pinned Editor failure')
    if mode in COMPAT and process.get('delegatedProcess') is not None:
        delegated = process['delegatedProcess']
        need(delegated['mode'] == mode and delegated['exitCode'] == 0
             and delegated['timedOut'] is False and delegated['version'].startswith('2022.3.62f3_')
             and utc(process['startedUtc']) <= utc(delegated['startedUtc']) < utc(delegated['finishedUtc']) <= utc(process['finishedUtc']),
             mode + ': delegated actual build process/restoration failed')
        if mode in ('AndroidBuild', 'AndroidReleaseBuild'):
            need(process['temporaryBuildSettingsRestored'] is True, mode + ': temporary build settings not restored')
    else:
        need(type(process['pid']) is int and process['pid'] > 0, mode + ': actual native PID absent')
    need(process['report'] == report_path and process['inputCount'] == len(files)
         and process['intentionalConfigurationMutation'] is False, mode + ': report/source scope differs')
    for key, hash_key in (('sourceManifest', 'sourceSHA256'), ('afterSourceManifest', 'afterSourceSHA256')):
        manifest = proof.read(folder + '/' + process[key], process[hash_key])
        need(manifest['files'] == files, mode + ': source differs from frozen connected app')
    delta = proof.read(folder + '/Native/' + mode + '_Input_Delta.json')
    need(delta == {'changed_existing': [], 'added': [], 'removed': []}, mode + ': source mutated during process')
    report = proof.read(folder + '/' + report_path, process['reportSHA256'])
    log = proof.file(folder + '/' + process['log'], process['logSHA256'])
    log_text = log.read_text('utf-8-sig', errors='replace')
    need(not re.search(r'\berror CS\d+\b', log_text), mode + ': C# compiler error in log')
    engine_pids = set()
    for line in log_text.splitlines():
        if not line.startswith('##utp:'):
            continue
        try:
            event = json.loads(line[6:])
        except ValueError:
            continue
        if event.get('type') in ('MemoryLeaks', 'EditorInfo', 'ProjectInfo', 'PlayerBuildInfo') and type(event.get('processId')) is int:
            need(event['processId'] > 0, mode + ': invalid native engine log PID')
            engine_pids.add(event['processId'])
    if engine_pids:
        need(len(engine_pids) == 1 and (process['pid'] is None or process['pid'] in engine_pids), mode + ': native engine log PID differs')
    report['_actualNativePid'] = next(iter(engine_pids)) if engine_pids else process['pid']
    report['_pidEvidence'] = 'SHA-bound engine log ##utp.processId' if engine_pids else 'direct process metadata' if process['pid'] else 'delegated exit/version/time only; PID unavailable'
    need(report['status'] == status, mode + ': report status differs')
    clean(report, mode)
    if 'unity' in report:
        need(report['unity'] == '2022.3.62f3', mode + ': report Unity version differs')
    return report


def main_suites(proof, files):
    invocation(proof, 'VerifiedAppWithJNI', MAIN)
    reports, captures = {}, []
    for mode, (path, status, checks, count) in MAIN.items():
        value = suite(proof, 'VerifiedAppWithJNI', mode, path, status, files)
        need(value['checks'] == checks if checks is not None else type(value['checks']) is int and value['checks'] > 0, mode + ': checks differ')
        if mode in ('AccountContracts', 'ServerCore'):
            need(value['cases'] == len(value['passed']) == count, mode + ': cases differ')
        elif mode == 'SocialExpiry':
            need(len(value['passed']) == count, mode + ': expiry scenarios differ')
        else:
            need(len(value['captures']) == count, mode + ': capture count differs')
            captures.extend(value['captures'])
        if 'ordinaryProfilesBefore' in value:
            need(value['ordinaryProfilesBefore'] == value['ordinaryProfilesAfter'], mode + ': ordinary profiles changed')
        need(value.get('android', False) is False and value.get('androidKeystore', False) is False
             and value.get('productionEnabled', False) is False, mode + ': unsupported device/production claim')
        reports[mode] = value
    core, account, social, gateway = (reports[k] for k in ('ServerCore', 'AccountHttp', 'SocialHttp', 'ServerHttp'))
    need((core['restoreComparisons'], core['restoreFutureCommands'], core['restoreContinues'], core['restoreDifferentOrders']) == (12, 90, 1, 12)
         and not core['restoreCounterexamples'], 'Restored board future-command parity differs')
    for key in ('actualHttp', 'selectedThroughOrdinaryHost', 'maskedRecovery', 'clipboardOnly', 'explicitLogout', 'explicitRecovery',
                'explicitDeletion', 'explicitFreshGuest', 'settingsReturn', 'localAppearanceUnchanged', 'rejectedRecoveryBlocked',
                'rejectedRecoveryCanRestart', 'recoveredRemoteAttemptPreserved', 'remoteAttemptExplicitlyForfeited'):
        need(account[key] is True, 'Account lifecycle acceptance missing: ' + key)
    # The trace includes its successful signed-challenge request before the
    # rejected recovery response, rather than two different rejection cases.
    need(account['rejectedRecoveryReady'] is False and account['rejectedRecoveryHttpStatuses'][-1] in (401, 422)
         and account['finalCoins'] == 1250 and account['finalLives'] == 5 and account['recoveredLives'] == 4,
         'Recovery rejection/financial lifecycle differs')
    need(social['cases'] == len(social['passed']) == 15 and social['actualHttp'] is True
         and social['ordinaryProfilesUnchanged'] and social['languagePreferenceUnchanged']
         and not social['localEconomyMutated'] and (social['pagingTransportChecks'], social['visibleReadChecks'], social['blockedPageChecks']) == (10, 5, 2),
         'Bounded social/privacy controls missing')
    need(social['actualPageCaptures'] == 19 and social['layoutCases'] == 175, 'Social rendering scope differs')
    for key in ('actualHttp', 'actualPinnedWorker', 'serverProfileRenameAndRecords', 'localAppearanceUnchanged', 'naturalVictoryObserved',
                'naturalHomeRevealObserved', 'dailyRevealObserved', 'ordinaryRewardPages', 'portraitSettingsRestored', 'readonlyHomeRewardBadges'):
        need(gateway[key] is True, 'Connected gameplay/reward acceptance missing: ' + key)
    need((gateway['paidTools'], gateway['paidContinues'], gateway['restoredShopBoards']) == (1, 1, 1)
         and (gateway['afterWinCoins'], gateway['dailyClaimCoins'], gateway['finalCoins'], gateway['finalStars'], gateway['finalLives'], gateway['finalCompleted']) == (400, 50, 450, 1, 4, 8)
         and (gateway['portraitWidth'], gateway['portraitHeight'], gateway['homeMetadataBatches']) == (900, 1600, 2), 'Connected wallet/reward/badge results differ')
    expiry = reports['SocialExpiry']
    for key in ('actualHttp', 'actualOrdinaryGateway', 'injectedMonotonicAccessAge', 'playersRenewed', 'teamsRenewed', 'pendingPreserved',
                'noAutomaticPendingWrite', 'samePlayerAndWallet', 'selectedPeerPreserved', 'homeBadgesRenewed'):
        need(expiry[key] is True, 'Access-expiry acceptance missing: ' + key)
    need(expiry['localExpiryInjections'] == 3 and expiry['signedRefreshRequests'] >= 6
         and expiry['signedRefreshRequests'] == expiry['finalSignedRequests'] - expiry['initialSignedRequests']
         and expiry['homeRenewalsAfter'] == expiry['homeRenewalsBefore'] + 1
         and expiry['homeBatchesAfter'] > expiry['homeBatchesBefore']
         and expiry['balancesBefore'] == expiry['balancesAfter']
         and expiry['passed'] == ['Players polling, protected pending and selection retention', 'Teams manualRetry renewal', 'Idle Home badge access renewal'],
         'Injected local-expiry/actual HTTP refresh, retained intent or Home renewal counters differ')
    need(len(captures) == len(set(captures)) == 39 and REVIEWED_SOCIAL <= set(captures), 'Capture matrix differs')
    images = []
    for name in captures:
        path = proof.file('VerifiedAppWithJNI/' + name)
        header = path.read_bytes()[:24]
        need(header[:8] == b'\x89PNG\r\n\x1a\n' and len(header) == 24, 'Invalid capture PNG: ' + name)
        width, height = struct.unpack('>II', header[16:24])
        need(width > 0 and height > width, 'Expected actual portrait capture: ' + name)
        reviewed = name.startswith(('Native/Account/', 'Native/RewardPages/')) or name in REVIEWED_SOCIAL
        images.append({'path': 'VerifiedAppWithJNI/' + name, 'sha256': proof.sha(path), 'width': width, 'height': height,
                       'actuallyReviewed': reviewed, 'reviewScope': 'Root agent explicit actual image inspection' if reviewed else 'Captured; no individual visual inspection claimed'})
    need(sum(image['actuallyReviewed'] for image in images) == 25, 'Actual sampled review scope differs')
    visual = proof.read('VerifiedAppWithJNI/Visual_Review.json')
    expected_review = {image['path'].removeprefix('VerifiedAppWithJNI/'): image['sha256'] for image in images if image['actuallyReviewed']}
    need(visual['status'] == 'ACTUAL_SAMPLED_CONNECTED84_NATIVE_REVIEW_WITH_EXTERNAL_GATES'
         and visual['sourcesSHA256'] == proof.sha(proof.file('VerifiedAppWithJNI/Sources.json'))
         and len(visual['inspected']) == 25 and set(visual['inspected']) == set(expected_review)
         and visual['artifactSHA256'] == expected_review and visual['scope'] and visual['limitations'],
         'Final package-bound actual visual review is missing, stale or broader than the exact25 inspected originals')
    return reports, images


def backend(proof):
    folder = 'Backend/Verified324/'
    value = proof.read(folder + 'Service_Tests.json')
    need(value['status'] == 'PASS_BACKEND_SERVICE_TESTS' and value['tests'] == value['executedTests'] == len(value['passed']) == 324,
         'Backend324 suite incomplete')
    clean(value, 'Backend324')
    need(not value['skipped'] and not value['failureLocations'] and value['actualPinnedWorkerIntegration'] is True
         and value['sourceSHA256'] == value['sourceSHA256After'] and not value['sourceInputsChangedDuringRun'], 'Backend skipped, changed, or real-worker proof absent')
    need(len(value['sourceSHA256']) == 73 and len(set(value['passed'])) == 324, 'Backend source/test membership differs')
    name = 'tests.test_replay_native_integration.NativeReplayBrokerIntegration.test_authenticated_native_full_history_continue_win_recovery'
    need(name in value['passed'] and len([n for n in value['passed'] if n.startswith('tests.test_bounded_social_reads.')]) == 11,
         'Actual worker or bounded social cases missing')
    need('Backend/README.md' in value['sourceSHA256'], 'Sealed README input missing')
    documentation_delta = []
    for name, expected in value['sourceSHA256'].items():
        proof.file(folder + 'Inputs/' + name, expected)
        if name == 'Backend/README.md':
            current = proof.ext(name)
            if proof.sha(current) != expected:
                documentation_delta.append({'path': name, 'sealed324SHA256': expected, 'currentSHA256': proof.sha(current),
                                            'scope': 'Documentation-only status update after the sealed324 test run; no retest or runtime-change claim.'})
        else:
            proof.ext(name, expected)
    invocation = proof.read(folder + 'Invocation.json')
    need(invocation['optInActualModel'] is True, 'Actual worker invocation not enabled')
    proof.file(folder + 'Local_Approval.json', invocation['approvalSHA256'])
    proof.ext('Verification/Evidence/ServerReplay83/Standalone/27891d602a644d7b9afb15cf6af28074/Local_Approval.json', invocation['approvalSHA256'])
    value['_documentationOnlyAfterTests'] = documentation_delta
    return value


def compatibility(proof, files):
    need((proof.output / 'VerifiedCompatibility').is_dir(), 'VerifiedCompatibility archive is required before publication')
    invocation(proof, 'VerifiedCompatibility', COMPAT)
    reports = {mode: suite(proof, 'VerifiedCompatibility', mode, path, status, files)
               for mode, (path, status) in COMPAT.items()}
    need(reports['Guard']['actualReleaseBlocked'] and reports['Guard']['settingsUnchanged'] and reports['Guard']['preferencesUnchanged'], 'Release guard compatibility differs')
    preflight = reports['Preflight']
    need(preflight['activationReady'] is False and preflight['projectSettingsUnchanged'] is True and preflight['blockers'], 'Release must remain explicitly blocked')
    smoke = reports['PlaySmoke']
    # bootStage records the initial saved onboarding stage, before the smoke's
    # explicit transient review skip. It is not an onboarding-completion claim.
    need(smoke['bootStage'] in ('Prologue', 'Chapter', 'Match', 'Rocket', 'Clear', 'Ready', 'Complete')
         and smoke['bootLevel'] == 1 and len(smoke['checks']) == 18 and smoke['startupWitnessed'] is True,
         'Ordinary app smoke/camera witness failed')
    for mode, development in (('AndroidBuild', True), ('AndroidReleaseBuild', False)):
        build = reports[mode]
        need(build.get('errors', 0) == 0, 'Internal Android build errors')
        # Report field names are retained from the pinned build harness.
        if 'development' in build:
            need(build['development'] is development, 'Internal build profile differs')
    return reports


def historical_preflight_notice(proof):
    name = 'Verification/Evidence/RuStore81/HISTORICAL_PREFLIGHT_ARTIFACT_NOTICE.json'
    path = proof.ext(name)
    notice = json.loads(path.read_text('utf-8-sig'))
    need(notice['status'] == 'HISTORICAL_PREFLIGHT_REPORT_OVERWRITTEN_BY_CHECKPOINT84_RUNNER'
         and notice['historicalExpectedSHA256'] != notice['observedReplacementSHA256'], 'Historical preflight limitation differs')
    proof.ext(notice['diagnosticArchive'], notice['observedReplacementSHA256'])
    return {'notice': name, 'noticeSHA256': proof.sha(path),
            'scope': 'One historical81 preflight report was overwritten; its exact original JSON is unavailable. Preserved original process/log/hash records do not reconstruct that report. Fresh84 preflight is independently required. Baseline81 is used here only for source-hash fallback, not historical release recertification.'}


def internal_apks(proof):
    prefix = 'VerifiedCompatibility/'
    profile = proof.read(prefix + 'APK_Profile.json')
    need(profile['status'] == 'PASS_CONNECTED84_INTERNAL_APKS_STATIC_INSPECTION' and len(profile['artifacts']) == 2, 'Both internal APK static checks required')
    expected = {'Unity/Builds/Verification/HeartOfTheRain_Development.apk', 'Unity/Builds/Verification/HeartOfTheRain_ReleaseCompile.apk'}
    need({row['path'] for row in profile['artifacts']} == expected, 'Internal APK profile membership differs')
    result = []
    for row in profile['artifacts']:
        apk = proof.ext(row['path'], row['sha256'])
        need(apk.stat().st_size == row['bytes'] and row['package'] == 'com.heartoftherain.verification'
             and row['displayName'] == 'Сердце дождя' and row['deviceIdentityJavaClassPresent'] is True
             and row['nativePayProviderAbsent'] is True and row['nativeRuStorePayCoreClassesAbsent'] is True, 'Internal APK package/label/SDK boundary differs')
        artifact = proof.read(prefix + row['staticArtifactReport'])
        need(artifact['sha256'] == row['sha256'] and artifact['bytes'] == row['bytes']
             and artifact['zipalign4KiBPass'] is True and artifact['developmentSignatureVerifies'] is True
             and artifact['elf16KiBLoadSegmentsPass'] is True and artifact['signatureNotes'] and artifact['libraries'],
             'Internal APK signature/alignment/ELF artifact differs')
        for library in artifact['libraries']:
            need(library['load_segments'] and all(segment['alignment'] >= 16384 for segment in library['load_segments']), 'Internal ELF load segment alignment failed')
        folder = Path(row['staticArtifactReport']).parent.as_posix()
        proof.file(prefix + folder + '/Badging.txt')
        proof.file(prefix + folder + '/Manifest.txt')
        result.append({'path': row['path'], 'sha256': row['sha256'], 'bytes': row['bytes'], 'package': row['package']})
    return result


def android_lifecycle(proof, files):
    prefix = 'Android/Connected84/'
    report = proof.read(prefix + 'Report.json')
    need(report['status'] == 'PASS_ACTUAL_ANDROID_CONNECTED84_DISTINCT_PROCESS_LIFECYCLE' and not report['errors'], 'Isolated Android lifecycle did not pass')
    need(report['qa_serial'] == 'emulator-5558' and report['package'] == 'com.heartoftherain.connected84fixture'
         and report['sourceFreezeSHA256'] == proof.sha(proof.file('VerifiedAppWithJNI/Sources.json'))
         and utc(report['startedUtc']) < utc(report['finishedUtc']), 'Android lifecycle target/source/time differs')
    target = report['qa_target']
    need(target['serial'] == report['qa_serial'] and target['isolated_clone'] is True, 'Android sealed isolated QA target differs')
    proof.ext(target['target_record'], target['target_record_sha256'])
    for key in ('ordinaryPackagesNeverStoppedOrInstalled', 'allAdbCommandsTargetSealedQA2', 'ordinaryDataUnchanged', 'ownFixtureStopped'):
        need(report[key] is True, 'Android isolation/cleanup failed: ' + key)
    need(report['ordinaryDataBefore'] == report['ordinaryDataAfter'] and report['ordinaryAttemptGuard']['activeAttempts'] == 0,
         'Ordinary app hashes/active-attempt guard differ')
    ordinary = report['ordinaryDataBefore']
    need(ordinary['preferences'] and any(name.startswith('Profiles/') and name.endswith('.json') for name in ordinary['externalFiles']),
         'Ordinary profile/preference hash control is vacuous')
    gateway, reverse = report['gateway'], report['adbReverse']
    need(gateway['owned'] is True and gateway['pid'] > 0 and gateway['connectionReady'] is True
         and gateway['credentialEnvironmentInherited'] is False and gateway['ownProcessStopped'] is True
         and gateway['syntheticCompleted7Unlock'] is True and gateway['noOperatorSeedUsedByLevel1'] is True, 'Own gateway lifecycle/synthetic fixture scope differs')
    need(reverse['noRebind'] is True and 1024 <= reverse['ownedDevicePort'] <= 65535 and 1024 <= reverse['ownHostPort'] <= 65535
         and sorted(reverse['preexisting']) == sorted(reverse['afterOwnCleanup']), 'Owned reverse cleanup changed unrelated state')
    proof.ext('Verification/Evidence/ServerReplay83/Standalone/27891d602a644d7b9afb15cf6af28074/Local_Approval.json', gateway['approvalSHA256'])
    build, process, preparation = (proof.read(prefix + name) for name in ('Build.json', 'Build_Process.json', 'Preparation.json'))
    need(build['status'] == 'PASS_ISOLATED_CONNECTED84_ANDROID_ASSEMBLY' and build['errors'] == 0 and not build['errorsStatic']
         and build['unity'] == preparation['unity'] == '2022.3.62f3'
         and build['package'] == preparation['package'] == report['package'], 'Isolated Android build failed')
    for key in ('development', 'arm64', 'il2cpp', 'min26', 'noPaySdkDefine', 'exactBaselineAssetsBefore', 'exactBaselineAssetsAfter'):
        need(build[key] is True, 'Isolated Android build flag missing: ' + key)
    need(process['status'] == 'COMPLETED_ROOT_ISOLATED_ANDROID_BUILD_PROCESS' and process['exitCode'] == 0 and process['pid'] > 0
         and process['project'] == preparation['project']
         and utc(process['startedUtc']) < utc(process['finishedUtc']) <= utc(report['startedUtc']), 'Isolated Android actual build process differs')
    need(preparation['status'] == 'PREPARED_ISOLATED_CONNECTED84_ANDROID_PROJECT_NOT_BUILT' and preparation['baselineInputs'] == 5321
         and preparation['baselineManifestSHA256'] == build['baselineManifestSHA256'] == report['sourceFreezeSHA256'], 'Android preparation baseline differs')
    copied_assets = {name: value for name, value in preparation['copiedSourceSHA256'].items() if name.startswith('Assets/')}
    baseline_assets = {name.removeprefix('Unity/'): value for name, value in files.items() if name.startswith('Unity/Assets/')}
    need(copied_assets == baseline_assets and len(copied_assets) == build['baselineAssetInputs'], 'Fixture copied app assets differ from frozen source')
    need(build['apkSHA256'] == report['apkSHA256'] == report['installedApkSHA256'], 'Built/installed fixture APK differs')
    for name, expected in preparation['generatedSources'].items():
        proof.file(prefix + 'Inputs/' + Path(name).name, expected)
    proof.file(prefix + 'Inputs/prepare_connected84_android.py', preparation['preparerSHA256'])
    proof.ext('Verification/Tools/Connected84/prepare_connected84_android.py', preparation['preparerSHA256'])
    helper = proof.file(prefix + 'Inputs/run_connected84_root.py', report['helperSHA256'])
    proof.ext('Verification/Tools/Connected84/run_connected84_root.py', report['helperSHA256'])
    external = report['externalSHA256']
    project = preparation['project']
    need(external[project + '/Build/Build.json'] == proof.sha(proof.file(prefix + 'Build.json'))
         and external[project + '_Preparation.json'] == proof.sha(proof.file(prefix + 'Preparation.json')),
         'Raw lifecycle build/preparation bindings differ')
    proof.ext(project + '/Build/Connected84.apk', build['apkSHA256'])
    # Compile ONLY the two I/O-free validator definitions. The orchestration
    # module, imports, Runner, CLI and process/build/device code never execute.
    tree = ast.parse(helper.read_text('utf-8-sig'))
    validators = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ('validate_stage', 'validate_sequence')]
    need(len(validators) == 2 and all(not node.decorator_list and not node.args.defaults and not node.args.kw_defaults for node in validators), 'Pure stage validator definitions differ')
    stages = ('setup', 'reopen', 'logout', 'closed', 'recover', 'recovered', 'delete', 'deleted')
    namespace = {'re': re, 'PACKAGE': report['package'], 'STAGES': stages, 'require': need,
                 'digest': lambda value: isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None}
    exec(compile(ast.Module(body=validators, type_ignores=[]), str(helper), 'exec'), namespace)
    checked = []
    need(len(report['stages']) == 8, 'All eight actual Android stages required')
    previous_pull = utc(report['startedUtc'])
    for name, recorded in zip(stages, report['stages']):
        path = prefix + 'Stage_' + name + '.json'
        raw = proof.read(path)
        original = 'Runs/' + report['runId'] + '/Stage_' + name + '.json'
        need(report['artifactSHA256'][original] == proof.sha(proof.file(path)), 'Raw stage archive SHA differs')
        value = namespace['validate_stage'](raw, name, report['scopeHash'], report['originHash'])
        need(all(recorded[key] == item for key, item in value.items()) and recorded['observedLivePid'] == value['pid']
             and previous_pull <= utc(recorded['precedingForceStopUtc']) < utc(recorded['pulledUtc']) <= utc(report['finishedUtc']), 'Stage process observation/sequence differs')
        previous_pull = utc(recorded['pulledUtc']); checked.append(value)
    namespace['validate_sequence'](checked)
    archive = proof.read(prefix + 'Archive.json')
    need(archive['status'] == 'SEALED_ACTUAL_ANDROID_CONNECTED84_LIFECYCLE_ARCHIVE'
         and archive['sourceFreezeSHA256'] == report['sourceFreezeSHA256'] and archive['rootRunId'] == report['runId']
         and archive['actualDistinctPids'] == [item['pid'] for item in checked]
         and archive['checks'] == sum(item['checks'] for item in checked) == 101
         and archive['ordinaryExternalFiles'] == len(ordinary['externalFiles']) == 324
         and archive['ordinaryPreferenceFiles'] == len(ordinary['preferences']) == 1
         and archive['originalBeforeEqualsFinalAfter'] is True, 'Root Android archive source/process/data summary differs')
    for name, expected in archive['artifactSHA256'].items():
        proof.file(prefix + name, expected)
    members = {path.relative_to(proof.output / prefix).as_posix() for path in (proof.output / prefix).rglob('*') if path.is_file()}
    need(members == set(archive['artifactSHA256']) | {'Archive.json'}, 'Android archive contains unbound/missing files')
    return {'verified': True, 'package': report['package'], 'apkSHA256': report['apkSHA256'], 'qaSerial': report['qa_serial'],
            'processes': 8, 'checks': sum(stage['checks'] for stage in checked), 'stages': list(stages),
            'actualPids': [item['pid'] for item in checked], 'ordinaryExternalFiles': len(ordinary['externalFiles']),
            'ordinaryPreferenceFiles': len(ordinary['preferences']),
            'ordinaryDataUnchanged': True, 'actualAndroidKeystoreNonexportability': True,
            'scope': 'Separate-package IL2CPP ARM64 fixture, programmatic frozen ordinary host/Play/Hammer/Quit/account service calls, eight externally observed process PIDs. Synthetic completed7 unlock. Not ordinary startup routing, physical input, payment or hardware attestation.'}


def collect(proof, require_compatibility=True):
    files = source_proof(proof)
    reports, captures = main_suites(proof, files)
    service = backend(proof)
    historical = historical_preflight_notice(proof)
    compatible = compatibility(proof, files) if require_compatibility else None
    apks = internal_apks(proof) if compatible else []
    android = android_lifecycle(proof, files) if require_compatibility or (proof.output / 'Android/Connected84/Report.json').is_file() else {'verified': False}
    return {
        'status': STATUS if compatible else 'PASS_CONNECTED_BACKEND84_MAIN_NATIVE_PENDING_COMPATIBILITY',
        'utc': datetime.now(timezone.utc).isoformat(), 'sourceCheckpoint': 84,
        'scope': 'Targeted pinned-native connected review, separately scoped isolated Android lifecycle and internal Android compilation; ordinary-app/physical-device/release gates remain explicit.',
        'sourceManifest': 'VerifiedAppWithJNI/Sources.json', 'sourceManifestSHA256': proof.sha(proof.file('VerifiedAppWithJNI/Sources.json')),
        'dependencyRepair': {'module': 'com.unity.modules.androidjni', 'version': '1.0.0', 'source': 'builtin',
                             'changedFiles': ['Unity/Packages/manifest.json', 'Unity/Packages/packages-lock.json'],
                             'additionalApprovedExpiryInputs': sorted(EXPIRY_INPUTS),
                             'artEngineAndOtherInputsUnchangedFromPriorFrozenApp': True},
        'frozenUnityInputs': len(files), 'archivedChangedOrNewInputs': 155, 'unchangedBaseline81FallbackInputs': 5166,
        'mainSuites': len(reports), 'mainChecks': sum(value['checks'] for value in reports.values()),
        'baseFiveChecks': 18398, 'expiryChecks': reports['SocialExpiry']['checks'],
        'expiryScope': 'Three local monotonic accessAt901s injections with actual signed loopback session renewal and generation-fenced controller/metadata recovery. Not a900second wall-clock soak or Android lifecycle proof.',
        'compatibilitySuites': len(compatible) if compatible else 0,
        'internalApkArtifacts': apks,
        'compatibility': {'requiredForPublication': True, 'completed': compatible is not None,
                          'reports': {mode: {'status': value['status'], 'report': COMPAT[mode][0],
                                             'actualNativePid': value['_actualNativePid'], 'pidEvidence': value['_pidEvidence']}
                                      for mode, value in (compatible or {}).items()}},
        'backendTests': service['executedTests'], 'backendInputs': len(service['sourceSHA256']), 'backendSkipped': 0,
        'backendCurrentStrictInputCount': 72, 'backendDocumentationOnlyAfterTests': service['_documentationOnlyAfterTests'],
        'actualApprovedWorkerBackendIntegration': True,
        'ordinaryServerReviewIntegrated': True, 'localProfileMigration': False,
        'androidInstallVerified': False, 'installedOrdinaryCheckpoint': 81, 'productionEnabled': False,
        'ordinaryAndroidInstallVerified': False, 'isolatedAndroidLifecycle': android,
        'captures': captures, 'captureCount': len(captures), 'explicitlyReviewedCaptureCount': 25,
        'explicitlyReviewedCapturePaths': [image['path'] for image in captures if image['actuallyReviewed']],
        'visualReviewScope': 'Root agent reported actual view_image inspection of all12 Account, all8 reward/Home and five explicitly listed social originals. Other14 captures are linked without individual review claims.',
        'historicalEvidenceLimitation': historical,
        'remaining': REMAINING, 'compatibilityRequiredForPublication': True,
        'artifactSHA256': proof.artifacts, 'externalInputSHA256': proof.external,
    }


def render_html(summary):
    esc = html.escape
    android = summary.get('isolatedAndroidLifecycle', {})
    android_scope = ('Eight distinct observed Android process PIDs; ' + str(android['checks']) + ' checks; same player and exact wallet, protected Keystore, key rotation, logout/recovery/deletion, ordinary hashes unchanged. Separate fixture package; no ordinary startup/touch/payment claim.'
                     if android.get('verified') else 'Pending isolated fixture lifecycle; no Android acceptance is claimed by this draft.')
    rows = []
    for image in summary['captures']:
        tag = 'Actually inspected' if image['actuallyReviewed'] else 'Captured; individual review not claimed'
        rows.append('<figure><a href="' + esc(image['path']) + '"><img loading="lazy" src="' + esc(image['path']) + '" alt="' + esc(Path(image['path']).stem) + '"></a><figcaption>' + esc(Path(image['path']).stem) + '<br><b>' + tag + '</b></figcaption></figure>')
    gates = ''.join('<li>' + esc(value) + '</li>' for value in summary['remaining'])
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Connected backend84 review</title>
<style>body{background:#102c3b;color:#edf5f5;font:16px/1.5 system-ui;margin:0}main{max-width:1200px;margin:auto;padding:28px}a{color:#a8e6df}h1,h2{line-height:1.2}.notice{background:#244552;border-left:4px solid #e9c878;padding:16px}table{border-collapse:collapse;width:100%;margin:20px 0}td,th{border:1px solid #52717c;padding:9px;text-align:left}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:18px}figure{margin:0;background:#1c3c4a;padding:10px}img{width:100%;height:320px;object-fit:contain;background:#132f3d}figcaption{font-size:12px;overflow-wrap:anywhere}code{overflow-wrap:anywhere}small{color:#bed1d5}</style><main>
<h1>Connected app and backend · checkpoint84</h1><p class="notice"><b>Connected native review, separately scoped isolated Android lifecycle and internal compile.</b> The ordinary installed QA app remains81. No current ordinary-app Android startup/touch acceptance, live payment, production deployment, local-save migration or whole-game smoothness approval is claimed.</p>
<p>Explicit server configuration connects managed accounts, authoritative gameplay settlement, Profile/Friends/Teams/chat, reward pages and read-only Home badges. Two package files add the built-in AndroidJNI module after the first Android compile exposed the missing dependency. Four further inputs repair access-expiry recovery in Players, Teams and idle Home with a focused verifier; artwork, engine and other inputs retain the prior frozen app hashes. Local mode keeps its separate existing profile.</p>
<table><tr><th>Evidence</th><th>Verified scope</th></tr><tr><td>Backend</td><td>324 tests, no skips; 73 frozen inputs; actual approved Unity worker integration</td></tr><tr><td>Six main native suites</td><td>''' + str(summary['mainChecks']) + ''' checks: the base five retain 18,398; access-expiry adds ''' + str(summary['expiryChecks']) + '''</td></tr><tr><td>Expiry scope</td><td>Three local accessAt901s injections plus actual signed session HTTP renewal, retained pending intent/selection and fresh Home metadata. This is not a 15-minute wall-clock soak.</td></tr><tr><td>Source binding</td><td>5,321 Unity inputs: 155 archived changed/new and 5,166 unchanged baseline81 files resolved by exact hash; each process has zero input delta</td></tr><tr><td>Compatibility</td><td>''' + str(summary['compatibilitySuites']) + ''' suites including both internal Android build profiles; publication requires all 9</td></tr><tr><td>Separate Android lifecycle</td><td>''' + esc(android_scope) + '''</td></tr><tr><td>Capture matrix</td><td>39 actual portrait captures; 25 explicitly inspected originals, 14 linked without an individual visual-review claim</td></tr></table>
<p><a href="Summary.json">Validated summary and artifact hashes</a> · <a href="VerifiedAppWithJNI/Sources.json">Frozen source manifest</a> · <a href="Backend/Verified324/Service_Tests.json">Backend report</a> · <a href="VerifiedAppWithJNI/Invocation.json">Native invocation</a></p>
<p><small>Historical evidence limitation: one checkpoint81 preflight JSON was overwritten by the copied runner and its exact original is unavailable. This page uses the81 source manifest as a hash fallback and requires a fresh84 preflight; it does not recertify that old report. <a href="../RuStore81/HISTORICAL_PREFLIGHT_ARTIFACT_NOTICE.json">Preserved notice and diagnostic binding</a>.</small></p>
<h2>Remaining launch gates</h2><ul>''' + gates + '''</ul><h2>Actual capture matrix</h2><p>Inspection labels identify the exact reported sample. Images are ordinary connected Editor states; operator-owned progression/seed fixtures and ephemeral Editor identity remain explicit test limits.</p><div class="gallery">''' + ''.join(rows) + '''</div><p><small>''' + esc(summary['status']) + ' · ' + esc(summary['utc']) + '''</small></p></main></html>'''


def self_test():
    """Read-only negative controls; no frozen artifact is changed."""
    proof = Proof()
    files = proof.read('VerifiedAppWithJNI/Sources.json')['files']
    passed = []

    class Mutated(Proof):
        def __init__(self, name, mutate):
            super().__init__(); self.name, self.mutate = name, mutate
            self.cached = proof.cached

        def read(self, name, expected=None):
            value = super().read(name, expected)
            if name == self.name:
                value = copy.deepcopy(value); self.mutate(value)
            return value

    def reject(label, run):
        try:
            run()
        except (AssertionError, FileNotFoundError):
            passed.append(label)
        else:
            raise AssertionError('Negative control unexpectedly accepted: ' + label)

    mode, path, status = 'ServerHttp', MAIN['ServerHttp'][0], MAIN['ServerHttp'][1]
    for label, name, mutate in (
        ('failed process', 'VerifiedAppWithJNI/Native/ServerHttp_Process.json', lambda row: row.update(exitCode=1)),
        ('timed-out process', 'VerifiedAppWithJNI/Native/ServerHttp_Process.json', lambda row: row.update(timedOut=True)),
        ('wrong Editor', 'VerifiedAppWithJNI/Native/ServerHttp_Process.json', lambda row: row.update(version='6000.0.0')),
        ('stale before-source', 'VerifiedAppWithJNI/Native/SuiteSources/ServerHttp.json', lambda row: row['files'].update({next(iter(files)): '0' * 64})),
        ('stale after-source', 'VerifiedAppWithJNI/Native/SuiteSources/ServerHttp_After.json', lambda row: row['files'].update({next(iter(files)): '0' * 64})),
        ('nonzero delta', 'VerifiedAppWithJNI/Native/ServerHttp_Input_Delta.json', lambda row: row['added'].append('unexpected')),
        ('failed report', 'VerifiedAppWithJNI/Native/ConnectedHTTP.json', lambda row: row['errors'].append('injected control')),
    ):
        reject(label, lambda name=name, mutate=mutate: suite(Mutated(name, mutate), 'VerifiedAppWithJNI', mode, path, status, files))
    reject('invalid source partition', lambda: source_proof(Mutated('VerifiedAppWithJNI/Sources.json', lambda row: row.update(unchangedBaselineInputs=5167))))
    reject('missing capture', lambda: main_suites(Mutated('VerifiedAppWithJNI/Native/ConnectedHTTP.json', lambda row: row['captures'].pop()), files))
    reject('claimed Android run', lambda: main_suites(Mutated('VerifiedAppWithJNI/Native/ConnectedHTTP.json', lambda row: row.update(android=True)), files))
    reject('missing Home metadata acceptance', lambda: main_suites(Mutated('VerifiedAppWithJNI/Native/ConnectedHTTP.json', lambda row: row.update(readonlyHomeRewardBadges=False)), files))
    reject('stale visual review', lambda: main_suites(Mutated('VerifiedAppWithJNI/Visual_Review.json', lambda row: row.update(sourcesSHA256='0'*64)), files))
    reject('backend skipped case', lambda: backend(Mutated('Backend/Verified324/Service_Tests.json', lambda row: row['skipped'].append('injected'))))
    reject('missing actual worker', lambda: backend(Mutated('Backend/Verified324/Service_Tests.json', lambda row: row.update(actualPinnedWorkerIntegration=False))))
    reject('wrong artifact hash', lambda: proof.file('VerifiedAppWithJNI/Native/ConnectedHTTP.json', '0' * 64))
    reject('path escape', lambda: proof.file('../ServerReplay83/Summary.json'))
    if (proof.output / 'Android/Connected84/Report.json').is_file():
        android_lifecycle(proof, files)
        reject('wrong Android target', lambda: android_lifecycle(Mutated('Android/Connected84/Report.json', lambda row: row.update(qa_serial='emulator-5556')), files))
        reject('Android fixture not stopped', lambda: android_lifecycle(Mutated('Android/Connected84/Report.json', lambda row: row.update(ownFixtureStopped=False)), files))
        reject('unrelated reverse removed', lambda: android_lifecycle(Mutated('Android/Connected84/Report.json', lambda row: row['adbReverse']['afterOwnCleanup'].append('injected')), files))
        reject('Android key exportability', lambda: android_lifecycle(Mutated('Android/Connected84/Stage_setup.json', lambda row: row.update(androidSigningKeyNonexportable=False)), files))
        reject('Android wallet changed', lambda: android_lifecycle(Mutated('Android/Connected84/Stage_reopen.json', lambda row: row.update(coins=99999)), files))
    # A complete real proof is the positive control for the same validators.
    positive = collect(proof, require_compatibility=False)
    need(positive['mainChecks'] == 18398 + positive['expiryChecks'] and positive['backendTests'] == 324, 'Collector positive control failed')
    print(json.dumps({'status': 'PASS_CONNECTED84_COLLECTOR_CONTROLS', 'negativeControls': len(passed), 'positiveMainChecks': positive['mainChecks'], 'controls': passed}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-only', action='store_true', help='Validate main/native/backend without claiming compatibility completion')
    parser.add_argument('--publish', action='store_true', help='Write Summary.json and Comparison.html only after full validation')
    parser.add_argument('--self-test', action='store_true', help='Run read-only intentional rejection controls')
    args = parser.parse_args()
    if args.self_test:
        need(not args.publish and not args.main_only, 'Collector controls do not publish')
        self_test(); return
    need(not (args.main_only and args.publish), 'Main-only validation cannot publish')
    summary = collect(Proof(), require_compatibility=not args.main_only)
    if args.publish:
        (OUT / 'Summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        (OUT / 'Comparison.html').write_text(render_html(summary), encoding='utf-8')
    print(json.dumps({key: summary[key] for key in ('status', 'mainChecks', 'backendTests', 'compatibilitySuites', 'captureCount', 'explicitlyReviewedCaptureCount')}))


if __name__ == '__main__':
    main()
