"""Signed non-Development APK for the RuStore review, built from an isolated copy of the sandbox project.

The copy drops the private diagnostics panel and demo ad units and adds HOTR_RUSTORE_REVIEW129, which
exempts only this copy from the release guards. Those gates stay unmet and are listed in the report; the
main project keeps every guard. The signing password stays in memory and is scrubbed from generated files.

Usage: build_review129.py <tag> <versionCode> <versionName>
"""
import hashlib, importlib.util, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(r'E:\.verification-cache\HOTR127\Pay01')
HOME = Path(r'E:\.verification-cache\HOTR129\Review01')
PROJECT = HOME / 'Game'
EDITOR = Path(r'E:\HeartRainUnity6LTS95\6000.3.27f1\Editor\Unity.exe')
ANDROID = EDITOR.parent / 'Data/PlaybackEngines/AndroidPlayer'
CUSTODY = Path(os.environ['LOCALAPPDATA']) / 'HeartOfTheRain/ReleaseSigning/RuStore'
GRADLE = Path(r'E:\G129R')
SIGNER = '7257537a5b329cc5b018d93299d748404432c1b49f1b2388444ab843a4ba170d'
EXEMPT = ('#if HOTR_RUSTORE_REVIEW129\n            return%s;\n#endif\n')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def need(value, code):
    if not value:
        raise SystemExit('BLOCKED ' + code)

def insert_after(path, anchor, text):
    source = path.read_bytes().decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in source else '\n'
    anchor_found = anchor.replace('\n', newline)
    need(source.count(anchor_found) == 1, 'GuardAnchor:' + path.name + ':' + anchor[:50])
    path.write_bytes((source.replace(anchor_found, anchor_found + text.replace('\n', newline))).encode('utf-8'))

def prepare():
    if not PROJECT.exists():
        started = time.time()
        shutil.copytree(SOURCE / 'Game', PROJECT, ignore=shutil.ignore_patterns('Bee', 'Temp', 'Builds', 'Logs', 'obj'))
        print('copied project', round(time.time() - started), 's', flush=True)
    assets = PROJECT / 'Assets'
    # Runtime sources follow the sandbox project, which sync128 keeps equal to the main project.
    for relative in ('HeartOfTheRain/App/Advertising/Runtime/InterstitialAds129.cs', 'HeartOfTheRain/App/Launch/Runtime/LaunchPage.cs', 'HeartOfTheRain/App/PreLevel/Runtime/HomeLevelFlow.cs'):
        shutil.copyfile(ROOT / 'Unity/Assets' / relative, assets / relative)
    meta = assets / 'HeartOfTheRain/App/Advertising/Runtime/InterstitialAds129.cs.meta'
    shutil.copyfile(ROOT / 'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/InterstitialAds129.cs.meta', meta)
    diagnostics = assets / 'Review127Diagnostics'
    if diagnostics.exists():
        shutil.rmtree(diagnostics)
        (assets / 'Review127Diagnostics.meta').unlink(missing_ok=True)
    rsp = assets / 'csc.rsp'
    symbols = [s for s in rsp.read_text('utf-8').strip().replace('-define:', '').split(';') if s and s not in ('HOTR_DIAGNOSTICS127', 'HOTR_INTERSTITIAL_DEMO129')]
    if 'HOTR_RUSTORE_REVIEW129' not in symbols:
        symbols.append('HOTR_RUSTORE_REVIEW129')
    rsp.write_text('-define:' + ';'.join(symbols) + '\n', 'utf-8')
    editor = assets / 'Review129Editor/Editor'
    editor.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'Verification/Tools/Review129/ReviewBuild129.cs', editor / 'ReviewBuild129.cs')
    app = assets / 'HeartOfTheRain/App'
    guards = (
        (app / 'RuStore/Editor/RuStoreReleasePreflight.cs', 'public void OnPreprocessBuild(BuildReport report)\n        {\n', ''),
        (app / 'Advertising/Editor/AdvertisingBuild107.cs', 'internal static void Guard(BuildReport report){\n', ''),
        (app / 'ServerGameplay/Editor/ProductionBuildConfiguration122.cs', 'public static bool GuardIfSelected(BuildReport report){\n', ' true'),
        (app / 'ServerGameplay/Editor/StagingServerBuild104.cs', 'internal static void Guard(BuildReport report){\n', ''),
    )
    for path, anchor, value in guards:
        if 'HOTR_RUSTORE_REVIEW129' not in path.read_text('utf-8-sig'):
            insert_after(path, anchor, EXEMPT % value)
    # A plain copy of the review release values; nothing here marks a gate as met.
    release = json.loads((SOURCE / 'Release127.json').read_text('utf-8'))
    release['status'] = 'RUSTORE_REVIEW129_TEST_VERSION_NOT_PRODUCTION_ACCEPTANCE'
    release['versionCode'] = int(sys.argv[2])
    path = HOME / 'Release129.json'
    path.write_text(json.dumps(release, indent=1), 'utf-8')
    return path

def main():
    tag, version = sys.argv[1], sys.argv[3]
    release = prepare()
    output = ROOT / 'Verification/Evidence/Review129/Build' / tag
    need(not output.exists(), 'FreshOutputRequired')
    raw = HOME / 'Raw' / tag
    raw.mkdir(parents=True)
    output.mkdir(parents=True)
    if not GRADLE.exists():
        GRADLE.mkdir()
        previous = Path(r'E:\G127Pay01\caches\modules-2\files-2.1')
        if previous.is_dir():
            shutil.copytree(previous, GRADLE / 'caches/modules-2/files-2.1', ignore=shutil.ignore_patterns('*.lock', '*.lck', 'gc.properties'))
    spec = importlib.util.spec_from_file_location('signing129', ROOT / 'Release/Signing/manage_release_signing.py')
    signing = importlib.util.module_from_spec(spec); spec.loader.exec_module(signing)
    password = signing.local_password(CUSTODY)
    need(signing.verify(CUSTODY, ANDROID / 'OpenJDK', password)['sha256'] == SIGNER, 'ReleaseSignerMismatch')
    apk = PROJECT / 'Builds' / ('HeartOfTheRain_RuStoreReview_' + tag + '.apk')
    need(not apk.exists(), 'FreshApkRequired')
    bee = PROJECT / 'Library/Bee'
    if bee.exists():
        for stale in [bee / 'Android/Prj/IL2CPP/Gradle/launcher/build.gradle', bee / 'artifacts/Android/Gradle/launcher/build.gradle', *bee.glob('Player*-inputdata.json')]:
            stale.unlink(missing_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('HOTR_') and not re.search('KEYSTORE|KEYALIAS|STOREPASS|KEYPASS', k, re.I)}
    env.update(GRADLE_USER_HOME=str(GRADLE), HOTR_REVIEW129_OUT=str(output), HOTR_REVIEW129_APK=str(apk), HOTR_REVIEW129_VERSION=version,
               HOTR_RUSTORE_RELEASE_CONFIG=str(release), HOTR_RELEASE_SIGNING_PASSWORD=password, HOTR_RELEASE_KEYSTORE=str(CUSTODY / signing.KEYSTORE))
    started = time.time()
    try:
        code = subprocess.run([str(EDITOR), '-batchmode', '-projectPath', str(PROJECT), '-buildTarget', 'Android', '-executeMethod', 'HeartOfTheRain.Verification129.ReviewBuild129.Run', '-logFile', str(raw / 'Unity.log')],
                              cwd=PROJECT, env=env, stdin=subprocess.DEVNULL, timeout=3300, creationflags=subprocess.CREATE_NO_WINDOW).returncode
    finally:
        env.pop('HOTR_RELEASE_SIGNING_PASSWORD', None)
        secret = password.encode('ascii'); scrubbed = 0
        for base in (PROJECT / 'Library', PROJECT / 'Temp', PROJECT / 'ProjectSettings', GRADLE, raw):
            if base.exists():
                for path in base.rglob('*'):
                    if path.is_file() and path.suffix.lower() in {'.gradle', '.properties', '.json', '.txt', '.log', '.yaml', '.yml', '.xml', '.bat', '.cmd', '.rsp', '.cs', '.java', '.kt', '.asset'}:
                        data = path.read_bytes()
                        if secret in data:
                            path.write_bytes(data.replace(secret, b'<private-signing-password-removed>')); scrubbed += 1
    log = (raw / 'Unity.log').read_text('utf-8', 'replace') if (raw / 'Unity.log').exists() else ''
    print('exit', code, round(time.time() - started), 's scrubbed', scrubbed, flush=True)
    print('\n'.join(sorted(set(re.findall(r'^.*error CS\d+.*$', log, re.M)))[:12])[:1800])
    print('\n'.join(l[:300] for l in log.splitlines() if re.search(r'BuildFailedException|Build Failed|What went wrong|Ads107|SdkCheckout\w+|blocked:', l))[:1200])
    report = output / 'Native.json'
    if report.exists():
        print(report.read_text('utf-8')[:1500])

if __name__ == '__main__':
    main()
