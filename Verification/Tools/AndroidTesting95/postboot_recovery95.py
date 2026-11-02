"""Root-only read-only inspection and separately gated ordinary LD0 relaunch.

A changed boot is recorded as a new private selector, never written over the
old selector. The completed regression belongs only to its original boot. No
device command runs on import; no reboot, reconnect, reset, install or deletion.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import time

import accepted93_ld as A
import regression95 as R
import recover_regression95 as C

ROOT=A.ROOT
OUT=ROOT/'Verification/Evidence/AndroidTesting95/PostBootRecovery'
PRIVATE=ROOT/'.verification-cache/AndroidTesting95/PostBootRecovery'
CONTEXT_SHA='89df6dbb79a3394ca7f60a39c62a5d3e5e75877b4f1ccb6520d9c5e0b5549073'


def validate_selector(current, old):
    A.need(isinstance(current,dict) and set(current)==set(old)
           and all(current[key]==old[key] for key in old if key!='bootID')
           and old.get('index')==0 and old.get('package')==A.PACKAGE,
           'PostBoot95OriginalLDSerialIndexPackageToolsRequired')
    A.need(isinstance(current.get('bootID'),str) and A.GUID.fullmatch(current['bootID']) is not None
           and A.GUID.fullmatch(old.get('bootID','')) is not None
           and current['bootID']!=old['bootID'], 'PostBoot95DistinctValidCurrentBootRequired')


def agree_boot(console_boot, adb_boot, old):
    A.need(console_boot==adb_boot and A.GUID.fullmatch(console_boot) is not None,
           'PostBoot95CurrentConsoleAndADBBootMustMatch')
    current={**old,'bootID':console_boot}
    validate_selector(current,old)
    return current


def fresh_outputs(path):
    path=Path(path)
    private=PRIVATE/path.name
    for candidate in (path,private):
        for item in (candidate,*candidate.parents):
            if item.exists():
                A.need(not item.is_symlink() and not getattr(item.stat(),'st_file_attributes',0)&0x400,
                       'PostBoot95LinkedOutputRefused')
    path=path.resolve();private=private.resolve()
    A.need(path.parent==OUT.resolve() and private.parent==PRIVATE.resolve()
           and re.fullmatch('[0-9a-f]{32}',path.name) is not None
           and not path.exists() and not private.exists(),'PostBoot95FreshScopedUUIDOutputRequired')
    path.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
    return path,private


def host_context():
    A.need(A.sha(Path(C.__file__))==CONTEXT_SHA,'PostBoot95FrozenContextHelperChanged')
    context=C.host_context()
    old_path=C.verify_binding(context['original']['identity']['privateSelector'])
    A.need(old_path.resolve()==A.SELECTOR.resolve(),'PostBoot95ExactOriginalPrivateSelectorRequired')
    old=A.load_selector()
    A.need(A.sha(A.ADB)==context['original']['identity']['adbSHA256']
           and A.sha(A.CONSOLE)==context['original']['identity']['consoleSHA256'],
           'PostBoot95OriginalTransportBinaryChanged')
    context['oldSelector']=old
    return context


def capture_selector(context, private, step):
    old=context['oldSelector']
    step('readCurrentConsoleBoot')
    console_boot=A.command([A.CONSOLE,'adb','--index','0','--command',A.BOOT_COMMAND],30)[0].decode('ascii').strip()
    step('readCurrentSelectedADBBoot')
    adb_boot=A.command([A.ADB,'-s',old['serial'],'shell','cat','/proc/sys/kernel/random/boot_id'],30)[0].decode('ascii').strip()
    current=agree_boot(console_boot,adb_boot,old)
    destination=private/'Selector.json'
    A.write(destination,current)
    return destination


class Target(A.Target):
    """Same bounded transport, with honest separately bound post-boot identity."""
    def __init__(self,selector_path,context):
        self.selector_path=Path(selector_path).resolve()
        A.need(self.selector_path.parent.parent==PRIVATE.resolve()
               and self.selector_path.name=='Selector.json'
               and re.fullmatch('[0-9a-f]{32}',self.selector_path.parent.name) is not None,
               'PostBoot95ScopedPrivateSelectorRequired')
        for item in (self.selector_path,*self.selector_path.parents):
            if item.exists():
                A.need(not item.is_symlink() and not getattr(item.stat(),'st_file_attributes',0)&0x400,
                       'PostBoot95LinkedSelectorRefused')
        self.selector=A.read(self.selector_path)
        self.context=context
        validate_selector(self.selector,context['oldSelector'])
        self.deadline=time.monotonic()+600

    def identity(self):
        validate_selector(self.selector,self.context['oldSelector'])
        A.need(A.read(self.selector_path)==self.selector,'PostBoot95NewSelectorChanged')
        C.verify_binding(self.context['original']['identity']['privateSelector'])
        original=self.context['original']['identity']
        A.need(A.sha(A.ADB)==original['adbSHA256'] and A.sha(A.CONSOLE)==original['consoleSHA256'],
               'PostBoot95OriginalTransportBinaryChanged')
        try:
            with socket.create_connection(('127.0.0.1',5037),timeout=2):pass
        except OSError:raise ValueError('PostBoot95ExistingADBServerRequired') from None
        A.need(self.adb('get-state')=='device','PostBoot95AuthorizedEmulatorUnavailable')
        listing=A.command([A.CONSOLE,'list2'],20)[0].decode('utf-8','replace')
        rows=[line.split(',') for line in listing.splitlines() if line.startswith('0,')]
        A.need(len(rows)==1 and len(rows[0])>=7 and rows[0][4]=='1'
               and all(re.fullmatch('[1-9][0-9]*',rows[0][i]) for i in (5,6)),
               'PostBoot95LDIndexZeroMustBeRunning')
        console_boot=A.command([A.CONSOLE,'adb','--index','0','--command',A.BOOT_COMMAND],30)[0].decode('ascii').strip()
        adb_boot=self.adb('shell','cat','/proc/sys/kernel/random/boot_id')
        A.need(agree_boot(console_boot,adb_boot,self.context['oldSelector'])==self.selector,
               'PostBoot95FreshCurrentBootChanged')
        abis=self.adb('shell','getprop','ro.product.cpu.abilist').split(',')
        wide=self.adb('shell','getprop','ro.product.cpu.abilist64').split(',')
        api=self.adb('shell','getprop','ro.build.version.sdk')
        A.need(abis==original['advertisedAbis'] and wide==original['advertised64BitAbis']
               and 'arm64-v8a' in abis and 'arm64-v8a' in wide
               and api==str(original['androidApi']),'PostBoot95OriginalABIAndAndroidAPIRequired')
        return {'privateSelector':A.bound(self.selector_path),'previousPrivateSelector':original['privateSelector'],
                'index':0,'sameCurrentLDConsoleAndADBBoot':True,'bootChangedSinceOriginalRegression':True,
                'selectorSHA256':hashlib.sha256(self.selector['serial'].encode()).hexdigest(),
                'advertisedAbis':abis,'advertised64BitAbis':wide,'androidApi':int(api),
                'adbSHA256':A.sha(A.ADB),'consoleSHA256':A.sha(A.CONSOLE)}


def live_idle(target,context,step,expected_identity=None):
    step('currentPostBootIdentity')
    identity=target.identity()
    if expected_identity is not None:A.need(identity==expected_identity,'PostBoot95InspectedIdentityChanged')
    step('pendingMarkers')
    A.need(not R.markers(target),'PostBoot95ForeignOrPendingMarkersPreserved')
    step('allDurableProfilesAndPreferences')
    current=R.ordinary(target);R.same_ordinary(context['before'],current)
    step('installedPackageInventory')
    A.need(target.packages()==context['update']['packagesAfter'],'PostBoot95PackagesChanged')
    step('ownerPID')
    current_pid=R.pid(target)
    return identity,current,current_pid


def validate_inspection(value,context):
    A.need(value.get('status')=='PASS_READ_ONLY_ACCEPTED93_LD_POSTBOOT95_INSPECTION'
           and value.get('action')=='inspect' and value.get('runner')==A.bound(Path(__file__))
           and value.get('originalInvocation')==context['originalInvocation']
           and value.get('proof')==context['update']['proof']
           and value.get('ordinary')==context['before'] and value.get('markers')==[]
           and value.get('readOnlyDeviceCommands') is True
           and value.get('regressionExecutedOnCurrentBoot') is False,
           'PostBoot95CurrentBoundReadOnlyInspectionRequired')
    selector_path=C.verify_binding(value['identity']['privateSelector'])
    validate_selector(A.read(selector_path),context['oldSelector'])
    return selector_path


def finish(target,context,expected_identity,step):
    identity,current,current_pid=live_idle(target,context,step,expected_identity)
    step('preStopMarkers')
    A.need(not R.markers(target),'PostBoot95PendingMarkersPreservedNoStop')
    if current_pid:
        step('exactOwnerForceStop')
        target.adb('shell','am','force-stop',A.PACKAGE)
    step('stoppedOwnerPID')
    A.need(not R.pid(target),'PostBoot95OwnerDidNotStop')
    step('stoppedDurableData')
    R.same_ordinary(context['before'],R.ordinary(target))
    step('preLaunchMarkers')
    A.need(not R.markers(target),'PostBoot95PendingMarkersPreservedNoLaunch')
    step('ordinaryOwnerLaunch')
    normal_pid=R.launch(target)
    step('ordinaryObservation')
    time.sleep(8)
    step('finalDurableData')
    final=R.ordinary(target);R.same_ordinary(context['before'],final)
    step('finalMarkers')
    A.need(not R.markers(target),'PostBoot95FinalPendingMarkers')
    step('finalCurrentBootIdentity')
    A.need(target.identity()==identity,'PostBoot95CurrentBootChangedAtExit')
    step('finalPackageInventory')
    A.need(target.packages()==context['update']['packagesAfter'],'PostBoot95FinalPackagesChanged')
    return {'identity':identity,'ordinaryAfterRelaunch':final,'ordinaryDataUnchanged':True,'markers':[],
            'normalRelaunch':{'pid':int(normal_pid),'fixedObservationSeconds':8,'readinessOrPerformanceClaim':False}}


def run(action,output,inspection=None):
    output,private=fresh_outputs(output)
    record={'schemaVersion':1,'action':action,'startedUtc':A.utc(),'runner':A.bound(Path(__file__)),
            'status':'RUNNING_ACCEPTED93_LD_POSTBOOT95_RECOVERY','steps':[],
            'readOnlyDeviceCommands':action=='inspect','regressionExecutedOnCurrentBoot':False,
            'originalBlockedStatusRewritten':False,'scope':'Post-boot ordinary app/save preservation only. '
                    'Original1716-check regression belongs to its old boot; old BLOCKED receipt retained. '
                    'No Unity6, phone, performance, provider or production acceptance.'}
    def step(name):
        record['currentStage']=name;record['steps'].append({'stage':name,'utc':A.utc()})
        R.save(output/'Progress.json',record)
    try:
        step('originalImmutableEvidenceAndCurrentSource')
        context=host_context()
        record.update(originalInvocation=context['originalInvocation'],proof=context['update']['proof'],
                      originalNativeReport=context['original']['nativeReport'],
                      originalOrdinaryBefore=context['original']['ordinaryBefore'],
                      originalOrdinaryAfter=context['original']['ordinaryAfter'],
                      originalNativeCounts={key:context['native'][key] for key in ('checks','boards','actions','clips')})
        if action=='inspect':
            selector_path=capture_selector(context,private,step)
            target=Target(selector_path,context)
            identity,current,current_pid=live_idle(target,context,step)
            record.update(identity=identity,ordinary=current,markers=[],ownerPID=int(current_pid) if current_pid else None,
                          status='PASS_READ_ONLY_ACCEPTED93_LD_POSTBOOT95_INSPECTION')
        else:
            A.need(inspection is not None,'PostBoot95InspectionRequiredBeforeFinish')
            inspection=Path(inspection).resolve()
            A.need(inspection.parent.parent==OUT.resolve() and inspection.name=='Recovery.json',
                   'PostBoot95ScopedInspectionRequired')
            previous=A.read(inspection);selector_path=validate_inspection(previous,context)
            record['inspection']=A.bound(inspection)
            target=Target(selector_path,context)
            record.update(finish(target,context,previous['identity'],step))
            record['status']='PASS_ACCEPTED93_LD_POSTBOOT95_SEPARATE_PRESERVATION_RECOVERY'
        step('finalMainAndOriginalEvidenceProof')
        A.need(A.accepted_proof()==context['update']['proof'],'PostBoot95MainSourceChangedAtExit')
        A.need(A.bound(C.RUN/'Invocation.json')==context['originalInvocation'],
               'PostBoot95OriginalBlockedReceiptChanged')
        C.verify_binding(context['original']['identity']['privateSelector'])
        record['sourceProofsAndOriginalSelectorUnchanged']=True
    except Exception as error:
        record.update(status='BLOCKED_ACCEPTED93_LD_POSTBOOT95_RECOVERY',failure=A.safe(error),requiresOperatorCleanup=True)
    finally:
        record['finishedUtc']=A.utc();A.write(output/'Recovery.json',record)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('inspect','finish'));parser.add_argument('--execute',action='store_true')
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--inspection',type=Path)
    args=parser.parse_args()
    if not args.execute or os.name!='nt' or not args.out.is_absolute():
        parser.error('Explicit root Windows execution and fresh absolute scoped output required')
    result=run(args.action,args.out,args.inspection)
    print(json.dumps({'status':result['status'],'stage':result.get('currentStage'),'regressionExecutedOnCurrentBoot':False}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
