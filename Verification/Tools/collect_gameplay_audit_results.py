"""Collect fresh GameplayAudit evidence; preserve prior branches as history.

This reads existing reports only. It never runs Unity, installs an APK, changes
evidence verdicts, or assigns an old report to the current build.
"""
from pathlib import Path
import csv
import datetime as dt
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence'
BRANCH = OUT / 'GameplayAudit'
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
MIXED_MODES = {'MixedH', 'MixedV', 'MixedBomb', 'MixedOrb', 'MixedSeeker', 'MixedChain'}
OBSTACLE_MODES = {'ObstaclePartial', 'ObstacleClear'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def utc(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def require_pass(report, label):
    status = report.get('status', '')
    assert status == 'PASS' or status.startswith('PASS_'), f'{label}: missing or failing verdict'
    for key in ('failures', 'errors', 'error', 'failed'):
        assert not report.get(key), f'{label}: {key} is nonempty'


def validate_runtime_checks(value, label='Native runtime checks'):
    """Validate each named runner report; diagnostic codes are not verdicts."""
    if 'reports' in value:
        if 'status' in value:
            require_pass(value, label)
        assert value['reports'], label + ': no runner reports were found'
        for entry in value['reports']:
            assert entry.get('mode') and isinstance(entry.get('report'), dict), label + ': malformed runner report'
            require_pass(entry['report'], label + '/' + entry['mode'])
    else:
        require_pass(value, label)
    return value


def measurement(variant, expected_sha):
    install = read(BRANCH / variant / 'Installation.json')
    assert install.get('sha256', install.get('apk_sha256')) == expected_sha, variant + ': installation hash is stale'
    report = read(BRANCH / variant / 'Measurement.json')
    assert report['status'] == 'RECORDED_NATIVE_FLUIDITY' and not report['errors'], variant + ': device measurement failed'
    assert report['platform'] == 'Android' and report['phases'], variant + ': Android phases missing'
    assert utc(report['utc']) >= utc(install['utc']), variant + ': measurement predates installation'
    if 'apk_sha256' in report:
        assert report['apk_sha256'] == expected_sha, variant + ': measurement hash is stale'
    return {'apk_sha256': expected_sha, 'installation': install, 'measurement': report}


def performance_rows(before, after):
    old = {row['name']: row for row in before['phases']}
    new = {row['name']: row for row in after['phases']}
    assert old.keys() == new.keys(), 'Before/after device phases do not match'
    fields = ('frames', 'p50Ms', 'p95Ms', 'worstMs', 'commandMs', 'firstPresentationMs',
              'settleSeconds', 'over33ms', 'over50ms', 'gen0Collections', 'synchronousTextureLoads')
    return [{'name': name,
             'before': {key: old[name].get(key) for key in fields},
             'after': {key: new[name].get(key) for key in fields}}
            for name in old]


def run():
    digest = sha(APK)
    mixed = read(BRANCH / 'Mixed_Swap_Checks.json')
    require_pass(mixed, 'Mixed swaps')
    assert mixed['status'] == 'PASS_NATIVE_MIXED_POWER_SWAP' and mixed['turns'] == 360
    assert len(mixed['cases']) == 360 and mixed['chainedBirths'] > 0
    audit = read(BRANCH / 'Audit_Checks.json')
    require_pass(audit, 'Broad model audit')
    assert audit['naturalBoards'] == 150 and audit['pairCases'] == 700 and audit['toolCases'] == 200
    assert audit['naturalActions'] > 0
    assert audit['obstacleBoundaries'] and all(row['status'] == 'NO_BOUNDARY_DISCONTINUITY' for row in audit['obstacleBoundaries']), 'Obstacle phase diagnostic remains open'
    runtime = validate_runtime_checks(read(BRANCH / 'Native_Runtime_Checks.json'))
    replay_refresh = read(BRANCH / 'Campaign_Replay_Refresh.json')
    require_pass(replay_refresh, 'Mixed-swap campaign replay refresh')
    assert replay_refresh['status'] == 'PASS_NATIVE_MIXED_SWAP_REPLAY_REFRESH'
    assert replay_refresh['changed'] and replay_refresh['otherReplaysUnchanged'] and replay_refresh['levelFilesUnchanged']
    assert {row['level'] for row in replay_refresh['differences']} == {21, 49}
    assert all(row['accepted'] and row['mixedSwap'] and row['immediateMatch'] and row['finalStatus'] == 'Won' for row in replay_refresh['differences'])
    assert replay_refresh['campaign']['status'] == 'PASS_CAMPAIGN_LOGIC' and not replay_refresh['campaign']['errors']
    replay_path = ROOT / 'Unity/Assets/HeartOfTheRain/M48/Resources/HOTR_Playtests/Campaign_Replays.json'
    assert sha(replay_path) == replay_refresh['afterSHA256'], 'Current replay resource changed after legal-clear verification'
    assert sha(BRANCH / 'Before/Campaign_Replays.json') == replay_refresh['beforeSHA256']
    assert all(sha(ROOT / 'Unity' / entry['path']) == entry['sha256'] for entry in replay_refresh['levelHashes']), 'Authored level content changed during replay refresh'

    freeze = read(BRANCH / 'Player_Source_SHA256.json')
    assert freeze['files'], 'No built-player source manifest'
    assert all(sha(ROOT / name) == expected for name, expected in freeze['files'].items()), 'Player source changed after build'
    assert freeze['apk_sha256'] == digest, 'Built-player source manifest is not bound to this APK'
    artifact = read(OUT / 'Native/APK_Artifact.json')
    assert artifact['sha256'] == digest and artifact['bytes'] == APK.stat().st_size, 'Canonical APK artifact evidence is stale'
    build = read(BRANCH / 'Android_Build.json')
    require_pass(build, 'Android build')
    packaging = read(BRANCH / 'APK_Packaging.json')
    require_pass(packaging, 'APK packaging')
    assert packaging['afterSHA256'] == digest and packaging['sameSignerCertificate'] and not packaging['changedNonSignatureEntries']
    for name in ('APK_Orientation.json', 'APK_Payloads.json'):
        report = read(BRANCH / name)
        require_pass(report, name)
        assert report['apk_sha256'] == digest, name + ': stale APK hash'
    integrity = read(BRANCH / 'Integrity.json')
    require_pass(integrity, 'Source/asset integrity')
    assert not integrity.get('unexpected_changed_baseline_files'), 'Undocumented baseline changes'

    before_sampler = read(BRANCH / 'Before/Sampler_Atlas.json')
    after_sampler = read(BRANCH / 'After/Sampler_Atlas.json')
    for label, report in [('Before sampler', before_sampler), ('After sampler', after_sampler)]:
        require_pass(report, label)
        assert report['status'] == 'PASS_NATIVE_GAMEPLAY_PERFORMANCE'
    old_poses = {row['name']: row['poseSignature'] for row in before_sampler['samplers']}
    authored = [row for row in after_sampler['samplers'] if row['name'].startswith('plan_') or row['name'] == 'crystal_idle']
    assert len(authored) == 67 and all(old_poses.get(row['name']) == row['poseSignature'] for row in authored), 'Authored sampler poses changed'
    assert after_sampler['atlases'] and all(row['warmCreates'] == row['warmEvictions'] == 0 for row in after_sampler['atlases']), 'Repeated combo cache still churns'
    model_before = read(BRANCH / 'Before/Model_Commands.json')
    model_after = read(BRANCH / 'After/Model_Commands.json')
    for label, report in [('Before model commands', model_before), ('After model commands', model_after)]:
        require_pass(report, label)
        assert report['status'] == 'PASS_NATIVE_MODEL_COMMANDS' and len(report['commands']) == 200
    old_model = {row['name']: row for row in model_before['commands']}
    for row in model_after['commands']:
        previous = old_model[row['name']]
        assert all(previous[key] == row[key] for key in ('turnSHA256', 'finalSHA256', 'steps', 'created')), 'Before/after command semantics changed: ' + row['name']
    baseline_install = read(BRANCH / 'Before/Installation.json')
    baseline_sha = baseline_install.get('sha256', baseline_install.get('apk_sha256'))
    assert baseline_sha and baseline_sha != digest, 'The previous APK must remain separately identified'
    before = measurement('Before', baseline_sha)
    after = measurement('After', digest)
    assert before['measurement']['graphics'] == after['measurement']['graphics'], 'Before/after graphics device changed'
    rows = performance_rows(before['measurement'], after['measurement'])

    touch = read(BRANCH / 'Touch/Report.json')
    visual = read(BRANCH / 'Visual_Review.json')
    require_pass(touch, 'Actual Android touch review')
    require_pass(visual, 'Native visual review')
    assert touch['status'] == visual['status'] == 'PASS_NATIVE_GAMEPLAY_AUDIT_VISUAL_REVIEW'
    assert touch['apk_sha256'] == visual['apk_sha256'] == digest
    cases = {case['mode']: case for case in touch['cases']}
    assert (MIXED_MODES | OBSTACLE_MODES) <= cases.keys(), 'A required actual mixed-swap/obstacle gesture is missing'
    for mode, case in cases.items():
        require_pass(case, 'Actual Android ' + mode)
    for mode in MIXED_MODES:
        case = cases[mode]
        assert case['accepted'] and case['createdId'] > 0 and case['createdX'] == case['createdY'] == 4
        assert any(pose['key'] == 'Create' or pose['key'].endswith('_Create') for pose in case['poses'])
    assert cases['MixedChain']['chained'], 'Actual hit newborn did not chain'
    assert all(cases[mode]['accepted'] for mode in OBSTACLE_MODES), 'An actual obstacle swipe was not accepted'
    assert any(pose['key'].startswith('stone/Stone_Hit') and pose['age'] > .3 for pose in cases['ObstaclePartial']['poses']), 'Native partial obstacle hit did not continue across the phase boundary'
    assert visual['artifactSHA256'], 'Visual artifacts have not been frozen after review'
    assert all(sha(BRANCH / name) == expected for name, expected in visual['artifactSHA256'].items()), 'Reviewed visual artifacts changed'
    reference = read(BRANCH / 'Reference/Review.json')
    assert reference['status'] == 'REVIEWED_ACTUAL_REFERENCE_SEQUENCES' and reference['versionName'] == '7307'
    assert all(sha(BRANCH / 'Reference' / name) == expected for name, expected in reference['videos'].items()), 'Reference evidence changed'
    ui_review = read(BRANCH / 'UI_Review.json')
    require_pass(ui_review, 'Selected native UI review')
    assert ui_review['apk_sha256'] == digest and all(sha(BRANCH / name) == expected for name, expected in ui_review['artifactSHA256'].items())

    regression = read(BRANCH / 'LDPlayer/Regression.json')
    require_pass(regression, 'Current Android regression')
    assert regression['status'] == 'PASS_NATIVE_REGRESSION' and regression['boards'] == 50
    assert regression['height'] > regression['width'], 'Current Android regression is not portrait'
    regression_install = read(BRANCH / 'LDPlayer/Installation.json')
    assert regression_install.get('sha256', regression_install.get('apk_sha256')) == digest
    assert utc(regression['utc']) >= utc(regression_install['utc']), 'Regression predates current installation'
    installs = [read(BRANCH / name) for name in ('MainInstance_Final_Installation.json', 'QA_Final_Installation.json')]
    for install in installs:
        require_pass(install, 'Final installation')
        assert install['apk_sha256'] == digest
    preferences = read(BRANCH / 'Preferences_Preservation.json')
    assert preferences['status'] == 'PASS_IDENTICAL_PREFERENCE_FILES' and installs[1]['preferencesIdentical']
    test_preferences = read(BRANCH / 'Test_Span_Preferences.json')
    assert test_preferences['status'] == 'PASS_IDENTICAL_PREFERENCE_FILES' and test_preferences['before'] == test_preferences['after']

    summary = {
        'status': 'PASS_VERIFICATION_WITH_OPEN_RELEASE_GATES',
        'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'current_evidence_branch': 'GameplayAudit', 'unity': '2022.3.62f3',
        'apk': artifact, 'mixed_power_swap': mixed, 'broad_model_audit': audit,
        'native_runtime_checks': runtime, 'campaign_replay_refresh': replay_refresh,
        'actual_android': touch, 'visual_review': visual, 'selected_ui_review': ui_review, 'reference_review': reference,
        'current_android_regression': regression, 'regression_installation': regression_install,
        'installations': installs, 'preferences_preservation': preferences, 'test_span_preferences': test_preferences,
        'sampler_before': before_sampler, 'sampler_after': after_sampler,
        'model_commands_before': model_before, 'model_commands_after': model_after,
        'device_performance_before': before, 'device_performance_after': after,
        'device_performance_comparison': rows,
        'performance_scope': 'Unaccelerated native LDPlayer intervals include emulator scheduling/ARM translation. CPU sampler evidence is separate from GPU/display. Reported remaining long frames do not certify a sustained 60-fps or physical-device budget.',
        'allocation_scope': ('Allocation counter passed a positive control; consult sampler counter method and device collection counts.' if after_sampler['allocationCounterUsable'] else 'Native Editor allocation counter unavailable; zero-allocation claims are not supported by that counter. Device collection counts remain separate.'),
        'historical_evidence': {'branch': 'M70R2', 'apk_sha256': baseline_sha,
                                'scope': 'Baseline APK and earlier verification retain their original scope; current checks are listed separately.'},
        'remaining': ['Orb + Rocket still shows18 of528 intervals above33.34ms and a99.95ms worst interval in the controlled emulator run; sustained60fps remains unverified',
                      'Physical Android/iOS performance, sensors and long-session stress',
                      'Human balance and exhaustive natural play',
                      'Durable profile/inventory/idempotent attempt settlement',
                      'Production billing, social and live services'],
    }
    for path in (BRANCH / 'Verification_Summary.json', OUT / 'Verification_Summary.json'):
        path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    status = subprocess.run(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout
    with (OUT / 'Changed_Files.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['status', 'path', 'category'])
        for line in status.splitlines():
            name = line[3:]
            category = 'Gameplay audit repair/evidence' if any(token in name for token in ('GameplayAudit', 'MixedPowerSwap', 'GameModelPerformance', 'gameplay_audit')) or name.endswith(('BoardModel.cs', 'BoardPresentation.cs', 'BoardPlayback.cs', 'GameplayScreen.cs', 'M46AtlasBank.cs')) else 'Existing project work or verification'
            writer.writerow([line[:2], name, category])
    print(json.dumps({'status': summary['status'], 'apk_sha256': digest,
                      'mixed_turns': mixed['turns'], 'audit_checks': audit['checks'],
                      'android_boards': regression['boards'], 'touch_cases': len(cases)}, indent=2))


if __name__ == '__main__':
    run()
