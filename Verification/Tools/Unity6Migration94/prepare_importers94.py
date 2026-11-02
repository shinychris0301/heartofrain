"""Prepare one fresh Editor-only native readback probe; root executes explicitly.

No Unity, SDK, importer or device command is run. Only two new candidate fixture
files and one external private expected-data file are added. Main is immutable.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PUBLIC = ROOT / 'Verification/Evidence/Unity6Migration94'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
PRIVATE = ROOT / '.verification-cache/Unity6Migration94/ImporterExpected'
RELATIVE = 'Assets/HeartOfTheRain/Verification/Editor/Unity6Importer94.cs'
TEMPLATE = HERE / 'Templates/Unity6Importer94.cs'
RECEIPT = PUBLIC / 'ImporterPreparation/Report.json'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def png_size(raw):
    if len(raw) < 24 or raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
        raise ValueError('Original target must be an intact PNG with IHDR')
    result = struct.unpack('>II', raw[16:24])
    if min(result) <= 0:
        raise ValueError('Original PNG dimensions must be positive')
    return result


def effective_pivot(alignment, pivot):
    pairs = ((.5, .5), (0, 1), (.5, 1), (1, 1), (0, .5), (1, .5), (0, 0), (.5, 0), (1, 0))
    if alignment == 9:
        return dict(pivot)
    if not 0 <= alignment < len(pairs):
        raise ValueError('Unknown original Sprite alignment')
    return dict(zip(('x', 'y'), pairs[alignment]))


def expected_row(relative, meta, source_png, candidate_meta_sha, main_meta_sha, asset_sha, refs):
    importer = meta['TextureImporter']
    if importer['spriteMode'] != 1 or importer['textureType'] != 8:
        raise ValueError('Original SingleSprite texture required')
    width, height = png_size(source_png)
    pivot = importer['spritePivot']
    ppu = importer['spritePixelsToUnits']
    if not isinstance(pivot, dict) or set(pivot) != {'x', 'y'} or ppu <= 0:
        raise ValueError('Explicit original pivot and positive PPU required')
    alignment = importer.get('alignment', importer.get('spriteAlignment'))
    if alignment is None:
        raise ValueError('Explicit original alignment required')
    settings = importer.get('textureSettings', {})
    result = {'path': relative, 'guid': str(meta['guid']),
        'mainMetaSHA256': main_meta_sha, 'candidateMetaSHA256': candidate_meta_sha, 'assetSHA256': asset_sha,
        'sourceWidth': width, 'sourceHeight': height, 'alignment': alignment,
        'pivot': pivot, 'effectivePivot': effective_pivot(alignment, pivot), 'pixelsPerUnit': ppu,
        'hasBorder': 'spriteBorder' in importer,
        'border': importer.get('spriteBorder', dict.fromkeys(('x', 'y', 'z', 'w'), 0)),
        'mipmaps': bool(importer['mipmaps']['enableMipMap']),
        'hasFilter': settings.get('filterMode', -1) >= 0, 'filterMode': settings.get('filterMode', -1),
        'referencedSpriteFileIDs': sorted(refs.get(str(meta['guid']), set())),
        'originalAndroidSettings': next((item for item in importer.get('platformSettings', [])
                                         if item.get('buildTarget') == 'Android'), None)}
    for axis in ('U', 'V', 'W'):
        key = 'wrap' + axis
        result['hasWrap' + axis] = key in settings and settings[key] >= 0
        result[key] = settings.get(key, -1)
    return result


def exact_added_fixture(before, after, template_sha, meta_sha):
    expected = {RELATIVE: template_sha, RELATIVE + '.meta': meta_sha}
    added = set(after) - set(before)
    if added != set(expected) or any(after[path] != before[path] for path in before):
        raise ValueError('Preparation must add only the two fresh fixture files')
    if any(after[path]['sha256'] != value for path, value in expected.items()):
        raise ValueError('Added fixture hashes differ from reviewed bytes')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--execute', action='store_true')
    args = cli.parse_args()
    if not args.execute:
        print('Root --execute adds only the new isolated Editor probe and private expected data; no native execution.')
        return 0
    if os.name != 'nt':
        cli.error('Explicit root Windows preparation required')
    audit = module('importer94_source_policy', HERE / 'audit_candidate94.py')
    semantic = module('importer94_original_meta_parser', HERE / 'review_importers94.py')
    processes = module('importer94_process_guard', ROOT / 'Verification/Tools/PageBackdrop90/process90.py')
    if processes.unity_pids():
        cli.error('No concurrent Unity process is permitted during preparation')
    for path in (PROJECT, PRIVATE, RECEIPT.parent, TEMPLATE):
        audit.reject_links(path)
    destination = PROJECT / RELATIVE
    if PRIVATE.exists() or RECEIPT.parent.exists() or destination.exists() or Path(str(destination) + '.meta').exists():
        cli.error('Fresh fixture/private expected directory/preparation receipt required')
    baseline = json.loads((PUBLIC / 'MainSources_Before.json').read_text('utf-8'))
    preparation = json.loads((PUBLIC / 'Preparation.json').read_text('utf-8'))
    if preparation['mainManifestSHA256'] != audit.sha(PUBLIC / 'MainSources_Before.json') or baseline['inputCount'] != 5407:
        raise ValueError('Exact authorized main5407 baseline required')
    before_main = audit.inventory(ROOT / 'Unity', 'Unity/')
    if before_main != baseline:
        raise ValueError('Original main source changed before preparation')
    before_candidate = audit.inventory(PROJECT)
    source_audit = PUBLIC / 'SourceAudit/Set01'
    selected = json.loads((source_audit / 'Report.json').read_text('utf-8'))
    delta = semantic.bound_audit_json(source_audit, selected, 'FileChanges.json')
    targets = []
    for item in delta:
        if item['kind'] != 'changed' or not item['path'].endswith('.meta'):
            continue
        path = ROOT / 'Unity' / item['path']
        if audit.sha(path) != item['before']['sha256']:
            raise ValueError('Selected original metadata authority changed')
        parsed = semantic.parse_yaml(path.read_bytes())
        parsed['guid'] = audit.GUID.search(path.read_bytes()).group(1).decode('ascii').lower()
        if parsed.get('TextureImporter', {}).get('spriteMode') == 1:
            targets.append((item['path'][:-5], parsed, item['before']['sha256']))
    if len(targets) != 438:
        raise ValueError('Exactly438 selected original SingleSprite targets required')
    guids = {str(meta['guid']) for _, meta, _ in targets}
    refs = {}
    pattern = re.compile(rb'\{fileID:\s*(21300000),\s*guid:\s*([0-9a-fA-F]{32}),\s*type:\s*3\}')
    for relative, entry in baseline['files'].items():
        if Path(relative).suffix not in ('.asset', '.unity', '.prefab', '.mat'):
            continue
        data = (ROOT / relative).read_bytes()
        if audit.sha_bytes(data) != entry['sha256']:
            raise ValueError('Original serialized reference bytes changed')
        for match in pattern.finditer(data):
            guid = match.group(2).decode('ascii').lower()
            if guid in guids:
                refs.setdefault(guid, set()).add(int(match.group(1)))
    rows = []
    for relative, parsed, meta_sha in targets:
        asset = ROOT / 'Unity' / relative
        candidate_meta = PROJECT / (relative + '.meta')
        if audit.sha(asset) != baseline['files']['Unity/' + relative]['sha256']:
            raise ValueError('Original PNG authority changed')
        if audit.sha(PROJECT / relative) != audit.sha(asset):
            raise ValueError('Candidate PNG differs from approved artwork')
        rows.append(expected_row(relative, parsed, asset.read_bytes(), audit.sha(candidate_meta),
                                 meta_sha, audit.sha(asset), refs))
    nonzero = sum(any(value != 0 for value in row['border'].values()) for row in rows)
    if nonzero != 105:
        raise ValueError('Exactly105 original nonzero borders required')
    expected = {'schemaVersion': 1, 'authority': 'ORIGINAL_MAIN_META_AND_PNG_BYTES94',
        'mainManifestSHA256': preparation['mainManifestSHA256'], 'rowsExpected': 438,
        'nonzeroBordersExpected': 105, 'rows': rows}
    guid = uuid.uuid4().hex
    meta = ('fileFormatVersion: 2\nguid: ' + guid + '\nMonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n').encode('utf-8')
    template = TEMPLATE.read_bytes()
    RECEIPT.parent.mkdir(parents=True, exist_ok=False)
    PRIVATE.mkdir(parents=True, exist_ok=False)
    expected_path = PRIVATE / 'Expected.json'
    audit.write_new(expected_path, expected)
    with destination.open('xb') as stream:
        stream.write(template)
    with Path(str(destination) + '.meta').open('xb') as stream:
        stream.write(meta)
    after_main = audit.inventory(ROOT / 'Unity', 'Unity/')
    after_candidate = audit.inventory(PROJECT)
    if before_main != after_main:
        raise ValueError('Main source changed during preparation')
    exact_added_fixture(before_candidate['files'], after_candidate['files'],
                        audit.sha_bytes(template), audit.sha_bytes(meta))
    for name, value in (('MainSources_before.json', before_main), ('MainSources_after.json', after_main),
                        ('CandidateSources_before.json', before_candidate), ('CandidateSources_after.json', after_candidate)):
        audit.write_new(RECEIPT.parent / name, value)
    record = {'schemaVersion': 1, 'status': 'PREPARED_ISOLATED_READ_ONLY_IMPORTER_PROBE94',
        'utc': audit.utc(), 'runnerSHA256': audit.sha(__file__), 'mainInputsUnchanged': True,
        'mainInputCount': 5407, 'onlyTwoCandidateFixtureFilesAdded': True,
        'newFixtureGuid': guid, 'fixture': RELATIVE, 'templateSHA256': audit.sha(TEMPLATE),
        'metaSHA256': audit.sha_bytes(meta), 'expectedPath': expected_path.relative_to(ROOT).as_posix(),
        'expectedSHA256': audit.sha(expected_path), 'expectedRows': 438, 'expectedNonzeroBorders': 105,
        'originalReferencedSpriteRows': sum(bool(row['referencedSpriteFileIDs']) for row in rows),
        'sourceAudit': source_audit.relative_to(ROOT).as_posix(), 'sourceAuditSHA256': audit.sha(source_audit / 'Report.json'),
        'companionSHA256': {name: audit.sha(RECEIPT.parent / name) for name in
            ('MainSources_before.json', 'MainSources_after.json', 'CandidateSources_before.json', 'CandidateSources_after.json')},
        'nativeOrSdkOrDeviceProcessesRun': False,
        'scope': 'Preparation only. Original438 SingleSprite metadata/PNG bytes and105 nonzero borders supply expected geometry. New Editor probe and its meta are the only candidate input additions; expected JSON stays outside Assets. No importer, native, device or main promotion approval.'}
    audit.write_new(RECEIPT, record)
    print(json.dumps(record), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
