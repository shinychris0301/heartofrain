"""Standby filesystem-only SDK copy with uncached single-lstat link guards.

The frozen97 copy/hash/provenance routines are reused without global changes.
An earlier root-owned copy PID must be proved stopped. Existing destination
components are preserved, never resumed, overlaid, moved or removed.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import time

import SDKcopy97 as reference
import official_download95 as process_reader

REFERENCE_SHA='47748ff7ee2db75bbdf94818f17af559bc29d524472ea637294118df3b6ed75b'
PROCESS_READER_SHA='0dcf067e2e92f6b6e8c51e36a4ebeea802e44997541bc2c86fcfb0601a9de0fb'


class GuardProxy:
    """Same symlink/reparse/hardlink policy; one lstat per node/ancestor call.

    No ancestor cache exists. Missing descendants are allowed for fresh output,
    but every ancestor is still inspected. Other I/O errors propagate closed.
    Audit/inventory readers retain their unchanged own validation routines.
    """
    def __init__(self,delegate):self.delegate=delegate

    def reject_links(self,path):
        path=Path(path)
        for node in (path,*path.parents):
            try:info=node.lstat()
            except FileNotFoundError:continue
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                raise ValueError('Linked or reparse input refused')
            if stat.S_ISREG(info.st_mode) and info.st_nlink!=1:
                raise ValueError('Hard-linked input refused')

    def __getattr__(self,name):return getattr(self.delegate,name)


def verify_frozen_helpers():
    reference.need(reference.hash_file(Path(reference.__file__))==REFERENCE_SHA,
                   'SDKcopy97FastFrozenReferenceChanged')
    reference.need(reference.hash_file(Path(process_reader.__file__))==PROCESS_READER_SHA,
                   'SDKcopy97FastFrozenStoppedProcessReaderChanged')


def run(module_report,output,stopped_copy_pid,max_seconds=1800):
    R=reference
    R.need(type(max_seconds) is int and 60<=max_seconds<=3600,'SDKcopy97BoundedFilesystemDeadlineRequired')
    R.need(type(stopped_copy_pid) is int and stopped_copy_pid>0,'SDKcopy97FastStoppedOwnedCopyPIDRequired')
    verify_frozen_helpers()
    # Read-only Win32 process-state proof only. No kill, wait mutation, process
    # launch, global guard replacement, monkeypatch or compatibility layer.
    process_reader.stopped_pid(stopped_copy_pid)
    api,candidate,processes,_,old_guards=R.smoke.readers();guards=GuardProxy(old_guards)
    R.need(not processes.unity_pids(),'SDKcopy97NoRunningEditorRequired')
    for path in (R.SOURCE,R.DESTINATION,output,module_report):guards.reject_links(path)
    output=R.smoke.contained_output(output,'SDKCopy97Fast');output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();deadline=started+max_seconds
    record={'schemaVersion':1,'status':'RUNNING_EXACT_EXTERNAL_TOOLS_COPY97','startedUtc':api.utc(),
            'runnerSHA256':R.hash_file(Path(__file__)),'referenceCopyHelper':R.smoke.binding(Path(R.__file__)),
            'source':str(R.SOURCE),'destination':str(R.DESTINATION),'components':list(R.COMPONENTS),
            'stoppedPriorOwnedCopyPID':stopped_copy_pid,'guardOptimization':'One lstat per node and ancestor; no caching or omitted hashes.',
            'editorSDKInstallerOrDeviceProcessesLaunched':False,'editorPreferencesWritten':False,
            'readOnlySourceObservers':'Read-only prior-PID/process/version state and Git source inventories only.',
            'hubFlagsOrLicensesFabricated':False,'maxSeconds':max_seconds,
            'scope':'Standby exact filesystem copy using the frozen97 full pre/post hashes and source/version gates. '
                    'Only SDK/NDK/OpenJDK go to absent matching LTS destinations. Own LTS platform/Gradle/Bee, main/backend/candidate66 preserved. '
                    'No partial-copy overlay, process stop, API35 substitution, preferences/license fabrication or native/device acceptance.'}
    main=current66=backend=platform=core_before=authority=proof=None
    try:
        authority,provenance=R.load_authority(guards);record['provenance']=provenance
        proof=R.module_proof(module_report,guards);record['matchingModuleInstall']=proof['receipt']
        R.require_fresh_components(R.DESTINATION,guards)
        main,current66=R.smoke.protected_sources(api,candidate);backend=guards.audit_backend('196f606d')
        R.need(backend.get('unchanged') is True,'SDKcopy97BackendBaselineChanged')
        platform=R.tree_manifest(R.DESTINATION,guards,deadline,R.COMPONENTS)
        R.need(platform['files']==proof['files'],'SDKcopy97InstalledLTSPlatformChanged')
        core_before=R.module_install.protected_core(guards)
        R.need(core_before==proof['stockCore'],'SDKcopy97InstalledLTSCoreChangedSinceModuleInstall')
        for name,value in [('MainSources_before',main),('Candidate66Sources_before',current66),
                           ('BackendSources_before',backend),('LTSPlatform_before',platform),('LTSCore_before',core_before)]:
            api.write(output/(name+'.json'),value)
        record['sourceAuthority']=R.smoke.binding(R.INVENTORY)
        R.need(R.shutil.disk_usage(R.DESTINATION).free>=3296501326+1024**3,'SDKcopy97InsufficientSpaceWithOneGiBReserve')
        process_reader.stopped_pid(stopped_copy_pid);verify_frozen_helpers()
        api.write(output/'Authorization.json',record)
        copied=R.copy_components(R.SOURCE,R.DESTINATION,authority,guards,deadline)
        api.write(output/'CopiedFiles.json',{'source':str(R.SOURCE),'destination':str(R.DESTINATION),**copied})
        record.update(status='PASS_EXACT_MATCHING_EXTERNAL_TOOLS_COPY97_NOT_NATIVE_ACCEPTANCE',
                      copiedFileCount=len(copied['files']),copiedBytes=sum(row['bytes'] for row in copied['files'].values()),
                      sourceAndDestinationExactlyMatchAuthority=True,copiedInventory=R.smoke.binding(output/'CopiedFiles.json'))
    except Exception as error:
        record.update(status='FAIL_EXACT_EXTERNAL_TOOLS_COPY97',errorType=type(error).__name__,error=str(error),
                      partialNewDestinationsPreserved=True)
    finally:
        try:
            if main is not None:
                after_main,after66=R.smoke.protected_sources(api,candidate);after_backend=guards.audit_backend('196f606d')
                after_platform=R.tree_manifest(R.DESTINATION,guards,None,R.COMPONENTS)
                after_core=R.module_install.protected_core(guards)
                for name,value in [('MainSources_after',after_main),('Candidate66Sources_after',after66),
                                   ('BackendSources_after',after_backend),('LTSPlatform_after',after_platform),('LTSCore_after',after_core)]:
                    api.write(output/(name+'.json'),value)
                record.update(mainInputsUnchanged=main==after_main,candidate66InputsUnchanged=current66==after66,
                              backendSourcesUnchanged=backend==after_backend,ltsPlatformAndGradleUnchanged=platform==after_platform,
                              ltsCoreUnchanged=core_before==after_core)
                R.need(all(record[name] for name in ('mainInputsUnchanged','candidate66InputsUnchanged','backendSourcesUnchanged',
                                                     'ltsPlatformAndGradleUnchanged','ltsCoreUnchanged')),
                       'SDKcopy97ProtectedSourcesOrLTSPlatformChanged')
            if authority is not None:
                R.same_manifest(authority,R.external_manifest(R.SOURCE,guards))
                final_authority,_=R.load_authority(guards);R.same_manifest(authority,final_authority)
                record['sourceInventoryUnchangedAtExit']=True;record['provenanceBindingsUnchangedAtExit']=True
            if proof is not None:
                R.need(R.smoke.binding(Path(module_report).resolve())==proof['receipt']
                       and R.hash_file(Path(R.module_install.__file__))==R.MODULE_HELPER_SHA,
                       'SDKcopy97ModuleReceiptOrInstallerHelperChangedAtExit')
                record['matchingModuleReceiptAndHelperUnchangedAtExit']=True
            verify_frozen_helpers();record['referenceHelperUnchangedAtExit']=True
            record['unityPidsAfter']=processes.unity_pids()
            R.need(not record['unityPidsAfter'],'SDKcopy97EditorAppearedDuringCopy')
        except Exception as error:
            record.update(status='FAIL_EXACT_EXTERNAL_TOOLS_COPY97_INVARIANT',invariantErrorType=type(error).__name__,invariantError=str(error))
        record.update(finishedUtc=api.utc(),elapsedSeconds=round(time.monotonic()-started,6))
        api.write(output/'Report.json',record)
        print(json.dumps({'status':record['status'],'report':str(output/'Report.json'),'nativeBuildAccepted':False}),flush=True)
    return 0 if record['status']=='PASS_EXACT_MATCHING_EXTERNAL_TOOLS_COPY97_NOT_NATIVE_ACCEPTANCE' else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--module-install-report',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--stopped-copy-pid',type=int,required=True);parser.add_argument('--max-seconds',type=int,default=1800)
    args=parser.parse_args()
    if not args.execute or os.name!='nt':parser.error('Explicit root Windows standby filesystem copy required')
    return run(args.module_install_report,args.out,args.stopped_copy_pid,args.max_seconds)


if __name__=='__main__':raise SystemExit(main())
