"""Prepare actual Android video contact sheets; a human/agent must inspect them."""
from pathlib import Path
import json, hashlib, subprocess
import imageio_ffmpeg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/IndividualFall'

def run():
    sha = hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    touch = json.loads((OUT/'Touch/Report.json').read_text())
    assert touch['apk_sha256'] == sha and len(touch['cases']) == 7
    metrics = []
    for case in touch['cases']:
        mode = case['mode']
        assert not case['failures'] and case['status'] == 'PASS_ACTUAL_OBSTACLE_FALL_INPUT'
        frames = OUT/'Touch/Frames'/mode
        frames.mkdir(parents=True, exist_ok=True)
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-loglevel', 'error', '-y', '-i', str(OUT/'Touch'/f'{mode}.mp4'), '-vf', 'fps=30', '-frames:v', '150', str(frames/'%03d.png')], check=True)
        crop = (20, 760, 350, 1160) if mode == 'EdgeLeft' else (550, 760, 880, 1160) if mode == 'EdgeRight' else (220, 710, 680, 1210)
        ids = list(range(15, 136, 6))
        width, height = crop[2]-crop[0], crop[3]-crop[1]
        sheet = Image.new('RGB', (width*5, (height+25)*5), '#172536')
        draw = ImageDraw.Draw(sheet)
        for i, n in enumerate(ids):
            frame = frames/f'{n:03d}.png'
            if not frame.exists(): continue
            x, y = i%5*width, i//5*(height+25)
            sheet.paste(Image.open(frame).crop(crop), (x, y+25))
            draw.text((x+5, y+5), f'{mode} {n/30:.2f}s', fill='white')
        sheet.save(OUT/f'{mode}_Sequence.png')
        poses = [p for p in case['poses'] if 0 < p['age'] < case['seconds']]
        assert len(poses) >= 4
        if mode == 'LargeGap':
            detail = Image.new('RGB', (1840, 2625), '#172536')
            labels = ImageDraw.Draw(detail)
            for i, n in enumerate(range(70, 90)):
                x, y = i%4*460, i//4*525
                detail.paste(Image.open(frames/f'{n:03d}.png').crop((220,710,680,1210)), (x,y+25))
                labels.text((x+5,y+5), f'LargeGap {n/30:.3f}s', fill='white')
            detail.save(OUT/'LargeGap_Detail.png')
        metrics.append({'mode': mode, 'movingSamples': len(poses), 'routeSeconds': case['seconds'], 'plate': f'{mode}_Sequence.png'})
    report = {'status': 'CAPTURED_REQUIRES_VISUAL_REVIEW', 'apk_sha256': sha, 'cases': metrics,
              'scope': 'Seven actual LDPlayer inputs and native sampled poses on transient fixtures. Slow deliberately stalls180ms. No physical-device or exact competitor-parity claim.'}
    (OUT/'Visual_Review.json').write_text(json.dumps(report, indent=2)+'\n')
    cards = ''.join(f'<article><h2>{c["mode"]}</h2><video controls preload="metadata" src="Touch/{c["mode"]}.mp4"></video><p><a href="{c["plate"]}">Frame sequence</a> &middot; <a href="Touch/{c["mode"]}_Report.json">Native poses</a></p></article>' for c in metrics)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Individual tile refill review</title><style>body{font:16px system-ui;background:#172536;color:#f5f5f5;margin:30px;max-width:1400px}p{line-height:1.5}a{color:#a5dcff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}video{width:100%;max-height:620px;background:#000}button,select{font:inherit;padding:8px;margin:5px}</style><h1>Individual tile refill</h1><p>Tiles start individually and follow continuous routes through consecutive gravity snapshots. Each tile settles at its final cell. A necessary yield remains local to that tile; independent columns keep moving. Artwork, level masks and model gravity rules are preserved.</p><p><label>Playback speed <select onchange="document.querySelectorAll('video').forEach(v=>v.playbackRate=Number(this.value))"><option value="1">Normal</option><option value=".5">Half speed</option><option value=".25">Quarter speed</option></select></label><button onclick="document.querySelectorAll('video').forEach(v=>v.pause())">Pause all</button></p><div class="grid">''' + cards + '''<article><h2>Reference: obstacle contact</h2><video controls preload="metadata" src="../ObstacleFall/MV_Obstacle_Gap.mp4"></video><p>Earlier Match Villains recording. Layout and mechanics differ; particles obscure part of the movement. It does not establish exact internal timing or identical-board parity.</p></article><article><h2>Preceding app build</h2><video controls preload="metadata" src="../ObstacleFall/Touch/Hammer.mp4"></video><p>Historical single-gap fixture from review22. The new LargeGap case adds a cabinet clear beneath surviving stones; these are different fixtures.</p></article></div><p><a href="Native_Checks.json">Native route checks</a> &middot; <a href="Visual_Review.json">Visual review status</a> &middot; <a href="../../../Codex_Handoff/Documentation/23_INDIVIDUAL_TILE_REFILL_REVIEW.md">Implementation and limitations</a></p></html>'''
    page = page.replace('<h2>LargeGap</h2>', '<h2>Large gap beneath surviving obstacles</h2><p><a href="LargeGap_Detail.png">Detailed flight frames</a></p>')
    (OUT/'Comparison.html').write_text(page, encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__': run()
