"""Prepare a fresh owned Teams109 same-phone-package LTS SDK candidate. Derived from sealed107 preparation; no import/build/device operation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
from prepare_yandex85_sdk import asset_entries, PACKAGE, PACKAGE_SHA256

LTS=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor')
BASE=ROOT/'.verification-cache/Review98/Game'
SYMBOLS='HOTR_YANDEX_ADS;APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED;APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED'
PROFILE_PACKAGE='com.heartoftherain.review98'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,code):
    if not ok:raise ValueError(code)
def plain(path):
    for p in (path,*path.parents):
        if p.exists():require(not p.is_symlink() and not getattr(p.stat(),'st_file_attributes',0)&0x400,'LinkedPathRejected107')
def tree(root):
    result={};seen=set();plain(root)
    for folder,names,files in os.walk(root,followlinks=False):
        for n in (*names,*files):plain(Path(folder)/n)
        for n in files:
            p=Path(folder)/n;key=p.relative_to(root).as_posix()
            require(key.lower() not in seen and p.stat().st_nlink==1,'SourceAliasRejected107');seen.add(key.lower());result[key]=sha(p)
    return result
def meta(path,folder=False):
    guid=uuid.uuid5(uuid.NAMESPACE_URL,'heart-rain-teams109/'+path).hex
    return ('fileFormatVersion: 2\nguid: '+guid+'\n'+('folderAsset: yes\nDefaultImporter:\n' if folder else 'DefaultImporter:\n')+'  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n').encode()
def prepare(tag,execute):
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,40}',tag or ''),'SafeFreshTagRequired107')
    require('m_EditorVersion: 2022.3.62f3' in (ROOT/'Unity/ProjectSettings/ProjectVersion.txt').read_text(),'MainEngineMustRemain2022')
    require('m_EditorVersion: 6000.3.27f1' in (BASE/'ProjectSettings/ProjectVersion.txt').read_text(),'ApprovedPrivateLtsRequired107')
    require(sha(PACKAGE)==PACKAGE_SHA256,'PinnedOfficialVendorRequired107')
    require(not (ROOT/'Unity/Assets/YandexMobileAds').exists() and not (ROOT/'Unity/Assets/AdRevenue').exists(),'PreserveMainSdkFree107')
    source={}
    for part in ('Assets','Packages','ProjectSettings'):
        source.update({part+'/'+k:v for k,v in tree(ROOT/'Unity'/part).items()})
    require(not any('/resources/hotr_server/managedstaging' in k.lower() and not k.endswith('.meta') for k in source),'SourceStagingPayloadRejected107')
    candidate=ROOT/'.verification-cache/Review109/Candidates'/tag;game=candidate/'Game';plain(candidate)
    require(not candidate.exists(),'PreserveExistingCandidate107')
    vendor=asset_entries(PACKAGE)
    tools=LTS/'Data/PlaybackEngines/AndroidPlayer'
    required=[tools/'Tools/GradleTemplates/mainTemplate.gradle',tools/'Tools/GradleTemplates/launcherTemplate.gradle',tools/'Tools/GradleTemplates/settingsTemplate.gradle',tools/'Tools/GradleTemplates/gradleTemplate.properties',tools/'Apk/UnityManifest.xml']
    require(all(p.is_file() for p in required),'StockLtsTemplatesRequired107')
    if not execute:return dict(status='READY_FOR_EXPLICIT_TEAMS109_PREPARATION',mainInputs=len(source),vendorSHA256=PACKAGE_SHA256,buildPerformed=False,networkContacted=False)
    candidate.mkdir(parents=True,exist_ok=False)
    (candidate/'PreparationStarted.json').write_text(json.dumps(dict(status='STARTED_TEAMS109_PREPARATION',project=str(game),sourceRoot=str(ROOT),vendorSHA256=PACKAGE_SHA256,mainSourceSHA256=source,buildPerformed=False,networkContacted=False),indent=2)+'\n',encoding='utf-8')
    copied={};provenance={};guids=0
    def write(relative,data,origin):
        target=game/relative;target.parent.mkdir(parents=True,exist_ok=True)
        require(not target.exists(),'CandidateCollision107');target.write_bytes(data);copied[relative]=sha(target);provenance[relative]=origin
    for relative,expected in sorted(source.items()):
        if not relative.startswith('Assets/'):continue
        src=ROOT/'Unity'/relative;data=src.read_bytes();origin='main'
        if relative.endswith('.meta') and (BASE/relative).is_file():
            old=(BASE/relative).read_bytes();guid=lambda b:re.findall(rb'(?m)^guid:\s*([a-fA-F0-9]{32})\s*$',b)
            require(len(guid(data))==1 and guid(data)==guid(old),'MigratedGuidMismatch107');data=old;origin='approvedLtsMigratedMeta';guids+=1
        write(relative,data,origin)
    # Retain only the technical transparent foreground referenced by the approved
    # private adaptive-icon settings, never historical101 test/helper sources.
    for relative in ('Assets/Review98Editor.meta','Assets/Review98Editor/TransparentIconForeground98.png','Assets/Review98Editor/TransparentIconForeground98.png.meta'):
        if relative not in copied:write(relative,(BASE/relative).read_bytes(),'approvedTechnicalIconForeground')
    for part in ('Packages','ProjectSettings'):
        for relative in tree(BASE/part):write(part+'/'+relative,(BASE/part/relative).read_bytes(),'approvedUnpromotedLtsSettings')
    settings=game/'ProjectSettings/ProjectSettings.asset';raw=settings.read_bytes()
    replacements={rb'(?m)^  companyName: [^\r\n]*':b'  companyName: HeartRainTeams109',
        rb'(?m)^    Android: com\.heartoftherain\.review98':b'    Android: '+PROFILE_PACKAGE.encode(),
        rb'(?m)^  AndroidBundleVersionCode: [^\r\n]*':b'  AndroidBundleVersionCode: 109',
        rb'(?m)^  androidUseCustomKeystore: [^\r\n]*':b'  androidUseCustomKeystore: 0',
        rb'(?m)^  scriptingDefineSymbols: \{\}':b'  scriptingDefineSymbols:\n    Android: '+SYMBOLS.encode()}
    for pattern,value in replacements.items():
        raw,n=re.subn(pattern,lambda _:value,raw);require(n==1,'IsolatedSettingShapeChanged107')
    for key in ('useCustomMainManifest','useCustomMainGradleTemplate','useCustomLauncherGradleManifest','useCustomGradlePropertiesTemplate','useCustomGradleSettingsTemplate'):
        raw,n=re.subn(rb'(?m)^  '+key.encode()+rb': [01]',b'  '+key.encode()+b': 1',raw);require(n==1,'IsolatedTemplateSettingMissing107')
    settings.write_bytes(raw);copied['ProjectSettings/ProjectSettings.asset']=sha(settings)
    for logical,guid,data,metadata in vendor:
        keep=logical.startswith('Assets/YandexMobileAds/') and not any(logical.startswith(p) for p in ('Assets/YandexMobileAds/Editor','Assets/YandexMobileAds/Inspector','Assets/YandexMobileAds/Platforms/iOS'))
        keep|=logical.startswith('Assets/AdRevenue/Runtime') and '/iOS' not in logical
        keep|=logical=='Assets/Plugins/Android/yandex-ads-unity-plugin.aar'
        if not keep:continue
        for suffix,value in (('',data),('.meta',metadata)):
            if value is not None:write(logical+suffix,value,'pinnedOfficialYandex860')
    require(not (game/'Assets/csc.rsp').exists(),'PreserveExistingCompilerResponse107')
    write('Assets/csc.rsp',('-define:'+SYMBOLS+'\n').encode(),'explicitPrivateAdsDefines107')
    templates=tools/'Tools/GradleTemplates'
    dependencies="    implementation('com.yandex.android:mobileads:8.6.0') { version { strictly '8.6.0' } }\n    implementation('io.appmetrica.analytics:analytics:8.6.0') { version { strictly '8.6.0' } }\n    implementation 'androidx.lifecycle:lifecycle-process:2.4.1'\n"
    for filename in ('mainTemplate.gradle','launcherTemplate.gradle','settingsTemplate.gradle','gradleTemplate.properties'):
        text=(templates/filename).read_text('utf-8')
        if filename=='mainTemplate.gradle':text=text.replace('**DEPS**',dependencies+'**DEPS**',1)
        if filename in ('mainTemplate.gradle','launcherTemplate.gradle'):text+='\ndependencyLocking { lockAllConfigurations() }\n'
        if filename=='settingsTemplate.gradle':text+='\n// Record the actual resolved build graph in this owned build-only candidate.\ngradle.startParameter.writeDependencyLocks = true\n'
        if filename=='gradleTemplate.properties':text+='\nandroid.useAndroidX=true\nandroid.enableJetifier=true\n'
        relative='Assets/Plugins/Android/'+filename
        write(relative,text.encode(),'stockLtsTemplateWithExplicitDeps107');write(relative+'.meta',meta(relative),'generatedPrivateTemplateMeta107')
    android='http://schemas.android.com/apk/res/android';ettools='http://schemas.android.com/tools';ET.register_namespace('android',android);ET.register_namespace('tools',ettools)
    manifest=ET.fromstring((tools/'Apk/UnityManifest.xml').read_bytes());application=manifest.find('application');application.set('{'+android+'}usesCleartextTraffic','false')
    for node in list(application):
        if node.tag=='activity' and node.get('{'+android+'}name')=='com.unity3d.player.UnityPlayerGameActivity':application.remove(node)
    ET.SubElement(application,'meta-data',{'{'+android+'}name':'com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION','{'+android+'}value':'false','{'+ettools+'}replace':'android:value'})
    for permission in ('android.permission.INTERNET','android.permission.ACCESS_FINE_LOCATION','android.permission.ACCESS_COARSE_LOCATION','android.permission.ACCESS_BACKGROUND_LOCATION','com.google.android.gms.permission.AD_ID'):
        values={'{'+android+'}name':permission}
        if permission!='android.permission.INTERNET':values['{'+ettools+'}node']='remove'
        manifest.insert(0,ET.Element('uses-permission',values))
    relative='Assets/Plugins/Android/AndroidManifest.xml';write(relative,ET.tostring(manifest,encoding='utf-8',xml_declaration=True),'stockLtsManifestWithExplicitPrivacy107');write(relative+'.meta',meta(relative),'generatedPrivateTemplateMeta107')
    # Explicit parent metadata prevents auto-generated GUIDs for new vendor roots.
    for parent in sorted({str(Path(p).parent).replace('\\','/') for p in copied if p.startswith('Assets/')},key=lambda v:v.count('/')):
        path=Path(parent)
        while len(path.parts)>1:
            relative=path.as_posix()+'.meta'
            if relative not in copied:write(relative,meta(path.as_posix(),True),'generatedPrivateFolderMeta107')
            path=path.parent
    # The prior107 guard remains byte-identical in main. Only this candidate
    # delegates to its own exact109 in-memory authority; all other guards run.
    helper='Assets/Review109Editor/Editor/TeamsBuild109.cs'
    write(helper,(ROOT/'Verification/Tools/Review109/TeamsBuild109.cs.template').read_bytes(),'privateOnlyTeams109Authority')
    write(helper+'.meta',meta(helper),'privateOnlyTeams109AuthorityMeta')
    write('Assets/Review109Editor.meta',meta('Assets/Review109Editor',True),'privateOnlyTeams109AuthorityFolder')
    write('Assets/Review109Editor/Editor.meta',meta('Assets/Review109Editor/Editor',True),'privateOnlyTeams109AuthorityEditorFolder')
    guard='Assets/HeartOfTheRain/App/Advertising/Editor/AdvertisingBuild107.cs'
    guard_path=game/guard;guard_before=guard_path.read_bytes()
    old=b'internal static void Guard(BuildReport report){var errors='
    new=b'internal static void Guard(BuildReport report){if(HeartOfTheRain.Verification.TeamsBuild109.Guard(report))return;var errors='
    require(guard_before.count(old)==1,'ExactPrivateGuardDelegationRequired109')
    guard_path.write_bytes(guard_before.replace(old,new));copied[guard]=sha(guard_path);provenance[guard]='explicitPrivateOnly109Delegation'
    frozen={p:h for p,h in copied.items() if p.startswith('Assets/') and not p.endswith('.meta')}
    receipt=dict(version=1,status='PREPARED_TEAMS109',sourceRoot=str(ROOT),project=str(game),nonce=uuid.uuid4().hex,unity='6000.3.27f1',packageName=PROFILE_PACKAGE,
        vendorSHA256=PACKAGE_SHA256,paths=list(frozen),sha256=list(frozen.values()),mainSourceSHA256=source,copiedSHA256=copied,provenance=provenance,
        private107GuardDelegation=dict(path=guard,mainSHA256=sha(ROOT/'Unity'/guard),candidateSHA256=sha(guard_path),mainUnchanged=True),
        retainedMigratedMetaGuids=guids,templateSourceSHA256={str(p.relative_to(LTS)):sha(p) for p in required},
        privateSettingsSHA256=sha(settings),buildPerformed=False,networkContacted=False,
        scope='Fresh109 same-phone-package LTS candidate with pinnedSDK, disabledads and no managedpayload. Main2022/107 authority and historical101/107 candidates remain unchanged. No app/SDK/device operation by preparation.')
    (candidate/'Preparation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    require(all(sha(ROOT/'Unity'/p)==h for p,h in source.items()),'MainChangedDuringPreparation107')
    return dict(status=receipt['status'],project=str(game.relative_to(ROOT)),receipt=str((candidate/'Preparation.json').relative_to(ROOT)),copied=len(copied),buildPerformed=False,networkContacted=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--tag',required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    try:print(json.dumps(prepare(args.tag,args.execute)))
    except Exception as error:print(json.dumps(dict(status='BLOCKED_TEAMS109_PREPARATION',code=str(error) if re.fullmatch('[A-Za-z0-9]{1,100}',str(error)) else type(error).__name__)));raise SystemExit(1)
