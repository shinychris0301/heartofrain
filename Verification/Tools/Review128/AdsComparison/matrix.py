"""One setting at a time on the minimal app. Fresh process per case; never taps the ad.
A case PASSES if the SDK's top bar stays up and its skip/close icon becomes visible.
Usage: matrix.py <pkg> <mask> [<mask> ...]"""
import re, subprocess, sys, time
ADB = r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe'
PKG = sys.argv[1]
def run(*a, timeout=40):
    return subprocess.run([ADB, *a], capture_output=True, timeout=timeout).stdout
def tap(x, y):
    run('shell', 'input', 'tap', str(x), str(y)); time.sleep(0.5)
def tree():
    text = run('shell', 'dumpsys', 'activity', 'top').decode('utf-8', 'replace')
    start = text.rfind('ACTIVITY ' + PKG + '/com.yandex')
    if start < 0:
        return None
    seg = text[start:]
    return [l for l in seg[seg.find('View Hierarchy'):].splitlines() if re.match(r'\s+(yads|com\.monetization|android\.widget)', l)]
for mask in [int(m) for m in sys.argv[2:]]:
    run('shell', 'am', 'force-stop', PKG); time.sleep(1)
    run('shell', 'monkey', '-p', PKG, '-c', 'android.intent.category.LAUNCHER', '1'); time.sleep(5)
    for i in range(7):
        if mask & (1 << i):
            tap(360, 692 + i * 95)
    tap(360, 400)
    if not mask & 64:
        time.sleep(5); tap(360, 560)
    begun = time.time(); collapsed = None; icon = None; seen = False
    while time.time() - begun < 32 and icon is None:
        lines = tree()
        if lines is None:
            time.sleep(0.5); continue
        seen = True
        t = time.time() - begun
        if collapsed is None and any(re.search(r'\bG\S* .*\b0,0-720,80\b', l) for l in lines):
            collapsed = round(t, 1)
        # The icon sits inside the 642,12 container and gains a real size when it appears.
        at = next((i for i, l in enumerate(lines) if re.search(r' 642,\d+-698,\d+', l)), None)
        if at is not None and any(re.search(r'yads\.dc1\{\w+ V\S* \S+ 0,0-36,36', l) for l in lines[at:at + 4]) and not collapsed:
            icon = round(t, 1)
    verdict = 'PASS icon at %ss' % icon if icon else ('FAIL bar hidden at %ss' % collapsed if collapsed else ('no ad shown' if not seen else 'inconclusive'))
    print('mask=%2d %s' % (mask, verdict), flush=True)
run('shell', 'am', 'force-stop', PKG)
