"""Assemble current swap review frames; approval remains pending inspection."""
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/SwapCreation'

def sheet(paths,target,columns=4,width=300,height=565,crop=None):
    result=Image.new('RGB',(columns*width,((len(paths)+columns-1)//columns)*height),'#172536');d=ImageDraw.Draw(result)
    for i,path in enumerate(paths):
        im=Image.open(path).convert('RGB')
        if crop:im=im.crop(crop)
        im.thumbnail((width-12,height-30));x=i%columns*width;y=i//columns*height;result.paste(im,(x+(width-im.width)//2,y+27));d.text((x+6,y+6),path.stem[:42],fill='white')
    result.save(target)

def run():
    sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    touch=json.loads((OUT/'Touch/Report.json').read_text());assert touch['apk_sha256']==sha and len(touch['cases'])==4
    for mode in ['H','HReverse','V','VReverse']:
        folder=OUT/'Touch/Frames'/mode;folder.mkdir(parents=True,exist_ok=True)
        if not (folder/'090.png').exists() or (folder/'090.png').stat().st_mtime<(OUT/'Touch'/f'{mode}.mp4').stat().st_mtime:
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-loglevel','error','-y','-i',str(OUT/'Touch'/f'{mode}.mp4'),'-vf','fps=30','-frames:v','90',str(folder/'%03d.png')],check=True,timeout=90)
        paths=[folder/f'{n:03}.png' for n in range(19,40,2) if (folder/f'{n:03}.png').exists()]
        sheet(paths,OUT/f'{mode}_Swap_Sequence.png',4,340,310,(230,590,660,940))
    if not (OUT/'LDPlayer/Regression.json').exists():
        print('Gesture contact plates captured; full suite manifest pending.');return
    report=json.loads((OUT/'LDPlayer/Regression.json').read_text());installation=json.loads((OUT/'LDPlayer/Installation.json').read_text());assert report['status']=='PASS_NATIVE_REGRESSION' and not report['failures'] and installation['sha256']==sha
    frames=[]
    for name in sorted(set(report['frames'])):
        path=OUT/'LDPlayer'/name
        with Image.open(path) as im:w,h=im.size
        assert h>w,name
        frames.append({'file':'LDPlayer/'+name,'width':w,'height':h,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (OUT/'Frame_Manifest.json').write_text(json.dumps({'status':'PASS_CURRENT_ANDROID_FRAME_MANIFEST','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'apk_sha256':sha,'all_frames_portrait':True,'uniqueFrames':len(frames),'frames':frames,'scope':'Fresh report-listed frame names only; old remote PNGs excluded.'},indent=2)+'\n')
    names=list(dict.fromkeys(n for n in report['frames'] if n.startswith(('Stacked_Stones_','Connected_Win_L21','Home_Reward_Increase_L21','Home_Reward_L21'))))
    sheet([OUT/'LDPlayer'/n for n in names],OUT/'Preserved_Flows_Review.png')
    powers=[]
    for p in [4,5,21,11,16,7]:powers += sorted(n for n in set(report['frames']) if n.startswith(f'Power_{p}_Effect_'))[:2]
    sheet([OUT/'LDPlayer'/n for n in powers],OUT/'Power_Effects_Review.png')
    review={'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','apk_sha256':sha,'regression_checks':report['checks'],'unique_frames':len(frames),'plates':[f'{m}_Swap_Sequence.png' for m in ['H','HReverse','V','VReverse']]+['Preserved_Flows_Review.png','Power_Effects_Review.png'],'scope':'Native Android gestures/frames on LDPlayer. Inspector must review plates/video before assigning PASS. No physical-device or performance certification.'}
    (OUT/'Visual_Review.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review),flush=True)

if __name__=='__main__':run()
