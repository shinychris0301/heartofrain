"""Decode fresh78 timing movies into hash-bound original-PTS review frames.

This tool performs no Unity/ADB calls, automatic endpoint selection, frame-rate
interpolation or visual approval. Earlier77 captures are comparison evidence
only and cannot satisfy a78 extraction.
"""
import argparse
import hashlib
import json
import re
import runpy
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEVELS = (4, 14, 31, 33)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def extract(out, level, start, end):
    source_name = 'Android/Cascade/visual' if level == 4 else f'ContinuationVisual/L{level}/visual'
    source, folder = out / source_name, out / f'TimingVisual/L{level}'
    frames, video = folder / 'Frames', source / 'HR_NaturalCascade.mp4'
    artifact, install, report = read(out / 'APK_Artifact.json'), read(source / 'Installation.json'), read(source / 'Report.json')
    assert install['serial'] == 'emulator-5556'
    assert install['apk_sha256'] == install['installed_apk_sha256'] == artifact['sha256']
    assert install.get('visual_level', 4) == report['visualLevel'] == level
    assert not install.get('checkpoint74_continuation') and not report['checkpoint74Continuation']
    assert not install.get('profile_model_work') and not report['modelWorkEnabled']
    assert report['status'] == 'PASS_CASCADE_PLAYBACK' and not report['errors'] and len(report['rows']) == 1
    assert report['rows'][0]['name'] == f'L{level}_0_30'
    assert install['data_unchanged'] and install['before'] == install['after'] == read(out / 'Android/Before.json')
    frozen, build_source = read(out / 'Source_SHA256.json'), read(out / 'Build_Source_SHA256.json')
    assert frozen['files'] == build_source['files'], 'Movie build/source inputs differ'
    process, build = read(out / 'AndroidBuild_Process.json'), read(out / 'Android_Build.json')
    assert process['exitCode'] == 0 and not process['timedOut'] and build['status'] == 'PASS_ANDROID_DEVELOPMENT_BUILD'
    assert utc(process['finishedUtc']) <= utc(install['utc']) <= utc(report['utc']), 'Movie/report predates current build'
    validator = runpy.run_path(str(Path(__file__).with_name('run_cascade_timing_device.py')), run_name='extract78_raw_contract_only')
    assert validator['validate_report'](report, 'visual', 1, require_profiling=True)
    assert 0 <= start < end <= 15 and video.is_file()
    assert not frames.exists() or not any(frames.iterdir()), 'Keep earlier frames intact; current Frames folder must be empty'
    baseline = ROOT / 'Verification/Evidence/Gameplay77/APK_Artifact.json'
    assert artifact['sha256'] != read(baseline)['sha256'] != '', 'A77 APK cannot be fresh78 evidence'
    assert read(baseline)['sha256'] == 'd4bb4e66e454db223871c91d66de4ee8e87fec05268aa9a27a3cf86da7930072', 'Archived77 APK identity changed'
    frames.mkdir(parents=True, exist_ok=True)
    import imageio_ffmpeg
    exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
    command = [str(exe), '-hide_banner', '-threads', '1', '-filter_threads', '1', '-copyts', '-i', str(video),
               '-vf', f"select='between(t,{start},{end})',showinfo", '-vsync', '0', '-threads', '1', str(frames / '%04d.png')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    (folder / 'Extraction.log').write_text(result.stderr, encoding='utf-8')
    assert result.returncode == 0, result.stderr[-2000:]
    pts = [float(x) for x in re.findall(r'\[Parsed_showinfo_.*?\].*?\bn:\s*\d+.*?\bpts_time:\s*([-+\d.eE]+)', result.stderr)]
    images = sorted(frames.glob('*.png'))
    assert len(images) == len(pts) > 0 and all(a < b for a, b in zip(pts, pts[1:]))
    index = {'status': 'EXTRACTED_ORIGINAL_PTS_FRAMES_FOR_MANUAL_REVIEW', 'checkpoint': 78,
        'apk_sha256': artifact['sha256'], 'source_sha256': sha(out / 'Source_SHA256.json'),
        'case': f'L{level}_0_30', 'visualLevel': level, 'checkpoint74Continuation': False,
        'video': video.relative_to(ROOT).as_posix(), 'sha256': sha(video),
        'reportSHA256': sha(source / 'Report.json'), 'installationSHA256': sha(source / 'Installation.json'),
        'ffmpegSHA256': sha(exe), 'command': command,
        'scope': 'Fresh78 decoded source timestamps, without CFR interpolation. No endpoints, continuity verdict, '
                 'input latency or displayed-pixel timing are inferred. Recorded intervals retain observer/recording overhead.',
        'frames': [{'file': p.relative_to(ROOT).as_posix(), 'pts': t, 'sha256': sha(p)} for p, t in zip(images, pts)]}
    (folder / 'PTS_Index.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    summary = {'status': index['status'], 'apk_sha256': artifact['sha256'], 'case': index['case'],
               'source': source_name, 'frames': len(images), 'firstPts': pts[0], 'lastPts': pts[-1],
               'ptsIndex': (folder / 'PTS_Index.json').relative_to(out).as_posix()}
    print(json.dumps(summary), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'Verification/Evidence/Gameplay78')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--level', type=int, choices=LEVELS, default=4)
    group.add_argument('--all', action='store_true')
    parser.add_argument('--start', type=float, default=.3)
    parser.add_argument('--end', type=float, help='Defaults to 5.8 seconds for L4 and 3.8 for terminal cases')
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(ROOT) and out.name == 'Gameplay78', 'Use the canonical fresh78 evidence folder'
    levels = LEVELS if args.all else [args.level]
    summaries = [extract(out, level, args.start, args.end if args.end is not None else 5.8 if level == 4 else 3.8)
                 for level in levels]
    if args.all:
        (out / 'TimingVisual/Extraction_Summary.json').write_text(json.dumps({
            'status': 'DECODED_FOUR_FRESH78_MOVIES_AWAITING_MANUAL_REVIEW', 'rows': summaries}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
