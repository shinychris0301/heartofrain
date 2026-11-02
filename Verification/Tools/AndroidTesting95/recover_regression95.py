"""Root-only, separately receipted continuation of the blocked LD regression.

`inspect` issues only read-only commands. `finish` requires a successful bound
inspection, re-proves idle unchanged saves, and may stop/relaunch this exact app
on the originally proved LDPlayer0. No reset, reconnect, clear, install or delete.
The original BLOCKED invocation and its evidence are never changed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

import accepted93_ld as A
import regression95 as R

ROOT = A.ROOT
RUN = ROOT / 'Verification/Evidence/AndroidTesting95/Regression/d95f33d790114d0baceb3bd219c22e62'
OUT = ROOT / 'Verification/Evidence/AndroidTesting95/RegressionRecovery'
REGRESSION_SHA = '0cc47237514e22a85f256d83c445b20ab267adafb38f873d58f1bdf76d77e511'
TRANSPORT_SHA = 'f569eea5daec09481dd9e027c802f67e375e16d1750e0efbae609568a2d37647'
BLOCKED_SHA = 'c423430ba3fbd56456021c8c080b32c3f6b55fabd578784e3785a3e3115284ac'


def verify_binding(value):
    path = ROOT / value['path']
    A.need(path.resolve().is_relative_to(ROOT) and A.bound(path) == value,
           'Recovery95BoundArtifactChanged')
    return path


def output_path(path):
    path = Path(path)
    for item in (path, *path.parents):
        if item.exists():
            A.need(not item.is_symlink() and not getattr(item.stat(), 'st_file_attributes', 0) & 0x400,
                   'Recovery95LinkedOutputRefused')
    path = path.resolve()
    A.need(path.parent == OUT.resolve() and re.fullmatch('[0-9a-f]{32}', path.name) is not None
           and not path.exists(), 'Recovery95FreshUUIDOutputRequired')
    path.mkdir(parents=True, exist_ok=False)
    return path


def host_context():
    A.need(A.sha(Path(A.__file__)) == TRANSPORT_SHA and A.sha(Path(R.__file__)) == REGRESSION_SHA,
           'Recovery95FrozenHelpersChanged')
    A.need(A.sha(RUN/'Invocation.json') == BLOCKED_SHA, 'Recovery95OriginalBlockedReceiptChanged')
    original = A.read(RUN / 'Invocation.json')
    A.need(original.get('status') == 'BLOCKED_ACCEPTED93_LD_REGRESSION95_PRESERVATION'
           and original.get('runId') == RUN.name
           and original.get('preservationFailure') == {'errorType': 'TimeoutExpired'}
           and original.get('sourceProofsUnchanged') is True
           and original.get('lastNativeStatus') == 'PASS_NATIVE_REGRESSION',
           'Recovery95ExactBlockedCompletedRunRequired')
    for name in ('runner', 'ordinaryBefore', 'ordinaryAfter', 'completedNativeReport',
                 'nativeReport', 'atlasReport', 'captureInventory', 'request'):
        verify_binding(original[name])
    for value in (*original['helpers'].values(), *original['fixtureSources']):
        verify_binding(value)
    update_dir = verify_binding(original['acceptedUpdate']).parent
    update = A.validate_update_receipt(update_dir)
    A.need(update['proof'] == original['proof'] and update['identity'] == original['identity'],
           'Recovery95OriginalUpdateSourceOrTargetChanged')
    before = A.read(verify_binding(original['ordinaryBefore']))
    R.same_ordinary(before, A.read(verify_binding(original['ordinaryAfter'])))
    native = A.read(verify_binding(original['nativeReport']))
    rules, proof, _ = R.modules()
    proof.native_scope(native)
    A.need(A.sha(verify_binding(original['completedNativeReport'])) == original['nativeReport']['sha256'],
           'Recovery95CompletedReportMismatch')
    inventory = A.read(verify_binding(original['captureInventory']))
    names = rules.frame_names(native)
    rows = inventory['frames']
    A.need(len(rows) == len(names) and {row['file'] for row in rows} == set(names)
           and len({row['file'] for row in rows}) == len(rows)
           and inventory.get('capturedPngCount') == len(names)
           and inventory.get('retainedPrivatePngCount') == 4,
           'Recovery95CompletedCaptureInventoryInvalid')
    for row in rows:
        A.need(re.fullmatch('[0-9a-f]{64}', row.get('sha256', '')) is not None
               and type(row.get('bytes')) is int and row['bytes'] > 0,
               'Recovery95CaptureHashOrSizeInvalid')
        if row.get('retainedPrivately'):
            verify_binding(row['privateArtifact'])
    return {'original': original, 'originalInvocation': A.bound(RUN/'Invocation.json'),
            'before': before, 'update': update, 'native': native}


def compare_inspection(value, context):
    A.need(value.get('status') == 'PASS_READ_ONLY_ACCEPTED93_LD_REGRESSION95_RECOVERY_INSPECTION'
           and value.get('action') == 'inspect' and value.get('runner') == A.bound(Path(__file__))
           and value.get('originalInvocation') == context['originalInvocation']
           and value.get('proof') == context['update']['proof']
           and value.get('identity') == context['original']['identity']
           and value.get('ordinary') == context['before']
           and value.get('markers') == [] and value.get('readOnlyDeviceCommands') is True,
           'Recovery95CurrentPassedInspectionRequired')


def live_idle(target, context, step):
    step('ldIdentity')
    identity = target.identity()
    A.need(identity == context['original']['identity'], 'Recovery95LDTargetChanged')
    step('pendingMarkers')
    A.need(not R.markers(target), 'Recovery95ForeignOrPendingMarkersPreserved')
    step('ordinaryProfileAndPreferences')
    current = R.ordinary(target)
    R.same_ordinary(context['before'], current)
    step('installedPackageInventory')
    packages = target.packages()
    A.need(packages == context['update']['packagesAfter'], 'Recovery95PackagesChanged')
    step('ownerPID')
    current_pid = R.pid(target)
    return identity, current, current_pid


def finalize(target, context, step):
    # The first mutating command is fenced by a fresh live_idle call. Do not
    # retry a timeout: its outcome is unknown and a new inspection is required.
    identity, current, current_pid = live_idle(target, context, step)
    step('preStopMarkerRecheck')
    A.need(not R.markers(target), 'Recovery95ForeignOrPendingMarkersPreserved')
    if current_pid:
        step('exactOwnerForceStop')
        target.adb('shell', 'am', 'force-stop', A.PACKAGE)
    step('stoppedPID')
    A.need(not R.pid(target), 'Recovery95OwnerDidNotStop')
    step('stoppedOrdinaryData')
    R.same_ordinary(context['before'], R.ordinary(target))
    step('beforeLaunchMarkers')
    A.need(not R.markers(target), 'Recovery95PendingMarkersPreservedNoLaunch')
    step('ordinaryOwnerLaunch')
    normal_pid = R.launch(target)
    step('ordinaryObservation')
    time.sleep(8)
    step('ordinaryAfterRelaunch')
    final = R.ordinary(target)
    R.same_ordinary(context['before'], final)
    step('finalMarkerRecheck')
    A.need(not R.markers(target), 'Recovery95FinalPendingMarkers')
    step('finalLDIdentity')
    A.need(target.identity() == identity, 'Recovery95LDTargetChangedAtExit')
    step('finalPackageInventory')
    A.need(target.packages() == context['update']['packagesAfter'], 'Recovery95FinalPackagesChanged')
    return {'ordinaryAfterRelaunch': final, 'ordinaryDataUnchanged': True, 'markers': [],
            'normalRelaunch': {'pid': int(normal_pid), 'fixedObservationSeconds': 8,
                              'readinessOrPerformanceClaim': False},
            'previousFixturePID': context['original']['fixturePID']}


def run(action, output, inspection=None):
    output = output_path(output)
    record = {'schemaVersion': 1, 'action': action, 'startedUtc': A.utc(),
              'runner': A.bound(Path(__file__)), 'status': 'RUNNING_ACCEPTED93_LD_REGRESSION95_RECOVERY',
              'scope': 'Separate continuation of one completed accepted93 Unity2022 LDPlayer0 regression. '
                       'No original evidence/status rewrite, Unity6, phone, performance or production acceptance.',
              'readOnlyDeviceCommands': action == 'inspect', 'steps': []}

    def step(name):
        record['currentStage'] = name
        record['steps'].append({'stage': name, 'utc': A.utc()})
        R.save(output/'Progress.json', record)

    try:
        step('hostEvidenceAndCurrentSource')
        context = host_context()
        record.update(originalInvocation=context['originalInvocation'], proof=context['update']['proof'],
                      nativeReport=context['original']['nativeReport'],
                      originalOrdinaryBefore=context['original']['ordinaryBefore'],
                      originalOrdinaryAfter=context['original']['ordinaryAfter'],
                      nativeChecks=context['native']['checks'], boards=context['native']['boards'],
                      actions=context['native']['actions'], clips=context['native']['clips'])
        if action == 'finish':
            A.need(inspection is not None, 'Recovery95InspectionRequiredBeforeFinish')
            inspection = Path(inspection).resolve()
            A.need(inspection.parent.parent == OUT.resolve() and inspection.name == 'Recovery.json',
                   'Recovery95ScopedInspectionRequired')
            compare_inspection(A.read(inspection), context)
            record['inspection'] = A.bound(inspection)
        target = A.Target()
        target.deadline = time.monotonic()+600
        if action == 'inspect':
            identity, current, current_pid = live_idle(target, context, step)
            record.update(identity=identity, ordinary=current, markers=[], ownerPID=int(current_pid) if current_pid else None)
            record['status'] = 'PASS_READ_ONLY_ACCEPTED93_LD_REGRESSION95_RECOVERY_INSPECTION'
        else:
            record.update(finalize(target, context, step))
            record['identity'] = context['original']['identity']
            record['status'] = 'PASS_ACCEPTED93_LD_REGRESSION95_SEPARATE_PRESERVATION_RECOVERY'
        step('finalSourceProof')
        A.need(A.accepted_proof() == context['update']['proof'], 'Recovery95SourceChangedAtExit')
        A.need(A.bound(RUN/'Invocation.json') == context['originalInvocation'],
               'Recovery95OriginalBlockedReceiptChangedAtExit')
        record['sourceProofsUnchanged'] = True
    except Exception as error:
        record.update(status='BLOCKED_ACCEPTED93_LD_REGRESSION95_RECOVERY', failure=A.safe(error),
                      requiresOperatorCleanup=True)
    finally:
        record['finishedUtc'] = A.utc()
        A.write(output/'Recovery.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'finish'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--inspection', type=Path)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not args.out.is_absolute():
        parser.error('Explicit root Windows execution and fresh absolute scoped output required')
    result = run(args.action, args.out, args.inspection)
    print(json.dumps({'status': result['status'], 'stage': result.get('currentStage'), 'action': args.action}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
