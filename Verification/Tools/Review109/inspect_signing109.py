"""Read-only signer binding for the exact APK freshly observed on the phone."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    evidence=ROOT/'Verification/Evidence/Review109/Physical/Inventory02'
    private=ROOT/'.verification-cache/Review109/Physical/Inventory02'
    inventory=json.loads((evidence/'Inventory109.json').read_text('utf-8'))
    matches=[v for v in inventory['packages'] if v['package']=='com.heartoftherain.review98' and v.get('activeBaseApk')]
    if len(matches)!=1:raise ValueError('ExactInstalledReview98Required109')
    apk=ROOT/'Unity/Builds/Review101/HeartOfTheRain_Review101_Android_Test.apk'
    if sha(apk)!=matches[0]['inventory']['installedSHA256']:raise ValueError('ExactCurrentApkBytesRequired109')
    android=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
    with (private/'ApkSigner109.out').open('xb') as stdout,(private/'ApkSigner109.err').open('xb') as stderr:
        result=subprocess.run([str(android/'OpenJDK/bin/java.exe'),'-jar',str(android/'SDK/build-tools/36.0.0/lib/apksigner.jar'),'verify','--print-certs',str(apk)],stdout=stdout,stderr=stderr,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    text=(private/'ApkSigner109.out').read_text('utf-8','replace');certs=re.findall(r'Signer #\d+ certificate SHA-256 digest: ([a-f0-9]{64})',text)
    if result.returncode or len(certs)!=1:raise ValueError('SingleValidExistingSignerRequired109')
    report=dict(status='PASS_EXACT_INSTALLED_APK_SIGNER109',package='com.heartoftherain.review98',apk=apk.relative_to(ROOT).as_posix(),apkSHA256=sha(apk),signerCertificateSHA256=certs[0],basis='Fresh installed APK SHA equals this exact locally signature-verified artifact. No device mutation or signing-key access.',inventorySHA256=sha(evidence/'Inventory109.json'))
    (evidence/'Signing109.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
