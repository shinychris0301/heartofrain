"""Copy exact main inputs into a fresh, approved migration sandbox; never link them."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'


def shared():
    spec = importlib.util.spec_from_file_location('migration94_source_reader', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reject_links(path):
    for node in (path, *path.parents):
        if node.exists() and (node.is_symlink() or getattr(node.stat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise RuntimeError('ReparsePointRefused')


def main():
    api = shared()
    reject_links(PROJECT)
    if PROJECT.exists() or (OUT / 'Preparation.json').exists():
        raise RuntimeError('ExistingMigrationPreserved')
    template = ROOT / 'Verification/Tools/Unity6Migration94/Templates/Unity6Migration94.cs'
    if not template.is_file():
        raise RuntimeError('ApprovedIsolatedTemplateRequired')
    original = api.freeze()
    OUT.mkdir(parents=True, exist_ok=True)
    api.write(OUT / 'MainSources_Before.json', original)
    PROJECT.mkdir(parents=True, exist_ok=False)
    for relative, expected in original['files'].items():
        source = ROOT / relative
        reject_links(source)
        tail = Path(relative).relative_to('Unity')
        destination = PROJECT / tail
        if not destination.resolve().is_relative_to(PROJECT.resolve()) or destination.exists():
            raise RuntimeError('FreshContainedCopyRequired')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if api.sha(destination) != expected['sha256'] or destination.stat().st_size != expected['bytes']:
            raise RuntimeError('CopiedInputMismatch')
    copied = PROJECT / 'Assets/HeartOfTheRain/Verification/Editor/Unity6Migration94.cs'
    if copied.exists() or copied.with_suffix('.cs.meta').exists():
        raise RuntimeError('TemplateCollision')
    shutil.copy2(template, copied)
    guid = uuid.uuid4().hex
    copied.with_suffix('.cs.meta').write_text('fileFormatVersion: 2\nguid: ' + guid + '\nMonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n', encoding='utf-8')
    after = api.freeze()
    api.write(OUT / 'MainSources_AfterCopy.json', after)
    if original != after:
        raise RuntimeError('ProtectedMainInputsChanged')
    review = ROOT / 'Verification/Evidence/Review93/Summary.json'
    record = {'schemaVersion': 1, 'status': 'PASS_EXACT_MAIN_COPY94', 'utc': api.utc(),
        'authorization': 'USER_APPROVED_ISOLATED_UNITY6_MIGRATION',
        'authorizationAnswer': 'Approve isolated Unity 6 migration',
        'baselineCommit': '196f606d', 'mainInputCount': original['inputCount'],
        'project': PROJECT.relative_to(ROOT).as_posix(), 'mainInputsUnchanged': True,
        'mainManifestSHA256': api.sha(OUT / 'MainSources_Before.json'),
        'accepted93SummarySHA256': api.sha(review), 'templateSHA256': api.sha(template),
        'newTemplateGuid': guid, 'runnerSHA256': api.sha(Path(__file__)),
        'scope': 'Ordinary separate file copies of exact Assets/Packages/ProjectSettings only, plus one isolated Editor verification template. No hardlinks, Library, builds, saves, credentials, backend or installed-app replacement.'}
    api.write(OUT / 'Preparation.json', record)
    print(json.dumps({'status': record['status'], 'mainInputs': original['inputCount']}), flush=True)


if __name__ == '__main__':
    main()
