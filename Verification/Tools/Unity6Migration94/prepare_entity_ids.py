"""Prepare/review then root-apply exact isolated Unity6 EntityId compatibility edits."""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
EDITOR = 'Assets/HeartOfTheRain/Verification/Editor/'
RUNTIME = 'Assets/HeartOfTheRain/'
FILES = (
    RUNTIME + 'M47/Runtime/EffectMeshBatcher.cs',
    EDITOR + 'EffectBatchVerification.cs', EDITOR + 'DenseSubmissionVerification.cs',
    RUNTIME + 'Verification/Execution78Probe.cs', RUNTIME + 'Verification/ProfileM71Verification.cs',
    EDITOR + 'PresentationWarmupVerification.cs', EDITOR + 'HomeLivesR1Review.cs',
    RUNTIME + 'Chapter01M04/Scripts/RocketSpritePlayer.cs', RUNTIME + 'Chapter01M05/Scripts/RenderedSpritePlayer.cs',
)
BATCH_KEY = '''        // Unity6 opaque identity stays intact; hashes only choose dictionary buckets.
        readonly struct BatchKey : System.IEquatable<BatchKey> {
            readonly EntityId texture;readonly int order;
            public BatchKey(EntityId texture,int order){this.texture=texture;this.order=order;}
            public bool Equals(BatchKey other)=>texture.Equals(other.texture)&&order==other.order;
            public override bool Equals(object value)=>value is BatchKey other&&Equals(other);
            public override int GetHashCode()=>unchecked((texture.GetHashCode()*397)^order);
            public static bool operator==(BatchKey left,BatchKey right)=>left.Equals(right);
            public static bool operator!=(BatchKey left,BatchKey right)=>!left.Equals(right);
        }
'''
COMMON = (
    ('readonly Dictionary<long,Slot> open=new Dictionary<long,Slot>();', 'readonly Dictionary<BatchKey,Slot> open=new Dictionary<BatchKey,Slot>();'),
    ('        static readonly int MainTexture=', BATCH_KEY + '        static readonly int MainTexture='),
)
CACHED = (
    ('public int textureId;', 'public EntityId textureId;'),
    ('Slot current;long currentKey;int used;', 'Slot current;BatchKey currentKey;int used;'),
    ('currentKey=0;', 'currentKey=default;'),
    ('textureId=texture.GetInstanceID()', 'textureId=texture.GetEntityId()'),
    ('long key=((long)g.textureId<<32)^(uint)order;', 'var key=new BatchKey(g.textureId,order);'),
)
UNCACHED = (('long key=((long)g.texture.GetInstanceID()<<32)^(uint)order;', 'var key=new BatchKey(g.texture.GetEntityId(),order);'),)
ARCHIVES = (
    ('Gameplay75', 'fa4a2ceb07d12f7835143a01216cfc2009aa6695d7b0fe39bdccf5bf2aebea97'),
    ('Gameplay76', '346d1a40be8df1fad764b66f00f1aa167b802be8f97d77c0a7e15427f81e2371'),
    ('Gameplay78', '5d0fc628430da9e342cb4d6c1c69229010960cac3118715a835cafa9fb8e4f7d'),
)


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def once(text, before, after):
    need(text.count(before) == 1, 'ExactSingleApiReplacementRequired:' + before[:70])
    return text.replace(before, after, 1)


def adapt_batch_body(text):
    """Only known local identity/key declarations; every expected edit occurs once."""
    need('readonly struct BatchKey' not in text, 'AlreadyAdaptedBatchBodyRefused')
    cached = 'public int textureId;' in text
    pairs = CACHED if cached else UNCACHED
    for before, after in (*pairs, *COMMON):
        text = once(text, before, after)
    return text


def csharp_normalizer():
    body = ['  // Raw archived-source SHA checks run first. Only this exact API port is normalized.',
            '  static string EntityIdReplaceOnce94(string text,string before,string after){',
            '   int at=text.IndexOf(before,StringComparison.Ordinal);if(at<0||text.IndexOf(before,at+before.Length,StringComparison.Ordinal)>=0)throw new InvalidOperationException("Unexpected archived EntityId API shape");',
            '   return text.Substring(0,at)+after+text.Substring(at+before.Length);',
            '  }',
            '  internal static string AdaptArchivedEntityIdentity94(string original){',
            '   if(original.Contains("readonly struct BatchKey"))throw new InvalidOperationException("Already adapted archived identity");',
            '   bool cached=original.Contains("public int textureId;");', '   if(cached){']
    for before, after in CACHED:
        body.append('    original=EntityIdReplaceOnce94(original,' + json.dumps(before) + ',' + json.dumps(after) + ');')
    body.extend(['   }else{'])
    for before, after in UNCACHED:
        body.append('    original=EntityIdReplaceOnce94(original,' + json.dumps(before) + ',' + json.dumps(after) + ');')
    body.append('   }')
    for before, after in COMMON:
        body.append('   original=EntityIdReplaceOnce94(original,' + json.dumps(before) + ',' + json.dumps(after) + ');')
    body.extend(['   return original;', '  }'])
    return '\n'.join(body) + '\n'


def replace_region(text, begin, end):
    need(text.count(begin) == text.count(end) == 1, 'ExactFrozenRegionRequired')
    start = text.index(begin) + len(begin)
    finish = text.index(end, start)
    return text[:start] + adapt_batch_body(text[start:finish]) + text[finish:]


def preserve_unmodified_line_bytes(raw, canonical_after):
    """Reuse original equal lines verbatim, including locally mixed LF/CRLF."""
    had_bom = raw.startswith(b'\xef\xbb\xbf')
    original = raw.decode('utf-8-sig')
    raw_lines = original.splitlines(keepends=True)
    before = [line.replace('\r\n', '\n') for line in raw_lines]
    after = canonical_after.splitlines(keepends=True)

    def ending(line):
        return '\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''

    def nearby_ending(index, next_index):
        for prior in reversed(raw_lines[:index]):
            if ending(prior):
                return ending(prior)
        for following in raw_lines[next_index:]:
            if ending(following):
                return ending(following)
        return '\n'

    result = []
    for kind, i1, i2, j1, j2 in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        if kind == 'equal':
            result.extend(raw_lines[i1:i2])
        elif kind in ('replace', 'insert'):
            local_newline = nearby_ending(i1, i2)
            result.extend(line[:-1] + local_newline if line.endswith('\n') else line for line in after[j1:j2])
    encoded = ''.join(result).encode('utf-8')
    return (b'\xef\xbb\xbf' + encoded) if had_bom else encoded


def transform(relative, raw):
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    if relative == RUNTIME + 'M47/Runtime/EffectMeshBatcher.cs':
        text = adapt_batch_body(text)
    elif relative == EDITOR + 'EffectBatchVerification.cs':
        for year in ('74', '75'):
            text = replace_region(text, '// BEGIN FROZEN_CHECKPOINT' + year + '_EFFECT_BATCHER\n', '\n// END FROZEN_CHECKPOINT' + year + '_EFFECT_BATCHER')
        text = once(text, 'writer.Write(renderer.sharedMaterial.GetInstanceID());', 'writer.Write(renderer.sharedMaterial.GetEntityId().ToString());')
        text = once(text, 'writer.Write(texture?texture.GetInstanceID():0);', 'writer.Write(texture?texture.GetEntityId().ToString():string.Empty);')
        text = once(text, ' public static class EffectBatchVerification {\n', ' public static class EffectBatchVerification {\n' + csharp_normalizer())
        original74 = 'original=original.Replace("namespace HeartOfTheRain.M47 {","namespace HeartOfTheRain.Verification.Baseline74 {").Replace("EffectMeshBatcher","ArchivedEffectMeshBatcher74");'
        text = once(text, original74, original74 + 'original=AdaptArchivedEntityIdentity94(original);')
        original75 = '.Replace("EffectMeshBatcher","ArchivedEffectMeshBatcher75");'
        text = once(text, original75, original75 + 'original=AdaptArchivedEntityIdentity94(original);')
        text = once(text, 'Compiled native control is byte-for-byte archived74 body apart from namespace/type rename', 'Compiled native control matches raw-hash-bound archived74 with exact namespace/type and Unity6 EntityId API adapter')
        text = once(text, 'Compiled transform control matches archived75 body except namespace/type rename', 'Compiled transform control matches raw-hash-bound archived75 with exact namespace/type and Unity6 EntityId API adapter')
        text = once(text, 'output=Path.GetFullPath("../Verification/Evidence/EffectBatch/Native");', 'output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_UNITY6_94_OUT")??"../Verification/Evidence/EffectBatch/Native");')
        text = once(text, '[Serializable] public sealed class Report {\n', '[Serializable] public sealed class Report {\n   public string entityIdAdapterScope="Raw-hash-bound archived74/75 with exact Unity6 EntityId API port; same Unity6 renderer only, not cross-engine pixel or performance proof.";\n')
        text = once(text, 'Exact archived75 uploaded mesh/pixel comparisons,', 'Raw-hash-bound archived75 with exact Unity6 EntityId API port, uploaded mesh/pixel comparisons within the same Unity6 renderer,')
        text = once(text, 'Exact archived74 implementation is compiled only in Editor verification.', 'Raw-hash-bound archived74 plus exact Unity6 EntityId API port is compiled only in Editor verification.')
    elif relative == EDITOR + 'DenseSubmissionVerification.cs':
        text = replace_region(text, '// BEGIN EXACT77 EFFECT BATCHER\n', '\n// END EXACT77 EFFECT BATCHER')
        text = once(text, 'writer.Write(renderer.sharedMaterial.GetInstanceID());', 'writer.Write(renderer.sharedMaterial.GetEntityId().ToString());')
        text = once(text, 'writer.Write(texture?texture.GetInstanceID():0);', 'writer.Write(texture?texture.GetEntityId().ToString():string.Empty);')
        original = '.Replace("EffectMeshBatcher","ArchivedEffectMeshBatcher77");'
        text = once(text, original, original + 'original=EffectBatchVerification.AdaptArchivedEntityIdentity94(original);')
        text = once(text, 'Independent control changes only namespace/type names', 'Independent control matches raw-hash-bound archived77 with exact namespace/type and Unity6 EntityId API adapter')
        text = once(text, '[Serializable] public sealed class Report {\n', '[Serializable] public sealed class Report {\n   public string entityIdAdapterScope="Raw-hash-bound archived77 with exact Unity6 EntityId API port; same Unity6 renderer only, not cross-engine pixel or performance proof. compiledSourceMatchesArchive means the complete explicitly API-normalized body matches after the raw archive SHA check.";\n')
        text = once(text, 'Native Unity Editor exact archived77/same-APK control mesh state', 'Native Unity6 Editor raw-hash-bound archived77 with exact EntityId API port/same-APK control mesh state')
    elif relative == RUNTIME + 'Verification/Execution78Probe.cs':
        text = once(text, 'public string name;public int order,materialId,textureId;', 'public string name,materialId,textureId;public int order;')
        text = once(text, 'materialId=material?material.GetInstanceID():0', 'materialId=material?material.GetEntityId().ToString():string.Empty')
        text = once(text, 'textureId=texture?texture.GetInstanceID():0', 'textureId=texture?texture.GetEntityId().ToString():string.Empty')
    elif relative == RUNTIME + 'Verification/ProfileM71Verification.cs':
        text = once(text, 'int blurId=0;', 'EntityId blurId=default;')
        need(text.count('.GetInstanceID()') == 2, 'ProfileIdentityCountChanged')
        text = text.replace('.GetInstanceID()', '.GetEntityId()')
    elif relative == EDITOR + 'PresentationWarmupVerification.cs':
        text = once(text, 'static int[] ids;', 'static EntityId[] ids;')
        need(text.count('.GetInstanceID()') == 4, 'PresentationIdentityCountChanged')
        text = text.replace('.GetInstanceID()', '.GetEntityId()')
    elif relative == EDITOR + 'HomeLivesR1Review.cs':
        need(text.count('.GetInstanceID()') == 4, 'HomeLivesIdentityCountChanged')
        text = text.replace('.GetInstanceID()', '.GetEntityId()')
    else:
        need(relative.endswith(('/RocketSpritePlayer.cs', '/RenderedSpritePlayer.cs')), 'UnknownEntityIdFileRefused')
        text = once(text, 'static readonly Dictionary<string, SharedFrames> Cache = new Dictionary<string, SharedFrames>();',
                    'static readonly Dictionary<(EntityId atlas,EntityId manifest), SharedFrames> Cache = new Dictionary<(EntityId atlas,EntityId manifest), SharedFrames>();')
        text = once(text, 'string cacheKey;', '(EntityId atlas,EntityId manifest) cacheKey;')
        text = once(text, 'cacheKey = atlas.GetInstanceID() + ":" + manifest.GetInstanceID();',
                    'cacheKey = (atlas.GetEntityId(), manifest.GetEntityId());')
    if relative != EDITOR + 'EffectBatchVerification.cs':
        need('GetInstanceID()' not in text, 'UnconvertedObsoleteIdentityCall')
    return preserve_unmodified_line_bytes(raw, text)


def raw_archive_inputs(effect_before):
    import re
    match = re.search(r'frozenBaselineSourceSHA256=="([a-f0-9]{64})"', effect_before.decode('utf-8-sig'))
    need(match is not None, 'Raw74HashAssertionRequired')
    result = []
    for name, expected in ARCHIVES:
        if name == 'Gameplay75':
            need(expected == match.group(1), 'Raw74HashAssertionChanged')
        tail = Path('.verification-cache') / name / 'BaselineSources/Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs'
        source = ROOT / tail
        data = source.read_bytes()
        need(sha(data) == expected, 'RawArchivedSourceHashMismatch:' + name)
        result.append({'source': source, 'destination': PROJECT.parent / tail, 'sha256': expected, 'bytes': len(data), 'group': name})
    return result


def prove_adapted_references(changes, archives):
    lookup = {change['relative']: change['after'].decode('utf-8-sig').replace('\r\n', '\n') for change in changes}
    result = []
    for archive, number, namespace, type_name, target, begin, end in (
        (archives[0], '74', 'Baseline74', 'ArchivedEffectMeshBatcher74', EDITOR + 'EffectBatchVerification.cs', '// BEGIN FROZEN_CHECKPOINT74_EFFECT_BATCHER\n', '\n// END FROZEN_CHECKPOINT74_EFFECT_BATCHER'),
        (archives[1], '75', 'Baseline75', 'ArchivedEffectMeshBatcher75', EDITOR + 'EffectBatchVerification.cs', '// BEGIN FROZEN_CHECKPOINT75_EFFECT_BATCHER\n', '\n// END FROZEN_CHECKPOINT75_EFFECT_BATCHER'),
        (archives[2], '77', 'Submission77', 'ArchivedEffectMeshBatcher77', EDITOR + 'DenseSubmissionVerification.cs', '// BEGIN EXACT77 EFFECT BATCHER\n', '\n// END EXACT77 EFFECT BATCHER')):
        original = archive['source'].read_text('utf-8-sig').replace('\r\n', '\n')
        original = original[original.index('namespace HeartOfTheRain.M47 {'):].strip()
        original = original.replace('namespace HeartOfTheRain.M47 {', 'namespace HeartOfTheRain.Verification.' + namespace + ' {').replace('EffectMeshBatcher', type_name)
        adapted = adapt_batch_body(original)
        own = lookup[target]
        compiled = own[own.index(begin) + len(begin):own.index(end)].strip()
        need(compiled == adapted, 'AdaptedCompiledReferenceMismatch:' + number)
        # A non-API source edit remains visible to the complete-body comparison.
        tampered = adapted.replace('Quads++;', 'Quads+=2;', 1)
        need(tampered != compiled, 'UnexpectedBodyEditNegativeControlFailed')
        result.append({'checkpoint': number, 'rawArchiveSHA256': archive['sha256'], 'adaptedBodySHA256': sha(adapted.encode()), 'fullCompiledBodyMatchesExactAdapter': True, 'nonApiBodyChangeRejected': True})
    return result


def prepare(out):
    guards = module('entity94_path_guards', Path(__file__).with_name('adapt_test_pins.py'))
    native = module('entity94_candidate_reader', Path(__file__).with_name('run_native.py'))
    guards.exact_project(PROJECT)
    out = guards.fresh_output(out)
    api = guards.shared()
    baseline = guards.load_baseline()
    need(api.freeze() == baseline, 'ProtectedMainBaselineChanged')
    changes = []
    for relative in FILES:
        source, target = ROOT / 'Unity' / relative, PROJECT / relative
        guards.reject_links(source)
        guards.reject_links(target)
        before = target.read_bytes()
        expected = baseline['files']['Unity/' + relative]
        need(before == source.read_bytes() and sha(before) == expected['sha256'], 'ExactUneditedMainAndCandidateFileRequired:' + relative)
        changes.append({'relative': relative, 'before': before, 'after': transform(relative, before)})
    archives = raw_archive_inputs(next(row['before'] for row in changes if row['relative'] == EDITOR + 'EffectBatchVerification.cs'))
    for archive in archives:
        guards.reject_links(archive['source'])
        guards.reject_links(archive['destination'])
        need(not archive['destination'].exists(), 'FreshArchivedSourceStageRequired')
    proofs = prove_adapted_references(changes, archives)
    out.mkdir(parents=True, exist_ok=False)
    api.write(out / 'MainSources_before.json', baseline)
    api.write(out / 'CandidateSources_before.json', native.candidate_sources(api))
    report = {'schemaVersion': 1, 'status': 'PREPARED_ENTITYID_API94_REQUIRES_ROOT_APPLICATION', 'utc': api.utc(),
              'runnerSHA256': sha(Path(__file__).read_bytes()), 'mainInputsUnchanged': True, 'candidateNotMutated': True,
              'scope': 'Read-only candidate preparation. Exact9-file full-opaque EntityId compatibility port with no geometry/timing/model/rule changes. Full equality of EntityId+order controls grouping; a hash only selects dictionary buckets. Runtime caches retain full identity, diagnostics serialize opaque ToString. Original archived SHA assertions remain and complete normalized bodies are compared; no assertions removed. Root must review diffs and explicitly apply. No Unity/ADB/backend execution.',
              'referenceProofs': proofs, 'changes': [], 'rawArchivesToStage': [],
              'officialApiReference': 'https://docs.unity3d.com/6000.6/Documentation/ScriptReference/EntityId.html'}
    for change in changes:
        for label in ('before', 'after'):
            path = out / label / change['relative']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(change[label])
        patch = out / 'diffs' / (Path(change['relative']).name + '.diff')
        patch.parent.mkdir(parents=True, exist_ok=True)
        difference = ''.join(difflib.unified_diff(change['before'].decode('utf-8-sig').splitlines(True), change['after'].decode('utf-8-sig').splitlines(True), fromfile='before/' + change['relative'], tofile='after/' + change['relative']))
        with patch.open('x', encoding='utf-8', newline='') as stream:
            stream.write(difference)
        report['changes'].append({'path': change['relative'], 'beforeSHA256': sha(change['before']), 'afterSHA256': sha(change['after']), 'diff': patch.relative_to(ROOT).as_posix()})
    for archive in archives:
        report['rawArchivesToStage'].append({key: value.relative_to(ROOT).as_posix() if isinstance(value, Path) else value for key, value in archive.items()})
    need(api.freeze() == baseline, 'ProtectedMainChangedWhilePreparing')
    api.write(out / 'Preparation.json', report)
    print(json.dumps({'status': report['status'], 'files': len(changes), 'references': len(proofs), 'preparation': (out / 'Preparation.json').relative_to(ROOT).as_posix()}), flush=True)


def apply(prepared):
    guards = module('entity94_apply_guards', Path(__file__).with_name('adapt_test_pins.py'))
    native = module('entity94_apply_candidate_reader', Path(__file__).with_name('run_native.py'))
    guards.exact_project(PROJECT)
    prepared = Path(prepared).resolve()
    need(prepared.is_relative_to(OUT) and prepared.name == 'Preparation.json', 'ContainedEntityPreparationRequired')
    guards.reject_links(prepared)
    data = json.loads(prepared.read_text('utf-8-sig'))
    need(data.get('status') == 'PREPARED_ENTITYID_API94_REQUIRES_ROOT_APPLICATION' and data.get('runnerSHA256') == sha(Path(__file__).read_bytes()), 'ExactPreparedEntityIdToolRequired')
    need([row['path'] for row in data['changes']] == list(FILES), 'ExactNineEntityIdFilesRequired')
    need(not (prepared.parent / 'Application.json').exists(), 'PreviousEntityIdApplicationPreserved')
    api = guards.shared()
    baseline = guards.load_baseline()
    need(api.freeze() == baseline, 'ProtectedMainBaselineChanged')
    need(native.candidate_sources(api) == json.loads((prepared.parent / 'CandidateSources_before.json').read_text('utf-8-sig')), 'CandidateChangedSinceEntityPreparation')
    for change in data['changes']:
        relative = change['path']
        target, before, after = PROJECT / relative, prepared.parent / 'before' / relative, prepared.parent / 'after' / relative
        for path in (target, before, after):
            guards.reject_links(path)
        need(target.read_bytes() == before.read_bytes() and sha(before.read_bytes()) == change['beforeSHA256'] and sha(after.read_bytes()) == change['afterSHA256'], 'EntityPreparedBytesChanged')
    for archive in data['rawArchivesToStage']:
        source, destination = ROOT / archive['source'], ROOT / archive['destination']
        guards.reject_links(source)
        guards.reject_links(destination)
        need(destination.resolve().is_relative_to(PROJECT.parent / '.verification-cache') and not destination.exists() and sha(source.read_bytes()) == archive['sha256'], 'EntityRawArchiveStageGuardFailed')
    receipt = {'schemaVersion': 1, 'status': 'RUNNING_ROOT_ENTITYID_API94_APPLICATION', 'startedUtc': api.utc(), 'preparationSHA256': sha(prepared.read_bytes()), 'runnerSHA256': sha(Path(__file__).read_bytes()), 'applied': [], 'stagedRawArchives': []}
    try:
        for change in data['changes']:
            target = PROJECT / change['path']
            temporary = target.with_name(target.name + '.entity94.tmp')
            guards.reject_links(temporary)
            with temporary.open('xb') as stream:
                stream.write((prepared.parent / 'after' / change['path']).read_bytes())
            os.replace(temporary, target)
            need(sha(target.read_bytes()) == change['afterSHA256'], 'EntityAppliedBytesMismatch')
            receipt['applied'].append(change)
        for archive in data['rawArchivesToStage']:
            source, destination = ROOT / archive['source'], ROOT / archive['destination']
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                stream.write(source.read_bytes())
            need(sha(destination.read_bytes()) == archive['sha256'] and destination.stat().st_nlink == 1, 'EntityRawArchiveStageMismatch')
            receipt['stagedRawArchives'].append(archive)
        receipt['status'] = 'PASS_ROOT_ISOLATED_ENTITYID_API94_APPLICATION'
    except Exception as error:
        receipt.update(status='FAIL_ROOT_ISOLATED_ENTITYID_API94_APPLICATION', errorType=type(error).__name__)
        raise
    finally:
        after = api.freeze()
        receipt.update(mainInputsUnchanged=after == baseline, finishedUtc=api.utc())
        api.write(prepared.parent / 'MainSources_after.json', after)
        api.write(prepared.parent / 'CandidateSources_after.json', native.candidate_sources(api))
        if after != baseline:
            receipt['status'] = 'FAIL_ENTITYID_API94_MAIN_SOURCE_PRESERVATION'
        api.write(prepared.parent / 'Application.json', receipt)
    print(json.dumps({'status': receipt['status'], 'files': len(receipt['applied']), 'rawArchives': len(receipt['stagedRawArchives']), 'mainInputsUnchanged': receipt['mainInputsUnchanged']}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'apply'))
    parser.add_argument('--out', type=Path)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        need(args.out is not None and args.prepared is None and not args.execute, 'ReadOnlyPrepareRequiresOnlyOut')
        prepare(args.out)
    else:
        need(args.execute and os.name == 'nt' and args.prepared is not None and args.out is None, 'RootWindowsApplyRequiresExplicitExecute')
        apply(args.prepared)


if __name__ == '__main__':
    main()
