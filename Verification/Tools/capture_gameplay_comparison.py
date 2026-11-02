"""Capture installed games without clearing data; timings are video presentation evidence."""
import argparse
import datetime as dt
import json
import subprocess
import time
from pathlib import Path
import imageio_ffmpeg
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/GameplayComparison'
ADB='C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe'

def run():
    p=argparse.ArgumentParser();p.add_argument('--serial',default='127.0.0.1:5555')
    p.add_argument('mode',choices=['snap','record','sheet']);p.add_argument('name')
    p.add_argument('--seconds',type=int,default=12);p.add_argument('--tap',type=int,nargs=2)
    p.add_argument('--swipe',type=int,nargs=5);p.add_argument('--wait',type=float,default=.8)
    p.add_argument('--start',type=float,default=0);p.add_argument('--end',type=float,default=8);p.add_argument('--fps',type=int,default=8)
    p.add_argument('--out',type=Path,default=OUT)
    p.add_argument('--size',help='Optional Android encoder size, e.g. 720x1280')
    a=p.parse_args();destination=a.out.resolve();destination.mkdir(parents=True,exist_ok=True)
    def adb(*parts):return subprocess.run([ADB,'-s',a.serial,*map(str,parts)],capture_output=True,check=True,timeout=90).stdout
    if a.mode=='snap':
        path=destination/(a.name+'.png');path.write_bytes(adb('exec-out','screencap','-p'));print(path);return
    video=destination/(a.name+'.mp4')
    if a.mode=='record':
        remote='/sdcard/HOTR_Gameplay_Comparison.mp4'
        size=['--size',a.size] if a.size else []
        proc=subprocess.Popen([ADB,'-s',a.serial,'shell','screenrecord',*size,'--time-limit',str(a.seconds),'--bit-rate','8000000',remote],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        started=time.monotonic();time.sleep(a.wait)
        action_start=time.monotonic()-started
        if a.tap:adb('shell','input','tap',*a.tap)
        if a.swipe:adb('shell','input','swipe',*a.swipe)
        proc.communicate(timeout=a.seconds+15);assert proc.returncode==0
        adb('pull',remote,video)
        (destination/(a.name+'.json')).write_text(json.dumps({'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'serial':a.serial,'tap':a.tap,'swipe':a.swipe,'action_adb_dispatch_seconds_after_record_command':action_start,'video':video.name,'scope':'Actual Android screenrecord. Dispatch clock and video clock are not synchronized; no physical touch/GPU profiler claim.'},indent=2)+'\n',encoding='utf-8',newline='\n')
        print(video);return
    frames=destination/a.name;frames.mkdir(exist_ok=True)
    reader=imageio_ffmpeg.read_frames(str(video),pix_fmt='rgb24',output_params=['-vf',f'fps={a.fps}'])
    meta=next(reader);w,h=meta['size'];selected=[]
    for i,raw in enumerate(reader):
        t=i/a.fps
        if t<a.start:continue
        if t>a.end:break
        im=Image.frombytes('RGB',(w,h),raw);im.save(frames/f'{t:06.3f}.png')
        thumb=im.copy();thumb.thumbnail((180,320));selected.append((t,thumb))
    reader.close()
    sheet=Image.new('RGB',(180*8,345*((len(selected)+7)//8)),(26,29,34));draw=ImageDraw.Draw(sheet)
    for i,(t,im) in enumerate(selected):
        x=(i%8)*180;y=(i//8)*345;sheet.paste(im,(x,y));draw.text((x+4,y+322),f'{t:.3f}s',fill='white')
    path=destination/(a.name+'_Sheet.png');sheet.save(path);print(path)

if __name__=='__main__':run()
