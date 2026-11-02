"""Read-only host/device-evidence reconciliation after the ordinary LD0 launch."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / '.verification-cache/Review116/EmulatorHostRelaunch01'
OUT = ROOT / 'Verification/Evidence/Review116/Emulator/ExternalShutdownRelaunch01'


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


def main():
    keep = ROOT / 'Verification/Evidence/Review116/RetainedSources/ExternalEmulatorLaunchUsed'
    keep.mkdir(exist_ok=False)
    runner = ROOT / 'Verification/Tools/Review116/relaunch_emulator116.py'
    (keep / runner.name).write_bytes(runner.read_bytes())
    base = ROOT / 'Verification/Evidence/Review116/Emulator'
    oldp = base / 'RegressionCanonicalAlias04/After.json'
    ownp = base / 'RegressionCanonicalAlias04/OwnOrdinaryAfter.json'
    newp = base / 'LTSAfterOrdinaryEmulatorLaunch01/Inventory.json'
    old, own, new = [json.loads(path.read_text()) for path in (oldp, ownp, newp)]
    config = Path('E:/LDPlayer/LDPlayer14/vms/config/leidian0.config')
    before = (CACHE / 'ConfigBefore.private').read_bytes()
    after = config.read_bytes()
    (CACHE / 'ConfigAfter.private').write_bytes(after)
    ca, cb = json.loads(before), json.loads(after)
    files = []
    for name in ('leidian.vbox', 'data.vdi', 'sdcard.vdi'):
        path = Path('E:/LDPlayer/LDPlayer14/vms/leidian0') / name
        info = path.stat()
        files.append(dict(name=name, bytes=info.st_size, inode=info.st_ino,
            createdUtc=datetime.datetime.fromtimestamp(info.st_ctime, datetime.timezone.utc).isoformat()))
    games = [dict(package=package, apkBytesEqual=row['apkSha256'] == new['games'][package]['apkSha256'],
        allObservedDataBytesEqual=row['data'] == new['games'][package]['data'],
        files=len(row['data']['files']), idle=new['games'][package]['idleProof']['idle'])
        for package, row in old['games'].items()]
    value = dict(status='PASS_READ_ONLY_POST_EXTERNAL_SHUTDOWN_RECONCILIATION116',
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), ordinaryExistingInstanceLaunch=True,
        instanceIndex=0, serialSha256=new['identity']['serialSha256'],
        newBootIdSha256=new['identity']['bootIdSha256'], priorBootIdSha256=old['identity']['bootIdSha256'],
        newBootExplicitlyRecorded=True, packageInstallationReferencesEqual=old['packages'] == new['packages'],
        packageCount=len(new['packages']), existingGames=games,
        r2CompleteDataBytesEqual=own == new['games']['com.heartoftherain.review116r2']['data'],
        r2Idle=new['games']['com.heartoftherain.review116r2']['idleProof']['idle'],
        settingsNamespaceEqual={key: old['settingsSha256'][key] == new['settingsSha256'][key]
            for key in old['settingsSha256']},
        globalChangedKeys=['Phenotype_boot_count', 'boot_count', 'network_watchlist_last_report_time', 'phone_package_install'],
        configurationSha256Before=hashlib.sha256(before).hexdigest(),
        configurationSha256After=hashlib.sha256(after).hexdigest(),
        configurationChangedKeys=sorted(key for key in set(ca) | set(cb) if ca.get(key) != cb.get(key)),
        existingDiskFileMetadataAfter=files, before=bind(oldp), r2Before=bind(ownp), after=bind(newp),
        launchRunner=bind(keep / runner.name), reconciliationRunner=bind(Path(__file__)),
        wrapperFailureRetained='Start-Process -Wait waited for the child player tree; timeout did not mean failed ordinary startup. No repeated launch.',
        privateBridge='Ownedlocalhost5041 registered only the already-listening instance0 adbd5555 with AOSP host:emulator notification; default server untouched.',
        protocolSource='https://android.googlesource.com/platform/packages/modules/adb/+/HEAD/docs/dev/services.md',
        scope='Same preserved instance ordinary launch after external shutdown. No phone query, emulator reset/recreate/repair, settings write, package/data reconstruction or default-server command. Historical full-disk hashes and a durable prelaunch disk-metadata receipt do not exist; no full-disk equality claim. Read-only observed package/profile bytes independently match the prior run.')
    assert value['packageInstallationReferencesEqual'] and value['r2CompleteDataBytesEqual'] and value['r2Idle']
    assert all(row['apkBytesEqual'] and row['allObservedDataBytesEqual'] and row['idle'] for row in games)
    for name, report in (
        ('Reconciliation.json', value),
        ('WrapperOutcome.json', dict(status='FAIL_LAUNCH_WRAPPER_TIMEOUT_ACTUAL_INSTANCE_STARTED',
            errorType='TimeoutExpired', runner=bind(keep / runner.name),
            actualOutcome='Reconciled separately read-only; no repeated launch.'))):
        with (OUT / name).open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
    print(json.dumps({key:value[key] for key in ('status', 'packageCount', 'configurationChangedKeys',
        'r2CompleteDataBytesEqual')}))


if __name__ == '__main__':
    main()
