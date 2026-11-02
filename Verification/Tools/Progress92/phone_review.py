"""Root-operated UI observations; imports never dispatch device mutations.

No account is linked, reward claimed or game attempt started.
Actual screenshots and root visual assessment establish the observed UI state.
"""
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from phone import CapturePathPhone, public_binding, utc, write

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Progress92/Phone/Device01'


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def when(value):
    return value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))


class Review:
    def __init__(self):
        self.phone = CapturePathPhone(OUT)
        self.path = OUT / 'UI_Actions.json'

    def begin(self, source_manifest, *, capture_home=False):
        if self.path.exists():
            raise RuntimeError('ExistingUiReviewPreserved')
        self.phone.assert_installed()
        self.phone.assert_no_active_attempt()
        write(OUT / 'OrdinaryBefore.json', self.phone.inventory())
        source_manifest = Path(source_manifest).resolve()
        if not source_manifest.is_relative_to((ROOT / 'Verification/Evidence/Progress92/Builds').resolve()) or source_manifest.name != 'FrozenSources.json':
            raise RuntimeError('Current92BuildSourceManifestRequired')
        shutil.copy2(source_manifest, OUT / 'SourceManifest.json')
        began = self.phone.start_marker('HOTR_RunPageBackdrop90', 'observe')
        save(self.path, {'status': 'OBSERVING_UI92_REQUIRES_VISUAL_REVIEW', 'startedUtc': utc(),
            'nativeLaunchUtc': began.isoformat(), 'runner': public_binding(Path(__file__)), 'actions': [], 'captures': []})
        self.wait('Home', began)
        return self.capture('Home_Initial') if capture_home else None

    def wait(self, page, after):
        launch = when(json.loads(self.path.read_text())['nativeLaunchUtc'])
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            raw = self.phone.adb('shell', 'cat', self.phone.base + '/PageBackdrop90/Report.json', check=False)
            try:
                report = json.loads(raw)
                fresh = when(report['startedUtc']) >= launch and when(report['lastSampleUtc']) >= when(after)
                geometry = report['snapshots'][-1]['geometry']
                overlays = geometry['visibleOverlayTypes']
                expected = geometry['home']['presentationVisible'] and not overlays if page == 'Home' else any(x.endswith('.' + page) for x in overlays)
                if fresh and expected:
                    return report
            except (ValueError, TypeError, KeyError, IndexError):
                pass
            time.sleep(1)
        raise RuntimeError('FreshObserverDeadline' + page)

    def tap(self, name, x, y, page, *, capture=True):
        record = json.loads(self.path.read_text())
        if any(row['name'] == name for row in record['actions']):
            raise RuntimeError('DuplicateUiActionRefused')
        if not 0 <= x < 720 or not 0 <= y < 1600:
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
        record = json.loads(self.path.read_text())
        record['captures'].append(public_binding(path))
        save(self.path, record)
        return str(path)

    def swipe(self, name, x1, y1, x2, y2, milliseconds, page):
        """One explicit bounded UI-scroll gesture; never infer a game action."""
        record = json.loads(self.path.read_text())
        if any(row['name'] == name for row in record['actions']):
            raise RuntimeError('DuplicateUiActionRefused')
        if not all(type(value) is int for value in (x1, y1, x2, y2, milliseconds)) or not (0 <= x1 < 720 and 0 <= x2 < 720 and 0 <= y1 < 1600 and 0 <= y2 < 1600 and 100 <= milliseconds <= 1000):
            raise RuntimeError('OutsideBoundedPhoneGesture')
        action = {'name': name, 'kind': 'swipe', 'from': [x1, y1], 'to': [x2, y2], 'milliseconds': milliseconds, 'utc': utc(), 'dispatch': 'PENDING'}
        record['actions'].append(action)
        save(self.path, record)
        self.phone.adb('shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(milliseconds))
        action.update(dispatch='ADB_COMPLETED', completedUtc=utc())
        save(self.path, record)
        report = self.wait(page, action['completedUtc'])
        save(OUT / ('Geometry_' + name + '.json'), report)
        return self.capture(name)

    def key_back(self, name):
        """One explicitly named Android Back key; no route or retry implied."""
        record = json.loads(self.path.read_text())
        if any(row['name'] == name for row in record['actions']):
            raise RuntimeError('DuplicateUiActionRefused')
        action = {'name': name, 'kind': 'AndroidBack', 'utc': utc(), 'dispatch': 'PENDING'}
        record['actions'].append(action)
        save(self.path, record)
        self.phone.adb('shell', 'input', 'keyevent', '4')
        action.update(dispatch='ADB_COMPLETED', completedUtc=utc())
        save(self.path, record)
        return action

    def observer(self, name='Observer_Final.json'):
        """Preserve the actual observer bytes without inferring pass/readiness."""
        destination = OUT / name
        if destination.exists() or not destination.resolve().is_relative_to(OUT.resolve()) or destination.suffix != '.json':
            raise RuntimeError('FreshObserverDestinationRequired')
        raw = self.phone.adb('exec-out', 'cat', self.phone.base + '/PageBackdrop90/Report.json', binary=True)
        report = json.loads(raw)
        if when(report['startedUtc']) < when(json.loads(self.path.read_text())['nativeLaunchUtc']):
            raise RuntimeError('ObserverFromPreviousLaunchRefused')
        destination.write_bytes(raw)
        return public_binding(destination)

    def renew_observer(self, name):
        """Explicit idle restart for another bounded observation segment."""
        if not name.isalnum() or len(name) > 24:
            raise RuntimeError('ShortObservationSegmentNameRequired')
        record = json.loads(self.path.read_text())
        if any(row['name'] == name for row in record['actions']):
            raise RuntimeError('DuplicateUiActionRefused')
        self.phone.assert_no_active_attempt()
        previous = self.observer('Observer_' + name + '_Before.json')
        action = {'name': name, 'kind': 'RestartReadOnlyObserver', 'utc': utc(), 'previousObserver': previous, 'previousNativeLaunchUtc': record['nativeLaunchUtc'], 'dispatch': 'PENDING'}
        record['actions'].append(action)
        save(self.path, record)
        began = self.phone.start_marker('HOTR_RunPageBackdrop90', 'observe')
        action.update(dispatch='ADB_COMPLETED', completedUtc=utc())
        record['nativeLaunchUtc'] = began.isoformat()
        save(self.path, record)
        report = self.wait('Home', began)
        save(OUT / ('Geometry_' + name + '.json'), report)
        return self.capture(name + '_Home')

    def finish(self):
        self.phone.assert_no_active_attempt()
        before = json.loads((OUT / 'OrdinaryBefore.json').read_text())
        after = self.phone.inventory()
        for field in ('profiles', 'preferences', 'profileSummaries'):
            if before[field] != after[field]:
                raise RuntimeError('OrdinaryDataChangedNoMoreMutations')
        write(OUT / 'OrdinaryAfter.json', after)
        self.observer()
        relaunch = self.phone.finish_probe()
        final = self.phone.inventory()
        for field in ('profiles', 'preferences', 'profileSummaries'):
            if before[field] != final[field]:
                raise RuntimeError('OrdinaryDataChangedAfterRelaunch')
        write(OUT / 'OrdinaryAfterRelaunch.json', final)
        write(OUT / 'Relaunch.json', relaunch)
        log = self.phone.app_log('Runtime.log')
        write(OUT / 'Log_Review.json', log)
        write(OUT / 'FinalMarkerState.json', {'pendingOptInMarkers': self.phone.pending_markers()})
        return self.capture('Relaunch_Observed')
