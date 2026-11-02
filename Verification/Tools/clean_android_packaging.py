"""Repack the pinned generated Android launcher; require identical game entries/signing."""
import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ANDROID=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer')

def run():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    project=(ROOT/'Unity/Library/Bee/Android/Prj/IL2CPP/Gradle').resolve()
    target=(project/'launcher/build').resolve()
    assert target.is_relative_to(project) and target.name=='build' and target.parent.name=='launcher'
    apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    before=ROOT/'.verification-cache'/out.name/'Unity_Incremental.apk';before.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(apk,before)
    java=ANDROID/'OpenJDK/bin/java.exe'
    with (out/'Gradle_Clean.log').open('w') as log:
        subprocess.run([str(java),'-classpath',str(ANDROID/'Tools/gradle/lib/gradle-launcher-7.5.1.jar'),'org.gradle.launcher.GradleMain','--no-daemon',':launcher:clean',':launcher:assembleDebug'],cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    built=target/'outputs/apk/debug/launcher-debug.apk'
    def entries(p):
        with zipfile.ZipFile(p) as z:return {i.filename:(i.CRC,i.file_size) for i in z.infolist() if not i.filename.startswith('META-INF/')}
    first,last=entries(before),entries(built);changed=sorted(k for k in first.keys()|last.keys() if first.get(k)!=last.get(k));assert not changed,changed
    def cert(p):
        v=subprocess.run([str(java),'-jar',str(ANDROID/'SDK/build-tools/34.0.0/lib/apksigner.jar'),'verify','--print-certs',str(p)],check=True,capture_output=True,text=True).stdout
        return next(s.split(': ',1)[1] for s in v.splitlines() if s.startswith('Signer #1 certificate SHA-256 digest:'))
    c=cert(before);assert cert(built)==c
    shutil.copyfile(built,apk)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result={'status':'PASS_CLEAN_GRADLE_APK_PACKAGING','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'beforeSHA256':sha(before),'afterSHA256':sha(apk),'beforeBytes':before.stat().st_size,'afterBytes':apk.stat().st_size,'removedBytes':before.stat().st_size-apk.stat().st_size,'unchangedNonSignatureEntries':len(last),'changedNonSignatureEntries':changed,'sameSignerCertificate':True,'signerCertificateSHA256':c,'scope':'Pinned generated launcher clean/assembleDebug after native Unity build. Identical nonsignature CRC/size entries and signer; no engine/SDK/game change.'}
    (out/'APK_Packaging.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':run()
