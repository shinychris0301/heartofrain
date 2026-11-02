"""Root-operated, idle-only accepted90 baseline; no new target or installation.

The root operator supplies each navigation touch explicitly. Only the unchanged
read-only observer marker is available; ordinary profile/preferences must remain
byte-identical. A newer owner save is preserved rather than reset to old evidence.
"""
import json
import os
from pathlib import Path

from phone import (ROOT, PACKAGE, CapturePathPhone, previous_phone_preflight,
                   public_binding, run_path, write, utc)
from phone_review import Review, save, when

OUT = ROOT / 'Verification/Evidence/Progress92/Baseline90'


class BaselinePhone(CapturePathPhone):
    def __init__(self):
        preflight = previous_phone_preflight()
        self.root, self.out = ROOT, run_path(OUT)
        self.run_dir, self.base = self.out, '/sdcard/Android/data/' + PACKAGE + '/files'
        self.serial = os.environ['HOTR_PHYSICAL_SERIAL']
        self.target = json.loads((ROOT / preflight['priorTarget']['path']).read_text('utf-8-sig'))
        self.serial_sha = self.target['serialSHA256']
        self.preflight = preflight

    def assert_installed(self):
        if self.installed_sha() != self.target['candidateApkSHA256']:
            raise RuntimeError('Accepted90BaselineRequiredNoNewTargetAuthorized')

    def install(self):
        raise RuntimeError('BaselineReaderCannotInstall')


class BaselineReview:
    # These methods use only the instance's reader/journal; no candidate output.
    wait = Review.wait
    key_back = Review.key_back

    def __init__(self):
        self.phone = BaselinePhone()
        self.path = OUT / 'Invocation.json'

    def begin(self):
        if self.path.exists():
            raise RuntimeError('ExistingBaselinePreserved')
        self.phone.assert_installed()
        before = self.phone.require_idle()
        write(OUT / 'Preflight.json', self.phone.preflight)
        write(OUT / 'OrdinaryBefore.json', before)
        record = {'schemaVersion': 1, 'checkpoint': 92, 'status': 'OBSERVING_ACCEPTED90_BASELINE',
                  'utc': utc(), 'runner': public_binding(Path(__file__)),
                  'priorTarget': self.phone.preflight['priorTarget'],
                  'installedSHA256': before['installedSHA256'],
                  'actions': [], 'captures': [],
                  'scope': 'Explicit UI-only accepted90 baseline at the current owner save. No new target, installation, model mutation, reward, account or gameplay action.'}
        save(self.path, record)
        began = self.phone.start_marker('HOTR_RunPageBackdrop90', 'observe')
        record['nativeLaunchUtc'] = began.isoformat()
        save(self.path, record)
        return self.wait('Home', began)

    def tap(self, name, x, y, page, *, capture=False):
        record = json.loads(self.path.read_text('utf-8'))
        if any(row['name'] == name for row in record['actions']):
            raise RuntimeError('DuplicateBaselineUiActionRefused')
        if type(x) is not int or type(y) is not int or not 0 <= x < 720 or not 0 <= y < 1600:
            raise RuntimeError('OutsidePhoneCoordinates')
        action = {'name': name, 'kind': 'tap', 'x': x, 'y': y, 'utc': utc(), 'dispatch': 'PENDING'}
        record['actions'].append(action)
        save(self.path, record)
        self.phone.adb('shell', 'input', 'tap', str(x), str(y))
        action.update(dispatch='ADB_COMPLETED', completedUtc=utc())
        save(self.path, record)
        report = self.wait(page, action['completedUtc'])
        save(OUT / ('Geometry_' + name + '.json'), report)
        return self.capture(name) if capture else report

    def capture(self, name):
        path = self.phone.capture('Screens/' + name + '.png')
        record = json.loads(self.path.read_text('utf-8'))
        record['captures'].append(public_binding(path))
        save(self.path, record)
        return str(path)

    def finish(self):
        self.phone.assert_installed()
        before = json.loads((OUT / 'OrdinaryBefore.json').read_text('utf-8-sig'))
        after = self.phone.require_idle()
        for field in ('profiles', 'preferences', 'profileSummaries'):
            if before[field] != after[field]:
                raise RuntimeError('BaselineOwnerDataChangedNoMoreMutations')
        write(OUT / 'OrdinaryAfter.json', after)
        raw = self.phone.adb('exec-out', 'cat', self.phone.base + '/PageBackdrop90/Report.json', binary=True)
        report = json.loads(raw)
        if when(report['startedUtc']) < when(json.loads(self.path.read_text())['nativeLaunchUtc']):
            raise RuntimeError('BaselineObserverPreviousLaunchRefused')
        with (OUT / 'Observer_Final.json').open('xb') as stream:
            stream.write(raw)
        write(OUT / 'Relaunch.json', self.phone.finish_probe())
        final = self.phone.require_idle()
        for field in ('profiles', 'preferences', 'profileSummaries'):
            if before[field] != final[field]:
                raise RuntimeError('BaselineOwnerDataChangedAfterRelaunch')
        write(OUT / 'OrdinaryAfterRelaunch.json', final)
        markers = self.phone.pending_markers()
        write(OUT / 'FinalMarkerState.json', {'pendingOptInMarkers': markers})
        if markers:
            raise RuntimeError('BaselinePendingMarkersPreserved')
        record = json.loads(self.path.read_text('utf-8'))
        record.update(status='RECORDED_ACCEPTED90_BASELINE_OWNER_PRESERVED',
                      ownerDataUnchanged=True, completedUtc=utc())
        save(self.path, record)
        return record
