"""Drive an on-screen ad through the SDK's own controls only: the skip icon, then the close icon.
A tap is sent only after the native tree shows that control visible at its real position.
Usage: finishad.py <pkg> [<wait seconds>]"""
import re, subprocess, sys, time
ADB = r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe'
PKG = sys.argv[1]
LIMIT = float(sys.argv[2]) if len(sys.argv) > 2 else 90
def run(*a, timeout=40):
    return subprocess.run([ADB, *a], capture_output=True, timeout=timeout).stdout
def tree():
    text = run('shell', 'dumpsys', 'activity', 'top').decode('utf-8', 'replace')
    start = text.rfind('ACTIVITY ' + PKG + '/com.yandex')
    if start < 0:
        return None
    seg = text[start:]
    return [l for l in seg[seg.find('View Hierarchy'):].splitlines() if re.match(r'\s+(yads|com\.monetization|android\.widget)', l)]
begun = time.time(); skipped = False; absent = 0
while time.time() - begun < LIMIT:
    lines = tree()
    t = round(time.time() - begun, 1)
    if lines is None:
        absent += 1
        if absent >= 3:
            print(t, 'ad closed', flush=True); break
        time.sleep(0.5); continue
    absent = 0
    at = next((i for i, l in enumerate(lines) if re.search(r' 642,\d+-698,\d+', l)), None)
    near = lines[at:at + 4] if at is not None else []
    bar_gone = any(re.search(r'\bG\S* .*\b0,0-720,80\b', l) for l in lines)
    if bar_gone:
        print(t, 'bar hidden: this layout has no usable control', flush=True); break
    if not skipped and any(re.search(r'yads\.dc1\{\w+ V\S* \S+ 0,0-36,36', l) for l in near):
        print(t, 'pressing skip', flush=True); run('shell', 'input', 'tap', '668', '104'); skipped = True; time.sleep(2); continue
    if any(re.search(r'yads\.dc1\{\w+ V\S* \S+ 10,10-46,46', l) for l in near):
        print(t, 'pressing close', flush=True); run('shell', 'input', 'tap', '670', '104'); time.sleep(2); continue
    time.sleep(0.5)
else:
    print('time limit', flush=True)
print('top', run('shell', 'dumpsys', 'activity', 'activities').decode('utf-8', 'replace').split('topResumedActivity=')[1][:90].strip())
