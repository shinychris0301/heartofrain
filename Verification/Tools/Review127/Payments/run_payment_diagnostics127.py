"""Root-executable native diagnostic127 runner. Authoring this file runs nothing.

Run --layout first, then default packaging with --layout-report, then --build.
Only the explicitly invoked --build path retrieves the existing DPAPI password;
it goes to the owned Editor child's environment, never argv or public output.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
PRIVATE=Path('E:/.verification-cache/HOTR127')
EDITOR=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe')
ANDROID=EDITOR.parent/'Data/PlaybackEngines/AndroidPlayer'
HUB=Path('C:/Program Files/Unity Hub/resources/unity.exe')
CUSTODY=Path(os.environ.get('LOCALAPPDATA',''))/'HeartOfTheRain/ReleaseSigning/RuStore'
GRADLE=Path('E:/G127Pay01')
PUBLIC=ROOT/'Verification/Evidence/Review127/Payments/Native'
EXPECTED_SIGNER='7257537a5b329cc5b018d93299d748404432c1b49f1b2388444ab843a4ba170d'
LAYOUT_STATUS='PASS_NATIVE_SIGNIN_LAYOUT127'
LAYOUT_SOURCE='Assets/Review127Diagnostics/Editor/SigninLayout127Verification.cs'

def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):value.update(block)
    return value.hexdigest()

def need(value,code):
    if not value:raise RuntimeError(code)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as output:json.dump(value,output,indent=2);output.write('\n')

def inventory(project):
    return {p.relative_to(project).as_posix():sha(p) for name in ('Assets','Packages','ProjectSettings') for p in sorted((project/name).rglob('*')) if p.is_file()}

def foreign_editors(project):
    script="@(Get-CimInstance Win32_Process -Filter \"Name='Unity.exe'\" | Select-Object ProcessId,ExecutablePath,CommandLine) | ConvertTo-Json -Compress"
    result=subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',script],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
    need(result.returncode==0,'EditorInventoryRequired127');data=json.loads(result.stdout.decode('utf-8-sig') or '[]');data=[] if data is None else [data] if isinstance(data,dict) else data
    observed=[]
    for value in data:
        executable=Path(value.get('ExecutablePath') or '').resolve()
        if executable==HUB.resolve():observed.append({'pid':value['ProcessId'],'kind':'ExactKnownUnityHubResourceHelper','touched':False});continue
        command=value.get('CommandLine') or '';match=re.search(r'(?:^|\s)-projectPath\s+(?:"([^"]+)"|([^\s]+))',command,re.I)
        need(match is not None,'UnknownEditorProjectBlocksNative127');other=Path(match.group(1) or match.group(2)).resolve()
        need(other!=project.resolve(),'SameProjectEditorBlocksNative127')
        observed.append({'pid':value['ProcessId'],'kind':'ForeignEditor','projectSHA256':hashlib.sha256(str(other).lower().encode()).hexdigest(),'touched':False})
    return observed

def asset_path(project,relative):
    need(type(relative) is str and relative.startswith('Assets/') and '\\' not in relative and not any(ord(v)<32 for v in relative) and not any(v in ('','..') or ':' in v for v in relative.split('/')),'ContainedAssetPathRequired127')
    path=(project/relative).resolve();need(path.is_relative_to(project.resolve()) and path.is_file(),'RealContainedAssetFileRequired127');return path

def accepted_layout(path,expected_sha,project):
    need(path is not None and re.fullmatch('[0-9a-f]{64}',expected_sha or ''),'SourceBoundLayoutReportRequired127')
    path=path.resolve();need(path.is_relative_to(PUBLIC.resolve()) and path.name=='Native.json' and sha(path)==expected_sha,'ExactOwnedLayoutReportRequired127')
    need(path.stat().st_size<=2097152,'BoundedNativeLayoutReportRequired127');value=json.loads(path.read_text('utf-8'))
    need(value.get('status')==LAYOUT_STATUS and value.get('actualNativeLayout') is True and value.get('actualProvider') is False and value.get('deviceTouched') is False and value.get('errors')==[],'ActualPassingNativeLayoutReportRequired127')
    need(value.get('unity')=='6000.3.27f1' and type(value.get('cases')) is int and value['cases']==180 and type(value.get('layouts')) is int and value['layouts']==540 and type(value.get('visibleBodyRaycasts')) is int and value['visibleBodyRaycasts']>0 and type(value.get('bodyRaycastRejects')) is int and value['bodyRaycastRejects']>0,'CompleteNativeLayoutMatrixRequired127')
    pins=value.get('sourceBindings');need(type(pins) is list and 5<=len(pins)<=32,'NativeLayoutSourcePinsRequired127')
    seen=set()
    for pin in pins:
        relative=pin.get('path','');digest=pin.get('sha256','')
        source=asset_path(project,relative);need(relative.casefold() not in seen and re.fullmatch('[0-9a-f]{64}',digest),'ContainedUniqueLayoutSourcePinRequired127')
        seen.add(relative.casefold());need(sha(source)==digest,'NativeLayoutSourceChanged127')
    need(LAYOUT_SOURCE.casefold() in seen and 'Assets/HeartOfTheRain/App/AccountDesign/AccountModal.cs'.casefold() in seen,'ActualModalAndNativeVerifierPinsRequired127')
    return expected_sha

def scrub_generated(project,raw,password):
    if not password:return {'complete':True,'files':0}
    secret=password.encode('ascii');changed=0
    extensions={'.gradle','.properties','.json','.txt','.log','.yaml','.yml','.xml','.bat','.cmd','.rsp','.cs','.java','.kt'}
    for base in (project/'Library',project/'Temp',GRADLE,raw):
        if not base.exists():continue
        for path in base.rglob('*'):
            if not path.is_file() or path.suffix.lower() not in extensions:continue
            data=path.read_bytes()
            if secret in data:path.write_bytes(data.replace(secret,b'<private-signing-password-removed>'));changed+=1
    return {'complete':True,'files':changed}

def run(receipt_path,tag,build,layout,timeout,layout_report=None,layout_sha=None):
    need(os.name=='nt' and re.fullmatch('[A-Za-z0-9_]{1,30}',tag or '') and 60<=timeout<=3600,'BoundedWindowsNativeInvocationRequired127')
    need(not (build and layout),'OneNativeOperationRequired127');need(EDITOR.is_file(),'ApprovedIsolatedEditorRequired127')
    receipt_path=receipt_path.resolve();receipt=json.loads(receipt_path.read_text('utf-8'));project=Path(receipt['project']).resolve()
    need(project.is_relative_to(PRIVATE.resolve()) and receipt_path.parent==project.parent and receipt['status']=='PREPARED_PAYMENT_DIAGNOSTIC127' and receipt['versionCode']==127 and receipt['packageName']=='com.heartoftherain.game','OwnedPreparedDiagnosticProjectRequired127')
    need(receipt['expectedSignerSHA256']==EXPECTED_SIGNER,'OriginalReleaseSignerIntentRequired127')
    need(receipt.get('nativeRunnerSHA256')==sha(__file__),'PreparedNativeRunnerSourceChanged127')
    for relative,digest in zip(receipt['paths'],receipt['sha256']):
        need(sha(asset_path(project,relative))==digest,'PreparedNativeSourceChanged127')
    need(sha(project/'Assets/Review127Diagnostics/Runtime/PaymentDiagnostics127.cs')==receipt['harnessSHA256'] and sha(project/'Assets/Review127Diagnostics/Editor/PaymentDiagnosticBuild127.cs')==receipt['builderSHA256'],'ActualPreparedDiagnosticSourcesRequired127')
    need((project/LAYOUT_SOURCE).is_file(),'NativeLayoutVerifierCopyRequired127')
    layout_binding=None if layout else accepted_layout(layout_report,layout_sha,project)
    foreign=foreign_editors(project);output=PUBLIC/tag;need(not output.exists(),'PreservePriorNativeAttempts127');output.mkdir(parents=True)
    signing=load('payment_signing_directory127',ROOT/'Release/Signing/manage_release_signing.py')
    raw=project.parent/'Runs'/tag;need(not raw.exists(),'FreshPrivateNativeCaptureRequired127');signing.private_directory(raw)
    cache_binding={'version':1,'project':str(project),'nonce':receipt['nonce']};marker=GRADLE/'.hotr-payment-diag127-cache.json'
    if GRADLE.exists():need(marker.is_file() and json.loads(marker.read_text('utf-8'))==cache_binding,'ExactOwnedPrivateGradleCacheRequired127')
    else:
        signing.private_directory(GRADLE);write(marker,cache_binding)
        previous=Path('E:/G126A/caches/modules-2/files-2.1')
        if previous.is_dir():shutil.copytree(previous,GRADLE/'caches/modules-2/files-2.1',ignore=shutil.ignore_patterns('*.lock','*.lck','gc.properties'))
    env={key:value for key,value in os.environ.items() if not key.upper().startswith('HOTR_') and not re.search('KEYSTORE|KEYALIAS|STOREPASS|KEYPASS',key,re.I)}
    need(not any(env.get(key) for key in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')),'UnreviewedJavaOptionsRejected127')
    release=receipt_path.parent/'Release127.json';need(sha(release)==receipt['releaseSHA256'],'PreparedPublicReleaseMetadataChanged127')
    env.update(HOTR_PAYMENTDIAG127_RECEIPT=str(receipt_path),HOTR_PAYMENTDIAG127_OUT=str(output),HOTR_SDK125_PACKAGING_PROJECT=str(project),HOTR_RUSTORE_RELEASE_CONFIG=str(release),GRADLE_USER_HOME=str(GRADLE))
    if layout:env['HOTR_SIGNIN_LAYOUT127_OUTPUT']=str(output)
    else:env['HOTR_SIGNIN_LAYOUT127_REPORT']=str(layout_report.resolve())
    apk=project/'Builds'/('HeartOfTheRain_Diagnostic127_'+tag+'.apk');password=None
    if build:
        need(not apk.exists(),'FreshPrivateDiagnosticApkRequired127')
        # This is the only credential retrieval branch. Root invokes --build;
        # no password is read during import, preparation, layout or packaging.
        password=signing.local_password(CUSTODY)
        certificate=signing.verify(CUSTODY,ANDROID/'OpenJDK',password)
        need(certificate['sha256']==EXPECTED_SIGNER,'ActualPrivateSignerMustMatchInstalled126Certificate127')
        env.update(HOTR_RELEASE_SIGNING_PASSWORD=password,HOTR_RELEASE_KEYSTORE=str(CUSTODY/signing.KEYSTORE),HOTR_PAYMENTDIAG127_APK=str(apk))
    operation='layout' if layout else 'build' if build else 'packaging'
    entry='HeartOfTheRain.Verification127.SigninLayout127Verification.Run' if layout else 'HeartOfTheRain.Verification.PaymentDiagnosticBuild127.'+('BuildSandbox' if build else 'RunPackaging')
    expected=LAYOUT_STATUS if layout else 'PASS_PAYMENT_DIAGNOSTIC127_ANDROID_BUILD' if build else 'PASS_PAYMENT_DIAGNOSTIC127_PACKAGING'
    command=[str(EDITOR),'-batchmode','-projectPath',str(project),'-buildTarget','Android','-executeMethod',entry,'-logFile',str(raw/'Unity.log')]
    # Real GameView frames/masks/raycast tests require graphics; no -nographics.
    before=inventory(ROOT/'Unity');write(output/'MainBefore.json',before)
    sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'));from run_ads85_native import OwnedJob
    record={'version':1,'status':'RUNNING_PAYMENT_DIAGNOSTIC127','operation':operation,'entry':entry,'startedUtc':datetime.now(timezone.utc).isoformat(),'project':str(project),'preparationSHA256':sha(receipt_path),'runnerSHA256':sha(__file__),'editorSHA256':sha(EDITOR),'layoutReportSHA256':layout_binding,'actualBuildRequested':build,'releaseSigningRequested':build,'providerActionsRequested':False,'deviceTouched':False,'foreignEditorsObservedOnly':foreign}
    process=job=None;started=time.monotonic();scrubbed=False
    try:
        job=OwnedJob()
        with (raw/'Console.log').open('xb') as capture:
            process=subprocess.Popen(command,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=capture,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);job.assign(process.pid);record['pid']=process.pid
            record['exitCode']=process.wait(timeout=timeout)
    except Exception as failure:record['errorType']=type(failure).__name__
    finally:
        if job:job.close()
        if process is not None and process.poll() is None:
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        env.pop('HOTR_RELEASE_SIGNING_PASSWORD',None)
        try:record['privateSigningDiagnosticsScrub']=scrub_generated(project,raw,password);scrubbed=True
        except Exception as failure:record['scrubFailureType']=type(failure).__name__
        # No public raw-log copy occurs until scrub has completed successfully.
        if scrubbed:
            for name in ('Unity.log','Console.log'):
                path=raw/name
                if path.is_file():shutil.copyfile(path,output/name)
        password=None
        after=inventory(ROOT/'Unity');record['mainInputsUnchanged']=before==after;record['mainPathsChangedDuringInvocation']=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
        record['processStopped']=process is None or process.poll() is not None;record['elapsedSeconds']=round(time.monotonic()-started,3);record['finishedUtc']=datetime.now(timezone.utc).isoformat()
        native_path=output/'Native.json';native=json.loads(native_path.read_text('utf-8')) if native_path.exists() else {};record['nativeStatus']=native.get('status','MISSING');record['nativeSHA256']=sha(native_path) if native_path.exists() else None
        valid=record.get('exitCode')==0 and record['processStopped'] and record['mainInputsUnchanged'] and scrubbed and native.get('status')==expected
        if layout:valid=valid and native.get('actualNativeLayout') is True and native.get('actualProvider') is False and native.get('deviceTouched') is False
        else:valid=valid and native.get('sourcePinsPreserved') is True and native.get('metaGuidsPreserved') is True
        record['status']='PASS_PAYMENT_DIAGNOSTIC127_NATIVE' if valid else 'FAIL_PAYMENT_DIAGNOSTIC127_NATIVE';write(output/'Process.json',record)
    need(record['status']=='PASS_PAYMENT_DIAGNOSTIC127_NATIVE','NativeDiagnosticInvocationFailed127')
    return {'status':record['status'],'operation':operation,'output':str(output.relative_to(ROOT)),'nativeStatus':record['nativeStatus'],'nativeSHA256':record['nativeSHA256'],'apk':str(apk) if build else None}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--receipt',type=Path,required=True);parser.add_argument('--tag',required=True);group=parser.add_mutually_exclusive_group();group.add_argument('--build',action='store_true');group.add_argument('--layout',action='store_true');parser.add_argument('--timeout',type=int,default=2400);parser.add_argument('--layout-report',type=Path);parser.add_argument('--layout-report-sha256');args=parser.parse_args()
    return run(args.receipt,args.tag,args.build,args.layout,args.timeout,args.layout_report,args.layout_report_sha256)

if __name__=='__main__':
    try:print(json.dumps(main()))
    except Exception as failure:
        code=str(failure);print(json.dumps({'status':'BLOCKED_NATIVE_DIAGNOSTIC127','code':code if re.fullmatch('[A-Za-z0-9_]{1,120}',code) else type(failure).__name__}));raise SystemExit(1)
