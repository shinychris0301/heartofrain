"""Extract original-PTS QA frames for manual inspection after timing finishes.

This script does not infer visual endpoints, interpolate frames, run Unity/ADB,
or write Timing_Visual_Notes.json. Keep it outside measured device phases.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / 'Verification/Evidence/Gameplay74'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--start', type=float, default=.3)
    parser.add_argument('--end', type=float, default=5.8)
    args = parser.parse_args()
    out = args.out.resolve()
    video = out / 'Android/Cascade/visual/HR_NaturalCascade.mp4'
    folder = out / 'TimingVisual'
    frames = folder / 'Frames'
    assert 0 <= args.start < args.end <= 15 and video.is_file()
    artifact = json.loads((out / 'APK_Artifact.json').read_text('utf-8-sig'))
    installed = json.loads((out / 'Android/Cascade/visual/Installation.json').read_text('utf-8-sig'))
    assert installed['apk_sha256'] == installed['installed_apk_sha256'] == artifact['sha256']
    assert not frames.exists() or not any(frames.iterdir()), 'Use an empty Frames folder; preserve prior evidence'
    frames.mkdir(parents=True, exist_ok=True)
    import imageio_ffmpeg
    exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
    command = [str(exe), '-hide_banner', '-copyts', '-i', str(video),
               '-vf', f"select='between(t,{args.start},{args.end})',showinfo",
               '-vsync', '0', str(frames / '%04d.png')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    (folder / 'Extraction.log').write_text(result.stderr, 'utf-8')
    assert result.returncode == 0, result.stderr[-2000:]
    pts = [float(x) for x in re.findall(r'\[Parsed_showinfo_.*?\].*?\bn:\s*\d+.*?\bpts_time:\s*([-+\d.eE]+)', result.stderr)]
    images = sorted(frames.glob('*.png'))
    assert len(images) == len(pts) > 0 and all(a < b for a, b in zip(pts, pts[1:])), 'Missing/duplicate PTS mapping'
    index = {'status': 'EXTRACTED_ORIGINAL_PTS_FRAMES_FOR_MANUAL_REVIEW',
        'apk_sha256': artifact['sha256'], 'video': video.relative_to(ROOT).as_posix(), 'sha256': sha(video),
        'ffmpegSHA256': sha(exe), 'command': command,
        'scope': 'Decoded source timestamps, with no CFR interpolation. PNG export and later contact sheets '
                 'are review aids, not a visual verdict or displayed-pixel latency measurement.',
        'frames': [{'file': p.relative_to(ROOT).as_posix(), 'pts': t, 'sha256': sha(p)} for p, t in zip(images, pts)]}
    (folder / 'PTS_Index.json').write_text(json.dumps(index, indent=2) + '\n', 'utf-8')
    print(json.dumps({'status': index['status'], 'apk_sha256': artifact['sha256'],
                      'frames': len(images), 'firstPts': pts[0], 'lastPts': pts[-1]}))


if __name__ == '__main__':
    main()
