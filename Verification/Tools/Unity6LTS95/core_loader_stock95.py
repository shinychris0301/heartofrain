"""Root-only Unity 6000.3 stock netcorerun loader diagnostic; no Android acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess

import core_loader95 as frozen
import smoke95

ROOT,EVIDENCE,EDITOR=smoke95.ROOT,smoke95.EVIDENCE,smoke95.EDITOR
VERSION='6000.3.27f1_672d562a42a7'
INSTALL=EVIDENCE/'Installation/Set02/Report.json'
INSTALL_SHA='3c387750ceb89d053d83d29188f7cf0b075affca165396de40e8ed3267661296'
PRIMARY_SOURCES=[
    'https://raw.githubusercontent.com/Unity-Technologies/UnityCsReference/6000.3/Editor/Mono/Modules/BeeBuildPostprocessor.cs',
    'https://raw.githubusercontent.com/Unity-Technologies/UnityCsReference/6000.3/Editor/Mono/Utils/NetCoreRunProgram.cs']
PINS={
    'editor':'cfaf4794df5b7ad0ae3afe43edcb6ccb1e08b422a2d6a768e52ce485e0bba673',
    'netcorerun':'d4f76464d34da3c5ebbbf4b31a3e52ab17cba410d072d65d8fa17fe4354f3bfa',
    'runtimeconfig':'67afe665477eaee905bb1853ecaa44c8ef6a910bc246dc7e60b2c75417d4def2',
    'deps':'0b5605b8b79dc870e04e7da97280eabab482c2b57c7118a41dfa5ada40eab930',
    'corelib':'edbc29ad170384d0e1203e38e029bfd0aebcecaa8a96c18ebeef77a888860847',
    'coreclr':'53b01f235e8b6909942f02f339d1765abd2a7e5d39422decb9ad5786ab8dc120',
    'hostfxr':'1330ca408495b1a206933c5b5e9bdd09b0311c9af4263dc96370380904b92fbc',
    'frontend':'8cea37243f0c8203b449b6120cdcfdc63c3325130752410026ef939c0ad2f72c',
    'playerLibrary':'6373be30daf7935d722d6fc687247b768eaa29b9327f95b3d6f6e8296d7fd2ac',
    'beeVisualStudioSolution':'2286d5cafcd9ddb8e905577f7d27d543d4c984811a30f0d7001f1dd3531f093f'}


def need(value,code):smoke95.need(value,code)


def stock_paths(editor):
    editor=Path(editor).resolve();data=editor.parent/'Data';runtime=data/'netcorerun';windows=data/'PlaybackEngines/windowsstandalonesupport';pipeline=data/'Tools/BuildPipeline'
    return {'editor':editor,'netcorerun':runtime/'netcorerun.exe','runtimeconfig':runtime/'netcorerun.runtimeconfig.json',
            'deps':runtime/'netcorerun.deps.json','corelib':runtime/'System.Private.CoreLib.dll','coreclr':runtime/'coreclr.dll',
            'hostfxr':runtime/'hostfxr.dll','frontend':windows/'WinPlayerBuildProgram.exe','frontendData':windows/'WinPlayerBuildProgram.Data.dll',
            'playerLibrary':pipeline/'PlayerBuildProgramLibrary.dll','beeVisualStudioSolution':pipeline/'Bee.VisualStudioSolution.dll'}


def validate_runtime(files):
    need(all(path.is_file() for path in files.values()),'Stock95CompleteInstalledCoreRequired')
    options=frozen.read(files['runtimeconfig']).get('runtimeOptions',{})
    need(options.get('tfm')=='net6.0' and options.get('includedFrameworks')==[{'name':'Microsoft.NETCore.App','version':'6.0.21'}],
         'Stock95ExactBundledNetCoreRunRuntimeRequired')
    deps=frozen.read(files['deps'])
    need(deps.get('runtimeTarget',{}).get('name')=='.NETCoreApp,Version=v6.0/win-x64'
         and 'runtimepack.Microsoft.NETCore.App.Runtime.win-x64/6.0.21' in deps.get('libraries',{}),'Stock95MatchingRuntimeDependencyManifestRequired')
    for key,expected in PINS.items():need(frozen.sha(files[key])==expected,'Stock95InstalledCorePinChanged:'+key)
    return options


def validate_installation(path):
    path=Path(path).resolve()
    need(path==INSTALL.resolve() and frozen.sha(path)==INSTALL_SHA,'Stock95ExactCompletedInstallationReceiptRequired')
    value=frozen.read(path)
    need(value.get('status')=='PASS_NORMAL_STOCK_EDITOR_INSTALL95' and value.get('installerExecuted') is True
         and value.get('target')==str(EDITOR.parent.parent) and value.get('editorProductVersion')==VERSION
         and value.get('launch',{}).get('exitCode')==0 and value.get('launch',{}).get('ownedJobAssignedBeforeResume') is True,
         'Stock95SuccessfulNormalStockInstallationRequired')
    need(value.get('installedEditor')==frozen.bound(EDITOR),'Stock95InstalledEditorChanged')
    official=value.get('verifiedInstaller',{});receipt=Path(official.get('receipt',{}).get('path',''))
    verified=frozen.verified_editor_installer(receipt)
    need(verified==official,'Stock95VerifiedInstallerChainChanged')
    return {'receipt':frozen.bound(path),'verifiedInstaller':verified,
            'earlierCoreLoaderLimitation':'The frozen initial diagnostic assumed the Unity 6000.6 DotNetSdk/frontend-runtimeconfig layout. Its coreLoaderReady=false is a layout guard result, not an application-control failure. This new helper uses the actual Unity 6000.3 stock netcorerun route.'}


def core_snapshot(files,guards):
    roots=(files['netcorerun'].parent,files['frontend'].parent/'Bee',files['playerLibrary'].parent)
    paths=set(files.values())
    for root in roots:
        need(root.is_dir(),'Stock95StockResolverDirectoryRequired');guards.reject_links(root)
        for path in root.rglob('*'):
            guards.reject_links(path)
            if path.is_file():paths.add(path)
    for path in paths:guards.reject_links(path)
    return {path.relative_to(EDITOR.parent).as_posix():frozen.bound(path) for path in sorted(paths)}


def command_for(files,output):
    output=Path(output).resolve();dag=output/'IntentionallyAbsent_DAG.json';source=output/'IntentionallyAbsent_Input.json'
    need(not dag.exists() and not source.exists(),'Stock95DeliberatelyAbsentInputsRequired')
    return [str(files['netcorerun']),str(files['frontend']),str(files['frontend'].parent/'Bee')+';'+str(files['playerLibrary'].parent),
            str(dag),str(source),str(output/'Frontend.traceevents')]


def environment_for(output,base):
    environment=dict(base)
    need(not any(environment.get(key) for key in ('DOTNET_STARTUP_HOOKS','CORECLR_ENABLE_PROFILING','COR_ENABLE_PROFILING',
                                                  'CORECLR_PROFILER','COR_PROFILER','DOTNET_ADDITIONAL_DEPS','DOTNET_SHARED_STORE')),
         'Stock95NoInjectedRuntimeHooksRequired')
    # This is the environment entry in Unity's stock 6000.3 BeeBuildPostprocessor.
    environment['DOTNET_SYSTEM_GLOBALIZATION_INVARIANT']='1'
    return environment


def diagnose(installation,output):
    api,candidate,processes,jobs,guards=smoke95.readers()
    need(not processes.unity_pids(),'Stock95NoConcurrentEditorRequired')
    for path in (EDITOR,installation,output):guards.reject_links(path)
    output=smoke95.contained_output(output,'CoreLoaderStock')
    provenance=validate_installation(installation);files=stock_paths(EDITOR)
    version=frozen.editor_product_version(EDITOR);need(version==VERSION,'Stock95ExactEditorVersionRequired')
    options=validate_runtime(files);before=core_snapshot(files,guards);main,current66=smoke95.protected_sources(api,candidate)
    environment=environment_for(output,os.environ);output.mkdir(parents=True,exist_ok=False);command=command_for(files,output)
    api.write(output/'MainSources_before.json',main);api.write(output/'Candidate66Sources_before.json',current66)
    report={'schemaVersion':1,'status':'RUNNING_STOCK_NETCORERUN95_DIAGNOSTIC','startedUtc':api.utc(),
            'runner':frozen.bound(Path(__file__)),'dependencies':[frozen.bound(Path(module.__file__)) for module in (smoke95,frozen)],
            'installation':provenance,'editorProductVersion':version,'primaryImplementationSources':PRIMARY_SOURCES,
            'runtimeOptions':options,'stockCoreFilesBefore':before,'command':command,'timeoutSeconds':60,
            'childEnvironmentOverrides':{'DOTNET_SYSTEM_GLOBALIZATION_INVARIANT':'1'},
            'scope':'Unmodified installed Unity 6000.3 Windows player frontend, its stock netcorerun and matching bundled runtime/resolver files, with deliberately absent inputs. No Mono fallback, copied DLL, custom assembly, compilation, Editor/project input, Android module/SDK, APK, security/prefs change, or game/device/backend acceptance. Reaching the intended missing-input exception is a loader diagnostic only.'}
    api.write(output/'Authorization.json',report);process=job=None
    try:
        job=api.OwnedJob();startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        with (output/'stdout.txt').open('xb') as stdout,(output/'stderr.txt').open('xb') as stderr:
            process=subprocess.Popen(command,cwd=output,env=environment,stdout=stdout,stderr=stderr,
                                     creationflags=subprocess.CREATE_NO_WINDOW|0x4,startupinfo=startup)
            job.assign(process.pid);jobs.resume_owned_primary(process);report.update(pid=process.pid,ownedJobAssignedBeforeResume=True)
            try:process.wait(timeout=60)
            except subprocess.TimeoutExpired:report['timedOut']=True;job.close();process.wait(timeout=20)
        report.update(exitCode=process.returncode,**frozen.classify((output/'stdout.txt').read_text('utf-8-sig',errors='replace'),
                      (output/'stderr.txt').read_text('utf-8-sig',errors='replace'),process.returncode,output/'IntentionallyAbsent_Input.json',report.get('timedOut',False)))
    except Exception as error:
        report.update(status='RECORDED_STOCK_NETCORERUN95_UNKNOWN_NOT_ANDROID_ACCEPTANCE',classification='UNKNOWN_HELPER_ERROR',errorType=type(error).__name__,error=str(error))
    finally:
        if job:job.close()
        if process and process.poll() is None:process.kill();process.wait(timeout=20)
        try:
            after=core_snapshot(files,guards);after_main,after66=api.freeze(),candidate.candidate_sources(api)
            api.write(output/'MainSources_after.json',after_main);api.write(output/'Candidate66Sources_after.json',after66)
            report.update(stockCoreFilesAfter=after,stockCoreUnchanged=after==before,mainInputsUnchanged=after_main==main,
                          candidate66InputsUnchanged=after66==current66,installationReceiptUnchanged=frozen.sha(INSTALL)==INSTALL_SHA)
            need(all(report[name] for name in ('stockCoreUnchanged','mainInputsUnchanged','candidate66InputsUnchanged','installationReceiptUnchanged')),
                 'Stock95CoreOrProtectedProjectChanged')
        except Exception as error:
            report.update(status='FAIL_STOCK_NETCORERUN95_INVARIANT',classification='UNKNOWN_INVARIANT_FAILURE',invariantErrorType=type(error).__name__,invariantError=str(error))
        report.update(deliberatelyAbsentInputStillAbsent=not (output/'IntentionallyAbsent_Input.json').exists(),unityPidsAfter=processes.unity_pids(),finishedUtc=api.utc(),
                      artifacts=[frozen.bound(path) for path in sorted(output.iterdir()) if path.is_file() and path.name!='Authorization.json'])
        if not report['deliberatelyAbsentInputStillAbsent'] or report['unityPidsAfter']:
            report.update(status='FAIL_STOCK_NETCORERUN95_PROCESS_OR_INPUT_INVARIANT',classification='UNKNOWN_INVARIANT_FAILURE')
        api.write(output/'Report.json',report)
        print(json.dumps({'status':report['status'],'classification':report.get('classification'),'report':(output/'Report.json').relative_to(ROOT).as_posix()}),flush=True)
    return 0 if report.get('classification')=='LOADER_REACHED_DELIBERATE_INPUT_FAILURE' else 2 if report.get('classification')=='BLOCK_APPLICATION_CONTROL_0x800711C7' else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--installation-report',type=Path,default=INSTALL);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if not args.execute or os.name!='nt':parser.error('Explicit root Windows stock netcorerun diagnostic required')
    return diagnose(args.installation_report,args.out)


if __name__=='__main__':raise SystemExit(main())
