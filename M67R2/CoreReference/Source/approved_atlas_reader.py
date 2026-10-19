"""Render the actual C#-sampled draw stream; no gameplay rules are implemented here."""
from pathlib import Path
import json,gzip,math,subprocess,sys
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter
import numpy as np
R=Path(__file__).resolve().parents[1];PROJECT=(R.parent.parent/'Unity') if (R.parent.parent/'Unity').exists() else R.parent/'Project/Heart_of_the_Rain_M66/Unity';U=PROJECT/'Assets/HeartOfTheRain';A=U/'M46';W,H=720,1280
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,b=False):return ImageFont.truetype(BOLD if b else FONT,n)
def read(p):return json.loads(Path(p).read_text())
visuals={b['id']:b for b in read(A/'Data/Visual_Catalog.json')['sprites']}
powers=[]
for i,name in enumerate(read(U/'Chapter01M07/Data/AssetCatalog.json')['names']):
 base=U/('Chapter01M07' if i<6 or i>=12 else 'Chapter01M04' if i in [9,10] else 'Chapter01M05')
 m=read(base/'Data'/f'{name}.json');m['path']=base/'Sprites'/f'{name}_Atlas.png';powers.append(m)
obstacles={}
for c in read(A/'Data/FX_Catalog.json')['clips']:
 m=read(A/c['metadata']);m['path']=(A/c['metadata']).parent;obstacles[c['family']+'/'+c['name']]=m
@lru_cache(maxsize=160)
def image(p):return Image.open(p).convert('RGBA')
@lru_cache(maxsize=600)
def raw(bank,key,atlas,index):
 if bank=='body':
  b=visuals[key];im=image(A/b['path']);return im,im.width/b['canvasCells']
 m=powers[atlas] if bank=='power' else obstacles[key];f=m['frames'][index]
 im=image(m['path']) if bank=='power' else image(m['path']/m['pages'][f['page']]);w=f.get('width',f.get('w'));h=f.get('height',f.get('h'));return im.crop((f['x'],im.height-f['y']-h,f['x']+w,im.height-f['y'])),m['pixelsPerUnit']
def frame_index(d):
 if d['bank']=='body':return 0
 m=powers[d['atlas']] if d['bank']=='power' else obstacles[d['key']]
 if d['bank']=='power':
  c=next((c for c in m['clips'] if c['name']==d['key']),None)
  if c is None:raise ValueError(('missing clip',d['atlas'],d['key']))
  i=int(max(0,d['age'])*c['fps']);n=c['count']
  if c['loop']:i%=n
  elif i>=n:
   if c['endBehavior']=='hide':return None
   i=n-1
  return c['start']+i
 i=int(max(0,d['age'])*m['fps']);n=len(m['frames'])
 if m['loop']:return i%n
 if i>=n and not m['holdLast']:return None
 return min(i,n-1)
@lru_cache(maxsize=420)
def resized(bank,key,atlas,index,w,h,angle):
 im,_=raw(bank,key,atlas,index);im=im.resize((w,h),Image.Resampling.LANCZOS)
 if angle:im=im.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
 return im
