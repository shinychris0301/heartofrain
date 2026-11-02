"""Root-only stock Windows player loader diagnostic; not an Android build or fix."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import smoke95
import official_download95

ROOT,EVIDENCE=smoke95.ROOT,smoke95.EVIDENCE
EDITOR=smoke95.EDITOR
VERSION=smoke95.VERSION


def need(value,code):smoke95.need(value,code)
def read(path):return json.loads(Path(path).read_text('utf-8-sig'))


def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def bound(path):
    path=Path(path).resolve()
    return {'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size}


def editor_product_version(path):
    """Read VERSIONINFO with Windows metadata APIs; never execute the Editor."""
    api=ctypes.WinDLL('version',use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];api.GetFileVersionInfoSizeW.restype=ctypes.c_ulong
    api.GetFileVersionInfoW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];api.GetFileVersionInfoW.restype=ctypes.c_int
    api.VerQueryValueW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_uint)];api.VerQueryValueW.restype=ctypes.c_int
    size=api.GetFileVersionInfoSizeW(str(path),None);need(size>0,'CoreLoader95VersionResourceRequired')
    buffer=ctypes.create_string_buffer(size);need(api.GetFileVersionInfoW(str(path),0,size,buffer),'CoreLoader95VersionResourceReadFailed')
    address=ctypes.c_void_p();length=ctypes.c_uint()
    need(api.VerQueryValueW(buffer,r'\VarFileInfo\Translation',ctypes.byref(address),ctypes.byref(length)) and length.value>=4,'CoreLoader95VersionTranslationRequired')
    values=ctypes.cast(address,ctypes.POINTER(ctypes.c_ushort));query=r'\StringFileInfo\%04x%04x\ProductVersion'%(values[0],values[1])
    need(api.VerQueryValueW(buffer,query,ctypes.byref(address),ctypes.byref(length)) and length.value>0,'CoreLoader95ProductVersionRequired')
    return ctypes.wstring_at(address.value)


def verified_editor_installer(report_path):
    report_path=Path(report_path).resolve()
    need(report_path.is_relative_to(EVIDENCE/'OfficialDownloads') and report_path.name=='Report.json','CoreLoader95OfficialInstallerReceiptRequired')
    value=read(report_path);info=official_download95.component_info('editor');proof=value.get('installer',{})
    need(value.get('status')=='PASS_COMPLETE_OFFICIAL_INSTALLER95' and value.get('component')=='editor' and value.get('trustedInstaller') is True
         and proof.get('filename')==info['filename'] and proof.get('bytes')==info['bytes'] and proof.get('md5')==info['md5']
         and proof.get('authenticode',{}).get('Status')=='Valid'
         and re.search(r'Unity Technologies',proof.get('authenticode',{}).get('SignerSubject',''),re.IGNORECASE),'CoreLoader95VerifiedPublisherEditorRequired')
    plan=value.get('normalInstallPlan',{})
    need(plan.get('arguments')==['/S','/D='+str(official_download95.TARGET)],'CoreLoader95ExactStockInstallTargetRequired')
    installer=Path(plan.get('executable','')).resolve()
    need(installer.is_relative_to(official_download95.PRIVATE) and installer.name==info['filename'] and installer.is_file()
         and installer.stat().st_size==info['bytes'] and sha(installer)==proof.get('sha256'),'CoreLoader95VerifiedInstallerBytesChanged')
    return {'receipt':bound(report_path),'installer':bound(installer),'publisherSignature':proof['authenticode']}


def core_inputs():
    need(EDITOR==Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe'),'CoreLoader95ExactLTSEditorRootRequired')
    data=EDITOR.parent/'Data';windows=data/'PlaybackEngines/windowsstandalonesupport';pipeline=data/'Tools/BuildPipeline'
    files={'editor':EDITOR,'dotnet':data/'DotNetSdk/dotnet.exe','frontend':windows/'WinPlayerBuildProgram.exe',
           'runtimeconfig':windows/'WinPlayerBuildProgram.runtimeconfig.json','frontendData':windows/'WinPlayerBuildProgram.Data.dll',
           'playerLibrary':pipeline/'PlayerBuildProgramLibrary.dll','beeVisualStudioSolution':pipeline/'Bee.VisualStudioSolution.dll'}
    need(all(path.is_file() for path in files.values()) and (windows/'Bee').is_dir(),'CoreLoader95StockCoreWindowsFrontendUnavailableKeepAndroidSmoke')
    runtime=read(files['runtimeconfig']).get('runtimeOptions',{});framework=runtime.get('framework',{})
    need(framework.get('name')=='Microsoft.NETCore.App' and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',framework.get('version','')),'CoreLoader95MatchingBundledRuntimeConfigRequired')
    files['coreRuntime']=data/'DotNetSdk/shared/Microsoft.NETCore.App'/framework['version']/'System.Private.CoreLib.dll'
    need(files['coreRuntime'].is_file(),'CoreLoader95ExactBundledRuntimeRequired')
    version=editor_product_version(EDITOR)
    need(VERSION in version,'CoreLoader95InstalledEditorVersionMismatch')
    return files,{'editorProductVersion':version,'runtimeOptions':runtime,'files':{key:bound(path) for key,path in files.items()}}


def command_for(files,output):
    output=Path(output).resolve();dag=output/'IntentionallyAbsent_DAG.json';source=output/'IntentionallyAbsent_Input.json'
    need(not dag.exists() and not source.exists(),'CoreLoader95DeliberatelyAbsentInputsRequired')
    windows=files['frontend'].parent;pipeline=files['playerLibrary'].parent
    return [str(files['dotnet']),str(files['frontend']),str(windows/'Bee')+';'+str(pipeline),str(dag),str(source),str(output/'Frontend.traceevents')]


def classify(stdout,stderr,exit_code,input_path,timed_out=False):
    text=stdout+'\n'+stderr
    if timed_out:return {'classification':'UNKNOWN_TIMEOUT','status':'RECORDED_CORE_LOADER95_UNKNOWN_NOT_ANDROID_ACCEPTANCE'}
    if exit_code!=0 and re.search(r'0x800711c7',text,re.IGNORECASE):
        return {'classification':'BLOCK_APPLICATION_CONTROL_0x800711C7','status':'BLOCK_STOCK_CORE_LOADER95_APPLICATION_CONTROL',
                'beeVisualStudioSolutionNamed':bool(re.search(r'Bee\.VisualStudioSolution',text,re.IGNORECASE))}
    deliberate=Path(input_path).resolve()
    if exit_code!=0 and not deliberate.exists() and not re.search(r'(?:FileLoadException|TypeLoadException|ReflectionTypeLoadException|could not load file or assembly)',text,re.IGNORECASE):
        exceptions=re.findall(r'(?:System\.IO\.)?(?:FileNotFoundException|DirectoryNotFoundException):[ \t]*([^\r\n]*)',text)
        missing=[]
        for message in exceptions:
            # Require the path named by the actual I/O exception, never an argv/log echo.
            match=re.fullmatch(r'''Could not find (?:file|a part of the path) ['"]([^'"\r\n]+)['"]\.?[ \t]*''',message,re.IGNORECASE)
            if not match or not Path(match[1]).is_absolute():break
            missing.append(Path(match[1]).resolve())
        if exceptions and len(missing)==len(exceptions) and all(path==deliberate for path in missing):
            return {'classification':'LOADER_REACHED_DELIBERATE_INPUT_FAILURE','status':'RECORDED_CORE_LOADER95_REACHED_INPUT_NOT_ANDROID_ACCEPTANCE'}
    return {'classification':'UNKNOWN_RESULT','status':'RECORDED_CORE_LOADER95_UNKNOWN_NOT_ANDROID_ACCEPTANCE'}


def diagnose(installer_report,output):
    api,_,processes,jobs,guards=smoke95.readers()
    need(not processes.unity_pids(),'CoreLoader95NoConcurrentEditorRequired')
    for path in (EDITOR,installer_report,output):guards.reject_links(path)
    output=smoke95.contained_output(output,'CoreLoader')
    official=verified_editor_installer(installer_report);files,inputs=core_inputs()
    for path in files.values():guards.reject_links(path)
    output.mkdir(parents=True,exist_ok=False);command=command_for(files,output)
    report={'schemaVersion':1,'status':'RUNNING_STOCK_CORE_LOADER95_DIAGNOSTIC','startedUtc':api.utc(),'runnerSHA256':sha(Path(__file__)),
            'officialEditorInstaller':official,'coreInputsBefore':inputs,'command':command,'timeoutSeconds':60,
            'scope':'Stock matching LTS Windows player frontend with deliberately absent input, using matching bundled dotnet/runtime and resolver folders only. No custom assembly, code compile, Unity Editor/project input, Android module/SDK, APK, security/prefs/vendor changes or game/device/backend acceptance. A loader-reaching missing-input error is not Android acceptance.'}
    api.write(output/'Authorization.json',report)
    environment=dict(os.environ);environment.update(DOTNET_CLI_HOME=str(output/'DotnetHome'),DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1')
    process=job=None
    try:
        job=api.OwnedJob();startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        with (output/'stdout.txt').open('xb') as stdout,(output/'stderr.txt').open('xb') as stderr:
            process=subprocess.Popen(command,cwd=output,env=environment,stdout=stdout,stderr=stderr,
                                     creationflags=subprocess.CREATE_NO_WINDOW|0x4,startupinfo=startup)
            job.assign(process.pid);jobs.resume_owned_primary(process);report.update(pid=process.pid,ownedJobAssignedBeforeResume=True)
            try:process.wait(timeout=60)
            except subprocess.TimeoutExpired:report['timedOut']=True;job.close();process.wait(timeout=20)
        report.update(exitCode=process.returncode,**classify((output/'stdout.txt').read_text('utf-8-sig',errors='replace'),
                      (output/'stderr.txt').read_text('utf-8-sig',errors='replace'),process.returncode,output/'IntentionallyAbsent_Input.json',report.get('timedOut',False)))
    except Exception as error:
        report.update(status='RECORDED_CORE_LOADER95_UNKNOWN_NOT_ANDROID_ACCEPTANCE',classification='UNKNOWN_HELPER_ERROR',errorType=type(error).__name__,error=str(error))
    finally:
        if job:job.close()
        if process and process.poll() is None:process.kill();process.wait(timeout=20)
        try:
            after={key:bound(path) for key,path in files.items()};report.update(coreFilesUnchanged=after==inputs['files'],coreInputsAfter=after)
        except Exception as invariant_error:
            report.update(coreFilesUnchanged=False,postHashErrorType=type(invariant_error).__name__)
        report.update(deliberatelyAbsentInputStillAbsent=not (output/'IntentionallyAbsent_Input.json').exists(),unityPidsAfter=processes.unity_pids(),finishedUtc=api.utc(),
                artifacts=[bound(path) for path in sorted(output.iterdir()) if path.is_file() and path.name!='Authorization.json'])
        if not report['coreFilesUnchanged'] or report['unityPidsAfter']:
            report.update(status='FAIL_CORE_LOADER95_STOCK_FILE_OR_PROCESS_INVARIANT',classification='UNKNOWN_INVARIANT_FAILURE')
        api.write(output/'Report.json',report)
        print(json.dumps({'status':report['status'],'classification':report.get('classification'),'report':(output/'Report.json').relative_to(ROOT).as_posix()}),flush=True)
    return 0 if report.get('classification')=='LOADER_REACHED_DELIBERATE_INPUT_FAILURE' else 2 if report.get('classification')=='BLOCK_APPLICATION_CONTROL_0x800711C7' else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');parser.add_argument('--verified-editor-report',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if not args.execute or os.name!='nt':parser.error('Explicit root Windows stock-loader diagnostic required')
    return diagnose(args.verified_editor_report,args.out)


if __name__=='__main__':raise SystemExit(main())
