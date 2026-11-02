"""Build a local checkpoint79 evidence gallery from actual reports."""
import argparse,html,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main(out):
 read=lambda name:json.loads((out/name).read_text('utf-8-sig'))
 report=read('FirstPose/Report.json');analysis=read('Performance_Analysis.json');source=read('Source_SHA256.json')
 esc=lambda value:html.escape(str(value))
 def image(name):return '<a href="'+esc(name)+'"><img loading="lazy" src="'+esc(name)+'"><span>'+esc(name)+'</span></a>'
 rows=[]
 for level in (4,14,31,33):
  for mode in ('update','coroutine'):
   pair=[r for r in report['rows'] if r['level']==level and r['dispatch']==mode and not r['holdWorker']]
   control=next(r for r in pair if r['checkpoint78']);now=next(r for r in pair if not r['checkpoint78']);trace=json.loads(now['startupTraceJson'])
   rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in (f'L{level} / {mode}',f"{control['commandMs']:.3f}",f"{now['commandMs']:.3f}",f"{control['presentationAcceptMs']:.3f}",f"{now['presentationAcceptMs']:.3f}",f"{trace['totalWorkerMs']:.3f}",f"{trace['mainInstallMs']:.3f}",f"{trace['holdMs']:.3f}",f"{control['settleSeconds']:.3f}",f"{now['settleSeconds']:.3f}"))+'</tr>')
 headers=['Fixture','Sync startup command ms','Worker startup command ms','Sync presentation ms','Worker presentation ms','79 worker elapsed ms','79 install ms','79 hold ms','78 settle s','79 settle s']
 lifecycle=read('Native/StartupLifecycle79.json');native=[p for r in lifecycle['rows'] for p in r['captures']]
 regression=read('RegressionVisual/Manifest.json');sheets=[p for group in regression['sheets'].values() for p in group]
 timing=[]
 for p in sorted((out/'TimingVisual').rglob('*Sheet.png')):timing.append(p.relative_to(out).as_posix())
 touch=[p.relative_to(out).as_posix() for p in sorted((out/'TouchVisual').rglob('*Sheet.png'))]
 limits=analysis['remainingGates']
 if isinstance(limits,dict):limits=[str(k)+': '+str(v) for k,v in limits.items()]
 else:limits=[v['gate']+': '+v['scope'] if isinstance(v,dict) else str(v) for v in limits]
 body='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Heart of the Rain — checkpoint79</title><style>body{margin:0;background:#081c32;color:#eef3f7;font:16px/1.5 system-ui}main{max-width:1400px;margin:auto;padding:28px}h1,h2{color:#f1cd72}a{color:#8fd6ff}.scroll{overflow:auto}table{border-collapse:collapse;white-space:nowrap}td,th{border:1px solid #426077;padding:8px;text-align:right}td:first-child,th:first-child{text-align:left}.gallery{display:flex;flex-wrap:wrap;gap:14px}.gallery a{display:flex;flex-direction:column;width:280px;font-size:12px}.gallery img{width:100%;height:auto;object-fit:contain}li{margin:7px 0}code{overflow-wrap:anywhere}</style><main><h1>First-pose preparation and snapshot repair · 79</h1><p>The unchanged leading 120 ms swap reaches its board camera before pure managed playback/resource preparation starts on a worker. Input and settlement remain guarded until the complete tail is available. Snapshot cache validity is explicit after duplicate IDs shrink.</p><p>This is targeted QA evidence. Initial command latency, worker elapsed time, tail installation, visible holds and total settlement are separate. Same-APK controls restore the archived synchronous startup helper; the current79 snapshot implementation remains active in both branches. They do not restore the historical application or isolate a model speedup.</p>'''
 body+='<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
 body+='<p>All eight natural pairs are shown, including slower results. The two deliberate worker holds are correctness controls and are excluded from ordinary performance maxima. The full analysis retains post-head Update/Render/interval outliers.</p><p><a href="Performance_Analysis.json">Full timing analysis</a> · <a href="FirstPose/Report.json">Raw Android first-pose report</a> · <a href="Native/Snapshot79.json">Snapshot proof and all direct timing pairs</a> · <a href="Native/Worker79.json">Worker queue/path proof</a> · <a href="Summary.json">Strict summary</a></p>'
 body+='<h2>Native lifecycle captures</h2><p>Actual Unity camera renders, including controlled holds, reload, resume, pause and terminal worker failures. These are untimed native fixtures.</p><div class="gallery">'+''.join(image(p) for p in native)+'</div>'
 if timing:body+='<h2>Current recorded gameplay samples</h2><div class="gallery">'+''.join(image(p) for p in timing)+'</div>'
 if touch:body+='<h2>Native gesture and obstacle samples</h2><p>Original timestamp samples of mixed-power protection, chaining and obstacle refill. These sheets support sampled visual review; precise endpoints and physical display latency are separate.</p><div class="gallery">'+''.join(image(p) for p in touch)+'</div>'
 body+='<h2>Current campaign regression sheets</h2><p>Automated regression covers all 50 boards. Sheets are samples for visual review; their thumbnails are not claims of full-size inspection of every original.</p><div class="gallery">'+''.join(image(p) for p in sheets)+'</div>'
 body+='<h2>Remaining gates</h2><ul>'+''.join('<li>'+esc(v)+'</li>' for v in limits)+'</ul><p>Candidate QA: separate instance2 / emulator-5558. Original QA1/5556 retains78 and its active attempt; main deployment remains64. Historical QA1 timings are cross-instance observations. No physical-device, fresh Match Villains parity, sustained 60 fps or whole-project completion claim.</p></main></html>'
 (out/'Comparison.html').write_text(body,encoding='utf-8');print(out/'Comparison.html')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'Verification/Evidence/Gameplay79');main(p.parse_args().out.resolve())
