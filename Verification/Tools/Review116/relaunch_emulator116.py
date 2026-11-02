"""Ordinary launch of the already established LDPlayer0 after external shutdown.

No reset, clone, configuration write, device repair, default-adb command or
physical-device command. Raw configuration and instance titles remain private.
"""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HOST = Path('E:/LDPlayer/LDPlayer14')
PRIVATE = ROOT / '.verification-cache/Review116/EmulatorHostRelaunch01'
PUBLIC = ROOT / 'Verification/Evidence/Review116/Emulator/ExternalShutdownRelaunch01'


def need(value, code):
    if not value:
        raise ValueError(code)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def record(path):
    info = path.stat()
    with path.open('rb') as source:
        header = source.read(1024 * 1024)
    return dict(name=path.name, bytes=info.st_size, inode=info.st_ino,
        createdUtc=datetime.datetime.fromtimestamp(info.st_ctime, datetime.timezone.utc).isoformat(),
        modifiedUtc=datetime.datetime.fromtimestamp(info.st_mtime, datetime.timezone.utc).isoformat(),
        firstMiBSha256=digest(header))


def listing(name):
    result = subprocess.run([str(HOST / 'ldconsole.exe'), 'list2'], capture_output=True,
        timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    (PRIVATE / (name + '.private')).write_bytes(result.stdout + result.stderr)
    need(result.returncode == 0, 'ExistingInstalledConsoleQueryRequired')
    rows = [line.split(',') for line in result.stdout.decode('utf-8', 'replace').splitlines() if line]
    selected = [row for row in rows if len(row) >= 7 and row[0] == '0']
    need(len(selected) == 1, 'EstablishedInstanceZeroRequired')
    return selected[0]


def main():
    need(PRIVATE.is_dir() and not PUBLIC.exists(), 'FreshOwnedRelaunchEvidenceRequired')
    PUBLIC.mkdir(parents=True)
    old = json.loads((ROOT / '.verification-cache/AndroidTesting95/Discovery/Set03/Selector.json').read_text('utf-8-sig'))
    need(old['index'] == 0 and digest(old['serial'].encode()) ==
        '04ab3fc382bfb33ea4fbc120f5172ecfc4aed71652e00977064492ca0f65a017', 'OriginalInstanceAndTransportRequired')
    before = listing('ConsoleBeforeLaunch')
    need(before[4] == '0' and before[5:7] == ['-1', '-1'], 'ExistingInstanceMustBeFullyStopped')
    config = HOST / 'vms/config/leidian0.config'
    original_config = config.read_bytes()
    (PRIVATE / 'ConfigBefore.private').write_bytes(original_config)
    settings = json.loads(original_config.decode('utf-8-sig'))
    prior = json.loads((ROOT / 'Verification/Evidence/Review116/Emulator/RegressionCanonicalAlias04/After.json').read_text('utf-8-sig'))
    need(settings['propertySettings.phoneModel'] == prior['identity']['model']
        and settings['propertySettings.phoneManufacturer'] == prior['identity']['manufacturer']
        and settings['advancedSettings.resolution'] == dict(width=1600, height=900)
        and settings['advancedSettings.resolutionDpi'] == 240, 'ExistingProfileMustMatchPriorInventory')
    paths = [HOST / 'vms/leidian0' / name for name in ('leidian.vbox', 'data.vdi', 'sdcard.vdi')]
    need(all(path.is_file() and not path.is_symlink() for path in paths), 'OriginalDescriptorAndDisksRequired')
    files_before = [record(path) for path in paths]
    need(files_before[1]['bytes'] > 1024**3 and files_before[2]['bytes'] > 1024**3, 'ExistingPopulatedDisksRequired')
    started = utc()
    (PUBLIC / 'BeforeLaunch.json').write_text(json.dumps(dict(utc=started, instanceIndex=0,
        files=files_before, configurationSha256=digest(original_config)), indent=2) + '\n', encoding='utf-8')
    # The shell starts only the installed console helper, with a hidden window.
    result = subprocess.run(['powershell', '-NoProfile', '-Command',
        "$launch116 = Start-Process -FilePath 'E:/LDPlayer/LDPlayer14/ldconsole.exe' -ArgumentList @('launch','--index','0') -WindowStyle Hidden -PassThru; if (-not $launch116.WaitForExit(15000)) { throw 'OwnedConsoleDidNotExit' }; $launch116 | Select-Object Id,ExitCode | ConvertTo-Json -Compress"],
        capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    (PRIVATE / 'OrdinaryLaunch.private').write_bytes(result.stdout + result.stderr)
    need(result.returncode == 0, 'OrdinaryExistingInstanceLaunchFailed')
    current = None
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        current = listing('ConsoleAfterLaunch')
        if current[4] == '1' and all(re.fullmatch('[1-9][0-9]*', current[column]) for column in (5, 6)):
            break
        time.sleep(4)
    need(current[4] == '1', 'OriginalInstanceDidNotStartNormally')
    files_after = [record(path) for path in paths]
    need(all(a['inode'] == b['inode'] and a['createdUtc'] == b['createdUtc']
        for a, b in zip(files_before, files_after, strict=True)), 'OriginalDiskFileIdentitiesRequired')
    config_after = config.read_bytes()
    (PRIVATE / 'ConfigAfter.private').write_bytes(config_after)
    settings_after = json.loads(config_after.decode('utf-8-sig'))
    changed_keys = sorted(key for key in set(settings) | set(settings_after) if settings.get(key) != settings_after.get(key))
    value = dict(status='PASS_ORDINARY_EXISTING_EMULATOR116_RELAUNCH', startedUtc=started, finishedUtc=utc(),
        instanceIndex=0, serialSha256=digest(old['serial'].encode()),
        externalShutdownObserved=True, originalInstanceWasStopped=True, normalInstalledConsoleLaunch=True,
        filesBefore=files_before, filesAfter=files_after, originalDiskFileIdentitiesPreserved=True,
        descriptorBytesUnchanged=files_before[0]['firstMiBSha256'] == files_after[0]['firstMiBSha256'],
        configurationSha256Before=digest(original_config), configurationSha256After=digest(config_after),
        configurationChangedKeys=changed_keys, hostPlayerPid=int(current[5]), hostVmPid=int(current[6]),
        deviceCommandsPerformed=False, defaultAdbServerCommandPerformed=False,
        runnerSha256=digest(Path(__file__).read_bytes()),
        scope='Ordinary launch of the same established stopped instance0 and same existing disk files after an external shutdown. No historical full-disk hashes existed, and guest boot legitimately writes its disks; no full-disk-byte equality claim. Package/profile preservation and current boot identity require the following private-bridge read-only inventory.')
    (PUBLIC / 'Relaunch.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key:value[key] for key in ('status', 'instanceIndex', 'originalDiskFileIdentitiesPreserved',
        'descriptorBytesUnchanged', 'configurationChangedKeys')}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        print(json.dumps(dict(status='BLOCKED_EXISTING_EMULATOR116_RELAUNCH', errorType=type(error).__name__,
            code=code if re.fullmatch('[A-Za-z0-9]{1,100}', code) else 'PrivateEvidenceRequired')), flush=True)
        raise SystemExit(1)
