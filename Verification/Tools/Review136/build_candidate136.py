"""Build the review 136 device candidate on the explicit first-moderation profile, versionCode 131.

Same procedure and guards as Review130/build_first_moderation130.py; only the project home, the
pinned version and the artifact name differ. This never changes a release guard. A failed guard is a
failed build. Private signing material is read from the developer's existing Windows custody only.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HOME = Path(r"E:\.verification-cache\HOTR136\Candidate01")
PROJECT = HOME / "Game"
EDITOR = Path(r"E:\HeartRainUnity6LTS95\6000.3.27f1\Editor\Unity.exe")
ANDROID = EDITOR.parent / "Data/PlaybackEngines/AndroidPlayer"
CUSTODY = Path(os.environ["LOCALAPPDATA"]) / "HeartOfTheRain/ReleaseSigning/RuStore"
GRADLE = Path(r"E:\G129R")
SIGNER = "7257537a5b329cc5b018d93299d748404432c1b49f1b2388444ab843a4ba170d"
OUT = ROOT / ".verification-cache/Review136/CandidateBuild01"
RAW = HOME / "Raw"
APK = PROJECT / "Builds/HeartOfTheRain_Candidate136.apk"
VERSION_CODE = 131
VERSION = "0.9.131"


def require(value: bool, code: str) -> None:
    if not value:
        raise RuntimeError(code)


def signing_module():
    spec = importlib.util.spec_from_file_location("hotr_signing136", ROOT / "Release/Signing/manage_release_signing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan_project() -> None:
    require(PROJECT.is_dir() and EDITOR.is_file(), "PinnedIsolatedUnity6ProjectRequired")
    rsp = (PROJECT / "Assets/csc.rsp").read_text("utf-8")
    for symbol in ("HOTR_FIRST_MODERATION130", "HOTR_RUSTORE_PAY", "HOTR_RUSTORE_SDK_ONLY125", "HOTR_YANDEX_ADS"):
        require(symbol in rsp, "ExplicitModerationFeatureMissing_" + symbol)
    for symbol in ("HOTR_RUSTORE_REVIEW129", "HOTR_DIAGNOSTICS127", "HOTR_INTERSTITIAL_DEMO129", "HOTR_PRODUCTION122"):
        require(symbol not in rsp, "UnsafeModerationFeature_" + symbol)
    android_defines = next((line for line in (PROJECT / "ProjectSettings/ProjectSettings.asset").read_text("utf-8-sig").splitlines()
                            if line.lstrip().startswith("Android: HOTR_")), "")
    require("HOTR_FIRST_MODERATION130" in android_defines, "AndroidScriptingDefineMissing")
    for symbol in ("HOTR_RUSTORE_REVIEW129", "HOTR_DIAGNOSTICS127", "HOTR_INTERSTITIAL_DEMO129", "HOTR_PRODUCTION122"):
        require(symbol not in android_defines, "UnsafeAndroidScriptingDefine_" + symbol)
    require(not (PROJECT / "Assets/Review127Diagnostics").exists(), "DiagnosticsAssetsPresent")
    require("android.permission.INTERNET" not in (PROJECT / "Assets/Plugins/Android/AndroidManifest.xml").read_text("utf-8-sig"),
            "DuplicateManualInternetPermission")
    require(not APK.exists(), "FreshApkRequired")
    require(not (PROJECT / "Library/Bee").exists(), "GeneratedGradleCredentialsRequireFreshClone")
    release = json.loads((HOME / "Release136.json").read_text("utf-8-sig"))
    require(release.get("versionCode") == VERSION_CODE and release.get("environment") == "sandbox", "PinnedCandidateMetadataRequired")
    ads = json.loads((PROJECT / "Assets/HeartOfTheRain/Resources/HOTR_Advertising/Configuration.json").read_text("utf-8-sig"))
    require(ads.get("privacyVersion") == "2026-11-01" and ads.get("enabled") is True, "ApprovedAdvertisingMetadataRequired")
    for path in ("Assets/HeartOfTheRain/App/RuStore/Editor/RuStoreReleasePreflight.cs",
                 "Assets/HeartOfTheRain/App/Advertising/Editor/AdvertisingBuild107.cs",
                 "Assets/HeartOfTheRain/App/ServerGameplay/Editor/ProductionBuildConfiguration122.cs",
                 "Assets/HeartOfTheRain/App/ServerGameplay/Editor/StagingServerBuild104.cs"):
        require("HOTR_RUSTORE_REVIEW129" not in (PROJECT / path).read_text("utf-8-sig"), "LegacyGuardExemptionPresent")


def scrub(password: str) -> int:
    marker = password.encode("ascii")
    count = 0
    for base in (PROJECT / "Library", PROJECT / "Temp", PROJECT / "ProjectSettings", GRADLE, RAW):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".gradle", ".properties", ".json", ".txt", ".log", ".yaml", ".yml", ".xml", ".bat", ".cmd", ".rsp", ".cs", ".java", ".kt", ".asset"}:
                data = path.read_bytes()
                if marker in data:
                    path.write_bytes(data.replace(marker, b"<private-signing-password-removed>"))
                    count += 1
    return count


def main() -> None:
    scan_project()
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    signing = signing_module()
    password = signing.local_password(CUSTODY)
    require(signing.verify(CUSTODY, ANDROID / "OpenJDK", password)["sha256"] == SIGNER, "ReleaseSignerMismatch")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("HOTR_") and not re.search(r"KEYSTORE|KEYALIAS|STOREPASS|KEYPASS", k, re.I)}
    env.update(GRADLE_USER_HOME=str(GRADLE), HOTR_BUILD_CHANNEL="first_moderation", HOTR_REVIEW130_OUT=str(OUT),
               HOTR_REVIEW130_APK=str(APK), HOTR_REVIEW130_VERSION=VERSION,
               HOTR_RUSTORE_RELEASE_CONFIG=str(HOME / "Release136.json"),
               HOTR_RELEASE_SIGNING_PASSWORD=password, HOTR_RELEASE_KEYSTORE=str(CUSTODY / signing.KEYSTORE))
    started = time.time()
    code = None
    try:
        process = subprocess.run([str(EDITOR), "-batchmode", "-nographics", "-projectPath", str(PROJECT),
                                  "-buildTarget", "Android", "-executeMethod",
                                  "HeartOfTheRain.App.RuStore.Editor.FirstModerationBuild130.Run",
                                  "-logFile", str(RAW / "Unity.log")], cwd=PROJECT, env=env,
                                 stdin=subprocess.DEVNULL, timeout=5400, creationflags=subprocess.CREATE_NO_WINDOW)
        code = process.returncode
    finally:
        env.pop("HOTR_RELEASE_SIGNING_PASSWORD", None)
        scrubbed = scrub(password)
        del password
    receipt = OUT / "Native.json"
    summary = json.loads(receipt.read_text("utf-8")) if receipt.is_file() else {"status": "NO_NATIVE_RECEIPT"}
    print(json.dumps({"unityExit": code, "seconds": round(time.time() - started), "secretFilesScrubbed": scrubbed,
                      "status": summary.get("status"), "error": summary.get("error"),
                      "errors": summary.get("errors"), "warnings": summary.get("warnings"),
                      "apkSha256": summary.get("apkSha256")}, separators=(",", ":")), flush=True)
    require(code == 0 and summary.get("status") == "PASS_FIRST_MODERATION130", "CandidateBuildDidNotPass")


if __name__ == "__main__":
    main()
