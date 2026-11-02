"""Bound read-only analysis of actual L1 or350-command two-engine native exports."""
import argparse
import collections
import json
from pathlib import Path
import re

import model_payload94 as base
import diagnose_json94 as diagnostic
import compare_model94 as historical


def need(value, code):
    base.need(value, code)


def analyze(invocation, output):
    api, _, _, _, guards = base.readers()
    invocation = Path(invocation).resolve(); output = guards.fresh_output(output)
    need(invocation.name == 'Invocation.json' and invocation.is_relative_to(base.OUT), 'Analysis94ActualContainedInvocationRequired')
    receipt = historical.read(invocation)
    need(receipt.get('status') in ('RECORDED_ACTUAL_TWO_ENGINE_PAYLOAD94_REQUIRES_ANALYSIS', 'RECORDED_ACTUAL_TWO_ENGINE_CORPUS94_REQUIRES_ANALYSIS')
         and receipt.get('mainInputsUnchanged') is True and receipt.get('candidateInputsUnchanged') is True
         and receipt.get('unityPidsAfter') == [] and len(receipt.get('runs', [])) == 2, 'Analysis94PassedActualTwoEngineCollectionRequired')
    corpus = 'CORPUS94' in receipt['status']
    def bound(path):
        return {'path': path.relative_to(base.ROOT).as_posix(), 'sha256': api.sha(path), 'bytes': path.stat().st_size}
    documents = {}
    bindings = [bound(invocation)]
    for row, (name, version, _) in zip(receipt['runs'], base.TARGETS):
        directory = invocation.parent / name; report_path = directory / 'Native.json'; log = directory / 'Unity.log'
        need(row.get('name') == name and row.get('expectedUnity') == version and row.get('exitCode') == 0
             and row.get('actualEngineVersionFromLog') == version and row.get('unityPidsAfter') == [], 'Analysis94ActualProcessIdentityRequired')
        need((bound(report_path) == row['nativeReport'] and bound(log) == row['unityLog']) if corpus
             else (api.sha(report_path) == row['nativeReportSHA256'] and api.sha(log) == row['unityLogSHA256']), 'Analysis94ActualProcessBindingChanged')
        match = re.search(r'Initialize engine version:\s*(\S+)', log.read_text('utf-8-sig', errors='replace'))
        native = historical.read(report_path)
        need(match is not None and match.group(1) == version == native.get('unity'), 'Analysis94LogAndNativeEngineRequired')
        need(native.get('status') == ('PASS_ACTUAL_SERIALIZATION_CORPUS94' if corpus else 'PASS_ACTUAL_SERIALIZATION_PAYLOAD94') and not native.get('error'), 'Analysis94PassedNativeExportRequired')
        rows = native['rows'] if corpus else [{'name': 'L1_match', 'payloads': native['payloads']}]
        need(len(rows) == (350 if corpus else 1) and len({item['name'] for item in rows}) == len(rows), 'Analysis94UniqueCompleteRowsRequired')
        documents[name] = {item['name']: item for item in rows}
        bindings.extend([bound(report_path), bound(log)])
    need(set(documents['Baseline2022']) == set(documents['Candidate6']), 'Analysis94SameNamedRowsRequired')
    output.mkdir(parents=True, exist_ok=False)
    pairs = []; totals = collections.Counter(); types = collections.defaultdict(collections.Counter)
    for name in sorted(documents['Baseline2022'], key=lambda name: (int(name.split('_')[0][1:]), name)):
        old, new = documents['Baseline2022'][name], documents['Candidate6'][name]
        a, b = ({item['name']: item for item in row['payloads']} for row in (old, new))
        need(set(a) == set(b) and len(a) == (3 if corpus else 11), 'Analysis94CompleteUniquePayloadSetRequired')
        details = []
        for payload_name in sorted(a):
            left = invocation.parent / 'Baseline2022' / a[payload_name]['file']
            right = invocation.parent / 'Candidate6' / b[payload_name]['file']
            need(left.parent == invocation.parent / 'Baseline2022' and right.parent == invocation.parent / 'Candidate6', 'Analysis94OnlyRecordedPayloadPathsRequired')
            for path, item in ((left, a[payload_name]), (right, b[payload_name])):
                need(api.sha(path) == item['sha256'] and path.stat().st_size == item['bytes'], 'Analysis94RawPayloadBindingChanged')
            result = diagnostic.compare(left.read_bytes(), right.read_bytes())
            detail = {'name': payload_name, 'baseline': bound(left), 'candidate': bound(right), **result}
            if corpus:
                fields = ('typedSHA256', 'typedNodes', 'typedFields', 'float32Values', 'float64Values', 'traversedTypes')
                need(all(field in a[payload_name] and field in b[payload_name] for field in fields), 'Analysis94NativeTypedCoverageRequired')
                detail['nativeTypedSignatureEqual'] = a[payload_name]['typedSHA256'] == b[payload_name]['typedSHA256']
                detail['nativeTypedCoverageEqual'] = all(a[payload_name][field] == b[payload_name][field] for field in fields[1:])
                detail['baselineTypedCoverage'] = {field: a[payload_name][field] for field in fields}
                detail['candidateTypedCoverage'] = {field: b[payload_name][field] for field in fields}
            details.append(detail)
            counts = {'pairs': 1, 'rawBytesEqual': int(result['rawBytesEqual']),
                      'exactDecimalScalarsEqual': int(result['exactDecimalScalarsEqual']),
                      'numericTokenDifferences': len(result['numericTokenDifferences']),
                      'structuralOrNonNumericDifferences': len(result['structuralOrNonNumericDifferences']),
                      'objectOrderDifferences': len(result['objectOrderDifferences']),
                      'changedNumericTokensWithDifferentBinary32Bits': sum(item.get('binary32BitsEqual') is not True for item in result['numericTokenDifferences'])}
            if corpus:
                counts.update(nativeTypedSignatureEqual=int(detail['nativeTypedSignatureEqual']), nativeTypedCoverageEqual=int(detail['nativeTypedCoverageEqual']))
            totals.update(counts); types[payload_name].update(counts)
        record = {'name': name, 'payloads': details}
        path = output / (name + '.json'); api.write(path, record)
        pairs.append({'name': name, 'diagnostic': bound(path)})
    aggregate = {'schemaVersion': 1, 'status': 'RECORDED_EXACT_SERIALIZATION_DIAGNOSTIC94_WITH_RAW_DIFFERENCES',
                 'utc': api.utc(), 'runnerSHA256': api.sha(Path(__file__)), 'diagnosticSHA256': api.sha(Path(diagnostic.__file__)),
                 'scope': 'Bound actual native payloads only. Exact decimal scalar differences remain differences; binary32 identity and native complete typed signatures are independent diagnostics, never a raw-hash waiver. No backend execution, universal model equivalence, pixel/performance/device or production acceptance.',
                 'inputBindings': bindings, 'commandRows': len(pairs), 'totals': dict(totals),
                 'byPayloadType': {key: dict(value) for key, value in types.items()}, 'rows': pairs,
                 'strictRawJSONParityPassed': totals['rawBytesEqual'] == totals['pairs']}
    api.write(output / 'Analysis.json', aggregate)
    print(json.dumps({'status': aggregate['status'], 'commandRows': len(pairs), 'totals': dict(totals),
                      'report': (output / 'Analysis.json').relative_to(base.ROOT).as_posix()}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--invocation', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True); args = parser.parse_args(); analyze(args.invocation, args.out)


if __name__ == '__main__': main()
