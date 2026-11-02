"""Prepare a fresh standalone real-SDK DEMO fixture. No build/device/provider action."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, re, shutil, sys, uuid
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'.verification-cache/Review98/Game'
LTS=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor')
PRIVATE=Path('E:/.verification-cache/HOTR127')
PACKAGE='com.heartoftherain.ads127demo'
SYMBOLS='HOTR_YANDEX_ADS;HOTR_YANDEX_ADS_ISOLATED_FIXTURE;APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED;APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(ok,code):
    if not ok:raise ValueError(code)
def plain(path):
    for p in (Path(path),*Path(path).parents):
        if p.exists():need(not p.is_symlink() and not getattr(p.stat(),'st_file_attributes',0)&0x400,'PlainLocalPathRequired127')
def meta(path,folder=False):
    return ('fileFormatVersion: 2\nguid: '+uuid.uuid5(uuid.NAMESPACE_URL,'hotr-ad-demo127/'+path).hex+'\n'+
        ('folderAsset: yes\nDefaultImporter:\n' if folder else 'DefaultImporter:\n')+'  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n').encode()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for d in ('Assets','Packages','ProjectSettings')
            for p in sorted((root/d).rglob('*')) if p.is_file()}

def prepare(tag):
    need(re.fullmatch(r'[A-Za-z0-9_-]{1,24}',tag or ''),'SafeUniqueTagRequired127')
    parent=PRIVATE/tag;game=parent/'Game';plain(parent);need(not parent.exists(),'FreshPrivateProjectRequired127')
    need('2022.3.62f3' in (ROOT/'Unity/ProjectSettings/ProjectVersion.txt').read_text(),'PreserveMain2022Baseline127')
    need('6000.3.27f1' in (BASE/'ProjectSettings/ProjectVersion.txt').read_text(),'ApprovedIsolatedLtsRequired127')
    entry=ROOT/'Verification/Tools/Ads85/prepare_yandex85_sdk.py'
    spec=importlib.util.spec_from_file_location('vendor127',entry);vendor=importlib.util.module_from_spec(spec);spec.loader.exec_module(vendor)
    need(sha(vendor.PACKAGE)==vendor.PACKAGE_SHA256,'ExactOfficialYandex860PackageRequired127')
    original=inventory(ROOT/'Unity');parent.mkdir(parents=True)
    (parent/'PreparationStarted.json').write_text(json.dumps({'status':'PREPARING_PRIVATE_AD_DEMO127','mainInputs':original,'deviceTouched':False,'providerContacted':False},indent=2)+'\n')
    copied={};source_bindings={};provenance={}
    def write(rel,data,origin):
        dst=game/rel;dst.parent.mkdir(parents=True,exist_ok=True);need(not dst.exists(),'PrivateFileCollision127');dst.write_bytes(data);copied[rel]=sha(dst);provenance[rel]=origin
    def source(rel):
        src=ROOT/'Unity'/rel;need(sha(src)==original[rel],'MainChangedDuringCopy127');write(rel,src.read_bytes(),'actualMainRuntimeUnchanged');source_bindings[rel]=original[rel]
    # Exact full runtime type dependencies, including the real context/session
    # types. Editor/review probes and the unused executable replay worker are
    # excluded. Only our clinical fixture scene will be instantiated.
    selected=[]
    # The original model deliberately calls these exact development partials
    # under UNITY_EDITOR || DEVELOPMENT_BUILD. They have no startup hooks.
    development_partials={'Assets/HeartOfTheRain/Verification/Model77Control78.cs','Assets/HeartOfTheRain/Verification/Snapshot78Control79.cs'}
    for path in sorted((ROOT/'Unity/Assets').rglob('*.cs')):
        rel=path.relative_to(ROOT/'Unity').as_posix()
        if any(part in ('Editor','Verification','ServerVerification','Review98Editor') for part in Path(rel).parts) and rel not in development_partials:continue
        selected.append(rel);source(rel);source(rel+'.meta')
    identity='Assets/HeartOfTheRain/App/OnlineIdentity/Plugins/Android/HeartOfTheRainIdentity82.androidlib'
    for path in sorted((ROOT/'Unity'/identity).rglob('*')):
        if path.is_file():source(path.relative_to(ROOT/'Unity').as_posix())
    for d in ('Packages','ProjectSettings'):
        for p in sorted((BASE/d).rglob('*')):
            if p.is_file():write(p.relative_to(BASE).as_posix(),p.read_bytes(),'approvedPrivateLtsSettings')
    settings=game/'ProjectSettings/ProjectSettings.asset';raw=settings.read_bytes()
    patterns={rb'(?m)^  companyName: [^\r\n]*':b'  companyName: HeartRainDiagnostics',
        rb'(?m)^  productName: [^\r\n]*':b'  productName: Heart Rain Demo Ads 127',
        rb'(?m)^    Android: com\.heartoftherain\.review98':b'    Android: '+PACKAGE.encode(),
        rb'(?m)^  AndroidBundleVersionCode: [^\r\n]*':b'  AndroidBundleVersionCode: 127',
        rb'(?m)^  androidUseCustomKeystore: [^\r\n]*':b'  androidUseCustomKeystore: 0',
        rb'(?m)^  scriptingDefineSymbols: \{\}':b'  scriptingDefineSymbols:\n    Android: '+SYMBOLS.encode()}
    for pattern,value in patterns.items():raw,n=re.subn(pattern,lambda _:value,raw);need(n==1,'ExpectedLtsSettingShape127')
    for key in ('useCustomMainManifest','useCustomMainGradleTemplate','useCustomLauncherGradleManifest','useCustomGradlePropertiesTemplate','useCustomGradleSettingsTemplate'):
        raw,n=re.subn(rb'(?m)^  '+key.encode()+rb': [01]',b'  '+key.encode()+b': 1',raw);need(n==1,'ExpectedLtsTemplateSetting127')
    settings.write_bytes(raw);copied['ProjectSettings/ProjectSettings.asset']=sha(settings)
    vendor_pins={}
    for logical,guid,data,metadata in vendor.asset_entries(vendor.PACKAGE):
        keep=logical.startswith('Assets/YandexMobileAds/') and not any(logical.startswith(p) for p in ('Assets/YandexMobileAds/Editor','Assets/YandexMobileAds/Inspector','Assets/YandexMobileAds/Platforms/iOS'))
        keep|=logical.startswith('Assets/AdRevenue/Runtime') and '/iOS' not in logical
        keep|=logical=='Assets/Plugins/Android/yandex-ads-unity-plugin.aar'
        if keep:
            for suffix,value in (('',data),('.meta',metadata)):
                if value is not None:write(logical+suffix,value,'officialPinnedYandex860');vendor_pins[logical+suffix]=copied[logical+suffix]
    write('Assets/csc.rsp',('-define:'+SYMBOLS+'\n').encode(),'explicitPrivateDemoAndPrivacyDefines')
    tools=LTS/'Data/PlaybackEngines/AndroidPlayer';templates=tools/'Tools/GradleTemplates'
    dependencies="    implementation('com.yandex.android:mobileads:8.6.0') { version { strictly '8.6.0' } }\n    implementation('io.appmetrica.analytics:analytics:8.6.0') { version { strictly '8.6.0' } }\n    implementation 'androidx.lifecycle:lifecycle-process:2.4.1'\n"
    for name in ('mainTemplate.gradle','launcherTemplate.gradle','settingsTemplate.gradle','gradleTemplate.properties'):
        text=(templates/name).read_text()
        if name=='mainTemplate.gradle':need(text.count('**DEPS**')==1,'StockDependencyMarker127');text=text.replace('**DEPS**',dependencies+'**DEPS**')
        if name in ('mainTemplate.gradle','launcherTemplate.gradle'):text+='\ndependencyLocking { lockAllConfigurations() }\n'
        if name=='settingsTemplate.gradle':text+='\ngradle.startParameter.writeDependencyLocks = true\n'
        if name=='gradleTemplate.properties':text+='\nandroid.useAndroidX=true\nandroid.enableJetifier=true\n'
        rel='Assets/Plugins/Android/'+name;write(rel,text.encode(),'stockApprovedLtsWithPinnedDependencies');write(rel+'.meta',meta(rel),'generatedFixtureMeta')
    android='http://schemas.android.com/apk/res/android';xtools='http://schemas.android.com/tools';ET.register_namespace('android',android);ET.register_namespace('tools',xtools)
    manifest=ET.fromstring((tools/'Apk/UnityManifest.xml').read_bytes());app=manifest.find('application');app.set('{'+android+'}usesCleartextTraffic','false')
    for node in list(app):
        if node.tag=='activity' and node.get('{'+android+'}name')=='com.unity3d.player.UnityPlayerGameActivity':app.remove(node)
    ET.SubElement(app,'meta-data',{'{'+android+'}name':'com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION','{'+android+'}value':'false','{'+xtools+'}replace':'android:value'})
    for permission in ('android.permission.INTERNET','android.permission.ACCESS_FINE_LOCATION','android.permission.ACCESS_COARSE_LOCATION','android.permission.ACCESS_BACKGROUND_LOCATION','com.google.android.gms.permission.AD_ID'):
        values={'{'+android+'}name':permission}
        if permission!='android.permission.INTERNET':values['{'+xtools+'}node']='remove'
        manifest.insert(0,ET.Element('uses-permission',values))
    rel='Assets/Plugins/Android/AndroidManifest.xml';write(rel,ET.tostring(manifest,encoding='utf-8',xml_declaration=True),'stockLtsManifestWithStrictPrivacy');write(rel+'.meta',meta(rel),'generatedFixtureMeta')
    for name,rel in [('AdsDemo127.cs','Assets/Fixture127/AdsDemo127.cs'),('AdsDemoBuild127.cs','Assets/Fixture127/Editor/AdsDemoBuild127.cs')]:
        write(rel,(HERE/name).read_bytes(),'reviewedClinicalDemoFixture127');write(rel+'.meta',meta(rel),'generatedFixtureMeta')
    # Preserve every original parent-folder metadata byte whenever it exists.
    for rel in list(copied):
        path=Path(rel).parent
        while len(path.parts)>1:
            key=path.as_posix()+'.meta'
            if key not in copied:
                if key in original:source(key)
                else:write(key,meta(path.as_posix(),True),'generatedFixtureFolderMeta')
            path=path.parent
    need(max(len(str(game/p)) for p in copied)<260,'ShortWindowsProjectPath127')
    need(inventory(ROOT/'Unity')==original,'MainUnchangedDuringPreparation127')
    record={'version':1,'status':'PREPARED_REAL_SDK_AD_DEMO127_NOT_BUILT','project':str(game),'sourceRoot':str(ROOT),
        'packageName':PACKAGE,'unity':'6000.3.27f1','demoUnit':'demo-rewarded-yandex','origin':'https://api.novamind-it.ru',
        'symbols':SYMBOLS,'mainInputs':original,'copiedSHA256':copied,'sourceBindings':source_bindings,'vendorPins':vendor_pins,
        'assetPaths':list(copied),'assetSHA256':list(copied.values()),
        'provenance':provenance,'actualRuntimeCSharpFiles':len(selected),'officialVendorPackageSHA256':vendor.PACKAGE_SHA256,
        'harnessSHA256':sha(HERE/'AdsDemo127.cs'),'builderSHA256':sha(HERE/'AdsDemoBuild127.cs'),'preparerSHA256':sha(__file__),
        'buildPerformed':False,'providerContacted':False,'deviceTouched':False,'backendEdited':False,
        'scope':'Separate minimal diagnostic scene with actual full runtime type dependencies, no main art/scenes/resources/profile imported. Exact existing auth/adflow/journal; no scripted provider success or seed/grant endpoint. Debug Development fixture only.'}
    receipt=parent/'Preparation127.json';receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return {'status':record['status'],'project':str(game),'receipt':str(receipt),'receiptSHA256':sha(receipt),'runtimeCs':len(selected),'files':len(copied)}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True)
    try:print(json.dumps(prepare(parser.parse_args().tag)))
    except Exception as error:print(json.dumps({'status':'BLOCKED_AD_DEMO_PREPARATION127','errorType':type(error).__name__}));raise
