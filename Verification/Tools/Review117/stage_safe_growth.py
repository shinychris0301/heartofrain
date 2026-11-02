"""Stage opt-in growth policy on draft levels 27/44 only; never ship assets."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args();root, output = a.root.resolve(), a.output.resolve();cache = (root / '.verification-cache').resolve()
    if not output.is_relative_to(cache) or output == cache or output.exists():
        raise ValueError('Output must be a new directory inside .verification-cache')
    previous = cache / 'Review117/CampaignAllBottom01';output.mkdir(parents=True)
    rows=[]
    for n in range(11, 51):
        name=f'C01_L{n:03}.json';before=(previous/name).read_bytes()
        if n in (27,44):
            level=json.loads(before.decode('utf-8'))
            if not level.get('mossRegrowth',{}).get('enabled') or 'safeSegmentBottom' in level['mossRegrowth']:
                raise ValueError('Unexpected growth rule')
            level['mossRegrowth']['safeSegmentBottom']=True
            after=(json.dumps(level,indent=2)+'\n').encode('utf-8')
        else:after=before
        (output/name).write_bytes(after)
        rows.append({'level':n,'priorSHA256':sha(before),'draftSHA256':sha(after),'optedIn':n in (27,44)})
    report={'scope':'Opt-in policy data staged only; requires explicit approval and separately tested model support before use.',
            'toolSHA256':sha(Path(__file__).read_bytes()),'levels':rows}
    (output/'Report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([r for r in rows if r['optedIn']],indent=2))


if __name__ == '__main__':main()
