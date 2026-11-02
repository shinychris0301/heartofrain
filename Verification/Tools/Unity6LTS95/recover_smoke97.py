"""Root-only preservation of one incomplete owned smoke project; no process stop.

Old receipts/logs stay unchanged. Only the fixed private Smoke directory is
atomically renamed after ended-PID/source/preference/template/stability guards.
"""
import argparse
import os
from pathlib import Path
import re

import official_download95 as download
import smoke95 as smoke

ROOT = smoke.ROOT
OLD_ID = 'e8cb7db157bc46fa8b90035fe59149f3'
OLD = smoke.EVIDENCE / 'SmokeRuns' / OLD_ID
PREPARED = smoke.EVIDENCE / 'SmokePreparation/Set01/Preparation.json'
AUTH_SHA = '16e523a79f28da9122a4fd5a92b28eacccb329f0303c42d25380ed4afc279199'
PREP_SHA = 'cc8f6eb6aa402e2c17a479ce8d17fe9450937a695d6cb9b3c9a820109ca23d50'
SOURCE = smoke.PRIVATE / 'Smoke'
DESTINATION = smoke.PRIVATE / 'SmokeFailed97' / OLD_ID
PUBLIC = smoke.EVIDENCE / 'SmokeRecovery97'
OBSERVED_PIDS = {'editor': 4036, 'wrapper': 11592, 'java': 21152}
OLD_FILES = ('Authorization.json', 'Unity.log', 'Console.log', 'MainSources_before.json',
             'Candidate66Sources_before.json', 'ExternalToolsPrefFingerprints_before.json')


def need(value, code):
    if not value:
        raise ValueError(code)


def no_links(path):
    path = Path(path).absolute()
    for node in (path, *path.parents):
        if node.exists():
            need(not node.is_symlink() and not getattr(node.stat(), 'st_file_attributes', 0) & 0x400,
                 'SmokeRecovery97ReparsePointRefused')
    return path.resolve()


def checked_paths(output):
    source, destination, private = no_links(SOURCE), no_links(DESTINATION), no_links(smoke.PRIVATE)
    need(source == no_links(smoke.PROJECT) and source.parent == private and source.name == 'Smoke'
         and source.is_dir(), 'SmokeRecovery97ExactOwnedSmokeRequired')
    need(destination == private / 'SmokeFailed97' / OLD_ID and source.drive == destination.drive
         and not destination.exists(), 'SmokeRecovery97FreshFixedPrivateDestinationRequired')
    output = no_links(output)
    need(output.parent == no_links(PUBLIC) and re.fullmatch(r'[a-f0-9]{32}', output.name)
         and not output.exists(), 'SmokeRecovery97FreshReceiptUUIDRequired')
    return source, destination, output


def old_inventory():
    need(not (OLD / 'Invocation.json').exists() and not (OLD / 'Native.json').exists(),
         'SmokeRecovery97MissingFinalReceiptRequiredNoRewrite')
    need({path.name for path in OLD.iterdir()} == set(OLD_FILES), 'SmokeRecovery97UnexpectedOldAttemptFiles')
    result = {}
    for name in OLD_FILES:
        path = no_links(OLD / name)
        need(path.is_file(), 'SmokeRecovery97OldEvidenceRequired')
        result[name] = {'sha256': download.digest(path), 'bytes': path.stat().st_size,
                        'mtimeNs': path.stat().st_mtime_ns}
    return result


def ownership(source):
    need(download.digest(OLD / 'Authorization.json') == AUTH_SHA and download.digest(PREPARED) == PREP_SHA,
         'SmokeRecovery97ExactOldAuthorizationAndPreparationRequired')
    auth, proof = smoke.read(OLD / 'Authorization.json'), smoke.read(PREPARED)
    command = [str(smoke.EDITOR), '-batchmode', '-nographics', '-buildTarget', 'Android', '-projectPath', str(source),
               '-executeMethod', smoke.ENTRY, '-logFile', str(OLD / 'Unity.log')]
    need(auth.get('status') == 'RUNNING_ACTUAL_LTS95_TOOLCHAIN_SMOKE' and auth.get('command') == command
         and auth.get('runnerSHA256') == smoke.sha(Path(smoke.__file__))
         and auth.get('preparation') == smoke.binding(PREPARED) and auth.get('editor') == smoke.binding(smoke.EDITOR)
         and proof.get('status') == 'PASS_FRESH_MINIMAL_LTS95_SMOKE_PREPARATION'
         and proof.get('project') == source.relative_to(ROOT).as_posix() and proof.get('version') == smoke.VERSION
         and proof.get('templateSHA256') == smoke.sha(smoke.TEMPLATE), 'SmokeRecovery97OwnedPreparedSmokeBindingRequired')
    for relative in ('Assets/Editor/ToolchainSmoke95.cs', 'Assets/Editor/ToolchainSmoke95.cs.meta', 'Packages/manifest.json'):
        path = no_links(source / relative)
        need(path.is_file() and smoke.sha(path) == proof['inputManifest']['files'][relative]['sha256']
             and path.stat().st_size == proof['inputManifest']['files'][relative]['bytes'], 'SmokeRecovery97OwnedPreparedInputChanged')
    version = (source / 'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig').replace('\r\n', '\n').strip()
    need(version in ('m_EditorVersion: 6000.3.27f1',
                     'm_EditorVersion: 6000.3.27f1\nm_EditorVersionWithRevision: 6000.3.27f1 (672d562a42a7)'),
         'SmokeRecovery97ExactGeneratedLTSVersionRequired')


def tree_inventory(source):
    files = {}
    for directory, folders, names in os.walk(source, followlinks=False):
        no_links(directory)
        for name in folders:
            no_links(Path(directory) / name)
        for name in names:
            path = no_links(Path(directory) / name)
            need(path.is_file() and path.is_relative_to(source), 'SmokeRecovery97RegularOwnedProjectFileRequired')
            need(path.stat().st_nlink == 1, 'SmokeRecovery97HardLinkedProjectFileRefused')
            files[path.relative_to(source).as_posix()] = {'sha256': download.digest(path), 'bytes': path.stat().st_size}
            need(len(files) <= 100000, 'SmokeRecovery97ProjectInventoryBound')
    need(files, 'SmokeRecovery97NonemptyProjectRequired')
    return {'files': files, 'fileCount': len(files), 'bytes': sum(item['bytes'] for item in files.values())}


def idle(processes):
    need(not processes.unity_pids(), 'SmokeRecovery97NoRunningEditorRequired')
    for pid in OBSERVED_PIDS.values():
        download.stopped_pid(pid)  # Read-only Windows ended-state check, never stop/kill.


def protected(api, candidate):
    main, previous66 = smoke.protected_sources(api, candidate)
    need(main == smoke.read(OLD / 'MainSources_before.json')
         and previous66 == smoke.read(OLD / 'Candidate66Sources_before.json'), 'SmokeRecovery97ProtectedSourceDrift')
    need(smoke.external_pref_fingerprints() == smoke.read(OLD / 'ExternalToolsPrefFingerprints_before.json'),
         'SmokeRecovery97ReadOnlyPreferenceFingerprintDrift')
    return main, previous66


def recover(output):
    source, destination, output = checked_paths(output)
    api, candidate, processes, _, _ = smoke.readers()
    idle(processes);ownership(source)
    old = old_inventory();main, previous66 = protected(api, candidate)
    project = tree_inventory(source)
    # Stable full-tree/evidence equality is checked immediately before rename.
    idle(processes)
    need(old_inventory() == old and tree_inventory(source) == project, 'SmokeRecovery97AttemptStillChanging')
    output.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 1, 'status': 'INCOMPLETE_INTERRUPTED_LTS95_SMOKE_OBSERVED97', 'startedUtc': api.utc(),
              'runnerSHA256': download.digest(__file__), 'oldAuthorization': smoke.binding(OLD / 'Authorization.json'),
              'oldAttemptDirectory': OLD.relative_to(ROOT).as_posix(), 'oldFinalInvocationMissing': True, 'oldNativeReportMissing': True,
              'oldEvidenceBefore': old, 'rootPreviouslyObservedPIDs': OBSERVED_PIDS, 'allObservedPIDsEnded': True,
              'processIdentityScope': 'PIDs previously observed by root in the active session. This helper proves current ended-state only; the original prelaunch Authorization did not record child PIDs.',
              'interruptionCause': 'UNPROVEN', 'oldFailureOrFinalResultFabricated': False, 'oldReceiptRewritten': False,
              'sourceProject': str(source), 'preservedProject': str(destination), 'projectFileCount': project['fileCount'],
              'projectBytes': project['bytes'], 'projectRelocated': False, 'processStopOrKillExecuted': False,
              'scope': 'One fixed incomplete private smoke attempt preserved for an explicit fresh retry. No compile FAIL/PASS inferred, process stopped, old receipt/log rewritten, project deleted, main/vendor/SDK/device changed or preference setter invoked.'}
    api.write(output / 'InterruptedAttempt.json', report)
    api.write(output / 'Project_before.json', project)
    try:
        idle(processes);need(protected(api, candidate) == (main, previous66), 'SmokeRecovery97SourceChangedBeforeRename')
        need(old_inventory() == old and tree_inventory(source) == project, 'SmokeRecovery97AttemptChangedBeforeRename')
        need(not destination.exists(), 'SmokeRecovery97DestinationCollisionPreserved')
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)  # Same-volume atomic rename; no recursive delete/copy.
        report['projectRelocated'] = True
        after = tree_inventory(destination);api.write(output / 'Project_after.json', after)
        need(after == project and not source.exists(), 'SmokeRecovery97PreservedProjectMismatch')
        need(old_inventory() == old and protected(api, candidate) == (main, previous66), 'SmokeRecovery97ProtectedEvidenceOrSourcesChanged')
        idle(processes)
        report.update(status='PRESERVED_INCOMPLETE_INTERRUPTED_SMOKE97_READY_FOR_FRESH_PREPARATION',
                      oldEvidenceUnchanged=True, mainAndCandidate66Unchanged=True, preferenceFingerprintsMatchBefore=True)
    except Exception as error:
        report.update(status='FAIL_SMOKE97_PRESERVATION_GUARD', errorType=type(error).__name__)
        if isinstance(error, ValueError) and re.fullmatch(r'[A-Za-z0-9]{1,120}', str(error)):
            report['errorCategory'] = str(error)
    finally:
        report['finishedUtc'] = api.utc();api.write(output / 'Recovery.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path, required=True);args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not args.out.is_absolute():
        parser.error('Explicit root Windows recovery and absolute fresh receipt UUID required')
    try:
        report = recover(args.out)
        print(__import__('json').dumps({'status': report['status'], 'projectRelocated': report['projectRelocated'],
                                      'interruptionCause': 'UNPROVEN', 'oldReceiptRewritten': False}))
        return 0 if report['status'] == 'PRESERVED_INCOMPLETE_INTERRUPTED_SMOKE97_READY_FOR_FRESH_PREPARATION' else 1
    except Exception as error:
        print(__import__('json').dumps({'status': 'REFUSED_SMOKE97_RECOVERY', 'errorType': type(error).__name__}));return 1


if __name__ == '__main__':
    raise SystemExit(main())
