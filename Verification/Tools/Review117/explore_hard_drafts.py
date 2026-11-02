"""Prepare a new isolated comparison set with three lower-density drafts.

This does not change source assets or endorse the variants as balanced.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from generate_campaign_drafts import candidate


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    cache = (root / '.verification-cache').resolve()
    if not output.is_relative_to(cache) or output == cache or output.exists():
        raise ValueError('Output must be a new directory in .verification-cache')
    previous = cache / 'Review117/CampaignDrafts02'
    output.mkdir(parents=True)
    report = {'scope': 'Static provisional lower-coverage variants only; no Unity, playability, difficulty, backend or device approval.', 'levels': []}
    for n in range(11, 51):
        name = f'C01_L{n:03}.json'
        prior = (previous / name).read_bytes()
        if n not in (15, 20, 35):
            (output / name).write_bytes(prior)
            continue
        original_path = root / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117' / name
        original_bytes = original_path.read_bytes()
        original = json.loads(original_bytes.decode('utf-8-sig'))
        original_cap = original['metrics'].get('coverageCapPercent')
        altered = copy.deepcopy(original)
        altered['metrics']['coverageCapPercent'] = 56
        draft, details = candidate(altered)
        draft['balancePass']['scope'] = 'Provisional 56 percent cap comparison; no human playability or difficulty assessment'
        new = (json.dumps(draft, indent=2) + '\n').encode('utf-8')
        (output / name).write_bytes(new)
        prior_data = json.loads(prior.decode('utf-8'))
        report['levels'].append({'level': n, 'legacySHA256': sha(original_bytes),
                                 'priorDraftSHA256': sha(prior), 'variantSHA256': sha(new),
                                 'originalCap': original_cap, 'variantCap': 56,
                                 'priorGoals': prior_data['goals'], 'variantGoals': draft['goals'], **details})
    report['toolSHA256'] = sha(Path(__file__).read_bytes())
    (output / 'VariantReport.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
