"""Compose timestamp-labelled evidence sheets; no motion endpoint inference."""
import argparse,hashlib,json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main(out):
 font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16);small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',14)
 manifest={'status':'PRESENTED_CURRENT_PTS_SAMPLES_FOR_ACTUAL_REVIEW','scope':'Automatically selected original decoded samples and native stills. Timestamp labels are source PTS, not physical display/input times. Selection makes no endpoint or smoothness verdict.','sheets':[]}
 for level in (4,14,31,33):
  folder=out/'TimingVisual'/('L'+str(level));index=json.loads((folder/'PTS_Index.json').read_text('utf-8-sig'));frames=index['frames'];n=min(24,len(frames));selected=[frames[round(i*(len(frames)-1)/max(1,n-1))] for i in range(n)]
  sets=[('Motion_Overview_Sheet.png',selected),('Initial_Samples_Sheet.png',frames[:24])]
  for name,values in sets:
   cols=6;thumbW,thumbH=160,285;cellW,cellH=172,318;header=66;canvas=Image.new('RGB',(cols*cellW,header+math.ceil(len(values)/cols)*cellH),(8,28,50));draw=ImageDraw.Draw(canvas)
   draw.text((12,8),f'Checkpoint79 L{level} — {name.removesuffix("_Sheet.png").replace("_"," ")}',font=font,fill=(245,214,128));draw.text((12,34),'Original PTS samples; selection is not an animation endpoint verdict.',font=small,fill=(225,236,245))
   for i,row in enumerate(values):
    path=ROOT/row['file'];assert path.is_relative_to(out) and sha(path)==row['sha256'];picture=Image.open(path).convert('RGB');picture.thumbnail((thumbW,thumbH));x=(i%cols)*cellW+6;y=header+(i//cols)*cellH;canvas.paste(picture,(x,y));draw.text((x,y+thumbH+4),f"{row['pts']:.6f}s  #{Path(row['file']).stem}",font=small,fill=(240,240,240))
   dest=folder/name;canvas.save(dest);manifest['sheets'].append({'file':dest.relative_to(out).as_posix(),'sha256':sha(dest),'index':(folder/'PTS_Index.json').relative_to(out).as_posix(),'indexSHA256':sha(folder/'PTS_Index.json'),'contributors':values})
 (out/'TimingVisual/Sheets.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print('Presented',len(manifest['sheets']),'current timestamped sheets')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'Verification/Evidence/Gameplay79');main(p.parse_args().out.resolve())
