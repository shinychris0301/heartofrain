"""Root-operated UI observations; imports never dispatch device mutations.

No country is selected, account linked, reward claimed or game attempt started.
Actual screenshots and root visual assessment establish the observed UI state.
"""
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from phone import CapturePathPhone, public_binding, utc, write

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/RegionalAccounts89/Phone/Device01'


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def when(value):
    return value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))


class Review:
    def __init__(self):
        self.phone = CapturePathPhone(OUT)
        self.path = OUT / 'UI_Actions.json'

    def begin(self):
        if self.path.exists():
            raise RuntimeError('ExistingUiReviewPreserved')
        self.phone.assert_installed()
        self.phone.assert_no_active_attempt()
        write(OUT / 'OrdinaryBefore.json', self.phone.inventory())
        shutil.copy2(ROOT / 'Verification/Evidence/RegionalAccounts89/Builds/8713b50e53fe4631b190d52ee3620d02/FrozenSources.json', OUT / 'SourceManifest.json')
        began = self.phone.start_marker('HOTR_RunDisplay88', 'observe')
        save(self.path, {'status': 'OBSERVING_UI89_REQUIRES_VISUAL_REVIEW', 'startedUtc': utc(),
            'nativeLaunchUtc': began.isoformat(), 'runner': public_binding(Path(__file__)), 'actions': [], 'captures': []})
        self.wait('Home', began)
        return self.capture('Home_Initial')

    def wait(self, page, after):
        launch = when(json.loads(self.path.read_text())['nativeLaunchUtc'])
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            raw = self.phone.adb('shell', 'cat', self.phone.base + '/Display88/Report.json', check=False)
            try:
                report = json.loads(raw)
                fresh = when(report['startedUtc']) >= launch and when(report['lastSampleUtc']) >= when(after)
                geometry = report['snapshots'][-1]['geometry']
                overlays = geometry['visibleOverlayTypes']
                expected = geometry['home']['presentationVisible'] and not any(x.endswith('LaunchPage') for x in overlays) if page == 'Home' else any(x.endswith('.' + page) for x in overlays)
                if fresh and expected:
                    return report
            except (ValueError, TypeError, KeyError, IndexError):
                pass
            time.sleep(1)
        raise RuntimeError('FreshObserverDeadline' + page)

    def tap(self, name, x, y, page):
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
        return self.capture(name)

    def capture(self, name):
        path = self.phone.capture('Screens/' + name + '.png')
        record = json.loads(self.path.read_text())
        record['captures'].append(public_binding(path))
        save(self.path, record)
        return str(path)

    def finish(self):
        self.phone.assert_no_active_attempt()
        before = json.loads((OUT / 'OrdinaryBefore.json').read_text())
        after = self.phone.inventory()
        for field in ('profiles', 'preferences', 'profileSummaries'):
            if before[field] != after[field]:
                raise RuntimeError('OrdinaryDataChangedNoMoreMutations')
        write(OUT / 'OrdinaryAfter.json', after)
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
