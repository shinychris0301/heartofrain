"""Archive Unity's importer round-trip output, then restore untouched metadata.

Run only after all native processes for this project have exited. The eight
intentional importer repairs are retained. Existing GUID identities must match.
"""
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITY = ROOT/'Unity'
OUT = ROOT/'Verification/Evidence/Native'
KEEP = {f'Assets/HeartOfTheRain/Boosters/Art/{name}.png.meta' for name in ['Hammer','Axe','Ram','Atlas']}
KEEP |= {f'Assets/HeartOfTheRain/M48/Resources/M48Textures/{key}.png.meta' for key in ['f4ce374da888522e9288484b5dae5dba','f44c77824d335b809727a40c1f959328','3480806884cb56aa933ca17ce9b45445','fd609f3080c0539db8f5bdc2a7289fa7']}


def sha(body): return hashlib.sha256(body).hexdigest()
def guid(body): return re.search(rb'(?m)^guid: ([0-9a-f]{32})',body)[1].decode()


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',default='',help='Keep a separate snapshot/report for a later verification run.')
    label=parser.parse_args().label
    if label and not re.fullmatch(r'[A-Za-z0-9_]+',label): raise ValueError('Use an alphanumeric snapshot label.')
    suffix='_'+label if label else ''
    expected = json.loads((ROOT/'Unity_Files_SHA256.json').read_text(encoding='utf-8-sig'))
    changes = []
    restores = []
    OUT.mkdir(parents=True,exist_ok=True)
    archive_path = OUT/('Imported_Metadata_Snapshot'+suffix+'.zip')
    if archive_path.exists(): raise SystemExit('Refusing to overwrite the first importer snapshot.')
    with zipfile.ZipFile(archive_path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for relative,baseline_sha in expected.items():
            if not relative.endswith('.meta'): continue
            path = (UNITY/relative).resolve()
            if not path.is_relative_to(UNITY.resolve()): raise ValueError('Path escaped Unity root.')
            body = path.read_bytes()
            if sha(body) == baseline_sha: continue
            original = subprocess.run(['git','show','1d1b30a:Unity/'+relative],cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout
            if sha(original) != baseline_sha: raise ValueError('Git baseline differs from supplied inventory: '+relative)
            if guid(body) != guid(original): raise ValueError('GUID changed: '+relative)
            archive.writestr(relative,body)
            keep = relative in KEEP
            changes.append({'file':relative,'original_sha256':baseline_sha,'imported_sha256':sha(body),'guid':guid(body),'action':'RETAIN_INTENTIONAL_IMPORTER_REPAIR' if keep else 'RESTORE_DELIVERED_METADATA'})
            if not keep: restores.append((path,original))
    # Finish validating the entire set before modifying any original metadata.
    for path,original in restores: path.write_bytes(original)
    report = {'scope':'Metadata only; no artwork, level, script or GUID changes. Import-generated metadata is archived before byte-exact restoration. A later native import can regenerate its serialization defaults.', 'round_trip_changed':len(changes),'restored':len(restores),'intentional_repairs_retained':sum(c['action']=='RETAIN_INTENTIONAL_IMPORTER_REPAIR' for c in changes),'files':changes}
    (OUT/('Metadata_Preservation'+suffix+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))


if __name__ == '__main__': run()
