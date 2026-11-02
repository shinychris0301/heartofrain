"""Collect obstacle fall recordings and measured-pose evidence; require visual review."""
from pathlib import Path
import json,hashlib,subprocess
import imageio_ffmpeg
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Verification/Evidence/ObstacleFall'

def plate(paths,target,crop,columns=5):
 w,h=crop[2]-crop[0],crop[3]-crop[1];result=Image.new('RGB',(columns*w,((len(paths)+columns-1)//columns)*(h+25)),'#172536');d=ImageDraw.Draw(result)
 for i,p in enumerate(paths):
  im=Image.open(p).crop(crop);x=i%columns*w;y=i//columns*(h+25);result.paste(im,(x,y+25));d.text((x+5,y+5),p.stem,fill='white')
 result.save(target)

def run():
 sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest();touch=json.loads((OUT/'Touch/Report.json').read_text());assert touch['apk_sha256']==sha and len(touch['cases'])==6
 metrics=[]
 for c in touch['cases']:
  mode=c['mode'];folder=OUT/'Touch/Frames'/mode;folder.mkdir(parents=True,exist_ok=True);video=OUT/'Touch'/f'{mode}.mp4'
  if not (folder/'150.png').exists() or (folder/'150.png').stat().st_mtime<video.stat().st_mtime:
   subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-loglevel','error','-y','-i',str(video),'-vf','fps=30','-frames:v','150',str(folder/'%03d.png')],check=True,timeout=90)
  moving=[p for p in c['poses'] if 0<p['age']<c['seconds']];assert len(moving)>=4
  source_x=450+(c['fromX']-4)*94;target_x=450+(c['toX']-4)*94
  roi=(int(min(source_x,target_x)-40),875,int(max(source_x,target_x)+40),1055);onset=None
  for n in range(47 if mode in ("Hammer","Slow") else 10,105):
   p=folder/f'{n:03d}.png'
   if not p.exists():continue
   a=np.array(Image.open(p).convert('RGB'))[roi[1]:roi[3],roi[0]:roi[2]].astype(float);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2];mask=(b>155)&(r<100)&(g>80)&(b>g*1.1) if mode=='Match' else (g>110)&(g>r*1.3)&(g>b*1.3) if mode.startswith('Edge') else (r>75)&(b>150)&(b>r*1.02)&(g<r*.85);yy,xx=np.where(mask)
   if len(xx)<200:continue
   center_x=float(xx.mean()+roi[0]);center_y=float(yy.mean()+roi[1]);progress=(center_x-source_x)/(target_x-source_x)
   if .12<progress<.85 and 921<center_y<1017:onset=max(1,n-2);break
  if onset is None:raise AssertionError('Cannot locate visible flight in '+mode)
  ids=range(max(1,onset-2),min(150,onset+16));paths=[folder/f'{n:03}.png' for n in ids if (folder/f'{n:03}.png').exists()]
  left=25 if mode=='EdgeLeft' else 610 if mode=='EdgeRight' else 275;crop=(left,780,left+265,1110);plate(paths,OUT/f'{mode}_Fall_Sequence.png',crop)
  metrics.append({'mode':mode,'flightSeconds':c['seconds'],'landingSeconds':c['landing'],'movingRenderedPoses':len(moving),'maximumTravelAspectRatio':max(p['sy']/p['sx'] for p in moving),'forcedSlowFrame':c['forcedSlowFrame'],'forcedSlowAge':c.get('forcedSlowAge',-1),'videoMotionStartApproxSeconds':onset/30,'sourceCell':[c['fromX'],c['fromY']],'restingCell':[c['toX'],c['toY']]})
 paths=[p for p in sorted((OUT/'MV_Obstacle_Gap').glob('*.png')) if 1.0<=float(p.stem)<=1.6];plate(paths,OUT/'MV_Gap_Fall_Detail.png',(25,560,320,900))
 review={'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','apk_sha256':sha,'cases':metrics,'scope':'Actual Android input/video and native rendered poses. Slow is an explicit180ms induced stall. Motion-start estimates are color-mask/video-frame approximations; no GPU/input-latency/physical-device certification.','plates':[f'{c["mode"]}_Fall_Sequence.png' for c in touch['cases']]+['MV_Fall_Detail.png','MV_Gap_Fall_Detail.png']}
 (OUT/'Visual_Review.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review,indent=2),flush=True)

if __name__=='__main__':run()
