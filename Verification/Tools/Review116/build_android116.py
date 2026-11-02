"""Build isolated, SDK-free Android candidates without changing the main project.

Uses the pinned Unity Editor and existing build guards. Fresh test package only;
neither APK is a store release. Raw logs and candidate data remain ignored.
"""
import argparse
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
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review93'))
from run_connected import resume_owned_primary

PACKAGE = 'com.heartoftherain.review116'
BASE = ROOT / '.verification-cache/Review116/Android'
PROJECT = BASE / 'Game'
EVIDENCE = ROOT / 'Verification/Evidence/Review116/Android'
EDITOR_SOURCE = r'''#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
namespace HeartOfTheRain.Verification {
 public static class AndroidBuild116 {
  [Serializable] sealed class Report {
   public string status="FAIL_ANDROID116",unity,packageName,apk,mode;
   public int errors,warnings; public long bytes; public bool actualBuild,development;
   public string scope="Isolated SDK-free ARM64 IL2CPP test package; no store signing, installation or provider acceptance.";
  }
  public static void Development()=>Build(true);
  public static void NonDevelopment()=>Build(false);
  static void Build(bool development) {
   string testPackage=Environment.GetEnvironmentVariable("HOTR_REVIEW116_DEVELOPMENT_PACKAGE")??"com.heartoftherain.review116";
   if(testPackage!="com.heartoftherain.review116"&&testPackage!="com.heartoftherain.review116r2")throw new InvalidOperationException("Owned116TestPackageRequired");
   var r=new Report{unity=Application.unityVersion,packageName=development?testPackage:"com.heartoftherain.verification",mode=development?"Development":"NonDevelopment",development=development};
   string output=Environment.GetEnvironmentVariable("HOTR_REVIEW116_ANDROID_OUT");
   if(string.IsNullOrEmpty(output)||Application.unityVersion!="2022.3.62f3")throw new InvalidOperationException("Pinned116EditorAndOutputRequired");
   try {
    if(!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Android,BuildTarget.Android))throw new InvalidOperationException("PinnedAndroidModuleRequired");
    if(PlayerSettings.Android.useCustomKeystore)throw new InvalidOperationException("InternalDebugSignerRequired");
    PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,r.packageName);
    PlayerSettings.companyName="HeartRainReview116"; PlayerSettings.Android.bundleVersionCode=116;
    PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android,ScriptingImplementation.IL2CPP);
    PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
    EditorUserBuildSettings.buildAppBundle=false;
    string tag=Environment.GetEnvironmentVariable("HOTR_REVIEW116_ANDROID_TAG")??"";
    if(tag.Length>0&&!System.Text.RegularExpressions.Regex.IsMatch(tag,"^[A-Za-z0-9_]{1,30}$"))throw new InvalidOperationException("Safe116TagRequired");
    r.apk=Path.GetFullPath("Builds/Review116/HeartOfTheRain_"+r.mode+(tag.Length>0?"_"+tag:"")+".apk");
    if(File.Exists(r.apk))throw new InvalidOperationException("PreservePrevious116Artifact");
    Directory.CreateDirectory(Path.GetDirectoryName(r.apk)); r.actualBuild=true;
    var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions {
     scenes=new[]{HeartOfTheRain.App.Launch.LaunchPage.ScenePath,HeartOfTheRain.App.Launch.LaunchPage.GameScenePath},
     locationPathName=r.apk,target=BuildTarget.Android,options=development?BuildOptions.Development:BuildOptions.None });
    r.errors=(int)result.summary.totalErrors; r.warnings=(int)result.summary.totalWarnings;
    if(result.summary.result==BuildResult.Succeeded&&r.errors==0&&File.Exists(r.apk)) {
     r.bytes=new FileInfo(r.apk).Length; r.status="PASS_ANDROID116_"+r.mode;
    }
   } catch(Exception ex) { Debug.LogError("Review116 build failure: "+ex.GetType().Name); }
   Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Build.json"),JsonUtility.ToJson(r,true));
   EditorApplication.Exit(r.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
  }
 }
}
#endif
'''


def inputs(project):
    return {p.relative_to(project).as_posix(): api.sha(p)
            for part in ('Assets', 'Packages', 'ProjectSettings')
            for p in sorted((project / part).rglob('*')) if p.is_file()}


def prepare():
    if BASE.exists():
        raise RuntimeError('Fresh116CandidateRequired')
    before = api.freeze()
    BASE.mkdir(parents=True)
    for part in ('Assets', 'Packages', 'ProjectSettings'):
        shutil.copytree(ROOT / 'Unity' / part, PROJECT / part)
    copied = inputs(PROJECT)
    expected = {k.removeprefix('Unity/'): v['sha256'] for k, v in before['files'].items()}
    if copied != expected:
        raise RuntimeError('ExactMainCopyRequired')
    folder = PROJECT / 'Assets/Review116Editor'
    folder.mkdir()
    (folder / 'Editor').mkdir()
    for p, is_folder in ((folder, True), (folder / 'Editor', True), (folder / 'Editor/AndroidBuild116.cs', False)):
        if not is_folder:
            p.write_text(EDITOR_SOURCE, encoding='utf-8')
        Path(str(p) + '.meta').write_text('fileFormatVersion: 2\nguid: ' + uuid.uuid4().hex + '\n' +
            ('folderAsset: yes\nDefaultImporter:\n' if is_folder else 'MonoImporter:\n  serializedVersion: 2\n') +
            '  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n', encoding='utf-8')
    after = api.freeze()
    if before != after:
        raise RuntimeError('MainSourceChangedDuringCopy')
    api.write(BASE / 'Preparation.json', dict(status='PREPARED_ISOLATED_ANDROID116',
        mainInputs=before, candidateInputs=inputs(PROJECT), package=PACKAGE,
        editorSHA256=api.sha(api.PINNED_UNITY), runnerSHA256=api.sha(Path(__file__)),
        scope='Byte-identical main inputs plus one private Editor build entry; no engine/SDK change.'))
    print(json.dumps(dict(status='PREPARED_ISOLATED_ANDROID116', inputCount=len(copied))), flush=True)


def source_manifest(project):
    return dict(schemaVersion=1, inputCount=len(values := inputs(project)),
                files={'Unity/' + k: dict(sha256=v, bytes=(project / k).stat().st_size)
                       for k, v in values.items()})


def canonical_project(value):
    expected = ROOT / '.verification-cache/Review116/NativeSnapshot/Game'
    if value is None:
        return None
    if Path(value).resolve() != expected.resolve():
        raise RuntimeError('ExactOwnedCanonical116SnapshotRequired')
    proof = ROOT / 'Verification/Evidence/Review116/App/NativeSnapshotPreparation116.json'
    if json.loads(proof.read_text('utf-8'))['status'] != 'PREPARED_IMMUTABLE_NATIVE_SNAPSHOT116':
        raise RuntimeError('Canonical116PreparationRequired')
    return expected


def refresh(source_project=None):
    sys.path.insert(0, str(ROOT / 'Verification/Tools/PageBackdrop90'))
    from process90 import unity_pids, process_details
    for pid in unity_pids():
        _, args = process_details(pid, include_command=True)
        if '-projectPath' in args and Path(args[args.index('-projectPath') + 1]).resolve() == PROJECT.resolve():
            raise RuntimeError('PreserveActive116CandidateEditor')
    original = json.loads((BASE / 'Preparation.json').read_text('utf-8'))['mainInputs']
    source = canonical_project(source_project) or ROOT / 'Unity'
    current = source_manifest(source)
    changes = api.delta(original, current)
    if changes['removed']:
        raise RuntimeError('ReviewRemovedMainInputsBeforeRefresh')
    for relative in changes['changed'] + changes['added']:
        source_file, destination = source / relative.removeprefix('Unity/'), PROJECT / relative.removeprefix('Unity/')
        if not destination.resolve().is_relative_to(PROJECT.resolve()):
            raise RuntimeError('Contained116RefreshRequired')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, destination)
    (PROJECT / 'Assets/Review116Editor/Editor/AndroidBuild116.cs').write_text(EDITOR_SOURCE, encoding='utf-8')
    after = source_manifest(source)
    if current != after:
        raise RuntimeError('MainSourceChangedDuring116Refresh')
    receipt = BASE / ('Refresh_' + uuid.uuid4().hex[:10] + '.json')
    api.write(receipt, dict(status='REFRESHED_ISOLATED_ANDROID116', mainInputs=current,
        changesFromInitialPreparation=changes, candidateInputs=inputs(PROJECT),
        sourceProject=str(source), runnerSHA256=api.sha(Path(__file__)), utc=api.utc()))
    print(json.dumps(dict(status='REFRESHED_ISOLATED_ANDROID116', changed=changes['changed'],
                         added=changes['added'], receipt=str(receipt))), flush=True)


def run(mode, tag=None, source_project=None, development_package=PACKAGE):
    if not (BASE / 'Preparation.json').is_file():
        raise RuntimeError('Owned116PreparationRequired')
    if tag and not re.fullmatch('[A-Za-z0-9_]{1,30}', tag):
        raise RuntimeError('SafeFresh116BuildTagRequired')
    out = EVIDENCE / (tag or mode)
    private = BASE / 'Logs' / (tag or mode)
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    before = inputs(PROJECT)
    main_before = api.freeze()
    canonical = canonical_project(source_project)
    canonical_before = source_manifest(canonical) if canonical else None
    source_match = all(before.get(k.removeprefix('Unity/')) == v['sha256']
                       for k, v in canonical_before['files'].items()) if canonical_before else None
    if canonical and not source_match:
        raise RuntimeError('RefreshCandidateFromCanonicalSnapshotBeforeBuild')
    settings = {p: p.read_bytes() for p in (PROJECT / 'ProjectSettings').glob('*') if p.is_file()}
    log, console = private / 'Unity.log', private / 'Console.log'
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith('HOTR_') or key in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS'):
            env.pop(key)
    env['HOTR_REVIEW116_ANDROID_OUT'] = str(out)
    if development_package not in (PACKAGE, 'com.heartoftherain.review116r2'):
        raise RuntimeError('Owned116DevelopmentPackageRequired')
    env['HOTR_REVIEW116_DEVELOPMENT_PACKAGE'] = development_package
    if tag:
        env['HOTR_REVIEW116_ANDROID_TAG'] = tag
    command = [str(api.PINNED_UNITY), '-batchmode', '-projectPath', str(PROJECT),
        '-buildTarget', 'Android', '-executeMethod', 'HeartOfTheRain.Verification.AndroidBuild116.' + mode,
        '-logFile', str(log)]
    state = dict(status='RUNNING_ANDROID116', startedUtc=api.utc(), mode=mode,
        mainBefore=main_before, candidateBefore=before, canonicalSourceProject=str(canonical) if canonical else None,
        canonicalSourceBefore=canonical_before, candidateMatchesCanonicalBefore=source_match,
        runnerSHA256=api.sha(Path(__file__)))
    api.write(out / 'Started.json', state)
    started = time.monotonic()
    job = api.OwnedJob()
    process = None
    try:
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        with console.open('x', encoding='utf-8') as stream:
            process = subprocess.Popen(command, cwd=PROJECT, env=env, stdout=stream,
                stderr=subprocess.STDOUT, startupinfo=startup,
                creationflags=subprocess.CREATE_NO_WINDOW | 0x4)
            job.assign(process.pid)
            resume_owned_primary(process)
            print(json.dumps(dict(status='STARTED_ANDROID116', mode=mode, pid=process.pid)), flush=True)
            process.wait(timeout=3600)
        native = json.loads((out / 'Build.json').read_text('utf-8-sig')) if (out / 'Build.json').exists() else {}
        text = log.read_text('utf-8-sig', errors='replace') if log.exists() else ''
        state.update(exitCode=process.returncode, native=native,
            csharpErrors=len(re.findall(r'\berror CS\d+', text)),
            csharpWarnings=len(re.findall(r'\bwarning CS\d+', text)))
        state['status'] = 'PASS_ANDROID116_INVOCATION' if (process.returncode == 0 and
            native.get('status') == 'PASS_ANDROID116_' + mode and native.get('errors') == 0 and
            native.get('actualBuild') and '2022.3.62f3' in text) else 'FAIL_ANDROID116_INVOCATION'
        if native.get('apk') and Path(native['apk']).is_file():
            state['apkSHA256'] = api.sha(Path(native['apk']))
    except Exception as error:
        state.update(status='FAIL_ANDROID116_RUNNER', errorType=type(error).__name__)
    finally:
        job.close()
        if process and process.poll() is None:
            process.wait(timeout=30)
        for p, data in settings.items():
            if p.read_bytes() != data:
                p.write_bytes(data)
        after = inputs(PROJECT)
        main_after = api.freeze()
        canonical_after = source_manifest(canonical) if canonical else None
        state.update(candidateAfter=after, mainAfter=main_after,
            mainInputsUnchanged=main_before == main_after,
            canonicalSourceAfter=canonical_after,
            canonicalInputsUnchanged=canonical_before == canonical_after if canonical else None,
            existingCandidateInputsPreserved=all(after.get(k) == v for k, v in before.items()),
            addedCandidateInputs=sorted(after.keys() - before.keys()),
            elapsedSeconds=round(time.monotonic() - started, 3), finishedUtc=api.utc(),
            rawLogs=[dict(path=p.relative_to(ROOT).as_posix(), sha256=api.sha(p), bytes=p.stat().st_size)
                     for p in (log, console) if p.is_file()])
        accepted_cut_unchanged = state['canonicalInputsUnchanged'] if canonical else state['mainInputsUnchanged']
        if not state['existingCandidateInputsPreserved'] or not accepted_cut_unchanged:
            state['status'] = 'FAIL_ANDROID116_SOURCE_DRIFT'
        api.write(out / 'Invocation.json', state)
    print(json.dumps(dict(status=state['status'], mode=mode, report=str(out / 'Invocation.json'))), flush=True)
    return 0 if state['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'refresh', 'Development', 'NonDevelopment'))
    parser.add_argument('--tag')
    parser.add_argument('--source-project', type=Path)
    parser.add_argument('--development-package', choices=(PACKAGE, 'com.heartoftherain.review116r2'), default=PACKAGE)
    args = parser.parse_args()
    if args.operation == 'prepare':
        prepare()
    elif args.operation == 'refresh':
        refresh(args.source_project)
    else:
        raise SystemExit(run(args.operation, args.tag, args.source_project, args.development_package))
