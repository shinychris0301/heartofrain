"""Explicit physical-phone access; never selects an emulator or resets app data."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
ADB = Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PACKAGE = 'com.heartoftherain.verification'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


class Phone:
    def __init__(self, run_dir):
        self.root = ROOT
        self.run_dir = Path(run_dir).resolve()
        assert self.run_dir.is_relative_to((ROOT/'Verification/Evidence/Physical87').resolve())
        self.target = json.loads((self.run_dir/'Target.json').read_text('utf-8'))
        self.serial = os.environ['HOTR_PHYSICAL_SERIAL']
        assert re.fullmatch(r'[A-Za-z0-9]{8,64}', self.serial) and not self.serial.startswith('emulator')
        assert hashlib.sha256(self.serial.encode()).hexdigest() == self.target['serialSHA256']
        assert self.target['authorization'] == 'OWNER_CONNECTED_PHYSICAL_PHONE87'
        self.base = '/sdcard/Android/data/' + PACKAGE + '/files'
        assert self.adb('get-state') == 'device'
        assert self.adb('shell', 'getprop', 'ro.kernel.qemu') != '1'
        assert self.adb('shell', 'getprop', 'ro.product.model') == self.target['model']
        self.apk = ROOT/self.target['apk']
        assert sha(self.apk) == self.target['apkSHA256']
        self.assert_installed()

    def adb(self, *args, binary=False, check=True):
        result = subprocess.run([str(ADB), '-s', self.serial, *map(str, args)], capture_output=True, timeout=180)
        if check and result.returncode:
            # Do not export private command bodies, clipboard text or tokens.
            raise RuntimeError('PhoneAdbFailed:' + str(args[0]))
        return result.stdout if binary else result.stdout.decode('utf-8', 'replace').strip()

    def exists(self, path):
        result = subprocess.run([str(ADB), '-s', self.serial, 'shell', 'test', '-e', path], capture_output=True, timeout=30)
        assert result.returncode in (0, 1)
        return result.returncode == 0

    def assert_installed(self):
        path = self.adb('shell', 'pm', 'path', PACKAGE).removeprefix('package:')
        assert path.startswith('/data/app/') and path.endswith('/base.apk') and '\n' not in path
        assert self.adb('shell', 'sha256sum', path).split()[0] == self.target['apkSHA256']

    def assert_no_active_attempt(self):
        path = self.base+'/Profiles/Development-v1/profile.json'
        if not self.exists(path):
            return {'profilePresent': False, 'activeAttempts': 0}
        envelope = json.loads(self.adb('exec-out', 'cat', path))
        profile = json.loads(envelope['payload'])
        active = sum(a['state'] in ('Reserved', 'Started') for a in profile['attempts'])
        assert active == 0, 'Preserve active ordinary attempt; no stop, install or fixture launch'
        return {'profilePresent': True, 'activeAttempts': active, 'profileRevision': profile['revision']}

    def snapshot(self):
        """Hash only ordinary profiles/preferences; never export their contents."""
        profiles = {}
        directory = self.base+'/Profiles'
        if self.exists(directory):
            for path in self.adb('shell', 'find', directory, '-type', 'f').splitlines():
                assert re.fullmatch(re.escape(directory)+r'/[A-Za-z0-9_./-]+', path)
                profiles[path.removeprefix(self.base+'/')] = self.adb('shell', 'sha256sum', path).split()[0]
        preferences = {}
        names = self.adb('shell', 'run-as', PACKAGE, 'ls', 'shared_prefs', check=False).split()
        for name in names:
            assert re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', name)
            preferences[name] = hashlib.sha256(self.adb('exec-out', 'run-as', PACKAGE, 'cat', 'shared_prefs/'+name, binary=True)).hexdigest()
        return {'profiles': profiles, 'preferences': preferences}

    def profile_summary(self):
        path = self.base+'/Profiles/Development-v1/profile.json'
        if not self.exists(path):
            return {'profilePresent': False}
        p = json.loads(json.loads(self.adb('exec-out', 'cat', path))['payload'])
        names = ['revision', 'coins', 'lives', 'maxLives', 'completed', 'currentLevel', 'livesRefillDueUnix']
        return {k: p.get(k) for k in names} | {'attemptStates': [a['state'] for a in p['attempts']]}

    def launch(self):
        return self.adb('shell', 'am', 'start', '-W', '-n', PACKAGE+'/com.unity3d.player.UnityPlayerActivity')

    def foreground(self):
        return any(PACKAGE in line for line in self.adb('shell', 'dumpsys', 'activity', 'activities').splitlines()
                   if 'topResumedActivity=' in line or 'mResumedActivity:' in line)

    def capture(self, name):
        assert self.foreground(), 'Capture only our foreground app'
        policy = self.adb('shell', 'dumpsys', 'window', 'policy')
        keyguard = policy.split('KeyguardServiceDelegate', 1)[-1]
        assert re.search(r'(?m)^\s*showing=false\s*$', keyguard), 'No lockscreen/notification capture'
        path = (self.run_dir/name).resolve()
        assert path.is_relative_to(self.run_dir) and path.suffix == '.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.adb('exec-out', 'screencap', '-p', binary=True)
        assert data.startswith(b'\x89PNG\r\n\x1a\n')
        path.write_bytes(data)
        return path

    def start_marker(self, name, content):
        assert re.fullmatch(r'HOTR_[A-Za-z0-9_]+', name)
        self.assert_no_active_attempt()
        self.adb('shell', 'am', 'force-stop', PACKAGE)
        assert not self.adb('shell', 'pidof', PACKAGE, check=False)
        private = ROOT/'.verification-cache/Physical87/Markers'/self.run_dir.name/name
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(content if isinstance(content, bytes) else str(content).encode('utf-8'))
        self.adb('shell', 'mkdir', '-p', self.base)
        self.adb('push', private, self.base+'/'+name)
        started = datetime.now(timezone.utc)
        self.launch()
        return started

    def finish_probe(self):
        self.assert_no_active_attempt()
        self.adb('shell', 'am', 'force-stop', PACKAGE)
        time.sleep(1)
        result = self.launch()
        time.sleep(4)
        assert self.adb('shell', 'pidof', PACKAGE, check=False)
        return result

    def app_log(self, name):
        pid = self.adb('shell', 'pidof', PACKAGE)
        assert re.fullmatch(r'\d+', pid)
        body = self.adb('logcat', '-d', '--pid='+pid, '-v', 'brief')
        body = body.replace(self.serial, 'physical-phone-1')
        assert not re.search(r'Bearer\s+[A-Za-z0-9_./+=-]{32,}|-----BEGIN (?:RSA )?PRIVATE KEY-----', body)
        path = self.run_dir/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')
        return {'pid': pid, 'log': path.relative_to(self.run_dir).as_posix(), 'sha256': sha(path),
                'selectedErrorCount': len(re.findall(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException|DllNotFoundException', body))}
