"""Read-only exact JSON token diagnostics. Never changes raw-hash acceptance."""
from decimal import Decimal
import json
import math
import struct


class Number:
    def __init__(self, token):
        self.token = token


def parsed(raw):
    def constant(value):
        raise ValueError('NonFiniteJSONNumberForbidden:' + value)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('DuplicateJSONObjectKeyForbidden:' + key)
            result[key] = value
        return result
    return json.loads(raw, parse_int=Number, parse_float=Number, parse_constant=constant,
                      object_pairs_hook=pairs)


def number_detail(left, right, path):
    a, b = left.token, right.token
    result = {'path': path, 'baselineToken': a, 'candidateToken': b,
              'exactDecimalEqual': Decimal(a) == Decimal(b),
              'binary64BitsEqual': struct.pack('>d', float(a)) == struct.pack('>d', float(b))}
    # Observational bit comparison only. No epsilon, rounding acceptance or raw-hash waiver.
    if any(character in token for token in (a, b) for character in '.eE'):
        try:
            old, new = struct.pack('>f', float(a)), struct.pack('>f', float(b))
            result.update(binary32BaselineBits=old.hex(), binary32CandidateBits=new.hex(),
                          binary32BitsEqual=old == new,
                          binary32BaselineExactValue=str(Decimal.from_float(struct.unpack('>f', old)[0])),
                          binary32CandidateExactValue=str(Decimal.from_float(struct.unpack('>f', new)[0])))
        except (OverflowError, ValueError):
            result['binary32Representable'] = False
    return result


def compare(left_raw, right_raw):
    left, right = parsed(left_raw), parsed(right_raw)
    numeric, structural, ordering = [], [], []

    def walk(a, b, path):
        if isinstance(a, Number) and isinstance(b, Number):
            if a.token != b.token:
                numeric.append(number_detail(a, b, path))
            return
        if type(a) is not type(b):
            structural.append({'path': path, 'reason': 'JSON value type changed'})
        elif isinstance(a, dict):
            if set(a) != set(b):
                structural.append({'path': path, 'reason': 'Object keys changed',
                                   'baselineKeys': list(a), 'candidateKeys': list(b)})
            elif list(a) != list(b):
                ordering.append({'path': path, 'baselineKeys': list(a), 'candidateKeys': list(b)})
            for key in a.keys() & b.keys():
                walk(a[key], b[key], path + '/' + key.replace('~', '~0').replace('/', '~1'))
        elif isinstance(a, list):
            if len(a) != len(b):
                structural.append({'path': path, 'reason': 'Array length changed',
                                   'baselineLength': len(a), 'candidateLength': len(b)})
            for index, (old, new) in enumerate(zip(a, b)):
                walk(old, new, path + '/' + str(index))
        elif a != b:
            structural.append({'path': path, 'reason': 'Non-number scalar changed',
                               'baseline': a, 'candidate': b})

    walk(left, right, '')
    numeric.sort(key=lambda row: row['path'])
    structural.sort(key=lambda row: row['path'])
    ordering.sort(key=lambda row: row['path'])
    return {'rawBytesEqual': left_raw == right_raw, 'numericTokenDifferences': numeric,
            'structuralOrNonNumericDifferences': structural, 'objectOrderDifferences': ordering,
            'exactDecimalScalarsEqual': not structural and all(row['exactDecimalEqual'] for row in numeric),
            'allDifferentNumericTokensHaveIdenticalBinary32Bits': bool(numeric) and all(
                row.get('binary32BitsEqual') is True for row in numeric),
            'scope': 'Exact decimal lexical/value differences remain differences. Binary32 bits are a separate diagnostic, not raw JSON parity, scalar tolerance, backend compatibility or release acceptance.'}
