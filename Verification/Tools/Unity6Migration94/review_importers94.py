"""Read-only semantic inventory of source-audit importer/package/settings deltas.

Uses the already-installed safe YAML parser. No Unity, SDK, importer, package,
account or device operation occurs. Generated metadata is not runtime proof.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import stat

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
MAIN = ROOT / 'Unity'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def reject_links(path):
    for item in (Path(path), *Path(path).parents):
        if item.exists() and (item.is_symlink() or getattr(item.stat(), 'st_file_attributes', 0)
                              & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)):
            raise ValueError('Reparse point or symbolic link refused')


def refuse_credentials(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if (re.search(r'(?i)(?:password|keystorepass|keyaliaspass|access.?token|api.?secret|client.?secret|private.?key)', str(key))
                    and item not in (None, '', [], {})):
                raise ValueError('Potential nonempty credential field refused from export')
            refuse_credentials(item)
    elif isinstance(value, list):
        for item in value:
            refuse_credentials(item)


class StrictLoader(yaml.SafeLoader):
    pass


def strict_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError('Repeated YAML key requires explicit review')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, strict_mapping)


def parse_yaml(raw):
    text = raw.decode('utf-8-sig')
    text = re.sub(r'(?m)^%(?:YAML|TAG)\b[^\n]*\n?', '', text)
    text = re.sub(r'(?m)^---\s*!u!\d+\s*&\d+\s*$', '---', text)
    if any(isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
           for token in yaml.scan(text)):
        raise ValueError('Unexpected YAML alias/anchor refused')
    value = yaml.load(text, Loader=StrictLoader)
    if not isinstance(value, dict):
        raise ValueError('Expected a serialized mapping')
    return value


def normalized(value):
    """Typed identity except equivalent finite integer/decimal YAML scalars."""
    if isinstance(value, bool):
        return ('bool', value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Nonfinite serialized numeric value requires review')
        if isinstance(value, float) and value == 0 and math.copysign(1, value) < 0:
            return ('number-negative-zero',)
        # Decimal equality/hash are exact here; normalize() would round long
        # serialized integer IDs through the ambient decimal context.
        return ('number', Decimal(str(value)))
    if isinstance(value, dict):
        return ('map', tuple(sorted(((normalized(key), normalized(item))
                                    for key, item in value.items()), key=repr)))
    if isinstance(value, list):
        return ('list', tuple(normalized(item) for item in value))
    return (type(value).__name__, value)


def equal(a, b):
    return normalized(a) == normalized(b)


def changes(before, after, prefix=''):
    result = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after), key=str):
            path = prefix + '/' + str(key) if prefix else str(key)
            if key not in before:
                result.append({'path': path, 'kind': 'added', 'after': after[key]})
            elif key not in after:
                result.append({'path': path, 'kind': 'removed', 'before': before[key]})
            else:
                result.extend(changes(before[key], after[key], path))
    elif not equal(before, after):
        result.append({'path': prefix, 'kind': 'changed', 'before': before, 'after': after})
    return result


def platform_map(importer):
    result, aliases = {}, []
    for row in importer.get('platformSettings', []):
        original = row.get('buildTarget')
        target = 'iOS' if original == 'iPhone' else original
        if not isinstance(target, str) or target in result:
            raise ValueError('Ambiguous importer platform settings')
        if original != target:
            aliases.append({'serialized': original, 'comparisonKey': target})
        result[target] = {key: value for key, value in row.items()
                          if key not in ('buildTarget', 'serializedVersion')}
    return result, aliases


def strip_versions(value):
    if isinstance(value, dict):
        return {key: strip_versions(item) for key, item in value.items() if key != 'serializedVersion'}
    if isinstance(value, list):
        return [strip_versions(item) for item in value]
    return value


def list_mapping_delta(before, after):
    a = [normalized(strip_versions(item)) for item in before]
    b = [normalized(strip_versions(item)) for item in after]
    # Preserve multiplicities; a set would hide duplicate subasset mappings.
    left, right = Counter(a), Counter(b)
    return {'beforeEntries': len(a), 'afterEntries': len(b),
            'existingEntriesPreserved': not (left - right),
            'removedOrChangedExistingEntries': sum((left - right).values()),
            'introducedOrChangedEntries': sum((right - left).values()),
            'exactEntriesEqual': a == b}


def review_meta(before, after):
    classes = [key for key in before if key not in ('fileFormatVersion', 'guid')]
    if len(classes) != 1 or classes != [key for key in after if key not in ('fileFormatVersion', 'guid')]:
        raise ValueError('Importer class changed or ambiguous')
    importer_type = classes[0]
    a, b = before[importer_type], after[importer_type]
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise ValueError('Expected importer settings mapping')
    result = {'importerType': importer_type, 'assetGuidPreserved': equal(before.get('guid'), after.get('guid')),
              'semanticYamlEqual': equal(before, after)}
    if importer_type != 'TextureImporter':
        result.update(semanticChanges=changes(before, after),
                      scope='Nontexture importer requires its explicit semantic diff review.')
        return result
    pa, aa = platform_map(a)
    pb, ab = platform_map(b)
    source_sheet, target_sheet = a.get('spriteSheet', {}), b.get('spriteSheet', {})
    existing_platform = {}
    for key in pa:
        differences = changes(pa[key], pb.get(key), key)
        existing_platform[key] = {
            'settingsEqualIgnoringSchemaVersion': equal(pa[key], pb.get(key)),
            'existingFieldsPreserved': all(change['kind'] == 'added' for change in differences),
            'addedFields': [change for change in differences if change['kind'] == 'added'],
            'changedOrRemovedExistingFields': [change for change in differences if change['kind'] != 'added'],
            'changes': differences}
    added_platforms = {key: pb[key] for key in pb if key not in pa}
    table_delta = list_mapping_delta(a.get('internalIDToNameTable', []), b.get('internalIDToNameTable', []))
    sprite_delta = list_mapping_delta(source_sheet.get('sprites', []), target_sheet.get('sprites', []))
    comparable_a, comparable_b = strip_versions(a), strip_versions(b)
    for item in (comparable_a, comparable_b):
        item.pop('platformSettings', None)
        item.pop('internalIDToNameTable', None)
        item.get('spriteSheet', {}).pop('sprites', None)
    core_changes = changes(comparable_a, comparable_b)
    introduced_fields, unresolved = [], []
    known_added_values = {'spriteTessellationMethod': 0, 'spriteGeometrySubdivision': -1,
                         'spriteSheet/customData': None,
                         'spriteSheet/spriteCustomMetadata': {'entries': []}}
    for change in core_changes:
        if (change['kind'] == 'added' and change['path'] in known_added_values
                and equal(change['after'], known_added_values[change['path']])):
            introduced_fields.append(change)
        else:
            unresolved.append(change)
    nonzero_border_new_zero = []
    original_border = a.get('spriteBorder', {})
    if isinstance(original_border, dict) and any(value != 0 for value in original_border.values()):
        for item in target_sheet.get('sprites', []):
            border = item.get('border', {})
            if isinstance(border, dict) and border and all(value == 0 for value in border.values()):
                nonzero_border_new_zero.append({'name': item.get('name'), 'internalID': item.get('internalID'),
                    'topLevelImporterBorder': original_border, 'generatedChildBorder': border})
    result.update(
        spriteModeBefore=a.get('spriteMode'), spriteModeAfter=b.get('spriteMode'),
        topLevelSpriteIDPreserved=equal(source_sheet.get('spriteID'), target_sheet.get('spriteID')),
        platformAliasObservations={'main': aa, 'candidate': ab}, existingPlatforms=existing_platform,
        androidSettingsUnchanged=equal(pa.get('Android'), pb.get('Android')),
        defaultSettingsUnchanged=equal(pa.get('DefaultTexturePlatform'), pb.get('DefaultTexturePlatform')),
        androidExistingFieldsPreserved=existing_platform.get('Android', {}).get('existingFieldsPreserved'),
        defaultExistingFieldsPreserved=existing_platform.get('DefaultTexturePlatform', {}).get('existingFieldsPreserved'),
        addedPlatforms=added_platforms,
        allAddedPlatformsAreNonOverridden=all(item.get('overridden') == 0 for item in added_platforms.values()),
        internalIDToNameTable=table_delta, spriteSheetEntries=sprite_delta,
        introducedUnity6FieldsRequiringRecordedReview=introduced_fields,
        remainingImporterFieldChangesRequiringReview=unresolved,
        addedImporterFieldsRequiringReview=[change for change in unresolved if change['kind'] == 'added'],
        changedOrRemovedExistingImporterFields=[change for change in unresolved if change['kind'] != 'added'],
        allOtherImporterFieldsEqualIgnoringSchemaVersions=not unresolved,
        nonzeroTopBorderAndGeneratedZeroChildBorder=nonzero_border_new_zero,
        scope='Serialized importer comparison, not imported runtime Sprite/mesh/UV/fileID equivalence. Schema versions and the observed iPhone/iOS key rename are separated. Generated subasset entries and newly introduced fields remain explicit changes; none is automatically approved.')
    return result


def semantic_settings(raw):
    value = parse_yaml(raw)
    if len(value) != 1:
        raise ValueError('Expected one Unity serialized settings object')
    return value


def bound_audit_json(directory, audit, name):
    path = Path(directory) / name
    reject_links(path)
    if audit.get('reportFileSHA256', {}).get(name) != sha(path):
        raise ValueError('Source audit companion hash differs: ' + name)
    return json.loads(path.read_text('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-audit', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    reject_links(args.source_audit)
    reject_links(args.out)
    audit_path, directory = args.source_audit.resolve(), args.out.resolve()
    if (not audit_path.is_relative_to(OUT / 'SourceAudit') or audit_path.name != 'Report.json'
            or not directory.is_relative_to(OUT / 'ImporterReview') or directory.exists()):
        parser.error('Explicit source audit and fresh ImporterReview child required')
    audit = json.loads(audit_path.read_text('utf-8'))
    if audit.get('status') != 'PASS_ISOLATED_CANDIDATE_SOURCE_AUDIT94_WITH_CONFIGURATION_REVIEW_REQUIRED':
        parser.error('Passing exact source audit required')
    audit_hash = sha(audit_path)
    main_manifest = bound_audit_json(audit_path.parent, audit, 'MainSources_before.json')['files']
    candidate_manifest = bound_audit_json(audit_path.parent, audit, 'CandidateSources.json')['files']
    delta = bound_audit_json(audit_path.parent, audit, 'FileChanges.json')
    directory.mkdir(parents=True, exist_ok=False)
    before_hashes, rows, settings, packages = {}, [], [], []
    for item in delta:
        relative = item['path']
        if not (relative.endswith('.meta') or relative.startswith(('Packages/', 'ProjectSettings/'))):
            continue
        source, target = MAIN / relative, PROJECT / relative
        if not source.resolve().is_relative_to(MAIN.resolve()) or not target.resolve().is_relative_to(PROJECT.resolve()):
            raise ValueError('Source audit path escaped project boundary')
        reject_links(source)
        reject_links(target)
        left = source.read_bytes() if source.is_file() else None
        right = target.read_bytes() if target.is_file() else None
        if left is not None and sha(source) != main_manifest['Unity/' + relative]['sha256']:
            raise ValueError('Main source differs from source-audit input: ' + relative)
        if right is not None and sha(target) != candidate_manifest[relative]['sha256']:
            raise ValueError('Candidate changed since selected source audit: ' + relative)
        before_hashes[relative] = {'mainSHA256': sha(source) if left is not None else None,
                                   'candidateSHA256': sha(target) if right is not None else None}
        if relative.endswith('.meta') and left is not None and right is not None:
            rows.append({'path': relative, **before_hashes[relative],
                         **review_meta(parse_yaml(left), parse_yaml(right))})
        elif relative.startswith('Packages/'):
            a = json.loads(left) if left is not None else {}
            b = json.loads(right) if right is not None else {}
            refuse_credentials(a)
            refuse_credentials(b)
            packages.append({'path': relative, **before_hashes[relative],
                             'semanticChanges': changes(a, b), 'rootReviewRequired': True})
        elif relative.endswith('.asset'):
            a = semantic_settings(left) if left is not None else {}
            b = semantic_settings(right) if right is not None else {}
            refuse_credentials(a)
            refuse_credentials(b)
            settings.append({'path': relative, **before_hashes[relative],
                             'semanticChanges': changes(a, b), 'rootReviewRequired': True})
        else:
            settings.append({'path': relative, **before_hashes[relative],
                             'mainText': left.decode('utf-8-sig') if left is not None else None,
                             'candidateText': right.decode('utf-8-sig') if right is not None else None,
                             'rootReviewRequired': True})
    for relative, expected in before_hashes.items():
        for project, key in ((MAIN, 'mainSHA256'), (PROJECT, 'candidateSHA256')):
            path = project / relative
            actual = sha(path) if path.is_file() else None
            if actual != expected[key]:
                raise ValueError('Input changed during semantic review: ' + relative)
    textures = [row for row in rows if row['importerType'] == 'TextureImporter']
    if len(rows) != audit['changedExistingMetadataCount']:
        raise ValueError('Changed existing metadata inventory is incomplete')
    if sha(audit_path) != audit_hash:
        raise ValueError('Source audit changed during importer analysis')
    for name in ('MainSources_before.json', 'CandidateSources.json', 'FileChanges.json'):
        bound_audit_json(audit_path.parent, audit, name)
    summary = {'schemaVersion': 1, 'status': 'RECORDED_IMPORTER_AND_CONFIGURATION_SEMANTICS94_REQUIRES_ROOT_REVIEW',
        'utc': datetime.now(timezone.utc).isoformat(), 'runnerSHA256': sha(__file__),
        'sourceAudit': audit_path.relative_to(ROOT).as_posix(), 'sourceAuditSHA256': sha(audit_path),
        'sourceAuditCandidateManifestSHA256': sha(audit_path.parent / 'CandidateSources.json'),
        'yamlParserVersion': yaml.__version__, 'yamlParserModuleSHA256': sha(yaml.__file__),
        'inputHashes': before_hashes, 'inputsUnchanged': True, 'nativeProcessesRun': False,
        'rootApprovalInferred': False, 'metadataFilesReviewed': len(rows), 'textureImportersReviewed': len(textures),
        'importerTypes': dict(Counter(row['importerType'] for row in rows)),
        'spriteModes': dict(Counter(str(row['spriteModeBefore']) + '->' + str(row['spriteModeAfter'])
                                   for row in textures)),
        'assetGuidsPreserved': sum(row['assetGuidPreserved'] for row in rows),
        'strictSemanticYamlEqual': sum(row['semanticYamlEqual'] for row in rows),
        'androidSettingsUnchanged': sum(row['androidSettingsUnchanged'] for row in textures),
        'defaultSettingsUnchanged': sum(row['defaultSettingsUnchanged'] for row in textures),
        'androidExistingFieldsPreserved': sum(row['androidExistingFieldsPreserved'] is True for row in textures),
        'defaultExistingFieldsPreserved': sum(row['defaultExistingFieldsPreserved'] is True for row in textures),
        'originalAndroidPlatformRows': sum('Android' in row['existingPlatforms'] for row in textures),
        'originalDefaultPlatformRows': sum('DefaultTexturePlatform' in row['existingPlatforms'] for row in textures),
        'topLevelSpriteIDsPreserved': sum(row['topLevelSpriteIDPreserved'] for row in textures),
        'existingIDTableEntriesPreserved': sum(row['internalIDToNameTable']['existingEntriesPreserved'] for row in textures),
        'existingSpriteSheetEntriesPreserved': sum(row['spriteSheetEntries']['existingEntriesPreserved'] for row in textures),
        'newIDTableEntries': sum(row['internalIDToNameTable']['introducedOrChangedEntries'] for row in textures),
        'newSpriteSheetEntries': sum(row['spriteSheetEntries']['introducedOrChangedEntries'] for row in textures),
        'remainingImporterChangeFieldCounts': dict(Counter(change['kind'] + ':' + change['path']
            for row in textures for change in row['remainingImporterFieldChangesRequiringReview'])),
        'platformAddedFieldCounts': dict(Counter(change['path'] for row in textures
            for platform in row['existingPlatforms'].values() for change in platform['addedFields'])),
        'existingPlatformFieldsChangedOrRemoved': [{'path': row['path'], 'platform': name,
            'changes': platform['changedOrRemovedExistingFields']} for row in textures
            for name, platform in row['existingPlatforms'].items() if platform['changedOrRemovedExistingFields']],
        'addedPlatformCounts': dict(Counter(name for row in textures for name in row['addedPlatforms'])),
        'allAddedPlatformsAreNonOverridden': all(row['allAddedPlatformsAreNonOverridden'] for row in textures),
        'filesWithRemainingImporterFieldChanges': [row['path'] for row in textures if row['remainingImporterFieldChangesRequiringReview']],
        'filesWithChangedOrRemovedExistingImporterFields': [row['path'] for row in textures if row['changedOrRemovedExistingImporterFields']],
        'filesWithNonzeroTopBorderAndGeneratedZeroChildBorder': [row['path'] for row in textures if row['nonzeroTopBorderAndGeneratedZeroChildBorder']],
        'scope': 'Every changed existing .meta file in the selected source audit is parsed and hash-bound; platform fields, existing GUID/ID entries, generated subassets, added fields, package and serialized settings changes are kept distinct. Serialization sameness/preservation does not prove runtime imported sprite IDs, borders, UVs, meshes, filtering or device equivalence.'}
    for value in (rows, packages, settings, summary):
        refuse_credentials(value)
    write(directory / 'ImporterRows.json', rows)
    write(directory / 'PackageRows.json', packages)
    write(directory / 'SettingsRows.json', settings)
    summary['companionSHA256'] = {name: sha(directory / name) for name in
                                  ('ImporterRows.json', 'PackageRows.json', 'SettingsRows.json')}
    write(directory / 'Report.json', summary)
    print(json.dumps({key: value for key, value in summary.items() if key not in ('inputHashes',)}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
