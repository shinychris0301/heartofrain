"""Read-only private capture of the exact running116 emulator host window."""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'Verification/Evidence/Review116/Emulator/FinalHostCapture116.json'
PRIVATE = ROOT / '.verification-cache/Review116/EmulatorFinalHostCapture116'


def main():
    if PUBLIC.exists() or PRIVATE.exists():
        raise RuntimeError('FreshPrivateHostCaptureRequired')
    PRIVATE.mkdir()
    result = subprocess.run(['E:/LDPlayer/LDPlayer14/ldconsole.exe', 'list2'], capture_output=True,
        timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    (PRIVATE / 'Console.private').write_bytes(result.stdout + result.stderr)
    rows = [line.split(',') for line in result.stdout.decode('utf-8', 'replace').splitlines()]
    row = next(row for row in rows if len(row) >= 7 and row[0] == '0')
    if result.returncode != 0 or row[4] != '1' or row[5:7] != ['38824', '1464']:
        raise RuntimeError('ExactPreservedRunningHostRequired')
    window = int(row[2])
    owner = wintypes.DWORD()
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    if not user.GetWindowThreadProcessId(window, ctypes.byref(owner)) or owner.value != 38824:
        raise RuntimeError('ExactOwnWindowOwnerRequired')
    picture = ImageGrab.grab(window=window)
    if picture.width < 200 or picture.height < 200:
        raise RuntimeError('BoundedActualOwnedWindowImageRequired')
    path = PRIVATE / 'FinalHomeHostWindow.png'
    picture.save(path)
    report = dict(status='CAPTURED_OWNED_EMULATOR_WINDOW_REQUIRES_VISUAL_REVIEW116',
        instanceIndex=0, playerPid=38824, vmPid=1464, exactWindowOwnerVerified=True,
        image=dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            bytes=path.stat().st_size, width=picture.width, height=picture.height),
        runnerSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        deviceCommandsPerformed=False, focusOrWindowPositionChanged=False,
        scope='Read-only Windows capture of only the exact preserved emulator host window after helper cleanup. Raw image stays private because the host frame can contain a user title. Actual Home interpretation is a separate visual review; this does not independently identify installed APK bytes.')
    PUBLIC.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], width=picture.width, height=picture.height)))


if __name__ == '__main__':
    main()
