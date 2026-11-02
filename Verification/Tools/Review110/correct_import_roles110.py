"""Correct only the ten already imported NEW TC metas in the closed safe window."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    evidence = ROOT / 'Verification/Evidence/Review110'
    imported = json.loads((evidence / 'Native/ImportMain01/MainSources_after.json').read_text('utf-8'))['files']
    baseline = json.loads((ROOT / 'Verification/Tools/Review110/BaselineMain110.json').read_text('utf-8'))['files']
    paths = sorted((ROOT / 'Unity/Assets/HeartOfTheRain/App/TeamsSocial/Art').glob('TC_*.png.meta'))
    if len(paths) != 10:
        raise ValueError('TenExactNewTcMetasRequired110')
    retained = evidence / 'RetainedSources/BeforeImporterCorrection110'
    retained.mkdir(parents=True, exist_ok=True)
    if any(retained.iterdir()):
        raise ValueError('FreshOwnedMetadataRetentionDirectoryRequired110')
    changes = []
    for path in paths:
        key = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        if key in baseline or sha(data) != imported[key]['sha256']:
            raise ValueError('ExactNewNormalizedMetadataRequired110')
        (retained / path.name).write_bytes(data)
        # Unity2022 serialized platform settings carry the actual values. The
        # thin package's top-level scalar was ignored by native import.
        after, compression = re.subn(rb'(?m)^(    textureCompression: )1(\r?)$', rb'\g<1>0\g<2>', data)
        after, budget = re.subn(rb'(?m)^(    maxTextureSize: )2048(\r?)$', rb'\g<1>4096\g<2>', after)
        if compression != 3 or budget != 3:
            raise ValueError('ExactThreeNativePlatformSettingsRequired110')
        before_guid = re.search(rb'(?m)^guid: ([a-f0-9]{32})', data).group(1)
        after_guid = re.search(rb'(?m)^guid: ([a-f0-9]{32})', after).group(1)
        if before_guid != after_guid:
            raise ValueError('GuidMustRemainExact110')
        path.write_bytes(after)
        changes.append(dict(path=key, before=sha(data), after=sha(after), guid=after_guid.decode('ascii'),
            platformCompressionFieldsCorrected=compression, platformPixelBudgetsCorrected=budget))
    (evidence / 'ImporterRoleCorrection110.json').write_text(json.dumps(dict(
        status='SOURCE_CORRECTION_NEW_TC_IMPORT_ROLES110', actualNativeVerification=False,
        scope='Closed-window correction of only ten NEW TC normalized metas. Default, Standalone and Android now use uncompressed/source4096 budgets; all authored GUIDs, filtering and sliced borders remain unchanged. Original pre-import and normalized pre-correction bytes are retained.',
        files=changes), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='SOURCE_CORRECTION_NEW_TC_IMPORT_ROLES110', changed=len(changes))))


if __name__ == '__main__':
    main()
