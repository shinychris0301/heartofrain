"""Bundle only full-suite-pinned backend sources and public sandbox inputs.

No server operation, database, virtual environment, signing key or credential
file is read/copied. Existing output is preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[3]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def need(ok,reason):
 if not ok:raise RuntimeError(reason)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--full-report',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 proof_path=a.full_report.resolve();need(proof_path.is_relative_to((ROOT/'Verification/Evidence/Review126/Backend').resolve()),'OwnedFullSuiteReceiptRequired126')
 proof=json.loads(proof_path.read_text('utf-8'))
 need(proof['status']=='PASS_BACKEND_SERVICE_TESTS' and proof['actualPinnedWorkerIntegration'] is True and not proof['skipped'] and not proof['errors'] and not proof['failures'] and not proof['sourceInputsChangedDuringRun'],'CompleteZeroSkipBackendPassRequired126')
 need(proof['sourceSHA256']==proof['sourceSHA256After'],'StableFullSuiteSourcesRequired126')
 files={}
 for relative,digest in proof['sourceSHA256'].items():
  need(relative.startswith('Backend/') and '..' not in Path(relative).parts,'ContainedBackendSourceRequired126')
  path=(ROOT/relative).resolve();need(path.is_relative_to((ROOT/'Backend').resolve()) and sha(path)==digest,'CurrentBackendMustMatchAcceptedFullRun126')
  files[relative]=digest
 focused_path=ROOT/'Verification/Evidence/Review126/Backend/FinalFocused126.json'
 focused=json.loads(focused_path.read_text('utf-8'))
 need(focused['successful'] and focused['sourcesStable'] and focused['sourceSHA256Before']==focused['sourceSHA256After'],'StableFocusedPublicFixturesRequired126')
 for relative in ('Release/RuStore/commerce.example.json','Release/Monetization126/commerce.sandbox.json'):
  need(sha(ROOT/relative)==focused['sourceSHA256After'][relative],'TestedExternalCommerceFixtureRequired126')
 for path in [ROOT/'Backend/requirements.lock',ROOT/'Release/RuStore/commerce.example.json',*sorted((ROOT/'Release/Monetization126').glob('*.json'))]:
  need(path.is_file(),'PublicBundleInputRequired126');files[path.relative_to(ROOT).as_posix()]=sha(path)
 need(all(Path(name).suffix.lower() in ('.py','.json','.lock','.in','.md','.ps1') for name in files),'SourceAndPublicInputsOnly126')
 need(not any('/.venv/' in name or name.endswith(('.keystore','.jks','.p12','.dpapi')) for name in files),'PrivateMaterialExcluded126')
 out=a.out.resolve();need(out.is_relative_to((ROOT/'Verification/Evidence/Review126').resolve()) and not out.exists(),'FreshOwnedStageOutputRequired126');out.mkdir(parents=True,exist_ok=False)
 manifest={'version':1,'status':'FULL_SUITE_PINNED_SANDBOX_SOURCE126','sourceReport':proof_path.relative_to(ROOT).as_posix(),'sourceReportSHA256':sha(proof_path),'focusedPublicFixtureReportSHA256':sha(focused_path),'tests':proof['tests'],'executedTests':proof['executedTests'],'filesSHA256':files,'schemaTarget':125,'productionEnabled':False,'actualSdkPaymentVerified':False,'actualAdViewVerified':False,'serverInstalled':False,'credentialsIncluded':False}
 encoded=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
 archive=out/'HeartOfTheRain_SDK126_Backend.zip'
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,digest in sorted(files.items()):
   path=ROOT/name;need(sha(path)==digest,'SourceChangedWhileBundling126');z.write(path,name)
  z.writestr('Bundle126.json',encoded)
 with zipfile.ZipFile(archive) as z:
  need(z.testzip() is None,'SourceBundleCrcFailed126')
  for name,digest in files.items():need(hashlib.sha256(z.read(name)).hexdigest()==digest,'SourceBundleHashFailed126')
 manifest['archiveSHA256']=sha(archive);manifest['archiveBytes']=archive.stat().st_size
 with (out/'Bundle126.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
 print(json.dumps({'status':manifest['status'],'files':len(files),'archive':str(archive.relative_to(ROOT)),'archiveSHA256':manifest['archiveSHA256']}))
if __name__=='__main__':main()
