"""Guarded same-package109 upgrade and bounded physical UI observations.
Never clears/uninstalls/restores saves, fabricates social data or selects emulator.
"""
import argparse,hashlib,json,re,subprocess,sys,time,zlib,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Review98'))
import physical as base
PACKAGE,OWNER=base.PACKAGE,base.OWNER

class Phone109(base.Physical):
 def __init__(self,out,build):
  self.out=out;self.private=ROOT/'.verification-cache/Review109/Physical'/out.name;self.private.mkdir(parents=True,exist_ok=False);self.counter=0
  inv=json.loads((ROOT/'Verification/Evidence/Review109/Physical/Inventory02/Inventory109.json').read_text('utf-8'))
  self.serial=(ROOT/inv['privateEvidenceDirectory']/'selected_device.txt').read_text('ascii');self.device=dict(model=inv['model'],selectorSHA256=inv['serialSHA256'])
  if hashlib.sha256(self.serial.encode()).hexdigest()!=inv['serialSHA256']:raise ValueError('CurrentAuthorizedUsbSelectorRequired109')
  if not build.resolve().is_relative_to((ROOT/'Verification/Evidence/Review109/Native').resolve()):raise ValueError('ExactCurrentNativeBuildEvidenceRequired109')
  self.build=json.loads(build.read_text('utf-8-sig'));self.apk=Path(self.build['apk']);self.expected=self.build['apkSHA256'];self.base='/sdcard/Android/data/'+PACKAGE+'/files'
  if not self.apk.resolve().is_relative_to((ROOT/'.verification-cache/Review109/Candidates').resolve()):raise ValueError('ExactOwned109ApkRequired')
  native=json.loads((build.parent/'Invocation.json').read_text('utf-8'))
  if self.build.get('status')!='PASS_NATIVE_TEAMS109_BUILD_DEVELOPMENT' or self.build.get('packageName')!=PACKAGE or self.build.get('unity')!='6000.3.27f1' or self.build.get('errors') or not self.build.get('actualSdkBranchCompiled') or self.build.get('adsEnabled') or self.build.get('managedPayload') or self.build.get('scriptDebugging') or base.sha(self.apk)!=self.expected or native.get('status')!='PASS_NATIVE109_LTS_INVOCATION':raise ValueError('ExactCurrentSdkDevelopmentBuildRequired109')
  static=build.parent/'Static/Audit01/StaticApk109.json';audit=json.loads(static.read_text('utf-8'))
  if audit.get('status')!='PASS_STATIC_TEAMS109_APK' or audit.get('apkSHA256')!=self.expected or audit.get('nativeBuildSHA256')!=base.sha(build) or audit.get('invocationSHA256')!=base.sha(build.parent/'Invocation.json') or audit.get('signerCertificateSHA256')!='2f26ec88310ec9edfda3335fb22f5843a9bba45441f5378c14ea2ef0c04f6dca':raise ValueError('ExactSamePhoneSignerStaticPassRequired109')
  self.identity()
  if self.adb('shell','am','get-current-user')!='0':raise ValueError('ExactPhoneUserRequired109')
 def lock_state(self):
  policy=self.adb('shell','dumpsys','window','policy').split('KeyguardServiceDelegate',1)[-1];power=self.adb('shell','dumpsys','power');match=re.search(r'(?m)^\s*showing=(true|false)\s*$',policy)
  return dict(keyguardShowing=match.group(1)=='true' if match else None,awake='mWakefulness=Awake' in power)
 def guard(self):
  self.identity();state=self.lock_state()
  if state['keyguardShowing'] is not False or not state['awake']:raise ValueError('OwnerAwakeUnlockedPhoneRequired109')
 def idle(self,expected,require_unlocked=True):
  if require_unlocked:self.guard()
  else:self.identity() # Installation never dismisses or bypasses the keyguard.
  value=self.stable(PACKAGE);self.last_idle=value
  if value['installedSHA256']!=expected or value['activeAttempts'] or not value['profileSummaries']:raise ValueError('FreshExactIdlePhoneProfileRequired109')
  self.adb('shell','test','-e',self.base+'/ServerReview/configuration.json',check=False)
  if self.last_exit!=1 or self.last_error:raise ValueError('ManagedConfigurationRequiresSeparateAudit109')
  marker=self.adb('shell','find',self.base,'-maxdepth','1','-type','f','-name','HOTR_Run*',check=False)
  if self.last_exit or marker:raise ValueError('PreserveUnknownPhoneFixtureMarkers109')
  return value
 def capture(self,name):
  found=super().capture(name);data=(ROOT/found['path']).read_bytes();at=8;ended=False;size=None
  while at<len(data):
   n=struct.unpack_from('>I',data,at)[0];end=at+12+n
   if end>len(data):raise ValueError('TruncatedOsPng109')
   kind=data[at+4:at+8];body=data[at+8:at+8+n]
   if zlib.crc32(kind+body)&0xffffffff!=struct.unpack_from('>I',data,at+8+n)[0]:raise ValueError('OsPngCrcInvalid109')
   if kind==b'IHDR':size=struct.unpack_from('>II',body)
   at=end
   if kind==b'IEND':ended=at==len(data);break
  if not ended or size!=(720,1600):raise ValueError('ExactPhysicalOsFramebufferRequired109')
  found['width'],found['height']=size;return found

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--tag',required=True);p.add_argument('--build',required=True,type=Path);p.add_argument('action',choices=('upgrade','launch','capture','tap','swipe'));p.add_argument('--x',type=int);p.add_argument('--y',type=int);p.add_argument('--x2',type=int);p.add_argument('--y2',type=int);a=p.parse_args()
 if not a.execute or not re.fullmatch('[A-Za-z0-9_]{1,35}',a.tag):p.error('ExplicitFreshPhysical109Required')
 out=ROOT/'Verification/Evidence/Review109/Physical'/a.tag;out.mkdir(parents=True,exist_ok=False);r=dict(status='RUNNING_PHYSICAL109',action=a.action,utc=base.utc(),runner=base.bound(Path(__file__)),build=base.bound(a.build),captures=[],scope='One actual owner-authorized phone and same signed review98 package. No clear/uninstall, stale save restoration, fake membership, provider request or whole-game certification.')
 phone=None
 try:
  phone=Phone109(out,a.build);r['lockStateBefore']=phone.lock_state()
  if a.action!='upgrade':phone.guard()
  r['privateEvidenceDirectory']=phone.private.relative_to(ROOT).as_posix();r['ownerBefore']=phone.stable(OWNER)
  if a.action=='upgrade':
   inv=json.loads((ROOT/'Verification/Evidence/Review109/Physical/Inventory02/Inventory109.json').read_text('utf-8'));previous=next(v['inventory']['installedSHA256'] for v in inv['packages'] if v['package']==PACKAGE)
   before=phone.idle(previous,False);r['candidateBefore']=before;r['installWhileLockedAuthorized']=True
   # User may have progressed since Inventory02; this fresh state, not that old
   # snapshot, is the preservation authority. Never restore prior profile bytes.
   phone.adb('shell','am','force-stop',PACKAGE)
   stopped=phone.adb('shell','pidof',PACKAGE,check=False)
   r['stopObservation']=dict(utc=base.utc(),pidEmpty=not stopped,exitCode=phone.last_exit,stderrEmpty=not phone.last_error)
   if stopped or phone.last_exit!=1 or phone.last_error:raise ValueError('ExactCandidateProcessStopNotObserved109')
   if phone.idle(previous,False)!=before:raise ValueError('PhoneStateChangedBeforeReplacement109')
   stopped=phone.adb('shell','pidof',PACKAGE,check=False);r['immediatePreinstallProcessObservation']=dict(utc=base.utc(),pidEmpty=not stopped,exitCode=phone.last_exit,stderrEmpty=not phone.last_error)
   if stopped or phone.last_exit!=1 or phone.last_error or base.sha(phone.apk)!=phone.expected:raise ValueError('ExactStoppedProcessAndApkRequiredBeforeInstall109')
   reply=phone.adb('install','-r','-t',str(phone.apk),timeout=240)
   if 'Success' not in reply:raise ValueError('AndroidReplacementNotConfirmed109')
   after=phone.installed();r['candidateAfter']=after;strip=lambda v:{k:w for k,w in v.items() if k!='installedSHA256'}
   if strip(before)!=strip(after):raise ValueError('SavedPhoneDataChangedByReplacement109')
   r.update(status='PASS_SAME_SIGNER_SAVE_PRESERVING_UPGRADE109',sameSigner=True,candidateDataPreserved=True,keyguardDismissed=False,lockStateAfter=phone.lock_state())
  else:
   before=phone.idle(phone.expected);r['candidateBefore']=before
   if a.action=='launch':r['amStart']=phone.launch();time.sleep(12)
   if a.action in ('tap','swipe'):
    if not all(type(v)==int for v in (a.x,a.y)) or not 0<=a.x<720 or not 0<=a.y<1600:raise ValueError('BoundedPhysicalCoordinatesRequired109')
    phone.capture('Before_Input_OS')
    if a.action=='tap':phone.adb('shell','input','tap',str(a.x),str(a.y))
    else:
     if not all(type(v)==int for v in (a.x2,a.y2)) or not 0<=a.x2<720 or not 0<=a.y2<1600:raise ValueError('BoundedPhysicalSwipeRequired109')
     phone.adb('shell','input','swipe',str(a.x),str(a.y),str(a.x2),str(a.y2),'450')
    time.sleep(2)
   r['captures'].append(phone.capture('Actual_OS_'+a.tag));after=phone.idle(phone.expected);r['candidateAfter']=after
   if before!=after:raise ValueError('OrdinaryUiChangedSavedPhoneState109')
   r.update(status='RECORDED_PHYSICAL_UI109_REQUIRES_VISUAL_REVIEW',candidateDataPreserved=True)
  r['ownerAfter']=phone.stable(OWNER)
  if r['ownerBefore']!=r['ownerAfter']:raise ValueError('OriginalPackageStateChanged109')
  r['ownerStatePreserved']=True
 except Exception as e:
  r.update(status='STOPPED_PHYSICAL109',errorType=type(e).__name__,code=str(e) if re.fullmatch('[A-Za-z0-9]{1,120}',str(e)) else 'SeePrivatePhysicalOutput109')
  if phone and hasattr(phone,'last_idle'):r['candidateObservedAtGuard']=phone.last_idle
 finally:
  if phone and 'ownerBefore' in r:
   try:
    r['ownerAfter']=phone.stable(OWNER);r['ownerStatePreserved']=r['ownerBefore']==r['ownerAfter']
    if not r['ownerStatePreserved']:r['status']='FAIL_PHYSICAL109_OWNER_STATE_CHANGED'
   except Exception as e:r['ownerReadbackErrorType']=type(e).__name__;r['status']='FAIL_PHYSICAL109_OWNER_READBACK'
 if phone:r['privateEvidence']=[dict(path=v.relative_to(ROOT).as_posix(),sha256=base.sha(v),bytes=v.stat().st_size) for v in sorted(phone.private.iterdir()) if v.is_file()]
 r['finishedUtc']=base.utc();base.save(out/'Report.json',r);print(json.dumps(dict(status=r['status'],report=(out/'Report.json').relative_to(ROOT).as_posix())),flush=True)
 return 0 if r['status'].startswith(('PASS_','RECORDED_')) else 1
if __name__=='__main__':raise SystemExit(main())
