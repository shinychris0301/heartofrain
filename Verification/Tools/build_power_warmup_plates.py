"""Create inspection plates; leave approval to a subsequent visual review."""
import argparse,datetime as dt,hashlib,json,shutil,subprocess
from pathlib import Path
import imageio_ffmpeg
from PIL import Image,ImageDraw
from measure_fluidity import ROOT,ADB,REMOTE
OUT=ROOT/'Verification/Evidence/PowerWarmup'

def still_plate(names,source,target,columns=4):
    sheet=Image.new('RGB',(columns*300,((len(names)+columns-1)//columns)*570),(22,27,36));draw=ImageDraw.Draw(sheet)
    for i,name in enumerate(names):
        im=Image.open(source/name).convert('RGB');im.thumbnail((295,530));x=i%columns*300;y=i//columns*570;sheet.paste(im,(x,y+28));draw.text((x+4,y+5),name,fill='white')
    sheet.save(target)

def starting():
    result=json.loads((OUT/'Starting/Report.json').read_text());assert len(result['cases'])==3
    plates=[];artifacts={}
    for case in result['cases']:
        mode=case['mode'];video=OUT/'Starting'/(mode+'.mp4');stream=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24',output_params=['-vf','fps=10']);meta=next(stream);w,h=meta['size'];assert w<h and meta['duration']>3
        chosen=[3,5,7,9,11,13,16,19,23,28,34,42];frames=[]
        for i,raw in enumerate(stream):
            if i in chosen:frames.append((i/10,Image.frombytes('RGB',(w,h),raw)))
            if i>=chosen[-1]:break
        stream.close();sheet=Image.new('RGB',(1200,1710),(22,27,36));draw=ImageDraw.Draw(sheet)
        for i,(at,im) in enumerate(frames):
            im.thumbnail((295,530));x=i%4*300;y=i//4*570;sheet.paste(im,(x,y+28));draw.text((x+5,y+5),f'{mode} {at:.1f}s',fill='white')
        path=OUT/(mode+'_Sequence.png');sheet.save(path);plates.append(path.name)
        for p in [path,video,OUT/'Starting'/(mode+'_Report.json')]:artifacts[p.relative_to(OUT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    names=['GrantIntro_Retry_Before.png','GrantIntro_Retry_Menu.png','GrantIntro_Retry_Intro.png','GrantIntro_Retry_After.png'];path=OUT/'Starting_Retry_UI.png';still_plate(names,OUT/'Starting',path);plates.append(path.name)
    for p in [path,*[OUT/'Starting'/n for n in names]]:artifacts[p.relative_to(OUT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'Starting_Visual_Review.json').write_text(json.dumps({'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','apk_sha256':result['apk_sha256'],'scope':result['scope']+' Supplementary pause-menu retry is visual UI coverage; native retryChecked remains false for GrantIntro.','plates':plates,'artifactSHA256':artifacts},indent=2)+'\n')

def ui():
    previous=json.loads((ROOT/'Verification/Evidence/GameplayAudit/UI_Review.json').read_text());report=json.loads((OUT/'LDPlayer/Regression.json').read_text());install=json.loads((OUT/'LDPlayer/Installation.json').read_text());source=json.loads((OUT/'Player_Source_SHA256.json').read_text());assert install['sha256']==source['apk_sha256']
    names=previous['frames']+['Connected_OutOfMoves_Retry.png','Connected_Exit.png','Connected_Win_L21.png','Home_Reward_Increase_L21.png','Home_Reward_L21.png','Finale_Daria.png','Finale_City_Hook.png','Home_Reward_Increase_L50.png','Home_Reward_L50.png']
    assert all(n in report['frames'] for n in names),'Wait for complete manifested native captures'
    raw=OUT/'UI_Review';raw.mkdir(exist_ok=True);artifacts={}
    for n in names:
        p=raw/n;shutil.copyfile(OUT/'LDPlayer'/n,p);artifacts[p.relative_to(OUT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    plates=[]
    for prefix,group in [('App_UI',names[:20]),('Flow_UI',names[20:])]:
        for i in range(0,len(group),8):
            p=OUT/f'{prefix}_{i//8+1}.png';still_plate(group[i:i+8],raw,p);plates.append(p.name);artifacts[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'UI_Review.json').write_text(json.dumps({'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','apk_sha256':install['sha256'],'runUtc':report['utc'],'scope':'29 selected freshly manifested native UI/GPU captures: story/practice, Home/navigation, ranking/Teams/Shop demo pages, settings, failure/exit, celebration/Home reward and finale. Not exhaustive pixel/native-language/service approval.','frames':names,'plates':plates,'artifactSHA256':artifacts},indent=2)+'\n')

def appui():
    install=json.loads((OUT/'LDPlayer/Installation.json').read_text())
    def adb(*args):return subprocess.run([str(ADB),'-s',install['serial'],*args],capture_output=True,check=True,timeout=45).stdout
    report=json.loads(adb('shell','cat',REMOTE+'/Regression/Regression.json'))
    assert dt.datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=dt.datetime.fromisoformat(install['utc'])
    names=json.loads((ROOT/'Verification/Evidence/GameplayAudit/UI_Review.json').read_text())['frames'];assert len(names)==20 and all(n in report['frames'] for n in names)
    raw=OUT/'UI_Review';raw.mkdir(exist_ok=True);artifacts={};plates=[]
    for n in names:
        path=raw/n;adb('pull',REMOTE+'/Regression/'+n,str(path));artifacts[path.relative_to(OUT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    for i in range(0,20,8):
        path=OUT/f'App_UI_{i//8+1}.png';still_plate(names[i:i+8],raw,path);plates.append(path.name);artifacts[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT/'App_UI_Review.json').write_text(json.dumps({'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','apk_sha256':install['sha256'],'runUtc':report['utc'],'frames':names,'plates':plates,'artifactSHA256':artifacts},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['starting','ui','appui']);a=p.parse_args();{'starting':starting,'ui':ui,'appui':appui}[a.stage]()
