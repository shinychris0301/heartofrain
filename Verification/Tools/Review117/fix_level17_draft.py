"""Prepare an isolated L17 topology variant; keep the other 39 drafts exact."""
import argparse
import hashlib
import json
from pathlib import Path

from generate_campaign_varied import candidate


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root, output = a.root.resolve(), a.output.resolve()
    cache = (root / '.verification-cache').resolve()
    if not output.is_relative_to(cache) or output == cache or output.exists():
        raise ValueError('Output must be a new directory in .verification-cache')
    prior = cache / 'Review117/CampaignVaried01'
    output.mkdir(parents=True)
    data = []
    for n in range(11, 51):
        name = f'C01_L{n:03}.json'
        before = (prior / name).read_bytes()
        if n == 17:
            source_path = root / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117' / name
            level = json.loads(source_path.read_text(encoding='utf-8-sig'))
            result, detail = candidate(level, bottom_fixed=True)
            result['balancePass']['scope'] = 'L17 fixed blockers moved below gem field; diagnostic candidate, not balance approved'
            after = (json.dumps(result, indent=2) + '\n').encode()
        else:
            after = before
            detail = None
        (output / name).write_bytes(after)
        data.append({'level': n, 'priorSHA256': sha(before), 'draftSHA256': sha(after),
                     'changed': before != after, 'details': detail})
    report = {'scope': 'L17 topology variant; no Unity, playability, replay, device or balance certification.',
              'toolSHA256': sha(Path(__file__).read_bytes()), 'levels': data}
    (output / 'Report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([x for x in data if x['changed']], indent=2))


if __name__ == '__main__':
    main()
