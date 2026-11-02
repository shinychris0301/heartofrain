"""Replace-install checkpoint 61 on main LDPlayer without modifying player data."""
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/HomeLivesAndroid'
ANDROID = Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer')
ADB = ANDROID / 'SDK/platform-tools/adb.exe'
PKG = 'com.heartoftherain.verification'
BASE = '/sdcard/Android/data/' + PKG + '/files'
SERIAL = 'emulator-5554'


def adb(*args):
    return subprocess.run([str(ADB), '-s', SERIAL, *map(str, args)], capture_output=True, check=True, timeout=180).stdout


def profile():
    envelope = json.loads(adb('exec-out', 'cat', BASE + '/Profiles/Development-v1/profile.json'))
    return json.loads(envelope['payload'])


def balances(p):
    return {k: p[k] for k in ['coins', 'lives', 'maxLives', 'completed', 'currentLevel', 'livesRefillDueUnix']}


def snapshot():
    prefs = {}
    for n in adb('shell', 'run-as', PKG, 'ls', 'shared_prefs').decode().split():
        if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', n):
            body = adb('exec-out', 'run-as', PKG, 'cat', 'shared_prefs/' + n)
            assert body, 'Empty preference read'
            prefs[n] = hashlib.sha256(body).hexdigest()
    saves = {}
    for n in adb('shell', 'find', BASE + '/Profiles', '-type', 'f', '-name', '*.json').decode().splitlines():
        n = n.strip()
        assert re.fullmatch(re.escape(BASE) + r'/Profiles/[A-Za-z0-9_./-]+\.json', n), 'Unexpected save path'
        saves[n.removeprefix(BASE + '/')] = adb('shell', 'sha256sum', n).decode().split()[0]
    assert prefs and saves
    return {'preferences': prefs, 'saves': saves}


def main():
    OUT.mkdir(exist_ok=True)
    source = json.loads((OUT / 'Source_SHA256.json').read_text())
    assert all(hashlib.sha256((ROOT / n).read_bytes()).hexdigest() == h for n, h in source['files'].items()), 'Reviewed source changed'
    artifact = json.loads((OUT / 'APK_Artifact.json').read_text())
    apk = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    sha = hashlib.sha256(apk.read_bytes()).hexdigest()
    assert artifact['sha256'] == sha
    p = profile()
    assert not any(a['state'] in ['Reserved', 'Started'] for a in p['attempts']), 'Active attempt: do not interrupt'
    adb('shell', 'am', 'force-stop', PKG)
    before = snapshot()
    result = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'INSTALLING', 'serial': SERIAL,
              'apk_sha256': sha, 'apk_bytes': apk.stat().st_size, 'profile_before': balances(p), 'before': before,
              'scope': 'Main LDPlayer replacement install and initial Home observation. No uninstall, data clear or gameplay actions in this installer. Hashes only; private save contents are not exported.'}
    def save(): (OUT / 'Main_Installation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    save()
    result['install'] = adb('install', '-r', apk).decode().strip()
    assert 'Success' in result['install']
    result['after_install'] = snapshot()
    result['data_unchanged_by_install'] = before == result['after_install']
    save()
    assert result['data_unchanged_by_install']
    remote = adb('shell', 'pm', 'path', PKG).decode().splitlines()[0].removeprefix('package:').strip()
    result['installed_apk_sha256'] = adb('shell', 'sha256sum', remote).decode().split()[0]
    assert result['installed_apk_sha256'] == sha
    adb('logcat', '-c')
    result['launch'] = adb('shell', 'am', 'start', '-W', '-n', PKG + '/com.unity3d.player.UnityPlayerActivity').decode().strip()
    time.sleep(25)
    result['pid'] = adb('shell', 'pidof', PKG).decode().strip()
    assert result['pid']
    log = adb('logcat', '-d', '--pid=' + result['pid']).decode(errors='replace')
    (OUT / 'Main_Player.log').write_text(log, encoding='utf-8')
    result['runtime_error_lines'] = [line for line in log.splitlines() if re.search(r'FATAL EXCEPTION|Fatal signal|\b(?:NullReferenceException|MissingReferenceException|InvalidOperationException|ArgumentException|IndexOutOfRangeException)\b|\bE Unity\s*:', line)]
    result['after_launch'] = snapshot()
    result['data_unchanged_after_launch'] = before == result['after_launch']
    result['profile_after_launch'] = balances(profile())
    result['foreground_activity'] = [l.strip() for l in adb('shell', 'dumpsys', 'activity', 'activities').decode(errors='replace').splitlines() if 'topResumedActivity=' in l]
    assert result['foreground_activity'] and PKG in result['foreground_activity'][0]
    (OUT / 'Main_Home.png').write_bytes(adb('exec-out', 'screencap', '-p'))
    result['status'] = 'PASS_INSTALLED_DATA_PRESERVED_LAUNCHED' if not result['runtime_error_lines'] and result['data_unchanged_after_launch'] else 'REVIEW_REQUIRED'
    save()
    assert result['status'].startswith('PASS_')
    print(json.dumps({k: result[k] for k in ['status', 'apk_sha256', 'pid', 'data_unchanged_by_install', 'data_unchanged_after_launch']}))


if __name__ == '__main__':
    main()
