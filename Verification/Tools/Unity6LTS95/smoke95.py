"""Root-only fresh embedded-toolchain LTS smoke preparation and bounded build."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
import zipfile

ROOT=Path(__file__).resolve().parents[3]
PRIVATE=ROOT/'.verification-cache/Unity6LTS95'
PROJECT=PRIVATE/'Smoke'
EVIDENCE=ROOT/'Verification/Evidence/Unity6LTS95'
TEMPLATE=Path(__file__).with_name('Templates')/'ToolchainSmoke95.cs'
EDITOR=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe')
VERSION='6000.3.27f1'
ENTRY='HeartOfTheRain.Verification.ToolchainSmoke95.Run'
BASELINE=ROOT/'Verification/Evidence/Unity6Migration94/MainSources_Before.json'
BASELINE_SHA='773493400ad57ea52db9e9cf11ba0cd1774fd47071c179ad15d88a4480cebccb'


def need(value,code):
    if not value:raise ValueError(code)


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def readers():
    api=module('smoke95_main_reader',ROOT/'Verification/Tools/Ads85/run_ads85_native.py')
    sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
    candidate=module('smoke95_candidate66_reader',ROOT/'Verification/Tools/Unity6Migration94/run_native.py')
    process=module('smoke95_process_reader',ROOT/'Verification/Tools/PageBackdrop90/process90.py')
    jobs=module('smoke95_owned_resume',ROOT/'Verification/Tools/Review93/run_connected.py')
    guards=module('smoke95_link_guard',ROOT/'Verification/Tools/Unity6Migration94/audit_candidate94.py')
    return api,candidate,process,jobs,guards


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text('utf-8-sig'))


def binding(path):
    path=Path(path).resolve()
    return {'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size}


def contained_output(path,category):
    path=Path(path).resolve();allowed=(EVIDENCE/category).resolve()
    need(path.is_relative_to(allowed) and path!=allowed and not path.exists(),'Smoke95FreshContainedEvidenceRequired')
    return path


def source_manifest(project):
    files={}
    for category in ('Assets','Packages','ProjectSettings'):
        for path in sorted((project/category).rglob('*')):
            if path.is_file():files[path.relative_to(project).as_posix()]={'sha256':sha(path),'bytes':path.stat().st_size}
    return {'files':files,'inputCount':len(files)}


def validate_prepared_inputs(proof,project,inventory):
    expected={'Assets/Editor/ToolchainSmoke95.cs','Assets/Editor/ToolchainSmoke95.cs.meta',
              'Packages/manifest.json','ProjectSettings/ProjectVersion.txt'}
    prepared=proof.get('inputManifest',{})
    need(prepared.get('inputCount')==4 and set(prepared.get('files',{}))==expected,'Smoke95ExactlyFourPreparedInputPathsRequired')
    # The inventory rejects linked files/directories as well as hashing every input.
    current=inventory(project)
    need(current.get('inputCount')==4 and current.get('files')==prepared['files'],
         'Smoke95ExactFreshPreparedInputSetRequiredNoImplicitPostImportRetry')


def tool_markers(editor):
    need(Path(editor).resolve()==EDITOR.resolve() and Path(editor).is_file(),'Smoke95ExactInstalledEditorRequired')
    android=Path(editor).parent/'Data/PlaybackEngines/AndroidPlayer'
    paths={
        'editor':Path(editor),'jdkRelease':android/'OpenJDK/release','java':android/'OpenJDK/bin/java.exe',
        'ndkProperties':android/'NDK/source.properties','clang':android/'NDK/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe',
        'sdkPlatform36':android/'SDK/platforms/android-36/android.jar','aapt2':android/'SDK/build-tools/36.0.0/aapt2.exe',
        'beeVisualStudioSolution':Path(editor).parent/'Data/Tools/BuildPipeline/Bee.VisualStudioSolution.dll',
        'beeBackend':Path(editor).parent/'Data/Tools/BuildPipeline/bee_backend.exe'}
    need(all(path.is_file() for path in paths.values()),'Smoke95CompleteEmbeddedOfficialChildrenRequired')
    need(re.search(r'^JAVA_VERSION="17\.',paths['jdkRelease'].read_text('utf-8-sig'),re.MULTILINE)
         and re.search(r'^Pkg.Revision\s*=\s*27\.2\.12479018\s*$',paths['ndkProperties'].read_text('utf-8-sig'),re.MULTILINE),
         'Smoke95ExactJDK17NDKr27cRequired')
    need((android/'Tools/gradle').is_dir(),'Smoke95EmbeddedGradleRequired')
    return {name:binding(path) for name,path in paths.items()}


def external_pref_fingerprints():
    # Read-only diagnostic; never guess preference keys, write, delete or restore them.
    import winreg
    key=r'Software\Unity Technologies\Unity Editor 5.x'
    result={'registryKey':key,'exists':False,'matchingValues':{}}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key,0,winreg.KEY_READ) as handle:
            result['exists']=True;index=0
            while True:
                try:name,value,kind=winreg.EnumValue(handle,index)
                except OSError as error:
                    if getattr(error,'winerror',None)==259:break
                    raise
                index+=1
                if not re.search(r'sdk|ndk|jdk|gradle',name,re.IGNORECASE):continue
                encoded=json.dumps([kind,value.hex() if isinstance(value,bytes) else value],ensure_ascii=True,sort_keys=True).encode('utf-8')
                result['matchingValues'][name]={'type':kind,'valueSHA256':hashlib.sha256(encoded).hexdigest()}
    except FileNotFoundError:pass
    return result


def protected_sources(api,candidate):
    need(sha(BASELINE)==BASELINE_SHA,'Smoke95ProtectedBaselineManifestChanged')
    main=api.freeze();need(main==read(BASELINE) and main['inputCount']==5407,'Smoke95Main2022Changed')
    return main,candidate.candidate_sources(api)


def prepare(output):
    api,candidate,process,_,guards=readers()
    need(not process.unity_pids(),'Smoke95NoConcurrentUnityDuringPreparation')
    for path in (PROJECT,PRIVATE,output,EDITOR):guards.reject_links(path)
    output=contained_output(output,'SmokePreparation')
    need(not PROJECT.exists(),'Smoke95ExistingMinimalProjectPreserved')
    tools=tool_markers(EDITOR);main,current66=protected_sources(api,candidate)
    output.mkdir(parents=True,exist_ok=False)
    inputs={
        'Assets/Editor/ToolchainSmoke95.cs':TEMPLATE.read_bytes(),
        'Assets/Editor/ToolchainSmoke95.cs.meta':b'fileFormatVersion: 2\nguid: 67225aaf5cdf40a082cc6c788935d095\n',
        'Packages/manifest.json':b'{"dependencies":{"com.unity.modules.jsonserialize":"1.0.0","com.unity.modules.androidjni":"1.0.0"}}\n',
        'ProjectSettings/ProjectVersion.txt':('m_EditorVersion: '+VERSION+'\n').encode('utf-8')}
    for relative,raw in inputs.items():
        path=PROJECT/relative;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    need((main,current66)==protected_sources(api,candidate),'Smoke95ProtectedProjectsChangedDuringPreparation')
    api.write(output/'MainSources_before.json',main);api.write(output/'Candidate66Sources_before.json',current66)
    report={'schemaVersion':1,'status':'PASS_FRESH_MINIMAL_LTS95_SMOKE_PREPARATION','utc':api.utc(),
            'runnerSHA256':sha(Path(__file__)),'templateSHA256':sha(TEMPLATE),'version':VERSION,
            'project':PROJECT.relative_to(ROOT).as_posix(),'editor':binding(EDITOR),'tools':tools,
            'inputManifest':source_manifest(PROJECT),'mainInputsUnchanged':True,'candidate66InputsUnchanged':True,
            'scope':'Four fresh minimal project text inputs only. No game copy/import, SDK installation, Unity execution, external-tool preference setter, APK/device/backend action. Embedded official children required; shared/custom preferences are never changed.'}
    api.write(output/'Preparation.json',report)
    print(json.dumps({'status':report['status'],'preparation':(output/'Preparation.json').relative_to(ROOT).as_posix()}),flush=True)


def validate_apk(path):
    path=Path(path)
    need(path.is_file() and path.stat().st_size>0,'Smoke95ActualAPKRequired')
    with zipfile.ZipFile(path) as archive:
        need(archive.testzip() is None,'Smoke95APKCRCFailed')
        names=archive.namelist()
        need(len(names)==len(set(names)) and 'AndroidManifest.xml' in names,'Smoke95ActualAPKManifestRequired')
        libs=[name for name in names if name.startswith('lib/') and name.endswith('.so')]
        need('lib/arm64-v8a/libil2cpp.so' in libs and 'lib/arm64-v8a/libunity.so' in libs
             and all(name.startswith('lib/arm64-v8a/') for name in libs),'Smoke95ARM64IL2CPPOnlyRequired')
    return {'sha256':sha(path),'bytes':path.stat().st_size,'entryCount':len(names),'nativeLibraries':libs,'crcVerified':True,
            'scope':'Host APK container/ABI only; package/API/splash values require actual native build report and manifest badging. Never install this smoke APK.'}


def run(prepared,timeout):
    api,candidate,processes,jobs,guards=readers()
    need(not processes.unity_pids(),'Smoke95OwnedSerialUnityRequired')
    prepared=Path(prepared).resolve();guards.reject_links(prepared)
    need(prepared.is_relative_to(EVIDENCE/'SmokePreparation') and prepared.name=='Preparation.json','Smoke95PreparedProjectProofRequired')
    proof=read(prepared)
    need(proof.get('status')=='PASS_FRESH_MINIMAL_LTS95_SMOKE_PREPARATION' and proof.get('version')==VERSION
         and proof.get('project')==PROJECT.relative_to(ROOT).as_posix() and proof.get('templateSHA256')==sha(TEMPLATE)
         and proof.get('editor')==binding(EDITOR),'Smoke95UnchangedPreparedFixtureAndEditorRequired')
    need(60<=timeout<=1200,'Smoke95BoundedTimeoutRequired')
    validate_prepared_inputs(proof,PROJECT,guards.inventory)
    tools=tool_markers(EDITOR);need(tools==proof['tools'],'Smoke95EmbeddedToolBytesChanged')
    main,current66=protected_sources(api,candidate);prefs=external_pref_fingerprints()
    identifier=uuid.uuid4().hex;output=EVIDENCE/'SmokeRuns'/identifier;output.mkdir(parents=True,exist_ok=False)
    apk=PRIVATE/'SmokeOutputs'/identifier/'ToolchainSmoke95.apk'
    api.write(output/'MainSources_before.json',main);api.write(output/'Candidate66Sources_before.json',current66)
    api.write(output/'ExternalToolsPrefFingerprints_before.json',prefs)
    environment=dict(os.environ);environment.update(HOTR_SMOKE95_EDITOR=str(EDITOR),HOTR_SMOKE95_OUT=str(output),HOTR_SMOKE95_APK=str(apk))
    command=[str(EDITOR),'-batchmode','-nographics','-buildTarget','Android','-projectPath',str(PROJECT),'-executeMethod',ENTRY,'-logFile',str(output/'Unity.log')]
    report={'schemaVersion':1,'status':'RUNNING_ACTUAL_LTS95_TOOLCHAIN_SMOKE','startedUtc':api.utc(),'runnerSHA256':sha(Path(__file__)),
            'preparation':binding(prepared),'editor':binding(EDITOR),'tools':tools,'command':command,'timeoutSeconds':timeout,
            'scope':'Actual owned hidden Editor empty-scene Android compile only. No full game assets/import, APK installation, device/emulator/backend/provider or production acceptance. No ExternalTools preference setters; relevant registry fingerprints are read-only and checked exactly.'}
    api.write(output/'Authorization.json',report);process=job=None
    try:
        job=api.OwnedJob();startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        with (output/'Console.log').open('x',encoding='utf-8') as stream:
            process=subprocess.Popen(command,cwd=PROJECT,env=environment,stdout=stream,stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW|0x4,startupinfo=startup)
            job.assign(process.pid);jobs.resume_owned_primary(process);report.update(pid=process.pid,ownedJobAssignedBeforeResume=True)
            try:process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:report['timedOut']=True;job.close();process.wait(timeout=20)
        native_path=output/'Native.json';native=read(native_path) if native_path.is_file() else {}
        log=(output/'Unity.log').read_text('utf-8-sig',errors='replace')
        match=re.search(r'Initialize engine version:\s*(\S+)',log)
        report.update(exitCode=process.returncode,nativeStatus=native.get('status','MISSING'),actualEngineVersionFromLog=match.group(1) if match else None,
                      nativeReport=binding(native_path) if native_path.is_file() else None)
        need(process.returncode==0 and not report.get('timedOut') and native.get('status')=='PASS_ACTUAL_LTS95_EMPTY_ANDROID_BUILD'
             and not native.get('error') and native.get('unity')==VERSION==report['actualEngineVersionFromLog']
             and native.get('package')=='com.heartoftherain.toolchain95' and native.get('preferencesReadOnly') is True,
             'Smoke95ActualNativeAndroidBuildFailed')
        apk_proof=validate_apk(apk);need(apk_proof['sha256']==native['apkSHA256'] and apk_proof['bytes']==native['apkBytes'],'Smoke95APKNativeBindingMismatch')
        # Read-only AAPT2 badging, bounded/hidden. Never adb/install or BuildAndRun.
        result=subprocess.run([tools['aapt2']['path'],'dump','badging',str(apk)],capture_output=True,text=True,timeout=45,
                              creationflags=subprocess.CREATE_NO_WINDOW,check=False)
        (output/'Badging.txt').write_text(result.stdout,encoding='utf-8')
        need(result.returncode==0 and "package: name='com.heartoftherain.toolchain95'" in result.stdout
             and "sdkVersion:'26'" in result.stdout and "targetSdkVersion:'36'" in result.stdout,'Smoke95ActualAPKPackageAndAPIValidationFailed')
        report.update(status='PASS_ACTUAL_LTS95_TOOLCHAIN_SMOKE_WITH_NO_GAME_ACCEPTANCE',apk=apk_proof,apkPath=apk.relative_to(ROOT).as_posix(),badging=binding(output/'Badging.txt'),
                      smokeAPKNeverInstalled=True,gameAssetsImported=False,externalToolsPreferenceSettersUsed=False)
    except Exception as error:
        report.update(status='FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE',errorType=type(error).__name__,error=str(error))
    finally:
        if job:job.close()
        if process and process.poll() is None:process.kill();process.wait(timeout=20)
        try:
            after_main,after66=api.freeze(),candidate.candidate_sources(api);after_prefs=external_pref_fingerprints()
            api.write(output/'MainSources_after.json',after_main);api.write(output/'Candidate66Sources_after.json',after66)
            api.write(output/'ExternalToolsPrefFingerprints_after.json',after_prefs)
            report.update(mainInputsUnchanged=after_main==main,candidate66InputsUnchanged=after66==current66,
                          externalToolPrefFingerprintsUnchanged=after_prefs==prefs,embeddedToolMarkersUnchanged=tool_markers(EDITOR)==tools)
        except Exception as invariant_error:
            report.update(mainInputsUnchanged=False,candidate66InputsUnchanged=False,externalToolPrefFingerprintsUnchanged=False,
                          embeddedToolMarkersUnchanged=False,invariantErrorType=type(invariant_error).__name__,invariantError=str(invariant_error))
        report.update(unityPidsAfter=processes.unity_pids(),finishedUtc=api.utc(),unityLog=binding(output/'Unity.log') if (output/'Unity.log').is_file() else None)
        if not(report['mainInputsUnchanged'] and report['candidate66InputsUnchanged'] and report['externalToolPrefFingerprintsUnchanged']
               and report['embeddedToolMarkersUnchanged'] and not report['unityPidsAfter']):
            report['status']='FAIL_ACTUAL_LTS95_SMOKE_SOURCE_OR_PREFERENCE_INVARIANT'
        api.write(output/'Invocation.json',report)
        print(json.dumps({'status':report['status'],'report':(output/'Invocation.json').relative_to(ROOT).as_posix()}),flush=True)
    return 0 if report['status'].startswith('PASS_') else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--execute',action='store_true')
    parser.add_argument('--out',type=Path);parser.add_argument('--prepared',type=Path);parser.add_argument('--timeout',type=int,default=900);args=parser.parse_args()
    if not args.execute or os.name!='nt':parser.error('Explicit root Windows action required; no engine execution performed by preparation authors')
    if args.action=='prepare':
        need(args.out is not None and args.prepared is None,'Smoke95FreshPreparationOutputRequired');prepare(args.out);return 0
    need(args.prepared is not None and args.out is None,'Smoke95PreparedProofRequired');return run(args.prepared,args.timeout)


if __name__=='__main__':raise SystemExit(main())
