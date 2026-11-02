"""Audit supplied PNG/JSON replacements; this is not a native rendering test."""
import datetime as dt
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]

def run():
    contract=json.loads((ROOT/'Unity/Assets/HeartOfTheRain/M69/Data/M70_PowerupContract.json').read_text())
    rows=[];count=0
    for e in contract['entries']:
        p=ROOT/'Unity'/e['texture'];m=json.loads((ROOT/'Unity'/e['manifest']).read_text())
        a=Image.open(p).convert('RGBA')
        assert a.size==(2048,2048)
        assert p.read_bytes()==(ROOT/'Unity'/e['resourceTexture']).read_bytes()
        assert hashlib.sha256(p.read_bytes()).hexdigest()==e['textureSHA256']
        assert hashlib.sha256((ROOT/'Unity'/e['manifest']).read_bytes()).hexdigest()==e['manifestSHA256']
        empty=[]
        for f in m['frames']:
            x,y,w,h=[f[k] for k in ['x','y','width','height']]
            assert 0<=x<x+w<=2048 and 0<=y<y+h<=2048
            alpha=a.crop((x,2048-y-h,x+w,2048-y)).getchannel('A')
            if alpha.getbbox() is None:empty.append(f['name'])
            assert alpha.crop((0,0,w,1)).getbbox() is None
            assert alpha.crop((0,h-1,w,h)).getbbox() is None
            assert alpha.crop((0,0,1,h)).getbbox() is None
            assert alpha.crop((w-1,0,w,h)).getbbox() is None
            count+=1
        idle=next((c for c in m['clips'] if c['name'] in ['Idle','RS_Idle','GS_Idle','OR_Idle']),None)
        if idle:
            for f in m['frames'][idle['start']:idle['start']+idle['count']]:
                x,y,w,h=[f[k] for k in ['x','y','width','height']]
                box=a.crop((x,2048-y-h,x+w,2048-y)).getchannel('A').point(lambda v:255 if v>8 else 0).getbbox()
                assert box, f['name']
                scale=1.4 if e['atlasIndex'] in [29,40] else 1
                coords=[(box[0]-w/2)*scale/m['pixelsPerUnit'],(box[1]-h/2)*scale/m['pixelsPerUnit'],(box[2]-w/2)*scale/m['pixelsPerUnit'],(box[3]-h/2)*scale/m['pixelsPerUnit']]
                assert max(map(abs,coords))<=.501,(e['name'],coords)
        rows.append({'name':e['name'],'frames':len(m['frames']),'idleFrames':idle['count'] if idle else 0,'runtimeAndReplayBytesMatch':True,'idleBodyAlphaAbove8InsideCell':True,'intentionallyTransparentEffectTails':empty})
    assert count==586
    result={'status':'PASS_OFFLINE_M70_ASSET_CHECKS','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'PNG/JSON checksum, bounds, gutter and cell-containment validation; not a Unity/device test. Transparent non-idle effect tails are permitted; cell containment excludes alpha<=8 glow fringes.','frames':count,'assets':rows}
    out=ROOT/'Verification/Evidence/M70/Offline_Assets.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'frames':count,'atlases':len(rows)}))

if __name__=='__main__':run()
