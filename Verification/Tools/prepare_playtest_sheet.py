import csv
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / 'Verification/Evidence/StaticBaseline/Chapter01_Levels.csv'
output = root / 'Verification/Campaign_Playtest.csv'
if output.exists():
    raise SystemExit('Refusing to overwrite recorded playtests: ' + str(output))
with source.open(encoding='utf-8-sig', newline='') as stream:
    levels = list(csv.DictReader(stream))
with output.open('w', encoding='utf-8-sig', newline='') as stream:
    columns = ['level','id','moves','goals','seed','device','os','build','locale','tester_cohort','attempts','wins','quits','remaining_moves','duration_seconds','starting_items','tools_used','notes','evidence','status']
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for level in levels:
        writer.writerow({**{key:level[key] for key in ['level','id','moves','goals','seed']},'status':'PENDING_HUMAN_DEVICE_PLAYTEST'})
print('Prepared 50 pending level rows:', output)
