"""Private video derivatives only; no SDK/device operation or visual approval."""
import argparse
import hashlib
import json
import math
import re
import subprocess
from fractions import Fraction
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageChops, ImageDraw, ImageStat


ROOT = Path(__file__).resolve().parents[3]
PRIVATE = ROOT / '.verification-cache/Review101/Media101'


def binding(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def timestamps(video, output):
    """Exact decoded PTS/timebase; recording time is not app readiness."""
    arguments = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-nostdin',
                 '-loglevel', 'info', '-i', str(video), '-map', '0:v:0',
                 '-vf', 'showinfo', '-fps_mode', 'passthrough', '-f', 'null', '-']
    probe = subprocess.run(arguments, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                           check=True, timeout=180, text=True, encoding='utf-8', errors='replace')
    log = output / 'DecoderPTS.log'
    log.write_text(probe.stderr, encoding='utf-8', newline='\n')
    match = re.search(r'config in time_base:\s*(\d+)/(\d+)', probe.stderr)
    if not match:
        raise ValueError('Decoder timebase missing')
    timebase = Fraction(int(match[1]), int(match[2]))
    rows = []
    for match in re.finditer(r'\bn:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:', probe.stderr):
        index, pts = int(match[1]), int(match[2])
        if index != len(rows) or index >= 21600:
            raise ValueError('PTS frame order/bound mismatch')
        seconds = pts * timebase
        elapsed = (pts - rows[0]['pts']) * timebase if rows else Fraction(0)
        if rows and elapsed < Fraction(rows[-1]['recordingSecondsRational']):
            raise ValueError('Non-monotonic recording PTS')
        rows.append({'frame': index, 'pts': pts,
                     'streamSecondsRational': str(seconds),
                     'recordingSecondsRational': str(elapsed),
                     'recordingSeconds': float(elapsed)})
    if not rows:
        raise ValueError('No exact decoded timestamps')
    return rows, {'timeBaseNumerator': timebase.numerator,
                  'timeBaseDenominator': timebase.denominator,
                  'firstPTS': rows[0]['pts'], 'frameCount': len(rows),
                  'log': binding(log),
                  'scope': 'Exact decoder PTS/timebase and relative recording clock; not intent, touch, TTID, fully-drawn or interactive readiness.'}


def extract(video, output, expected=None, receipt=None):
    video, output = video.resolve(), output.resolve()
    if (not video.is_file() or video.suffix.lower() != '.mp4'
            or not video.is_relative_to((ROOT / '.verification-cache').resolve())
            or not output.is_relative_to(PRIVATE.resolve()) or output == PRIVATE.resolve()
            or output.exists()):
        raise ValueError('Existing private MP4 and fresh private Media100 output required')
    before = binding(video)
    if expected is not None and before['sha256'] != expected.lower():
        raise ValueError('Completed recording hash does not match')
    receipt_before = binding(receipt) if receipt else None
    output.mkdir(parents=True)
    pts_rows, pts_metadata = timestamps(video, output)
    reader = imageio_ffmpeg.read_frames(str(video), pix_fmt='rgb24',
                                        output_params=['-fps_mode', 'passthrough'])
    metadata = next(reader)
    width, height = metadata['size']
    fps, duration = float(metadata['fps']), float(metadata['duration'])
    if not (0 < width <= 4096 and 0 < height <= 4096 and math.isfinite(fps)
            and 1 <= fps <= 120 and math.isfinite(duration) and 0 < duration <= 180):
        reader.close()
        raise ValueError('Bounded physical recording geometry/rate/duration required')

    thumb_w, columns, rows, header, label_h = 108, 12, 10, 44, 22
    thumb_h = round(height * thumb_w / width)
    capacity = columns * rows
    sheet = draw = previous = None
    sheets, samples, frame_map = [], [], []
    frame_count, last_transition = 0, -10000
    sampled_indices = set()

    def save_sample(picture, index, reason):
        if index in sampled_indices:
            return
        destination = output / ('Frame_%05d.png' % index)
        picture.save(destination)
        samples.append({**binding(destination), 'frame': index,
                        'nominalSeconds': round(index / fps, 6),
                        'exactPTS': pts_rows[index], 'reason': reason})
        sampled_indices.add(index)

    def finish_sheet(last_frame):
        nonlocal sheet, draw
        destination = output / ('AllFrames_%02d.png' % (len(sheets) + 1))
        sheet.save(destination)
        sheets.append({**binding(destination), 'firstFrame': last_frame // capacity * capacity,
                       'lastFrame': last_frame})
        sheet = draw = None

    last_picture = None
    try:
        for index, raw in enumerate(reader):
            if index >= len(pts_rows) or len(raw) != width * height * 3:
                raise ValueError('Decoded frame bound exceeded')
            picture = Image.frombytes('RGB', (width, height), raw)
            thumbnail = picture.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            position = index % capacity
            if position == 0:
                if sheet is not None:
                    finish_sheet(index - 1)
                sheet = Image.new('RGB', (columns * thumb_w, header + rows * (thumb_h + label_h)), '#142132')
                draw = ImageDraw.Draw(sheet)
                draw.text((8, 6), 'Decoded recording: every frame, fitted without crop', fill='white')
                draw.text((8, 24), 'Exact recording-relative decoder PTS; not app readiness. Private; root review separate.', fill='white')
            x = position % columns * thumb_w
            y = header + position // columns * (thumb_h + label_h)
            sheet.paste(thumbnail, (x, y))
            draw.text((x + 2, y + thumb_h + 2), '%d / %.3fs' % (index, pts_rows[index]['recordingSeconds']), fill='white')
            frame_map.append({**pts_rows[index], 'sheet': len(sheets) + 1, 'cell': position})
            periodic = max(1, round(fps / 2 if index / fps <= 8 else fps * 2))
            if index % periodic == 0:
                save_sample(picture, index, 'periodic full-resolution decoded frame')
            if previous is not None:
                change = sum(ImageStat.Stat(ImageChops.difference(previous, thumbnail)).mean) / 3
                if change >= 12 and index - last_transition >= max(1, round(fps / 4)):
                    save_sample(picture, index, 'large thumbnail change; candidate transition only')
                    last_transition = index
            previous, last_picture, frame_count = thumbnail, picture, index + 1
        if frame_count != len(pts_rows):
            raise ValueError('Image decoder and exact PTS frame counts differ')
        save_sample(last_picture, frame_count - 1, 'last decoded frame')
        finish_sheet(frame_count - 1)
    finally:
        reader.close()

    if binding(video) != before or receipt and binding(receipt) != receipt_before:
        raise ValueError('Original media or recording receipt changed during decoding')
    samples.sort(key=lambda item: item['frame'])
    chosen = samples[:]
    contact_columns, cell_w, cell_h = 4, 180, round(height * 180 / width) + 24
    # Representative gallery is private and includes launcher frames. It is not
    # a declaration that detected thumbnail changes are actual app transitions.
    sample_sheet = Image.new('RGB', (contact_columns * cell_w,
                             math.ceil(len(chosen) / contact_columns) * cell_h + 30), '#142132')
    sample_draw = ImageDraw.Draw(sample_sheet)
    sample_draw.text((8, 7), 'Private representative decoded frames - NOT visual acceptance', fill='white')
    for index, item in enumerate(chosen):
        with Image.open(ROOT / item['path']) as source:
            small = source.resize((cell_w, cell_h - 24), Image.Resampling.LANCZOS)
        x, y = index % contact_columns * cell_w, 30 + index // contact_columns * cell_h
        sample_sheet.paste(small, (x, y))
        sample_draw.text((x + 3, y + cell_h - 21), '%d / %.3fs' % (item['frame'], item['exactPTS']['recordingSeconds']), fill='white')
    sample_path = output / 'Representatives.png'
    sample_sheet.save(sample_path)
    result = {
        'schemaVersion': 1,
        'status': 'PREPARED_PRIVATE_MEDIA101_DERIVATIVES_REQUIRES_ROOT_REVIEW',
        'originalVideoBefore': before, 'originalVideoAfter': binding(video),
        'recordingReceipt': receipt_before, 'extractor': binding(Path(__file__)),
        'decoderBinary': binding(Path(imageio_ffmpeg.get_ffmpeg_exe())),
        'decoderOutputParameters': ['-fps_mode', 'passthrough'],
        'width': width, 'height': height, 'nominalFps': fps, 'containerDurationSeconds': duration,
        'decodedFrames': frame_count, 'contactSheets': sheets,
        'exactPTS': pts_metadata,
        'representativeSheet': binding(sample_path), 'fullResolutionFrames': samples,
        'everyDecodedFrameMap': frame_map,
        'frameTimesAreApproximateIndexDividedByNominalFPS': False,
        'nominalFPSValuesRemainMetadataOnly': True,
        'rootVisualReviewCompleted': False, 'splashAbsenceAutomaticallyCertified': False,
        'scope': 'Filesystem/local ffmpeg decoding only. Every decoded frame is present in chronological contact sheets; full-resolution frames are representative decoded derivatives, not original OS screenshots. No crop or source replacement. Launcher/OS frames and raw media stay private. No SDK/ADB/Unity, first-ever/cold-launch correctness, splash absence, performance or visual acceptance is inferred.',
    }
    destination = output / 'MediaManifest.json'
    destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'manifest': binding(destination),
                      'decodedFrames': frame_count, 'contactSheets': len(sheets),
                      'representativeFrames': len(samples)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sha256')
    parser.add_argument('--receipt', type=Path)
    arguments = parser.parse_args()
    extract(arguments.video, arguments.out, arguments.sha256, arguments.receipt)
