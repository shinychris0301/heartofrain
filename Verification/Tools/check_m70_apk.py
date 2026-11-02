"""Audit M70 texture payloads and preserved portrait policy in the built APK."""
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def run():
    apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='Verification/Evidence/M70');args=parser.parse_args()
    out=ROOT/args.out;out.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256(apk.read_bytes()).hexdigest()
    contract=json.loads((ROOT/'Unity/Assets/HeartOfTheRain/M69/Data/M70_PowerupContract.json').read_text())
    rows=[]
    with zipfile.ZipFile(apk) as z:
        names=z.namelist()
        for e in contract['entries']:
            def payload(path):
                guid=re.search(r'^guid: ([0-9a-f]{32})',Path(str(ROOT/'Unity'/path)+'.meta').read_text(),re.M)[1]
                prefix='assets/bin/Data/'+guid
                return [n for n in names if n==prefix or n.startswith(prefix+'.')]
            runtime=payload(e['resourceTexture']);reference=payload(e['texture'])
            assert runtime, e['name']+' missing runtime payload'
            assert not reference, e['name']+' duplicate reference atlas packaged'
            rows.append({'name':e['name'],'runtimePayloads':runtime,'runtimePayloadBytes':sum(z.getinfo(n).file_size for n in runtime),'referencePayloads':reference})
    (out/'APK_Payloads.json').write_text(json.dumps({'status':'PASS_M70_APK_TEXTURE_PAYLOADS','apk_sha256':sha,'scope':'GUID-named compiled APK payload presence. Android runtime format and residency are tested separately.','textures':rows},indent=2)+'\n')
    aapt=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/build-tools/34.0.0/aapt.exe')
    manifest=subprocess.run([str(aapt),'dump','xmltree',str(apk),'AndroidManifest.xml'],check=True,capture_output=True,text=True).stdout
    (out/'APK_Manifest.txt').write_text(manifest)
    assert re.search(r'android:screenOrientation[^\n]*\(type 0x10\)0x1\b',manifest)
    assert re.search(r'android:appCategory[^\n]*\(type 0x10\)0x0\b',manifest)
    result={'status':'PASS_APK_PORTRAIT_MANIFEST','apk_sha256':sha,'primary_activity':'com.unity3d.player.UnityPlayerActivity','screenOrientation':'portrait (enum1)','appCategory':'game (enum0)','scope':'Compiled manifest inspected with bundled aapt; physical sensor/device behavior is separate.'}
    (out/'APK_Orientation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'PASS_M70_APK_AUDIT','runtimeSheets':len(rows),'duplicateReferenceSheets':0,'apk_sha256':sha}))

if __name__=='__main__':run()
