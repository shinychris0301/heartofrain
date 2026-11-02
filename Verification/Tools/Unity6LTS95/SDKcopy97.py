"""Root-only exact filesystem copy of three matching official external tools.

Requires the actual matching LTS Android module install PASS. Copies only SDK,
NDK and OpenJDK to absent embedded destinations; never copies platform/Gradle,
executes an SDK/Editor/device command, fabricates licenses or edits preferences.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import time

import smoke95 as smoke
import core_loader95 as core
import module_install97 as module_install

ROOT,EVIDENCE=smoke.ROOT,smoke.EVIDENCE
SOURCE=Path('E:/HeartRainUnity6_94/6000.6.6f1/Editor/Data/PlaybackEngines/AndroidPlayer')
DESTINATION=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
COMPONENTS=('SDK','NDK','OpenJDK')
INVENTORY=EVIDENCE/'Research/EmbeddedReuseSet01/SourceInventory.json.gz'
PROVENANCE=EVIDENCE/'Research/EmbeddedReuseSet01/Report.json'
SUPPLEMENT=EVIDENCE/'Research/EmbeddedReuseSupplementSet03/Report.json'
SOURCE_INSTALL=ROOT/'Verification/Evidence/Unity6Migration94/Environment/Installed/Report.json'
SOURCE_MODULES=SOURCE.parents[3]/'modules.json'
PINS={INVENTORY:'4c6ef97ad265e1426c9e7054d0318a1278a275de425e991614d56601e90baffd',
      PROVENANCE:'89a80318d7e3d9c092572e7e9e6d20b19dc7e31729e774f985bb10ab0149a60b',
      SUPPLEMENT:'0dc2a69c6bd3f7dbad9643baa3168ba5a9336cfe9ff259ac148c45604237bd30',
      SOURCE_INSTALL:'6050c0028e0daa563e37706f242b9e999cb7359be177757e87d633f6e01510c2',
      SOURCE_MODULES:'0bf2e3bed168e12dcb931e798a6a73e491388d14459331c91cba8e2f0ceff670'}
MODULE_HELPER_SHA='76ccbb54e4412a15cc7695fa51baaa08cc5f2a3a72610f939b6b509b03188c71'
EXPECTED_COUNTS={'SDK':(36975,695937282),'NDK':(7935,2361056613),'OpenJDK':(421,239507431)}
EXTERNAL_IDS={'android-open-jdk-17.0.18+8','android-sdk-ndk-tools','android-ndk-r27c','cmake-3.22.1',
              'android-sdk-build-tools-36.0.0','android-sdk-platform-tools-37.0.1','android-sdk-platforms-34',
              'android-sdk-platforms-36','android-sdk-platforms-37.0','android-sdk-command-line-tools-16.0'}


def need(value,code):smoke.need(value,code)


def hash_file(path,deadline=None):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            need(deadline is None or time.monotonic()<deadline,'SDKcopy97FilesystemDeadline')
            value.update(block)
    return value.hexdigest()


def safe_relative(relative):
    need(isinstance(relative,str) and relative and '\\' not in relative and ':' not in relative
         and '\x00' not in relative,'SDKcopy97UnsafeRelativePath')
    parts=PurePosixPath(relative).parts
    need(len(parts)>=2 and parts[0] in COMPONENTS and str(PurePosixPath(relative))==relative
         and not PurePosixPath(relative).is_absolute() and all(part not in ('.','..') for part in parts),
         'SDKcopy97OnlyThreeExternalComponentPathsAllowed')
    return relative


def inventory_maps(value):
    need(value.get('components')==list(COMPONENTS),'SDKcopy97ExactThreeComponentInventoryRequired')
    files={};seen=set()
    for row in value['files']:
        path=safe_relative(row['path']);folded=path.casefold()
        need(folded not in seen and type(row.get('bytes')) is int and row['bytes']>=0
             and re.fullmatch('[0-9a-f]{64}',row.get('sha256','')) is not None,
             'SDKcopy97InvalidOrDuplicateInventoryFile')
        seen.add(folded);files[path]={'bytes':row['bytes'],'sha256':row['sha256']}
    directories=set();directory_keys=set()
    for relative in value['directories']:
        path=safe_relative(relative);folded=path.casefold()
        need(folded not in seen and folded not in directory_keys,
             'SDKcopy97DuplicateOrConflictingInventoryDirectory')
        directories.add(path);directory_keys.add(folded)
    for path in (*files,*directories):
        for ancestor in PurePosixPath(path).parents:
            if len(ancestor.parts)>=2:
                need(ancestor.as_posix() in directories,'SDKcopy97InventoryParentDirectoryMissing')
    return {'files':files,'directories':sorted(directories)}


def counts(files):
    return {name:(sum(path.startswith(name+'/') for path in files),
                  sum(row['bytes'] for path,row in files.items() if path.startswith(name+'/')))
            for name in COMPONENTS}


def load_authority(guards):
    for path,digest in PINS.items():
        guards.reject_links(path);need(hash_file(path)==digest,'SDKcopy97FrozenProvenanceChanged')
    need(INVENTORY.stat().st_size<=3*1024*1024,'SDKcopy97CompressedInventoryTooLarge')
    with gzip.open(INVENTORY,'rb') as stream:raw=stream.read(20*1024*1024+1)
    need(len(raw)<=20*1024*1024 and hashlib.sha256(raw).hexdigest()==
         '9109bca8a47820a770048825790983592cc36deff9fa617d458d673ef245dcf5',
         'SDKcopy97UncompressedInventoryChanged')
    value=json.loads(raw);authority=inventory_maps(value)
    need(value.get('source')==str(SOURCE) and len(authority['files'])==45331
         and counts(authority['files'])==EXPECTED_COUNTS,'SDKcopy97Pinned45331FileInventoryRequired')
    provenance=smoke.read(PROVENANCE);supplement=smoke.read(SUPPLEMENT);installed=smoke.read(SOURCE_INSTALL)
    rows=supplement['installedVersusLTSMetadataComparisons']
    need(supplement.get('status')=='PASS_TEN_EXTERNAL_INSTALLED_METADATA_MATCHES95_COPY_PLAN_ONLY'
         and len(rows)==10 and {row['id'] for row in rows}==EXTERNAL_IDS
         and all(row.get('canonicalMetadataFieldsMatchLTS') is True and row.get('selectedInstalled') is True for row in rows)
         and supplement.get('sourceInventorySHA256')==PINS[INVENTORY]
         and provenance.get('inventorySHA256')==PINS[INVENTORY]
         and installed.get('status')=='PASS_PORTABLE_UNITY6_ANDROID_TOOLCHAIN94_ONLY'
         and installed.get('installedModulesMetadataSHA256')==PINS[SOURCE_MODULES],
         'SDKcopy97ExactTenOfficialComponentOverlapRequired')
    return authority,{'bindings':[smoke.binding(path) for path in PINS],
                      'matchedExternalModuleIds':sorted(EXTERNAL_IDS),'sourceFileCount':45331,'sourceBytes':3296501326,
                      'api35Absent':True,'fullLTSHubModuleParity':False,
                      'provenanceLimit':provenance['provenanceLimit']}


def tree_manifest(root,guards,deadline=None,excluded=()):
    root=Path(root);guards.reject_links(root);need(root.is_dir(),'SDKcopy97TreeRootRequired')
    files={};directories=[]
    for parent,folders,names in os.walk(root,followlinks=False):
        parent=Path(parent);guards.reject_links(parent)
        if parent==root:folders[:]=[name for name in folders if name not in excluded]
        folders.sort();names.sort()
        for name in folders:
            path=parent/name;guards.reject_links(path)
            directories.append(path.relative_to(root).as_posix())
        for name in names:
            path=parent/name;guards.reject_links(path);need(path.is_file(),'SDKcopy97RegularFilesRequired')
            files[path.relative_to(root).as_posix()]={'bytes':path.stat().st_size,'sha256':hash_file(path,deadline)}
    return {'files':files,'directories':sorted(directories)}


def external_manifest(root,guards,deadline=None):
    files={};directories=[]
    for component in COMPONENTS:
        current=tree_manifest(Path(root)/component,guards,deadline)
        files.update({component+'/'+path:row for path,row in current['files'].items()})
        directories.extend(component+'/'+relative for relative in current['directories'])
    return {'files':files,'directories':sorted(directories)}


def same_manifest(expected,actual):
    need(actual==expected,'SDKcopy97ExactSourceOrDestinationInventoryMismatch')


def require_fresh_components(destination,guards):
    guards.reject_links(destination);need(Path(destination).is_dir(),'SDKcopy97InstalledAndroidRootRequired')
    for name in COMPONENTS:
        path=Path(destination)/name;guards.reject_links(path)
        need(not path.exists(),'SDKcopy97ExistingOrPartialComponentPreserved')


def copy_components(source,destination,authority,guards,deadline=None):
    # All destination absence and complete source hashes are checked before even
    # the first new component directory is made. Failed partial copies remain.
    require_fresh_components(destination,guards)
    same_manifest(authority,external_manifest(source,guards,deadline))
    for component in COMPONENTS:
        target_root=Path(destination)/component
        guards.reject_links(target_root);need(not target_root.exists(),'SDKcopy97ExistingOrPartialComponentPreserved')
        target_root.mkdir(exist_ok=False)
        prefix=component+'/'
        directories=[path[len(prefix):] for path in authority['directories'] if path.startswith(prefix)]
        for relative in sorted(directories,key=lambda value:(len(PurePosixPath(value).parts),value)):
            path=target_root/relative;guards.reject_links(path);path.mkdir(exist_ok=False)
        for relative,expected in sorted(authority['files'].items()):
            if not relative.startswith(prefix):continue
            need(deadline is None or time.monotonic()<deadline,'SDKcopy97FilesystemDeadline')
            origin=Path(source)/relative;target=Path(destination)/relative
            guards.reject_links(origin);guards.reject_links(target)
            before=origin.stat();need(before.st_size==expected['bytes'],'SDKcopy97SourceSizeChangedBeforeCopy')
            digest=hashlib.sha256();total=0
            with origin.open('rb') as reader,target.open('xb') as writer:
                for block in iter(lambda:reader.read(1024*1024),b''):
                    need(deadline is None or time.monotonic()<deadline,'SDKcopy97FilesystemDeadline')
                    writer.write(block);digest.update(block);total+=len(block)
            after=origin.stat();guards.reject_links(origin)
            need(total==expected['bytes'] and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
                 and digest.hexdigest()==expected['sha256'] and hash_file(target,deadline)==expected['sha256'],
                 'SDKcopy97CopiedBytesOrSourceChanged')
            shutil.copystat(origin,target,follow_symlinks=False)
    same_manifest(authority,external_manifest(source,guards,deadline))
    copied=external_manifest(destination,guards,deadline);same_manifest(authority,copied)
    return copied


def module_proof(path,guards):
    path=Path(path).resolve();guards.reject_links(path)
    need(path.is_relative_to(EVIDENCE/'AndroidModuleInstallation') and path.name=='Report.json',
         'SDKcopy97ScopedActualModuleInstallReceiptRequired')
    value=smoke.read(path)
    validate_module_record(value)
    need(hash_file(Path(module_install.__file__))==MODULE_HELPER_SHA,'SDKcopy97FrozenModuleHelperChanged')
    inventory_path=Path(value['installedAndroid']['path']).resolve();guards.reject_links(inventory_path)
    need(inventory_path.parent==path.parent and smoke.binding(inventory_path)==value['installedAndroid'],
         'SDKcopy97InstalledModuleInventoryBindingChanged')
    inventory=smoke.read(inventory_path)
    need(inventory.get('root')==str(DESTINATION)
         and inventory.get('fileCount')==len(inventory['files'])
         and smoke.binding(smoke.EDITOR)==value['stockEditor']['installedEditor']
         and module_install.core.editor_product_version(smoke.EDITOR)==module_install.EXACT_VERSION,
         'SDKcopy97ExactLTSModuleRootOrEditorVersionRequired')
    cores=[row for row in value.get('artifacts',[]) if Path(row['path']).name=='StockCore_after.json']
    need(len(cores)==1,'SDKcopy97InstalledCoreAfterReceiptRequired')
    core_path=Path(cores[0]['path']).resolve();guards.reject_links(core_path)
    need(core_path.parent==path.parent and smoke.binding(core_path)==cores[0],
         'SDKcopy97InstalledCoreAfterBindingChanged')
    return {'receipt':smoke.binding(path),'installedAndroid':value['installedAndroid'],'files':inventory['files'],
            'stockCore':smoke.read(core_path),'stockCoreBinding':cores[0]}


def validate_module_record(value):
    need(value.get('runnerSHA256')==MODULE_HELPER_SHA and value.get('moduleLayoutRevision')==97
         and value.get('status')=='PASS_NORMAL_STOCK_ANDROID_MODULE_INSTALL95'
         and value.get('target')==str(module_install.TARGET) and value.get('installerExecuted') is True
         and value.get('normalUacRequired') is False and value.get('unityPidsAfter')==[]
         and all(value.get(name) is True for name in ('mainInputsUnchanged','candidate66InputsUnchanged',
                 'stockCoreUnchanged','exactEditorVersionUnchanged','moduleInstallerUnchanged')),
         'SDKcopy97ActualMatchingAndroidModuleInstallPassRequired')


def run(module_report,output,max_seconds=1800):
    need(type(max_seconds) is int and 60<=max_seconds<=3600,'SDKcopy97BoundedFilesystemDeadlineRequired')
    api,candidate,processes,_,guards=smoke.readers()
    need(not processes.unity_pids(),'SDKcopy97NoRunningEditorRequired')
    for path in (SOURCE,DESTINATION,output,module_report):guards.reject_links(path)
    output=smoke.contained_output(output,'SDKCopy97')
    output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();deadline=started+max_seconds
    record={'schemaVersion':1,'status':'RUNNING_EXACT_EXTERNAL_TOOLS_COPY97','startedUtc':api.utc(),
            'runnerSHA256':hash_file(Path(__file__)),'source':str(SOURCE),'destination':str(DESTINATION),
            'components':list(COMPONENTS),'editorSDKInstallerOrDeviceProcessesLaunched':False,'editorPreferencesWritten':False,
            'readOnlySourceObservers':'Git source inventory and process/version metadata only; no native build or tool execution.',
            'hubFlagsOrLicensesFabricated':False,'maxSeconds':max_seconds,
            'scope':'Exact filesystem equality copy of three observed matching official external tool folders only. '
                    'Own LTS platform/engine/Gradle/Bee preserved. API35 absent; not full Hub module parity, '
                    'license acceptance, SDK execution, native build, app/backend/device or production acceptance.'}
    main=current66=backend=platform=core_before=authority=proof=None
    try:
        authority,provenance=load_authority(guards);record['provenance']=provenance
        proof=module_proof(module_report,guards);record['matchingModuleInstall']=proof['receipt']
        require_fresh_components(DESTINATION,guards)
        main,current66=smoke.protected_sources(api,candidate);backend=guards.audit_backend('196f606d')
        need(backend.get('unchanged') is True,'SDKcopy97BackendBaselineChanged')
        platform=tree_manifest(DESTINATION,guards,deadline,COMPONENTS)
        need(platform['files']==proof['files'],'SDKcopy97InstalledLTSPlatformChanged')
        core_before=module_install.protected_core(guards)
        need(core_before==proof['stockCore'],'SDKcopy97InstalledLTSCoreChangedSinceModuleInstall')
        for name,value in [('MainSources_before',main),('Candidate66Sources_before',current66),
                           ('BackendSources_before',backend),('LTSPlatform_before',platform),('LTSCore_before',core_before)]:
            api.write(output/(name+'.json'),value)
        record['sourceAuthority']=smoke.binding(INVENTORY)
        need(shutil.disk_usage(DESTINATION).free>=3296501326+1024**3,'SDKcopy97InsufficientSpaceWithOneGiBReserve')
        api.write(output/'Authorization.json',record)
        copied=copy_components(SOURCE,DESTINATION,authority,guards,deadline)
        api.write(output/'CopiedFiles.json',{'source':str(SOURCE),'destination':str(DESTINATION),**copied})
        record.update(status='PASS_EXACT_MATCHING_EXTERNAL_TOOLS_COPY97_NOT_NATIVE_ACCEPTANCE',
                      copiedFileCount=len(copied['files']),copiedBytes=sum(row['bytes'] for row in copied['files'].values()),
                      sourceAndDestinationExactlyMatchAuthority=True,copiedInventory=smoke.binding(output/'CopiedFiles.json'))
    except Exception as error:
        record.update(status='FAIL_EXACT_EXTERNAL_TOOLS_COPY97',errorType=type(error).__name__,error=str(error),
                      partialNewDestinationsPreserved=True)
    finally:
        try:
            if main is not None:
                after_main,after66=smoke.protected_sources(api,candidate);after_backend=guards.audit_backend('196f606d')
                after_platform=tree_manifest(DESTINATION,guards,None,COMPONENTS)
                after_core=module_install.protected_core(guards)
                for name,value in [('MainSources_after',after_main),('Candidate66Sources_after',after66),
                                   ('BackendSources_after',after_backend),('LTSPlatform_after',after_platform),('LTSCore_after',after_core)]:
                    api.write(output/(name+'.json'),value)
                record.update(mainInputsUnchanged=main==after_main,candidate66InputsUnchanged=current66==after66,
                              backendSourcesUnchanged=backend==after_backend,ltsPlatformAndGradleUnchanged=platform==after_platform,
                              ltsCoreUnchanged=core_before==after_core)
                need(all(record[name] for name in ('mainInputsUnchanged','candidate66InputsUnchanged','backendSourcesUnchanged',
                                                   'ltsPlatformAndGradleUnchanged','ltsCoreUnchanged')),
                     'SDKcopy97ProtectedSourcesOrLTSPlatformChanged')
            if authority is not None:
                same_manifest(authority,external_manifest(SOURCE,guards))
                final_authority,_=load_authority(guards);same_manifest(authority,final_authority)
                record['sourceInventoryUnchangedAtExit']=True
                record['provenanceBindingsUnchangedAtExit']=True
            if proof is not None:
                need(smoke.binding(Path(module_report).resolve())==proof['receipt']
                     and hash_file(Path(module_install.__file__))==MODULE_HELPER_SHA,
                     'SDKcopy97ModuleReceiptOrInstallerHelperChangedAtExit')
                record['matchingModuleReceiptAndHelperUnchangedAtExit']=True
            record['unityPidsAfter']=processes.unity_pids()
            need(not record['unityPidsAfter'],'SDKcopy97EditorAppearedDuringCopy')
        except Exception as error:
            record.update(status='FAIL_EXACT_EXTERNAL_TOOLS_COPY97_INVARIANT',invariantErrorType=type(error).__name__,invariantError=str(error))
        record.update(finishedUtc=api.utc(),elapsedSeconds=round(time.monotonic()-started,6))
        api.write(output/'Report.json',record)
        print(json.dumps({'status':record['status'],'report':str(output/'Report.json'),'nativeBuildAccepted':False}),flush=True)
    return 0 if record['status']=='PASS_EXACT_MATCHING_EXTERNAL_TOOLS_COPY97_NOT_NATIVE_ACCEPTANCE' else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--module-install-report',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--max-seconds',type=int,default=1800);args=parser.parse_args()
    if not args.execute or os.name!='nt':parser.error('Explicit root Windows filesystem copy required')
    return run(args.module_install_report,args.out,args.max_seconds)


if __name__=='__main__':raise SystemExit(main())
