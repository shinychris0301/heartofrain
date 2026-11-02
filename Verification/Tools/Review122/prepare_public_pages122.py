"""Prepare an offline, hash-pinned transfer of the temporary public pages."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Release/Production122/public'
OUTPUT = ROOT / '.verification-cache/Review122/PublicPages01'


def main():
    OUTPUT.mkdir(exist_ok=False)
    installer = (SOURCE / 'Install-PublicDrafts122.ps1').read_text(encoding='utf-8-sig')
    expected = re.search(r"\$expected122=@'\n(.*?)\n'@", installer, re.S).group(1) + '\n'
    routes = re.search(r'\$routes122=@"\n(.*?)\n"@', installer, re.S).group(1)
    routes = routes.replace('$slashRoot122', 'C:/ProgramData/HeartOfTheRain/public-draft122')
    candidate = expected.replace('api.novamind-it.ru {\n', 'api.novamind-it.ru {\n' + routes)
    with (OUTPUT / 'CaddyDraftCandidate').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(candidate)
    names = ['privacy.html', 'support.html', 'terms.html', 'pages.sha256.json', 'Install-PublicDrafts122.ps1']
    hashes = {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in names}
    with zipfile.ZipFile(OUTPUT / 'hotr-public-drafts122.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.write(SOURCE / name, arcname=name)
    receipt = {'status': 'prepared_not_published', 'files': hashes,
               'archiveSHA256': hashlib.sha256((OUTPUT / 'hotr-public-drafts122.zip').read_bytes()).hexdigest(),
               'legalContentApproved': False, 'operatorDetailsPending': True}
    with (OUTPUT / 'transfer.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
