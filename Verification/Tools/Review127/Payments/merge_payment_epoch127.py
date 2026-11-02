"""Merge only independently reviewed diagnostic accuracy fixes into private Pay01.

No app layout, SDK, key, build, signing, device, backend or provider operation.
Both original preparation and run-plan bytes are retained unchanged.
"""
from __future__ import annotations
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('payment_preparation_epoch127',HERE/'prepare_payment_diagnostics127.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
PARENT=Path('E:/.verification-cache/HOTR127/Pay01')
ORIGINAL='223712b40a51ac417132133216b1afb877cc1de2faa84dffa2d59cd3ae66bafb'
ORIGINAL_PLAN='5e36e945fcd3895173e610cde0ab7bf82a07c146d5d8ce76c410ce5d26c56e27'
HARNES_BEFORE='f8f40739f4885d39a33f694a206e0c655128e300408b498bea589a0623860e36'
HARNES_AFTER='60cceebcc41ec6a62ca0ae5877da9ea72faa9981978d480700415b51dbe716c2'
RELATIVE='Assets/Review127Diagnostics/Runtime/PaymentDiagnostics127.cs'

def merge():
    original=PARENT/'Preparation127.json';plan_path=PARENT/'RunPlan127.json';new_path=PARENT/'Preparation127_Epoch02.json';new_plan=PARENT/'RunPlan127_Epoch02.json'
    prep.need(prep.sha(original)==ORIGINAL and prep.sha(plan_path)==ORIGINAL_PLAN,'ExactOriginalPrivateEpochRequired127')
    prep.need(not new_path.exists() and not new_plan.exists(),'FreshPrivateEpoch02Required127')
    value=json.loads(original.read_text('utf-8'));plan=json.loads(plan_path.read_text('utf-8'));project=PARENT/'Game'
    prep.need(Path(value['project']).resolve()==project.resolve() and value['status']=='PREPARED_PAYMENT_DIAGNOSTIC127' and value['versionCode']==127,'ExactPrivateDiagnosticProjectRequired127')
    prep.need(value['harnessSHA256']==HARNES_BEFORE and prep.sha(HERE/'PaymentDiagnostics127.cs')==HARNES_AFTER,'ExactReviewedAccuracyFixRequired127')
    before=prep.inventory(project);prep.need(before==value['inputs'],'OriginalPrivateEpochDrifted127')
    target=project/RELATIVE;prep.need(not target.is_symlink() and prep.sha(target)==HARNES_BEFORE,'OriginalPrivateHarnessRequired127')
    shutil.copyfile(HERE/'PaymentDiagnostics127.cs',target);prep.need(prep.sha(target)==HARNES_AFTER,'PrivateAccuracyMergeFailed127')
    before[RELATIVE]=HARNES_AFTER;value['inputs']=before;index=value['paths'].index(RELATIVE);value['sha256'][index]=HARNES_AFTER;value['harnessSHA256']=HARNES_AFTER
    value.update(sourceEpoch=2,epochPreparedUtc=datetime.now(timezone.utc).isoformat(),previousPreparationSHA256=ORIGINAL,epochToolSHA256=prep.sha(__file__),epochDelta={RELATIVE:{'before':HARNES_BEFORE,'after':HARNES_AFTER}},epochScope='Only two reviewed diagnostic accuracy fixes; no app modal/layout/source repair, SDK or configuration change.')
    prep.write(new_path,value)
    plan.update(sourceEpoch=2,preparationSHA256=prep.sha(new_path),previousRunPlanSHA256=ORIGINAL_PLAN,epochScope=value['epochScope'])
    plan['environmentReferences']['HOTR_PAYMENTDIAG127_RECEIPT']=str(new_path)
    prep.write(new_plan,plan)
    prep.need(prep.sha(original)==ORIGINAL and prep.sha(plan_path)==ORIGINAL_PLAN,'OriginalPrivateEpochMustRemainUnchanged127')
    return {'status':'PREPARED_PAYMENT_DIAGNOSTIC127_EPOCH02','project':str(project),'preparationSHA256':prep.sha(new_path),'runPlanSHA256':prep.sha(new_plan),'harnessSHA256':HARNES_AFTER,'changedPaths':[RELATIVE],'originalReceiptPreserved':True,'modalOrLayoutChanged':False,'actualBuild':False,'sdkAvailabilityInvoked':False}

if __name__=='__main__':
    try:print(json.dumps(merge()))
    except Exception as failure:
        code=str(failure);print(json.dumps({'status':'BLOCKED_PAYMENT_DIAGNOSTIC_EPOCH02','code':code if re.fullmatch('[A-Za-z0-9_]{1,120}',code) else type(failure).__name__}));raise SystemExit(1)
