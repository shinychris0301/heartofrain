"""Offline composition from compiled C# geometry/poses and the shipped artwork.
This does not capture Unity and does not simulate a live winning board.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from functools import lru_cache
import json,math,importlib.util,re,subprocess,numpy as np,wave
R=Path(__file__).resolve().parents[1];U=(R.parent/'Unity') if (R.parent/'Unity').exists() else R/'Project/Heart_of_the_Rain_M66/Unity';A=U/'Assets/HeartOfTheRain';S=1
raw=json.loads((R/'M66Reference/Validation/Sprite_Bindings.json').read_text());borders=raw['borders']
sprites={k:str(U/v.split('/Unity/',1)[1]) for k,v in raw['sprites'].items()}
profiles=json.loads((R/'Validation/Runtime_Layouts.json').read_text());motion=json.loads((R/'Validation/Motion_Samples.json').read_text())
daria_poses=json.loads((R/'Validation/Daria_Poses.json').read_text());finale_poses=json.loads((R/'Validation/Finale_Poses.json').read_text());geometry=json.loads((R/'Validation/Cinematic_Layouts.json').read_text())
victory_poses=json.loads((R/'Validation/Victory_Poses.json').read_text());victory_layouts=json.loads((R/'Validation/Victory_Layouts.json').read_text());victory_particles=json.loads((R/'Validation/Victory_Particles.json').read_text())
translations=json.loads((R/'Validation/Celebration_Translations.json').read_text())
def tr(key,locale='en'):return next((t['text'] for t in translations if t['locale']==locale and t['key']==key),key)
@lru_cache(maxsize=100)
def source(key):return Image.open(sprites[key]).convert('RGBA')
@lru_cache(maxsize=100)
def font(size,bold=True):return ImageFont.truetype(str(A/'App/Home/Fonts'/('HomeRounded-Black.ttf' if bold else 'HomeRounded-ExtraBold.ttf')),max(9,round(size)))
def color(value):
 s=value.lstrip('#');return tuple(int(s[i:i+2],16) for i in range(0,len(s),2))+(255,)*(4-len(s)//2)
def nine(im,w,h,key):
 l,b,r,t=borders[key];sx=[0,l,im.width-r,im.width];sy=[0,t,im.height-b,im.height];xx=min(1,w/max(1,(l+r)/4));yy=min(1,h/max(1,(t+b)/4));dx=[0,round(l/4*xx),w-round(r/4*xx),w];dy=[0,round(t/4*yy),h-round(b/4*yy),h];out=Image.new('RGBA',(w,h))
 for j in range(3):
  for i in range(3):
   ww,hh=dx[i+1]-dx[i],dy[j+1]-dy[j]
   if ww>0 and hh>0:out.alpha_composite(im.crop((sx[i],sy[j],sx[i+1],sy[j+1])).resize((ww,hh),Image.Resampling.LANCZOS),(dx[i],dy[j]))
 return out
def sprite(out,key,box,sliced=False,contain=False,alpha=1,angle=0):
 x,y,w,h=map(round,box);w=max(1,w);h=max(1,h);im=source(key)
 if sliced:im=nine(im,w,h,key)
 elif contain:
  ratio=min(w/im.width,h/im.height);im=im.resize((max(1,round(im.width*ratio)),max(1,round(im.height*ratio))),Image.Resampling.LANCZOS)
 else:im=im.resize((w,h),Image.Resampling.LANCZOS)
 if angle:im=im.rotate(angle,Image.Resampling.BICUBIC,expand=True)
 if alpha<1:im=im.copy();im.putalpha(im.getchannel('A').point(lambda a:round(a*max(0,alpha))))
 out.alpha_composite(im,(round(x+(w-im.width)/2),round(y+(h-im.height)/2)))
def text(out,copy,box,size=17,ink='#17354E',bold=True,wrap=False,min_size=10,fit_pad=0):
 x,y,w,h=box;size=int(size)
 def lines(ff):
  if not wrap:return [copy]
  result=[];line=''
  for word in copy.split():
   candidate=(line+' '+word).strip()
   if ff.getlength(candidate)>w and line:result.append(line);line=word
   else:line=candidate
  return result+[line]
 while True:
  ff=font(size,bold);ls=lines(ff);step=size*1.22
  if size<=min_size or (len(ls)*step<=h and max(ff.getlength(l) for l in ls)<=w-fit_pad):break
  size-=1
 d=ImageDraw.Draw(out);yy=y+(h-len(ls)*step)/2
 for line in ls:
  b=ff.getbbox(line);d.text((x+(w-ff.getlength(line))/2,yy-b[1]+(step-b[3]+b[1])/2),line,font=ff,fill=color(ink));yy+=step
 return size
atlas=Image.open(A/'App/Celebrations/Art/Daria_Celebration_Atlas.png').convert('RGBA')
@lru_cache(maxsize=16)
def frame(n):
 w=atlas.width/4;x=(n%4)*w;rows=[0,320,633,947,1254];y=rows[n//4];bottom=rows[n//4+1]
 return atlas.crop((round(x+2),round(y+2),round(x+w-2),round(bottom-2))).resize((448,448),Image.Resampling.LANCZOS)
def daria_image(pose,size,opacity=1):
 a=np.array(frame(pose['frame']),dtype=np.float32)/255;b=np.array(frame(pose['nextFrame']),dtype=np.float32)/255;t=pose['blend']
 alpha=a[:,:,3:]*(1-t)+b[:,:,3:]*t;rgb=(a[:,:,:3]*a[:,:,3:]*(1-t)+b[:,:,:3]*b[:,:,3:]*t)/np.maximum(alpha,.0001)
 mask=np.clip((1-np.linspace(0,1,448))/.055,0,1);mask=mask*mask*(3-2*mask);alpha*=mask[:,None,None]
 result=np.concatenate([rgb,alpha*opacity],axis=2);im=Image.fromarray(np.clip(result*255,0,255).astype('uint8'),'RGBA')
 target=max(1,round(size));sz=max(1,round(size*pose.get('scale',1)));im=im.resize((sz,sz),Image.Resampling.LANCZOS).rotate(pose.get('angle',0),Image.Resampling.BICUBIC,expand=True)
 out=Image.new('RGBA',(target+20,target+20));out.alpha_composite(im,(round((target+20-im.width)/2+pose.get('sway',0)),round((target+20-im.height)/2-pose.get('lift',0))));return out
spec=importlib.util.spec_from_file_location('ui',R/'CoreReference/Source/render_ui.py');ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)
@lru_cache(maxsize=4)
def background(level):return Image.open(R/'CoreReference/Previews/Level50_Initial.png').convert('RGBA') if level==50 else ui.still(level).convert('RGBA')
def cover(im,w,h,zoom=1):
 scale=max(w/im.width,h/im.height)*zoom;cw=w/scale;ch=h/scale;left=(im.width-cw)/2;top=(im.height-ch)*(1-.68)
 return im.crop((round(left),round(top),round(left+cw),round(top+ch))).resize((round(w),round(h)),Image.Resampling.LANCZOS)
def result(width=430,height=852,time=1,reduced=False,level=18):
 g=next(v['geometry'] for v in victory_layouts if v['width']==width and v['height']==height)
 p=min((v for v in victory_poses if v['reduced']==reduced),key=lambda v:abs(v['time']-time))['pose']
 out=cover(background(level),width,height);out.alpha_composite(Image.new('RGBA',(width,height),(0,0,0,round(255*p['dim']))))
 hs=g['size']*p['haloScale'];sprite(out,'LC_Halo',(g['x']+(g['size']-hs)/2,g['y']+(g['size']-hs)/2,hs,hs),alpha=p['haloAlpha'],angle=p['haloAngle'])
 dp=min((v for v in daria_poses if v['variant']==level%3 and v['reduced']==reduced),key=lambda v:abs(v['time']-max(0,time-.18)))['pose']
 size=g['size']*p['scale'];char=daria_image(dp,size,p['alpha']);out.alpha_composite(char,(round(g['x']+(g['size']-size)/2-10),round(g['y']+(g['size']-size)/2+p['lift']-10)))
 if not reduced:
  ps=min(victory_particles,key=lambda v:abs(v['time']-time))['particles']
  for v in ps:
   x=v['x']*width/430;y=v['y']*height/852;pw=v['width'];ph=v['height'];alpha=v['alpha']*p['alpha']
   if v['star']:sprite(out,'RewardStar_R2',(x-pw/2,y-ph/2,pw,ph),alpha=alpha,angle=v['angle'])
   else:
    c=[(240,186,82),(247,232,194),(125,135,77)][v['color']];confetti=Image.new('RGBA',(max(1,round(pw)),max(1,round(ph))),c+(round(alpha*255),)).rotate(v['angle'],Image.Resampling.BICUBIC,expand=True);out.alpha_composite(confetti,(round(x-confetti.width/2),round(y-confetti.height/2)))
 return out.convert('RGB')
well=Image.open(A/'App/Celebrations/Art/Chapter01_RestoredWell.png').convert('RGBA');hook=Image.open(A/'App/Celebrations/Art/Chapter01_Messenger.png').convert('RGBA')
def finale(time=3.5,width=430,height=852,locale='en',reduced=False):
 g=next(x['geometry'] for x in geometry if x['width']==width and x['height']==height);p=min((x for x in finale_poses if x['reduced']==reduced),key=lambda x:abs(x['time']-time))['pose'];out=Image.new('RGBA',(width,height),'#09131F')
 stage=cover(well,g['stageW'],g['stageH'],p['wellZoom']);other=cover(hook,g['stageW'],g['stageH'],p['hookZoom']);out.alpha_composite(Image.blend(stage,other,p['mix']),(0,0))
 out.alpha_composite(daria_image(p['daria'],g['dariaSize'],p['dariaAlpha']),(round(g['dariaX']-10),round(g['dariaY']-10)))
 if not reduced:
  for i in range(12):
   phase=(time*.28+i*.173)%1;x=g['stageW']*(.08+.84*((i*.618)%1));y=g['stageH']*(.25+.53*(1-phase));size=5+i%4
   sprite(out,'RewardStar_R2',(x,y,size,size),alpha=math.sin(phase*math.pi)*.65*(1-p['mix']),angle=time*24+i*39)
 pw=g['captionW'] if g['landscape'] else min(360,width-28);px=g['captionX'] if g['landscape'] else (width-pw)/2;sprite(out,'R4_Chapter',(px,12,pw,96));text(out,tr('Chapter {0} complete',locale).format(1),(px+18,23,pw-36,30),24,'#FFFFFF',fit_pad=12);chapter_titles={'en':'The Village Well','es':'El pozo del pueblo','fr':'Le puits du village','de':'Der Dorfbrunnen','ru':'Деревенский колодец'};text(out,chapter_titles[locale],(px+18,51,pw-36,24),16,'#FFF0CC');text(out,tr('Levels {0}–{1}',locale).format(1,50),(px+18,76,pw-36,20),12,'#FFE0A3')
 x,y,cw,ch=g['captionX'],g['captionY'],g['captionW'],g['captionH'];sprite(out,'LC_RewardWell',(x,y,cw,ch),True)
 beat=p['beat'];speaker=['Village restored','Daria','A message from the city'][beat];copy=['The village well is restored.','You did it! The well is working again.','A messenger arrives: the Heart of Ancient Moscow is faltering.'][beat]
 text(out,tr(speaker,locale),(x+16,y+12,cw-32,22),14,'#876129');text(out,tr(copy,locale),(x+18,y+38,cw-36,ch-111),17,'#17334D',False,True,12)
 bx,by,bw=g['buttonX'],g['buttonY'],g['buttonW'];sprite(out,'R4_Start',(bx,by,bw,56));text(out,tr('Continue' if time>=9.4 else 'Skip',locale),(bx,by,bw,56),22,'#FFFFFF')
 return out.convert('RGB')
def stills():
 for name,w,h,t in [('Portrait',430,852,.9),('Compact',320,480,1.7),('Landscape',750,369,2.5),('Settled',430,852,2.8)]:result(w,h,t).save(R/'Previews'/('M67R2_Victory_'+name+'.png'))
 result(430,852,.9,True).save(R/'Previews/M67R2_Victory_Reduced.png')
 finale(3.4).save(R/'Previews/M67R2_Chapter_Daria.png')
 out=Image.new('RGB',(1180,1030),'#112C3D');d=ImageDraw.Draw(out);d.text((30,22),'DARIA · VICTORY ANIMATION',font=font(30),fill='#FFF0CE');d.text((30,65),'No result panel · Direct eye contact · Original character palette',font=font(18),fill='#C2D5D8')
 for i,(t,label) in enumerate([(.48,'ARRIVE'),(.9,'CELEBRATE'),(2.8,'SETTLE')]):
  x=30+i*385;d.text((x,112),label,font=font(18),fill='#FFF0CE');im=result(time=t);im.thumbnail((350,730),Image.Resampling.LANCZOS);out.paste(im,(x,147))
 d.text((30,914),'3.5 seconds · Tap to skip · Advances automatically',font=font(20),fill='#FFF0CE');d.text((30,955),'Offline playback using shipped art and production motion samples.',font=font(16),fill='#C2D5D8');d.text((30,983),'Actual Unity rendering and device checks are still required.',font=font(16),fill='#C2D5D8');out.save(R/'Previews/M67R2_Victory_Review.png')
def movie():
 path=R/'Previews/M67R2_Victory_Playback.mp4';video=R/'Validation/motion_no_audio.mp4';duration=4.5;fps=60;w,h=430,852
 process=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(video)],stdin=subprocess.PIPE)
 for i in range(round(duration*fps)):
  t=i/fps-.25;im=result(time=max(0,min(t,3.5)));process.stdin.write(im.tobytes())
 process.stdin.close();assert process.wait()==0
 sr=44100;mix=np.zeros((round(duration*sr),2),np.float32)
 wins=list((A/'M47').rglob('*Win*.wav'))+list((A/'M47').rglob('*win*.wav'))
 if wins:
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(wins[0]),'-f','f32le','-ac','2','-ar',str(sr),'-']);arr=np.frombuffer(raw,dtype=np.float32).reshape(-1,2);start=round(.25*sr);length=min(len(arr),len(mix)-start);mix[start:start+length]+=arr[:length]*.6
 wav=R/'Validation/Preview_Audio.wav'
 with wave.open(str(wav),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(mix,-1,1)*32767).astype('<i2').tobytes())
 subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(video),'-i',str(wav),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-t',str(duration),'-movflags','+faststart',str(path)],check=True)
 subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
 (R/'Validation/Playback.json').write_text(json.dumps({'status':'PASS_OFFLINE_EXPORT','duration_seconds':duration,'frames':round(duration*fps),'fps':fps,'width':w,'height':h,'UnityCapture':False,'note':'Isolated animation review on initial board; next-level route verified separately.'},indent=2));print('Video exported',path.stat().st_size,flush=True)
if __name__=='__main__':
 import sys
 if '--movie' in sys.argv:movie()
 else:stills();print('Review stills exported')
