"""Present original-PTS samples from four current native touch clips.

No Unity/ADB calls, interpolation, endpoint inference or visual approval. Run
only after the parent confirms that all timing/video capture has completed.
Imports do not decode media or inspect a report.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from qa_android_target import validate_qa_target

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'Verification/Evidence/Gameplay79'
CASES = ('MixedH', 'MixedChain', 'ObstaclePartial', 'ObstacleClear')
ALL_NATIVE_CASES = {'MixedH', 'MixedV', 'MixedBomb', 'MixedOrb', 'MixedSeeker',
                    'MixedChain', 'ObstaclePartial', 'ObstacleClear'}
START, END, STRIDE = .3, 5.8, 8


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need(value, message):
    if not value:
        raise AssertionError(message)


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(result.tzinfo is not None, 'Missing UTC timezone')
    return result.astimezone(timezone.utc)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read_bound(out, name, artifacts):
    path = (out / name).resolve()
    need(path.is_relative_to(out) and path.is_file(), 'Missing/unsafe current proof: ' + name)
    artifacts[path.relative_to(out).as_posix()] = sha(path)
    return json.loads(path.read_text('utf-8-sig'))


def validate_inputs(out, cases):
    """Read-only source/APK/target/native fixture bindings before any decoder."""
    out = Path(out).resolve()
    need(out == DEFAULT.resolve(), 'Use canonical Gameplay79 evidence')
    need(set(cases).issubset(CASES) and len(cases) == len(set(cases)) and cases, 'Unsupported/duplicate clip selection')
    artifacts = {}
    artifact = read_bound(out, 'APK_Artifact.json', artifacts)
    frozen = read_bound(out, 'Source_SHA256.json', artifacts)
    source_build = read_bound(out, 'Build_Source_SHA256.json', artifacts)
    build = read_bound(out, 'Android_Build.json', artifacts)
    process = read_bound(out, 'AndroidBuild_Process.json', artifacts)
    touch = read_bound(out, 'Android/Touch/Report.json', artifacts)
    target = validate_qa_target(touch['serial'], out)
    need(target['isolated_clone'] is True and touch['serial'] == 'emulator-5558', 'Current79 presentation requires the authorized isolated clone')
    read_bound(out, 'QA_Target.json', artifacts)
    need(target['target_record_sha256'] == artifacts['QA_Target.json'] and touch.get('qa_target') == target, 'Native touch target authorization differs')
    need(touch['status'] == 'CAPTURED_GAMEPLAY_AUDIT_REQUIRES_VISUAL_REVIEW', 'Native touch capture is incomplete')
    need(touch['apk_sha256'] == artifact['sha256'], 'Touch movie report belongs to another APK')
    need(touch.get('attempt_guard', {}).get('activeAttempts') == 0, 'Native transient fixture lacks its no-active-attempt guard')
    need(frozen['files'] == source_build['files'], 'Touch build/source inputs differ')
    need(build['status'] == 'PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors'] == 0 and build['unity'] == '2022.3.62f3', 'Current development build did not pass')
    need(process['exitCode'] == 0 and not process['timedOut'] and process['version'].startswith('2022.3.62f3'), 'Current build process failed/wrong engine')
    need(utc(process['finishedUtc']) <= utc(touch['utc']), 'Touch capture predates the current build')
    baseline = read_bound(out, 'Baseline78.json', artifacts)
    need(baseline['status'] == 'PRESERVED_VERIFIED78_BASELINE' and artifact['sha256'] != baseline['apk_sha256'], 'Historical78 APK cannot satisfy current79 presentation')
    saved = read_bound(out, 'Android/Before.json', artifacts)
    audit = read_bound(out, 'Android/Touch_Data_Audit.json', artifacts)
    need(audit['serial'] == touch['serial'] and audit['apk_sha256'] == artifact['sha256'] and audit['exit_code'] == 0, 'Touch saved-data wrapper did not run the current target/APK')
    need(audit['data_unchanged'] and audit['before'] == audit['after'] == saved, 'Touch fixtures changed real clone saves/preferences')
    need(utc(process['finishedUtc']) <= utc(audit['utc']) <= utc(touch['utc']), 'Touch save/build chronology differs')
    if 'qa_target' in audit:
        need(audit['qa_target'] == target, 'Touch save-wrapper target authorization differs')
    need(len(touch['cases']) == 8 and {case['mode'] for case in touch['cases']} == ALL_NATIVE_CASES, 'Native touch eight-case scope is incomplete')
    rows = {}
    for mode in cases:
        case = read_bound(out, 'Android/Touch/' + mode + '_Report.json', artifacts)
        need(case == next(value for value in touch['cases'] if value['mode'] == mode), 'Individual native case differs from aggregate: ' + mode)
        need(case['status'] == 'PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT' and not case['failures'] and case['accepted'] is True and case['launchCleared'] is True, 'Selected native case failed or launch covered it: ' + mode)
        need(utc(case['utc']) >= utc(touch['utc']), 'Selected native case is stale: ' + mode)
        poses = case['poses']
        need(poses and all(a['frame'] < b['frame'] and a['clock'] <= b['clock'] for a, b in zip(poses, poses[1:])), 'Native pose ownership/clock order differs: ' + mode)
        need(all(all(finite(p[key]) for key in ('age', 'x', 'y', 'clock')) and p['id'] == case['createdId'] for p in poses), 'Invalid/native pose ID changed: ' + mode)
        need(case['powerSteps'] >= 1, 'Selected fixture did not dispatch its native power action: ' + mode)
        if mode in ('MixedH', 'MixedChain'):
            need(case['sourceActivated'] is True and case['protectedBirth'] is True and case['chained'] is False, 'Mixed origin wave/newborn protection failed: ' + mode)
            need(case['createdId'] > 0 and case['createdKind'] == 4 and case['createdX'] == 4 and case['createdY'] == 4 and case['powerSteps'] == 1, 'Wrong mixed Rocket fixture: ' + mode)
            need(case['sourcePower'] == (5 if mode == 'MixedH' else 4), 'Wrong original source power: ' + mode)
            need(any(p['key'] == 'Create' for p in poses) and poses[-1]['phase'] == 'idle' and poses[-1]['key'] == 'Idle', 'Native reward creation/idle survival trace missing: ' + mode)
        elif mode == 'ObstaclePartial':
            need(any(p['key'].startswith('stone/Stone_Hit_2') and p['age'] > .3 for p in poses) and poses[-1]['key'] == 'stone_1', 'Partial stone hit/retained stone pose trace missing')
        else:
            need(any(p['key'].startswith('stone/Stone_Hit_1') and p['age'] > 0 for p in poses), 'Destroyed stone hit trace missing')
        video = out / 'Android/Touch' / (mode + '.mp4')
        need(video.is_file() and video.stat().st_size > 0, 'Missing actual source video: ' + mode)
        artifacts[video.relative_to(out).as_posix()] = sha(video)
        for suffix in ('_Before.png', '_After.png'):
            still = out / 'Android/Touch' / (mode + suffix)
            need(still.is_file(), 'Missing native before/after still: ' + mode)
            artifacts[still.relative_to(out).as_posix()] = sha(still)
        rows[mode] = case
    return {'out': out, 'apk_sha256': artifact['sha256'], 'source_sha256': artifacts['Source_SHA256.json'], 'qa_target': target,
            'cases': rows, 'artifacts': artifacts}


def parse_showinfo(log, filter_index):
    pattern = re.compile(r'\[Parsed_showinfo_' + str(filter_index) + r'\b[^\]]*\].*?\bn:\s*(\d+).*?\bpts:\s*(-?\d+).*?\bpts_time:\s*([-+\d.eE]+)')
    return [{'index': int(n), 'ptsTicks': int(ticks), 'pts': float(pts)} for n, ticks, pts in pattern.findall(log)]


def parse_time_base(log, filter_index):
    pattern = r'\[Parsed_showinfo_' + str(filter_index) + r'\b[^\]]*\].*?config in time_base:\s*(\d+)/(\d+)'
    matches = re.findall(pattern, log)
    need(len(set(matches)) == 1, 'Missing/changed original filter time base')
    numerator, denominator = map(int, matches[0])
    need(numerator > 0 and denominator > 0, 'Invalid original filter time base')
    return Fraction(numerator, denominator)


def sheet(out, destination, mode, name, values):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)
    small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 14)
    cols, cell_w, cell_h, header = 6, 172, 318, 70
    canvas = Image.new('RGB', (cols * cell_w, header + math.ceil(len(values) / cols) * cell_h), (8, 28, 50))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 8), 'Checkpoint79 ' + mode + ' - ' + name.replace('_', ' '), font=font, fill=(245, 214, 128))
    draw.text((12, 35), 'Original PTS / source frame; samples are not a motion or smoothness verdict.', font=small, fill=(225, 236, 245))
    for i, entry in enumerate(values):
        path = out / entry['file']
        need(path.is_relative_to(out) and sha(path) == entry['sha256'], 'Selected original frame changed')
        with Image.open(path) as source:
            picture = source.convert('RGB')
        picture.thumbnail((160, 285))
        x, y = (i % cols) * cell_w + 6, header + (i // cols) * cell_h
        canvas.paste(picture, (x, y))
        draw.text((x, y + 289), f"{entry['pts']:.6f}s #{entry['sourceFrameIndex']}", font=small, fill=(240, 240, 240))
    canvas.save(destination)
    return {'file': destination.relative_to(out).as_posix(), 'sha256': sha(destination), 'samples': len(values), 'contributors': values}


def present(out=DEFAULT, cases=CASES):
    checked = validate_inputs(out, tuple(cases))
    out = checked['out']
    original_bindings = dict(checked['artifacts'])
    import imageio_ffmpeg
    exe = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    need(exe.is_file(), 'Pinned Python imageio_ffmpeg binary is unavailable')
    ffmpeg_sha, tool_sha = sha(exe), sha(Path(__file__))
    artifacts = dict(original_bindings)
    rows = []
    for mode in cases:
        folder = out / 'TouchVisual' / mode
        need(not folder.exists() or not any(folder.iterdir()), 'Preserve existing media; current case output must be empty: ' + mode)
        frames_folder = folder / 'Frames'
        frames_folder.mkdir(parents=True, exist_ok=True)
        video = out / 'Android/Touch' / (mode + '.mp4')
        # First showinfo retains each original decoded source-picture index;
        # the second logs only selected pictures. PTS/ticks pass through intact.
        graph = f"showinfo,select='between(t,{START},{END})*not(mod(n,{STRIDE}))',showinfo"
        command = [str(exe), '-hide_banner', '-threads', '1', '-filter_threads', '1', '-copyts', '-i', str(video),
                   '-vf', graph, '-vsync', '0', '-threads', '1', str(frames_folder / '%04d.png')]
        result = subprocess.run(command, capture_output=True, text=True, timeout=180,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        log = folder / 'Extraction.log'
        log.write_text(result.stderr, encoding='utf-8')
        artifacts[log.relative_to(out).as_posix()] = sha(log)
        need(result.returncode == 0, 'FFmpeg extraction failed: ' + result.stderr[-2000:])
        original = parse_showinfo(result.stderr, 0)
        selected = parse_showinfo(result.stderr, 2)
        time_base = parse_time_base(result.stderr, 0)
        need(time_base == parse_time_base(result.stderr, 2), 'Selected filter changed original timestamp units')
        for entry in original + selected:
            entry['reportedPts'] = entry['pts']
            entry['pts'] = float(entry['ptsTicks'] * time_base)
        images = sorted(frames_folder.glob('*.png'))
        need(original and len(images) == len(selected) > 0, 'Selected PNG/PTS log counts disagree')
        need([e['index'] for e in original] == list(range(len(original))), 'Original decoded picture indices were dropped/reordered')
        need(all(a['ptsTicks'] < b['ptsTicks'] and a['pts'] < b['pts'] for a, b in zip(original, original[1:])), 'Original video presentation timestamps are not increasing')
        expected = [e for e in original if Fraction(str(START)) <= e['ptsTicks'] * time_base <= Fraction(str(END)) and e['index'] % STRIDE == 0]
        need([(e['ptsTicks'], e['pts']) for e in selected] == [(e['ptsTicks'], e['pts']) for e in expected], 'Selection changed original PTS or source-picture stride')
        entries = []
        for i, (picture, source) in enumerate(zip(images, expected)):
            entry = {'file': picture.relative_to(out).as_posix(), 'sha256': sha(picture), 'sourceFrameIndex': source['index'],
                     'selectedOutputIndex': i, 'pts': source['pts'], 'ptsTicks': source['ptsTicks'], 'reportedPts': source['reportedPts']}
            entries.append(entry)
            artifacts[entry['file']] = entry['sha256']
        n = min(24, len(entries))
        overview = [entries[round(i * (len(entries) - 1) / max(1, n - 1))] for i in range(n)]
        views = [('Overview', overview)]
        if overview != entries[:24]:
            views.append(('Initial', entries[:24]))
        sheets = [sheet(out, folder / (name + '_Sheet.png'), mode, name, values) for name, values in views]
        for value in sheets:
            artifacts[value['file']] = value['sha256']
        native = checked['cases'][mode]
        index = {'status': 'PRESENTED_ORIGINAL_PTS_TOUCH79_SAMPLES_FOR_ACTUAL_REVIEW', 'checkpoint': 79,
                 'mode': mode, 'apk_sha256': checked['apk_sha256'], 'source_sha256': checked['source_sha256'],
                 'qa_serial': checked['qa_target']['serial'], 'qa_target': checked['qa_target'],
                 'video': video.relative_to(out).as_posix(), 'videoSHA256': sha(video),
                 'ffmpeg': str(exe), 'ffmpegSHA256': ffmpeg_sha, 'imageio_ffmpegVersion': imageio_ffmpeg.__version__,
                 'command': command, 'exitCode': result.returncode, 'sourcePictures': len(original), 'timeBase': {'numerator': time_base.numerator, 'denominator': time_base.denominator},
                 'selection': {'startPts': START, 'endPts': END, 'sourcePictureStride': STRIDE, 'interpolation': False, 'constantFrameRateConversion': False},
                 'scope': 'Every eighth original decoded picture in the encoded source between the stated original PTS bounds. Full selected PNGs are retained. Native Unity pose clocks/frame IDs are separate from encoded PTS; no automated alignment, endpoint, continuity, protected-power visual verdict or physical-display timing is inferred.',
                 'nativeSemanticFacts': {k: native[k] for k in ('mode', 'status', 'createdId', 'createdKind', 'sourcePower', 'powerSteps', 'sourceActivated', 'protectedBirth', 'chained')},
                 'frames': entries, 'sheets': sheets, 'artifactSHA256': dict(sorted(original_bindings.items()))}
        index_path = folder / 'PTS_Index.json'
        index_path.write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
        artifacts[index_path.relative_to(out).as_posix()] = sha(index_path)
        rows.append({'mode': mode, 'index': index_path.relative_to(out).as_posix(), 'indexSHA256': sha(index_path),
                     'frames': len(entries), 'firstPts': entries[0]['pts'], 'lastPts': entries[-1]['pts'], 'sheets': sheets})
    need(all(sha(out / name) == value for name, value in original_bindings.items()), 'Source reports/target/video changed during presentation')
    need(sha(Path(__file__)) == tool_sha and sha(exe) == ffmpeg_sha, 'Presentation tool/decoder changed during processing')
    manifest = {'status': 'PRESENTED_CURRENT_TOUCH79_PTS_SAMPLES_AWAITING_ACTUAL_REVIEW', 'utc': datetime.now(timezone.utc).isoformat(),
                'checkpoint': 79, 'apk_sha256': checked['apk_sha256'], 'source_sha256': checked['source_sha256'], 'qa_serial': checked['qa_target']['serial'],
                'qa_target': checked['qa_target'], 'cases': rows, 'toolSHA256': tool_sha, 'ffmpegSHA256': ffmpeg_sha,
                'scope': 'Source/build/target/native-data checks plus automatic original-PTS contact-sheet presentation. This is preparation for actual human/assistant inspection, not visual approval, endpoint measurement, new Unity/Android execution or a speedup/reference-parity claim.',
                'artifactSHA256': dict(sorted(artifacts.items()))}
    target = out / 'TouchVisual/Manifest.json'
    need(not target.exists(), 'Preserve existing presentation manifest')
    target.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT, help='Canonical Gameplay79 evidence folder')
    parser.add_argument('--case', choices=CASES, action='append', help='Default: all four requested clips')
    args = parser.parse_args()
    value = present(args.out, tuple(args.case) if args.case else CASES)
    print(json.dumps({'status': value['status'], 'apk_sha256': value['apk_sha256'], 'cases': [(r['mode'], r['frames'], len(r['sheets'])) for r in value['cases']]}), flush=True)


if __name__ == '__main__':
    main()
