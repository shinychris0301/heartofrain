"""Root-only preservation of the completed failed f8f715 smoke; no deletion/stop."""
import argparse
import json
import os
from pathlib import Path
import re
import stat

import official_download95 as download
import smoke95 as smoke

ROOT = smoke.ROOT
OLD_ID = 'f8f71579f2d146debe242be34fbc6322'
OLD = smoke.EVIDENCE / 'SmokeRuns' / OLD_ID
SOURCE = smoke.PRIVATE / 'Smoke'
DESTINATION = smoke.PRIVATE / 'SF2'
PUBLIC = smoke.EVIDENCE / 'SmokePreservation97'
INVOCATION_SHA = '6c9c37dae97babbb29dfac945549920fb0b6db764bd429fea29febf23d270921'
NATIVE_SHA = 'bb2c9b7808310d4aa3e429833f43e970d685185311b69fb6c6a8736a95b0b158'
AUTH_SHA = 'b9d9d97b9b2299ba402e84e25e77ed8de3c8d31aa2625e26428fdb2e97e54f76'
OLD_FILES = ('Authorization.json', 'Candidate66Sources_after.json', 'Candidate66Sources_before.json', 'Console.log',
             'ExternalToolsPrefFingerprints_after.json', 'ExternalToolsPrefFingerprints_before.json', 'Invocation.json',
             'MainSources_after.json', 'MainSources_before.json', 'Native.json', 'Unity.log')


def need(value, code):
    if not value:
        raise ValueError(code)


def logical(path):
    text = str(path)
    if text.startswith('\\\\?\\'):
        text = text[4:]
    return Path(text).absolute()


def extended(path):
    value = str(logical(path))
    return '\\\\?\\' + value if os.name == 'nt' else value


def safe(path):
    path = logical(path)
    for node in (path, *path.parents):
        try:
            info = os.lstat(extended(node))
        except FileNotFoundError:
            continue
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
             'SmokePreserve97LinkOrReparseRefused')
        need(not stat.S_ISREG(info.st_mode) or info.st_nlink == 1, 'SmokePreserve97HardLinkedFileRefused')
    return path


def present(path):
    try:
        os.lstat(extended(path))
        return True
    except FileNotFoundError:
        return False


def binding(path):
    path = safe(path);info = os.lstat(extended(path))
    need(stat.S_ISREG(info.st_mode), 'SmokePreserve97RegularFileRequired')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': download.digest(extended(path)), 'bytes': info.st_size}


def paths(output):
    source, destination, private = safe(SOURCE), safe(DESTINATION), safe(smoke.PRIVATE)
    need(source == safe(smoke.PROJECT) and source == private / 'Smoke'
         and present(source) and stat.S_ISDIR(os.lstat(extended(source)).st_mode), 'SmokePreserve97FixedOwnedSourceRequired')
    need(destination == private / 'SF2' and source.drive == destination.drive and not present(destination),
         'SmokePreserve97FreshShortDestinationRequired')
    output = safe(output)
    need(output.parent == safe(PUBLIC) and re.fullmatch(r'[a-f0-9]{32}', output.name) and not present(output),
         'SmokePreserve97FreshReceiptUUIDRequired')
    return source, destination, output


def evidence():
    safe(OLD)
    need({path.name for path in OLD.iterdir()} == set(OLD_FILES), 'SmokePreserve97ExactCompletedEvidenceRequired')
    return {name: {**binding(OLD / name), 'mtimeNs': os.lstat(extended(OLD / name)).st_mtime_ns} for name in OLD_FILES}


def completed(source):
    need(binding(OLD / 'Invocation.json')['sha256'] == INVOCATION_SHA
         and binding(OLD / 'Native.json')['sha256'] == NATIVE_SHA
         and binding(OLD / 'Authorization.json')['sha256'] == AUTH_SHA, 'SmokePreserve97FrozenFailedReceiptsRequired')
    report, native, auth = (smoke.read(OLD / name) for name in ('Invocation.json', 'Native.json', 'Authorization.json'))
    need(report.get('status') == 'FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE' and report.get('exitCode') == 1
         and not report.get('timedOut') and report.get('nativeStatus') == 'FAIL_ACTUAL_LTS95_EMPTY_ANDROID_BUILD'
         and native.get('status') == 'FAIL_ACTUAL_LTS95_EMPTY_ANDROID_BUILD' and native.get('unity') == smoke.VERSION
         and report.get('actualEngineVersionFromLog') == smoke.VERSION and report.get('ownedJobAssignedBeforeResume') is True
         and type(report.get('pid')) is int and report['pid'] > 0 and report.get('unityPidsAfter') == []
         and all(report.get(key) is True for key in ('mainInputsUnchanged', 'candidate66InputsUnchanged',
              'externalToolPrefFingerprintsUnchanged', 'embeddedToolMarkersUnchanged')),
         'SmokePreserve97CompletedFailedNativeAttemptRequired')
    expected = [str(smoke.EDITOR), '-batchmode', '-nographics', '-buildTarget', 'Android', '-projectPath', str(source),
                '-executeMethod', smoke.ENTRY, '-logFile', str(OLD / 'Unity.log')]
    need(report.get('command') == auth.get('command') == expected
         and report.get('runnerSHA256') == auth.get('runnerSHA256') == smoke.sha(Path(smoke.__file__))
         and report.get('editor') == smoke.binding(smoke.EDITOR), 'SmokePreserve97OwnedCommandAndRunnerRequired')
    prepared = safe(report['preparation']['path'])
    need(prepared == smoke.EVIDENCE / 'SmokePreparation/Set02/Preparation.json'
         and smoke.binding(prepared) == report['preparation'] == auth['preparation'], 'SmokePreserve97ExactPreparationRequired')
    proof = smoke.read(prepared)
    need(proof.get('status') == 'PASS_FRESH_MINIMAL_LTS95_SMOKE_PREPARATION'
         and proof.get('project') == source.relative_to(ROOT).as_posix() and proof.get('version') == smoke.VERSION
         and proof.get('templateSHA256') == smoke.sha(smoke.TEMPLATE)
         and report.get('nativeReport') == smoke.binding(OLD / 'Native.json'), 'SmokePreserve97PreparedNativeBindingRequired')
    for relative in ('Assets/Editor/ToolchainSmoke95.cs', 'Assets/Editor/ToolchainSmoke95.cs.meta', 'Packages/manifest.json'):
        item = binding(source / relative)
        need({key: item[key] for key in ('sha256', 'bytes')} == proof['inputManifest']['files'][relative],
             'SmokePreserve97PreparedSourceChanged')
    version = Path(extended(safe(source / 'ProjectSettings/ProjectVersion.txt'))).read_text('utf-8-sig').strip()
    need(version.replace('\r\n', '\n') in ('m_EditorVersion: 6000.3.27f1',
         'm_EditorVersion: 6000.3.27f1\nm_EditorVersionWithRevision: 6000.3.27f1 (672d562a42a7)'),
         'SmokePreserve97ExactGeneratedVersionRequired')
    return report


def inventory(directory):
    directory = safe(directory);files = {}
    def inaccessible(error):
        raise error
    for current, folders, names in os.walk(extended(directory), followlinks=False, onerror=inaccessible):
        current = safe(current)
        for name in folders:
            safe(current / name)
        for name in names:
            path = safe(current / name);item = binding(path)
            files[path.relative_to(directory).as_posix()] = {key: item[key] for key in ('sha256', 'bytes')}
            need(len(files) <= 100000, 'SmokePreserve97ProjectInventoryBound')
    need(files, 'SmokePreserve97NonemptyProjectRequired')
    return {'files': files, 'fileCount': len(files), 'bytes': sum(item['bytes'] for item in files.values())}


def idle(processes, pid):
    need(not processes.unity_pids(), 'SmokePreserve97NoRunningUnityRequired')
    download.stopped_pid(pid)


def protected(api, candidate):
    current = smoke.protected_sources(api, candidate)
    for prefix, value in zip(('Main', 'Candidate66'), current):
        need(value == smoke.read(OLD / (prefix + 'Sources_before.json')) == smoke.read(OLD / (prefix + 'Sources_after.json')),
             'SmokePreserve97ProtectedSourceDrift')
    need(smoke.external_pref_fingerprints() == smoke.read(OLD / 'ExternalToolsPrefFingerprints_before.json')
         == smoke.read(OLD / 'ExternalToolsPrefFingerprints_after.json'), 'SmokePreserve97PreferenceFingerprintDrift')
    return current


def preserve(output):
    source, destination, output = paths(output)
    api, candidate, processes, _, _ = smoke.readers()
    old_report = completed(source);idle(processes, old_report['pid'])
    old = evidence();inputs = protected(api, candidate);before = inventory(source)
    need(evidence() == old, 'SmokePreserve97OldEvidenceChanging')
    safe(output);output.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 1, 'status': 'PRESERVING_COMPLETED_FAILED_SMOKE97', 'startedUtc': api.utc(),
              'runner': binding(Path(__file__)), 'failedInvocation': binding(OLD / 'Invocation.json'),
              'failedNativeReport': binding(OLD / 'Native.json'), 'sourceProject': str(source), 'preservedProject': str(destination),
              'oldEvidenceBefore': old, 'projectRelocated': False, 'processStopOrDeleteExecuted': False,
              'oldResultRewritten': False, 'scope': 'One completed failed private smoke preserved by same-volume rename. No new compile result, deletion, process stop, vendor/main/SDK/preference or device mutation.'}
    api.write(output / 'Authorization.json', report);api.write(output / 'Project_before.json', before)
    try:
        idle(processes, old_report['pid']);need(protected(api, candidate) == inputs, 'SmokePreserve97SourceChangedBeforeRename')
        need(inventory(source) == before and evidence() == old, 'SmokePreserve97EvidenceOrProjectChanging')
        # Recheck every existing ancestor immediately around the mutation.
        source, destination, _ = paths_for_rename(source, destination)
        os.rename(extended(source), extended(destination));report['projectRelocated'] = True
        after = inventory(destination);api.write(output / 'Project_after.json', after)
        need(after == before and not present(source), 'SmokePreserve97MovedProjectMismatch')
        need(evidence() == old and protected(api, candidate) == inputs, 'SmokePreserve97OldEvidenceOrInputsChanged')
        idle(processes, old_report['pid'])
        report.update(status='PASS_COMPLETED_FAILED_SMOKE97_PRESERVED_READY_FOR_FRESH_PREPARATION',
                      projectFileCount=after['fileCount'], projectBytes=after['bytes'], oldEvidenceUnchanged=True,
                      mainAndCandidate66Unchanged=True, preferenceFingerprintsUnchanged=True)
    except Exception as error:
        report.update(status='FAIL_COMPLETED_SMOKE97_PRESERVATION_GUARD', errorType=type(error).__name__)
        if isinstance(error, ValueError) and re.fullmatch(r'[A-Za-z0-9]{1,120}', str(error)):
            report['errorCategory'] = str(error)
    finally:
        report['finishedUtc'] = api.utc();api.write(output / 'Report.json', report)
    return report


def paths_for_rename(source, destination):
    safe(source);safe(destination);safe(destination.parent)
    need(source == safe(smoke.PRIVATE / 'Smoke') and destination == safe(smoke.PRIVATE / 'SF2')
         and present(source) and not present(destination), 'SmokePreserve97FixedRenameBoundaryRequired')
    return source, destination, None


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path, required=True);args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not args.out.is_absolute():
        parser.error('Explicit root Windows preservation with absolute fresh receipt UUID required')
    try:
        report = preserve(args.out)
        print(json.dumps({'status': report['status'], 'projectRelocated': report['projectRelocated'], 'oldResultRewritten': False}))
        return 0 if report['status'].startswith('PASS_') else 1
    except Exception as error:
        print(json.dumps({'status': 'REFUSED_COMPLETED_SMOKE97_PRESERVATION', 'errorType': type(error).__name__}));return 1


if __name__ == '__main__':
    raise SystemExit(main())
