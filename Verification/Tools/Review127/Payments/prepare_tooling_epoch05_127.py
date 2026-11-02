"""Append only runner02 metadata after Layout01 closed; never edits project inputs."""
from __future__ import annotations
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tooling_preparation_epoch127',HERE/'prepare_payment_diagnostics127.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
PARENT=Path('E:/.verification-cache/HOTR127/Pay01')
PREVIOUS='cf762bcf737c72c92255e100f606726af4beb513692e703973a5838e49320544'
OLD_RUNNER='69c7d098f0a3d99a99a42392d04d67b00ac64a10e548020647c9f1f78ce0f650'
NEW_RUNNER='56e7ee24e04a436230c6c85802f5d623606ef1130972064a81213692dfdd2c96'
REVIEW='e5e424fb9e0b33dfc931eacda3993ea6078a612aa5d6307d830ca13cdccf891a'

def prepare():
    original=PARENT/'Preparation127_Epoch04.json';old_plan=PARENT/'RunPlan127_Epoch04.json';new=PARENT/'Preparation127_Epoch05.json';new_plan=PARENT/'RunPlan127_Epoch05.json'
    prep.need(prep.sha(original)==PREVIOUS,'ExactPreviousSourceEpoch04Required127')
    prep.need(not new.exists() and not new_plan.exists(),'FreshToolOnlyEpoch05Required127')
    value=json.loads(original.read_text('utf-8'));plan=json.loads(old_plan.read_text('utf-8'));project=PARENT/'Game'
    prep.need(Path(value['project']).resolve()==project.resolve() and value['sourceEpoch']==4,'ExactFrozenPrivateSourceEpoch04Required127')
    before=prep.inventory(project);prep.need(len(before)==6310 and before==value['inputs'],'UnexpectedPrivateInputDriftMustNotBeResealed127')
    prep.need(prep.sha(HERE/'run_payment_diagnostics127.py')==OLD_RUNNER and prep.sha(HERE/'run_payment_diagnostics127_02.py')==NEW_RUNNER,'ExactImmutableRunnerVersionsRequired127')
    review=prep.ROOT/'Verification/Evidence/Review127/Payments/IndependentNativeRunnerReview127.json';prep.need(prep.sha(review)==REVIEW,'ExactIndependentHardenedRunnerReviewRequired127')
    process=prep.ROOT/'Verification/Evidence/Review127/Payments/Native/Layout01/Process.json';failure=prep.ROOT/'Verification/Evidence/Review127/Payments/Native/Layout01/Native.json';facts=json.loads(process.read_text('utf-8'));native=json.loads(failure.read_text('utf-8'))
    prep.need(facts.get('processStopped') is True and facts.get('operation')=='layout' and facts.get('preparationSHA256')==PREVIOUS and facts.get('runnerSHA256')==OLD_RUNNER and native.get('cases')==0,'ClosedPriorNativeLayoutAttemptRequired127')
    value.update(toolingEpoch=5,epochPreparedUtc=datetime.now(timezone.utc).isoformat(),previousPreparationSHA256=PREVIOUS,epochToolSHA256=prep.sha(__file__),epochDelta={},toolingEpochDelta={'nativeRunner':{'before':OLD_RUNNER,'after':NEW_RUNNER,'path':'Verification/Tools/Review127/Payments/run_payment_diagnostics127_02.py'}},nativeRunnerSHA256=NEW_RUNNER,nativeRunnerReviewSHA256=REVIEW,privateInputComparison={'count':6310,'changed':0,'missing':0,'new':0,'unityGeneratedSettingsChanges':[]},priorClosedLayout01={'processSHA256':prep.sha(process),'nativeSHA256':prep.sha(failure),'cases':0,'sourceChanged':False,'reason':'Cold Unity Editor SearchDatabase startup indexing error before any UI case; one Root-authorized unchanged-source warm-cache retry.'},epochScope='TOOL ONLY: exact same6310 private inputs/source epoch4; hardened Python pre-credential report/source-pin gate. Original source/fixture/builder/art/vendor/runtime settings bytes remain exact.')
    prep.write(new,value)
    plan.update(toolingEpoch=5,sourceEpoch=4,preparationSHA256=prep.sha(new),previousRunPlanSHA256=prep.sha(old_plan),nativeRunnerSHA256=NEW_RUNNER,nativeRunnerReviewSHA256=REVIEW,epochScope=value['epochScope'])
    plan['environmentReferences']['HOTR_PAYMENTDIAG127_RECEIPT']=str(new)
    for command in plan['rootCommands']:
        for index,part in enumerate(command):
            if part.endswith('run_payment_diagnostics127.py'):command[index]=str(HERE/'run_payment_diagnostics127_02.py')
            elif part==str(original):command[index]=str(new)
            elif part=='Layout01':command[index]='Layout02'
            elif part=='<Layout01/Native.json>':command[index]='<Layout02/Native.json>'
    prep.write(new_plan,plan);prep.need(prep.sha(original)==PREVIOUS and prep.sha(HERE/'run_payment_diagnostics127.py')==OLD_RUNNER,'OriginalEpoch04AndRunnerMustRemainUnchanged127')
    return {'status':'PREPARED_TOOL_ONLY_PAYMENT_DIAGNOSTIC127_EPOCH05','preparationSHA256':prep.sha(new),'runPlanSHA256':prep.sha(new_plan),'sourceEpoch':4,'toolingEpoch':5,'privateInputs':6310,'privateInputChanges':0,'hardenedRunnerSHA256':NEW_RUNNER,'nativeRunnerExecuted':False,'signingAttempted':False}

if __name__=='__main__':
    try:print(json.dumps(prepare()))
    except Exception as failure:
        code=str(failure);print(json.dumps({'status':'BLOCKED_TOOLING_EPOCH05','code':code if re.fullmatch('[A-Za-z0-9_]{1,120}',code) else type(failure).__name__}));raise SystemExit(1)
