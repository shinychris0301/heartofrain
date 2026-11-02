"""Copy only Root's frozen AccountModal layout fix into private Pay01 Epoch03."""
from __future__ import annotations
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('layout_preparation_epoch127',HERE/'prepare_payment_diagnostics127.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
PARENT=Path('E:/.verification-cache/HOTR127/Pay01')
PREVIOUS='4bba9f2c9d2d25687cdea0866fc7daa4c48a3e40e5c88c0b5eb044464ab56bfd'
PREVIOUS_PLAN='cedf55f7bb518e9dce4ed76b2df460bd06c939e4295144867f1f6232cac22ca7'
EXPECTED='e6997e94a6de9de15bf5fa88346e92c249dd00a91d02fb329715f2fcda8733ec'
RELATIVE='Assets/HeartOfTheRain/App/AccountDesign/AccountModal.cs'

def merge():
    original=PARENT/'Preparation127_Epoch02.json';plan_path=PARENT/'RunPlan127_Epoch02.json';new_path=PARENT/'Preparation127_Epoch03.json';new_plan=PARENT/'RunPlan127_Epoch03.json'
    prep.need(prep.sha(original)==PREVIOUS and prep.sha(plan_path)==PREVIOUS_PLAN,'ExactPreviousPrivateEpochRequired127')
    prep.need(not new_path.exists() and not new_plan.exists(),'FreshPrivateEpoch03Required127')
    value=json.loads(original.read_text('utf-8'));plan=json.loads(plan_path.read_text('utf-8'));project=PARENT/'Game';source=prep.ROOT/'Unity'/RELATIVE;target=project/RELATIVE
    prep.need(Path(value['project']).resolve()==project.resolve() and value['sourceEpoch']==2,'ExactPrivateEpoch02ProjectRequired127')
    prep.need(prep.sha(source)==EXPECTED,'RootFrozenAccountLayoutRequired127')
    before=prep.inventory(project);prep.need(before==value['inputs'],'PreviousPrivateEpochDrifted127')
    prior=before[RELATIVE];meta=RELATIVE+'.meta';prep.need(prep.sha(prep.ROOT/'Unity'/meta)==before[meta],'OriginalAccountModalMetaMustRemainExact127')
    shutil.copyfile(source,target);prep.need(prep.sha(target)==EXPECTED,'PrivateLayoutMergeFailed127')
    before[RELATIVE]=EXPECTED;value['inputs']=before;index=value['paths'].index(RELATIVE);value['sha256'][index]=EXPECTED;value['mainInputs'][RELATIVE]=EXPECTED
    value['sourceDelta'][RELATIVE]={'before':value['sourceInputs'][RELATIVE],'after':EXPECTED}
    value.update(sourceEpoch=3,epochPreparedUtc=datetime.now(timezone.utc).isoformat(),previousPreparationSHA256=PREVIOUS,epochToolSHA256=prep.sha(__file__),epochDelta={RELATIVE:{'before':prior,'after':EXPECTED}},epochScope='Only Root-frozen AccountModal padding and bounded button-label layout; same actions, auth, original artwork/meta, provider and runtime configuration.')
    prep.write(new_path,value)
    plan.update(sourceEpoch=3,preparationSHA256=prep.sha(new_path),previousRunPlanSHA256=PREVIOUS_PLAN,epochScope=value['epochScope'])
    plan['environmentReferences']['HOTR_PAYMENTDIAG127_RECEIPT']=str(new_path);prep.write(new_plan,plan)
    prep.need(prep.sha(original)==PREVIOUS and prep.sha(plan_path)==PREVIOUS_PLAN,'PreviousPrivateEpochMustRemainUnchanged127')
    return {'status':'PREPARED_PAYMENT_DIAGNOSTIC127_EPOCH03','project':str(project),'preparationSHA256':prep.sha(new_path),'runPlanSHA256':prep.sha(new_plan),'accountModalSHA256':EXPECTED,'changedPaths':[RELATIVE],'previousReceiptsPreserved':True,'actualBuild':False,'sdkAvailabilityInvoked':False}

if __name__=='__main__':
    try:print(json.dumps(merge()))
    except Exception as failure:
        code=str(failure);print(json.dumps({'status':'BLOCKED_PAYMENT_DIAGNOSTIC_EPOCH03','code':code if re.fullmatch('[A-Za-z0-9_]{1,120}',code) else type(failure).__name__}));raise SystemExit(1)
