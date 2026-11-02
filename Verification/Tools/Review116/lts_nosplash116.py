"""Fresh isolated SDK-free LTS build from the canonical116 asset snapshot.

Main and older candidates are read-only. Approved98 LTS Packages/settings and
same-GUID migrated metadata are reused; no SDK, provider or licensing guard is
patched. Build logs remain private and every invocation/artifact is fresh.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
CANONICAL = ROOT / '.verification-cache/Review116/NativeSnapshot/Game'
CANONICAL_PROOF = ROOT / 'Verification/Evidence/Review116/App/NativeSnapshotSourceCut116_Harness05.json'
CANONICAL_SHA = 'b0bc2b91f3a22b9b8bcc6ab230ffa28a7a8f9a8f4972038fd9eeb3c66dfbe28d'
BASE = ROOT / '.verification-cache/Review116/LTSNoSplashCandidate01'
PROJECT = BASE / 'Game'
PUBLIC = ROOT / 'Verification/Evidence/Review116/LTSNoSplash'
EDITOR = Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe')
PACKAGE = 'com.heartoftherain.review116lts'
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review93'))
from run_connected import resume_owned_primary
sys.path.insert(0, str(ROOT / 'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids, process_details
spec = importlib.util.spec_from_file_location('owned_lts116_shutdown', ROOT / 'Verification/Tools/Review107/run_native107.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def need(value, code):
    if not value:
        raise RuntimeError(code)


def write(path, value):
    api.write(path, value)


def plain(path):
    for item in (path, *path.parents):
        if item.exists():
            need(not item.is_symlink() and not getattr(item.stat(), 'st_file_attributes', 0) & 0x400,
                 'LinkedCandidateInputRejected')


def tree(project, parts=('Assets', 'Packages', 'ProjectSettings')):
    values = {}
    for part in parts:
        for path in sorted((project / part).rglob('*')):
            if path.is_file():
                plain(path)
                values[path.relative_to(project).as_posix()] = dict(sha256=api.sha(path), bytes=path.stat().st_size)
    return values


def guid(data):
    result = re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$', data)
    need(len(result) == 1, 'OneAssetGuidRequired')
    return result[0].decode('ascii').lower()


def guids(project):
    values = {p.relative_to(project).as_posix(): guid(p.read_bytes()) for p in (project / 'Assets').rglob('*.meta')}
    need(len(set(values.values())) == len(values), 'AssetGuidCollisionRejected')
    return values


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=api.sha(path), bytes=path.stat().st_size)


def prepare():
    from launch_profile116 import approved_profile, PROFILE, PROFILE_SHA256
    profile, approved_files = approved_profile()
    need(not BASE.exists() and not (PUBLIC / 'Preparation.json').exists(), 'FreshLts116CandidateRequired')
    need(api.sha(CANONICAL_PROOF) == CANONICAL_SHA, 'ExactCanonicalHarness05Required')
    proof = json.loads(CANONICAL_PROOF.read_text('utf-8-sig'))
    before = tree(CANONICAL)
    need({'Unity/' + p: row for p, row in before.items()} == proof['files'], 'CanonicalSourceCutChanged')
    need(os.name != 'nt' or all(len(str(PROJECT / name)) < 260 for name in before),
         'FreshCandidateTagMustKeepWindowsPathsBelow260')
    need(b'6000.3.27f1' in approved_files['ProjectSettings/ProjectVersion.txt'], 'ApprovedPublicLtsProfileRequired')
    settings_before = {name: dict(sha256=row['sha256'], bytes=row['bytes'])
                       for name, row in profile['files'].items() if name.startswith(('Packages/', 'ProjectSettings/'))}
    need(b'  m_ShowUnitySplashScreen: 0' in approved_files['ProjectSettings/ProjectSettings.asset']
         and b'  m_ShowUnitySplashLogo: 0' in approved_files['ProjectSettings/ProjectSettings.asset'],
         'ApprovedNoSplashSettingsRequired')
    BASE.mkdir(parents=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    provenance, migrated = {}, []
    def copy(relative, source, origin):
        destination = PROJECT / relative
        need(not destination.exists(), 'CandidateLeafCollisionRejected')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(source, bytes):
            destination.write_bytes(source)
        else:
            shutil.copy2(source, destination)
        provenance[relative] = origin
    for relative in sorted(before):
        if not relative.startswith('Assets/'):
            continue
        source = CANONICAL / relative
        if relative.endswith('.meta') and relative in approved_files:
            if guid(source.read_bytes()) == guid(approved_files[relative]):
                copy(relative, approved_files[relative], 'approved98-same-GUID-migrated-meta')
                migrated.append(relative)
                continue
        copy(relative, source, 'canonical-Harness05-exact-bytes')
    for relative in ('Assets/Review98Editor.meta', 'Assets/Review98Editor/TransparentIconForeground98.png',
                     'Assets/Review98Editor/TransparentIconForeground98.png.meta'):
        if not (PROJECT / relative).exists():
            copy(relative, approved_files[relative], 'approved98-technical-icon-foreground-only')
    for relative in settings_before:
        copy(relative, approved_files[relative], 'approved98-LTS-package-or-settings')
    settings = PROJECT / 'ProjectSettings/ProjectSettings.asset'
    raw = settings.read_bytes()
    replacements = {
        rb'(?m)^  companyName: [^\r\n]*': b'  companyName: HeartRainReview116LTS',
        rb'(?m)^    Android: com\.heartoftherain\.review98': b'    Android: ' + PACKAGE.encode(),
        rb'(?m)^  bundleVersion: [^\r\n]*': b'  bundleVersion: 116',
        rb'(?m)^  AndroidBundleVersionCode: [^\r\n]*': b'  AndroidBundleVersionCode: 116',
        rb'(?m)^  androidUseCustomKeystore: [^\r\n]*': b'  androidUseCustomKeystore: 0',
    }
    for pattern, replacement in replacements.items():
        raw, count = re.subn(pattern, lambda _: replacement, raw)
        need(count == 1, 'ExactApprovedSettingsShapeRequired')
    settings.write_bytes(raw)
    helper = 'Assets/Review116LtsEditor/Editor/LtsNoSplashBuild116.cs'
    source = Path(__file__).with_name('LtsNoSplashBuild116.cs.template')
    copy(helper, source, 'owned116-Editor-only-no-splash-build-guard')
    for relative, folder in (('Assets/Review116LtsEditor', True), ('Assets/Review116LtsEditor/Editor', True), (helper, False)):
        path = PROJECT / (relative + '.meta')
        need(not path.exists(), 'OwnedHelperMetaCollisionRejected')
        path.write_text('fileFormatVersion: 2\nguid: ' + uuid.uuid4().hex + '\n' +
                        ('folderAsset: yes\nDefaultImporter:\n' if folder else 'MonoImporter:\n  serializedVersion: 2\n') +
                        '  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n', encoding='utf-8')
        provenance[relative + '.meta'] = 'owned116-Editor-helper-GUID'
    copied = tree(PROJECT)
    asset_pins = {name: row['sha256'] for name, row in copied.items() if name.startswith('Assets/') and not name.endswith('.meta')}
    meta_guids = guids(PROJECT)
    original_nonmeta = {name: row for name, row in before.items() if name.startswith('Assets/') and not name.endswith('.meta')}
    need(all(copied[name] == row for name, row in original_nonmeta.items()), 'CanonicalAssetOrSourceCopyChanged')
    need(all(meta_guids[name] == guid((CANONICAL / name).read_bytes()) for name in before if name.startswith('Assets/') and name.endswith('.meta')), 'CanonicalAssetGuidChanged')
    need(tree(CANONICAL) == before, 'ReadOnlySourceChangedDuringPreparation')
    java = {name: row for name, row in copied.items() if name.endswith('.java')}
    launch = [row['sha256'] for name, row in java.items() if name.endswith('/LaunchCurtain99.java')]
    need(launch == ['1de78774460c27255e52ce87efd24d05c8398ad6d23353564d9d2ff9131c8222'], 'ApprovedWorkingStartupJavaRequired')
    receipt = dict(status='PREPARED_LTS_NOSPLASH116', project=str(PROJECT), sourceRoot=str(ROOT), nonce=uuid.uuid4().hex,
        unity='6000.3.27f1', packageName=PACKAGE, paths=list(asset_pins), sha256=list(asset_pins.values()),
        metaPaths=list(meta_guids), metaGuids=list(meta_guids.values()), canonicalManifest=bind(CANONICAL_PROOF),
        canonicalProject=str(CANONICAL), requestedCanonicalSHA256=CANONICAL_SHA,
        durablePublicProfile=dict(path=PROFILE.relative_to(ROOT).as_posix(), sha256=PROFILE_SHA256),
        canonicalInputs=before, copiedInputs=copied, approvedLtsSettingsInputs=settings_before, provenance=provenance,
        migratedMetaPaths=migrated, originalStartupJava=java, candidateOnlySettings=['companyName', 'applicationIdentifier.Android', 'bundleVersion', 'AndroidBundleVersionCode', 'androidUseCustomKeystore'],
        bothSplashFlagsPreservedFalse=True, mainModified=False, sdkProviderActivation=False,
        scope='Fresh SDK-free unpromoted LTS candidate: canonical116 assets/source plus approved98 LTS package/settings, same-GUID migrated metas and one Editor-only build guard. Technical transparent foreground only is inherited outside canonical assets.')
    write(BASE / 'Preparation.json', receipt)
    write(PUBLIC / 'Preparation.json', receipt)
    print(json.dumps(dict(status=receipt['status'], project=PROJECT.relative_to(ROOT).as_posix(), canonicalInputs=len(before), migratedMetaGuids=len(migrated), assetPins=len(asset_pins))), flush=True)


def owned_gradle_home(seed=None, selected_home=None):
    """Seed only public dependencies; never run a foreign cache's init scripts."""
    receipt_path = BASE / 'GradleHomePreparation.json'
    existing = json.loads(receipt_path.read_text('utf-8-sig')) if receipt_path.is_file() else None
    home = (selected_home.resolve() if selected_home is not None else
            Path(existing['home']).resolve() if existing else None)
    need(home is not None and home.parent == Path(ROOT.anchor)
         and re.fullmatch(r'HR116G_[A-Za-z0-9_-]{1,40}', home.name),
         'ExplicitShortOwnedReview116GradleHomeRequired')
    plain(home)
    allowed = [PROJECT / 'Library/Bee/Android/Prj/IL2CPP/Gradle',
               PROJECT / 'Library/Bee/Android/Prj/IL2CPP/Gradle/launcher',
               PROJECT / 'Temp/StagingArea/gradleWarmupArea']
    script = ("if (System.getenv('HOTR_GRADLE116_OFFLINE') != '1') { throw new GradleException('Owned offline116 invocation required') }\n"
              + 'def allowed = ' + json.dumps([p.resolve().as_posix() for p in allowed]) + '\n'
              + "def current = gradle.startParameter.currentDir.canonicalPath.replace('\\\\', '/')\n"
              + "if (!allowed.contains(current)) { throw new GradleException('Unexpected offline116 project') }\n"
              + 'gradle.startParameter.offline = true\n').encode('utf-8')
    init = home / 'init.d/hotr_offline116.gradle'
    if home.exists():
        need(seed is None and existing and Path(existing['home']).resolve() == home and init.read_bytes() == script,
             'ExistingOwnedGradleHomeMustRetainGuardAndReceipt')
        receipt = json.loads(receipt_path.read_text('utf-8-sig'))
        need(receipt['project'] == str(PROJECT) and receipt['status'] == 'PREPARED_OWNED_OFFLINE116_GRADLE_HOME',
             'ExactOwnedGradleProjectRequired')
        return home, bind(receipt_path)
    need(seed is not None, 'ExplicitPublicModules2CacheSeedRequired')
    seed = seed.resolve()
    need(seed.is_dir() and seed.name == 'modules-2' and (seed / 'files-2.1').is_dir(),
         'ExplicitPublicModules2CacheRequired')
    plain(seed)
    before = {}
    for path in sorted(seed.rglob('*')):
        if path.is_file() and not path.name.endswith('.lock') and path.name != 'gc.properties':
            plain(path)
            before[path.relative_to(seed).as_posix()] = dict(sha256=api.sha(path), bytes=path.stat().st_size)
    need(before, 'NonemptyPublicDependencySeedRequired')
    home.mkdir()
    for name in before:
        destination = home / 'caches/modules-2' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(seed / name, destination)
        need(api.sha(destination) == before[name]['sha256'] and api.sha(seed / name) == before[name]['sha256'],
             'PublicDependencySeedCopyMismatch')
    init.parent.mkdir(parents=True)
    init.write_bytes(script)
    write(receipt_path, dict(status='PREPARED_OWNED_OFFLINE116_GRADLE_HOME', project=str(PROJECT), home=str(home),
        seed=str(seed), copiedFiles=before, copiedBytes=sum(row['bytes'] for row in before.values()),
        excluded=['*.lock', 'gc.properties', 'all foreign init scripts and non-module caches'],
        initScript=dict(path=str(init), sha256=api.sha(init), bytes=init.stat().st_size), allowedProjects=[str(p.resolve()) for p in allowed],
        seedFilesReadOnlyAndPreserved=True,
        reference='https://docs.gradle.org/current/userguide/dependency_caching.html#sec:copying_and_reusing_the_cache'))
    return home, bind(receipt_path)


def build(tag, gradle_cache_seed=None, gradle_home_path=None):
    need(os.name == 'nt' and re.fullmatch(r'[A-Za-z0-9_]{1,40}', tag), 'ExplicitFreshWindowsBuildTagRequired')
    receipt = BASE / 'Preparation.json'
    preparation = json.loads(receipt.read_text('utf-8-sig'))
    need(preparation['status'] == 'PREPARED_LTS_NOSPLASH116' and Path(preparation['project']).resolve() == PROJECT.resolve(), 'OwnedLts116PreparationRequired')
    for pid in unity_pids():
        try:
            _, args = process_details(pid, include_command=True)
            if '-projectPath' in args:
                need(Path(args[args.index('-projectPath') + 1]).resolve() != PROJECT.resolve(), 'PreserveActiveCandidateEditor')
        except PermissionError:
            pass
    need(not any(os.environ.get(key) for key in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')), 'UnreviewedJavaOptionsRejected')
    gradle_home, gradle_receipt = owned_gradle_home(gradle_cache_seed, gradle_home_path)
    out, private = PUBLIC / tag, BASE / 'Raw' / tag
    need(not out.exists() and not private.exists(), 'PreserveEarlierInvocationArtifacts')
    out.mkdir(parents=True)
    private.mkdir(parents=True)
    apk = PROJECT / 'Builds/Review116LTS' / ('HeartOfTheRain_Review116LTS_' + tag + '.apk')
    need(not apk.exists(), 'PreserveEarlierApk')
    before = tree(PROJECT)
    source_before = tree(CANONICAL)
    main_critical = {name: api.sha(ROOT / name) for name in ('Unity/ProjectSettings/ProjectVersion.txt', 'Unity/ProjectSettings/ProjectSettings.asset')}
    before_guids = guids(PROJECT)
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith('HOTR_') and key.upper() != 'GRADLE_RO_DEP_CACHE'}
    environment.update(HOTR_LTS116_OUT=str(out), HOTR_LTS116_RECEIPT=str(receipt), HOTR_LTS116_APK=str(apk),
                       GRADLE_USER_HOME=str(gradle_home), HOTR_GRADLE116_OFFLINE='1',
                       SDKMANAGER_OPTS='-Dsun.net.client.defaultConnectTimeout=5000 -Dsun.net.client.defaultReadTimeout=15000')
    log, console = private / 'Unity.log', private / 'Console.log'
    command = [str(EDITOR), '-batchmode', '-projectPath', str(PROJECT), '-buildTarget', 'Android',
               '-executeMethod', 'HeartOfTheRain.Verification.LtsNoSplashBuild116.BuildDevelopment', '-logFile', str(log)]
    record = dict(status='RUNNING_LTS_NOSPLASH116_BUILD', startedUtc=api.utc(), command=command,
                  runnerSHA256=api.sha(Path(__file__)), helperTemplateSHA256=api.sha(Path(__file__).with_name('LtsNoSplashBuild116.cs.template')),
                  editor=bind(EDITOR) if EDITOR.is_relative_to(ROOT) else dict(path=str(EDITOR), sha256=api.sha(EDITOR)),
                  preparation=bind(receipt), candidateBefore=before, candidateGuidBefore=before_guids,
                  canonicalBefore=source_before, mainCriticalSettingsBefore=main_critical,
                  scope='Owned isolated LTS SDK-free Android Development build. No device, main promotion, provider or production operation.')
    runner_copy = out / 'RunnerSourceAtStart116.py'
    shutil.copyfile(Path(__file__), runner_copy)
    record.update(runnerSourceAtStart=bind(runner_copy), gradleHomePreparation=gradle_receipt,
                  processEnvironmentOverrides={key:environment[key] for key in ('GRADLE_USER_HOME', 'HOTR_GRADLE116_OFFLINE', 'SDKMANAGER_OPTS')},
                  foreignGradleInitScriptsUsed=False)
    write(out / 'Authorization.json', record)
    job, process, started = None, None, time.monotonic()
    try:
        job = api.OwnedJob()
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        with console.open('x', encoding='utf-8') as stream:
            process = subprocess.Popen(command, cwd=PROJECT, env=environment, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW | 0x4, startupinfo=startup)
            record['pid'] = process.pid
            job.assign(process.pid)
            resume_owned_primary(process)
            record['ownedJobAssignedBeforeResume'] = True
            print(json.dumps(dict(status='STARTED_LTS_NOSPLASH116_BUILD', tag=tag, pid=process.pid)), flush=True)
            try:
                process.wait(timeout=5400)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True
                job.close()
                process.wait(timeout=30)
        native = json.loads((out / 'Build.json').read_text('utf-8-sig')) if (out / 'Build.json').is_file() else {}
        text = log.read_text('utf-8-sig', errors='replace') if log.exists() else ''
        engine = re.search(r'Initialize engine version:\s*(\S+)', text)
        good = process.returncode == 0 and not record.get('timedOut') and engine and engine[1] == '6000.3.27f1' and native.get('status') == 'PASS_LTS_NOSPLASH116_BUILD' and native.get('actualBuild') is True and native.get('errors') == 0 and all(native.get(key) is False for key in ('showSplashBefore', 'showLogoBefore', 'showSplashAfter', 'showLogoAfter'))
        record.update(status='PASS_LTS_NOSPLASH116_INVOCATION' if good else 'FAIL_LTS_NOSPLASH116_INVOCATION', exitCode=process.returncode,
            actualEngine=engine[1] if engine else None, native=native,
            compilerWarnings=len(re.findall(r'(?m)\bwarning CS\d+:', text)), compilerErrors=len(re.findall(r'(?m)\berror CS\d+:', text)))
    except Exception as error:
        record.update(status='FAIL_LTS_NOSPLASH116_RUNNER', errorType=type(error).__name__)
    finally:
        record['ownedChildClosure'] = shared.owned_shutdown(job)
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=30)
        after = tree(PROJECT)
        after_guids = guids(PROJECT)
        source_after = tree(CANONICAL)
        nonmeta_changes = sorted(name for name, row in before.items() if name.startswith('Assets/') and not name.endswith('.meta') and after.get(name) != row)
        package_changes = sorted(name for name, row in before.items() if name.startswith('Packages/') and after.get(name) != row)
        guid_changes = sorted(name for name, value in before_guids.items() if after_guids.get(name) != value)
        main_after = {name: api.sha(ROOT / name) for name in main_critical}
        record.update(candidateAfter=after, candidateGuidAfter=after_guids, canonicalAfter=source_after,
            mainCriticalSettingsAfter=main_after, mainCriticalSettingsUnchanged=main_after == main_critical,
            originalCandidateAssetsAndSourcePreserved=not nonmeta_changes, originalCandidateGuidsPreserved=not guid_changes,
            candidateAssetSourceChangedPaths=nonmeta_changes, candidateGuidChangedPaths=guid_changes, packageChangedPaths=package_changes,
            candidateMetaBodyChangedPaths=sorted(name for name, row in before.items() if name.endswith('.meta') and after.get(name) != row),
            canonicalChangedPaths=sorted(name for name in source_before.keys() | source_after.keys() if source_before.get(name) != source_after.get(name)),
            elapsedSeconds=round(time.monotonic()-started, 3), finishedUtc=api.utc(),
            rawLogs=[bind(path) for path in (log, console) if path.is_file()])
        if nonmeta_changes or guid_changes or package_changes or main_after != main_critical or not record['ownedChildClosure'].get('allObservedHandlesSignaled'):
            record['status'] = 'FAIL_LTS_NOSPLASH116_SOURCE_OR_OWNERSHIP'
        if apk.is_file():
            record['artifact'] = bind(apk)
        write(out / 'Invocation.json', record)
    print(json.dumps(dict(status=record['status'], report=(out / 'Invocation.json').relative_to(ROOT).as_posix(), artifact=record.get('artifact'))), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


def main():
    global CANONICAL, CANONICAL_PROOF, CANONICAL_SHA, BASE, PROJECT, PUBLIC
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'build'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag')
    parser.add_argument('--gradle-cache-seed', type=Path,
                        help='First build only: explicit compatible public modules-2 cache; copied without locks or foreign init scripts into the owned candidate GradleHome.')
    parser.add_argument('--gradle-home', type=Path,
                        help='First build only: fresh short drive-root HR116G_<tag> directory, owned by this candidate; avoids Windows MAX_PATH without global changes.')
    parser.add_argument('--source-project', type=Path,
                        help='Explicit source for a fresh checkout: Unity is accepted only when all bytes equal the pinned canonical manifest; no automatic main fallback.')
    parser.add_argument('--canonical-manifest', type=Path)
    parser.add_argument('--canonical-sha256')
    candidates = parser.add_mutually_exclusive_group()
    candidates.add_argument('--candidate-root', type=Path)
    candidates.add_argument('--candidate-tag')
    args = parser.parse_args()
    if args.candidate_root is not None or args.candidate_tag is not None:
        if args.candidate_tag is not None:
            need(re.fullmatch(r'[A-Za-z0-9_-]{1,40}', args.candidate_tag), 'SafeFreshCandidateTagRequired')
            selected_base = ROOT / '.verification-cache/Review116' / ('LTSNoSplashCandidate_' + args.candidate_tag)
        else:
            selected_base = args.candidate_root.resolve()
        need(selected_base.parent.resolve() == (ROOT / '.verification-cache/Review116').resolve()
             and re.fullmatch(r'LTSNoSplashCandidate[A-Za-z0-9_-]{1,50}', selected_base.name), 'ContainedOwnedFreshCandidateRootRequired')
        BASE, PROJECT = selected_base, selected_base / 'Game'
        PUBLIC = ROOT / 'Verification/Evidence/Review116/LTSNoSplash/Candidates' / selected_base.name
    need(bool(args.canonical_manifest) == bool(args.canonical_sha256), 'ExplicitManifestAndHashPairRequired')
    if args.operation == 'build':
        need((BASE / 'Preparation.json').is_file(), 'OwnedPreparationMustExistBeforeBuild')
        existing = json.loads((BASE / 'Preparation.json').read_text('utf-8-sig'))
        if args.canonical_manifest is None:
            CANONICAL_PROOF = ROOT / existing['canonicalManifest']['path']
            CANONICAL_SHA = existing['canonicalManifest']['sha256']
        if args.source_project is None and existing.get('canonicalProject'):
            CANONICAL = Path(existing['canonicalProject']).resolve()
    if args.canonical_manifest is not None:
        selected_proof = args.canonical_manifest.resolve()
        need(selected_proof.is_relative_to(ROOT / 'Verification/Evidence/Review116/App')
             and selected_proof.name.startswith('NativeSnapshotSourceCut116')
             and selected_proof.suffix == '.json'
             and re.fullmatch(r'[0-9a-fA-F]{64}', args.canonical_sha256), 'ExplicitOwnedCanonicalManifestRequired')
        CANONICAL_PROOF, CANONICAL_SHA = selected_proof, args.canonical_sha256.lower()
    need(api.sha(CANONICAL_PROOF) == CANONICAL_SHA, 'ExplicitCanonicalManifestHashMismatch')
    if args.source_project is not None:
        selected = args.source_project.resolve()
        need(selected in ((ROOT / 'Unity').resolve(), (ROOT / '.verification-cache/Review116/NativeSnapshot/Game').resolve()),
             'ExplicitCanonicalOrExactCheckoutSourceRequired')
        CANONICAL = selected
    if args.operation == 'build':
        need(existing['canonicalManifest']['sha256'] == CANONICAL_SHA,
             'BuildMustRetainPreparedSourceCut')
    need(args.execute, 'ExplicitOwnedPreparationOrBuildRequired')
    if args.operation == 'prepare':
        prepare()
        return 0
    return build(args.tag, args.gradle_cache_seed, args.gradle_home)


if __name__ == '__main__':
    raise SystemExit(main())
