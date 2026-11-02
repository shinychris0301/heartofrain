"""Root-only normal stock Editor install; no elevation bypass or automatic UAC fallback."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess

import smoke95
import core_loader95
import official_download95

ROOT,EVIDENCE=smoke95.ROOT,smoke95.EVIDENCE
TARGET=Path('E:/HeartRainUnity6LTS95/6000.3.27f1')


def need(value,code):smoke95.need(value,code)


def installer_command(installer):
    need(TARGET==official_download95.TARGET and not re.search(r'\s',str(TARGET)),'Install95ExactUnquotedStockTargetRequired')
    return [str(Path(installer)), '/S', '/D='+str(TARGET)]


def launch_owned(command,output,timeout,api,jobs):
    """Ordinary Popen only.740 is returned for normal UAC action, never bypassed."""
    need(60<=timeout<=3600,'Install95BoundedTimeoutRequired')
    result={'installerLaunched':False,'ownedJobAssignedBeforeResume':False};process=job=None
    try:
        job=api.OwnedJob();startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        with (output/'stdout.txt').open('xb') as stdout,(output/'stderr.txt').open('xb') as stderr:
            try:
                process=subprocess.Popen(command,cwd=output,stdout=stdout,stderr=stderr,
                                         creationflags=subprocess.CREATE_NO_WINDOW|0x4,startupinfo=startup)
            except OSError as error:
                if getattr(error,'winerror',None)==740:
                    result.update(outcome='RequiresNormalUAC',winerror=740,
                                  action='Use the normal Windows UAC consent flow to run this same checked helper from an elevated terminal with a fresh output. No RunAsInvoker, compatibility-layer, security-setting or unowned elevated-installer fallback is implemented.')
                    return result
                raise
            result.update(installerLaunched=True,pid=process.pid);job.assign(process.pid);jobs.resume_owned_primary(process)
            result['ownedJobAssignedBeforeResume']=True
            try:process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result['timedOut']=True;job.close();process.wait(timeout=20)
        result.update(exitCode=process.returncode,outcome='Completed' if not result.get('timedOut') else 'TimedOut')
    except Exception as error:
        result.update(outcome='Failed',errorType=type(error).__name__,error=str(error))
    finally:
        if job:job.close()
        if process and process.poll() is None:process.kill();process.wait(timeout=20)
    return result


def install(verified_report,output,timeout):
    api,candidate,processes,jobs,guards=smoke95.readers()
    need(not processes.unity_pids(),'Install95NoRunningEditorRequired')
    for path in (verified_report,TARGET,output):guards.reject_links(path)
    output=smoke95.contained_output(output,'Installation')
    need(not TARGET.exists(),'Install95ExistingTargetPreserved')
    # This checks the actual complete publisher checksum/signature receipt and rehashes its installer.
    official=core_loader95.verified_editor_installer(verified_report);installer=Path(official['installer']['path']);guards.reject_links(installer)
    command=installer_command(installer);main,current66=smoke95.protected_sources(api,candidate)
    output.mkdir(parents=True,exist_ok=False)
    api.write(output/'MainSources_before.json',main);api.write(output/'Candidate66Sources_before.json',current66)
    report={'schemaVersion':1,'status':'RUNNING_NORMAL_STOCK_EDITOR_INSTALL95','startedUtc':api.utc(),'runnerSHA256':core_loader95.sha(Path(__file__)),
            'verifiedInstaller':official,'command':command,'target':str(TARGET),'targetAbsentBefore':True,'timeoutSeconds':timeout,
            'parentElevated':bool(ctypes.WinDLL('shell32').IsUserAnAdmin()),
            'scope':'Normal unmodified publisher-verified Unity Editor installer to one absent short target. Ordinary silent /S with /D last, owned suspended process. No installer patch, compatibility/elevation/security bypass, automatic unowned UAC fallback, game copy/build/device operation or APK acceptance. The stock installer may perform its normal documented system registration/prerequisite actions.'}
    api.write(output/'Authorization.json',report)
    try:
        report['launch']=launch_owned(command,output,timeout,api,jobs)
        launch=report['launch']
        if launch['outcome']=='RequiresNormalUAC':
            report.update(status='REQUIRES_NORMAL_UAC_STOCK_EDITOR_INSTALL95',normalUacRequired=True,installerExecuted=False)
        else:
            need(launch.get('outcome')=='Completed' and launch.get('exitCode') in (0,3010)
                 and launch.get('ownedJobAssignedBeforeResume') is True,'Install95StockInstallerDidNotComplete')
            need(smoke95.EDITOR.is_file(),'Install95ActualInstalledEditorRequired')
            version=core_loader95.editor_product_version(smoke95.EDITOR);need(smoke95.VERSION in version,'Install95ActualEditorVersionMismatch')
            try:
                _,core=core_loader95.core_inputs();api.write(output/'InstalledCoreFiles.json',core)
                report['coreLoaderReady']=True;report['installedCore']=smoke95.binding(output/'InstalledCoreFiles.json')
            except ValueError as error:
                if str(error)=='CoreLoader95StockCoreWindowsFrontendUnavailableKeepAndroidSmoke':
                    report.update(coreLoaderReady=False,coreLoaderLimitation=str(error))
                else:raise
            report.update(status='PASS_NORMAL_STOCK_EDITOR_INSTALL95',installedEditor=smoke95.binding(smoke95.EDITOR),editorProductVersion=version,
                          normalUacRequired=False,installerExecuted=True,rebootRequested=launch['exitCode']==3010)
    except Exception as error:
        report.update(status='FAIL_NORMAL_STOCK_EDITOR_INSTALL95',errorType=type(error).__name__,error=str(error))
    finally:
        try:
            after_main,after66=api.freeze(),candidate.candidate_sources(api)
            api.write(output/'MainSources_after.json',after_main);api.write(output/'Candidate66Sources_after.json',after66)
            report.update(mainInputsUnchanged=after_main==main,candidate66InputsUnchanged=after66==current66)
            need(report['mainInputsUnchanged'] and report['candidate66InputsUnchanged'],'Install95ProtectedProjectsChanged')
            if report.get('installerExecuted'):
                need(core_loader95.bound(installer)==official['installer'],'Install95VerifiedInstallerChangedDuringExecution')
        except Exception as invariant_error:
            report.update(status='FAIL_NORMAL_STOCK_EDITOR_INSTALL95_INVARIANT',invariantErrorType=type(invariant_error).__name__,invariantError=str(invariant_error))
        report.update(targetExistsAfter=TARGET.exists(),unityPidsAfter=processes.unity_pids(),finishedUtc=api.utc(),
                      artifacts=[smoke95.binding(path) for path in sorted(output.iterdir()) if path.is_file() and path.name!='Authorization.json'])
        if report['unityPidsAfter']:report['status']='FAIL_NORMAL_STOCK_EDITOR_INSTALL95_EDITOR_REMAINS'
        api.write(output/'Report.json',report)
        print(json.dumps({'status':report['status'],'report':(output/'Report.json').relative_to(ROOT).as_posix(),'coreLoaderReady':report.get('coreLoaderReady')}),flush=True)
    return 0 if report['status']=='PASS_NORMAL_STOCK_EDITOR_INSTALL95' else 2 if report['status']=='REQUIRES_NORMAL_UAC_STOCK_EDITOR_INSTALL95' else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--verified-editor-report',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=1200);args=parser.parse_args()
    if not args.execute or os.name!='nt':parser.error('Explicit root Windows stock installation required')
    return install(args.verified_editor_report,args.out,args.timeout)


if __name__=='__main__':raise SystemExit(main())
