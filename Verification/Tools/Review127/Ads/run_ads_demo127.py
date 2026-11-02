"""Build only the independently reviewed private demo project; never install/run it."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
EDITOR=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe')
PRIVATE=Path('E:/.verification-cache/HOTR127')
OUT=ROOT/'Verification/Evidence/Review127/Ads'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,code):
    if not ok:raise ValueError(code)
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for part in ('Assets','Packages','ProjectSettings')
            for p in sorted((root/part).rglob('*')) if p.is_file()}

def run(tag,attempt,review_path,review_sha):
    need(re.fullmatch('[A-Za-z0-9_-]{1,24}',tag or '') and re.fullmatch('[A-Za-z0-9_-]{1,24}',attempt or ''),'SafeTags127')
    parent=PRIVATE/tag;receipt_path=parent/'Preparation127.json';receipt=json.loads(receipt_path.read_bytes());project=Path(receipt['project'])
    need(project==parent/'Game' and project.is_dir(),'ExactPreparedProject127')
    need(sha(review_path)==review_sha,'ExactIndependentReviewReceipt127')
    review=json.loads(Path(review_path).read_bytes())
    need(review['status']=='PASS_READONLY_AD_DEMO127_PREBUILD_REVIEW'
         and review['preparationSHA256']==sha(receipt_path)
         and review['harnessSHA256']==receipt['harnessSHA256'] and review['builderSHA256']==receipt['builderSHA256'],
         'AcceptedSourceBoundIndependentReview127')
    for rel,want in receipt['copiedSHA256'].items():need(sha(project/rel)==want,'PreparedSourceChanged127')
    observed=subprocess.run(['powershell.exe','-NoProfile','-Command',
        'Get-CimInstance Win32_Process -Filter "Name=\'Unity.exe\'" | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress'],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,creationflags=0x08000000)
    need(observed.returncode==0,'ReadableEditorProcessInventory127')
    processes=json.loads(observed.stdout.decode('utf-8-sig')) if observed.stdout.strip() else []
    if isinstance(processes,dict):processes=[processes]
    foreign=[]
    for item in processes:
        if Path(item.get('ExecutablePath') or '').resolve()==Path('C:/Program Files/Unity Hub/resources/unity.exe').resolve():
            foreign.append({'pid':item['ProcessId'],'kind':'ExactKnownUnityHubResourceHelper','touched':False});continue
        match=re.search(r'(?:^|\s)-projectPath\s+(?:"([^"]+)"|(\S+))',item.get('CommandLine') or '',re.I)
        need(match is not None,'UnknownEditorProjectBlocksBuild127')
        active_project=Path(match.group(1) or match.group(2)).resolve()
        need(active_project!=project.resolve(),'SameProjectEditorBlocksBuild127')
        foreign.append({'pid':item['ProcessId'],'project':str(active_project),'touched':False})
    output=OUT/attempt;need(not output.exists(),'PreserveAllPriorAttempts127');output.mkdir(parents=True)
    before=inventory(ROOT/'Unity');(output/'MainBefore.json').write_text(json.dumps(before,indent=2)+'\n')
    env=dict(os.environ)
    for key in list(env):
        if key.upper().startswith('HOTR_') or re.search('KEYSTORE|KEYALIAS|STOREPASS|KEYPASS',key,re.I):env.pop(key,None)
    need(not any(env.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')),'UnreviewedJavaOptionsRejected127')
    gradle=Path('E:/G127'+tag);marker=gradle/'.ads-demo127.json'
    custody={'project':str(project),'preparationSHA256':sha(receipt_path)}
    if gradle.exists():need(marker.exists() and json.loads(marker.read_bytes())==custody,'OwnedShortPrivateGradleCache127')
    else:gradle.mkdir();marker.write_text(json.dumps(custody)+'\n')
    # Only uncredentialed compiled/download cache directories may be reused.
    # No Gradle properties, daemon state, signing inputs or raw former logs.
    previous=Path('E:/G126A/caches/modules-2/files-2.1')
    if previous.is_dir() and not (gradle/'caches/modules-2/files-2.1').exists():
        shutil.copytree(previous,gradle/'caches/modules-2/files-2.1',ignore=shutil.ignore_patterns('*.lock','*.lck','gc.properties'))
    env.update(GRADLE_USER_HOME=str(gradle),HOTR_ADS127_RECEIPT=str(receipt_path),
        HOTR_ADS127_RECEIPT_SHA256=sha(receipt_path),HOTR_ADS127_OUT=str(output))
    record={'status':'RUNNING_PRIVATE_AD_DEMO127_BUILD','startedUtc':datetime.now(timezone.utc).isoformat(),
        'project':str(project),'preparationSHA256':sha(receipt_path),'independentReviewSHA256':review_sha,
        'runnerSHA256':sha(__file__),'editorSHA256':sha(EDITOR),'actualBuildRequested':True,
        'providerContacted':False,'deviceTouched':False,'mainSourceEdited':False,'foreignEditorsObservedOnly':foreign}
    process=None;started=time.monotonic()
    try:
        with (output/'Console.log').open('xb') as log:
            process=subprocess.Popen([str(EDITOR),'-batchmode','-nographics','-projectPath',str(project),'-buildTarget','Android',
                '-executeMethod','HeartOfTheRain.Verification127.Editor.AdsDemoBuild127.Run','-logFile',str(output/'Unity.log')],
                cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=0x08000000)
            record['pid']=process.pid;record['exitCode']=process.wait(timeout=1500)
    except Exception as error:
        record['errorType']=type(error).__name__
        if process is not None and process.poll() is None:
            # Only this owned invocation, never another Editor/Hub/project.
            subprocess.run(['C:/Windows/System32/taskkill.exe','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
    finally:
        record['processStopped']=process is None or process.poll() is not None
        record['elapsedSeconds']=round(time.monotonic()-started,3)
        after=inventory(ROOT/'Unity');record['newerUnrelatedMainPathsDuringBuild']=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
        record['mainSettingsUnchanged']=all(before.get(k)==after.get(k) for k in ('ProjectSettings/ProjectSettings.asset','ProjectSettings/ProjectVersion.txt'))
        record['sourceBindingsStillMatchCurrentMain']={rel:sha(ROOT/'Unity'/rel)==want for rel,want in receipt['sourceBindings'].items()}
        native=json.loads((output/'Native.json').read_bytes()) if (output/'Native.json').exists() else {}
        record['nativeStatus']=native.get('status');record['nativeSHA256']=sha(output/'Native.json') if native else None
        record['status']='PASS_PRIVATE_AD_DEMO127_BUILD' if record.get('exitCode')==0 and native.get('status')=='PASS_REAL_SDK_AD_DEMO127_ANDROID_BUILD' and record['processStopped'] and record['mainSettingsUnchanged'] else 'FAIL_PRIVATE_AD_DEMO127_BUILD'
        record['finishedUtc']=datetime.now(timezone.utc).isoformat();(output/'Process.json').write_text(json.dumps(record,indent=2)+'\n')
    return {'status':record['status'],'output':str(output),'nativeStatus':record['nativeStatus'],'apk':native.get('apk'),'apkSHA256':native.get('apkSHA256')}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--attempt',required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--review-sha256',required=True);a=p.parse_args()
    print(json.dumps(run(a.tag,a.attempt,a.review,a.review_sha256)))
