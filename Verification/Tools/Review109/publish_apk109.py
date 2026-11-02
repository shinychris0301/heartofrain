"""Publish exact native/static-passed109 bytes without replacing an unknown file."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as s:
  for block in iter(lambda:s.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def main():
 build=ROOT/'Verification/Evidence/Review109/Native/AndroidBuildLts01/BuildDevelopment109.json';native=json.loads(build.read_text('utf-8'));static=build.parent/'Static/Audit01/StaticApk109.json';audit=json.loads(static.read_text('utf-8'))
 source=Path(native['apk']);expected=native['apkSHA256']
 if native['status']!='PASS_NATIVE_TEAMS109_BUILD_DEVELOPMENT' or native['errors'] or audit['status']!='PASS_STATIC_TEAMS109_APK' or audit['apkSHA256']!=expected or audit['nativeBuildSHA256']!=sha(build) or sha(source)!=expected:raise ValueError('ExactPassingNativeStatic109Required')
 dest=ROOT/'Unity/Builds/Review109/HeartOfTheRain_109_Android_Test.apk';dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():
  if sha(dest)!=expected:raise ValueError('PreserveUnknownPublishedApk109')
 else:
  with source.open('rb') as s,dest.open('xb') as d:
   for block in iter(lambda:s.read(1024*1024),b''):d.write(block)
 if sha(dest)!=expected:raise ValueError('ExactDeliveredApk109Required')
 binding=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
 record=dict(status='PUBLISHED_INTERNAL_DEVELOPMENT_APK109',source=binding(source),published=binding(dest),build=binding(build),static=binding(static),package='com.heartoftherain.review98',versionCode=109,signerCertificateSHA256=audit['signerCertificateSHA256'],sdk='Pinned Yandex lite8.6.0; AppMetrica8.6.0 retained',adsEnabled=False,managedPayload=False,productionApproved=False,note='Same-package internal development update. Future same-package builds require versionCode at least109. Physical installation is a separately guarded operation and is not claimed by publication.')
 out=ROOT/'Verification/Evidence/Review109/APKDelivery109.json'
 with out.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
 print(json.dumps(dict(status=record['status'],apk=dest.relative_to(ROOT).as_posix(),sha256=expected,bytes=dest.stat().st_size)))
if __name__=='__main__':main()
