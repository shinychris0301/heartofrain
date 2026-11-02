"""Fail closed on current-source native, build, QA, power-fall and visual proof."""
import hashlib,json,math,re,runpy,statistics
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Gameplay77';BASE=ROOT/'Verification/Evidence/Gameplay76'
CONTRACT=runpy.run_path(str(Path(__file__).with_name('collect_gameplay75_results.py')),run_name='contracts_only')
PROFILE=CONTRACT['PROFILE_CONTRACT'];NATIVE=dict(CONTRACT['NATIVE'])|{'SmoothnessCommand':'PASS_NATIVE_SMOOTHNESS_COMMAND76','PowerFallSampling':'PASS_NATIVE_POWER_FALL_SAMPLING77','PowerFallPreparation':'PASS_NATIVE_POWER_FALL_PREPARATION77','PowerFallInstrumentation':'PASS_NATIVE_POWER_FALL_INSTRUMENTATION77'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
evidence={}
def need(value,message):
 if not value:raise AssertionError(message)
def file(name):
 p=(OUT/name).resolve();need(p.is_relative_to(OUT.resolve()) and p.is_file(),'Missing/unsafe proof: '+str(name))
 evidence[p.relative_to(OUT).as_posix()]=sha(p);return p
def read(name):return json.loads(file(name).read_text('utf-8-sig'))
def utc(value):return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
def clean(report,label):need(not any(report.get(k) for k in ['error','errors','failures','failed']),label+' failed')

def baseline_read(name,sealed):
 path=(BASE/name).resolve();need(path.is_relative_to(BASE.resolve()) and path.is_file() and sha(path)==sealed['evidence_sha256'].get(name),'Changed/unsealed76 baseline input: '+name)
 return json.loads(path.read_text('utf-8-sig'))

def bind_maps(report,sealed76,baseline):
 need(report.get('artifactSHA256'),'Evidence hash map is empty')
 for name,digest in report['artifactSHA256'].items():need(sha(file(name))==digest,'Final artifact changed: '+name)
 for name,digest in report.get('externalEvidenceSHA256',{}).items():
  path=(ROOT/name).resolve();need(path.is_relative_to(ROOT.resolve()) and path.is_file() and sha(path)==digest,'External evidence changed: '+name)
  if path.is_relative_to(BASE.resolve()):
   relative=path.relative_to(BASE.resolve()).as_posix()
   expected=baseline['summary_sha256'] if relative=='Summary.json' else baseline['source_sha256'] if relative=='Source_SHA256.json' else sealed76['evidence_sha256'].get(relative)
   need(expected==digest,'Baseline evidence is not sealed in76 Summary: '+relative)

def power_fall_native(native,old,sealed76):
 # These are actual original model results, not hashes from the new queue or
 # a duplicated implementation. Sampling/preparation must not change any turn.
 prior=baseline_read('Native/LocalCascade.json',sealed76)
 current=native['LocalCascade']
 def corpus(report):
  need(len(report['rows'])==350 and len({r['name'] for r in report['rows']})==350,'Native350-turn corpus incomplete')
  return {r['name']:(r['turnHash'],r['finalHash']) for r in report['rows']}
 need(sha(BASE/'Native/LocalCascade.json')==sealed76['evidence_sha256']['Native/LocalCascade.json'] and corpus(current)==corpus(prior),'Model turn/final hashes differ from sealed76')
 sampling=native['PowerFallSampling']
 need(sampling['compiledSourceMatchesArchive'] and sampling['rawTurnParity'] and sampling['finalSnapshotParity'],'Sampler control/parity failed')
 need(sampling['archivedMainSHA256']==old['Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs'] and sampling['archivedAdvancedSHA256']==old['Unity/Assets/HeartOfTheRain/M48/Runtime/AdvancedObstaclePresentationPure.cs'],'Sampler archived76 control source differs')
 need(sampling['familyCases']>1000 and sampling['familySamples']>20000 and sampling['actualTurns']==len(sampling['actualRows'])==18 and sampling['actualSamples']>1000 and sampling['negativeControls']==4 and sampling['syntheticDelayCases']>0 and sampling['coldFallbackSamples']>0,'Sampler fixture/fallback/signature coverage incomplete')
 need(sampling['controlSamples']==sampling['familySamples']+sampling['actualSamples']+sampling['syntheticDelayCases']+sampling['coldFallbackSamples'] and len(sampling['timings'])==6,'Sampler controls omitted cases')
 need(len({r['name'] for r in sampling['actualRows']})==18 and all(r['turnBeforeHash']==r['turnAfterHash'] and r['finalBeforeHash']==r['finalAfterHash'] and r['samples']>0 for r in sampling['actualRows']),'Actual sampler input/model parity differs')
 for row in sampling['timings']:
  need(row['pairs']>0 and len(row['legacyMs'])==len(row['currentMs'])==row['pairs'] and all(PROFILE['finite_nonnegative'](v) for v in row['legacyMs']+row['currentMs']),'Sampler paired timing source is incomplete')
 prep=native['PowerFallPreparation'];path='PairedDensity/paired_1-stone/Report.json'
 need(prep['baselineReportSHA256']==sha(BASE/path)==sealed76['evidence_sha256'][path],'Preparation proof uses unsealed resource trace')
 need(all(prep[k] for k in ['rawTurnParity','finalSnapshotMatchesAndroid','poseParity','meshParity','noAdditionalTextureLoads','workingCapsUnchanged','disposedWorkerStops','overlapDeduplicated','conflictingOwnerRejected','evictedFrameRecreated']),'Preparation parity/lifecycle guard failed')
 source_paths={'Unity/Assets/HeartOfTheRain/'+p for p in ['M46/Runtime/BoardModel.cs','M46/Runtime/LivePowerPlan.cs','M46/Runtime/ReviewPlan.cs','M46/Runtime/BoardPlayback.cs','Verification/ObstacleDensityFixture.cs']}
 need(len(prep['sourceBindings'])==5 and {b['path'] for b in prep['sourceBindings']}==source_paths and all(b['currentSHA256']==b['archivedSHA256']==old[b['path']] for b in prep['sourceBindings']),'Preparation model/planner/fixture source identity is not archived76')
 need(all(prep[k]==prep['turnHash'] for k in ['coldBeforeHash','coldAfterHash','preparedBeforeHash','preparedAfterHash']),'Preparation raw immutability fields disagree')
 archived_trace=json.loads((BASE/path).read_text('utf-8-sig'));archived_row=next(r for r in archived_trace['rows'] if r['name']=='stone_1_0_current76')
 need(prep['androidTurnHash']==archived_row['turnHash'] and prep['finalHash']==archived_row['finalHash'] and prep['rawTurnHashMatchesAndroid']==(prep['turnHash']==prep['androidTurnHash']),'Android raw/final diagnostics are misreported')
 need(prep['preparedDemandCreates']==prep['preparedDemandGeometryMisses']==0 and prep['coldCreates']>0 and prep['overlapFrames']==94 and prep['skippedEvictedAtlases']==1,'Preparation zero-demand/control coverage differs')
 need(prep['replayedFrames']==len(prep['rows'])>0 and len({r['frame'] for r in prep['rows']})==len(prep['rows']),'Preparation original-frame coverage missing')
 for row in prep['rows']:
  need(row['coldPoseHash']==row['preparedPoseHash'] and row['coldMeshHash']==row['preparedMeshHash'] and row['preparedCreates']==row['preparedGeometryMisses']==0,'Prepared replay changes a pose/mesh or reaches demand allocation')
 for frame,keys in [(1247,{'p/21/44','p/28/27'}),(1248,{'p/21/45','p/28/29'})]:
  rows=[r for r in prep['rows'] if r['frame']==frame]
  need(len(rows)==1 and set(rows[0]['coldKeys'])==keys and rows[0]['coldCreates']==2,'Original late native first-use keys not reproduced')
 need(prep['preparationFrames']>0 and prep['preparationCreates']>0 and prep['preparationBatches']==len(prep['batches'])>0,'Preparation accounting is incomplete')
 need(sum(b['frames'] for b in prep['batches'])==prep['preparationFrames'] and sum(b['spriteCreates'] for b in prep['batches'])==prep['preparationCreates'],'Preparation counters differ from batch records')
 for batch in prep['batches']:
  need(0<=batch['frames']<=16 and batch['startedWall']<=batch['finishedWall'] and PROFILE['finite_nonnegative'](batch['milliseconds']),'Preparation batch provenance/count invalid')
 # Instrumentation-specific fields are additionally validated by the new
 # device runner's shared native contract after its schema is frozen.
 instrumentation=native['PowerFallInstrumentation']
 need(instrumentation['checks']==19 and instrumentation['negativeControls']==17,'Instrumentation hierarchy/GC negative controls incomplete')

def power_fall_device(digest,source_sha256,build_finished,before,native,sealed76):
 helper=Path(__file__).with_name('run_power_fall77_device.py')
 need(helper.is_file(),'PowerFall77 runner contract is not available')
 runner=runpy.run_path(str(helper),run_name='power_fall77_contract_only')
 need('validate_report' in runner,'PowerFall77 runner lacks a strict raw validator')
 report=read('PowerFall/Report.json');installed=read('PowerFall/Installation.json')
 need(installed['serial']=='emulator-5556' and installed['apk_sha256']==installed['installed_apk_sha256']==digest,'PowerFall77 installed APK/device differs')
 need(utc(report['utc'])>=utc(installed['utc'])>=build_finished,'PowerFall77 report is stale')
 need(installed['status']=='PASS_POWER_FALL77_DEVICE_AUDIT' and installed['runtime_errors']==0 and not installed.get('error') and installed['data_unchanged'] and installed['before']==installed['after']==before,'PowerFall77 failed or changed real owner data')
 need(utc(report['utc'])<=utc(installed['finishedUtc']),'PowerFall77 report postdates its process audit')
 hashes={}
 for family in ['crate','stone']:
  old=baseline_read('Android/Density/candidate_review-'+family+'/Report.json',sealed76)
  for count in [1,45]:
   values={(r['turnHash'],r['finalHash']) for r in old['rows'] if r['crates']==count};need(len(values)==1,'Historical density model controls disagree');hashes[(family,count)]=values.pop()
 validated=runner['validate_report'](report,hashes)
 need(validated and validated==installed['validated'],'PowerFall77 raw paired/frozen controls failed or installation summary differs')
 return {'status':report['status'],'source_sha256':source_sha256,'apk_sha256':digest,'validated':validated,'runner_sha256':sha(helper),'scope':report['scope']}

def historical_attempts():
 rows=[]
 for attempt,suite in [('FirstCompileFailure','PowerFallSampling'),('FirstPreparationBaselineFailure','PowerFallPreparation')]:
  folder='Attempts/'+attempt+'/';source=read(folder+'Source_SHA256.json');read(folder+'Source_Delta.json')
  process=read(folder+'Native/'+suite+'_Process.json');snapshot=read(folder+process['sourceManifest'])
  need(source['files']==snapshot['files'] and sha(file(folder+process['sourceManifest']))==process['sourceSHA256'],'Historical failed-attempt source provenance changed')
  need(process['exitCode']!=0 and process['version'].startswith('2022.3.62f3') and utc(process['startedUtc'])<=utc(process['finishedUtc']),'Historical failed process was relabeled as success')
  file(folder+'Native/'+suite+'.log')
  row={'attempt':attempt,'suite':suite,'exit_code':process['exitCode'],'source_sha256':sha(file(folder+'Source_SHA256.json')),'scope':'Historical failed proof only; not counted toward final passing suites.'}
  if suite=='PowerFallPreparation':
   report=read(folder+'Native/'+suite+'.json');need(report['status']=='FAIL_NATIVE_POWER_FALL_PREPARATION77' and report['errors'] and report['rawTurnParity'] is False,'Original native/Android hash assertion failure was not preserved')
   row['failed_status']=report['status'];row['failed_checks']=report['checks']
  rows.append(row)
 return rows

def timing_visual_review(visual,digest,source_sha256,installation,before,continuation,sealed76,baseline):
 notes=read('Timing_Visual_Notes.json')
 need(notes['status']=='REVIEWED_POWER_FALL77_WITH_REMAINING_GATES' and notes['apk_sha256']==digest and notes['source_sha256']==source_sha256 and notes['qa_serial']=='emulator-5556' and notes.get('scope') and notes.get('limitations') and notes.get('remainingGates'),'Fresh timing review identity/scope/gates missing')
 bind_maps(notes,sealed76,baseline)
 need(visual['artifactSHA256'].get('Timing_Visual_Notes.json')==sha(file('Timing_Visual_Notes.json')),'Parent review omits final timing notes')
 for name,h in notes['artifactSHA256'].items():need(visual['artifactSHA256'].get(name)==h,'Parent review omits inspected timing artifact: '+name)
 cases=[notes['localMatch']]+notes['continuationCases']
 need(len(cases)==4 and [r['level'] for r in cases]==[4,14,31,33],'Timing review omits/repeats a current movie')
 corpus={r['name']:r for r in continuation['rows']}
 archived_native={r['name']:r for r in baseline_read('Native/LocalContinuation.json',sealed76)['rows']}
 for case in cases:
  level=case['level'];folder='Android/Cascade/visual/' if level==4 else 'ContinuationVisual/L'+str(level)+'/visual/'
  need(case['case']=='L'+str(level)+'_0_30' and case['sourceFolder']==folder,'Timing review uses wrong fixture/folder')
  if level!=4:need(case['routeContinuityReviewed'] is True and case['landingIntoIdleReviewed'] is True and case.get('visualFinding') and case.get('measurementLimitations'),'Continuity/landing review scope missing')
  installed=installation(folder+'Installation.json');report=read(folder+'Report.json')
  need(installed['data_unchanged'] and installed['before']==installed['after']==before and installed['visual_level']==report['visualLevel']==level and installed['checkpoint74_continuation'] is False and report['checkpoint74Continuation'] is False and installed['profile_model_work'] is False and report['modelWorkEnabled'] is False and report['repeats']==1 and utc(report['utc'])>=utc(installed['utc']),'Recorded current timing provenance differs')
  need(PROFILE['RUNNER']['validate_report'](report,'visual',1,require_profiling=True),'Recorded current timing spans invalid')
  row=report['rows'][0];native_name='L'+str(level)+'_match';native=corpus[native_name];old_native=archived_native[native_name]
  archived_movie=baseline_read(folder+'Report.json',sealed76);old_row=archived_movie['rows'][0]
  need(row['name']==row['baseCase']==old_row['name']==case['case'] and (row['turnHash'],row['finalHash'])==(old_row['turnHash'],old_row['finalHash']),'Fresh Android timing outcome differs from sealed76 Android fixture')
  need(all(native[k]==old_native[k] for k in ['refinedTurnHash','refinedFinalHash','refinedSeconds']),'Fresh native timing outcome/schedule differs from sealed76 native fixture')
  need(abs(row['scheduledSeconds']-old_row['scheduledSeconds'])<.001 and abs(row['scheduledSeconds']-native['refinedSeconds'])<.001,'Timing movie schedule differs from the unchanged Android/native schedules')
  movie=folder+'HR_NaturalCascade.mp4';index_path=case['ptsIndex'];index=read(index_path)
  need(index['status']=='EXTRACTED_ORIGINAL_PTS_FRAMES_FOR_MANUAL_REVIEW' and index['checkpoint']==77 and index['apk_sha256']==digest and index['source_sha256']==source_sha256 and index['case']==case['case'] and index['visualLevel']==level and index['checkpoint74Continuation'] is False,'Endpoint index is not fresh77')
  need(index['video']==file(movie).relative_to(ROOT).as_posix() and index['sha256']==sha(file(movie))==notes['artifactSHA256'].get(movie) and index['reportSHA256']==sha(file(folder+'Report.json')) and index['installationSHA256']==sha(file(folder+'Installation.json')),'PTS index source movie/report/install binding differs')
  need(notes['artifactSHA256'].get(index_path)==sha(file(index_path)) and len(index['frames'])>1 and all(a['pts']<b['pts'] for a,b in zip(index['frames'],index['frames'][1:])),'PTS source/index chronology invalid')
  def endpoint_bracket(frame_key,pts_key):
   selected=case[frame_key];need(len(selected)==2 and all(isinstance(i,int) and not isinstance(i,bool) and 1<=i<=len(index['frames']) for i in selected) and selected[1]==selected[0]+1,'Manual endpoint bracket does not use adjacent original frames')
   values=[]
   for i in selected:
    original=index['frames'][i-1];path=(ROOT/original['file']).resolve();need(path.is_relative_to(OUT.resolve()),'Endpoint image leaves checkpoint77')
    relative=path.relative_to(OUT.resolve()).as_posix();need(original['sha256']==sha(file(relative))==notes['artifactSHA256'].get(relative),'Inspected endpoint original hash differs');values.append(original['pts'])
   need(len(case[pts_key])==2 and all(abs(a-b)<.000001 for a,b in zip(values,case[pts_key])),'Endpoint PTS values differ from originals')
   return values
  contact=endpoint_bracket('contactFrames','contactBracketPts');reaction=endpoint_bracket('firstVisibleReactionFrames','firstVisibleReactionBracketPts')
  expected=[(reaction[0]-contact[1])*1000,(reaction[1]-contact[0])*1000]
  need(len(case['contactToReactionBoundMs'])==2 and all(abs(a-b)<.001 for a,b in zip(expected,case['contactToReactionBoundMs'])),'Contact/reaction bounds discard endpoint uncertainty')
 swap=notes['acceptedSwap'];onset=swap['onsetBracketPts'];completion=swap['completionBracketPts']
 need(swap['nativeScheduledMs']==120 and len(onset)==len(completion)==len(swap['visibleDurationBoundMs'])==2 and onset==sorted(onset) and completion==sorted(completion),'Swap review schedule/endpoints missing')
 need(all(abs(a-b)<.001 for a,b in zip([(completion[0]-onset[1])*1000,(completion[1]-onset[0])*1000],swap['visibleDurationBoundMs'])),'Swap duration fails two-endpoint arithmetic')
 l4=read(notes['localMatch']['ptsIndex']);pts={r['pts'] for r in l4['frames']}
 need(all(v in pts for v in onset+completion),'Swap endpoints are absent from original PTS frames')
 return notes
def main(publish=False):
 evidence.clear()
 frozen=read('Source_SHA256.json');current={p.relative_to(ROOT).as_posix():sha(p) for d in ['Assets','Packages','ProjectSettings'] for p in (ROOT/'Unity'/d).rglob('*') if p.is_file()}
 need(frozen['files']==current,'Current Unity inputs changed after freeze')
 old=read('Baseline76_Source_SHA256.json')['files'];delta=read('Source_Delta.json')
 allowed={'Unity/Assets/HeartOfTheRain/'+p for p in ['M46/Runtime/BoardPresentation.cs','M46/Runtime/M46AtlasBank.cs','M47/Runtime/EffectMeshBatcher.cs','M47/Runtime/GameplayScreen.cs']}
 added={'Unity/Assets/HeartOfTheRain/'+p+s for p in ['M47/Runtime/GameplayPowerFramePreparation.cs','Verification/PowerFall76Control.cs','Verification/PowerFall77Probe.cs','Verification/Editor/PowerFallSamplingVerification.cs','Verification/Editor/PowerFallPreparationVerification.cs'] for s in ['', '.meta']}
 need(set(delta['changed_existing'])==allowed and set(delta['added'])==added and not (old.keys()-current.keys()) and not delta['removed'],'Source allowlist/removals differ')
 guids={}
 for p in current:
  if p.endswith('.meta'):
   match=re.search(r'^guid: ([0-9a-f]{32})$',(ROOT/p).read_text('utf-8-sig'),re.M)
   if match:guids.setdefault(match[1],[]).append(p)
 for p in added:
  if p.endswith('.meta'):
   match=re.search(r'^guid: ([0-9a-f]{32})$',(ROOT/p).read_text('utf-8-sig'),re.M)
   need(match and guids[match[1]]==[p],'New GUID absent/duplicated: '+p)
 need(not delta['removed'] and not any(p.endswith('.meta') or '/Resources/' in p or '/Packages/' in p or '/ProjectSettings/' in p for p in delta['changed_existing']),'Protected inputs changed')
 need(delta['changed_existing']==sorted(k for k in old.keys()&current.keys() if old[k]!=current[k]) and delta['added']==sorted(current.keys()-old.keys()),'Source delta mismatches')
 baseline_proof=read('Baseline76.json')
 need(baseline_proof['status']=='PRESERVED_VERIFIED76_BASELINE' and baseline_proof['source_inputs']==len(old),'Baseline identity/count differs')
 need(baseline_proof['source_sha256']==sha(file('Baseline76_Source_SHA256.json'))==sha(BASE/'Source_SHA256.json'),'Baseline source binding differs')
 need(sha(BASE/'Summary.json')==baseline_proof['summary_sha256'],'Sealed76 summary changed')
 need(sha(file('Baseline76_Summary.json'))==baseline_proof['summary_sha256'],'Copied baseline76 summary changed')
 sealed76=json.loads((BASE/'Summary.json').read_text('utf-8-sig'))
 need(sealed76['source_checkpoint']==76 and sealed76['source_sha256']==baseline_proof['source_sha256'] and sealed76['apk_sha256']==baseline_proof['apk_sha256'],'Sealed76 identity differs')

 legacy_path=BASE/'Baseline75_Source_SHA256.json'
 need(sha(legacy_path)==sealed76['evidence_sha256']['Baseline75_Source_SHA256.json'],'Historical75 control source manifest changed')
 legacy75=json.loads(legacy_path.read_text('utf-8-sig'))['files']
 baseline_apk=(ROOT/baseline_proof['apk_archive']).resolve()
 need(baseline_apk.is_relative_to(ROOT.resolve()) and sha(baseline_apk)==baseline_proof['apk_sha256'],'Archived76 APK changed')
 archive=(ROOT/baseline_proof['source_archive']).resolve()
 for name in allowed:
  need(archive.is_relative_to(ROOT.resolve()) and sha(archive/name)==old[name],'Archived changed76 source differs: '+name)
 need(read('Build_Source_SHA256.json')['files']==current,'Build did not start with frozen inputs')
 build=read('Android_Build.json');process=read('AndroidBuild_Process.json');artifact=read('APK_Artifact.json');pack=read('APK_Packaging.json')
 clean(build,'Development build');need(build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['unity']=='2022.3.62f3' and build['errors']==0 and process['exitCode']==0 and not process['timedOut'],'Development build failed')
 apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk';digest=sha(apk)
 need(digest==artifact['sha256']==pack['afterSHA256'] and apk.stat().st_size==artifact['bytes']==pack['afterBytes'],'APK identity differs')
 need(all(artifact[k] for k in ['zipalign4KiBPass','developmentSignatureVerifies','elf16KiBLoadSegmentsPass']) and pack['sameSignerCertificate'] and not pack['changedNonSignatureEntries'],'APK packaging failed')
 need('Errors: 0' in file('Build_Import_Audit.txt').read_text('utf-8-sig'),'Import guard failed')
 release=read('Android_Release_Build.json');rp=read('AndroidReleaseBuild_Process.json');ra=read('Release_APK_Artifact.json')
 release_apk=(ROOT/ra['path']).resolve();need(release_apk.is_relative_to(ROOT.resolve()) and release_apk.is_file(),'Release APK path is outside the workspace or missing')
 clean(release,'Nondevelopment build');need(release['status']=='PASS_ANDROID_RELEASE_COMPILE_BUILD' and release['unity']=='2022.3.62f3' and release['errors']==0 and rp['exitCode']==0 and not rp['timedOut'] and sha(release_apk)==ra['sha256'],'Nondevelopment build failed')
 need(read('Release_Source_SHA256.json')['files']==current,'Release source differs')
 need(ra['status']=='RECORDED_NATIVE_NON_DEVELOPMENT_BUILD_ARTIFACT' and ra['sourceManifest']=='Release_Source_SHA256.json' and ra['sourceSHA256']==sha(file(ra['sourceManifest'])) and ra['bytes']==release_apk.stat().st_size,'Release artifact source/status/byte metadata differs')
 need(utc(rp['finishedUtc'])<=utc(ra['utc'])<=utc(process['startedUtc']),'Release artifact metadata is stale or postdates development-build start')
 need('Errors: 0' in file('Release_Build_Import_Audit.txt').read_text('utf-8-sig'),'Release import guard failed')
 native={}
 for name,status in NATIVE.items():
  report,run=read('Native/'+name+'.json'),read('Native/'+name+'_Process.json');clean(report,name)
  need(report['status']==status and run['exitCode']==0 and not run['timedOut'] and run['version'].startswith('2022.3.62f3'),name+' failed/stale/unpinned')
  need(utc(frozen['utc'])<=utc(run['startedUtc'])<=utc(report['utc'])<=utc(run['finishedUtc']),name+' source/report chronology differs')
  need(read(run['sourceManifest'])['files']==current and sha(file(run['sourceManifest']))==run['sourceSHA256'],name+' ran different inputs')
  need(CONTRACT['BASE_CONTRACT']['checks'](report)>0,name+' ran no checks');native[name]=report
 need(len(native)==29,'Missing native suite')
 native_runner=read('Native_Runner.json')
 need(native_runner['status']=='PASS_SELECTED_NATIVE_GAMEPLAY77_SUITES' and len(native_runner['runs'])==29 and {r['mode'] for r in native_runner['runs']}==set(native),'Native runner did not finish all29 suites')
 for run in native_runner['runs']:need(run==read('Native/'+run['mode']+'_Process.json'),'Native runner/process provenance differs: '+run['mode'])
 need(utc(process['startedUtc'])>=max(utc(read('Native/'+name+'_Process.json')['finishedUtc']) for name in native) and utc(process['startedUtc'])<=utc(build['utc'])<=utc(process['finishedUtc']),'Native/build chronology differs')
 need(utc(frozen['utc'])<=utc(rp['startedUtc'])<=utc(release['utc'])<=utc(rp['finishedUtc']),'Release chronology differs')
 need(max(utc(read('Native/'+name+'_Process.json')['finishedUtc']) for name in native)<=utc(rp['startedUtc'])<=utc(rp['finishedUtc'])<=utc(process['startedUtc']),'Native/release/development order differs')
 command=native['SmoothnessCommand']
 need(command['modelCases']==350 and command['queueComparisons']==1400 and command['sourceFiles']==3 and all(command[k] for k in ['exactQueueParity','rawInputUnchanged','rawTurnParity','finalSnapshotParity','compiledSourceMatchesArchive']),'Command construction parity coverage missing')
 need(len(command['sourceBindings'])==3 and all(b['compiledExactAdaptation'] and b['sha256']==legacy75[b['path']] for b in command['sourceBindings']),'Archived75 command control source binding differs')
 need(len(command['timings'])==8 and all(len(r['pairs'])==12 for r in command['timings']),'Native paired construction controls missing')
 effects=native['EffectBatchChecks']
 need(effects['transformParityFrames']==len(effects['transformParityRows'])==65 and len(effects['transformPixelRows'])==2 and all(r['differingPixels']==r['maxChannelDelta']==0 for r in effects['transformPixelRows']) and len(effects['transformRows'])==15 and all(r['iterations']==64 for r in effects['transformRows']),'Archived75 mesh/pixel/CPU proof incomplete')
 need(effects['frozen75SourceSHA256']==legacy75['Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs'],'Archived75 effect source differs')
 for name in ['LocalCascade','LocalContinuation']:
  need(native[name]['modelCases']==350 and native[name]['rawTurnParity'] and native[name]['finalSnapshotParity'],name+' model coverage incomplete')
 need(native['LocalContinuation']['acceptedHandoffs']==4 and native['LocalContinuation']['terminalHandoffs']==3,'Continuation coverage changed')
 continuation=native['LocalContinuation']
 need(all(continuation[k] for k in ['checkpoint75QueueParity','checkpoint75DecisionParity','compiledCheckpoint75SourceMatchesArchive']) and continuation['checkpoint75Comparisons']>=388 and continuation['checkpoint75GuardComparisons']>=43 and continuation['checkpoint75PublicDecisionComparisons']>0,'Archived75 continuation/guard/decision proof incomplete')
 need(native['MixedSwapChecks']['protectedBirths']==360 and native['MixedSwapChecks']['chainedBirths']==0,'Power birth protection regressed')
 before=read('Android/Before.json')
 for name in CONTRACT['TOOLS']:
  audit=read('Android/'+name+'_Data_Audit.json')
  need(audit['exit_code']==0 and audit['data_unchanged'] and audit['before']==audit['after']==before and audit['apk_sha256']==digest,name+' failed, different APK or changed saves')
 def installation(path):
  v=read(path);need(v['serial']=='emulator-5556' and v.get('apk_sha256',v.get('sha256'))==digest,path+' wrong APK/device')
  if 'installed_apk_sha256' in v:need(v['installed_apk_sha256']==digest,path+' installed identity differs')
  if 'data_unchanged' in v:need(v['data_unchanged'] and v['before']==v['after']==before,path+' changed saves')
  need(utc(v['utc'])>=utc(process['finishedUtc']),path+' predates build');return v
 fluid=read('Android/Fluidity/Measurement.json');clean(fluid,'Fluidity');fi=installation('Android/Fluidity/Installation.json')
 need(fluid['status']=='RECORDED_NATIVE_FLUIDITY' and fluid['isolatedProfile'] and fluid['launchCleared'] and {r['name'] for r in fluid['phases']}==CONTRACT['FLUIDITY_PHASES'] and len(fluid['phases'])==8 and utc(fluid['utc'])>=utc(fi['utc']),'Fluidity scope differs')
 touch=read('Android/Touch/Report.json');clean(touch,'Touch');need(touch['apk_sha256']==digest and touch['serial']=='emulator-5556' and len(touch['cases'])==8 and {r['mode'] for r in touch['cases']}==CONTRACT['TOUCH'],'Touch scope differs')
 need(touch['status']=='CAPTURED_GAMEPLAY_AUDIT_REQUIRES_VISUAL_REVIEW' and utc(touch['utc'])>=utc(process['finishedUtc']),'Touch is stale')
 for row in touch['cases']:
  clean(row,row['mode']);need(row==read('Android/Touch/'+row['mode']+'_Report.json') and utc(row['utc'])>=utc(touch['utc']),'Native touch source differs/stale')
  need(row['status']=='PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT' and row['launchCleared'] and row['accepted'],'Touch case rejected/hidden')
  if row['mode'] in CONTRACT['MIXED']:need(row['sourceActivated'] and row['protectedBirth'] and not row['chained'],'Power protection failed')
  need(sha(file('Android/Touch/'+row['mode']+'_Before.png'))!=sha(file('Android/Touch/'+row['mode']+'_After.png')),'Touch captures unchanged/obscured')
 timing={}
 for variant in ['measure','visual']:
  report=read('Android/Cascade/'+variant+'/Report.json');installed=installation('Android/Cascade/'+variant+'/Installation.json')
  need(utc(report['utc'])>=utc(installed['utc']) and not report['modelWorkEnabled'] and not report['checkpoint74Continuation'] and report['visualLevel']==4 and report['repeats']==1,'Default cascade stale/control enabled')
  baseline=baseline_read('Android/Cascade/'+variant+'/Report.json',sealed76)
  hashes={r['baseCase']:(r['turnHash'],r['finalHash']) for r in baseline['rows']}
  timing[variant]=PROFILE['validate'](report,variant,hashes)
 density={}
 for family in ['crate','stone','gate','tiles']:
  path='Android/Density/candidate_review-'+family+'/'
  report=read(path+'Report.json');installed=installation(path+'Installation.json');need(utc(report['utc'])>=utc(installed['utc']) and report['detailedDrawCosts'] is True,'Default density is stale or coarse')
  baseline=baseline_read(path+'Report.json',sealed76);hashes={r['name']:(r['turnHash'],r['finalHash']) for r in baseline['rows']}
  density[family]=PROFILE['validate_density'](report,family,hashes)
 regression=read('Android/Regression/Regression.json');clean(regression,'Full Android regression');ri=installation('Android/Regression/Installation.json')
 need(regression['status']=='PASS_NATIVE_REGRESSION' and regression['boards']==50 and regression['checks']>=1716 and regression['clips']>=354 and regression['actions']>=408 and regression['labels']>=14105 and len(regression['damageFamilies'])==8 and utc(regression['utc'])>=utc(ri['utc']),'Campaign regression incomplete')
 need({'Native refill button spends 900 and fills all five lives','Repeated native refill callback charges exactly once','Confirmed decline charges exactly one life, no coins, and opens retry pre-level'}<=set(regression['passed']),'Life/Continue settlement proof missing')
 idle=read('Android/Regression/M70_Device.json');clean(idle,'Live idle')
 idle_controls=CONTRACT['idle_device_controls'](idle,regression,ri)
 need(idle_controls,'Bounded live idle proof missing')
 # New77 native/resource/device contracts are deliberately required before any publication.
 history=historical_attempts()
 power_fall_native(native,old,sealed76)
 device=power_fall_device(digest,sha(file('Source_SHA256.json')),utc(process['finishedUtc']),before,native,sealed76)
 performance=read('Performance_Analysis.json')
 need(performance['status']=='ANALYZED_POWER_FALL77_WITH_REMAINING_GATES' and performance['apk_sha256']==digest and performance['source_sha256']==sha(file('Source_SHA256.json')) and performance.get('remainingGates'),'Missing/bad power-fall analysis or remaining gates')
 analyzer=Path(__file__).with_name('analyze_power_fall77_performance.py')
 expected=runpy.run_path(str(analyzer),run_name='power_fall77_recompute')['build'](OUT)
 need({k:v for k,v in performance.items() if k!='utc'}=={k:v for k,v in expected.items() if k!='utc'},'Power-fall analysis differs from recomputed raw proof')
 bind_maps(performance,sealed76,baseline_proof)
 visual=read('Visual_Review.json')
 need(visual['status']=='REVIEWED_SAMPLED_GAMEPLAY77' and visual['apk_sha256']==digest and visual['source_sha256']==sha(file('Source_SHA256.json')) and visual['qa_serial']=='emulator-5556' and visual.get('scope') and visual.get('limitations'),'Actual final77 visual review missing/misbound')
 bind_maps(visual,sealed76,baseline_proof)
 need(visual['artifactSHA256'].get('Performance_Analysis.json')==sha(file('Performance_Analysis.json')),'Visual review omits final performance analysis')
 timing_review=timing_visual_review(visual,digest,sha(file('Source_SHA256.json')),installation,before,native['LocalContinuation'],sealed76,baseline_proof)
 manifest=read('RegressionVisual/Manifest.json')
 need(manifest['status']=='PRESENTED_FOR_VISUAL_REVIEW' and set(manifest['groups'])=={'BoardMasks','TilesTools','Powers','PowerPairs','ObstacleRoutes','ConnectedFlow'},'Regression gallery incomplete')
 inspected={p for group in manifest['sheets'].values() for p in group}
 originals={'Android/Regression/'+p for group in manifest['groups'].values() for p in group}
 need(len(inspected)==14 and all(visual['artifactSHA256'].get(p)==sha(file(p)) for p in inspected|originals),'Reviewed final regression sheets/originals incomplete')
 result={'status':'PASS_TARGETED_POWER_FALL77_WITH_REMAINING_PERFORMANCE_GATES','utc':datetime.now(timezone.utc).isoformat(),'source_checkpoint':77,'source_inputs':len(current),'source_sha256':sha(file('Source_SHA256.json')),'baseline_checkpoint':76,'baseline_summary_sha256':baseline_proof['summary_sha256'],'baseline_apk_sha256':baseline_proof['apk_sha256'],'baseline_source_sha256':baseline_proof['source_sha256'],'apk_sha256':digest,'apk_bytes':artifact['bytes'],'native_suites':len(native),'native_checks':sum(CONTRACT['BASE_CONTRACT']['checks'](r) for r in native.values()),'non_development_compile_build_passed':True,'qa_data_unchanged':True,'main_apk_updated':False,'android':{'stages':9,'boards':50,'checks':regression['checks'],'actions':regression['actions'],'clips':regression['clips'],'density_turns':40,'fluidity_phases':8,'touch_cases':8},'power_fall':device,'native_preparation_android_raw_turn_hash_matches':native['PowerFallPreparation']['rawTurnHashMatchesAndroid'],'historical_attempts':history,'performance_analysis':performance,'visual_scope':visual['scope'],'limits':visual['limitations'],'collector_sha256':sha(Path(__file__)),'evidence_sha256':dict(sorted(evidence.items()))}
 if publish:
  for p in [OUT/'Summary.json',OUT.parent/'Verification_Summary.json']:p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  checkpoint={'utc':result['utc'],'status':result['status'],'source_checkpoint':77,'installed_checkpoint':64,'qa_installed_checkpoint':77,'source_sha256':result['source_sha256'],'android_apk_sha256':digest,'android_apk_matches_current_source':True,'main_installed_apk_matches_current_source':False,'review':'Codex_Handoff/Documentation/77_POWER_FALL_PREPARATION_REVIEW.md','summary':'Verification/Evidence/Gameplay77/Summary.json','scope':'Targeted power-fall work verified on QA only; remaining performance, fresh-reference and physical-device gates stay explicit.'}
  (OUT.parent/'Native_Source_Checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ['performance_analysis','evidence_sha256']},indent=2))
 return result

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--publish',action='store_true');args=parser.parse_args();main(publish=args.publish)
