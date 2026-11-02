"""Prepare R2 video sheets; visual approval is deliberately separate."""
from pathlib import Path
import json, hashlib, subprocess, shutil
import imageio_ffmpeg
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/M70R2'

def run():
    touch=json.loads((OUT/'Touch/Report.json').read_text());sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    assert touch['apk_sha256']==sha and len(touch['cases'])==10
    metrics=[]
    for case in touch['cases']:
        mode=case['mode'];assert case['status']=='PASS_NATIVE_DEVICE_M70R2_CREATION' and not case['failures']
        folder=OUT/'Touch/Frames'/mode;folder.mkdir(parents=True,exist_ok=True)
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-loglevel','error','-y','-i',str(OUT/'Touch'/f'{mode}.mp4'),'-vf','fps=30',str(folder/'%03d.png')],check=True)
        crop=(230,620,730,1180) if mode.startswith('Match') else (20,330,880,1240)
        ids=list(range(20,60,2)) if mode.startswith('Match') else list(range(15,136,6))
        width,height=crop[2]-crop[0],crop[3]-crop[1];scale=min(1,450/width);w,h=round(width*scale),round(height*scale)
        sheet=Image.new('RGB',(w*4,(h+25)*((len(ids)+3)//4)),'#172536');draw=ImageDraw.Draw(sheet)
        for i,n in enumerate(ids):
            p=folder/f'{n:03d}.png'
            if not p.exists():continue
            x,y=i%4*w,i//4*(h+25);sheet.paste(Image.open(p).crop(crop).resize((w,h)),(x,y+25));draw.text((x+4,y+5),f'{mode} {n/30:.3f}s',fill='white')
        sheet.save(OUT/f'{mode}_Sequence.png')
        born=[p for p in case['poses'] if p['key']=='Create' or p['key'].endswith('_Create')]
        metrics.append({'mode':mode,'columns':case['columns'],'rows':case['rows'],'formationSamples':len(born),'distinctFormationFrames':len({p['sprite'] for p in born}),'pauseChecked':case['pauseChecked'],'retryChecked':case['retryChecked'],'retryUISupplement':case['mode']=='GrantIntro','failureChecked':case['failureChecked'],'gateHeld':case['gateHeld'],'plate':f'{mode}_Sequence.png'})
    shutil.copyfile(ROOT/'.verification-cache/M70R2/Package/Review/Creation_Playback_Poster.png',OUT/'Supplied_Creation_Poster.png')
    shutil.copyfile(ROOT/'.verification-cache/M70R2/Package/Review/Powerup_Creation_Playback.mp4',OUT/'Supplied_Creation_Playback.mp4')
    review={'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','apk_sha256':sha,'cases':metrics,'scope':'Decoded actual Android recordings and sampled native sprite poses. Supplied poster/movie are offline reference assets, not Unity/device evidence. Lifecycle controls are identified in each raw report; no physical performance claim.'}
    (OUT/'Visual_Review.json').write_text(json.dumps(review,indent=2)+'\n')
    cards=''.join(f'<article><h2>{c["mode"]} ({c["columns"]} x {c["rows"]})</h2><video controls preload="metadata" src="Touch/{c["mode"]}.mp4"></video><p><a href="{c["plate"]}">Frame sheet</a> &middot; <a href="Touch/{c["mode"]}_Report.json">Native sprite poses</a></p></article>' for c in metrics)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>M70 R2 creation playback</title><style>body{font:16px system-ui;background:#172536;color:#f5f5f5;margin:30px;max-width:1400px}p{line-height:1.5}a{color:#a5dcff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}video{width:100%;max-height:620px;background:#000}button,select{font:inherit;padding:8px;margin:5px}</style><h1>M70 R2 power-up creation</h1><p><a href="Retry_UI_Sequence.png">Actual pause/restart/Play sequence</a> &middot; <a href="Touch/GrantIntro_Retry_UI.json">Retry review and scope</a></p><p>The requested M70_R2_After_M70.patch is merged into the current pooled renderer. Newborn powers use their authored formation frames, continue during tile falls, and enter idle. Stars follow the piece. Converted bodies fit formation into the existing pre-charge window. Starting-item clocks begin after prewarming and visible gameplay ownership.</p><p>Five real match swipes, two combination swipes, a real intro Play tap, and explicit development controls for starting ownership, pause/retry and injected texture failure. Grant boards retain their authored layouts. These are targeted emulator checks; the injected failure is not a normal-launch recording.</p><p><label>Playback speed <select onchange="document.querySelectorAll('video').forEach(v=>v.playbackRate=Number(this.value))"><option value="1">Normal</option><option value=".5">Half speed</option><option value=".25">Quarter speed</option></select></label><button onclick="document.querySelectorAll('video').forEach(v=>v.pause())">Pause all</button></p><div class="grid">'''+cards+'''<article><h2>Supplied offline creation preview</h2><video controls preload="metadata" src="Supplied_Creation_Playback.mp4"></video><p>Package artwork/timing reference, not a native capture. <a href="Supplied_Creation_Poster.png">Supplied poster</a>.</p></article></div><p><a href="Native_Checks.json">Native integration checks</a> &middot; <a href="Supplied_Checks.json">Executed supplied Unity runner</a> &middot; <a href="Visual_Review.json">Visual review status</a> &middot; <a href="../../../Codex_Handoff/Documentation/24_M70_R2_CREATION_REVIEW.md">Changes and limitations</a></p></html>'''
    (OUT/'Comparison.html').write_text(page,encoding='utf-8');print(json.dumps(review,indent=2))

if __name__=='__main__':run()
