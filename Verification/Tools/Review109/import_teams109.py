"""File-only R4 import: no Unity, provider, backend, network or test execution."""
from pathlib import Path
import hashlib,json,re,shutil,uuid
ROOT=Path(__file__).resolve().parents[3]
PKG=ROOT/'.verification-cache/Teams109/Package/Heart_of_the_Rain_Teams_Access_Assets_R4'
SRC=PKG/'Unity/Assets/HeartOfTheRain/App'
OUT=ROOT/'Verification/Evidence/Review109'
TARGET=ROOT/'Unity/Assets/HeartOfTheRain/App/TeamsAccess'
def require(ok,code):
    if not ok:raise ValueError(code)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def guid(s):return uuid.uuid5(uuid.NAMESPACE_URL,'hotr-teams109/'+s).hex
def put(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data)
def main():
    require(not TARGET.exists() and not TARGET.with_suffix('.meta').exists(),'PreserveExistingTeams109')
    files=sorted((SRC/'TeamsAccess').rglob('*'))+[SRC/'TeamsAccess.meta']
    files=[p for p in files if p.is_file()]
    existing={}
    for p in (ROOT/'Unity/Assets').rglob('*.meta'):
        found=re.findall(rb'(?m)^guid:\s*([0-9a-f]{32})\s*$',p.read_bytes());require(len(found)==1,'ExistingGuidMalformed109');existing[found[0].decode()]=p
    incoming={}
    for p in files:
        if p.suffix=='.meta':
            found=re.findall(rb'(?m)^guid:\s*([0-9a-f]{32})\s*$',p.read_bytes());require(len(found)==1,'PackageGuidMalformed109');key=found[0].decode();require(key not in existing and key not in incoming,'PackageGuidCollision109');incoming[key]=p
    require(len(incoming)==77,'Expected77PackageGuids109')
    retained=OUT/'RetainedSources'
    for rel in ('App/Teams/Runtime/TeamsAssets.cs','App/Teams/TeamsAssets.asset','App/OnlineSocial/Runtime/OnlineTeamsPage82.cs','App/OnlineSocial/Runtime/OnlineTeamsLayout82.cs','App/OnlineSocial/Runtime/SocialContracts82.cs','App/OnlineSocial/Runtime/SocialBackendClient82.cs','App/OnlineSocial/Runtime/SocialPageSession82.cs'):
        source=ROOT/'Unity/Assets/HeartOfTheRain'/rel;put(retained/rel,source.read_bytes())
    manifest=json.loads((PKG/'Data/ComponentManifest.json').read_text('utf-8-sig'));byid={v['id']:v for v in manifest};rows=[]
    for source in files:
        relative=source.relative_to(SRC);target=ROOT/'Unity/Assets/HeartOfTheRain/App'/relative;data=source.read_bytes()
        if source.suffix=='.meta' and source.name.endswith('.png.meta'):
            asset=byid[source.name[:-9]];detail=not any(asset.get('border',[0,0,0,0]))
            text=data.decode('utf-8-sig');text=text.replace('enableMipMap: 0','enableMipMap: '+str(int(detail))).replace('filterMode: 1','filterMode: '+str(2 if detail else 1))
            text=text.replace('  isReadable: 0','  isReadable: 0\n  streamingMipmaps: 0\n  ignoreMipmapLimit: 1')
            text=text.replace('  userData:', '  platformSettings:\n'+''.join('  - serializedVersion: 3\n    buildTarget: '+platform+'\n    maxTextureSize: 4096\n    resizeAlgorithm: 0\n    textureFormat: 4\n    textureCompression: 0\n    compressionQuality: 100\n    crunchedCompression: 0\n    allowsAlphaSplitting: 0\n    overridden: '+str(int(platform!='DefaultTexturePlatform'))+'\n' for platform in ('DefaultTexturePlatform','Android','iPhone','Standalone'))+'  userData:')
            data=text.encode('utf-8');rows.append(dict(id=asset['id'],path=target.relative_to(ROOT).as_posix(),mipmaps=detail,filter='Trilinear' if detail else 'Bilinear',border=asset.get('border'),sourceMetaSHA256=digest(source),importMetaSHA256=hashlib.sha256(data).hexdigest()))
        put(target,data)
    # Only actually rendered roles are referenced, not duplicate emblems,
    # pressed variants, the packaged navigation tray, or authoring masters.
    names=['TA_Background','TA_Panel_Cream','TA_Panel_Blue','TA_Panel_Inner','TA_Field','TA_Stat','TA_Tab_Track','TA_Tab_Selected','TA_Button_Blue','TA_Button_Green','TA_Button_Red','TA_Button_Disabled','TA_Badge_Cell','TA_Badge_Selected','TA_Close_Disc','TA_Check_Disc','TA_Icon_Close','TA_Icon_Check','TA_Icon_Search','TA_Icon_People','TA_Icon_Help','TA_Icon_Invite','TA_Stat_star','TA_Stat_up','TA_Stat_heart']+['TA_Badge_'+v for v in ('drop','lantern','well','sun','wave','crystal','book','oak','moon','cottage','banners','raincloud')]
    classguid=guid('TeamsAccessAssets109.cs');assetguid=guid('TeamsAccessAssets109.asset')
    header='%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n--- !u!114 &11400000\nMonoBehaviour:\n  m_ObjectHideFlags: 0\n  m_CorrespondingSourceObject: {fileID: 0}\n  m_PrefabInstance: {fileID: 0}\n  m_PrefabAsset: {fileID: 0}\n  m_GameObject: {fileID: 0}\n  m_Enabled: 1\n  m_EditorHideFlags: 0\n  m_Script: {fileID: 11500000, guid: '+classguid+', type: 3}\n  m_Name: Teams Access R4\n  m_EditorClassIdentifier:\n  sprites:\n'
    for name in names:
        meta=(SRC/'TeamsAccess/Art'/f'{name}.png.meta').read_text('utf-8');g=re.search(r'^guid: ([0-9a-f]{32})$',meta,re.M)[1];header+='  - id: '+name+'\n    sprite: {fileID: 21300000, guid: '+g+', type: 3}\n'
    header+='  slices:\n'
    for name in names:
        asset=byid[name]
        if any(asset.get('border',[0,0,0,0])):header+='  - id: '+name+'\n    proofScale: '+str(asset.get('proofBorderScale',.6))+'\n'
    put(TARGET/'TeamsAccessAssets109.asset',header.encode());put(TARGET/'TeamsAccessAssets109.asset.meta',('fileFormatVersion: 2\nguid: '+assetguid+'\nNativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 11400000\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n').encode())
    put(TARGET/'Runtime.meta',('fileFormatVersion: 2\nguid: '+guid('Runtime')+'\nfolderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n').encode())
    for name in ('TeamsAccessAssets109','TeamsAccessText109','TeamsAccessLayout109'):
        put(TARGET/'Runtime'/f'{name}.cs.meta',('fileFormatVersion: 2\nguid: '+guid(name+'.cs')+'\n').encode())
    strings=json.loads((PKG/'Data/Teams_Access_Strings.json').read_text('utf-8-sig'))['strings'];langs=('en','es','fr','de','ru')
    text='using System;\nusing System.Collections.Generic;\nusing HeartOfTheRain.App.Localization;\nusing HeartOfTheRain.App.OnlineSocial;\nnamespace HeartOfTheRain.App.TeamsAccess {\n public static class TeamsAccessText109 {\n  static readonly Dictionary<string,string[]> Copy=new Dictionary<string,string[]>(StringComparer.Ordinal) {\n'
    for key in strings['en']:text+='   {'+json.dumps(key)+',new[]{'+','.join(json.dumps(strings[l][key],ensure_ascii=False) for l in langs)+'}},\n'
    text+='  };\n  public static string T(string key){string[] values;return Copy.TryGetValue(key,out values)?values[GameLocale.ResolveStored(GameLocale.Current)]:OnlineTeamsText82.T(key);}\n }\n}\n'
    put(TARGET/'Runtime/TeamsAccessText109.cs',text.encode('utf-8'))
    path=ROOT/'Unity/Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset';before=path.read_bytes();ending='\r\n' if b'\r\n' in before else '\n';addition='  access: {fileID: 11400000, guid: '+assetguid+', type: 2}'+ending;path.write_bytes(before+addition.encode())
    put(OUT/'AssetImport109.json',(json.dumps(dict(status='FILE_IMPORT_PREPARED_NOT_UNITY_VERIFIED',packageGuids=77,pngs=69,referencedRoles=names,roleImports=rows,sharedNavigationImported=False,originalAssetMetasChanged=False,sourcePackage=str(PKG.relative_to(ROOT))),indent=2)+'\n').encode())
    print(json.dumps(dict(status='IMPORTED_FILES_NOT_UNITY_TESTED',files=len(files),art=69,guids=77,referencedSprites=len(names))))
if __name__=='__main__':main()
