"""Root-only full-game LTS copy/config/build, gated by an actual minimal smoke PASS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

import smoke95

ROOT,EVIDENCE,PRIVATE=smoke95.ROOT,smoke95.EVIDENCE,smoke95.PRIVATE
PROJECT=PRIVATE/'Game'
TEMPLATE=Path(__file__).with_name('Templates')/'Unity6LTSGame95.cs'
RELATIVE_FIXTURE='Assets/HeartOfTheRain/Verification/Editor/Unity6LTSGame95.cs'
PACKAGE='com.heartoftherain.unity6lts95'
COMPANY='HeartRainUnity6LTSReview95'
ENTRY='HeartOfTheRain.Verification.Unity6LTSGame95.'


def need(value,code):smoke95.need(value,code)
def sha(path):return smoke95.sha(path)
def read(path):return smoke95.read(path)
def binding(path):return smoke95.binding(path)


def check_bound(item):
    path=Path(item['path']).resolve()
    need(path.is_relative_to(ROOT) and binding(path)==item,'LTS95BoundArtifactChanged')
    return path


def validate_smoke_receipt(path):
    path=Path(path).resolve()
    need(path.is_relative_to(EVIDENCE/'SmokeRuns') and path.name=='Invocation.json','LTS95ActualContainedSmokeReceiptRequired')
    value=read(path)
    need(value.get('status')=='PASS_ACTUAL_LTS95_TOOLCHAIN_SMOKE_WITH_NO_GAME_ACCEPTANCE' and value.get('exitCode')==0
         and value.get('actualEngineVersionFromLog')==smoke95.VERSION and value.get('mainInputsUnchanged') is True
         and value.get('candidate66InputsUnchanged') is True and value.get('externalToolPrefFingerprintsUnchanged') is True
         and value.get('embeddedToolMarkersUnchanged') is True and value.get('unityPidsAfter')==[]
         and value.get('smokeAPKNeverInstalled') is True,'LTS95ActualSuccessfulMinimalSmokeRequired')
    native=read(check_bound(value['nativeReport']));log=check_bound(value['unityLog']).read_text('utf-8-sig',errors='replace')
    need(native.get('status')=='PASS_ACTUAL_LTS95_EMPTY_ANDROID_BUILD' and not native.get('error') and native.get('unity')==smoke95.VERSION
         and native.get('package')=='com.heartoftherain.toolchain95' and native.get('development') is True
         and native.get('minSdk')==26 and native.get('targetSdk')==36 and native.get('splash') is False and native.get('unityLogo') is False
         and re.search(r'Initialize engine version:\s*'+re.escape(smoke95.VERSION),log),'LTS95ActualSmokeNativeEngineAndSettingsRequired')
    apk=(ROOT/value['apkPath']).resolve()
    need(apk.is_relative_to(PRIVATE/'SmokeOutputs') and smoke95.validate_apk(apk)['sha256']==value['apk']['sha256']==native.get('apkSHA256')
         and apk.stat().st_size==value['apk']['bytes']==native.get('apkBytes'),'LTS95ActualSmokeAPKBindingRequired')
    check_bound(value['badging'])
    return value


def isolated_settings(raw):
    # Identity isolation before InitializeOnLoad callbacks; never edit splash/license flags in YAML.
    changed,count=re.subn(rb'(?m)^(  companyName: )[^\r\n]*(?=\r?$)',lambda found:found[1]+COMPANY.encode('ascii'),raw)
    need(count==1,'LTS95ExactlyOneCompanyIdentityRequired')
    changed,count=re.subn(rb'(?m)^(  applicationIdentifier:\r?\n    Android: )[^\r\n]*(?=\r?$)',lambda found:found[1]+PACKAGE.encode('ascii'),changed)
    need(count==1,'LTS95ExactlyOneAndroidIdentityRequired')
    return changed


def delta(before,after):
    return [{'path':path,'kind':'added' if path not in before else 'deleted' if path not in after else 'changed',
             'before':before.get(path),'after':after.get(path)} for path in sorted(set(before)|set(after)) if before.get(path)!=after.get(path)]


def protected_assets(main,game,guards):
    original={path.removeprefix('Unity/'):bound for path,bound in main['files'].items()}
    guid_count=0
    for relative,bound in original.items():
        if not relative.startswith('Assets/'):continue
        path=PROJECT/relative
        need(relative in game['files'] and path.is_file(),'LTS95OriginalAssetMissing')
        if relative.endswith('.meta'):
            need(guards.one_guid((ROOT/'Unity'/relative).read_bytes())==guards.one_guid(path.read_bytes()),'LTS95OriginalAssetGUIDChanged')
            guid_count+=1
        else:
            need(game['files'][relative]==bound,'LTS95OriginalArtLevelRuntimeOrTestSourceChanged')
    additions={relative for relative in game['files'] if relative.startswith('Assets/') and relative not in original}
    need(additions=={RELATIVE_FIXTURE,RELATIVE_FIXTURE+'.meta'},'LTS95UnexpectedAddedGameAsset')
    need(sha(PROJECT/RELATIVE_FIXTURE)==sha(TEMPLATE),'LTS95PreparedFixtureChanged')
    return {'allOriginalAssetBytesExceptMetadataUnchanged':True,'allOriginalGUIDsPreserved':True,'originalMetadataCount':guid_count,
            'originalCSharpUnchangedIncludingGetInstanceIDAndTestPins':True,'newEditorFixtureOnly':True}


def prepare(output,smoke_receipt):
    api,candidate,process,_,guards=smoke95.readers()
    need(not process.unity_pids(),'LTS95IdleEditorBeforeCopyRequired')
    validate_smoke_receipt(smoke_receipt)
    for path in (PROJECT,output,TEMPLATE):guards.reject_links(path)
    output=smoke95.contained_output(output,'GamePreparation');need(not PROJECT.exists(),'LTS95ExistingGameCopyPreserved')
    main,current66=smoke95.protected_sources(api,candidate);tools=smoke95.tool_markers(smoke95.EDITOR)
    output.mkdir(parents=True,exist_ok=False)
    api.write(output/'MainSources_before.json',main);api.write(output/'Candidate66Sources_before.json',current66)
    receipt={'schemaVersion':1,'status':'RUNNING_EXACT_MAIN_COPY_LTS95','startedUtc':api.utc(),'runnerSHA256':sha(Path(__file__)),
             'smokeInvocation':binding(smoke_receipt),'baselineCommit':'196f606d','mainManifestSHA256':sha(smoke95.BASELINE),
             'version':smoke95.VERSION,'project':PROJECT.relative_to(ROOT).as_posix(),'tools':tools,'templateSHA256':sha(TEMPLATE),
             'scope':'Fresh ordinary copies of exact5407 protected Unity inputs after actual stock minimal Android smoke PASS. Only project version, pre-import company/Android identity and one new Editor fixture are prepared. Original APIs/GetInstanceID/icons/test assertions, artwork/GUIDs/masks/model/backend/trusted2022 worker remain untouched. No engine execution, game acceptance, SDK update or device installation.'}
    api.write(output/'Authorization.json',receipt)
    try:
        PROJECT.mkdir(parents=True,exist_ok=False)
        for relative,expected in main['files'].items():
            source=ROOT/relative;guards.reject_links(source);target=PROJECT/Path(relative).relative_to('Unity')
            need(target.resolve().is_relative_to(PROJECT.resolve()) and not target.exists(),'LTS95FreshContainedOrdinaryCopyRequired')
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            need(sha(target)==expected['sha256'] and target.stat().st_size==expected['bytes'] and target.stat().st_nlink==1,'LTS95ExactOrdinaryCopyMismatch')
        copied=guards.inventory(PROJECT);base={key.removeprefix('Unity/'):value for key,value in main['files'].items()}
        need(copied['files']==base and copied['inputCount']==5407,'LTS95Exact5407CopyProofRequired')
        api.write(output/'GameSources_exact5407Copy.json',copied)
        version=PROJECT/'ProjectSettings/ProjectVersion.txt';settings=PROJECT/'ProjectSettings/ProjectSettings.asset'
        version.write_bytes(('m_EditorVersion: '+smoke95.VERSION+'\n').encode('utf-8'));settings.write_bytes(isolated_settings(settings.read_bytes()))
        fixture=PROJECT/RELATIVE_FIXTURE;need(not fixture.exists() and not fixture.with_suffix('.cs.meta').exists(),'LTS95FixtureCollision')
        fixture.write_bytes(TEMPLATE.read_bytes());guid=uuid.uuid4().hex
        fixture.with_suffix('.cs.meta').write_text('fileFormatVersion: 2\nguid: '+guid+'\n',encoding='utf-8')
        prepared=guards.inventory(PROJECT);preserved=protected_assets(main,prepared,guards)
        changes=delta(copied['files'],prepared['files'])
        need({row['path'] for row in changes}=={'ProjectSettings/ProjectVersion.txt','ProjectSettings/ProjectSettings.asset',RELATIVE_FIXTURE,RELATIVE_FIXTURE+'.meta'},'LTS95OnlyFourPreparationDeltasAllowed')
        api.write(output/'GameSources_prepared.json',prepared);api.write(output/'PreparationDeltas.json',changes)
        need((main,current66)==smoke95.protected_sources(api,candidate),'LTS95ProtectedProjectsChangedDuringCopy')
        api.write(output/'MainSources_after.json',main);api.write(output/'Candidate66Sources_after.json',current66)
        manifest=read(PROJECT/'Packages/manifest.json')
        receipt.update(status='PASS_EXACT_MAIN_COPY_LTS95_AFTER_ACTUAL_SMOKE',mainInputCount=5407,mainInputsUnchanged=True,candidate66InputsUnchanged=True,
                       newFixtureGuid=guid,preparedManifest=binding(output/'GameSources_prepared.json'),assetProtection=preserved,
                       preparedDeltaPaths=[row['path'] for row in changes],packagesCopiedUnchanged=True,
                       initialUguiVersion=manifest['dependencies'].get('com.unity.ugui'),initialRecorderVersion=manifest['dependencies'].get('com.unity.recorder'),
                       packagePlan='Keep copied ugui1.0.0/Recorder4.0.3 and lock bytes initially. Record actual native package-resolution/import changes; adapt only a demonstrated compatibility failure, with a separate reviewed diff. No6000.6 ports/packages or automatic SDK upgrades are carried over.')
    except Exception as error:
        receipt.update(status='FAIL_EXACT_MAIN_COPY_LTS95',errorType=type(error).__name__,error=str(error));raise
    finally:
        receipt['finishedUtc']=api.utc();api.write(output/'Preparation.json',receipt)
        print(json.dumps({'status':receipt['status'],'preparation':(output/'Preparation.json').relative_to(ROOT).as_posix()}),flush=True)


def validate_native_settings(value):
    need(value.get('packageName')==PACKAGE and value.get('companyName')==COMPANY and value.get('productName')=='Сердце дождя'
         and value.get('backend')=='IL2CPP' and value.get('architectures')=='ARM64' and value.get('applicationEntry')=='Activity'
         and value.get('minApi')==26 and value.get('targetApi')==36 and value.get('showSplashScreen') is False
         and value.get('showUnityLogo') is False and value.get('portraitOnly') is True and value.get('orientation')=='Portrait'
         and value.get('bundle') is False and value.get('customKeystore') is False and value.get('sdkFreeDefines') is True,'LTS95ExactNativeGameSettingsRequired')


def validate_native_identity_paths(native,apk):
    need(isinstance(native.get('project'),str) and native['project'] and Path(native['project']).resolve()==PROJECT.resolve(),
         'LTS95NativeReportProjectMustEqualExactGameRoot')
    need(isinstance(native.get('apk'),str) and native['apk'] and Path(native['apk']).resolve()==Path(apk).resolve(),
         'LTS95NativeReportAPKMustEqualOuterBoundAPK')


def validate_build_receipt(path):
    """Read-only shared guard for a later explicit LD/device helper; never installs anything."""
    path=Path(path).resolve();need(path.is_relative_to(EVIDENCE/'GameRuns') and path.name=='Invocation.json','LTS95ActualGameBuildReceiptRequired')
    value=read(path)
    need(value.get('status')=='PASS_ACTUAL_LTS95_GAME_BUILDDEVELOPMENT' and value.get('operation')=='BuildDevelopment'
         and value.get('exitCode')==0 and value.get('actualEngineVersionFromLog')==smoke95.VERSION
         and value.get('mainInputsUnchanged') is True and value.get('candidate66InputsUnchanged') is True
         and value.get('gameInputsStable') is True and value.get('unityPidsAfter')==[] and not value.get('timedOut')
         and value.get('runnerSHA256')==sha(Path(__file__)),'LTS95ActualSuccessfulFullGameBuildRequired')
    native_path=check_bound(value['nativeReport']);log_path=check_bound(value['unityLog'])
    need(native_path==path.parent/'BuildDevelopment.json' and log_path==path.parent/'Unity.log','LTS95ExactSiblingBuildReportsRequired')
    native=read(native_path)
    need(re.search(r'Initialize engine version:\s*'+re.escape(smoke95.VERSION),log_path.read_text('utf-8-sig',errors='replace')),'LTS95ActualBuildLogEngineRequired')
    need(native.get('status')=='PASS_NATIVE_LTS95_GAME_BUILDDEVELOPMENT' and native.get('operation')=='BuildDevelopment'
         and native.get('unity')==smoke95.VERSION and not native.get('error') and native.get('exitCode')==0
         and native.get('development') is True and native.get('buildResult')=='Succeeded' and native.get('errors')==0
         and native.get('buildPackageName')==PACKAGE and native.get('checks') and all(row.get('passed') is True for row in native['checks']),'LTS95ActualBoundNativeBuildRequired')
    validate_native_settings(native['after'])
    apk=check_bound(value['apk']);need(apk.is_relative_to(PROJECT/'Builds') and value['apk']['sha256']==native['apkSHA256']
         and value['apk']['bytes']==native['bytes'],'LTS95ActualFullGameAPKBindingRequired')
    validate_native_identity_paths(native,apk)
    for prefix in ('Main','Candidate66','Game'):
        for suffix in ('Before','After'):
            manifest=path.parent/(prefix+'Sources_'+suffix.lower()+'.json')
            need(sha(manifest)==value.get(prefix[0].lower()+prefix[1:]+'Sources'+suffix+'SHA256'),'LTS95StoredSourceManifestSHAChanged')
        need(read(path.parent/(prefix+'Sources_before.json'))==read(path.parent/(prefix+'Sources_after.json')),'LTS95BuildSourceMapsDiffer')
    api,candidate,_,_,guards=smoke95.readers();main,current66=smoke95.protected_sources(api,candidate)
    need(main==read(path.parent/'MainSources_after.json') and current66==read(path.parent/'Candidate66Sources_after.json')
         and guards.inventory(PROJECT)==read(path.parent/'GameSources_after.json'),'LTS95CurrentSourcesDifferFromActualBuild')
    smoke95.validate_apk(apk)
    return value


def validate_development_build(path):
    """Normalized read-only handoff to a separately authorized device/static helper."""
    invocation_path=Path(path).resolve();value=validate_build_receipt(invocation_path)
    native_path=Path(value['nativeReport']['path']).resolve()
    return {'nativePath':native_path,'invocationPath':invocation_path,'native':read(native_path),
            'apk':Path(value['apk']['path']).resolve(),'package':PACKAGE,'unity':smoke95.VERSION,
            'gameSources':invocation_path.parent/'GameSources_after.json'}


def run(operation,prepared,timeout):
    api,candidate,processes,jobs,guards=smoke95.readers();need(not processes.unity_pids(),'LTS95SerialOwnedEditorRequired')
    prepared=Path(prepared).resolve();guards.reject_links(prepared)
    need(prepared.is_relative_to(EVIDENCE/'GamePreparation') and prepared.name=='Preparation.json','LTS95PreparedFullGameProofRequired')
    proof=read(prepared)
    need(proof.get('status')=='PASS_EXACT_MAIN_COPY_LTS95_AFTER_ACTUAL_SMOKE' and proof.get('templateSHA256')==sha(TEMPLATE)
         and proof.get('project')==PROJECT.relative_to(ROOT).as_posix(),'LTS95PreparedExactFixtureRequired')
    validate_smoke_receipt(check_bound(proof['smokeInvocation']))
    need(60<=timeout<=1800,'LTS95BoundedNativeTimeoutRequired')
    main,current66=smoke95.protected_sources(api,candidate);before=guards.inventory(PROJECT);protected_assets(main,before,guards)
    tool_prefs=smoke95.external_pref_fingerprints()
    prepared_inputs=read(check_bound(proof['preparedManifest']))
    need('6000.3.27f1' in (PROJECT/'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig'),'LTS95CurrentGameVersionRequired')
    identifier=uuid.uuid4().hex;output=EVIDENCE/'GameRuns'/identifier;output.mkdir(parents=True,exist_ok=False)
    for prefix,data in (('Main',main),('Candidate66',current66),('Game',before)):api.write(output/(prefix+'Sources_before.json'),data)
    api.write(output/'ExternalToolsPrefFingerprints_before.json',tool_prefs)
    api.write(output/'PreexistingPreparedInputDeltas.json',delta(prepared_inputs['files'],before['files']))
    tools=smoke95.tool_markers(smoke95.EDITOR);need(tools==proof['tools'],'LTS95ApprovedToolchainBytesChanged')
    environment=dict(os.environ);environment['HOTR_LTS95_GAME_OUT']=str(output)
    apk=PROJECT/'Builds'/identifier/'HeartOfTheRain_LTS95_Development.apk'
    if operation=='BuildDevelopment':environment['HOTR_LTS95_GAME_APK']=str(apk)
    else:environment.pop('HOTR_LTS95_GAME_APK',None)
    command=[str(smoke95.EDITOR),'-batchmode','-buildTarget','Android','-projectPath',str(PROJECT),'-executeMethod',ENTRY+operation,'-logFile',str(output/'Unity.log')]
    report={'schemaVersion':1,'status':'RUNNING_ACTUAL_LTS95_GAME_'+operation.upper(),'operation':operation,'startedUtc':api.utc(),
            'runnerSHA256':sha(Path(__file__)),'preparation':binding(prepared),'editor':binding(smoke95.EDITOR),'tools':tools,'command':command,
            'startsAtExactPreparedInputs':before==prepared_inputs,'preexistingPreparedInputDeltas':binding(output/'PreexistingPreparedInputDeltas.json'),
            'scope':'Actual isolated full-game native LTS inspection/Development compile only. Exact original main and6000.6 candidate protected. No provider/backend/device, gameplay campaign, cross-engine pixels/performance or production certification.'}
    api.write(output/'Authorization.json',report);process=job=None
    try:
        job=api.OwnedJob();startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        with (output/'Console.log').open('x',encoding='utf-8') as stream:
            process=subprocess.Popen(command,cwd=PROJECT,env=environment,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|0x4,startupinfo=startup)
            job.assign(process.pid);jobs.resume_owned_primary(process);report.update(pid=process.pid,ownedJobAssignedBeforeResume=True)
            try:process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:report['timedOut']=True;job.close();process.wait(timeout=20)
        native_path=output/(operation+'.json');native=read(native_path) if native_path.is_file() else {};log=(output/'Unity.log').read_text('utf-8-sig',errors='replace')
        match=re.search(r'Initialize engine version:\s*(\S+)',log)
        report.update(exitCode=process.returncode,nativeStatus=native.get('status','MISSING'),actualEngineVersionFromLog=match.group(1) if match else None,
                      nativeReport=binding(native_path) if native_path.is_file() else None)
        need(process.returncode==0 and not report.get('timedOut') and native.get('status')=='PASS_NATIVE_LTS95_GAME_'+operation.upper()
             and native.get('unity')==smoke95.VERSION==report['actualEngineVersionFromLog'] and not native.get('error')
             and native.get('exitCode')==0 and native.get('checks') and all(row.get('passed') is True for row in native['checks']),'LTS95ActualNativeGameOperationFailed')
        validate_native_settings(native['after'])
        if operation=='BuildDevelopment':
            static=smoke95.validate_apk(apk);need(static['sha256']==native.get('apkSHA256') and static['bytes']==native.get('bytes'),'LTS95ActualBuildAPKHashMismatch')
            report.update(apk=binding(apk),apkContainer=static)
        report['status']='PASS_ACTUAL_LTS95_GAME_'+operation.upper()
    except Exception as error:report.update(status='FAIL_ACTUAL_LTS95_GAME_'+operation.upper(),errorType=type(error).__name__,error=str(error))
    finally:
        if job:job.close()
        if process and process.poll() is None:process.kill();process.wait(timeout=20)
        try:
            after_main,after66=api.freeze(),candidate.candidate_sources(api);after=guards.inventory(PROJECT)
            for prefix,data in (('Main',after_main),('Candidate66',after66),('Game',after)):api.write(output/(prefix+'Sources_after.json'),data)
            changes=delta(before['files'],after['files']);api.write(output/'GameInputDeltas.json',changes)
            after_prefs=smoke95.external_pref_fingerprints();api.write(output/'ExternalToolsPrefFingerprints_after.json',after_prefs)
            report.update(mainInputsUnchanged=after_main==main,candidate66InputsUnchanged=after66==current66,gameInputsStable=before==after,
                          externalToolPrefFingerprintsUnchanged=after_prefs==tool_prefs,embeddedToolMarkersUnchanged=smoke95.tool_markers(smoke95.EDITOR)==tools,
                          assetProtection=protected_assets(main,after,guards),gameSourceDeltaCount=len(changes),gameInputDeltas=binding(output/'GameInputDeltas.json'),
                          gameSourcesBeforeSHA256=sha(output/'GameSources_before.json'),gameSourcesAfterSHA256=sha(output/'GameSources_after.json'),
                          mainSourcesBeforeSHA256=sha(output/'MainSources_before.json'),mainSourcesAfterSHA256=sha(output/'MainSources_after.json'),
                          candidate66SourcesBeforeSHA256=sha(output/'Candidate66Sources_before.json'),candidate66SourcesAfterSHA256=sha(output/'Candidate66Sources_after.json'))
            need(report['mainInputsUnchanged'] and report['candidate66InputsUnchanged'],'LTS95ProtectedProjectsChanged')
            need(report['externalToolPrefFingerprintsUnchanged'] and report['embeddedToolMarkersUnchanged'],'LTS95ExternalToolsOrPreferencesChanged')
            if operation!='Configure':need(report['gameInputsStable'],'LTS95GameInputChangedDuringInspectionOrBuild')
        except Exception as error:report.update(status='FAIL_ACTUAL_LTS95_GAME_SOURCE_INVARIANT',invariantErrorType=type(error).__name__,invariantError=str(error))
        report.update(unityPidsAfter=processes.unity_pids(),finishedUtc=api.utc(),unityLog=binding(output/'Unity.log') if (output/'Unity.log').is_file() else None)
        if report['unityPidsAfter']:report['status']='FAIL_ACTUAL_LTS95_GAME_PROCESS_REMAINS'
        api.write(output/'Invocation.json',report)
        print(json.dumps({'status':report['status'],'report':(output/'Invocation.json').relative_to(ROOT).as_posix()}),flush=True)
    return 0 if report['status'].startswith('PASS_') else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--execute',action='store_true')
    parser.add_argument('--out',type=Path);parser.add_argument('--smoke-invocation',type=Path);parser.add_argument('--prepared',type=Path)
    parser.add_argument('--operation',choices=('Configure','Inspect','BuildDevelopment'));parser.add_argument('--timeout',type=int,default=1200);args=parser.parse_args()
    if not args.execute or os.name!='nt':parser.error('Explicit root Windows action required')
    if args.action=='prepare':
        need(args.out is not None and args.smoke_invocation is not None and args.prepared is None and args.operation is None,'LTS95FreshCopyArgumentsRequired')
        prepare(args.out,args.smoke_invocation);return 0
    need(args.prepared is not None and args.operation is not None and args.out is None and args.smoke_invocation is None,'LTS95NativeRunArgumentsRequired')
    return run(args.operation,args.prepared,args.timeout)


if __name__=='__main__':raise SystemExit(main())
