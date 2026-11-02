"""Read supplied records without executing embedded code or workbook formulas."""
import hashlib
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from openpyxl import load_workbook
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SUPPLIED = ROOT.parent / 'zips'
OUT = ROOT / 'Verification' / 'Evidence' / 'Materials'
CACHE = ROOT / '.verification-cache' / 'references'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('style', 'script'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    summary = {'scope': 'Document extraction, integrity and workbook structure; no embedded instructions executed, no formula recalculation or visual approval.', 'files': [], 'archives': [], 'references': []}
    names = ['Heart_of_the_Rain_Codex_Documentation.zip', 'Heart_of_the_Rain_Handbook.html', 'Heart_of_the_Rain_Monetization_Model.xlsx', 'Heart_of_the_Rain_Original_References.zip']
    for name in names:
        path = SUPPLIED / name
        data = path.read_bytes()
        summary['files'].append({'file': str(path), 'bytes': len(data), 'sha256': sha(data)})
        if path.suffix != '.zip':
            local = ROOT / 'Codex_Handoff' / ('Monetization' if path.suffix == '.xlsx' else '') / name
            summary['files'][-1]['matches_handoff_copy'] = local.exists() and local.read_bytes() == data
            continue
        with zipfile.ZipFile(path) as archive:
            record = {'file': name, 'crc_error': archive.testzip(), 'entries': [], 'handoff_matches': 0, 'handoff_mismatches': []}
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                body = archive.read(entry)
                record['entries'].append({'path': entry.filename, 'bytes': len(body), 'sha256': sha(body)})
                parts = Path(entry.filename.replace('\\', '/')).parts
                if '..' in parts or Path(entry.filename).is_absolute():
                    raise ValueError('Unsafe archive path: ' + entry.filename)
                if name.endswith('Codex_Documentation.zip'):
                    candidates = [ROOT / Path(*parts)]
                    if 'Codex_Handoff' in parts:
                        candidates.append(ROOT / Path(*parts[parts.index('Codex_Handoff'):]))
                    else:
                        candidates.append(ROOT / 'Codex_Handoff' / Path(*parts[1:]))
                    existing = next((p for p in candidates if p.is_file()), None)
                    if existing:
                        if existing.read_bytes() == body:
                            record['handoff_matches'] += 1
                        else:
                            record['handoff_mismatches'].append(str(existing.relative_to(ROOT)))
                else:
                    target = CACHE / Path(entry.filename).name
                    target.write_bytes(body)
                    if target.suffix.lower() == '.pdf':
                        reader = PdfReader(target)
                        pages = [page.extract_text() or '' for page in reader.pages]
                        (OUT / (target.stem + '.txt')).write_text('\n'.join(f'\n--- PAGE {i+1} ---\n{text}' for i, text in enumerate(pages)), encoding='utf-8')
                        summary['references'].append({'file': target.name, 'pages': len(pages), 'page_text_lengths': [len(t) for t in pages], 'text_characters': sum(map(len, pages)), 'sha256': sha(body)})
                    elif target.suffix.lower() in ('.md', '.txt'):
                        (OUT / target.name).write_bytes(body)
                        summary['references'].append({'file': target.name, 'text_characters': len(body.decode('utf-8-sig')), 'sha256': sha(body)})
            summary['archives'].append(record)
    parser = TextHTML()
    parser.feed((SUPPLIED / names[1]).read_text(encoding='utf-8-sig'))
    (OUT / 'Handbook_Text.txt').write_text('\n'.join(parser.parts), encoding='utf-8')
    book_path = SUPPLIED / names[2]
    book = load_workbook(book_path, data_only=False)
    cached = load_workbook(book_path, data_only=True)
    sheets = []
    lines = []
    for sheet in book:
        formulas = errors = missing = 0
        for row in sheet:
            values = []
            for cell in row:
                if cell.value is None:
                    continue
                value = cached[sheet.title][cell.coordinate].value
                if cell.data_type == 'f':
                    formulas += 1
                    missing += value is None
                errors += cached[sheet.title][cell.coordinate].data_type == 'e'
                values.append(f'{cell.coordinate}: {cell.value}' + (f' [cached={value}]' if cell.data_type == 'f' else ''))
            if values:
                lines.append(f'[{sheet.title}] ' + ' | '.join(values))
        sheets.append({'name': sheet.title, 'rows': sheet.max_row, 'columns': sheet.max_column, 'formulas': formulas, 'cached_errors': errors, 'formulas_without_cached_values': missing})
    summary['workbook'] = {'sheets': sheets, 'external_links': len(book._external_links), 'vba': book.vba_archive is not None, 'formula_recalculation': 'NOT_RUN; cached values inspected only'}
    (OUT / 'Workbook_Cells.txt').write_text('\n'.join(lines), encoding='utf-8')
    (OUT / 'Materials_Review.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({**summary, 'archives': [{k:v for k,v in a.items() if k != 'entries'} for a in summary['archives']]}, indent=2))


if __name__ == '__main__':
    run()
