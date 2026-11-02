"""Root-only revision97 stock Android support install for the verified LTS Editor.

This prepares no SDK copies and executes no Editor, Java, SDK or device command.
The installer is independently rechecked against publisher MD5 and Authenticode.
An existing/partial AndroidPlayer is preserved rather than overlaid or removed.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import re

import core_loader95 as core
import install95 as stock
import official_download95 as download
import smoke95 as smoke
import core_loader_stock95 as stock_core

ROOT,EVIDENCE=smoke.ROOT,smoke.EVIDENCE
TARGET=Path('E:/HeartRainUnity6LTS95/6000.3.27f1')
ANDROID=TARGET/'Editor/Data/PlaybackEngines/AndroidPlayer'
EXACT_VERSION='6000.3.27f1_672d562a42a7'
COMPONENT_PUBLIC=EVIDENCE/'ComponentDownloads'
COMPONENT_PRIVATE=ROOT/'.verification-cache/Unity6LTS95/ComponentDownloads'
COMPONENT_HELPER=Path(__file__).with_name('download_component95.py')
COMPONENT_HELPER_SHA='873d9e02302057cf858c98ea58c2ea3c0b62ca42106ef3e535b3113891608d05'
OFFICIAL_HELPER_SHA='0dcf067e2e92f6b6e8c51e36a4ebeea802e44997541bc2c86fcfb0601a9de0fb'
METADATA_SHA='20b0336f3950a89aeafafb2b58dc173c0774aca91e7c91fac6cd1ff2fe32e63f'
CORE_READER_SHA='5cae33216b2d2b47363578a7e7f790c6ab1a0bb6a8becbf11531e12da632b2a1'
CORE_BASELINE=EVIDENCE/'CoreLoaderStock/Set01/Report.json'
CORE_BASELINE_SHA='1050fc19c3215a2bd6b15d87f85f2ab46ca13dd6c7d923e55942ad5289da5f77'
EDITOR_RECEIPT=EVIDENCE/'Installation/Set02/Report.json'
EDITOR_RECEIPT_SHA='3c387750ceb89d053d83d29188f7cf0b075affca165396de40e8ed3267661296'


def need(value,code):smoke.need(value,code)


def installer_command(installer):
    need(TARGET==stock.TARGET==download.TARGET and not re.search(r'\s',str(TARGET)),
         'Module95ExactUnquotedStockEditorTargetRequired')
    return [str(Path(installer)),'/S','/D='+str(TARGET)]


def verify_stock_record(value,editor_binding,version,runner_sha):
    need(value.get('status')=='PASS_NORMAL_STOCK_EDITOR_INSTALL95'
         and value.get('runnerSHA256')==runner_sha and value.get('target')==str(TARGET)
         and value.get('installedEditor')==editor_binding
         and value.get('editorProductVersion')==version==EXACT_VERSION
         and value.get('installerExecuted') is True and value.get('normalUacRequired') is False
         and value.get('mainInputsUnchanged') is True and value.get('candidate66InputsUnchanged') is True
         and value.get('unityPidsAfter')==[]
         and value.get('launch',{}).get('outcome')=='Completed'
         and value.get('launch',{}).get('exitCode') in (0,3010)
         and value.get('launch',{}).get('ownedJobAssignedBeforeResume') is True,
         'Module95CurrentVerifiedStockEditorInstallationRequired')


def installed_editor(report_path,main,current66,guards):
    guards.reject_links(report_path)
    report_path=Path(report_path).resolve()
    need(report_path==EDITOR_RECEIPT.resolve() and core.sha(report_path)==EDITOR_RECEIPT_SHA,
         'Module97ExactStockInstallationSet02Required')
    for path in (report_path,smoke.EDITOR):guards.reject_links(path)
    value=smoke.read(report_path)
    verify_stock_record(value,smoke.binding(smoke.EDITOR),core.editor_product_version(smoke.EDITOR),
                        core.sha(Path(stock.__file__)))
    artifacts={Path(row['path']).name:row for row in value.get('artifacts',[])}
    for name,expected in [('MainSources_before.json',main),('MainSources_after.json',main),
                          ('Candidate66Sources_before.json',current66),('Candidate66Sources_after.json',current66)]:
        need(name in artifacts,'Module95StockSourceReceiptMissing')
        path=Path(artifacts[name]['path']).resolve();guards.reject_links(path)
        need(path.parent==report_path.parent and smoke.binding(path)==artifacts[name]
             and smoke.read(path)==expected,'Module95StockProtectedSourceBindingChanged')
    return {'receipt':smoke.binding(report_path),'installedEditor':smoke.binding(smoke.EDITOR),
            'editorProductVersion':EXACT_VERSION,'stockInstaller':value['verifiedInstaller']}


def verify_download_record(value,info):
    proof=value.get('installer',{});plan=value.get('normalInstallPlan',{})
    need(value.get('status')=='PASS_COMPLETE_OFFICIAL_INSTALLER95'
         and value.get('component')=='android' and value.get('trustedInstaller') is True
         and value.get('installerExecuted') is False
         and value.get('url')==info['url']
         and proof.get('filename')==info['filename'] and proof.get('bytes')==info['bytes']
         and proof.get('md5')==info['md5']
         and re.fullmatch('[0-9a-f]{64}',proof.get('sha256','')) is not None
         and proof.get('authenticode',{}).get('Status')=='Valid'
         and re.search('Unity Technologies',proof.get('authenticode',{}).get('SignerSubject',''),re.IGNORECASE)
         and plan.get('arguments')==['/S','/D='+str(TARGET)],
         'Module95VerifiedMatchingPublisherAndroidReceiptRequired')
    need(value.get('schemaVersion')==2 and value.get('helperSHA256')==COMPONENT_HELPER_SHA
         and value.get('officialHelperSHA256')==OFFICIAL_HELPER_SHA and value.get('metadataSHA256')==METADATA_SHA
         and value.get('protectedSourcesUnchanged') is True and value.get('sectionCount')==16
         and value.get('maxAttemptsPerSection')==16 and type(value.get('maxSeconds')) is int
         and 60<=value['maxSeconds']<=5400,'Module97FrozenComponentDownloadProofRequired')


def verified_module(report_path,guards):
    guards.reject_links(report_path);report_path=Path(report_path).resolve()
    need(report_path.name=='Report.json' and report_path.parent.parent==COMPONENT_PUBLIC.resolve()
         and re.fullmatch('[0-9a-f]{32}',report_path.parent.name) is not None,
         'Module97ExactComponentDownloadUUIDReceiptRequired')
    need(core.sha(COMPONENT_HELPER)==COMPONENT_HELPER_SHA and core.sha(Path(download.__file__))==OFFICIAL_HELPER_SHA
         and core.sha(download.METADATA)==METADATA_SHA,'Module97FrozenDownloadReadersChanged')
    value=smoke.read(report_path);info=download.component_info('android')
    verify_download_record(value,info)
    raw_installer=Path(value['normalInstallPlan']['executable']);guards.reject_links(raw_installer)
    installer=raw_installer.resolve()
    expected=(COMPONENT_PRIVATE/report_path.parent.name/info['filename']).resolve()
    need(installer==expected and installer.name==info['filename']
         and installer.is_file(),'Module95ExactIndependentOfficialAndroidInstallerRequired')
    # Real root execution rechecks complete publisher MD5, actual Unity signature
    # via a hidden bounded read-only observer, and full SHA256 before any install.
    actual=download.verified_file(installer,info)
    need(actual==value['installer'],'Module95OfficialModuleBytesOrSignatureChanged')
    return {'receipt':smoke.binding(report_path),'installer':core.bound(installer),
            'publisherMD5':info['md5'],'publisherSignature':actual['authenticode'],
            'officialReleaseMetadata':smoke.binding(download.METADATA),'url':info['url']}


def protected_core(guards):
    need(core.sha(Path(stock_core.__file__))==CORE_READER_SHA and core.sha(CORE_BASELINE)==CORE_BASELINE_SHA,
         'Module97FrozenStockCoreReaderOrBaselineChanged')
    files=stock_core.stock_paths(smoke.EDITOR)
    for path in files.values():guards.reject_links(path)
    stock_core.validate_runtime(files)
    result=stock_core.core_snapshot(files,guards)
    baseline=smoke.read(CORE_BASELINE)
    need(len(result)==790 and result==baseline['stockCoreFilesBefore']==baseline['stockCoreFilesAfter'],
         'Module97Actual790StockCoreFilesChanged')
    unity=smoke.EDITOR.parent/'Unity.dll';guards.reject_links(unity)
    need(unity.is_file(),'Module95StockCoreFileRequired')
    result[unity.relative_to(smoke.EDITOR.parent).as_posix()]=core.bound(unity)
    return result


def arm64_elf(path):
    with Path(path).open('rb') as stream:header=stream.read(20)
    need(len(header)==20 and header[:6]==b'\x7fELF\x02\x01'
         and int.from_bytes(header[18:20],'little')==183,'Module95ActualARM64ELFRequired')


def installed_android(guards):
    need(ANDROID.is_dir(),'Module95AndroidPlayerDirectoryMissing')
    required=['UnityEditor.Android.Extensions.dll','Unity.Android.Gradle.dll','modules.asset',
              'AndroidPlayerBuildProgram.exe','AndroidPlayerBuildProgram.Data.dll',
              'Variations/il2cpp/Release/Libs/arm64-v8a/libunity.so',
              'Variations/il2cpp/Release/Libs/arm64-v8a/libmain.so',
              'Variations/il2cpp/Development/Libs/arm64-v8a/libunity.so']
    for relative in required:
        path=ANDROID/relative;guards.reject_links(path)
        need(path.is_file(),'Module95ActualAndroidSupportPayloadMissing')
        if path.suffix=='.so':arm64_elf(path)
    need((ANDROID/'Tools/gradle').is_dir(),'Module95StockMatchingEmbeddedGradleRequired')
    files={}
    for directory,folders,names in os.walk(ANDROID,followlinks=False):
        directory=Path(directory);guards.reject_links(directory)
        for name in folders:guards.reject_links(directory/name)
        for name in sorted(names):
            path=directory/name;guards.reject_links(path)
            need(path.is_file(),'Module95RegularInstalledFilesRequired')
            files[path.relative_to(ANDROID).as_posix()]={'sha256':core.sha(path),'bytes':path.stat().st_size}
    need(set(required)<=set(files) and len(files)<=100000,'Module95InstalledPayloadInventoryInvalid')
    return {'root':str(ANDROID),'files':files,'fileCount':len(files),
            'bytes':sum(row['bytes'] for row in files.values()),
            'runtimeOptions':stock_core.validate_runtime(stock_core.stock_paths(smoke.EDITOR)),
            'runtimeOptionsSource':smoke.binding(stock_core.stock_paths(smoke.EDITOR)['runtimeconfig']),
            'sdkChildrenVerified':False,'scope':'Actual matching stock Android platform payload and static ARM64 ELF headers only; external SDK/JDK/NDK children, native loader/build and devices not accepted.'}


def install(module_report,editor_report,output,timeout):
    need(type(timeout) is int and 60<=timeout<=3600,'Module95BoundedInstallerTimeoutRequired')
    api,candidate,processes,jobs,guards=smoke.readers()
    need(not processes.unity_pids(),'Module95NoRunningEditorRequired')
    for path in (module_report,editor_report,TARGET,ANDROID,output):guards.reject_links(path)
    output=smoke.contained_output(output,'AndroidModuleInstallation')
    need(TARGET.is_dir() and not ANDROID.exists(),'Module95ExistingOrPartialAndroidPlayerPreserved')
    main,current66=smoke.protected_sources(api,candidate)
    stock_editor=installed_editor(editor_report,main,current66,guards)
    official=verified_module(module_report,guards);installer=Path(official['installer']['path'])
    before_core=protected_core(guards);command=installer_command(installer)
    output.mkdir(parents=True,exist_ok=False)
    api.write(output/'MainSources_before.json',main);api.write(output/'Candidate66Sources_before.json',current66)
    api.write(output/'StockCore_before.json',before_core)
    report={'schemaVersion':1,'status':'RUNNING_NORMAL_STOCK_ANDROID_MODULE_INSTALL95','startedUtc':api.utc(),
            'runnerSHA256':core.sha(Path(__file__)),'moduleLayoutRevision':97,'stockEditor':stock_editor,'verifiedModuleInstaller':official,
            'command':command,'target':str(TARGET),'androidAbsentBefore':True,'timeoutSeconds':timeout,
            'parentElevated':bool(ctypes.WinDLL('shell32').IsUserAnAdmin()),
            'scope':'Normal unmodified matching official Android support installer into the existing verified LTS Editor. /S and /D last; owned bounded process and normal UAC only. No SDK copy, Editor/build/device execution, cross-version platform/Gradle/Bee reuse, security bypass or project promotion. Vendor installer may perform normal documented registration/prerequisite actions.'}
    api.write(output/'Authorization.json',report)
    try:
        report['launch']=stock.launch_owned(command,output,timeout,api,jobs)
        launch=report['launch']
        if launch.get('outcome')=='RequiresNormalUAC':
            report.update(status='REQUIRES_NORMAL_UAC_STOCK_ANDROID_MODULE_INSTALL95',normalUacRequired=True,installerExecuted=False)
        else:
            need(launch.get('outcome')=='Completed' and launch.get('exitCode') in (0,3010)
                 and launch.get('ownedJobAssignedBeforeResume') is True,'Module95StockInstallerDidNotComplete')
            payload=installed_android(guards);api.write(output/'InstalledAndroidFiles.json',payload)
            report.update(status='PASS_NORMAL_STOCK_ANDROID_MODULE_INSTALL95',installedAndroid=smoke.binding(output/'InstalledAndroidFiles.json'),
                          installedFileCount=payload['fileCount'],installedBytes=payload['bytes'],
                          installerExecuted=True,normalUacRequired=False,rebootRequested=launch['exitCode']==3010,
                          externalSDKChildrenVerified=False,nativeAndroidBuildAccepted=False)
    except Exception as error:
        report.update(status='FAIL_NORMAL_STOCK_ANDROID_MODULE_INSTALL95',errorType=type(error).__name__,error=str(error))
    finally:
        try:
            after_main,after66=api.freeze(),candidate.candidate_sources(api)
            api.write(output/'MainSources_after.json',after_main);api.write(output/'Candidate66Sources_after.json',after66)
            after_core=protected_core(guards);api.write(output/'StockCore_after.json',after_core)
            report.update(mainInputsUnchanged=after_main==main,candidate66InputsUnchanged=after66==current66,
                          stockCoreUnchanged=after_core==before_core,
                          exactEditorVersionUnchanged=core.editor_product_version(smoke.EDITOR)==EXACT_VERSION,
                          moduleInstallerUnchanged=core.bound(installer)==official['installer'])
            need(all(report[name] for name in ('mainInputsUnchanged','candidate66InputsUnchanged','stockCoreUnchanged',
                                               'exactEditorVersionUnchanged','moduleInstallerUnchanged')),
                 'Module95ProtectedSourceCoreOrInstallerChanged')
        except Exception as error:
            report.update(status='FAIL_NORMAL_STOCK_ANDROID_MODULE_INSTALL95_INVARIANT',invariantErrorType=type(error).__name__,invariantError=str(error))
        report.update(androidExistsAfter=ANDROID.exists(),unityPidsAfter=processes.unity_pids(),finishedUtc=api.utc(),
                      artifacts=[smoke.binding(path) for path in sorted(output.iterdir()) if path.is_file() and path.name!='Authorization.json'])
        if report['unityPidsAfter']:report['status']='FAIL_NORMAL_STOCK_ANDROID_MODULE_INSTALL95_EDITOR_REMAINS'
        api.write(output/'Report.json',report)
        print(json.dumps({'status':report['status'],'report':(output/'Report.json').relative_to(ROOT).as_posix(),
                          'nativeAndroidBuildAccepted':False}),flush=True)
    return 0 if report['status']=='PASS_NORMAL_STOCK_ANDROID_MODULE_INSTALL95' else 2 if report['status']=='REQUIRES_NORMAL_UAC_STOCK_ANDROID_MODULE_INSTALL95' else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--verified-module-report',type=Path,required=True);parser.add_argument('--stock-editor-report',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--timeout',type=int,default=1200)
    args=parser.parse_args()
    if not args.execute or os.name!='nt':parser.error('Explicit root Windows normal stock module installation required')
    return install(args.verified_module_report,args.stock_editor_report,args.out,args.timeout)


if __name__=='__main__':raise SystemExit(main())
