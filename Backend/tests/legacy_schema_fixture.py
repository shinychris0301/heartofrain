"""Build an exact historic schema and copy only columns it actually contained.

Test fixtures must not relabel a current schema with an old version number.
This helper is never loaded by the backend or used for production downgrades.
"""
import json

from hotr_backend.operations import _expected


def copy_legacy(source, target, version):
    objects = _expected(version)
    for kind in ('table', 'index'):
        for typ, _, _, sql in objects:
            if typ == kind:
                target.execute(sql)
    if version < 9:
        columns = {row[1] for row in source.execute('PRAGMA table_info(commerce_orders)')}
        if 'grant_json' in columns:
            for grant, limit, released in source.execute('SELECT grant_json,purchase_limit,reservation_released FROM commerce_orders'):
                value = json.loads(grant) if grant else {}
                if limit is not None or released or value.get('stars') or any(value.get('starting', [])) or any(value.get('tools', [])):
                    raise ValueError('Full-inventory/policy orders did not exist in legacy schemas')
    for typ, table, _, _ in objects:
        if typ != 'table' or table == 'schema_info':
            continue
        columns = [row[1] for row in target.execute('PRAGMA table_info(' + table + ')')]
        names = ','.join(columns)
        for row in source.execute('SELECT ' + names + ' FROM ' + table):
            target.execute('INSERT INTO ' + table + '(' + names + ') VALUES(' + ','.join('?' for _ in row) + ')', tuple(row))
    target.execute('INSERT INTO schema_info VALUES(?)', (version,))
    target.commit()
