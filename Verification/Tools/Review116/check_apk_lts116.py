"""Static audit and reusable launch-policy check of the actual approved LTS APK."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import zipfile

import check_apk116 as common
import launch_profile116 as launch

ROOT = common.ROOT
ANDROID = Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
CANONICAL_SHA = 'b0bc2b91f3a22b9b8bcc6ab230ffa28a7a8f9a8f4972038fd9eeb3c66dfbe28d'
STARTUP_JAVA_SHA = '1de78774460c27255e52ce87efd24d05c8398ad6d23353564d9d2ff9131c8222'
PACKAGE = 'com.heartoftherain.review116lts'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    common.need(build.is_relative_to(ROOT / 'Verification/Evidence/Review116/LTSNoSplash')
        and out.is_relative_to(ROOT / 'Verification/Evidence/Review116/LTSNoSplash') and not out.exists(),
        'FreshOwnedLtsStaticEvidenceRequired')
    eligibility = launch.qualify(build)
    common.need(eligibility['ordinaryUserVisibleLaunchAllowed'] is True and eligibility['diagnosticOnly'] is False,
        'ApprovedActualLtsLaunchEligibilityRequired')
    native = common.read(build)
    invocation = common.read(build.with_name('Invocation.json'))
    prep = common.read(ROOT / invocation['preparation']['path'])
    canonical_path = ROOT / prep['canonicalManifest']['path']
    common.need(common.sha(canonical_path) == CANONICAL_SHA == prep['canonicalManifest']['sha256'],
        'ExactApprovedHarness05CanonicalCutRequired')
    canonical = common.read(canonical_path)['files']
    expected = {name.removeprefix('Unity/'): row for name, row in canonical.items()}
    common.need(prep['canonicalInputs'] == expected, 'LtsCanonicalInputMapMismatch')
    runtime_art = {name: row for name, row in expected.items()
        if name.startswith('Assets/') and not name.endswith('.meta')}
    common.need(all(prep['copiedInputs'].get(name) == row for name, row in runtime_art.items()),
        'ExactCanonicalRuntimeSourceAndArtworkRequired')
    java = [row['sha256'] for name, row in prep['copiedInputs'].items() if name.endswith('/LaunchCurtain99.java')]
    common.need(java == [STARTUP_JAVA_SHA], 'ApprovedStartupJavaRequired')
    apk = ROOT / eligibility['apk']['path']
    raw = ROOT / '.verification-cache/Review116/LTSStatic' / out.name
    common.need(not raw.exists(), 'PreservePreviousLtsStaticOutput')
    raw.mkdir(parents=True)
    out.mkdir(parents=True)
    result = dict(status='FAIL_STATIC_APK116_LTS', package=PACKAGE, unity='6000.3.27f1', development=True,
        showSplashScreen=False, showUnityLogo=False, apk=common.bind(apk),
        nativeBuild=common.bind(build), invocation=common.bind(build.with_name('Invocation.json')),
        preparation=invocation['preparation'], launchEligibility=eligibility,
        launchValidator=common.bind(Path(launch.__file__)), runner=common.bind(Path(__file__)),
        canonicalSnapshot=dict(manifest=common.bind(canonical_path), runtimeAndArtFiles=len(runtime_art),
            runtimeAndArtByteEquality=True, approvedProfileSettingsAndSameGuidMetas=True,
            mainEnginePromoted=False), startupJavaSha256=STARTUP_JAVA_SHA,
        checks={}, errors=[], scope='Actual approved isolated6000.3 LTS no-splash-configured internal APK. Static source/profile/signature/manifest/DEX/CRC/alignment checks only; actual cold video/frame review, runtime regression and ordinary Home remain separate.')
    spec = importlib.util.spec_from_file_location('review116_lts_apk_primitive',
        ROOT / 'Verification/Tools/Unity6Migration94/check_apk94.py')
    primitive = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(primitive)
    tools = ANDROID / 'SDK/build-tools/36.0.0'

    def command(name, args):
        with (raw / (name + '.out')).open('xb') as stdout, (raw / (name + '.err')).open('xb') as stderr:
            run = subprocess.run([str(x) for x in args], stdout=stdout, stderr=stderr,
                timeout=240, creationflags=subprocess.CREATE_NO_WINDOW)
        common.need(run.returncode == 0, 'LtsStaticToolFailed' + name)
        return (raw / (name + '.out')).read_text('utf-8', errors='strict')

    try:
        signature = command('Signature', [ANDROID / 'OpenJDK/bin/java.exe', '-jar',
            tools / 'lib/apksigner.jar', 'verify', '--verbose', '--print-certs', apk])
        cert = re.search(r'(?m)^Signer #1 certificate SHA-256 digest: ([a-fA-F0-9]{64})\s*$', signature)
        common.need(cert is not None and 'CN=Android Debug' in signature, 'LtsInternalDebugSignatureRequired')
        result['publicCertificateSha256'] = cert[1].lower()
        result['checks']['actualInternalSignatureVerifies'] = True
        command('Zipalign', [tools / 'zipalign.exe', '-c', '-v', '4', apk])
        result['checks']['actualZipalignFourByte'] = True
        badging = command('Badging', [tools / 'aapt.exe', 'dump', 'badging', apk])
        manifest = command('Manifest', [tools / 'aapt.exe', 'dump', 'xmltree', apk, 'AndroidManifest.xml'])
        result['manifest'] = primitive.manifest_profile(badging, manifest, PACKAGE, True)
        common.need(result['manifest']['targetApi'] == 36, 'ApprovedLtsTargetApi36Required')
        result['checks'].update(packageLabelApiPortraitDevelopment=True, sdkFreeManifest=True)
        nodes = primitive.parse_manifest(manifest)
        curtain = [node for node in nodes if node['tag'] == 'provider' and
            primitive.attribute_value(node['attributes'].get('android:name')) == 'com.heartoftherain.launch99.LaunchCurtain99']
        common.need(len(curtain) == 1 and primitive.attribute_value(curtain[0]['attributes'].get('android:authorities')) == PACKAGE + '.launch99'
            and primitive.attribute_value(curtain[0]['attributes'].get('android:exported')) == 0,
            'SamePackageNonExportedApprovedCurtainRequired')
        result['checks']['nonExportedSamePackageStartupProvider'] = True
        result['zip'] = primitive.zip_profile(apk)
        result['checks'].update(zipCrcNoDuplicates=True, arm64ElfAnd16KiBOffsets=True,
            sdkFreeDex=True, nativeIdentityBridgeInDex=True)
        with zipfile.ZipFile(apk) as archive:
            metadata = [name for name in archive.namelist() if name.endswith('/Metadata/global-metadata.dat')]
            common.need(len(metadata) == 1 and b'PlayerRegressionSuite\0' in archive.read(metadata[0]),
                'ActualLtsDevelopmentRegressionMetadataRequired')
        result['checks']['actualDevelopmentRegressionPresent'] = True
        common.need(common.sha(apk) == result['apk']['sha256'], 'LtsApkChangedDuringChecks')
        result['checks'].update(exactCanonicalRuntimeAndArt=True, approvedDurableLtsProfileAndActualSplashGetters=True,
            exactApprovedStartupJava=True, artifactUnchanged=True)
        result['status'] = 'PASS_STATIC_APK116_LTS'
    except Exception as error:
        message = str(error)
        result['errors'].append(dict(type=type(error).__name__,
            code=message if re.fullmatch('[A-Za-z0-9]{1,100}', message) else 'PrivateLtsStaticOutputRequired'))
    (out / 'StaticApkLts116.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], checks=len(result['checks']),
        report=(out / 'StaticApkLts116.json').relative_to(ROOT).as_posix())), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
