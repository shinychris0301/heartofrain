"""Root-approved isolated Editor-fixture-only update; no native or provider call."""
from __future__ import annotations
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('editor_fixture_epoch06',HERE/'prepare_payment_diagnostics127.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
PARENT=Path('E:/.verification-cache/HOTR127/Pay01')
PREVIOUS='ea1f699416b0ef7299aafa5454b4786f62fe6a215b7540dd2616f6a1e7c287c8'
PREVIOUS_PLAN='aeada410c696f9fef944c96555623d841517adac57350ead4681469c334ce346'
BEFORE='683fc91985b6b66f61f2c8aeb57d1c439ab4ab70c496ad3c30992d82f5e38787'
AFTER='ba55deb177260489032e3fe121500c1b402ccca6dbdc02d47993f122b0394733'
RELATIVE='Assets/Review127Diagnostics/Editor/SigninLayout127Verification.cs'
BUILDER='a23b3a242f542a3187baa69f5e45cd11ed06f95b1a65f2ad219ea017fda2db11'

def prepare():
    old=PARENT/'Preparation127_Epoch05.json';old_plan=PARENT/'RunPlan127_Epoch05.json';new=PARENT/'Preparation127_Epoch06.json';new_plan=PARENT/'RunPlan127_Epoch06.json'
    prep.need(prep.sha(old)==PREVIOUS and prep.sha(old_plan)==PREVIOUS_PLAN,'ExactPreviousFrozenEpoch05Required127')
    prep.need(not new.exists() and not new_plan.exists(),'FreshEditorFixtureEpoch06Required127')
    value=json.loads(old.read_text('utf-8'));plan=json.loads(old_plan.read_text('utf-8'));project=PARENT/'Game';target=project/RELATIVE;source=prep.ROOT/'Verification/Tools/Review127/Signin/SigninLayout127Verification.cs'
    prep.need(Path(value['project']).resolve()==project.resolve() and prep.sha(source)==AFTER and prep.sha(target)==BEFORE,'ExactReviewedEditorStartupFixtureRequired127')
    inputs=prep.inventory(project);prep.need(len(inputs)==6310 and inputs==value['inputs'],'UnexpectedProjectDriftBeforeEditorFix127')
    prep.need(prep.sha(project/'Assets/Review127Diagnostics/Editor/PaymentDiagnosticBuild127.cs')==BUILDER,'NativeBuilderMustRemainFrozen127')
    history=PARENT/'History/EditorFixture683fc919';history.mkdir(parents=True,exist_ok=False);shutil.copyfile(target,history/'SigninLayout127Verification.cs');shutil.copyfile(Path(str(target)+'.meta'),history/'SigninLayout127Verification.cs.meta');prep.need(prep.sha(history/'SigninLayout127Verification.cs')==BEFORE,'ExactOriginalEditorFixtureHistoryRequired127')
    meta=prep.sha(Path(str(target)+'.meta'));shutil.copyfile(source,target);prep.need(prep.sha(target)==AFTER and prep.sha(Path(str(target)+'.meta'))==meta,'EditorFixtureOnlyCopyRequired127')
    inputs[RELATIVE]=AFTER;value['inputs']=inputs;value['sha256'][value['paths'].index(RELATIVE)]=AFTER
    value.update(sourceEpoch=6,runtimeSourceEpoch=4,toolingEpoch=5,epochPreparedUtc=datetime.now(timezone.utc).isoformat(),previousPreparationSHA256=PREVIOUS,epochToolSHA256=prep.sha(__file__),nativeFixtureSHA256=AFTER,epochDelta={RELATIVE:{'before':BEFORE,'after':AFTER}},runtimeAssetChanges=[],epochScope='EDITOR FIXTURE ONLY: ordinary Search startup completes in Edit mode before Play, strict errors retained across reload. All other6309 project inputs, seven runtime/UI bindings, original meta/art/vendor, builder and immutable runners remain unchanged.')
    prep.write(new,value)
    plan.update(sourceEpoch=6,runtimeSourceEpoch=4,toolingEpoch=5,preparationSHA256=prep.sha(new),previousRunPlanSHA256=PREVIOUS_PLAN,epochScope=value['epochScope'],isolationWrapper='Verification/Tools/Review127/Payments/run_isolated_native127_02.py',isolationWrapperSHA256=prep.sha(HERE/'run_isolated_native127_02.py'))
    plan['environmentReferences']['HOTR_PAYMENTDIAG127_RECEIPT']=str(new)
    plan['additionalRootPreCredentialCheck']='Before invoking packaging or --build, Root must inspect actual accepted native layout report and require editorStartupCompletedBeforePlay=true, complete180cases/540layouts, zeroerrors, actualNativeLayout=true, actualProvider=false, deviceTouched=false, and all6 source bindings matching current private project. Existing immutable runner02 gate remains unchanged; C# RequireAcceptedReport also requires the startup flag.'
    plan['editorStateScope']='Ordinary private UserSettings/Search.index creation by normal Editor startup is expected and outside sourceInputs. No claim that all global Editor preferences remain unchanged; the isolation wrapper separately leases/restores only the two exact ADB lifecycle preferences.'
    for command in plan['rootCommands']:
        for index,part in enumerate(command):
            if part==str(old):command[index]=str(new)
            elif part=='Layout02':command[index]='Layout04'
            elif part=='<Layout02/Native.json>':command[index]='<Layout04/Native.json>'
            elif part.endswith('run_payment_diagnostics127_02.py'):command[index]=str(HERE/'run_isolated_native127_02.py')
    prep.write(new_plan,plan)
    prep.need(prep.sha(old)==PREVIOUS and prep.sha(old_plan)==PREVIOUS_PLAN,'PriorEpoch05MustRemainExact127')
    return {'status':'PREPARED_EDITOR_ONLY_EPOCH06_127','preparationSHA256':prep.sha(new),'runPlanSHA256':prep.sha(new_plan),'editorFixtureSHA256':AFTER,'projectInputs':6310,'changedProjectPaths':[RELATIVE],'runtimeAssetChanges':[],'builderUnchanged':True,'metaUnchanged':True,'actualNativeExecution':False}

if __name__=='__main__':
    try:print(json.dumps(prepare()))
    except Exception as failure:
        code=str(failure);print(json.dumps({'status':'BLOCKED_EDITOR_FIXTURE_EPOCH06','code':code if re.fullmatch('[A-Za-z0-9_]{1,120}',code) else type(failure).__name__}));raise SystemExit(1)
