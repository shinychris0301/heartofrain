"""Offline Unity-asset composition. Shared C# pose/feedback streams, not a Unity capture."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter
import numpy as np
from functools import lru_cache
import importlib.util,json,gzip,subprocess,sys,math,os,tempfile
R=Path(__file__).resolve().parents[1];PROJECT=(R.parent.parent/'Unity') if (R.parent.parent/'Unity').exists() else R.parent/'Project/Heart_of_the_Rain_M66/Unity';A=PROJECT/'Assets/HeartOfTheRain/M47';M=PROJECT/'Assets/HeartOfTheRain/M46';W,H=720,1280
spec=importlib.util.spec_from_file_location('approved_renderer',R/'Source/approved_atlas_reader.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
catalog={v['id']:v for v in json.loads((M/'Data/Visual_Catalog.json').read_text())['sprites']}
ink='#203044';cream='#fff4d5'
@lru_cache(maxsize=180)
def img(path):return Image.open(path).convert('RGBA')
def asset(key):return img(A/'Art'/f'{key}.png') if (A/'Art'/f'{key}.png').exists() else img(M/catalog[key]['path'])
def font(n,b=True):return ImageFont.truetype(str(A/'Fonts'/('DejaVuSans-Bold.ttf' if b else 'DejaVuSans.ttf')),n)
def text(im,s,box,n=24,color=ink,b=True):
 d=ImageDraw.Draw(im);x,y,w,h=box;f=font(n,b);d.text((x+w/2,y+h/2),s,anchor='mm',font=f,fill=color,align='center',spacing=7)
def lines(im,s,box,n=24,color=ink,b=False):
 d=ImageDraw.Draw(im);x,y,w,h=box;f=font(n,b);words=s.split();out=[];line=''
 for word in words:
  c=(line+' '+word).strip()
  if d.textlength(c,font=f)>w and line:out.append(line);line=word
  else:line=c
 if line:out.append(line)
 for i,line in enumerate(out):text(im,line,(x,y+h/2-len(out)*(n+10)/2+i*(n+10),w,n+10),n,color,b)
@lru_cache(maxsize=160)
def scaled(key,w,h,sliced=False):
 src=asset(key)
 if key=="Button_Settings":sliced=False
 if not sliced:
  ratio=min(w/src.width,h/src.height);tw=max(1,round(src.width*ratio));th=max(1,round(src.height*ratio));out=Image.new('RGBA',(w,h));out.alpha_composite(src.resize((tw,th),Image.Resampling.LANCZOS),((w-tw)//2,(h-th)//2));return out
 b=min(12 if key=='Label_Tab' else 36,src.width//3,src.height//3,w//2,h//2);out=Image.new('RGBA',(w,h));xs=[0,b,src.width-b,src.width];ys=[0,b,src.height-b,src.height];xd=[0,b,w-b,w];yd=[0,b,h-b,h]
 for j in range(3):
  for i in range(3):out.alpha_composite(src.crop((xs[i],ys[j],xs[i+1],ys[j+1])).resize((xd[i+1]-xd[i],yd[j+1]-yd[j]),Image.Resampling.LANCZOS),(xd[i],yd[j]))
 return out
def put(im,key,box,sliced=False):
 x,y,w,h=map(round,box);im.alpha_composite(scaled(key,w,h,sliced),(x,y))
def goal_key(f):return {'crate':'crate_1','moss':'moss_1','stone':'stone_1','pail':'pail_Full','case':'case_1','gate':'gate_1','crystal':'crystalIcon','pod':'waterSpirit','rainlight':'rainlight'}[f]
def hud(im,level,moves,goals,stock=None,selection=-1,hint=''):
 stock=stock or [3,3,3,3]
 put(im,'Panel_Header',(30,38,660,192))
 put(im,'Panel_Moves',(42,82,112,120),True);put(im,'Label_Tab',(50,66,96,34),True);text(im,'Moves',(52,65,92,34),22,'#ffffff');text(im,str(moves),(48,105,100,84),58,'#a65322' if moves<=5 else ink)
 put(im,'Panel_Goals',(166,82,324,120),True);put(im,'Label_Tab',(264,66,128,34),True);text(im,'Targets',(266,65,124,34),22,'#ffffff')
 span=min(296,len(goals)*104);gw=span/len(goals)
 for i,g in enumerate(goals):
  x=328-span/2+i*gw;put(im,goal_key(g['family']),(x+(gw-56)/2,105,56,56));text(im,'✓' if g['count']==0 else str(g['count']),(x,158,gw,32),28,'#21826d' if g['count']==0 else ink)
 portrait=asset('Avatar_Ivan').crop((400,0,760,360)).resize((180,180),Image.Resampling.LANCZOS)
 portrait.putalpha(ImageChops.multiply(portrait.getchannel('A'),scaled('Avatar_Mask',180,180).getchannel('A')));im.alpha_composite(portrait,(502,44));put(im,'Avatar_Frame',(502,44,180,180))
 for i,key in enumerate(['boosterHammer','boosterAxe','boosterRam','boosterAtlas']):
  x=26+i*140;y=H-162;put(im,'Booster_Outline',(x-7,y-7,144,148));put(im,'Booster_Disabled' if stock[i]<=0 else 'Booster_Selected' if selection==i else 'Booster_Default',(x,y,126,126),True);put(im,key,(x+11,y+7,104,104));put(im,'Badge_Count',(x+88,y+90,44,44));text(im,str(stock[i]),(x+90,y+89,40,44),25,'#ffffff')
 put(im,'Button_Settings',(590,H-149,98,98));put(im,'Icon_Settings',(614,H-126,50,50))
 if hint:text(im,hint,(34,6,652,28),19,'#ffffff')
def loadlevel(n):return json.loads((R/f'Data/Levels/C01_L{n:03}.json').read_text())
@lru_cache(maxsize=50)
def base(n):
 l=loadlevel(n);c=l['columns'];r=l['rows'];cell=min(676/c,(H-460)/r);cy=H/2+20;out=asset('Gameplay_Backdrop').resize((W,H),Image.Resampling.LANCZOS)
 p=PROJECT/'Assets/HeartOfTheRain/M47/Art/Boards'/f'C01_L{n:03}_Surface.png';surface=img(p);surface=surface.resize((round(surface.width*cell/64),round(surface.height*cell/64)),Image.Resampling.LANCZOS);out.alpha_composite(surface,((W-surface.width)//2,round(cy-surface.height/2)))
 mask=Image.open(p.with_name(p.name.replace('Surface','Mask'))).convert('L').resize(surface.size,Image.Resampling.LANCZOS);fullmask=Image.new('L',(W,H));fullmask.paste(mask,((W-surface.width)//2,round(cy-surface.height/2)))
 for e in l.get('deliveryExits',[]):
  m=img(M/'Art/BoardKit/Exit_Marker.png').resize((round(.78*cell),round(.39*cell)),Image.Resampling.LANCZOS);out.alpha_composite(m,(round(W/2+(e['x']-(c-1)/2)*cell-m.width/2),round(cy-(e['y']-.39-(r-1)/2)*cell-m.height/2)))
 return out,fullmask,cell
def board(n,draws=None,shake=(0,0),canvas=None):
 l=loadlevel(n);bg,mask,cell=base(n);out=bg.copy() if canvas is None else canvas.copy();cy=H/2+20;c=l['columns'];r=l['rows']
 if draws is None:
  draws=[dict(bank='body',key='tile'+str(g['color']),atlas=0,x=g['x'],y=g['y'],sx=1,sy=1,angle=0,alpha=1,masked=True,age=0) for g in l['initialTiles']]
  draws += [dict(bank='body',key=('pail_Full' if o['family']=='pail' else o['family']+'_'+str(o['hp'])),atlas=0,x=o['x'],y=o['y'],sx=1,sy=1,angle=0,alpha=1,masked=True,age=0) for o in l['obstacles']]
 layer=Image.new('RGBA',(W,H));has=False
 for d in draws:
  index=old.frame_index(d)
  if index is None or d['alpha']<=.001:continue
  raw,ppu=old.raw(d['bank'],d['key'],d['atlas'],index);w=max(1,round(raw.width/ppu*cell*d['sx']));h=max(1,round(raw.height/ppu*cell*d['sy']));im=old.resized(d['bank'],d['key'],d['atlas'],index,w,h,round(d['angle'],1)%360)
  tint=(d.get('red',1),d.get('green',1),d.get('blue',1));glow=d.get('glow',0)
  if tint!=(1,1,1):
   ar=np.array(im);ar[:,:,:3]=(ar[:,:,:3]*np.array(tint)).clip(0,255).astype('uint8');im=Image.fromarray(ar)
  if glow>.001:
   ar=np.array(im);a=im.getchannel('A');near=a.filter(ImageFilter.MinFilter(9));edge=np.clip((np.array(a).astype(float)-np.array(near))*3/255,0,1);strength=(glow*(.22+.78*edge))[:,:,None];ar[:,:,:3]=np.minimum(255,ar[:,:,:3]*(1-strength)+np.array([255,255,245])*strength).astype('uint8');im=Image.fromarray(ar)
  if d['alpha']<.999:im=im.copy();im.putalpha(im.getchannel('A').point(lambda a:round(a*d['alpha'])))
  x=round(W/2+(d['x']-(c-1)/2+shake[0])*cell-im.width/2);y=round(cy-(d['y']-(r-1)/2+shake[1])*cell-im.height/2)
  if d['masked']:layer.alpha_composite(im,(x,y));has=True
  else:
   if has:layer.putalpha(ImageChops.multiply(layer.getchannel('A'),mask));out.alpha_composite(layer);layer=Image.new('RGBA',(W,H));has=False
   out.alpha_composite(im,(x,y))
 if has:layer.putalpha(ImageChops.multiply(layer.getchannel('A'),mask));out.alpha_composite(layer)
 return out
def dialog(im,state,n):
 im.alpha_composite(Image.new('RGBA',(W,H),(4,18,26,199)));x=80;y=(H-584)//2;put(im,'Panel_Modal',(x,y,560,584),True)
 titles={'pause':'Take a breath','win':'Level complete!','lose':'Out of moves','intro':'Clear these targets','tutorial':'Your first match'}
 bodies={'pause':'Your board will be right here.','win':'The village is one step closer to flowing again.','lose':'Try a new route through the obstacles.','intro':'Clear the targets to restore the village.','tutorial':'Swap two neighboring tiles to line up three of the same kind.'}
 text(im,titles[state],(x+34,y+30,492,75),32,ink);lines(im,bodies[state],(x+48,y+125,464,88),22,ink)
 def button(label,bx,by,w,h,bg='Button_Teal'):put(im,bg,(x+bx,y+by,w,h),True);text(im,label,(x+bx,y+by-4,w,h),26,cream)
 if state=='pause':
  for dx,label,key,bg in [(50,'Sound\nOn','Icon_Sound','Button_Teal'),(290,'Haptics\nOff','Icon_Haptic','Button_Disabled')]:
   put(im,bg,(x+dx,y+230,220,92),True);put(im,key,(x+dx+18,y+251,44,44));text(im,label,(x+dx+66,y+230,140,80),20,cream)
  button('Resume',64,342,432,94);button('Restart level',64,446,432,88,'Button_Burgundy')
 elif state=='intro':
  goals=loadlevel(n)['goals'];span=min(424,len(goals)*108);gw=span/len(goals)
  for i,g in enumerate(goals):
   gx=x+280-span/2+i*gw;put(im,goal_key(g['family']),(gx+(gw-72)/2,y+249,72,72));text(im,str(g['count']),(gx,y+329,gw,42),30)
  button('Play',64,446,432,94)
 else:
  if state=='win':
   put(im,'Focus_Ring',(x+204,y+228,152,152));put(im,'HeartEmblem',(x+226,y+245,108,108));put(im,'Star_Gold',(x+146,y+271,36,36));put(im,'Star_Gold',(x+378,y+271,36,36))
  else:
   put(im,'Button_Settings',(x+212,y+236,136,136),True);put(im,'Icon_Retry' if state=='lose' else 'Icon_Hand',(x+239,y+258,82,82))
  button('Continue' if state=='win' else 'Try again' if state=='lose' else 'Got it',64,446,432,94)
 return im
def still(n,state=None,selection=-1):
 l=loadlevel(n);im=board(n);hint=['Hammer: choose a tile','Axe: choose a column','Ram: choose a row',''][selection] if selection>=0 else ''
 hud(im,n,l['movesProposal'],l['goals'],selection=selection,hint=hint)
 if selection>=0:
  cell=base(n)[2];x=4;y=4;put(im,'Focus_Cell',(W/2+(x-(l['columns']-1)/2-.5)*cell,H/2+20-(y-(l['rows']-1)/2+.5)*cell,cell,cell))
 if state:dialog(im,state,n)
 return im.convert('RGB')
def save_preview(im,path):
 fd,temporary=tempfile.mkstemp(suffix='.png');os.close(fd)
 try:
  im.save(temporary);os.replace(temporary,path)
 finally:
  if os.path.exists(temporary):os.unlink(temporary)
def run_stills():
 for n in [1,10,18,40,41,50]:save_preview(still(n),R/f'Previews/Gameplay_Level_{n:02}.png')
 for s in ['intro','pause','tutorial','win','lose']:save_preview(still(18,s),R/f'Previews/UI_{s}.png')
 save_preview(still(40,selection=0),R/'Previews/UI_Booster_Targeting.png')
 overview=Image.new('RGB',(1440,1000),'#10232e');d=ImageDraw.Draw(overview);d.text((32,20),'HEART OF THE RAIN',font=font(34),fill=cream);d.text((32,68),'Gameplay UI / approved Ivory & Slate / R11',font=font(21,False),fill='#b9d2d2')
 for i,n in enumerate([10,18,40,41]):
  im=still(n).resize((330,587),Image.Resampling.LANCZOS);overview.paste(im,(28+i*354,126));text(overview,f"LEVEL {n:02}",(28+i*354,730,330,32),23,cream);l=loadlevel(n);text(overview,f"{l['columns']} × {l['rows']}  ·  {len(l['goals'])} goals",(28+i*354,769,330,32),19,'#b9d2d2',False)
 d.text((32,860),'Direction A applied to UI, all 50 board surfaces, and background.',font=font(23),fill=cream);d.text((32,907),'Approved tile, obstacle and booster artwork retained; gameplay unchanged.',font=font(19,False),fill='#b9d2d2');save_preview(overview,R/'Previews/Gameplay_UI_Overview.png')
 sheet=Image.new('RGBA',(1440,1060),'#10232e');d=ImageDraw.Draw(sheet);d.text((30,24),'Clean gameplay interface states',font=font(34),fill=cream)
 for i,(s,label) in enumerate([('intro','Level goals'),('tutorial','Tutorial'),('pause','Pause & settings'),('win','Success'),('lose','Out of moves')]):
  im=still(18,s).resize((264,469));sheet.paste(im,(24+i*285,100));text(sheet,label,(24+i*285,584,264,36),20,cream)
 d.text((30,666),'Reusable sprites + live text + Unity Canvas controls',font=font(26),fill=cream);d.text((30,715),'Result panels shown as UI samples; no claim that the preview completes the level.',font=font(19,False),fill='#b9d2d2')
 for i,key in enumerate(['Panel_Goals','Panel_Moves','Button_Teal','Button_Burgundy','Booster_Default','Booster_Selected','Button_Settings','Badge_Count']):
  put(sheet,key,(30+i*174,800,154,150),True);text(sheet,key.replace('_','\n'),(24+i*174,960,166,65),15,cream)
 save_preview(sheet,R/'Previews/Gameplay_UI_States.png')
 comparison=Image.new('RGB',(1488,1418),'#10232e');d=ImageDraw.Draw(comparison);d.text((24,16),'DIRECTION A / APPLIED TO GAMEPLAY ASSETS',font=font(30),fill=cream)
 for x,label,path in [(16,'PREVIOUS / MINT',R/'Source/Review_Baseline_Level40.png'),(752,'APPROVED A / IVORY & SLATE',R/'Previews/Gameplay_Level_40.png')]:
  d.text((x,64),label,font=font(23),fill='#b9d2d2');comparison.paste(Image.open(path).convert('RGB'),(x,100))
 save_preview(comparison,R/'Previews/Gameplay_UI_Before_After.png')
 save_preview(still(40),R/'Previews/Gameplay_Direction_A_R11.png')
 print('Gameplay and UI stills rendered with Direction A',flush=True)

def run_video(name):
 path=R/f'Previews/Gameplay_{name}.mp4';cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(path)];proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 with gzip.open(R/f'Validation/Playback_{name}.jsonl.gz','rt') as stream:
  for line in stream:
   f=json.loads(line);im=board(f['level'],f['draws'],(f.get('shakeX',0),f.get('shakeY',0)));stock=[3]*4;stock[['Hammer','Axe','Ram','Atlas'].index(name)]=3 if f['time']<.75 else 2;hud(im,f['level'],f['moves'],f['goals'],stock);proc.stdin.write(im.convert('RGB').tobytes())
 proc.stdin.close();assert proc.wait()==0;print('Gameplay clip',name,flush=True)
if __name__=='__main__':
 if len(sys.argv)>1:run_video(sys.argv[1])
 else:run_stills()
