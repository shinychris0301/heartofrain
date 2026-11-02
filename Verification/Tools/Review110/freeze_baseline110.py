"""Read-only pre-edit110 source/GUID receipt; never launches Unity or a device."""
import hashlib,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bind(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
def main():
 out=Path(__file__).parent;current=api.freeze();previous=ROOT/'Verification/Evidence/Review109/Native/AndroidBuildLts01/MainSources_after.json';prior=json.loads(previous.read_text('utf-8'))
 guids={}
 for p in (ROOT/'Unity/Assets').rglob('*.meta'):
  values=re.findall(rb'(?m)^guid:\s*([a-fA-F0-9]{32})\s*$',p.read_bytes())
  if len(values)!=1:raise ValueError('UniqueValidGuidRequired110')
  guids[p.relative_to(ROOT/'Unity').as_posix()]=values[0].decode('ascii').lower()
 if len(set(guids.values()))!=len(guids):raise ValueError('GuidCollision110')
 if current!=prior:raise ValueError('PreEditMainMustMatchFinal109')
 api.write(out/'BaselineMain110.json',current);api.write(out/'BaselineGuids110.json',dict(sorted(guids.items())))
 receipt=dict(status='FROZEN_PRE_EDIT_BASELINE110',utc=datetime.now(timezone.utc).isoformat(),mainInputs=current['inputCount'],assetGuids=len(guids),matchesExactFinal109=True,main=bind(out/'BaselineMain110.json'),guids=bind(out/'BaselineGuids110.json'),previous=bind(previous),instructions=[bind(ROOT/'AGENTS.md'),bind(ROOT/'Codex_Handoff/Documentation/00_START_HERE.md'),bind(ROOT/'Codex_Handoff/Documentation/01_STATUS_AND_DECISIONS.md')],scope='Read-only pre-edit main Assets/Packages/ProjectSettings and unique GUID snapshot. No Unity/compiler/import/build/SDK/service/ADB/device operation.')
 api.write(out/'Baseline110.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
