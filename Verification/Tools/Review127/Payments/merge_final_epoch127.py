"""Merge only Root-frozen seven-file UI delta and reviewed native fixture/gate.

Writes private Pay01 Epoch04; does not run Unity, sign, inspect secrets or touch a
device/provider/backend. All earlier preparation/run-plan bytes are retained.
"""
from __future__ import annotations
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('final_preparation_epoch127',HERE/'prepare_payment_diagnostics127.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
PARENT=Path('E:/.verification-cache/HOTR127/Pay01')
PREVIOUS='6bdb804b14e87ccf72550dd599862ecd02be6ca56b9f2764dbc20482ee7abd0f'
PREVIOUS_PLAN='3c528700dd8f621d7827f40842fe2be4155f7a963111e8a383fba81f1b35fd7c'
FIXTURE='683fc91985b6b66f61f2c8aeb57d1c439ab4ab70c496ad3c30992d82f5e38787'
FIXTURE_RELATIVE='Assets/Review127Diagnostics/Editor/SigninLayout127Verification.cs'
BUILDER_RELATIVE='Assets/Review127Diagnostics/Editor/PaymentDiagnosticBuild127.cs'

def merge():
    original=PARENT/'Preparation127_Epoch03.json';old_plan=PARENT/'RunPlan127_Epoch03.json';new=PARENT/'Preparation127_Epoch04.json';new_plan=PARENT/'RunPlan127_Epoch04.json'
    prep.need(prep.sha(original)==PREVIOUS and prep.sha(old_plan)==PREVIOUS_PLAN,'ExactPreviousPrivateEpoch03Required127')
    prep.need(not new.exists() and not new_plan.exists(),'FreshFinalPrivateEpoch04Required127')
    value=json.loads(original.read_text('utf-8'));plan=json.loads(old_plan.read_text('utf-8'));project=PARENT/'Game'
    delta_path=prep.ROOT/'Verification/Evidence/Review127/Signin/SourceDelta02_127.json';delta=json.loads(delta_path.read_text('utf-8'));rows=delta['changed'];prep.need(len(rows)==7,'ExactRootSevenPathDeltaRequired127')
    expected_paths={'Unity/Assets/HeartOfTheRain/App/AccountDesign/AccountModal.cs','Unity/Assets/HeartOfTheRain/App/ServerAccount/Runtime/VkSigninUI102.cs','Unity/Assets/HeartOfTheRain/App/ServerAccount/Runtime/ProviderAccountUI89.cs','Unity/Assets/HeartOfTheRain/App/ServerAccount/Runtime/ServerAccountText83.cs','Unity/Assets/HeartOfTheRain/Verification/Editor/AccountR6Review.cs','Unity/Assets/HeartOfTheRain/Verification/Editor/ProviderIdentity89Verification.cs','Unity/Assets/HeartOfTheRain/Verification/Editor/VkSignin102Verification.cs'}
    prep.need({row['path'] for row in rows}==expected_paths,'ExactRootUiAndAssertionPathsRequired127')
    before=prep.inventory(project);prep.need(before==value['inputs'],'PreviousPrivateEpoch03Drifted127');changes={}
    for row in rows:
        relative=row['path'][6:];source=prep.ROOT/row['path'];meta=relative+'.meta'
        prep.need(prep.sha(source)==row['afterSHA256'] and before[relative]==row['beforeSHA256'],'RootFrozenUiDeltaSourceMismatch127')
        prep.need(prep.sha(prep.ROOT/'Unity'/meta)==row['metaSHA256']==before[meta],'OriginalUiMetaBytesRequired127')
    fixture=prep.ROOT/'Verification/Tools/Review127/Signin/SigninLayout127Verification.cs';prep.need(prep.sha(fixture)==FIXTURE,'ReviewedFinalNativeFixtureRequired127')
    for row in rows:
        relative=row['path'][6:];shutil.copyfile(prep.ROOT/row['path'],project/relative);changes[relative]={'before':before[relative],'after':row['afterSHA256']};before[relative]=row['afterSHA256'];value['mainInputs'][relative]=row['afterSHA256'];value['sourceDelta'][relative]={'before':value['sourceInputs'][relative],'after':row['afterSHA256']}
    prep.put(project,FIXTURE_RELATIVE,fixture.read_bytes())
    before[FIXTURE_RELATIVE]=prep.sha(project/FIXTURE_RELATIVE);before[FIXTURE_RELATIVE+'.meta']=prep.sha(project/(FIXTURE_RELATIVE+'.meta'))
    changes[FIXTURE_RELATIVE]={'before':None,'after':before[FIXTURE_RELATIVE]};changes[FIXTURE_RELATIVE+'.meta']={'before':None,'after':before[FIXTURE_RELATIVE+'.meta']}
    old_builder=before[BUILDER_RELATIVE];(project/BUILDER_RELATIVE).write_bytes(prep.builder(require_layout=True));before[BUILDER_RELATIVE]=prep.sha(project/BUILDER_RELATIVE);changes[BUILDER_RELATIVE]={'before':old_builder,'after':before[BUILDER_RELATIVE]}
    for relative,change in changes.items():prep.need(prep.sha(project/relative)==change['after'],'FinalMergedPrivateSourceMismatch127')
    pins={p:h for p,h in before.items() if p.startswith('Assets/') and not p.endswith('.meta') and p!='Assets/Plugins/Android/AndroidManifest.xml'}
    guid={}
    for relative in before:
        if not relative.startswith('Assets/') or not relative.endswith('.meta'):continue
        matches=re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$',(project/relative).read_bytes());prep.need(len(matches)==1,'ExactlyOneFinalMetaGuidRequired127');guid[relative]=matches[0].decode().lower()
    prep.need(len(set(guid.values()))==len(guid),'UniqueFinalPrivateGuidSetRequired127')
    value.update(inputs=before,paths=list(pins),sha256=list(pins.values()),metaPaths=list(guid),metaGuids=list(guid.values()),builderSHA256=before[BUILDER_RELATIVE],sourceEpoch=4,epochPreparedUtc=datetime.now(timezone.utc).isoformat(),previousPreparationSHA256=PREVIOUS,epochToolSHA256=prep.sha(__file__),epochBuilderGeneratorSHA256=prep.sha(HERE/'prepare_payment_diagnostics127.py'),rootUiSourceDeltaSHA256=prep.sha(delta_path),nativeFixtureSHA256=FIXTURE,nativeRunnerSHA256=prep.sha(HERE/'run_payment_diagnostics127.py'),apkCheckerSHA256=prep.sha(HERE/'check_payment_apk127.py'),epochDelta=changes,epochScope='Only Root-authorized seven-file modal size/copy/assertion delta plus isolated Editor native layout fixture and source-bound builder gate. No auth/business/provider/backend or SDK change.')
    value['newPaths']=sorted(set(value['newPaths'])|{FIXTURE_RELATIVE,FIXTURE_RELATIVE+'.meta'});prep.write(new,value)
    plan.update(sourceEpoch=4,preparationSHA256=prep.sha(new),previousRunPlanSHA256=PREVIOUS_PLAN,epochScope=value['epochScope'],entryLayout='HeartOfTheRain.Verification127.SigninLayout127Verification.Run',nativeRunnerSHA256=value['nativeRunnerSHA256'],apkCheckerSHA256=value['apkCheckerSHA256'])
    plan['environmentReferences'].update(HOTR_PAYMENTDIAG127_RECEIPT=str(new),HOTR_PAYMENTDIAG127_APK=str(project/'Builds/HeartOfTheRain_Diagnostic127_<run-tag>.apk'),HOTR_SIGNIN_LAYOUT127_OUTPUT='<fresh layout output>',HOTR_SIGNIN_LAYOUT127_REPORT='<accepted source-bound Layout/Native.json>')
    plan['nativeRequiredChecks']=['Root --layout first: actual180case/540layout native UGUI/font/mask/raycast/camera checks with passive managed/VK fixtures','Default packaging: actual C# diagnostic serializer/privacy checks plus exact accepted layout source bindings','Root --build only: existing developer release signing identity, child-environment-only password','check_payment_apk127.py: actual certificate/version127/SDK/privacy/resources/DEX/16KiB/dependency locks and diagnostic IL2CPP type metadata']
    runner=str(HERE/'run_payment_diagnostics127.py');receipt=str(new)
    plan['rootCommands']=[['Backend/.venv/Scripts/python.exe','-B',runner,'--receipt',receipt,'--tag','Layout01','--layout'],['Backend/.venv/Scripts/python.exe','-B',runner,'--receipt',receipt,'--tag','Packaging01','--layout-report','<Layout01/Native.json>','--layout-report-sha256','<actual native report SHA256>'],['Backend/.venv/Scripts/python.exe','-B',runner,'--receipt',receipt,'--tag','Build01','--build','--layout-report','<Layout01/Native.json>','--layout-report-sha256','<actual native report SHA256>'],['Backend/.venv/Scripts/python.exe','-B',str(HERE/'check_payment_apk127.py'),'--build','<Build01/Native.json>']]
    prep.write(new_plan,plan);prep.need(prep.sha(original)==PREVIOUS and prep.sha(old_plan)==PREVIOUS_PLAN,'PreviousEpoch03MustRemainUnchanged127')
    return {'status':'PREPARED_PAYMENT_DIAGNOSTIC127_EPOCH04','project':str(project),'preparationSHA256':prep.sha(new),'runPlanSHA256':prep.sha(new_plan),'builderSHA256':value['builderSHA256'],'nativeRunnerSHA256':value['nativeRunnerSHA256'],'apkCheckerSHA256':value['apkCheckerSHA256'],'fixtureSHA256':FIXTURE,'inputs':len(before),'guids':len(guid),'changedPaths':len(changes),'actualBuild':False,'sdkAvailabilityInvoked':False}

if __name__=='__main__':
    try:print(json.dumps(merge()))
    except Exception as failure:
        code=str(failure);print(json.dumps({'status':'BLOCKED_PAYMENT_DIAGNOSTIC_EPOCH04','code':code if re.fullmatch('[A-Za-z0-9_]{1,120}',code) else type(failure).__name__}));raise SystemExit(1)
