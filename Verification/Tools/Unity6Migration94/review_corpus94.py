"""Independent read-only recheck of completed94 native corpus and token diagnostics."""
import argparse
import collections
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import struct

import model_payload94 as base


def require(value, reason):
    if not value:
        raise ValueError(reason)


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path):
    return {'path': path.resolve().relative_to(base.ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def check_binding(item):
    path = (base.ROOT / item['path']).resolve()
    require(path.is_relative_to(base.ROOT) and binding(path) == item, 'Independent94BoundInputChanged')
    return path


def independent_values(a, b):
    """Separate decoder/traversal; never calls diagnose_json94.compare or rounds values."""
    def pairs(items):
        keys = [key for key, _ in items]
        require(len(set(keys)) == len(keys), 'Independent94DuplicateJSONKey')
        return dict(items)
    def reject(token):
        raise ValueError('Independent94NonFiniteJSON:' + token)
    options = dict(parse_int=lambda text: ('integer', text), parse_float=lambda text: ('float', text),
                   object_pairs_hook=pairs, parse_constant=reject)
    left, right = json.loads(a, **options), json.loads(b, **options)
    counts = collections.Counter()
    examples = []
    def walk(old, new, path):
        counts['visitedJSONValues'] += 1
        require(type(old) is type(new), 'Independent94JSONTypeChanged:' + path)
        if isinstance(old, tuple):
            require(old[0] == new[0], 'Independent94JSONNumericKindChanged:' + path)
            if old[1] != new[1]:
                counts['numericLexicalDifferences'] += 1
                if Decimal(old[1]) != Decimal(new[1]): counts['exactDecimalValueDifferences'] += 1
                require(old[0] == 'float', 'Independent94IntegerChanged:' + path)
                old_bits, new_bits = struct.pack('<f', float(old[1])), struct.pack('<f', float(new[1]))
                require(old_bits == new_bits, 'Independent94Binary32ValueChanged:' + path)
                counts['differentTokensWithIdenticalBinary32'] += 1
                if len(examples) < 3: examples.append({'path': path, 'baseline': old[1], 'candidate': new[1], 'binary32BitsLittleEndian': old_bits.hex()})
        elif isinstance(old, dict):
            require(list(old) == list(new), 'Independent94ObjectKeysOrOrderChanged:' + path)
            for key in old: walk(old[key], new[key], path + '/' + key)
        elif isinstance(old, list):
            require(len(old) == len(new), 'Independent94ArrayLengthChanged:' + path)
            for index, (x, y) in enumerate(zip(old, new)): walk(x, y, path + '/' + str(index))
        else:
            require(old == new, 'Independent94NonNumericValueChanged:' + path)
    walk(left, right, '')
    return counts, examples


def review(invocation, analysis, output):
    api, _, _, _, guards = base.readers()
    invocation, analysis = Path(invocation).resolve(), Path(analysis).resolve()
    output = guards.fresh_output(output)
    require(invocation.is_relative_to(base.OUT / 'SerializationCorpus') and invocation.name == 'Invocation.json', 'Independent94ActualCorpusInvocationRequired')
    require(analysis.is_relative_to(base.OUT / 'Compatibility') and analysis.name == 'Analysis.json', 'Independent94RecordedAnalysisRequired')
    run, summary = read(invocation), read(analysis)
    require(run['status'] == 'RECORDED_ACTUAL_TWO_ENGINE_CORPUS94_REQUIRES_ANALYSIS' and run['mainInputsUnchanged'] and run['candidateInputsUnchanged']
            and run['unityPidsAfter'] == [] and len(run['runs']) == 2, 'Independent94SuccessfulCollectionRequired')
    require(summary['commandRows'] == 350 and summary['strictRawJSONParityPassed'] is False, 'Independent94RawFailureMustRemain')
    for item in summary['inputBindings']: check_binding(item)
    require(binding(invocation) in summary['inputBindings'], 'Independent94AnalysisInvocationBindingRequired')
    prepared = read(check_binding(run['preparation']))
    require(prepared['status'] == 'PASS_CORPUS94_PREPARATION', 'Independent94PreparedProjectsRequired')
    template = check_binding(prepared['template']); text = template.read_text('utf-8-sig')
    require(text.count('different(') == 8 and 'SignatureControls(report);' in text and 'report.typedNegativeControls++' in text,
            'Independent94EightNativeNegativeControlsRequired')
    require('Typed94 refuses untraversed private serialized field' in text and 'BindingFlags.Public|BindingFlags.Instance' in text
            and '!f.IsStatic&&!f.IsNotSerialized' in text and 'writer.Write((float)value)' in text and 'writer.Write((double)value)' in text,
            'Independent94CompleteTypedTraversalRequired')
    original = read(check_binding(prepared['originalPreparation']))
    projects = {}; native = {}; evidence = [binding(invocation), binding(analysis), binding(template), binding(check_binding(run['preparation']))]
    for item in original['projects']:
        source_manifest = base.ROOT / item['sources']
        require(sha(source_manifest) == item['sourcesSHA256'], 'Independent94OriginalProbeManifestChanged')
        project = base.relative_project(base.PROBES / item['name'])
        for relative, bound in read(source_manifest)['files'].items():
            require(sha(project / relative) == bound['sha256'], 'Independent94OriginalProbeSourceChanged')
        projects[item['name']] = project
    for addition in prepared['projects']:
        project = projects[addition['name']]
        for relative, bound in addition['addedFiles'].items():
            require(sha(project / relative) == bound['sha256'], 'Independent94CorpusProbeInputChanged')
    names = {'L'+str(level)+'_'+kind for level in range(1,51) for kind in ('match','power4','power5','power7','power11','power16','power21')}
    references = {}
    for kind in ('baselineCorpus', 'candidateCorpus'):
        report_path = check_binding(run[kind]); rows = read(report_path)['rows']
        require(len(rows) == 350 and {row['name'] for row in rows} == names, 'Independent94Original350CorpusRequired')
        references[kind] = {row['name']: row for row in rows}; evidence.append(binding(report_path))
    controls = []
    for row, (name, version, _) in zip(run['runs'], base.TARGETS):
        report_path, log_path = check_binding(row['nativeReport']), check_binding(row['unityLog'])
        result = read(report_path); log = log_path.read_text('utf-8-sig', errors='replace')
        require(row['name'] == name and row['status'] == 'PASS_ACTUAL_NATIVE_CORPUS94' and row['exitCode'] == 0
                and row['unityPidsAfter'] == [] and row['actualEngineVersionFromLog'] == version == result['unity']
                and re.search(r'Initialize engine version:\s*'+re.escape(version), log), 'Independent94ActualEngineProcessRequired')
        require(result['status'] == 'PASS_ACTUAL_SERIALIZATION_CORPUS94' and not result['error'] and result['typedNegativeControls'] == 8,
                'Independent94AllNativeTypedCounterexamplesMustPass')
        require(len(result['rows']) == 350 and {item['name'] for item in result['rows']} == names, 'Independent94UniqueComplete350NativeRowsRequired')
        require(result['explicitBaselineCommands'] is (name == 'Candidate6'), 'Independent94ActualBaselineCommandControlRequired')
        native[name] = {item['name']: item for item in result['rows']}
        controls.append({'engine': version, 'nativeChecks': result['checks'], 'negativeControlsPassed': 8, 'explicitNonSerializedControlPassed': True})
        evidence.extend([binding(report_path), binding(log_path)])
    analysis_rows = {row['name']: row for row in summary['rows']}
    require(len(summary['rows']) == 350 and set(analysis_rows) == names, 'Independent94Complete350DiagnosticRowsRequired')
    totals = collections.Counter(); types = collections.Counter(); commands = []
    for name in sorted(names):
        old, new = native['Baseline2022'][name], native['Candidate6'][name]
        fields = ('name','levelSHA256','level','kind','seed','ax','ay','bx','by','sourceId','accepted')
        require(all(old[field] == new[field] for field in fields) and old['accepted'], 'Independent94CommandChanged')
        authored = base.ROOT / ('Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L'+str(old['level']).zfill(3)+'.json')
        require(sha(authored) == old['levelSHA256'], 'Independent94AuthoredInputChanged')
        a, b = ({item['name']: item for item in row['payloads']} for row in (old, new))
        require(len(old['payloads']) == len(new['payloads']) == 3 and set(a) == set(b) == {'RawTurn','FinalSnapshot','FinalCheckpoint'}, 'Independent94ThreePayloadsRequired')
        detail_path = check_binding(analysis_rows[name]['diagnostic']); details = {row['name']: row for row in read(detail_path)['payloads']}
        command = {'name': name, 'payloads': []}
        for payload in a:
            x,y = a[payload],b[payload]
            left = invocation.parent/'Baseline2022'/x['file']; right = invocation.parent/'Candidate6'/y['file']
            require(x['file'] == y['file'] == name+'_'+payload+'.json', 'Independent94PayloadNameMismatch')
            for path, bound in ((left,x),(right,y)):
                require(sha(path) == bound['sha256'] and path.stat().st_size == bound['bytes'], 'Independent94RawPayloadChanged')
            require(binding(left) == details[payload]['baseline'] and binding(right) == details[payload]['candidate'], 'Independent94DiagnosticRawBindingChanged')
            typed = ('typedSHA256','typedNodes','typedFields','float32Values','float64Values','traversedTypes')
            require(all(x[key] == y[key] for key in typed) and re.fullmatch('[a-f0-9]{64}',x['typedSHA256'])
                    and x['typedNodes'] > 0 and x['typedFields'] > 0, 'Independent94TypedValueOrCoverageMismatch')
            for model in x['traversedTypes']: types[model] += 1
            if payload in ('RawTurn','FinalSnapshot'):
                key = 'turnHash' if payload == 'RawTurn' else 'finalHash'
                require(x['sha256'] == references['baselineCorpus'][name][key] and y['sha256'] == references['candidateCorpus'][name][key], 'Independent94NativeReferenceHashMismatch')
            raw_equal = left.read_bytes() == right.read_bytes()
            require(raw_equal is (payload != 'RawTurn'), 'Independent94UnexpectedRawParityResult')
            counts, examples = independent_values(left.read_bytes(), right.read_bytes())
            require(counts['numericLexicalDifferences'] == len(details[payload]['numericTokenDifferences']), 'Independent94NumericDifferenceCountMismatch')
            require(details[payload]['structuralOrNonNumericDifferences'] == details[payload]['objectOrderDifferences'] == [], 'Independent94OriginalDiagnosticHasStructuralDifference')
            totals.update(counts); totals['payloadPairs'] += 1; totals['rawByteEqualPairs'] += int(raw_equal); totals['typedSignaturesAndCoverageEqual'] += 1
            totals['runtimeFloat32ValuesTraversed'] += x['float32Values']; totals['runtimeFloat64ValuesTraversed'] += x['float64Values']
            command['payloads'].append({'name':payload,'rawBytesEqual':raw_equal,'typedSHA256':x['typedSHA256'],**dict(counts),'examples':examples})
        commands.append(command)
    require(totals['numericLexicalDifferences'] == summary['totals']['numericTokenDifferences'] == 20788
            and totals['rawByteEqualPairs'] == 700 and totals['typedSignaturesAndCoverageEqual'] == 1050,
            'Independent94AggregateMismatch')
    report = {'schemaVersion':1,'status':'PASS_INDEPENDENT_REVIEW_OF_SCOPED_MODEL_VALUES94_WITH_RAW_HASH_FAILURE',
              'utc':api.utc(),'reviewerSHA256':sha(Path(__file__)),'evidence':evidence,'nativeControls':controls,
              'commandRows':350,'totals':dict(totals),'traversedTypes':dict(sorted(types.items())),
              'strictRawTurnHashGate':'FAIL:0/350 exact raw turn hashes match; retained without waiver',
              'finalSnapshotByteParity':'PASS:350/350','finalCheckpointByteParity':'PASS:350/350',
              'engineeringConclusion':'No gameplay/runtime or trusted-backend code fix is justified by these sampled differences. All compared runtime values are bit-identical and all final checkpoint bytes match. Differences are confined to decimal JSON spelling of unchanged float32 values in RawTurn. Keep exact raw hashes distinct across these engine outputs; do not change worker pins or relax existing assertions.',
              'limits':'Only50 authored initial boards times one first legal match and six injected power taps at their authored seed. No arbitrary seeds, full50-level playthrough, repeated turns, tools, mixed swaps, Continue transactions, live client/server execution, payments/social/provider/Android/render/performance or universal wire-compatibility certification.',
              'commands':commands}
    output.mkdir(parents=True,exist_ok=False); api.write(output/'Review.json',report)
    print(json.dumps({'status':report['status'],'totals':dict(totals),'report':(output/'Review.json').relative_to(base.ROOT).as_posix()}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--invocation',type=Path,required=True)
    parser.add_argument('--analysis',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();review(args.invocation,args.analysis,args.out)


if __name__=='__main__': main()
