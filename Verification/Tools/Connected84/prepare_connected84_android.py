"""Prepare only an isolated Android project from sealed VerifiedApp inputs.

No Unity/Gradle/ADB execution. Source Assets retain their exact approved bytes
and metadata; only copied project settings and three fixture-only C# sources
are derived. Existing output projects are preserved and never recursively
deleted. Recovery credentials are produced at runtime only inside Android's
protected store, never here or in generated configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path

def logical(path: Path) -> Path:
    """Keep manifests/containment checks free of Windows device-path syntax."""
    value = os.fspath(path)
    if os.name == 'nt':
        if value.startswith('\\\\?\\UNC\\'):
            value = '\\\\' + value[8:]
        elif value.startswith('\\\\?\\'):
            value = value[4:]
    return Path(value).resolve()


def fs(path: Path) -> Path:
    """Filesystem operations ONLY: permit approved archive paths over MAX_PATH."""
    if os.name != 'nt':
        return path
    value = os.fspath(path.absolute())
    if value.startswith('\\\\?\\'):
        return Path(value)
    return Path('\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value)


ROOT = logical(Path(__file__)).parents[3]
HERE = logical(Path(__file__)).parent
DEFAULT_BASELINE = ROOT / 'Verification/Evidence/ServerGameplay83/VerifiedAppWithJNI/Sources.json'
DEFAULT = ROOT / '.verification-cache/Connected84/AndroidProject'
PACKAGE = 'com.heartoftherain.connected84fixture'
NAMESPACE = uuid.UUID('29c9d65e-0193-4e32-8b37-6cf5c0b682c0')
GENERATED = {
    'Connected84FixtureBootstrap.cs': 'Assets/Connected84Fixture/Connected84FixtureBootstrap.cs',
    'Connected84FixtureAccess.cs': 'Assets/Connected84Fixture/Connected84FixtureAccess.cs',
    'Connected84FixtureBuild.cs': 'Assets/Connected84Fixture/Editor/Connected84FixtureBuild.cs',
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with fs(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def source_file(relative: str, expected: str, baseline: Path) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts or rel.parts[0] != 'Unity':
        raise ValueError('Frozen input path must be relative to Unity')
    package_fallback = ROOT / 'Verification/Evidence/ServerGameplay83/Attempts/006_android_jni_module/Inputs' / rel
    candidates = [baseline.parent / 'Inputs' / rel, ROOT / rel]
    if relative.startswith('Unity/Packages/'):
        candidates.append(package_fallback)
    if relative.startswith('Unity/ProjectSettings/'):
        # Root's serialized build temporarily derives these settings, then
        # restores the approved original. Resolve ONLY that exact sealed hash
        # from its explicit pre-build backups while a build is in progress.
        backups = ROOT / '.verification-cache/ServerGameplay83/RunnerBackups'
        for stage in ('AndroidReleaseBuild', 'AndroidBuild'):
            candidates.extend(logical(path) for path in sorted(fs(backups).glob(f'*/{stage}/ApprovedPreBuildSettings/{relative}')))
    for source in candidates:
        if fs(source).is_file() and not fs(source).is_symlink() and sha(source) == expected:
            return source
    raise ValueError(f'Frozen input unavailable or changed: {relative}')


def describe(source_freeze: Path = DEFAULT_BASELINE) -> dict:
    source_freeze = logical(source_freeze)
    if not source_freeze.is_relative_to(logical(ROOT / 'Verification/Evidence/ServerGameplay83')):
        raise ValueError('Explicit source freeze must remain within ServerGameplay83 evidence')
    baseline = json.loads(fs(source_freeze).read_text(encoding='utf-8'))
    if len(baseline['files']) != 5321:
        raise ValueError('Expected the explicitly sealed 5321-input VerifiedApp')
    return {
        'status': 'DRAFT_ISOLATED_CONNECTED84_ANDROID_PREPARATION_NOT_EXECUTED',
        'baselineManifest': source_freeze.relative_to(ROOT).as_posix(),
        'baselineManifestSHA256': sha(source_freeze), 'baselineInputs': 5321,
        'package': PACKAGE, 'unity': '2022.3.62f3',
        'entrypoint': 'Connected84FixtureBuild.Build',
        'preparerSHA256': sha(logical(Path(__file__))),
        'permittedPackageDerivation': {'com.unity.modules.androidjni': {'version': '1.0.0', 'source': 'builtin', 'reason': 'Existing Android JNI source requires the module in Android player compilation; pinned engine module, no engine or SDK upgrade'}},
        'sourceResolution': 'Exact sealed hash from archive Inputs or current source; old package hashes may resolve from preserved attempt006, and settings temporarily derived by a root build may resolve from its ApprovedPreBuildSettings backup. Resolved locations are recorded in validation.',
        'generatedSources': {destination: sha(HERE / source) for source, destination in GENERATED.items()},
        'stages': ['setup', 'reopen', 'logout', 'closed', 'recover', 'recovered', 'delete', 'deleted'],
        'intentExtras': {
            'connected84_scope': 'qa84-<32 lowercase hex; same value across all stages>',
            'connected84_stage': 'one stage from the ordered stages list',
            'connected84_origin': 'explicit loopback HTTP authority; adb reverse is orchestrated externally',
        },
        'reports': 'files/Connected84/Reports/<sha256(scope)>/Stage_<stage>.json',
        'secretStorage': 'ONLY AndroidDeviceIdentity82 encrypted CAS under a separate proof namespace; no clipboard, plain recovery file, source constant or report field',
        'scope': 'Fixture explicitly instantiates frozen ordinary Home/ProfileHost. Actual SDK-absent programmatic Play/paid Hammer/quit and account service calls; no normal startup routing or physical-input claim. Each process boundary must be externally forced and independently PID-verified.',
        'limits': ['Preparation is not build/device proof.', 'Pinned replay HTTP fixture/worker is required for the paid Hammer.', 'No actual Android execution is performed by this tool.', 'No main/original QA/ordinary verification app nonmutation claim without external audits.', 'No production/store/SDK payment, hardware attestation or OS power-loss claim.'],
    }


def validate_sources(source_freeze: Path = DEFAULT_BASELINE) -> dict:
    source_freeze = logical(source_freeze)
    plan = describe(source_freeze)
    baseline = json.loads(fs(source_freeze).read_text(encoding='utf-8'))
    resolved = {relative: source_file(relative, digest, source_freeze) for relative, digest in baseline['files'].items()}
    return {
        **plan, 'status': 'VALIDATED_CONNECTED84_FROZEN_SOURCES_NO_PROJECT_COPY',
        'resolvedCount': len(resolved),
        'longLogicalPathCount': sum(len(str(path)) >= 260 for path in resolved.values()),
        'maximumLogicalPathLength': max(len(str(path)) for path in resolved.values()),
        'resolved': {relative: {'source': path.relative_to(ROOT).as_posix(), 'sha256': baseline['files'][relative]} for relative, path in resolved.items()},
        'validationScope': 'Python filesystem/hash resolution only. All sealed inputs read before project copying; no Unity, build, ADB or runtime claim. Logical manifest paths stay unprefixed; Windows extended paths are used only for I/O.',
    }


def prepare(out: Path, source_freeze: Path = DEFAULT_BASELINE) -> dict:
    out = logical(out)
    allowed = logical(ROOT / '.verification-cache/Connected84')
    if not out.is_relative_to(allowed) or out == allowed or fs(out).exists():
        raise ValueError('Use a new output path inside ignored Connected84 cache; preserve existing attempts')
    source_freeze = logical(source_freeze)
    plan = describe(source_freeze)
    baseline = json.loads(fs(source_freeze).read_text(encoding='utf-8'))
    # Resolve and verify all originals before writing a copied project.
    resolved = {relative: source_file(relative, digest, source_freeze) for relative, digest in baseline['files'].items()}
    copied = {}
    for relative, source in resolved.items():
        target = out / Path(relative).relative_to('Unity')
        fs(target.parent).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fs(source), fs(target))
        if sha(target) != baseline['files'][relative]:
            raise ValueError('Copied fixture input digest mismatch')
        copied[target.relative_to(out).as_posix()] = baseline['files'][relative]
    generated = {}
    derived = {}
    # Sealed main-project Editor proof did not require the Android-only module.
    # This player fixture explicitly includes the SAME pinned engine's builtin
    # JNI package; retain both original and derived hashes for review.
    for relative in ('Packages/manifest.json', 'Packages/packages-lock.json'):
        target = out / relative
        value = json.loads(fs(target).read_text(encoding='utf-8'))
        before = sha(target)
        if relative.endswith('manifest.json'):
            entry = value['dependencies'].get('com.unity.modules.androidjni')
            if entry not in (None, '1.0.0'):
                raise ValueError('Unexpected JNI module version in frozen manifest')
            value['dependencies']['com.unity.modules.androidjni'] = '1.0.0'
        else:
            entry = value['dependencies'].get('com.unity.modules.androidjni')
            expected = {'version': '1.0.0', 'depth': 0, 'source': 'builtin', 'dependencies': {}}
            if entry is not None and entry != expected:
                raise ValueError('Unexpected JNI module resolution in frozen lock')
            value['dependencies']['com.unity.modules.androidjni'] = expected
        fs(target).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
        derived[relative] = {'beforeSHA256': before, 'afterSHA256': sha(target), 'change': 'Pinned-engine builtin JNI 1.0.0 only'}

    def write(relative: str, value: str):
        target = out / relative
        if fs(target).exists():
            raise ValueError('Generated fixture path collides with a frozen input')
        fs(target.parent).mkdir(parents=True, exist_ok=True)
        fs(target).write_text(value, encoding='utf-8', newline='\n')
        generated[relative] = sha(target)

    for source, destination in GENERATED.items():
        write(destination, fs(HERE / source).read_text(encoding='utf-8'))
        write(destination + '.meta', 'fileFormatVersion: 2\nguid: ' + uuid.uuid5(NAMESPACE, destination).hex + '\nMonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
    for folder in ('Assets/Connected84Fixture', 'Assets/Connected84Fixture/Editor'):
        write(folder + '.meta', 'fileFormatVersion: 2\nguid: ' + uuid.uuid5(NAMESPACE, folder).hex + '\nfolderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
    write('Connected84_BaselineAssets.json', json.dumps({'files': [{'path': path, 'sha256': digest} for path, digest in copied.items() if path.startswith('Assets/')]}, indent=2) + '\n')
    write('Connected84_BaselineManifest.sha256', sha(source_freeze) + '\n')
    result = {**plan, 'status': 'PREPARED_ISOLATED_CONNECTED84_ANDROID_PROJECT_NOT_BUILT', 'project': out.relative_to(ROOT).as_posix(), 'copiedSourceSHA256': copied, 'derivedPackageSHA256': derived, 'generatedSHA256': generated}
    fs(out.parent / (out.name + '_Preparation.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT)
    parser.add_argument('--source-freeze', type=Path, default=DEFAULT_BASELINE, help='Explicit sealed input manifest (defaults to forthcoming VerifiedAppWithJNI)')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--describe', action='store_true', help='Write only the source plan, with no project copy')
    mode.add_argument('--validate-sources-only', action='store_true', help='Resolve/hash all sealed inputs, without copying a project or launching Unity')
    args = parser.parse_args()
    if args.describe:
        result = describe(args.source_freeze)
        fs(HERE / 'Fixture_Change_Manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    elif args.validate_sources_only:
        result = validate_sources(args.source_freeze)
        target = ROOT / '.verification-cache/Connected84/Preparation/Sources_Validation.json'
        fs(target.parent).mkdir(parents=True, exist_ok=True)
        fs(target).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    else:
        result = prepare(args.out, args.source_freeze)
    print(json.dumps({'status': result['status'], 'baselineInputs': result['baselineInputs'], 'generatedSources': len(result['generatedSources'])}))


if __name__ == '__main__':
    main()
