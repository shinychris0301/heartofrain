"""Prepare a private sealed126 diagnostic copy. Never builds, signs or installs."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid

ROOT=Path(__file__).resolve().parents[4]
TOOLS=Path(__file__).resolve().parent
SOURCE=Path('E:/.verification-cache/HOTR126/Sandbox01/Game')
PRIVATE=Path('E:/.verification-cache/HOTR127')
NATIVE=ROOT/'Verification/Evidence/Review126/Android/SignedBuild01/Native.json'
TEMPLATE=ROOT/'Verification/Tools/Review126/MonetizationBuild126.cs.template'
EDITOR=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe')
SIGNER='7257537a5b329cc5b018d93299d748404432c1b49f1b2388444ab843a4ba170d'
APK126='a5477b4e14e98b23a72c71fba1ee2e95a61a745b9df1d1034a8f8342aff62d3d'
SDK=SOURCE/'Library/PackageCache/ru.rustore.pay@268ab2fb33b6/Runtime'
SDK_FILES=('RuStorePayClient.cs','Model/PurchaseAvailabilityResult.cs','Callbacks/PurchaseAvailabilityListener.cs','Data/PaymentExceptionConverter.cs')

def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):value.update(block)
    return value.hexdigest()

def need(ok,code):
    if not ok:raise RuntimeError(code)

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as output:json.dump(value,output,indent=2);output.write('\n')

def inventory(project):
    result={}
    for name in ('Assets','Packages','ProjectSettings'):
        base=project/name
        need(base.is_dir() and not base.is_symlink(),'RealThreeInputDirectoriesRequired127')
        for path in sorted(base.rglob('*')):
            need(not path.is_symlink(),'SourceSymlinkRejected127')
            if path.is_file():result[path.relative_to(project).as_posix()]=sha(path)
    return result

def meta(relative,folder=False):
    guid=hashlib.sha256(('HOTR_PRIVATE_PAYMENT_DIAGNOSTIC127/'+relative).encode()).hexdigest()[:32]
    value='fileFormatVersion: 2\nguid: '+guid+'\n'
    return (value+('folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n' if folder else 'DefaultImporter:\n  externalObjects: {}\n')).encode()

def put(project,relative,data):
    target=project/relative;need(not target.exists(),'FreshDiagnosticAssetRequired127');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    Path(str(target)+'.meta').write_bytes(meta(relative))
    folder=target.parent
    while folder!=project/'Assets':
        fm=Path(str(folder)+'.meta')
        if not fm.exists():fm.write_bytes(meta(folder.relative_to(project).as_posix(),True))
        folder=folder.parent

def replace_once(data,pattern,replacement,code):
    result,count=re.subn(pattern,lambda unused:replacement,data)
    need(count==1,code);return result

def allowed_names():
    names={'NONE','Error','Exception','InvalidOperationException','ArgumentException','ArgumentNullException','IOException','UnauthorizedAccessException','NullReferenceException','AndroidJavaException','NotSupportedException','SecurityException','DirectoryNotFoundException','ObjectDisposedException','SocketTimeoutException','SSLHandshakeException','CertPathValidatorException','CertificateException','ConnectException','UnknownHostException','HttpException','RuntimeException','IllegalArgumentException','IllegalStateException'}
    roots=(SOURCE/'Assets/HeartOfTheRain/App',SDK,SOURCE/'Library/PackageCache/ru.rustore.core@985c393e8d98/Runtime')
    for base in roots:
        for path in base.rglob('*.cs'):
            text=path.read_text('utf-8-sig')
            # Only source literals qualify; arbitrary runtime data never does.
            names.update(re.findall(r'"([A-Za-z_][A-Za-z0-9_.]{0,95})"',text))
    need('CheckoutPaymentUnavailable' in names,'FrozenCheckoutErrorLiteralRequired127')
    need(not any(v in names for v in ('SECRET_SENSITIVE_12345','7f6e5d4c3b2a1098','private-subject')),'PrivacyProbeMustNotBeKnown127')
    return sorted(names)

def builder(require_layout=False):
    text=TEMPLATE.read_text('utf-8-sig')
    text=text.replace('MonetizationBuild126','PaymentDiagnosticBuild127').replace('HOTR_MONETIZATION126_','HOTR_PAYMENTDIAG127_')
    text=text.replace('PREPARED_MONETIZATION126','PREPARED_PAYMENT_DIAGNOSTIC127').replace('FAIL_MONETIZATION126','FAIL_PAYMENT_DIAGNOSTIC127')
    text=text.replace('PASS_COMBINED_MONETIZATION126_ANDROID_BUILD','PASS_PAYMENT_DIAGNOSTIC127_ANDROID_BUILD').replace('PASS_COMBINED_MONETIZATION126_PACKAGING','PASS_PAYMENT_DIAGNOSTIC127_PACKAGING')
    text=text.replace('E:/.verification-cache/HOTR126','E:/.verification-cache/HOTR127').replace('PlayerSettings.Android.bundleVersionCode==126','PlayerSettings.Android.bundleVersionCode==127')
    text=text.replace('Validate();\n   Check(r,Application.unityVersion', 'Validate();\n   Check(r,HeartOfTheRain.Verification.Diagnostics127.PaymentDiagnostics127.PrivacyChecks(),"ActualDiagnosticSerializerPrivacyChecks127");\n   Check(r,Application.unityVersion')
    # Keep existing SDK, combined advertising and isolated toolchain policies.
    need('AdvertisingBuild107.CombinedErrors126()' in text and 'SdkCheckoutBuild125.ActualToolchainErrors()' in text,'OriginalBuildBoundariesPreserved127')
    need('ActualDiagnosticSerializerPrivacyChecks127' in text,'NativePrivacyCheckRequired127')
    if require_layout:
        anchor='Check(r,HeartOfTheRain.Verification.Diagnostics127.PaymentDiagnostics127.PrivacyChecks(),"ActualDiagnosticSerializerPrivacyChecks127");'
        need(text.count(anchor)==1,'UniqueNativeDiagnosticPrivacyGateRequired127')
        text=text.replace(anchor,anchor+'\n   HeartOfTheRain.Verification127.SigninLayout127Verification.RequireAcceptedReport(Environment.GetEnvironmentVariable("HOTR_SIGNIN_LAYOUT127_REPORT"));\n   Check(r,true,"ActualSourceBoundSigninLayout127Accepted");')
    return text.encode('utf-8')

def prepare(tag):
    need(re.fullmatch(r'Pay[A-Za-z0-9_]{1,16}',tag or ''),'FreshSafePaymentTagRequired127')
    need(not os.environ.get('HOTR_RELEASE_SIGNING_PASSWORD'),'PreparationMustNotReceiveSigningPassword127')
    native=json.loads(NATIVE.read_text('utf-8'))
    need(native.get('status')=='PASS_COMBINED_MONETIZATION126_ANDROID_BUILD' and native.get('apkSHA256')==APK126 and native.get('signingCertificateSha256')==SIGNER,'AcceptedSealed126NativeReceiptRequired127')
    source_receipt=json.loads((SOURCE.parent/'Preparation126.json').read_text('utf-8'))
    for relative,digest in zip(source_receipt['paths'],source_receipt['sha256']):need(sha(SOURCE/relative)==digest,'Sealed126PinnedSourceChanged127')
    sdk_pins={name:sha(SDK/name) for name in SDK_FILES}
    sdk_client=(SDK/'RuStorePayClient.cs').read_text('utf-8-sig');model=(SDK/'Model/PurchaseAvailabilityResult.cs').read_text('utf-8-sig')
    need('PluginVersion = "11.1.0"' in sdk_client and 'GetPurchaseAvailability(Action<RuStoreError> onFailure, Action<PurchaseAvailabilityResult> onSuccess)' in sdk_client,'ActualPinnedAvailabilitySignatureRequired127')
    need('public bool isAvailable;' in model and 'public RuStoreError cause;' in model,'ActualPinnedAvailabilityCauseRequired127')
    before=inventory(SOURCE);main_before=inventory(ROOT/'Unity')
    custody_path=ROOT/'Release/Signing/manage_release_signing.py';spec=importlib.util.spec_from_file_location('diagnostic127_private_directory',custody_path);custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)
    need(not (PRIVATE/tag).exists(),'FreshDiagnosticParentRequired127');parent=custody.private_directory(PRIVATE/tag);project=parent/'Game'
    need(not project.exists(),'FreshDiagnosticProjectRequired127')
    for name in ('Assets','Packages','ProjectSettings'):shutil.copytree(SOURCE/name,project/name)
    settings=project/'ProjectSettings/ProjectSettings.asset';data=settings.read_bytes()
    data=replace_once(data,rb'(?m)^  AndroidBundleVersionCode: 126\r?$',b'  AndroidBundleVersionCode: 127','SealedVersion126Required127')
    match=re.findall(rb'(?m)^    Android: (HOTR_YANDEX_ADS[^\r\n]*)',data);need(len(match)==1 and b'HOTR_DIAGNOSTICS127' not in match[0],'OriginalSandboxDefinesRequired127')
    data=data.replace(b'    Android: '+match[0],b'    Android: '+match[0]+b';HOTR_DIAGNOSTICS127',1);settings.write_bytes(data)
    rsp=project/'Assets/csc.rsp';rsp_bytes=rsp.read_bytes();need(b'HOTR_DIAGNOSTICS127' not in rsp_bytes,'FreshDiagnosticDefineRequired127');rsp.write_bytes(rsp_bytes.rstrip()+b';HOTR_DIAGNOSTICS127\n')
    put(project,'Assets/Review127Diagnostics/Runtime/PaymentDiagnostics127.cs',(TOOLS/'PaymentDiagnostics127.cs').read_bytes())
    names=allowed_names();literal=',\n'.join(json.dumps(value) for value in names)
    generated='#if HOTR_DIAGNOSTICS127\nnamespace HeartOfTheRain.Verification.Diagnostics127 { internal static class PaymentDiagnosticNames127 { internal static readonly string[] Values=new[]{\n'+literal+'\n}; } }\n#endif\n'
    put(project,'Assets/Review127Diagnostics/Runtime/PaymentDiagnosticNames127.cs',generated.encode())
    put(project,'Assets/Review127Diagnostics/link.xml',b'<linker><assembly fullname="Assembly-CSharp"><type fullname="HeartOfTheRain.App.ShopCheckout86.ShopCheckoutHost86"><field name="flow" /></type></assembly></linker>\n')
    # Old private builder remains byte-identical but is never selected. The new
    # separately named builder uses the same provider/toolchain safety checks.
    put(project,'Assets/Review127Diagnostics/Editor/PaymentDiagnosticBuild127.cs',builder())
    release=json.loads((ROOT/'Release/Monetization126/release.sandbox.json').read_text('utf-8'));release['versionCode']=127
    need(release['packageName']=='com.heartoftherain.game' and release['consoleApplicationId']=='2063777840' and release['signingCertificateSha256']==SIGNER,'BoundPublicReleaseMetadataRequired127')
    write(parent/'Release127.json',release)
    current=inventory(project);original_changes={p:{'before':digest,'after':current.get(p)} for p,digest in before.items() if current.get(p)!=digest}
    need(set(original_changes)=={'ProjectSettings/ProjectSettings.asset','Assets/csc.rsp'},'OnlyDiagnosticDefinesAndVersionMayChange127')
    need(all(current[p]==digest for p,digest in before.items() if p.endswith('.meta')),'OriginalAssetGuidBytesChanged127')
    guid={}
    for p,digest in current.items():
        if not p.endswith('.meta') or not p.startswith('Assets/'):continue
        values=re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$',(project/p).read_bytes());need(len(values)==1,'ExactlyOneGuidRequired127');guid[p]=values[0].decode().lower()
    need(len(set(guid.values()))==len(guid),'UniqueDiagnosticGuidsRequired127')
    pins={p:h for p,h in current.items() if p.startswith('Assets/') and not p.endswith('.meta') and p!='Assets/Plugins/Android/AndroidManifest.xml'}
    need(max(map(lambda p:len(str(project/p)),current))<260,'ShortDiagnosticProjectRequired127')
    receipt={'version':1,'status':'PREPARED_PAYMENT_DIAGNOSTIC127','preparedUtc':datetime.now(timezone.utc).isoformat(),'sourceRoot':str(ROOT),'sourceProject':str(SOURCE),'project':str(project),'nonce':uuid.uuid4().hex,'unity':'6000.3.27f1','packageName':'com.heartoftherain.game','versionCode':127,'paths':list(pins),'sha256':list(pins.values()),'metaPaths':list(guid),'metaGuids':list(guid.values()),'inputs':current,'sourceInputs':before,'mainInputs':main_before,'sourceNativeSHA256':sha(NATIVE),'sourceApkSHA256':APK126,'expectedSignerSHA256':SIGNER,'diagnosticNames':len(names),'sdkAvailabilitySourceSHA256':sdk_pins,'sourceDelta':original_changes,'newPaths':sorted(set(current)-set(before)),'toolSHA256':sha(__file__),'harnessSHA256':sha(TOOLS/'PaymentDiagnostics127.cs'),'builderSHA256':sha(project/'Assets/Review127Diagnostics/Editor/PaymentDiagnosticBuild127.cs'),'releaseSHA256':sha(parent/'Release127.json'),'actualBuild':False,'signingAttempted':False,'sdkAvailabilityInvoked':False,'providerAcceptance':False,'scope':'Private same-package manual enum/boolean diagnostics only. No source repair, provider purchase, VK transition, device operation or production acceptance.'}
    write(parent/'Preparation127.json',receipt)
    need(inventory(SOURCE)==before,'Sealed126ChangedDuringPreparation127');need(inventory(ROOT/'Unity')==main_before,'MainChangedDuringPreparation127')
    plan={'version':1,'status':'PREPARED_NOT_EXECUTED','project':str(project),'preparationSHA256':sha(parent/'Preparation127.json'),'editor':str(EDITOR),'packageName':receipt['packageName'],'versionCode':127,'expectedSignerSHA256':SIGNER,'entryPackaging':'HeartOfTheRain.Verification.PaymentDiagnosticBuild127.RunPackaging','entryBuild':'HeartOfTheRain.Verification.PaymentDiagnosticBuild127.BuildSandbox','environmentReferences':{'HOTR_PAYMENTDIAG127_RECEIPT':str(parent/'Preparation127.json'),'HOTR_PAYMENTDIAG127_OUT':'<fresh private output directory>','HOTR_PAYMENTDIAG127_APK':str(project/'Builds/HeartOfTheRain_Diagnostic127.apk'),'HOTR_SDK125_PACKAGING_PROJECT':str(project),'HOTR_RUSTORE_RELEASE_CONFIG':str(parent/'Release127.json'),'HOTR_RELEASE_SIGNING_PASSWORD':'<Root-supplied child-process environment only>','HOTR_RELEASE_KEYSTORE':'<Root-supplied external protected keystore reference>','GRADLE_USER_HOME':'E:/G127Pay01'},'gradleCacheReuse':'Only read-copy E:/G126A/caches/modules-2/files-2.1 into a fresh owned cache. No wrappers/history/scripts/transforms/daemon/properties/signing data.','nativeRequiredChecks':['ActualDiagnosticSerializerPrivacyChecks127','exact SDK11.1/Core10.5/Yandex8.6 and stock Unity6000.3.27f1 tools','source pins and original GUIDs unchanged','version127 same package and same release certificate','APK postcheck with Review126/check_apk126.py plus explicit version127/diagnostic class checks'],'releaseSigningOwner':'Root only; preparer never retrieves/signs/executes credentials','executionPermittedByThisTool':False,'newGuestCreatedByOverlay':False,'diagnosticFile':'Application.persistentDataPath/PaymentDiagnostics127.json','manualActionsOnly':['Read local status','Query payment availability (one actual SDK call per explicit press, max20/process, no purchase or identity transition)']}
    write(parent/'RunPlan127.json',plan)
    return {'status':receipt['status'],'project':str(project),'receiptSHA256':sha(parent/'Preparation127.json'),'inputs':len(current),'guids':len(guid),'originalChanges':sorted(original_changes),'newPaths':len(receipt['newPaths']),'sdkAvailabilityInvoked':False,'actualBuild':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--tag',required=True);args=parser.parse_args();return prepare(args.tag)

if __name__=='__main__':
    try:print(json.dumps(main()))
    except Exception as failure:
        text=str(failure);print(json.dumps({'status':'BLOCKED_PAYMENT_DIAGNOSTIC127','code':text if re.fullmatch('[A-Za-z0-9_]{1,120}',text) else type(failure).__name__}));raise SystemExit(1)
