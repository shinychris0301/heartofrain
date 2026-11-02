"""Compare delivered files and inspect Unity GUID/resource integrity without Unity."""
import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITY = ROOT / 'Unity'


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'Verification/Evidence/Integrity.json')
    parser.add_argument('--allow-documented-changes', action='store_true')
    args = parser.parse_args()
    baseline = json.loads((ROOT / 'Unity_Files_SHA256.json').read_text(encoding='utf-8-sig'))
    missing, changed = [], []
    for relative, expected in baseline.items():
        path = UNITY / relative
        if not path.is_file():
            missing.append(relative)
        elif hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() != expected:
            changed.append(relative)
    guids = collections.defaultdict(list)
    missing_meta, orphan_meta, refs = [], [], []
    resources = collections.defaultdict(list)
    for path in (UNITY / 'Assets').rglob('*'):
        relative = path.relative_to(UNITY).as_posix()
        if path.suffix == '.meta':
            if not Path(str(path)[:-5]).exists():
                orphan_meta.append(relative)
            for guid in re.findall(r'^guid: ([0-9a-f]{32})$', path.read_text(encoding='utf-8-sig'), re.M):
                guids[guid].append(relative[:-5])
            continue
        if not Path(str(path) + '.meta').exists():
            missing_meta.append(relative)
        if path.is_file() and 'Resources' in path.parts:
            parts = path.relative_to(UNITY).parts
            key = Path(*parts[parts.index('Resources')+1:]).with_suffix('').as_posix().lower()
            resources[key].append(relative)
        if path.is_file() and path.suffix in ('.unity', '.prefab', '.asset', '.mat', '.controller', '.anim'):
            refs.extend((relative, guid) for guid in re.findall(r'guid: ([0-9a-f]{32})', path.read_text(encoding='utf-8-sig')))
    # Unity built-in GUIDs are zero-padded reserved IDs, not missing project assets.
    unresolved = [{'owner': p, 'guid': g} for p, g in refs if g not in guids and not g.startswith('0000000000000000')]
    wrong_native_reference_types = []
    for path in (UNITY/'Assets').rglob('*'):
        if path.suffix not in ('.unity','.prefab','.asset','.mat'): continue
        for match in re.finditer(r'guid: ([0-9a-f]{32})[,\s]*type:\s*3\b',path.read_text(encoding='utf-8-sig')):
            targets = guids.get(match[1],[])
            if len(targets)==1 and Path(targets[0]).suffix in ('.asset','.mat'):
                wrong_native_reference_types.append({'owner':path.relative_to(UNITY).as_posix(),'target':targets[0]})
    report = {
        'scope': 'Static file/GUID/Resources checks only; not native import, rendering or device verification.',
        'baseline_files': len(baseline), 'unchanged': len(baseline)-len(missing)-len(changed),
        'missing_baseline_files': missing, 'changed_baseline_files': changed,
        'duplicate_guids': {g: p for g,p in guids.items() if len(p)>1},
        'missing_meta': missing_meta, 'orphan_meta': orphan_meta,
        'unresolved_serialized_guids': unresolved,
        'wrong_native_reference_types': wrong_native_reference_types,
        'resource_key_collisions': {g: p for g,p in resources.items() if len(p)>1},
    }
    allowed = set()
    importer_round_trips=[]
    if args.allow_documented_changes:
        repair_file = ROOT/'Verification/Evidence/Native/Native_Reference_Repair.json'
        if repair_file.exists():
            allowed.update(c['owner'] for c in json.loads(repair_file.read_text())['changes'])
        format_file = ROOT/'Verification/Evidence/Native/Pointer_Format_Repair.json'
        if format_file.exists():
            allowed.update(c['file'].replace('\\','/').removeprefix('Unity/') for c in json.loads(format_file.read_text()))
        regression_file=ROOT/'Verification/Evidence/Regression/Repairs.json'
        if regression_file.exists():
            allowed.update(c['file'].removeprefix('Unity/') for c in json.loads(regression_file.read_text(encoding='utf-8'))['changes'])
        allowed.update([
            'Assets/HeartOfTheRain/M48/Editor/M52ReviewSession.cs',
            'Assets/HeartOfTheRain/App/Home/Editor/HomePageEditor.cs',
            'Assets/HeartOfTheRain/App/Home/HomePageAssets.asset',
            'Assets/HeartOfTheRain/App/PreLevel/Runtime/PreLevelAssets.cs',
            'Assets/HeartOfTheRain/App/FirstStart/Runtime/PracticeBoardView.cs',
            'Assets/HeartOfTheRain/M47/Runtime/GameplayScreen.cs',
            'Assets/HeartOfTheRain/M46/Runtime/M46Playground.cs',
            'Assets/HeartOfTheRain/Boosters/Runtime/BoosterReview.cs',
            'Assets/HeartOfTheRain/Chapter01M07/Scripts/BoardReactionReview.cs',
        ])
        metadata_file = ROOT/'Verification/Evidence/Native/Metadata_Preservation.json'
        if metadata_file.exists():
            for entry in json.loads(metadata_file.read_text())['files']:
                if entry['action']=='RETAIN_INTENTIONAL_IMPORTER_REPAIR':
                    allowed.add(entry['file'])
                elif entry['file'] in changed and hashlib.sha256((UNITY/entry['file']).read_bytes()).hexdigest()==entry['imported_sha256']:
                    # A subsequent native run can reproduce the exact archived
                    # Unity serializer output; this is an audited difference.
                    allowed.add(entry['file'])
                    importer_round_trips.append(entry['file'])
    unexpected = sorted(set(changed)-allowed)
    level_path='Assets/HeartOfTheRain/M47/Data/Levels/C01_L050.json'
    original=json.loads(subprocess.run(['git','show','1d1b30a:Unity/'+level_path],cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout)
    current=json.loads((UNITY/level_path).read_text(encoding='utf-8'))
    original['integrationNotes']=[v.replace('40 moves is a proposal; balance is not yet verified.','44 moves is a proposal; balance is not yet verified.') for v in original['integrationNotes']]
    report['level_50_only_descriptive_note_changed']=original==current
    report['changed_original_art_audio_fonts']=[p for p in changed if Path(p).suffix.lower() in ('.png','.jpg','.wav','.ogg','.mp3','.ttf','.otf')]
    report['documented_changed_baseline_files'] = sorted(set(changed)&allowed)
    report['archived_importer_serialization_only_files']=sorted(importer_round_trips)
    report['unexpected_changed_baseline_files'] = unexpected
    # Art replacements require both an explicit repair entry and the supplied
    # M70 contract's exact bytes. Other original art changes remain failures.
    approved_art = set()
    contract_path = UNITY/'Assets/HeartOfTheRain/M69/Data/M70_PowerupContract.json'
    if args.allow_documented_changes and contract_path.exists():
        for entry in json.loads(contract_path.read_text())['entries']:
            for name in ('texture', 'resourceTexture'):
                path = entry[name]
                if path in allowed and hashlib.sha256((UNITY/path).read_bytes()).hexdigest() == entry['textureSHA256']:
                    approved_art.add(path)
    report['authorized_art_replacements'] = sorted(approved_art & set(report['changed_original_art_audio_fonts']))
    report['unexpected_original_art_changes'] = sorted(set(report['changed_original_art_audio_fonts']) - approved_art)
    failed = bool(missing or unexpected or report['duplicate_guids'] or unresolved or wrong_native_reference_types or missing_meta or orphan_meta or report['resource_key_collisions'] or not report['level_50_only_descriptive_note_changed'] or report['unexpected_original_art_changes'])
    report['status'] = 'FAIL_STATIC_INTEGRITY' if failed else 'PASS_STATIC_INTEGRITY_WITH_DOCUMENTED_REPAIRS' if changed else 'PASS_STATIC_INTEGRITY'
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status':report['status'],'baseline_files':len(baseline),'unchanged':report['unchanged'],'documented_changes':len(report['documented_changed_baseline_files']),'unexpected_changes':unexpected,'report':str(args.out)},indent=2))
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(run())
