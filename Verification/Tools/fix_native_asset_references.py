"""Repair only PPtr type tags for GUIDs resolving to native .asset/.mat files.

Default is a dry run. Imported-file assets (scripts, textures, audio, etc.) keep
their type=3 references. GUIDs, file IDs, object data and .meta files are retained.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    unity = ROOT / 'Unity'
    guid_paths = {}
    for meta in (unity/'Assets').rglob('*.meta'):
        match = re.search(r'^guid: ([0-9a-f]{32})$',meta.read_text(encoding='utf-8-sig'),re.M)
        if match: guid_paths[match[1]] = Path(str(meta)[:-5])
    changes = []
    pattern = re.compile(r'(guid: ([0-9a-f]{32})[,\s]*type:\s*)3\b')
    for path in (unity/'Assets').rglob('*'):
        if path.suffix not in ('.asset','.unity','.prefab','.mat'): continue
        text = path.read_bytes().decode('utf-8')
        def replace(match):
            target = guid_paths.get(match[2])
            if target is None or target.suffix not in ('.asset','.mat'): return match[0]
            changes.append({'owner':path.relative_to(unity).as_posix(),'target':target.relative_to(unity).as_posix(),'guid':match[2],'before_type':3,'after_type':2})
            return match[1]+'2'
        fixed = pattern.sub(replace,text)
        if fixed != text and args.apply: path.write_bytes(fixed.encode('utf-8'))
    report = {'mode':'APPLIED' if args.apply else 'DRY_RUN','reference_count':len(changes),'file_count':len({c['owner'] for c in changes}),'changes':changes}
    output = ROOT/'Verification/Evidence/Native'/('Native_Reference_Repair.json' if args.apply else 'Native_Reference_Repair_DryRun.json')
    if args.apply and output.exists():
        output = output.with_name('Native_Reference_Repair_Latest.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=2))


if __name__ == '__main__': run()
