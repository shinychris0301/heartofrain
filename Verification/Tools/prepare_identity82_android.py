"""Prepare, never run, an isolated pinned-Unity Android identity fixture.

Exact main-project identity sources/metas plus two SDK-independent transport
dependencies are copied. Generated bootstrap/build scripts exist ONLY under
the ignored fixture directory and cannot auto-start the ordinary game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / '.verification-cache/Launch82/AndroidIdentityProject'

BOOTSTRAP = r'''using System;
using System.Collections;
using System.IO;
using UnityEngine;
using HeartOfTheRain.Verification;

public sealed class Identity82FixtureBootstrap : MonoBehaviour {
    [Serializable] sealed class Envelope { public string status, scopeHash, stage, reportPath; public int pid; }
    IEnumerator Start() {
        string scope = null, stage = null;
#if UNITY_ANDROID && !UNITY_EDITOR
        try {
            using(var player = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
            using(var activity = player.GetStatic<AndroidJavaObject>("currentActivity"))
            using(var intent = activity.Call<AndroidJavaObject>("getIntent")) {
                scope = intent.Call<string>("getStringExtra", "identity82_scope");
                stage = intent.Call<string>("getStringExtra", "identity82_stage");
            }
        } catch(Exception) { Debug.LogError("Explicit identity82 fixture arguments unavailable"); yield break; }
#endif
        if(scope == null || stage == null) { Debug.LogError("Explicit identity82 fixture arguments required"); yield break; }
        string directory = Path.Combine(Application.persistentDataPath, "Identity82", "Reports");
        yield return Identity82DeviceProbe.RunStage(scope, stage, directory, report => {
            int pid = 0;
#if UNITY_ANDROID && !UNITY_EDITOR
            using(var process = new AndroidJavaClass("android.os.Process")) pid = process.CallStatic<int>("myPid");
#endif
            var envelope = new Envelope { status = report.status, scopeHash = report.scopeHash, stage = stage, pid = pid,
                reportPath = "Identity82/Reports/Identity82_" + stage + ".json" };
            File.WriteAllText(Path.Combine(directory, "Fixture_" + stage + ".json"), JsonUtility.ToJson(envelope, true));
            Debug.Log("IDENTITY82_EXPLICIT_STAGE_COMPLETE");
        });
    }
}
'''

BUILD = r'''#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class Identity82FixtureBuild {
    [Serializable] sealed class Result { public string status, unity, package, result; public int errors, warnings; public bool development, arm64; }
    public static void Build() {
        string folder = Path.GetFullPath("Build"); Directory.CreateDirectory(folder);
        var output = new Result { unity = Application.unityVersion, package = "com.heartoftherain.identity82fixture", development = true, arm64 = true };
        try {
            if(Application.unityVersion != "2022.3.62f3") throw new InvalidOperationException("Pinned Unity required");
            EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android);
            PlayerSettings.companyName = "HeartOfTheRainVerification"; PlayerSettings.productName = "Identity82QA";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, output.package);
            PlayerSettings.bundleVersion = "82.0"; PlayerSettings.Android.bundleVersionCode = 82;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
            PlayerSettings.Android.targetSdkVersion = (AndroidSdkVersions)35;
            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.useCustomKeystore = false;
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.Portrait;
            PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Android, ManagedStrippingLevel.Low);
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            new GameObject("ExplicitIdentity82Fixture").AddComponent<Identity82FixtureBootstrap>();
            string scenePath = "Assets/Fixture.unity"; EditorSceneManager.SaveScene(scene, scenePath);
            var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { scenePath }, target = BuildTarget.Android,
                locationPathName = Path.Combine(folder, "Identity82.apk"), options = BuildOptions.Development });
            output.result = build.summary.result.ToString(); output.errors = (int)build.summary.totalErrors; output.warnings = (int)build.summary.totalWarnings;
            output.status = build.summary.result == BuildResult.Succeeded ? "PASS_ISOLATED_IDENTITY82_ANDROID_ASSEMBLY" : "FAIL_ISOLATED_IDENTITY82_ANDROID_ASSEMBLY";
        } catch(Exception error) { output.status = "FAIL_ISOLATED_IDENTITY82_ANDROID_ASSEMBLY"; output.result = error.GetType().Name; }
        File.WriteAllText(Path.Combine(folder, "Build.json"), JsonUtility.ToJson(output, true));
        if(Application.isBatchMode) EditorApplication.Exit(output.status.StartsWith("PASS_") ? 0 : 1);
    }
}
#endif
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(out: Path = DEFAULT) -> dict:
    out = out.resolve()
    allowed = (ROOT / '.verification-cache/Launch82').resolve()
    if not out.is_relative_to(allowed) or out == allowed:
        raise ValueError('Fixture must remain in ignored Launch82 cache')
    original = ROOT / 'Unity/Assets/HeartOfTheRain'
    source = original / 'App/OnlineIdentity'
    if not source.is_dir():
        raise FileNotFoundError('Held identity source tree missing')
    destination = out / 'Assets/HeartOfTheRain/App/OnlineIdentity'
    copied: dict[str, str] = {}

    # Unity's generated Gradle module uses src/main/java. Earlier fixture
    # attempts copied src/com without compiling it. Remove ONLY those exact
    # now-obsolete copied files, after checking both cache containment and
    # byte identity against the corresponding held source at its new path.
    old_java_root = destination / 'Plugins/Android/HeartOfTheRainIdentity82.androidlib/src/com'
    fresh_java_root = source / 'Plugins/Android/HeartOfTheRainIdentity82.androidlib/src/main/java/com'
    obsolete = [Path(str(old_java_root) + '.meta')]
    if old_java_root.exists():
        obsolete.extend(sorted(p for p in old_java_root.rglob('*') if p.is_file()))
    for old in obsolete:
        if not old.exists():
            continue
        assert old.resolve().is_relative_to(out), 'Obsolete copy must stay inside the fixture'
        suffix = Path(str(old)[len(str(old_java_root)):].lstrip('/\\'))
        corresponding = Path(str(fresh_java_root) + '.meta') if old.name == 'com.meta' and old.parent == old_java_root.parent else fresh_java_root / suffix
        assert corresponding.is_file() and sha(old) == sha(corresponding), 'Refuse to remove an altered obsolete source copy'
        old.unlink()
    if old_java_root.exists():
        for directory in sorted((p for p in old_java_root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            directory.rmdir()  # Fail rather than recursively deleting unknown files.
        old_java_root.rmdir()

    def copy(src: Path, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        if sha(src) != sha(dest):
            raise ValueError('Fixture copy digest mismatch')
        copied[src.relative_to(ROOT).as_posix()] = sha(src)

    for src in [source.with_suffix('.meta'), *sorted(p for p in source.rglob('*') if p.is_file())]:
        dest = destination.with_suffix('.meta') if src == source.with_suffix('.meta') else destination / src.relative_to(source)
        copy(src, dest)
    # These exact SDK-independent source files supply strict origin validation
    # for the copied identity HTTP transport; no Pay SDK adapter/bootstrap.
    for relative in ('App/RuStore/Runtime/RuStoreBackendClient.cs', 'App/RuStore/Runtime/PayStoreContracts.cs', 'Verification/Identity82DeviceProbe.cs'):
        src = original / relative
        for item in (src, src.with_suffix(src.suffix + '.meta')):
            copy(item, out / 'Assets/HeartOfTheRain' / item.relative_to(original))

    generated: dict[str, str] = {}

    def write(relative: str, text: str):
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8', newline='\n')
        generated[relative] = sha(path)

    write('ProjectSettings/ProjectVersion.txt', 'm_EditorVersion: 2022.3.62f3\nm_EditorVersionWithRevision: 2022.3.62f3 (96770f904ca7)\n')
    write('Packages/manifest.json', json.dumps({'dependencies': {
        'com.unity.modules.androidjni': '1.0.0', 'com.unity.modules.jsonserialize': '1.0.0',
        'com.unity.modules.unitywebrequest': '1.0.0',
    }}, indent=2) + '\n')
    write('Assets/Identity82FixtureBootstrap.cs', BOOTSTRAP)
    write('Assets/Editor/Identity82FixtureBuild.cs', BUILD)
    # Generated C# metas are fixture-only; stable once first prepared.
    for relative in ('Assets/Identity82FixtureBootstrap.cs', 'Assets/Editor/Identity82FixtureBuild.cs'):
        meta = out / (relative + '.meta')
        if not meta.exists():
            write(relative + '.meta', 'fileFormatVersion: 2\nguid: ' + uuid.uuid4().hex + '\n')
    result = {
        'status': 'PREPARED_ISOLATED_IDENTITY82_ANDROID_PROJECT_NOT_BUILT',
        'unity': '2022.3.62f3', 'package': 'com.heartoftherain.identity82fixture',
        'entrypoint': 'Identity82FixtureBuild.Build', 'project': out.relative_to(ROOT).as_posix(),
        'copiedSourceSHA256': copied, 'generatedSHA256': generated,
        'scope': 'Preparation only, no Unity/build/install/device execution. Exact held identity sources and two SDK-independent dependencies, no ordinary save/bootstrap, provider SDK, backend login or payment.',
        'intentExtras': {'identity82_scope': 'qa82-<32 lowercase hex>', 'identity82_stage': 'setup|reopen|clear'},
        'output': 'files/Identity82/Reports/Identity82_<stage>.json plus Fixture_<stage>.json with actual process ID',
        'limitations': ['Actual root-controlled build must verify .androidlib JNI import.', 'A distinct-process reopen is required before claiming process persistence.', 'No OS power-loss, hardware attestation or physical-device claim.'],
    }
    write('Preparation.json', json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT)
    args = parser.parse_args()
    result = prepare(args.out)
    print(json.dumps({'status': result['status'], 'copied': len(result['copiedSourceSHA256']), 'project': result['project']}))


if __name__ == '__main__':
    main()
