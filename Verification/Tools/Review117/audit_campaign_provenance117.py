"""Validate staged candidate chain, versioned level bytes and art bindings.

Host-side byte audit only; not Unity, replay, balance or device certification.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CACHE=ROOT/'.verification-cache/Review117'
EVIDENCE=ROOT/'Verification/Evidence/Review117'
LEGACY=ROOT/'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117'
CURRENT=ROOT/'Unity/Assets/HeartOfTheRain/M47/Data/Levels'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    errors=[];rows=[]
    low={x['level']:x for x in read(CACHE/'CampaignVaried03/Report.json')['levels']}
    bottom={x['level']:x for x in read(CACHE/'CampaignAllBottom01/Report.json')['levels']}
    safe={x['level']:x for x in read(CACHE/'CampaignSafeGrowth01/Report.json')['levels']}
    art={x['level']:x for x in read(CACHE/'BoardVaried03/Report.json')['levels']}
    golden=read(EVIDENCE/'BoardGolden04Report.json')
    if len(golden['levels'])!=50 or any(x['surfaceDifferentPixels'] or x['maskDifferentPixels'] for x in golden['levels']):errors.append('Legacy golden art comparison incomplete or differs')
    manifest=read(EVIDENCE/'CampaignSafeGrowth01Manifest.json');bound={x['level']:x for x in manifest['levels']}
    for n in range(1,51):
        name=f'C01_L{n:03}';legacy=LEGACY/(name+'.json');current=CURRENT/(name+'.json')
        if sha(legacy)!=sha(current):errors.append(f'L{n}: current/legacy source changed')
        record={'level':n,'legacySHA256':sha(legacy)}
        if n>=11:
            varied=CACHE/'CampaignVaried03'/(name+'.json');bottom_file=CACHE/'CampaignAllBottom01'/(name+'.json');safe_file=CACHE/'CampaignSafeGrowth01'/(name+'.json')
            av,bv,sv=sha(varied),sha(bottom_file),sha(safe_file)
            if (low[n]['sourceSHA256']!=sha(legacy) or low[n]['draftSHA256']!=av or
                bottom[n]['priorSHA256']!=av or bottom[n]['draftSHA256']!=bv or
                safe[n]['priorSHA256']!=bv or safe[n]['draftSHA256']!=sv):errors.append(f'L{n}: draft chain hash mismatch')
            if art[n]['levelSHA256']!=av:errors.append(f'L{n}: art input mismatch')
            v,b,s=read(varied),read(bottom_file),read(safe_file)
            if any(d['activeCells']!=v['activeCells'] or (d['columns'],d['rows'])!=(v['columns'],v['rows']) for d in (b,s)):errors.append(f'L{n}: level/art geometry mismatch')
            if n in (27,44):
                if s['mossRegrowth'].pop('safeSegmentBottom',None) is not True or b!=s:errors.append(f'L{n}: unexpected opt-in changes')
            elif bv!=sv:errors.append(f'L{n}: unexpected safe-growth stage changes')
            record.update(variedSHA256=av,bottomSHA256=bv,safeSHA256=sv)
        bound_row=bound[n]
        for field,pathfield in (('levelSHA256','levelPath'),('surfaceSHA256','surfacePath'),('maskSHA256','maskPath')):
            if sha(ROOT/bound_row[pathfield])!=bound_row[field]:errors.append(f'L{n}: manifest {field} mismatch')
        rows.append(record)
    model=ROOT/'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs'; model_report=read(EVIDENCE/'SafeGrowthSource117.json')
    if sha(model)!=model_report['afterSHA256']:errors.append('Safe-growth model changed after source record')
    out={'status':'PASS' if not errors else 'FAIL','scope':'Host byte/geometry/art chain audit only; no Unity, device, balance or backend release acceptance.',
         'errors':errors,'levels':rows,'modelSHA256':sha(model),'goldenBoardCount':len(golden['levels'])}
    (EVIDENCE/'CampaignProvenance117.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'levels':len(rows),'errors':errors}))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
