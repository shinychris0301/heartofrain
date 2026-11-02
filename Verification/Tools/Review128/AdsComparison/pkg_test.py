"""The minimal script under different package names: same code, only the identifier changes."""
import re, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).parent
M = Path(r'E:\.verification-cache\HOTR128\AdsMin\Game')
ADB = r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe'
PY = sys.executable
builder = M / 'Assets/Minimal128/Editor/MinimalBuild128.cs'
original = builder.read_text('utf-8')
for pkg in sys.argv[1:]:
    tag = 'p' + re.sub(r'\W', '', pkg.split('.')[-1])
    text = re.sub(r'SetApplicationIdentifier\(BuildTargetGroup\.Android,"[^"]+"\)', 'SetApplicationIdentifier(BuildTargetGroup.Android,"%s")' % pkg, original)
    builder.write_text(text, 'utf-8')
    r = subprocess.run([PY, '-I', str(HERE / 'build_min.py'), tag, '36'], capture_output=True, text=True, errors='replace')
    head = r.stdout.splitlines()[:2]
    print(pkg, head[1][:40] if len(head) > 1 else r.stdout[:200], flush=True)
    apk = M / ('Builds/AdsMinimal128_%s.apk' % tag)
    i = subprocess.run([ADB, 'install', '-r', str(apk)], capture_output=True, text=True, timeout=240, errors='replace').stdout.strip().splitlines()
    print(' install', i[-1][:60] if i else '?', flush=True)
    m = subprocess.run([PY, '-I', str(HERE / 'matrix.py'), pkg, '0', '0'], capture_output=True, text=True, timeout=240, errors='replace')
    print(' ', m.stdout.strip().replace('\n', ' | ')[:120], m.stderr[:160], flush=True)
builder.write_text(original, 'utf-8')
