"""Build native review plates without assigning a visual approval verdict."""
from pathlib import Path
import argparse, hashlib, json, datetime as dt
import imageio_ffmpeg
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/GameplayAudit'

def run():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=OUT);OUT=parser.parse_args().out.resolve()
    report=json.loads((OUT/'Touch/Report.json').read_text());artifacts={};plates=[]
    for case in report['cases']:
        mode=case['mode'];video=OUT/'Touch'/(mode+'.mp4')
        stream=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24',output_params=['-vf','fps=12']);meta=next(stream);w,h=meta['size']
        assert meta['duration']>2 and w<h, (mode,meta)
        chosen=[9,11,13,15,17,19,21,24,28,34,42,54];frames=[]
        for index,raw in enumerate(stream):
            if index in chosen:
                im=Image.frombytes('RGB',(w,h),raw);cx=case['toX'];cy=case['toY']-(90 if mode.startswith('Obstacle') else 0)
                half=245;box=(max(0,cx-half),max(0,cy-half),min(w,cx+half),min(h,cy+half));im=im.crop(box);im.thumbnail((290,290));frames.append((index/12,im))
            if index>chosen[-1]:break
        stream.close();assert len(frames)==12
        sheet=Image.new('RGB',(1200,1010),(22,27,36));draw=ImageDraw.Draw(sheet);draw.text((15,10),mode+' | actual Android swipe | native video samples; recording affects frame cadence',fill='white')
        for i,(at,im) in enumerate(frames):
            x=(i%4)*300;y=35+(i//4)*320;sheet.paste(im,(x,y));draw.text((x+8,y+294),f'{at:.3f}s',fill='white')
        path=OUT/(mode+'_Sequence.png');sheet.save(path);plates.append(path.name)
        for path in [path,video,OUT/'Touch'/(mode+'_Report.json')]:artifacts[path.relative_to(OUT).as_posix()]=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
    review={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','apk_sha256':report['apk_sha256'],'scope':'Actual Android movies and cropped native display plates; review required. Capture and dispatch clocks are not synchronized, and video cadence is not a performance benchmark.','plates':plates,'artifactSHA256':artifacts}
    (OUT/'Visual_Review.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps({'status':review['status'],'plates':plates},indent=2))

if __name__=='__main__':run()
