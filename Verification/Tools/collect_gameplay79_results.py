"""Read-only checkpoint79 evidence validation; --publish is explicit.

The native/device runners establish execution. This collector checks their
source, artifact and saved-data bindings without turning analysis into a test.
"""
import argparse, hashlib, json, math, re, statistics
from datetime import datetime, timezone
from pathlib import Path
from collect_gameplay78_results import NATIVE as PRIOR_NATIVE, CONTRACT, PROFILE
from run_first_pose79_device import validate_report as validate_first_pose
from run_cascade_timing_device import validate_report as validate_cascade
from run_power_fall77_device import validate_report as validate_power_fall
from run_execution78_device import validate_report as validate_execution
from analyze_first_pose79_performance import build as analyze_first_pose
from qa_android_target import validate_qa_target

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Gameplay79'
BASE=ROOT/'Verification/Evidence/Gameplay78'
NATIVE=dict(PRIOR_NATIVE)|{'Snapshot79':'PASS_NATIVE_SNAPSHOT79','Worker79':'PASS_NATIVE_PLAYBACK_PREPARATION79','StartupLifecycle79':'PASS_NATIVE_STARTUP_LIFECYCLE79'}
CHANGED_SOURCE79={'Unity/Assets/HeartOfTheRain/'+p for p in ['M46/Runtime/BoardModel.cs','M46/Runtime/BoardPlayback.cs','M46/Runtime/LocalCascadeContinuation.cs','M47/Runtime/GameplayCommandPreparation.cs','M47/Runtime/GameplayScreen.cs','M48/Runtime/EffectResourcesPure.cs','Verification/CascadeTimingProbe.cs','Verification/Editor/CommandPreparation78Verification.cs','Verification/Editor/PowerFallPreparationVerification.cs','Verification/Editor/PresentationWarmupVerification.cs','Verification/Editor/NativePlaySmoke.cs','Verification/Execution78Probe.cs','Verification/PowerFall77Probe.cs']}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
evidence={}
external_evidence={}
def need(value,message):
 if not value:raise AssertionError(message)
def file(name):
 p=(OUT/name).resolve();need(p.is_relative_to(OUT.resolve()) and p.is_file(),'Missing/unsafe proof: '+name)
 evidence[p.relative_to(OUT).as_posix()]=sha(p);return p
def read(name):return json.loads(file(name).read_text('utf-8-sig'))
def external_file(name,expected=None):
 p=(ROOT/name).resolve();need(p.is_relative_to(ROOT.resolve()) and p.is_file(),'Missing/unsafe external proof: '+name)
 digest=sha(p);need(expected is None or digest==expected,'Changed external proof: '+name)
 external_evidence[p.relative_to(ROOT).as_posix()]=digest;return p
def external_read(name,expected=None):return json.loads(external_file(name,expected).read_text('utf-8-sig'))
def utc(value):return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
def clean(v,label):need(not any(v.get(k) for k in ['error','errors','failures','failed']),label+' contains a failure')
def native_camera_startup(report,label):
 """Legacy harnesses witness an active head or its held post-swap pose.

 First-head camera timing itself is proved by Lifecycle79/FirstPose controls.
 """
 mode=report['startupMode'];trace=report['startupTrace']
 need(mode in ('default79-leading-swap-offscreen-own-camera','default79-leading-swap-automatic-own-camera') and report['startupWitnessed'] is True,label+' did not exercise witnessed default79 startup')
 need(report['startupExplicitOffscreenWitness'] is (mode=='default79-leading-swap-offscreen-own-camera'),label+' witness mode/flag differs')
 need(trace['eligible'] is True and trace['pending'] is False and trace['workerFailed'] is False and trace['cancelled'] is False,label+' retained trace is incomplete or failed')
 frames=[trace[k] for k in ('acceptedFrame','headSubmittedFrame','cameraWitnessFrame','jobStartedFrame','jobCompletedFrame','tailInstalledFrame')]
 need(all(isinstance(v,int) and not isinstance(v,bool) and v>0 for v in frames) and frames==sorted(frames) and trace['cameraWitnessFrame']==trace['jobStartedFrame'] and trace['jobCompletedFrame']==trace['tailInstalledFrame'],label+' retained frame chronology differs')
 need(report['startupHeadSubmittedFrame']==trace['headSubmittedFrame'] and report['startupCameraWitnessFrame']==trace['cameraWitnessFrame'] and report['startupJobStartedFrame']==trace['jobStartedFrame'],label+' primitive witness fields do not match retained completed trace')
 ticks=[trace[k] for k in ('acceptedTicks','headSubmittedTicks','cameraWitnessTicks','jobStartedTicks','workerQueuedTicks','workerStartedTicks','workerFinishedTicks','jobCompletedTicks','tailInstalledTicks')]
 need(all(isinstance(v,int) and not isinstance(v,bool) and v>0 for v in ticks) and ticks==sorted(ticks),label+' retained camera/worker/install chronology differs')
 need(trace['callerThreadId']>0 and trace['workerThreadId']>0 and trace['callerThreadId']!=trace['workerThreadId'] and abs(trace['headDuration']-.12)<1e-6,label+' lost detached worker or120ms prefix identity')
 return {'mode':mode,'actualOwnCameraWitness':True,'explicitOffscreenWitness':report['startupExplicitOffscreenWitness'],'tailInstalledFrame':trace['tailInstalledFrame'],'scope':'One default79 startup completes in this native lifecycle harness. Camera witness can occur on its active head or held post-swap pose; first-head timing, physical display and device pacing are separate proofs.'}
def preserved_attempts(current_source,old):
 """Failed runs remain source-bound history, never final passing assertions."""
 values=[]
 for attempt,suite,method,status in (('001_snapshot_fixture','Snapshot79','Snapshot79Verification.Run','FAIL_NATIVE_SNAPSHOT79'),('002_snapshot_direct_fixture','Snapshot79','Snapshot79Verification.Run','FAIL_NATIVE_SNAPSHOT79'),('003_legacy_source_guard','PowerFallPreparation','PowerFallPreparationVerification.Run','FAIL_NATIVE_POWER_FALL_PREPARATION77'),('004_worker_process_bom','PowerFallPreparation','PowerFallPreparationVerification.Run','FAIL_NATIVE_POWER_FALL_PREPARATION77'),('005_batchmode_camera_witness','WarmupChecks',None,'FAIL_NATIVE_PRESENTATION_WARMUP')):
  prefix='Attempts/'+attempt+'/';source=read(prefix+'Source_SHA256.json');delta=read(prefix+'Source_Delta.json')
  run=read(prefix+'Native/'+suite+'_Process.json');report=read(prefix+'Native/'+suite+'.json')
  manifest=read(prefix+run['sourceManifest']);file(prefix+'Native/'+suite+'.log');reason=file(prefix+'Reason.txt').read_text('utf-8-sig').strip()
  need(reason and run['mode']==suite and run['method']==method and run['exitCode']!=0 and not run['timedOut'] and run['version'].startswith('2022.3.62f3'),'Historical failed run identity differs: '+attempt)
  need(manifest['files']==source['files'] and sha(file(prefix+run['sourceManifest']))==run['sourceSHA256'],'Historical failed run/source manifest differs: '+attempt)
  need(utc(source['utc'])<=utc(run['startedUtc'])<=utc(report['utc'])<=utc(run['finishedUtc'])<=utc(current_source['utc']),'Historical failed run chronology differs: '+attempt)
  need(report['status']==status and (report.get('errors') or report.get('failures')),'Historical failed report is missing: '+attempt)
  if suite=='Snapshot79':need(report['modelCases']==350,'Historical350 corpus is missing: '+attempt)
  elif suite=='PowerFallPreparation':need(report['checks']==(19 if attempt=='004_worker_process_bom' else 14) and report['replayedFrames']==0,'Historical preparation source-guard failure differs')
  else:need(report['checks']==11662 and suite=='WarmupChecks','Historical batchmode camera-witness failure differs')
  changed=sorted(k for k in old.keys()&source['files'].keys() if old[k]!=source['files'][k]);added=sorted(source['files'].keys()-old.keys())
  need(delta['baseline']==78 and delta['changed_existing']==changed and delta['added']==added and not delta['removed'] and not old.keys()-source['files'].keys(),'Historical source delta differs: '+attempt)
  if attempt in ('004_worker_process_bom','005_batchmode_camera_witness'):need(set(changed)==CHANGED_SOURCE79-{'Unity/Assets/HeartOfTheRain/Verification/Editor/PresentationWarmupVerification.cs','Unity/Assets/HeartOfTheRain/Verification/Editor/NativePlaySmoke.cs'} and len(added)==18,'Historical004/005 source11/18 migration scope differs')
  for name in changed+added:need(sha(file(prefix+'SourceFiles/'+name))==source['files'][name],'Historical source bytes differ: '+attempt+'/'+name)
  if suite=='Snapshot79':
   bindings={'currentModelSHA256':'M46/Runtime/BoardModel.cs','controlSourceSHA256':'Verification/Snapshot78Control79.cs','proofSourceSHA256':'Verification/Snapshot79Proof.cs','verificationSourceSHA256':'Verification/Editor/Snapshot79Verification.cs'}
   need(all(report[field]==source['files']['Unity/Assets/HeartOfTheRain/'+name] for field,name in bindings.items()),'Historical report/source fields differ: '+attempt)
  elif suite=='PowerFallPreparation':
   need(report['model78ProofSHA256']==sha(file(prefix+'Native/ModelWork78.json')),'Historical preparation/model proof binding differs')
   need(all(row['currentSHA256']==source['files'][row['path']] for row in report['sourceBindings']),'Historical preparation/source fields differ')
   file(prefix+'Native_Lifecycle_Visual_Notes.json')
   for prior in ('Snapshot79','Worker79','StartupLifecycle79','ModelWork78','DenseSubmission','CommandPreparation78','PowerFallSampling'):
    prior_run=read(prefix+'Native/'+prior+'_Process.json');prior_report=read(prefix+'Native/'+prior+'.json');prior_manifest=read(prefix+prior_run['sourceManifest']);file(prefix+'Native/'+prior+'.log')
    need(prior_run['exitCode']==0 and not prior_run['timedOut'] and prior_report['status']==NATIVE[prior] and prior_manifest['files']==source['files'] and sha(file(prefix+prior_run['sourceManifest']))==prior_run['sourceSHA256'],'Historical partial-run proof differs: '+prior)
    need(utc(prior_run['startedUtc'])<=utc(prior_report['utc'])<=utc(prior_run['finishedUtc'])<=utc(run['startedUtc']),'Historical partial-run chronology differs: '+prior)
  else:
   file(prefix+'Native_Lifecycle_Visual_Notes.json');file(prefix+'Native_Pixel_Visual_Notes.json')
   earlier=sorted(p.stem.removesuffix('_Process') for p in (OUT/prefix/'Native').glob('*_Process.json') if p.name!=suite+'_Process.json')
   need(len(earlier)==32,'Historical005 preceding32-suite scope differs')
   for prior in earlier:
    prior_run=read(prefix+'Native/'+prior+'_Process.json');prior_report=read(prefix+'Native/'+prior+'.json');prior_manifest=read(prefix+prior_run['sourceManifest']);file(prefix+'Native/'+prior+'.log')
    need(prior_run['exitCode']==0 and not prior_run['timedOut'] and prior_report['status']==NATIVE[prior] and prior_manifest['files']==source['files'] and sha(file(prefix+prior_run['sourceManifest']))==prior_run['sourceSHA256'],'Historical005 partial-run proof differs: '+prior)
    need(utc(source['utc'])<=utc(prior_run['startedUtc'])<=utc(prior_report['utc'])<=utc(prior_run['finishedUtc'])<=utc(run['startedUtc']),'Historical005 partial-run chronology differs: '+prior)
  values.append({'attempt':attempt,'suite':suite,'exit_code':run['exitCode'],'source_sha256':sha(file(prefix+'Source_SHA256.json')),'process_source_sha256':run['sourceSHA256'],'changed_existing':len(changed),'added_inputs':len(added),'failed_status':report['status'],'failed_checks':report['checks'],'reason':reason,'scope':'Preserved failed native proof only; none of these assertions or preceding partial-run passes contributes to the final passing suite/check count.'})
 return values
def main(publish=False):
 evidence.clear();external_evidence.clear();frozen=read('Source_SHA256.json');current={p.relative_to(ROOT).as_posix():sha(p) for d in ('Assets','Packages','ProjectSettings') for p in (ROOT/'Unity'/d).rglob('*') if p.is_file()}
 need(frozen['files']==current,'Frozen Unity inputs changed')
 old=read('Baseline78_Source_SHA256.json')['files'];baseline=read('Baseline78.json');sealed=read('Baseline78_Summary.json')
 need(baseline['status']=='PRESERVED_VERIFIED78_BASELINE' and baseline['source_inputs']==len(old)==5141,'Baseline scope differs')
 need(baseline['source_sha256']==sha(file('Baseline78_Source_SHA256.json'))==sha(BASE/'Source_SHA256.json')=='bb4957a736bd76bee426cbf2cc7ab1a6da3080e3c86d8ac07a89f45da51747c7','Changed78 source baseline')
 need(baseline['summary_sha256']==sha(file('Baseline78_Summary.json'))==sha(BASE/'Summary.json') and sealed['source_checkpoint']==78,'Changed78 published baseline')
 need(sha(ROOT/baseline['apk_archive'])==baseline['apk_sha256']==sealed['apk_sha256'],'Changed78 APK archive')
 delta=read('Source_Delta.json');changed=sorted(k for k in old.keys()&current.keys() if old[k]!=current[k]);added=sorted(current.keys()-old.keys())
 need(delta['baseline']==78 and delta['changed_existing']==changed and delta['added']==added and not delta['removed'] and not old.keys()-current.keys(),'Source delta mismatch')
 need(set(changed)==CHANGED_SOURCE79,'Unapproved source79 existing-file delta')
 allowed=CHANGED_SOURCE79
 new={'Unity/Assets/HeartOfTheRain/'+p+suffix for p in ['M47/Runtime/GameplayStartupPreparation79.cs','M47/Runtime/PlaybackPreparationJob79.cs','Verification/Editor/PlaybackPreparation79Verification.cs','Verification/Editor/Snapshot79Verification.cs','Verification/Editor/StartupLifecycle79Verification.cs','Verification/FirstPose79Probe.cs','Verification/Playback78Control79.cs','Verification/Snapshot78Control79.cs','Verification/Snapshot79Proof.cs'] for suffix in ['', '.meta']}
 need(set(changed)==allowed and set(added)==new and len(current)==5159,'Source scope/count differs from approved79 engineering delta')
 protected=('.meta','/Resources/','/Packages/','/ProjectSettings/')
 need(not any(p.endswith(protected[0]) or any(t in p for t in protected[1:]) for p in changed),'Protected artwork/metadata/settings changed')
 for name in changed:need(sha(ROOT/baseline['source_archive']/name)==old[name],'Archived78 source changed: '+name)
 history=preserved_attempts(frozen,old)
 native={}
 for name,status in NATIVE.items():
  report,run=read('Native/'+name+'.json'),read('Native/'+name+'_Process.json');clean(report,name)
  need(report['status']==status and run['exitCode']==0 and not run['timedOut'] and run['version'].startswith('2022.3.62f3'),name+' did not pass pinned Unity')
  need(utc(frozen['utc'])<=utc(run['startedUtc'])<=utc(report['utc'])<=utc(run['finishedUtc']),name+' source/report chronology differs')
  need(read(run['sourceManifest'])['files']==current and sha(file(run['sourceManifest']))==run['sourceSHA256'],name+' ran different Unity inputs')
  need(CONTRACT['BASE_CONTRACT']['checks'](report)>0,name+' ran no assertions');native[name]=report
 runner=read('Native_Runner.json');need(runner['status']=='PASS_SELECTED_NATIVE_GAMEPLAY79_SUITES' and len(runner['runs'])==len(native)==35,'Missing final35-suite run')
 need({v['mode'] for v in runner['runs']}==set(native),'Native runner omitted suite')
 for v in runner['runs']:need(v==read('Native/'+v['mode']+'_Process.json'),'Runner/process binding differs')
 snapshot=native['Snapshot79'];need(snapshot['modelCases']==350 and snapshot['transitionCases']>=2 and snapshot['presentationFaultCases']>=6 and all(snapshot[k] for k in ['exact78Control','rawParity','finalParity','checkpointParity','dictionaryParity']),'Snapshot state/corpus/fault proof incomplete')
 need(len(snapshot['timings'])==24 and all(len(t['pairs'])==12 for t in snapshot['timings']),'Snapshot isolation workloads missing')
 for row in snapshot['timings']:
  need(row['slowerPairs']==sum(v['currentMs']>v['controlMs'] for v in row['pairs']),'Slower snapshot pairs omitted')
  for branch in ('control','current'):need(math.isclose(row[branch+'MedianMs'],statistics.median(v[branch+'Ms'] for v in row['pairs']),rel_tol=1e-8,abs_tol=1e-8),'Snapshot median differs')
 worker=native['Worker79'];need(worker['modelCases']==350 and all(worker[k] for k in ['compiledSourceMatchesArchive','queueParity','rawParity','pathOrderParity','poseParity','metadataManagedOnly']),'Worker exact78 queue/data/path/pose proof incomplete')
 need(worker['queueComparisons']>=350 and worker['cancellationCases']>=4 and worker['negativeCases']>0 and worker['eligibleSwaps']>0,'Worker controls incomplete')
 camera_startups={name:native_camera_startup(native[name],name) for name in ('WarmupChecks','PlaySmoke')}
 for name in ('LocalCascade','LocalContinuation'):need(native[name]['modelCases']==350 and native[name]['rawTurnParity'] and native[name]['finalSnapshotParity'],name+' model semantics changed')
 need(native['MixedSwapChecks']['protectedBirths']==360 and native['MixedSwapChecks']['chainedBirths']==0,'Mixed-swap birth protection regressed')
 lifecycle=native['StartupLifecycle79'];cases={r['name']:r for r in lifecycle['rows']}
 need(set(cases)=={'pure_swap_hold_rapid_input','reload_discards_stale','disable_resume','pause_worker_install','fault_out_of_moves','fault_won'} and len(lifecycle['rows'])==6,'Lifecycle case coverage missing')
 for name,row in cases.items():
  need(row['playerRecords']==row['modelAccepted']==row['authorizations']==1 and row['toolSpends']==0 and row['settled']==(0 if name=='reload_discards_stale' else 1),'Lifecycle action/charge/settlement replayed')
  for image in row['captures']:file(image)
 need(cases['reload_discards_stale']['staleDiscarded'] and cases['disable_resume']['resumed'] and cases['pause_worker_install']['paused'],'Lifecycle ownership/pause controls missing')
 need(cases['fault_out_of_moves']['settledStatus']=='Engine fault' and cases['fault_won']['settledStatus']=='Won' and cases['fault_out_of_moves']['expectedFaultLogs']==cases['fault_won']['expectedFaultLogs']==1,'Terminal presentation faults changed accepted outcome')
 build,process,artifact,pack=read('Android_Build.json'),read('AndroidBuild_Process.json'),read('APK_Artifact.json'),read('APK_Packaging.json');clean(build,'Development build')
 apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk';digest=sha(apk)
 need(build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['unity']=='2022.3.62f3' and build['errors']==0 and process['exitCode']==0 and not process['timedOut'],'Development build failed')
 need(read('Build_Source_SHA256.json')['files']==current and digest==artifact['sha256']==pack['afterSHA256'] and apk.stat().st_size==artifact['bytes']==pack['afterBytes'],'APK/source identity differs')
 need(all(artifact[k] for k in ('zipalign4KiBPass','developmentSignatureVerifies','elf16KiBLoadSegmentsPass')) and pack['sameSignerCertificate'] and not pack['changedNonSignatureEntries'],'Packaging checks failed')
 release,rp,ra=read('Android_Release_Build.json'),read('AndroidReleaseBuild_Process.json'),read('Release_APK_Artifact.json');clean(release,'Release compile')
 need(release['status']=='PASS_ANDROID_RELEASE_COMPILE_BUILD' and release['unity']=='2022.3.62f3' and release['errors']==0 and rp['exitCode']==0 and not rp['timedOut'],'Nondevelopment compile/build failed')
 need(read('Release_Source_SHA256.json')['files']==current and sha(ROOT/ra['path'])==ra['sha256'] and ra['sourceSHA256']==sha(file('Release_Source_SHA256.json')),'Release artifact/source differs')
 need(max(utc(read('Native/'+n+'_Process.json')['finishedUtc']) for n in native)<=utc(rp['startedUtc'])<=utc(rp['finishedUtc'])<=utc(process['startedUtc']),'Native/release/development order differs')
 for name in ('Build_Import_Audit.txt','Release_Build_Import_Audit.txt'):need('Errors: 0' in file(name).read_text('utf-8-sig'),'Import guard failed')
 target=validate_qa_target('emulator-5558',OUT);read('QA_Target.json');external_file('Verification/Tools/qa_android_target.py')
 isolation=read('QA_Isolation.json');protected=read('Protected_Original_Final.json')
 need(isolation['status']=='PASS_SEPARATE_QA79_INSTANCE_CREATED' and isolation['protectedUnchanged'] and isolation['protectedBefore']==isolation['protectedAfter']==protected['state'] and protected['unchanged'],'Original active QA data/APK changed')
 need(protected['state']['activeAttempts']==1 and protected['state']['installedAPK']==baseline['apk_sha256'],'Original QA attempt/APK not preserved')
 preflight=read('QA_Preflight.json');need(preflight['status']=='PASS_READ_ONLY_QA_PREFLIGHT' and preflight['serial']==target['serial'] and preflight['activeAttempts']==0,'Fresh isolated QA preflight failed')
 before=read('Android/Before.json')
 normal=read('Normal_Startup.json');need(normal['status']=='PASS_NORMAL_ISOLATED_QA79_STARTUP' and normal['serial']==target['serial'] and normal['qa_target']==target and normal['apk_sha256']==digest and normal['data_unchanged'] and normal['before']==normal['after']==before and normal['runtime_errors']==0 and normal['attempt_guard']['activeAttempts']==0,'Normal isolated startup failed or changed data')
 file('Normal_Startup.png');file('Normal_Startup.log')
 def installation(name):
  v=read(name);need(v['serial']==target['serial'] and v.get('qa_target')==target and v.get('apk_sha256',v.get('sha256'))==digest and v.get('installed_apk_sha256',digest)==digest,'Wrong QA device/APK: '+name)
  need(utc(v['utc'])>=utc(process['finishedUtc']),'QA installation predates build')
  if 'before' in v:need(v['data_unchanged'] and v['before']==v['after']==before,'QA saved data changed: '+name)
  return v
 def isolated_control(folder,status,validator,hashes=None):
  value=read(folder+'/Report.json');installed=installation(folder+'/Installation.json');clean(installed,folder)
  need(installed['status']==status and installed['installed_apk_sha256']==digest and installed['runtime_errors']==0,folder+' APK/runtime audit failed')
  need(installed['data_unchanged'] and installed['before']==installed['after']==before,folder+' changed real saved data')
  need(utc(process['finishedUtc'])<=utc(installed['utc'])<=utc(value['utc'])<=utc(installed['finishedUtc']),folder+' build/process/report chronology differs')
  need(re.fullmatch('[0-9]+',str(installed['pid'])) is not None,folder+' lacks an unambiguous native process')
  log=file(folder+'/Runtime.log').read_text('utf-8-sig')
  need(not re.search('FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException',log),folder+' runtime log contains a native error')
  validated=validator(value) if hashes is None else validator(value,hashes)
  need(validated==installed['validated'],folder+' audit/raw validation differs')
  return value,installed,validated
 # The published78 summary seals its77 parent. Android hashes stay within
 # that platform domain; native serialized hashes are never substituted.
 old77_name='Verification/Evidence/Gameplay78/Baseline77_Summary.json'
 sealed77=external_read(old77_name,sealed['evidence_sha256']['Baseline77_Summary.json'])
 need(sealed77['source_checkpoint']==77 and sha(external_file(old77_name))==sealed['baseline_summary_sha256'],'Sealed77 parent identity differs')
 external_file('Verification/Evidence/Gameplay77/Summary.json',sealed['baseline_summary_sha256'])
 old76=external_read('Verification/Evidence/Gameplay77/Baseline76_Source_SHA256.json',sealed77['evidence_sha256']['Baseline76_Source_SHA256.json'])['files']
 prep=native['PowerFallPreparation'];prep_paths={'Unity/Assets/HeartOfTheRain/'+p for p in ('M46/Runtime/BoardModel.cs','M46/Runtime/LivePowerPlan.cs','M46/Runtime/ReviewPlan.cs','M46/Runtime/BoardPlayback.cs','Verification/ObstacleDensityFixture.cs','M46/Runtime/LocalCascadeContinuation.cs','M48/Runtime/EffectResourcesPure.cs')}
 need(len(prep['sourceBindings'])==7 and {v['path'] for v in prep['sourceBindings']}==prep_paths,'Preparation79 source coverage must be exactly seven explicit paths')
 model_paths={'Unity/Assets/HeartOfTheRain/'+p for p in ('M46/Runtime/BoardModel.cs','M46/Runtime/LivePowerPlan.cs')}
 worker_paths={'Unity/Assets/HeartOfTheRain/'+p for p in ('M46/Runtime/BoardPlayback.cs','M46/Runtime/LocalCascadeContinuation.cs','M48/Runtime/EffectResourcesPure.cs')}
 model_bindings={v['path']:v for v in native['ModelWork78']['currentProductionSourceBindings']}
 for binding in prep['sourceBindings']:
  name=binding['path'];need(binding['currentSHA256']==current[name] and binding['archivedSHA256']==old76[name],'Preparation79 source bytes differ: '+name)
  external_file('.verification-cache/Gameplay77/BaselineSources/'+name,old76[name])
  if name in model_paths:need(binding['currentSHA256']==model_bindings[name]['currentSHA256'] and binding['archivedSHA256']==model_bindings[name]['archived77SHA256'],'Preparation79 model equivalence link differs')
  elif name not in worker_paths:need(binding['currentSHA256']==binding['archivedSHA256'],'Unapproved preparation79 source guard migration: '+name)
 need(prep['sourceParityMode']=='ARCHIVED76_UNCHANGED_PLUS_MODEL78_AND_WORKER79_EQUIVALENCE' and prep['worker79CurrentSourceBound'] is True,'Preparation79 must declare fresh equivalence rather than unchanged source bytes')
 links=(('model78ProofPath','model78ProofSHA256','Native/ModelWork78.json'),('worker79ProofPath','worker79ProofSHA256','Native/Worker79.json'),('worker79ProcessPath','worker79ProcessSHA256','Native/Worker79_Process.json'))
 for path_key,sha_key,name in links:need(Path(prep[path_key]).resolve()==file(name).resolve() and prep[sha_key]==sha(file(name)),'Preparation79 fresh proof/process link differs: '+name)
 worker_run=read('Native/Worker79_Process.json');worker_manifest=file(worker_run['sourceManifest'])
 need(Path(prep['worker79SourceManifestPath']).resolve()==worker_manifest.resolve() and prep['worker79SourceManifestSHA256']==worker_run['sourceSHA256']==sha(worker_manifest) and prep['worker79SourceInputs']==len(current),'Preparation79 full Worker79 source-manifest link differs')
 need(read(worker_run['sourceManifest'])['files']==current and utc(worker_run['finishedUtc'])<=utc(prep['utc']),'Preparation79 worker proof is stale or later than preparation replay')
 need(prep['fixture77RawParity'] and prep['fixture77FinalParity'] and prep['fixture77TurnHash']==prep['turnHash'] and prep['fixture77FinalHash']==prep['finalHash'],'Preparation79 fixture native77 parity differs')
 need(all(prep[k]==prep['turnHash'] for k in ('coldBeforeHash','coldAfterHash','preparedBeforeHash','preparedAfterHash')) and prep['rawTurnParity'],'Preparation79 replay mutated native raw turn')
 need(prep['rawTurnHashMatchesAndroid']==(prep['turnHash']==prep['androidTurnHash']) and prep['finalSnapshotMatchesAndroid'],'Preparation79 native/Android hash domains are misreported')
 need(prep['poseParity'] and prep['meshParity'] and prep['preparedDemandCreates']==prep['preparedDemandGeometryMisses']==0,'Preparation79 native replay parity/demand proof failed')
 old_power=external_read('Verification/Evidence/Gameplay77/PowerFall/Report.json',sealed77['evidence_sha256']['PowerFall/Report.json'])
 need(old_power['status']=='PASS_NATIVE_POWER_FALL77' and len(old_power['frozenRows'])==4,'Sealed77 Android density outcomes missing')
 density_hashes={(r['family'],r['count']):(r['turnHash'],r['finalHash']) for r in old_power['frozenRows']}
 need(set(density_hashes)=={(family,count) for family in ('crate','stone') for count in (1,45)},'Sealed77 density fixture coverage differs')
 power,power_install,power_summary=isolated_control('PowerFall','PASS_POWER_FALL77_DEVICE_AUDIT',validate_power_fall,density_hashes)
 execution,execution_install,execution_summary=isolated_control('Execution','PASS_EXECUTION78_DEVICE_AUDIT',validate_execution,density_hashes)
 need(execution_install['baseline_android77_report_sha256']==sealed77['evidence_sha256']['PowerFall/Report.json'],'Execution78 transport used an unsealed Android77 baseline')
 for tool in ('run_power_fall77_device.py','run_execution78_device.py','run_first_pose79_device.py'):external_file('Verification/Tools/'+tool)
 for name in CONTRACT['TOOLS']:
  v=read('Android/'+name+'_Data_Audit.json');need(v['serial']==target['serial'] and v['qa_target']==target and v['exit_code']==0 and v['data_unchanged'] and v['before']==v['after']==before and v['apk_sha256']==digest,'QA stage failed/changed data: '+name)
 first,first_install,first_summary=isolated_control('FirstPose','PASS_FIRST_POSE79_DEVICE_AUDIT',validate_first_pose)
 controls=read('FirstPose_Contract_Controls.json')
 need(controls['status']=='PASS_PYTHON_FIRST_POSE79_CONTRACT_CONTROLS' and controls['positiveOriginalAccepted'] and controls['originalInMemoryUnchanged'] and controls['originalBytesUnchanged'] and not controls['failures'] and controls['negativeControls']==controls['rejectedControls']==62 and len(controls['categories'])==18,'Python evidence-contract controls incomplete')
 need(controls['reportSHA256']==sha(file('FirstPose/Report.json')) and controls['runnerSHA256']==sha(external_file('Verification/Tools/run_first_pose79_device.py')) and controls['frameCostValidatorSHA256']==sha(external_file('Verification/Tools/run_execution78_device.py')) and controls['toolSHA256']==sha(external_file('Verification/Tools/check_first_pose79_contract.py')),'Python evidence-contract proof binding differs')
 target_controls=read('QA_Target_Tools_Static_Checks.json');need(target_controls['status']=='PASS_PYTHON_QA79_TARGET_AND_ARGV_GUARDS' and len(target_controls['negative_controls'])==13,'Python QA target controls incomplete')
 for name,d in target_controls['tools'].items():external_file('Verification/Tools/'+name,d)
 for variant in ('measure','visual'):
  value=read('Android/Cascade/'+variant+'/Report.json');installation('Android/Cascade/'+variant+'/Installation.json');validate_cascade(value,variant,require_profiling=True)
  prior=json.loads((BASE/('Android/Cascade/'+variant+'/Report.json')).read_text('utf-8-sig'));hashes={r['baseCase']:(r['turnHash'],r['finalHash']) for r in prior['rows']}
  PROFILE['validate'](value,variant,hashes)
 for level in (14,31,33):
  prefix='ContinuationVisual/L'+str(level)+'/visual/';value=read(prefix+'Report.json');installation(prefix+'Installation.json');validate_cascade(value,'visual',require_profiling=True)
 for family in ('crate','stone','gate','tiles'):
  prefix='Android/Density/candidate_review-'+family+'/';value=read(prefix+'Report.json');installation(prefix+'Installation.json');prior=json.loads((BASE/(prefix+'Report.json')).read_text('utf-8-sig'))
  PROFILE['validate_density'](value,family,{r['name']:(r['turnHash'],r['finalHash']) for r in prior['rows']})
 fluid=read('Android/Fluidity/Measurement.json');clean(fluid,'Fluidity');installation('Android/Fluidity/Installation.json');need(fluid['isolatedProfile'] and fluid['launchCleared'] and len(fluid['phases'])==8,'Fluidity coverage missing')
 touch=read('Android/Touch/Report.json');clean(touch,'Touch');need(touch['apk_sha256']==digest and touch['serial']==target['serial'] and touch['qa_target']==target and len(touch['cases'])==8,'Touch coverage missing')
 for row in touch['cases']:
  clean(row,row['mode']);need(row==read('Android/Touch/'+row['mode']+'_Report.json') and row['accepted'] and row['launchCleared'],'Native input failed')
  if row['mode'] in CONTRACT['MIXED']:need(row['sourceActivated'] and row['protectedBirth'] and not row['chained'],'Mixed-power runtime protection failed')
 regression=read('Android/Regression/Regression.json');clean(regression,'Campaign');installation('Android/Regression/Installation.json')
 need(regression['status']=='PASS_NATIVE_REGRESSION' and regression['boards']==50 and regression['checks']>=1716 and regression['clips']>=354 and regression['actions']>=408 and regression['labels']>=14105,'Full50-board native regression missing')
 need({'Native refill button spends 900 and fills all five lives','Repeated native refill callback charges exactly once','Confirmed decline charges exactly one life, no coins, and opens retry pre-level'}<=set(regression['passed']),'Life/Continue transaction assertions missing')
 idle=read('Android/Regression/M70_Device.json');clean(idle,'Live idle');CONTRACT['idle_device_controls'](idle,regression,read('Android/Regression/Installation.json'))
 analysis=read('Performance_Analysis.json');need(analysis['status']=='ANALYZED_FIRST_POSE79_WITH_REMAINING_GATES' and analysis['apk_sha256']==digest and analysis['source_sha256']==sha(file('Source_SHA256.json')) and analysis.get('remainingGates'),'Performance status/source/limits missing')
 expected_analysis=analyze_first_pose(OUT)
 need({k:v for k,v in analysis.items() if k!='utc'}=={k:v for k,v in expected_analysis.items() if k!='utc'},'First-pose analysis differs from recomputed raw proof')
 need(analysis['analyzerSHA256']==sha(external_file('Verification/Tools/analyze_first_pose79_performance.py')) and analysis['validatorSHA256']==sha(external_file('Verification/Tools/run_first_pose79_device.py')),'Analysis/validator source identity differs')
 need(analysis.get('artifactSHA256'),'Analyzed artifact map is empty')
 for name,d in analysis['artifactSHA256'].items():need(sha(file(name))==d,'Analyzed artifact changed: '+name)
 for name,d in analysis.get('externalEvidenceSHA256',{}).items():external_file(name,d)
 metrics=read('Android_Metrics_Review.json');need(metrics['status']=='REVIEWED_ANDROID79_METRICS_WITH_REMAINING_GATES' and metrics['source_sha256']==sha(file('Source_SHA256.json')) and metrics['apk_sha256']==digest and metrics['qa_serial']==target['serial'] and metrics['remainingGates'],'Wider Android timing review missing')
 for name,d in metrics['artifactSHA256'].items():need(sha(file(name))==d,'Wider reviewed timing artifact changed: '+name)
 reviewed_notes={}
 for name,status in (('Timing_Visual_Notes.json','ACTUAL_SAMPLED_TIMING_REVIEW79_WITH_REMAINING_GATES'),('Touch_Visual_Notes.json','ACTUAL_SAMPLED_TOUCH_REVIEW79_WITH_REMAINING_GATES'),('Campaign_Visual_Notes.json','ACTUAL_SAMPLED_CAMPAIGN_REVIEW79_WITH_REMAINING_GATES')):
  notes=read(name);need(notes['status']==status and notes['source_sha256']==sha(file('Source_SHA256.json')) and notes['apk_sha256']==digest and notes['qa_serial']==target['serial'] and notes['inspected'] and notes['limitations'],'Actual reviewer notes misbound: '+name)
  for p,d in notes['artifactSHA256'].items():need(sha(file(p))==d,'Reviewer artifact changed: '+p)
  for p,d in notes.get('externalEvidenceSHA256',{}).items():external_file(p,d)
  reviewed_notes[name]=notes
 timing_sheets=read('TimingVisual/Sheets.json');need(len(timing_sheets['sheets'])==8 and {r['file'] for r in timing_sheets['sheets']}<={v if isinstance(v,str) else v['file'] for v in reviewed_notes['Timing_Visual_Notes.json']['inspected']},'Eight current timing sheets not actually reviewed')
 touch_sheets=read('TouchVisual/Manifest.json');need(touch_sheets['source_sha256']==sha(file('Source_SHA256.json')) and touch_sheets['apk_sha256']==digest and touch_sheets['qa_target']==target and len(touch_sheets['cases'])==4,'Touch media provenance differs')
 expected_touch={s['file'] for case in touch_sheets['cases'] for s in case['sheets']};need(len(expected_touch)==8 and expected_touch<=set(reviewed_notes['Touch_Visual_Notes.json']['inspected']),'Eight current touch sheets not actually reviewed')
 campaign_sheets=read('RegressionVisual/Manifest.json');expected_campaign={p for group in campaign_sheets['sheets'].values() for p in group};need(len(expected_campaign)==14 and expected_campaign<=set(reviewed_notes['Campaign_Visual_Notes.json']['inspected']),'Fourteen campaign sheets not actually reviewed')
 visual=read('Visual_Review.json');need(visual['status']=='ACTUAL_SAMPLED_REVIEW79' and visual['apk_sha256']==digest and visual['source_sha256']==sha(file('Source_SHA256.json')) and visual['inspected'] and visual['limitations'],'Actual sampled review missing')
 need(visual['qa_serial']==target['serial'] and {'native_lifecycle','native_mesh_pixels','timing_four_levels','campaign_sheets','power_birth_chain_fall','settlement_refill'}<=set(visual['reviewedScopes']),'Actual visual review scope/device incomplete')
 for name,d in visual['artifactSHA256'].items():need(sha(file(name))==d,'Reviewed artifact changed: '+name)
 for name,d in visual.get('externalEvidenceSHA256',{}).items():external_file(name,d)
 result={'status':'PASS_TARGETED_STARTUP79_WITH_REMAINING_PERFORMANCE_GATES','utc':datetime.now(timezone.utc).isoformat(),'source_checkpoint':79,'source_inputs':len(current),'source_sha256':sha(file('Source_SHA256.json')),'baseline_checkpoint':78,'baseline_source_sha256':baseline['source_sha256'],'baseline_summary_sha256':baseline['summary_sha256'],'baseline_apk_sha256':baseline['apk_sha256'],'apk_sha256':digest,'apk_bytes':artifact['bytes'],'native_suites':len(native),'native_checks':sum(CONTRACT['BASE_CONTRACT']['checks'](v) for v in native.values()),'non_development_compile_build_passed':True,'qa_data_unchanged':True,'main_apk_updated':False,'android':{'stages':9,'boards':50,'checks':regression['checks'],'actions':regression['actions'],'clips':regression['clips']},'first_pose':first_summary,'power_fall':power_summary,'execution':execution_summary,'performance_analysis':analysis,'historical_attempts':history,'limits':visual['limitations'],'collector_sha256':sha(Path(__file__)),'evidence_sha256':dict(sorted(evidence.items())),'external_evidence_sha256':dict(sorted(external_evidence.items()))}
 result['native_camera_startup']=camera_startups
 result['qa_target']=target;result['original_qa_checkpoint']=78;result['original_active_attempt_preserved']=True
 result['python_contract_controls']={'negativeControls':controls['negativeControls'],'scope':'Python evidence validation only; excluded from native and device check totals.'}
 result['wider_android_review']='Android_Metrics_Review.json'
 if publish:
  for p in (OUT/'Summary.json',OUT.parent/'Verification_Summary.json'):p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  checkpoint={'utc':result['utc'],'status':result['status'],'source_checkpoint':79,'installed_checkpoint':64,'qa_installed_checkpoint':78,'isolated_qa_installed_checkpoint':79,'isolated_qa_serial':target['serial'],'original_qa_active_attempt_preserved':True,'source_sha256':result['source_sha256'],'android_apk_sha256':digest,'android_apk_matches_current_source':True,'main_installed_apk_matches_current_source':False,'review':'Codex_Handoff/Documentation/79_FIRST_POSE_AND_SNAPSHOT_REVIEW.md','summary':'Verification/Evidence/Gameplay79/Summary.json','scope':'Targeted startup/snapshot verification on new isolated QA2/5558 only. Original active QA1 remains78; main remains64. Performance, fresh-reference and physical-device gates remain open.'}
  (OUT.parent/'Native_Source_Checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ('evidence_sha256','external_evidence_sha256','first_pose','power_fall','execution','performance_analysis')},indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--publish',action='store_true');main(p.parse_args().publish)
