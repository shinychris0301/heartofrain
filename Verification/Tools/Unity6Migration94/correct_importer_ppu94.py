"""Root-only exact verification-assertion correction after paired native proof."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
TEMPLATE = HERE / 'Templates/Unity6Importer94.cs'
RELATIVE = 'Assets/HeartOfTheRain/Verification/Editor/Unity6Importer94.cs'
ORIGINAL = OUT / 'ImporterPreparation/Report.json'
CORRECTION = OUT / 'ImporterPPUCorrection/Set01/Report.json'
STATUS = 'APPLIED_EXACT_IMPORTER_PPU_ASSERTION_CORRECTION94'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def binding(path):
    return {'path': Path(path).resolve().relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': Path(path).stat().st_size}


def need(condition, message):
    if not condition: raise ValueError(message)


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def expected_runtime_ppu(ppu, source_width, source_height, rect_width, rect_height):
    need(all(math.isfinite(value) and value > 0 for value in
             (ppu, source_width, source_height, rect_width, rect_height)), 'Positive finite original/native geometry required')
    scale = min(f32(rect_width / source_width), f32(rect_height / source_height))
    return f32(f32(ppu) * (scale if scale < 1 else 1))


def bits(value):
    return struct.pack('>f', f32(value)).hex()


METHOD = '''        [Serializable] sealed class PPURuleCorrection94
        {
            public string status, originalPreparationSHA256, templateBeforeSHA256, templateAfterSHA256, expectedPath, expectedSHA256;
        }
        static string ValidatedPPUTemplateHash94(Preparation original)
        {
            string path = Path.Combine(workspace, "Verification/Evidence/Unity6Migration94/ImporterPPUCorrection/Set01/Report.json");
            RequireInside(path, Path.Combine(workspace, "Verification/Evidence/Unity6Migration94/ImporterPPUCorrection"));
            var correction = JsonUtility.FromJson<PPURuleCorrection94>(File.ReadAllText(path));
            string preparation = Path.Combine(workspace, "Verification/Evidence/Unity6Migration94/ImporterPreparation/Report.json");
            Check(correction.status == "APPLIED_EXACT_IMPORTER_PPU_ASSERTION_CORRECTION94"
                  && correction.originalPreparationSHA256 == Hash(preparation)
                  && correction.templateBeforeSHA256 == original.templateSHA256
                  && correction.expectedPath == original.expectedPath && correction.expectedSHA256 == original.expectedSHA256,
                  "Immutable original preparation/expected data and paired-native PPU correction receipt");
            report.correctionSHA256 = Hash(path);
            return correction.templateAfterSHA256;
        }

'''


def transform(raw):
    text = raw.decode('utf-8')
    replacements = [
        ('public string status, utc, unity, expectedSHA256, expectedPath, error;',
         'public string status, utc, unity, expectedSHA256, expectedPath, error, correctionSHA256;'),
        ('public float importerPPU, spritePPU;',
         'public float importerPPU, spritePPU, expectedRuntimePPU;\n            public bool runtimePPUWasRescaled;'),
        ('Check(Hash(self) == preparation.templateSHA256, "Native probe equals root-reviewed template");',
         'Check(Hash(self) == ValidatedPPUTemplateHash94(preparation), "Native probe equals root-reviewed corrected template");'),
        ('        static void Read(ExpectedRow expected)\n', METHOD + '        static void Read(ExpectedRow expected)\n'),
        ('''                Check(Mathf.Abs(actual.importerPPU - expected.pixelsPerUnit) < .001f && Mathf.Abs(actual.spritePPU - expected.pixelsPerUnit) < .001f,
                      expected.path + " original importer and runtime pixels per unit");''',
         '''                float nativeScale = Mathf.Min(actual.spriteRect.width / actual.sourceWidth, actual.spriteRect.height / actual.sourceHeight);
                actual.runtimePPUWasRescaled = nativeScale > 0f && nativeScale < 1f;
                actual.expectedRuntimePPU = expected.pixelsPerUnit * (actual.runtimePPUWasRescaled ? nativeScale : 1f);
                Check(nativeScale > 0f && Mathf.Abs(actual.importerPPU - expected.pixelsPerUnit) < .001f
                      && Mathf.Abs(actual.spritePPU - actual.expectedRuntimePPU) < .001f,
                      expected.path + " original importer PPU and native downsample-adjusted runtime PPU");''')]
    for before, after in replacements:
        need(text.count(before) == 1, 'Exact original importer assertion anchors required')
        text = text.replace(before, after, 1)
    return text.encode('utf-8')


def validate_scale_proof(path):
    path = Path(path).resolve()
    need(path.is_relative_to(OUT / 'SpriteScale') and path.name == 'Invocation.json', 'Explicit paired native sprite-scale proof required')
    proof = json.loads(path.read_text('utf-8-sig'))
    need(proof.get('status') == 'PASS_TWO_ENGINE_SPRITE_SCALE94_READBACK_PARITY'
         and proof.get('readbackDifferences') == [] and proof.get('mainInputsUnchanged') is True
         and proof.get('candidateInputsUnchanged') is True and proof.get('unityPidsAfter') == []
         and len(proof.get('runs', [])) == 2, 'Actual paired native readback parity required')
    reports = []
    for row, name, version in zip(proof['runs'], ('Baseline2022', 'Candidate6'), ('2022.3.62f3', '6000.6.6f1')):
        need(row.get('name') == name and row.get('status') == 'RECORDED_NATIVE_SPRITE_SCALE94'
             and row.get('exitCode') == 0 and row.get('actualEngineVersionFromLog') == version
             and row.get('unityPidsAfter') == [] and row.get('preexistingAssetOrInputChanges') == []
             and row.get('unexpectedAddedAssets') == [], 'Actual preserved expected native process required')
        source = ROOT / row['nativeReport']['path']
        need(source.resolve().is_relative_to(path.parent / name) and binding(source) == row['nativeReport'], 'Native readback binding changed')
        report = json.loads(source.read_text('utf-8-sig'))
        need(report.get('status') == 'RECORDED_NATIVE_SPRITE_SCALE94_REQUIRES_COMPARISON'
             and not report.get('error') and report.get('unity') == version and report.get('activeBuildTarget') == 'Android'
             and report.get('inputPNGUnchanged') is True and report.get('sourceWidth') == 2170
             and report.get('sourceHeight') == 725 and report.get('spriteRect', {}).get('width') == 2048
             and report.get('spriteRect', {}).get('height') == 684 and report.get('importerPPU') == 100
             and report.get('spritePPUBits') == report.get('heightScalePPUBits') == '42bcb08e',
             'Confirmed original quantized downsample case required')
        original_asset = ROOT / 'Unity/Assets/HeartOfTheRain/App/Teams/Art/TM_WellRally.png'
        need(report['assetSHA256'] == sha(original_asset) and report['originalMetaSHA256'] == sha(Path(str(original_asset) + '.meta')),
             'Original PNG/meta authority differs')
        reports.append(row['nativeReport'])
    return {'pairedInvocation': binding(path), 'nativeReports': reports}


def validated_correction(original):
    record = json.loads(CORRECTION.read_text('utf-8-sig'))
    need(record.get('status') == STATUS and record['originalPreparationSHA256'] == sha(ORIGINAL)
         and record['templateBeforeSHA256'] == original['templateSHA256']
         and record['templateAfterSHA256'] == sha(TEMPLATE)
         and record['expectedPath'] == original['expectedPath'] and record['expectedSHA256'] == original['expectedSHA256']
         and sha(ROOT / original['expectedPath']) == original['expectedSHA256'], 'Exact importer correction receipt required')
    before = CORRECTION.parent / 'Template_before.cs'
    need(sha(before) == record['templateBeforeSHA256'] and transform(before.read_bytes()) == TEMPLATE.read_bytes(),
         'Only exact reviewed PPU assertion correction allowed')
    need(validate_scale_proof(ROOT / record['scaleProof']['pairedInvocation']['path']) == record['scaleProof'],
         'Paired native correction evidence changed')
    return record


def main():
    cli = argparse.ArgumentParser(description=__doc__); cli.add_argument('--execute', action='store_true')
    cli.add_argument('--proof', type=Path, required=True); args = cli.parse_args()
    if not args.execute or os.name != 'nt': cli.error('Explicit root Windows correction required')
    audit = module('ppu94_source_guard', HERE / 'audit_candidate94.py')
    processes = module('ppu94_idle_guard', ROOT / 'Verification/Tools/PageBackdrop90/process90.py')
    need(not processes.unity_pids(), 'No concurrent Unity during correction')
    audit.reject_links(CORRECTION); audit.reject_links(PROJECT); audit.reject_links(TEMPLATE)
    need(not CORRECTION.parent.exists(), 'Fresh correction checkpoint required')
    original = json.loads(ORIGINAL.read_text('utf-8-sig'))
    scale_proof = validate_scale_proof(args.proof)
    old = TEMPLATE.read_bytes(); candidate = PROJECT / RELATIVE
    need(sha(TEMPLATE) == original['templateSHA256'] and candidate.read_bytes() == old, 'Exact initial native probe bytes required')
    need(sha(ROOT / original['expectedPath']) == original['expectedSHA256'], 'Immutable original438-row expected data required')
    baseline = json.loads((OUT / 'MainSources_Before.json').read_text('utf-8-sig'))
    main = audit.inventory(ROOT / 'Unity', 'Unity/'); before = audit.inventory(PROJECT)
    need(main == baseline, 'Original main5407 baseline changed')
    new = transform(old)
    CORRECTION.parent.mkdir(parents=True, exist_ok=False)
    with (CORRECTION.parent / 'Template_before.cs').open('xb') as stream: stream.write(old)
    with TEMPLATE.open('wb') as stream: stream.write(new)
    with candidate.open('wb') as stream: stream.write(new)
    after = audit.inventory(PROJECT); main_after = audit.inventory(ROOT / 'Unity', 'Unity/')
    need(main == main_after and set(before['files']) == set(after['files'])
         and [path for path in before['files'] if before['files'][path] != after['files'][path]] == [RELATIVE],
         'Only the one existing isolated Editor assertion fixture may change')
    for name, value in (('MainSources_before.json', main), ('MainSources_after.json', main_after),
                        ('CandidateSources_before.json', before), ('CandidateSources_after.json', after)):
        audit.write_new(CORRECTION.parent / name, value)
    record = {'schemaVersion': 1, 'status': STATUS, 'utc': audit.utc(), 'runnerSHA256': sha(__file__),
        'originalPreparationSHA256': sha(ORIGINAL), 'templateBeforeSHA256': hashlib.sha256(old).hexdigest(),
        'templateAfterSHA256': sha(TEMPLATE), 'expectedPath': original['expectedPath'], 'expectedSHA256': original['expectedSHA256'],
        'scaleProof': scale_proof, 'mainInputsUnchanged': True, 'onlyCandidateInputChanged': RELATIVE,
        'nativeProcessesRun': False, 'originalPreparationPreserved': True,
        'scope': 'Exact Editor verification assertion correction only, grounded in actual 2022/6000 readback parity. Runtime PPU uses original PPU times the smaller native rect/source scale only for downsampling; importer PPU,105 borders and every other assertion stay intact. Original failed native invocation and preparation remain immutable. No app/model/artwork change or rendering/performance acceptance inferred.'}
    audit.write_new(CORRECTION, record)
    print(json.dumps({'status': STATUS, 'report': CORRECTION.relative_to(ROOT).as_posix()}), flush=True)
    return 0


if __name__ == '__main__': raise SystemExit(main())
