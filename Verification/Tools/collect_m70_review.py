"""Assemble final-build Android evidence without automatically granting visual approval."""
import datetime as dt
import hashlib
import json
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/M70'

def sheet(names,path,columns=3,width=330,height=625):
    result=Image.new('RGB',(columns*width,((len(names)+columns-1)//columns)*height),'#101e2c');draw=ImageDraw.Draw(result)
    for i,name in enumerate(names):
        source=OUT/'LDPlayer'/name
        assert source.exists(), name
        frame=Image.open(source).convert('RGB');frame.thumbnail((width-12,height-35))
        x=(i%columns)*width;y=(i//columns)*height
        result.paste(frame,(x+(width-frame.width)//2,y+30));draw.text((x+8,y+8),source.stem[:45],fill='white')
    result.save(path)

def run():
    report=json.loads((OUT/'LDPlayer/Regression.json').read_text())
    assert report['status']=='PASS_NATIVE_REGRESSION' and not report['failures']
    install=json.loads((OUT/'LDPlayer/Installation.json').read_text())
    sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    assert sha==install['sha256']
    device=json.loads((OUT/'LDPlayer/M70_Device.json').read_text())
    assert device['status']=='PASS_NATIVE_M70_DEVICE' and not device['failures']
    frames=[]
    for name in sorted(set(report['frames'])):
        path=OUT/'LDPlayer'/name
        with Image.open(path) as im:w,h=im.size
        assert h>w, name
        frames.append({'file':'LDPlayer/'+name,'width':w,'height':h,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest={'status':'PASS_CURRENT_ANDROID_FRAME_MANIFEST','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'apk_sha256':sha,'all_frames_portrait':True,'uniqueFrames':len(frames),'frames':frames,'scope':'Only frame names listed by the fresh final-APK suite; excludes old leftover remote PNGs.'}
    (OUT/'Frame_Manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    idle=[f'M70_{shape}_Idle_{pose}.png' for shape in ['9x9','9x11','11x11'] for pose in ['A','B']]
    sheet(idle,OUT/'Android_Idle_Review.png',3)
    effects=[]
    for power in [4,5,21,11,16,7]:
        actual=sorted(n for n in set(report['frames']) if n.startswith(f'Power_{power}_Effect_'))
        assert actual, f'No current activation capture for {power}'
        effects.extend(actual[:2])
    effects+=sorted(n for n in set(report['frames']) if n.startswith('Pair_7_7_False_False_Effect_'))
    sheet(effects,OUT/'Android_Effects_Review.png',4,300,565)
    comparisons=[n for n in report['frames'] if n.startswith(('Stacked_Stones_','Home_Reward_Increase_','Connected_Win_L21'))]
    sheet(list(dict.fromkeys(comparisons)),OUT/'Preserved_Flows_Review.png',4,300,565)
    review={'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','apk_sha256':sha,'device':device['graphics'],'scope':'Agent must inspect the actual Android frames/contact plates before marking review complete. No frame-budget or physical-device certification.','plates':['Android_Idle_Review.png','Android_Effects_Review.png','Preserved_Flows_Review.png'],'runtime_body_bytes':device['sevenBodyBytes'],'regression_checks':report['checks'],'frames':len(frames)}
    (OUT/'Visual_Review.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(review,indent=2))

if __name__=='__main__':run()
