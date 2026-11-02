"""Independent workbook arithmetic and structural localization checks."""
import json
import math
import re
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Content_Review.json'


def run():
    source = load_workbook(ROOT / 'Codex_Handoff/Monetization/Heart_of_the_Rain_Monetization_Model.xlsx', data_only=False)
    cached = load_workbook(ROOT / 'Codex_Handoff/Monetization/Heart_of_the_Rain_Monetization_Model.xlsx', data_only=True)
    checked, failures = set(), []

    def check(sheet, address, expected):
        actual = cached[sheet][address].value
        checked.add((sheet, address))
        equal = actual == expected if isinstance(expected, str) else isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-8)
        if not equal:
            failures.append({'sheet': sheet, 'cell': address, 'expected': expected, 'cached': actual})

    m = {i: cached['Monthly Model'][f'B{i}'].value for i in range(16, 31)}
    gross = m[18]*m[19]*m[20]
    iap = gross*(1-m[22])*(1-m[21])
    impressions = m[17]*m[16]*m[23]*m[24]*m[25]
    ads = impressions/1000*m[26]
    service = m[17]*m[16]*m[27]
    acquisition = m[29]*m[30]
    outputs = {5:gross,6:iap,7:impressions,8:ads,9:iap+ads,10:service,11:acquisition,12:iap+ads-service-m[28]-acquisition,13:(iap+ads)/(m[17]*m[16]),32:'OK'}
    for row, value in outputs.items(): check('Monthly Model', f'B{row}', value)

    c = {i: cached['Cohort 90d'][f'B{i}'].value for i in list(range(5,12))+list(range(14,19))}
    check('Cohort 90d','B10',m[21]); check('Cohort 90d','B11',m[22])
    revenue = contribution = 0
    payback = 'Not reached'
    for day in range(91):
        points = [(0,c[14]),(1,c[15]),(7,c[16]),(30,c[17]),(90,c[18])]
        for (a,ra),(b,rb) in zip(points,points[1:]):
            if a <= day <= b:
                retention = ra+(rb-ra)*(day-a)/(b-a)
                break
        active = c[5]*retention
        daily_iap = active*c[7]*(1-m[21])*(1-m[22])
        daily_ads = active*c[8]
        cost = active*c[9]
        net = daily_iap+daily_ads-cost
        revenue += daily_iap+daily_ads; contribution += net
        paid = int(contribution >= c[5]*c[6])
        if paid and payback == 'Not reached': payback = day
        for col,value in zip('ABCDEFGHIJ',[day,retention,active,daily_iap,daily_ads,cost,net,revenue,contribution,paid]):
            check('Cohort 90d',f'{col}{day+22}',value)
    for row,value in {5:revenue/c[5],6:contribution/c[5],7:revenue/(c[5]*c[6]),8:contribution-c[5]*c[6],9:payback,10:contribution/c[5],11:'OK',12:'OK'}.items():
        check('Cohort 90d',f'F{row}',value)

    e = {i: cached['Economy'][f'B{i}'].value for i in range(16,28)}
    first = e[16]*e[17]*e[18]
    faucets = first*e[19]+e[20]+e[21]
    tool = e[16]*e[22]*e[23]; refill = e[24]*e[25]; cont = e[16]*e[26]*e[27]
    for row,value in {5:first,6:faucets,7:tool,8:refill,9:cont,10:faucets-tool-refill-cont,11:math.ceil(e[23]/e[19]),29:'OK'}.items():
        check('Economy',f'B{row}',value)
    formula_cells = {(s.title,c.coordinate) for s in source for row in s for c in row if c.data_type=='f'}

    localization = []
    translations = ROOT / 'Unity/Assets/HeartOfTheRain/App/Localization/Data/Translations.json'
    data = json.loads(translations.read_text(encoding='utf-8'))
    issues = []
    expected_locales = ['en','es','fr','de','ru']
    if data['locales'] != expected_locales: issues.append('Unexpected locale registry')
    for key,values in data['entries'].items():
        if len(values) != 5 or any(not isinstance(v,str) or not v.strip() for v in values):
            issues.append('Missing translation: '+key)
        placeholders = [sorted(re.findall(r'\{\d+(?::[^}]+)?\}',v)) for v in values]
        if any(p != placeholders[0] for p in placeholders): issues.append('Placeholder mismatch: '+key)
    localization.append({'file': str(translations.relative_to(ROOT)), 'entries': len(data['entries']), 'issues': issues})
    for path in sorted(translations.parent.joinpath('Stories').glob('Story_*.json')):
        story = json.loads(path.read_text(encoding='utf-8'))
        problems = []
        if [c['number'] for c in story['chapters']] != list(range(1,101)): problems.append('Chapter IDs differ')
        for chapter in story['chapters']:
            if any(not chapter.get(key,'').strip() for key in ('title','opening','ending')): problems.append('Missing narrative '+str(chapter['number']))
        localization.append({'file': str(path.relative_to(ROOT)), 'locale': story['locale'], 'chapters': len(story['chapters']), 'issues': problems})
    report = {
        'scope':'Independent arithmetic for supplied base inputs and structural locale checks; no Excel engine recalculation, sensitivity validation, native-speaker or glyph certification.',
        'workbook':{'formula_cells':len(formula_cells),'independently_checked':len(checked & formula_cells),'uncovered_formula_cells':sorted(formula_cells-checked),'mismatches':failures,'example_monthly_contribution':outputs[12],'example_contribution_per_install_90d':contribution/c[5],'example_payback_day':payback},
        'localization':localization,
    }
    OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return int(bool(failures or formula_cells-checked or any(row['issues'] for row in localization)))


if __name__ == '__main__':
    raise SystemExit(run())
