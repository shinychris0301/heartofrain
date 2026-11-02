"""Fail closed on current-source native, build, QA, power-fall and visual proof."""
import hashlib,json,math,re,runpy,statistics
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Gameplay78';BASE=ROOT/'Verification/Evidence/Gameplay77'
HIST76=ROOT/'Verification/Evidence/Gameplay76';HIST75=ROOT/'Verification/Evidence/Gameplay75'
CONTRACT=runpy.run_path(str(Path(__file__).with_name('collect_gameplay75_results.py')),run_name='contracts_only')
PROFILE=CONTRACT['PROFILE_CONTRACT'];NATIVE=dict(CONTRACT['NATIVE'])|{'SmoothnessCommand':'PASS_NATIVE_SMOOTHNESS_COMMAND76','PowerFallSampling':'PASS_NATIVE_POWER_FALL_SAMPLING77','PowerFallPreparation':'PASS_NATIVE_POWER_FALL_PREPARATION77','PowerFallInstrumentation':'PASS_NATIVE_POWER_FALL_INSTRUMENTATION77','ModelWork78':'PASS_NATIVE_MODEL_WORK78','DenseSubmission':'PASS_NATIVE_DENSE_SUBMISSION78','CommandPreparation78':'PASS_NATIVE_COMMAND_PREPARATION78'}
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

def finite(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0

def close(a,b):return finite(a) and finite(b) and math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-8)

def signature(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None

def command_cost78(row,label):
 value=row['enqueueCost'];stages=('buildMs','resourcePlanMs','nextMs','dependenciesMs','prefetchMs')
 need(all(finite(value[k]) for k in stages+('totalMs',)) and sum(value[k] for k in stages)<=value['totalMs']+.15 and value['totalMs']<=row['acceptMs']+.15,label+' resource-plan/command decomposition differs')

def baseline_read(name,sealed):
 path=(BASE/name).resolve();need(path.is_relative_to(BASE.resolve()) and path.is_file() and sha(path)==sealed['evidence_sha256'].get(name),'Changed/unsealed77 baseline input: '+name)
 return json.loads(path.read_text('utf-8-sig'))

def historical_chain(sealed77,baseline):
 """Seal old controls through their published parent, never relabel their domain."""
 contexts={77:(BASE,sealed77,baseline['summary_sha256'],baseline['source_sha256'])}
 parent=sealed77;parent_root=BASE
 for checkpoint,root in [(76,HIST76),(75,HIST75)]:
  label='Baseline'+str(checkpoint)
  summary_copy=parent_root/(label+'_Summary.json');source_copy=parent_root/(label+'_Source_SHA256.json')
  if checkpoint==76:
   need(sha(summary_copy)==parent['evidence_sha256'].get(summary_copy.name)==parent['baseline_summary_sha256'],'Historical76 summary chain differs')
   need(sha(source_copy)==parent['evidence_sha256'].get(source_copy.name)==parent['baseline_source_sha256'],'Historical76 source chain differs')
  else:
   external=parent['baseline_external_sha256'];prefix='Verification/Evidence/Gameplay75/'
   need(sha(summary_copy)==parent['baseline_summary_sha256']==external[prefix+'Summary.json'],'Historical75 external summary chain differs')
   need(sha(source_copy)==parent['evidence_sha256'].get(source_copy.name)==external[prefix+'Source_SHA256.json'],'Historical75 source chain differs')
  need(sha(root/'Summary.json')==sha(summary_copy) and sha(root/'Source_SHA256.json')==sha(source_copy),'Published historical source/summary changed: '+str(checkpoint))
  old=json.loads(summary_copy.read_text('utf-8-sig'));need(old['source_checkpoint']==checkpoint,'Wrong historical checkpoint')
  contexts[checkpoint]=(root,old,sha(summary_copy),sha(source_copy));parent=old;parent_root=root
 return contexts


def historical_read(contexts,checkpoint,name):
 root,sealed,summary_sha,source_sha=contexts[checkpoint];path=(root/name).resolve()
 need(path.is_relative_to(root.resolve()) and path.is_file(),'Missing historical input: '+name)
 expected=summary_sha if name=='Summary.json' else source_sha if name=='Source_SHA256.json' else sealed['evidence_sha256'].get(name)
 need(sha(path)==expected,'Historical input is changed/unsealed: '+str(checkpoint)+'/'+name)
 return json.loads(path.read_text('utf-8-sig'))


def bind_maps(report,sealed77,baseline):
 need(report.get('artifactSHA256'),'Evidence hash map is empty')
 for name,digest in report['artifactSHA256'].items():need(sha(file(name))==digest,'Final artifact changed: '+name)
 contexts=historical_chain(sealed77,baseline)
 for name,digest in report.get('externalEvidenceSHA256',{}).items():
  path=(ROOT/name).resolve();need(path.is_relative_to(ROOT.resolve()) and path.is_file() and sha(path)==digest,'External evidence changed: '+name)
  for checkpoint,(root,sealed,summary_sha,source_sha) in contexts.items():
   if path.is_relative_to(root.resolve()):
    relative=path.relative_to(root.resolve()).as_posix();expected=summary_sha if relative=='Summary.json' else source_sha if relative=='Source_SHA256.json' else sealed['evidence_sha256'].get(relative)
    need(expected==digest,'Historical evidence is not sealed in its published Summary: '+str(checkpoint)+'/'+relative)


def targeted_native78(native,old,sealed77):
 """Validate new proof scopes without requiring favorable performance numbers."""
 model=native['ModelWork78'];model_paths={'Unity/Assets/HeartOfTheRain/'+p for p in ['M46/Runtime/BoardModel.cs','M46/Runtime/LivePowerPlan.cs','M48/Runtime/AdvancedObstacleRulesPure.cs']}
 need(model['modelCases']==350 and model['pairCases']==70 and model['plannerCases']==110 and model['snapshotCases']>=13 and model['invalidCases']>=9,'Native78 model/snapshot/invalid/pair/planner coverage missing')
 need(all(model[k] for k in ['rawParity','finalParity','checkpointParity','dictionaryParity','controlSourceParity']),'Native78 model equivalence failed')
 need(model['controlSourceSHA256']==sha(ROOT/'Unity/Assets/HeartOfTheRain/Verification/Model77Control78.cs') and model['verificationSourceSHA256']==sha(ROOT/'Unity/Assets/HeartOfTheRain/Verification/Editor/ModelWork78Verification.cs'),'Native78 model proof does not bind actual compiled control/test')
 need(len(model['currentProductionSourceBindings'])==3 and {r['path'] for r in model['currentProductionSourceBindings']}==model_paths,'Native78 model source coverage differs')
 for row in model['currentProductionSourceBindings']:need(row['currentSHA256']==sha(ROOT/row['path']) and row['archived77SHA256']==old[row['path']],'Native78 model source bytes differ')
 need(len(model['sources'])==4 and {r['path'] for r in model['sources']}=={'SnapshotFromScratch','Validate','ValidateFootprints','LivePowerPlan'} and all(r['exact'] and r['sha256']==r['compiledBodySHA256'] and signature(r['sha256']) for r in model['sources']),'Native78 exact77 helper controls are incomplete')
 prior=baseline_read('Native/ModelCommands.json',sealed77);need(prior['status']=='PASS_NATIVE_MODEL_COMMANDS75' and len(prior['rows'])==350,'Sealed77 native model corpus missing')
 expected={r['name']:r for r in prior['rows']};need(len(model['rows'])==350 and {r['name'] for r in model['rows']}==set(expected),'Native78 model corpus names differ')
 for row in model['rows']:
  old_row=expected[row['name']];need(row['rawHash']==old_row['turnHash'] and row['finalHash']==old_row['finalHash'] and row['checkpointHash']==old_row['checkpointHash'] and row['dictionaryOrder']==old_row['dictionaryOrder'] and row['steps']>0,'Native78 raw/final/RNG/dictionary outcome differs: '+row['name'])
  counts=('snapshotCalls','copiedPieces','validationCalls','footprintCalls','matchCalls','gravityCalls','verticalCalls','activationCalls','planningCalls','legalQueryCalls')
  need(all(isinstance(row['work'][k],int) and row['work'][k]>=0 and row['work'][k]==row['controlWork'][k] for k in counts),'Native78 deterministic model work counts differ')
 names={'L4_match','L14_match','L31_match','L33_match','L1_three_rocket_chain','L1_orb_rocket','L1_golden_bomb','L26_power7'}
 need(len(model['timings'])==8 and {r['name'] for r in model['timings']}==names,'Native78 matched model timing fixtures differ')
 for row in model['timings']:
  pairs=row['pairs'];need(len(pairs)==12 and [p['index'] for p in pairs]==list(range(12)) and [p['controlFirst'] for p in pairs]==[i%2==0 for i in range(12)],'Native78 model AB/BA order missing')
  for pair in pairs:need(all(finite(pair[k]) for k in ['controlMs','currentMs']) and all(isinstance(pair[k],int) and pair[k]>=0 for k in ['controlCollections','currentCollections']),'Native78 model timing/GC sample invalid')
  for branch in ['control','current']:
   values=[p[branch+'Ms'] for p in pairs];need(close(row[branch+'MedianMs'],statistics.median(values)) and close(row[branch+'MaxMs'],max(values)),'Native78 model timing summary differs')
  need(row['slowerPairs']==sum(p['currentMs']>p['controlMs'] for p in pairs),'Native78 slower model pairs omitted')

 dense=native['DenseSubmission']
 need(dense['compiledSourceMatchesArchive'] and dense['archivedSourceSHA256']==old['Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs'] and signature(dense['compiledBodySHA256']),'Dense submission exact77 source binding differs')
 need(dense['midFrameSwitchOwnership'] and dense['disposedOwnershipReleased'] and dense['negativeControls']==1 and dense.get('memoryScope'),'Dense submission ownership/signature/memory controls missing')
 need(dense['fixtures']==9 and dense['parityFrames']==len(dense['parityRows'])==135 and len({r['name'] for r in dense['parityRows']})==135,'Dense submission fixture/upload-state coverage differs')
 for row in dense['parityRows']:need(row['archivedHash']==row['arrayHash']==row['controlHash'] and signature(row['arrayHash']) and row['quads']>=0 and row['meshes']>=0,'Dense submission mesh/UV/color/order/depth parity differs')
 need(len(dense['pixelRows'])==2 and {r['name'] for r in dense['pixelRows']}=={'actual_dense','rotated_flipped_scaled_tinted'} and all(r['differingPixels']==r['maxChannelDelta']==0 for r in dense['pixelRows']),'Dense submission strict pixels differ')
 frames={'Dense77.png','Dense78.png','DenseControl.png','Transforms77.png','Transforms78.png','TransformsControl.png'}
 need(len(dense['frames'])==6 and set(dense['frames'])==frames,'Dense submission pixel plates missing')
 for frame in frames:file('Native/DenseSubmission/Artifacts/'+frame)
 need(len(dense['timings'])==9 and len({r['name'] for r in dense['timings']})==9,'Dense submission CPU fixtures missing')
 for row in dense['timings']:
  need(row['pairs']==64 and row.get('scope'),'Dense submission warmed timing scope missing')
  for branch in ['archived','array','control']:
   for stage in ['Add','Upload','Frame']:
    values=row[branch+stage+'Ms'];need(len(values)==64 and all(finite(v) for v in values) and close(row[branch+stage+'MedianMs'],statistics.median(values)),'Dense submission raw samples/median differ')
   values=sorted(row[branch+'FrameMs']);need(close(row[branch+'FrameP95Ms'],values[math.ceil(.95*64)-1]),'Dense submission P95 differs')
  need(row['currentSlowerPairs']==sum(c>a for c,a in zip(row['arrayFrameMs'],row['archivedFrameMs'])) and row['controlSlowerPairs']==sum(c>a for c,a in zip(row['arrayFrameMs'],row['controlFrameMs'])),'Dense submission slower pairs omitted')

 resources=native['CommandPreparation78']
 need(all(resources[k] for k in ['compiledSourceMatchesArchive','pathSetParity','pathOrderParity','rawTurnParity','queueUnchanged','evictionReadinessPreserved','ownerReloadPreserved','legacyControlPreserved']),'Command resource parity/lifecycle controls failed')
 need(resources['archivedMethodSHA256']==resources['compiledMethodSHA256'] and signature(resources['archivedMethodSHA256']),'Resource exact77 method control differs')
 effect_path='Unity/Assets/HeartOfTheRain/M48/Runtime/EffectResourcesPure.cs'
 need(sha(ROOT/effect_path)==old[effect_path] and resources['effectResourcesSHA256']==hashlib.sha256((ROOT/effect_path).read_bytes().decode('utf-8-sig').encode('utf-8')).hexdigest(),'Typed dependency walker changed')
 need(resources['authoredTurns']==350 and resources['queues']==len(resources['rows'])>=700 and resources['phaseComparisons']>700 and resources['compositePhases']>0 and resources['continuedMotions']>0 and resources['syntheticCases']>=14,'Command resource natural/composite/continued/guard coverage missing')
 for row in resources['rows']:need(row['queueBeforeHash']==row['queueAfterHash'] and signature(row['wholePathsHash']) and row['phases']>=0 and row['paths']>=0,'Command dependency construction mutated the queue')
 resource_names={'L4_match','L14_match','L31_match','L33_match','L26_power4','L26_power7','L26_power16','L26_power21'}
 need(len(resources['benchmarks'])==24 and {r['name'] for r in resources['benchmarks']}==resource_names,'Command resource complete timing workloads missing')
 scenarios={'initial_phase_and_whole_queue','all_phase_entries','all_phase_entries_plus_two_retry_lookups'}
 for name in resource_names:need({r['scenario'] for r in resources['benchmarks'] if r['name']==name}==scenarios,'A complete resource workload is omitted')
 for row in resources['benchmarks']:
  need(row['blocks']==8 and row['iterations']==16 and row['currentWalkerCalls']==row['phases'],'Resource paired workload/count differs')
  n=row['phases'];walkers=(2 if n else 1) if row['scenario']=='initial_phase_and_whole_queue' else n+1 if row['scenario']=='all_phase_entries' else n*3+1
  need(row['legacyWalkerCalls']==walkers,'Resource legacy workload omits traversal/retry calls')
  for branch in ['legacy','current']:
   values=row[branch+'Blocks'];need(len(values)==8 and all(finite(v) and v>0 for v in values) and close(row[branch+'MedianMs'],statistics.median(values)),'Resource complete raw timing/median differs')

def power_fall_native(native,old,sealed77,contexts):
 old76=historical_read(contexts,76,'Source_SHA256.json')['files']
 # These are actual original model results, not hashes from the new queue or
 # a duplicated implementation. Sampling/preparation must not change any turn.
 prior=baseline_read('Native/LocalCascade.json',sealed77)
 current=native['LocalCascade']
 def corpus(report):
  need(len(report['rows'])==350 and len({r['name'] for r in report['rows']})==350,'Native350-turn corpus incomplete')
  return {r['name']:(r['turnHash'],r['finalHash']) for r in report['rows']}
 need(sha(BASE/'Native/LocalCascade.json')==sealed77['evidence_sha256']['Native/LocalCascade.json'] and corpus(current)==corpus(prior),'Model turn/final hashes differ from sealed77')
 sampling=native['PowerFallSampling']
 need(sampling['compiledSourceMatchesArchive'] and sampling['rawTurnParity'] and sampling['finalSnapshotParity'],'Sampler control/parity failed')
 need(sampling['archivedMainSHA256']==old76['Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs'] and sampling['archivedAdvancedSHA256']==old76['Unity/Assets/HeartOfTheRain/M48/Runtime/AdvancedObstaclePresentationPure.cs'],'Sampler archived76 control source differs')
 need(sampling['familyCases']>1000 and sampling['familySamples']>20000 and sampling['actualTurns']==len(sampling['actualRows'])==18 and sampling['actualSamples']>1000 and sampling['negativeControls']==4 and sampling['syntheticDelayCases']>0 and sampling['coldFallbackSamples']>0,'Sampler fixture/fallback/signature coverage incomplete')
 need(sampling['controlSamples']==sampling['familySamples']+sampling['actualSamples']+sampling['syntheticDelayCases']+sampling['coldFallbackSamples'] and len(sampling['timings'])==6,'Sampler controls omitted cases')
 need(len({r['name'] for r in sampling['actualRows']})==18 and all(r['turnBeforeHash']==r['turnAfterHash'] and r['finalBeforeHash']==r['finalAfterHash'] and r['samples']>0 for r in sampling['actualRows']),'Actual sampler input/model parity differs')
 for row in sampling['timings']:
  need(row['pairs']>0 and len(row['legacyMs'])==len(row['currentMs'])==row['pairs'] and all(PROFILE['finite_nonnegative'](v) for v in row['legacyMs']+row['currentMs']),'Sampler paired timing source is incomplete')
 prep=native['PowerFallPreparation'];path='PairedDensity/paired_1-stone/Report.json'
 archived_trace=historical_read(contexts,76,path)
 need(prep['baselineReportSHA256']==sha(HIST76/path),'Preparation proof uses unsealed resource trace')
 need(all(prep[k] for k in ['rawTurnParity','finalSnapshotMatchesAndroid','poseParity','meshParity','noAdditionalTextureLoads','workingCapsUnchanged','disposedWorkerStops','overlapDeduplicated','conflictingOwnerRejected','evictedFrameRecreated']),'Preparation parity/lifecycle guard failed')
 source_paths={'Unity/Assets/HeartOfTheRain/'+p for p in ['M46/Runtime/BoardModel.cs','M46/Runtime/LivePowerPlan.cs','M46/Runtime/ReviewPlan.cs','M46/Runtime/BoardPlayback.cs','Verification/ObstacleDensityFixture.cs']}
 need(len(prep['sourceBindings'])==5 and {b['path'] for b in prep['sourceBindings']}==source_paths,'Preparation source/fixture bindings are incomplete')
 changed={'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs','Unity/Assets/HeartOfTheRain/M46/Runtime/LivePowerPlan.cs'}
 model=native['ModelWork78'];production={b['path']:b for b in model['currentProductionSourceBindings']}
 for binding in prep['sourceBindings']:
  path=binding['path'];need(binding['currentSHA256']==sha(ROOT/path) and binding['archivedSHA256']==old76[path],'Preparation source bytes differ')
  if path in changed:need(binding['currentSHA256']==production[path]['currentSHA256'] and binding['archivedSHA256']==production[path]['archived77SHA256'],'Preparation is not covered by fresh native78 equivalence')
  else:need(binding['currentSHA256']==binding['archivedSHA256'],'An unapproved preparation fixture/planner source changed')
 need(prep['sourceParityMode']=='ARCHIVED76_UNCHANGED_PLUS_MODEL78_EQUIVALENCE' and prep['model78ProofSHA256']==sha(file('Native/ModelWork78.json')) and Path(prep['model78ProofPath']).resolve()==file('Native/ModelWork78.json'),'Preparation does not link the actual current native78 proof')
 need(prep['fixture77RawParity'] and prep['fixture77FinalParity'] and prep['fixture77TurnHash']==prep['turnHash'] and prep['fixture77FinalHash']==prep['finalHash'],'This preparation fixture lacks exact77 native turn/final parity')
 need(all(prep[k]==prep['turnHash'] for k in ['coldBeforeHash','coldAfterHash','preparedBeforeHash','preparedAfterHash']),'Preparation raw immutability fields disagree')
 archived_row=next(r for r in archived_trace['rows'] if r['name']=='stone_1_0_current76')
 need(prep['androidTurnHash']==archived_row['turnHash'] and prep['finalHash']==archived_row['finalHash'] and prep['rawTurnHashMatchesAndroid']==(prep['turnHash']==prep['androidTurnHash']),'Android raw/final diagnostics are misreported')
 need(prep['preparedDemandCreates']==prep['preparedDemandGeometryMisses']==0 and prep['coldCreates']>0 and prep['overlapFrames']==94 and prep['skippedEvictedAtlases']==1,'Preparation zero-demand/control coverage differs')
 phase=next(i for i,r in enumerate(archived_trace['rows']) if r['name']=='stone_1_0_current76')
 expected_frames=[r['frame'] for r in archived_trace['frames'] if r['phase']==phase and r['step']=='powerFall']
 need(len(expected_frames)==228 and prep['replayedFrames']==len(prep['rows'])==len(expected_frames) and [r['frame'] for r in prep['rows']]==expected_frames,'Preparation full original228-frame replay coverage missing/reordered')
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

def power_fall_device(digest,source_sha256,build_finished,before,native,sealed77):
 helper=Path(__file__).with_name('run_power_fall77_device.py')
 need(helper.is_file(),'PowerFall77 runner contract is not available')
 runner=runpy.run_path(str(helper),run_name='power_fall77_contract_only')
 need('validate_report' in runner,'PowerFall77 runner lacks a strict raw validator')
 report=read('PowerFall/Report.json');installed=read('PowerFall/Installation.json')
 file('PowerFall/Runtime.log')
 need(installed['serial']=='emulator-5556' and installed['apk_sha256']==installed['installed_apk_sha256']==digest,'PowerFall77 installed APK/device differs')
 need(utc(report['utc'])>=utc(installed['utc'])>=build_finished,'PowerFall77 report is stale')
 need(installed['status']=='PASS_POWER_FALL77_DEVICE_AUDIT' and installed['runtime_errors']==0 and not installed.get('error') and installed['data_unchanged'] and installed['before']==installed['after']==before,'PowerFall77 failed or changed real owner data')
 need(utc(report['utc'])<=utc(installed['finishedUtc']),'PowerFall77 report postdates its process audit')
 hashes={}
 for family in ['crate','stone']:
  old=baseline_read('Android/Density/candidate_review-'+family+'/Report.json',sealed77)
  for count in [1,45]:
   values={(r['turnHash'],r['finalHash']) for r in old['rows'] if r['crates']==count};need(len(values)==1,'Historical density model controls disagree');hashes[(family,count)]=values.pop()
 validated=runner['validate_report'](report,hashes)
 need(validated and validated==installed['validated'],'PowerFall77 raw paired/frozen controls failed or installation summary differs')
 for row in report['naturalRows']:command_cost78(row,'PowerFall '+row['name'])
 return {'status':report['status'],'source_sha256':source_sha256,'apk_sha256':digest,'validated':validated,'runner_sha256':sha(helper),'scope':report['scope']}


def execution_device(digest,source_sha256,build_finished,before,sealed77):
 helper=Path(__file__).with_name('run_execution78_device.py');need(helper.is_file(),'Execution78 strict runner contract is not available')
 runner=runpy.run_path(str(helper),run_name='execution78_contract_only');need(callable(runner.get('validate_report')),'Execution78 runner lacks raw validator')
 report=read('Execution/Report.json');installed=read('Execution/Installation.json')
 file('Execution/Runtime.log')
 need(installed['serial']=='emulator-5556' and installed['apk_sha256']==installed['installed_apk_sha256']==digest,'Execution78 APK/device identity differs')
 need(installed['status']=='PASS_EXECUTION78_DEVICE_AUDIT' and installed['runtime_errors']==0 and not installed.get('error') and installed['data_unchanged'] and installed['before']==installed['after']==before,'Execution78 failed or changed real owner data')
 need(build_finished<=utc(installed['utc'])<=utc(report['utc'])<=utc(installed['finishedUtc']),'Execution78 process/report chronology differs')
 old=baseline_read('PowerFall/Report.json',sealed77)
 need(old['status']=='PASS_NATIVE_POWER_FALL77' and len(old['frozenRows'])==4,'Sealed77 Android density outcomes missing')
 need(installed['baseline_android77_report_sha256']==sealed77['evidence_sha256']['PowerFall/Report.json'],'Execution78 transport used an unsealed Android baseline')
 hashes={(r['family'],r['count']):(r['turnHash'],r['finalHash']) for r in old['frozenRows']}
 need(set(hashes)=={(family,count) for family in ['crate','stone'] for count in [1,45]},'Sealed77 density fixture coverage differs')
 validated=runner['validate_report'](report,hashes)
 need(validated and validated==installed['validated'],'Execution78 raw controls failed or audit summary differs')
 for row in report['naturalRows']:command_cost78(row,'Execution78 '+row['name'])
 return {'status':report['status'],'source_sha256':source_sha256,'apk_sha256':digest,'validated':validated,'runner_sha256':sha(helper),'scope':report['scope']}


def power_tool_review(visual,manifest,digest,source_sha256,sealed77,baseline):
 name='RegressionVisual/Power_Tool_Review.json';notes=read(name)
 need(notes['status']=='REVIEWED_FINAL_ANDROID_POWER_PAIRS_AND_TOOLS_WITH_OPEN_GAMEPLAY_GATES' and notes['sourceCheckpoint']==78 and notes['source_sha256']==source_sha256 and notes['apk_sha256']==digest and notes['qa_serial']=='emulator-5556','Independent current power/tool visual identity differs')
 need(notes['baselineOnly'] is False and notes['currentFinalAPKCertified'] is True and notes.get('certificationScope') and notes.get('scope') and notes.get('limitations'),'Independent visual scope/limits missing')
 bind_maps(notes,sealed77,baseline)
 need(visual['artifactSHA256'].get(name)==sha(file(name)),'Parent review omits actual independent power/tool review')
 method=notes['inspection_method'];sheets={p for group in ['PowerPairs','TilesTools'] for p in manifest['sheets'][group]};originals={'Android/Regression/'+p for group in ['PowerPairs','TilesTools'] for p in manifest['groups'][group]}
 need(len(sheets)==8 and set(method['contact_sheets'])==sheets and set(method['constituent_originals'])==originals,'Independent reviewed power/tool captures differ from fresh manifest')
 full=method['full_originals_also_inspected'];need(len(full)>=2 and len(full)==len(set(full)) and set(full)<=originals,'Two actually inspected full power/tool originals missing')
 for path in sheets|originals|set(full):need(notes['artifactSHA256'].get(path)==sha(file(path)),'Independent inspected artifact changed: '+path)
 return notes


def native_plate_review(visual,source_sha256,native,sealed77,baseline):
 name='Native/DenseSubmission_Visual_Review.json';notes=read(name)
 need(notes['status']=='REVIEWED_NATIVE_DENSE_SUBMISSION78_PLATES_ONLY' and notes['sourceCheckpoint']==78 and notes['source_sha256']==source_sha256 and notes['nativeSuite']=='DenseSubmission','Native plate review identity/source differs')
 need(notes.get('scope') and notes.get('limitations') and notes.get('observations') and not notes.get('new_confirmed_rendering_discrepancies') and 'apk_sha256' not in notes,'Native plate review lacks its narrow scope or improperly certifies an APK')
 process=read('Native/DenseSubmission_Process.json')
 need(notes['nativeReport']=='Native/DenseSubmission.json' and notes['nativeReportSHA256']==sha(file(notes['nativeReport'])) and notes['nativeSourceManifest']==process['sourceManifest'] and notes['nativeSourceSHA256']==process['sourceSHA256'],'Native plate review report/source provenance differs')
 paths={'Native/DenseSubmission/Artifacts/'+p for p in native['DenseSubmission']['frames']}
 viewed=notes['inspection_method']['original_images_individually_viewed']
 need(len(viewed)==6 and set(viewed)==paths and notes['imageWidth']==900 and notes['imageHeight']==1600,'Native six-plate inspection scope differs')
 required=paths|{'Source_SHA256.json','Native/DenseSubmission.json','Native/DenseSubmission_Process.json',process['sourceManifest']}
 bind_maps(notes,sealed77,baseline)
 need(all(notes['artifactSHA256'].get(p)==sha(file(p)) for p in required),'Native inspected plate/report/source hash missing')
 need(visual['artifactSHA256'].get(name)==sha(file(name)) and all(visual['artifactSHA256'].get(p)==sha(file(p)) for p in paths),'Parent visual review omits native note/inspected plates')
 return notes

def historical_attempts(sealed77):
 # Failed77 proofs remain historical and sealed in77, never passing78 suites.
 rows=sealed77.get('historical_attempts',[])
 need(len(rows)==2 and {r['attempt'] for r in rows}=={'FirstCompileFailure','FirstPreparationBaselineFailure'},'Historical77 failure record missing')
 for row in rows:
  prefix='Attempts/'+row['attempt']+'/'
  historical=baseline_read(prefix+'Native/'+row['suite']+'_Process.json',sealed77)
  need(historical['exitCode']==row['exit_code']!=0,'Historical failed proof relabeled as success')
 return rows


def current_failed_attempt(current):
 prefix='Attempts/FirstCompileFailure/';frozen=read(prefix+'Source_SHA256.json');delta=read(prefix+'Source_Delta.json');failure=read(prefix+'Failure.json')
 run=read(prefix+'Native/ModelWork78_Process.json');manifest=read(prefix+run['sourceManifest']);log=file(prefix+'Native/ModelWork78.log')
 need(failure['status']=='HISTORICAL_COMPILE_FAILURE_NOT_A_PASS' and failure['source_sha256']==sha(file(prefix+'Source_SHA256.json')),'Current78 failed-attempt identity differs')
 need(run['mode']=='ModelWork78' and run['exitCode']!=0 and not run['timedOut'] and run['version'].startswith('2022.3.62f3'),'Original78 compile failure was relabeled')
 need(frozen['files']==manifest['files'] and run['sourceSHA256']==sha(file(prefix+run['sourceManifest'])) and utc(frozen['utc'])<=utc(run['startedUtc'])<=utc(run['finishedUtc'])<=utc(failure['utc']),'Failed78 source/process chronology differs')
 need('CS0819' in log.read_text('utf-8-sig') and 'CommandPreparation78Verification.cs' in log.read_text('utf-8-sig'),'Original78 compile failure log is missing')
 paths={p for p in delta['changed_existing']+delta['added'] if p.endswith('.cs')}
 for path in paths:need(sha(file(prefix+'Sources/'+path))==frozen['files'][path],'Failed78 changed/new source archive differs: '+path)
 need(set(frozen['files'])==set(current) and {p for p in current if current[p]!=frozen['files'][p]}=={'Unity/Assets/HeartOfTheRain/Verification/Editor/CommandPreparation78Verification.cs'},'Initial compile correction changed unexpected runtime/source files')
 return {'attempt':'FirstCompileFailure','checkpoint':78,'suite':'ModelWork78','exit_code':run['exitCode'],'source_sha256':failure['source_sha256'],'cause':failure['cause'],'scope':'Preserved failed compile only; no passing suite or native check is counted from it.'}

def timing_visual_review(visual,digest,source_sha256,installation,before,continuation,sealed77,baseline):
 notes=read('Timing_Visual_Notes.json')
 need(notes['status']=='REVIEWED_EXECUTION78_WITH_REMAINING_GATES' and notes['apk_sha256']==digest and notes['source_sha256']==source_sha256 and notes['qa_serial']=='emulator-5556' and notes.get('scope') and notes.get('limitations') and notes.get('remainingGates'),'Fresh78 timing review identity/scope/gates missing')
 bind_maps(notes,sealed77,baseline)
 need(visual['artifactSHA256'].get('Timing_Visual_Notes.json')==sha(file('Timing_Visual_Notes.json')),'Parent review omits final timing notes')
 for name,h in notes['artifactSHA256'].items():need(visual['artifactSHA256'].get(name)==h,'Parent review omits inspected timing artifact: '+name)
 cases=[notes['localMatch']]+notes['continuationCases']
 need(len(cases)==4 and [r['level'] for r in cases]==[4,14,31,33],'Timing review omits/repeats a current movie')
 corpus={r['name']:r for r in continuation['rows']}
 archived_native={r['name']:r for r in baseline_read('Native/LocalContinuation.json',sealed77)['rows']}
 for case in cases:
  level=case['level'];folder='Android/Cascade/visual/' if level==4 else 'ContinuationVisual/L'+str(level)+'/visual/'
  need(case['case']=='L'+str(level)+'_0_30' and case['sourceFolder']==folder,'Timing review uses wrong fixture/folder')
  if level!=4:need(case['routeContinuityReviewed'] is True and case['landingIntoIdleReviewed'] is True and case.get('visualFinding') and case.get('measurementLimitations'),'Continuity/landing review scope missing')
  installed=installation(folder+'Installation.json');report=read(folder+'Report.json')
  need(installed['data_unchanged'] and installed['before']==installed['after']==before and installed['visual_level']==report['visualLevel']==level and installed['checkpoint74_continuation'] is False and report['checkpoint74Continuation'] is False and installed['profile_model_work'] is False and report['modelWorkEnabled'] is False and report['repeats']==1 and utc(report['utc'])>=utc(installed['utc']),'Recorded current timing provenance differs')
  need(PROFILE['RUNNER']['validate_report'](report,'visual',1,require_profiling=True),'Recorded current timing spans invalid')
  row=report['rows'][0];command_cost78(row,'Recorded L'+str(level));native_name='L'+str(level)+'_match';native=corpus[native_name];old_native=archived_native[native_name]
  archived_movie=baseline_read(folder+'Report.json',sealed77);old_row=archived_movie['rows'][0]
  need(row['name']==row['baseCase']==old_row['name']==case['case'] and (row['turnHash'],row['finalHash'])==(old_row['turnHash'],old_row['finalHash']),'Fresh Android timing outcome differs from sealed77 Android fixture')
  need(all(native[k]==old_native[k] for k in ['refinedTurnHash','refinedFinalHash','refinedSeconds']),'Fresh native timing outcome/schedule differs from sealed77 native fixture')
  need(abs(row['scheduledSeconds']-old_row['scheduledSeconds'])<.001 and abs(row['scheduledSeconds']-native['refinedSeconds'])<.001,'Timing movie schedule differs from the unchanged Android/native schedules')
  movie=folder+'HR_NaturalCascade.mp4';index_path=case['ptsIndex'];index=read(index_path)
  need(index['status']=='EXTRACTED_ORIGINAL_PTS_FRAMES_FOR_MANUAL_REVIEW' and index['checkpoint']==78 and index['apk_sha256']==digest and index['source_sha256']==source_sha256 and index['case']==case['case'] and index['visualLevel']==level and index['checkpoint74Continuation'] is False,'Endpoint index is not fresh78')
  need(index['video']==file(movie).relative_to(ROOT).as_posix() and index['sha256']==sha(file(movie))==notes['artifactSHA256'].get(movie) and index['reportSHA256']==sha(file(folder+'Report.json')) and index['installationSHA256']==sha(file(folder+'Installation.json')),'PTS index source movie/report/install binding differs')
  need(notes['artifactSHA256'].get(index_path)==sha(file(index_path)) and len(index['frames'])>1 and all(a['pts']<b['pts'] for a,b in zip(index['frames'],index['frames'][1:])),'PTS source/index chronology invalid')
  def endpoint_bracket(frame_key,pts_key):
   selected=case[frame_key];need(len(selected)==2 and all(isinstance(i,int) and not isinstance(i,bool) and 1<=i<=len(index['frames']) for i in selected) and selected[1]==selected[0]+1,'Manual endpoint bracket does not use adjacent original frames')
   values=[]
   for i in selected:
    original=index['frames'][i-1];path=(ROOT/original['file']).resolve();need(path.is_relative_to(OUT.resolve()),'Endpoint image leaves checkpoint78')
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
 need(frozen['files']==current and len(current)==5141,'Current Unity inputs changed after freeze/count differs')
 old=read('Baseline77_Source_SHA256.json')['files'];delta=read('Source_Delta.json')
 allowed={'Unity/Assets/HeartOfTheRain/'+p for p in ['M46/Runtime/BoardModel.cs','M46/Runtime/LivePowerPlan.cs','M47/Runtime/EffectMeshBatcher.cs','M47/Runtime/GameplayScreen.cs','M48/Runtime/AdvancedObstacleRulesPure.cs','Verification/Editor/PowerFallPreparationVerification.cs']}
 added={'Unity/Assets/HeartOfTheRain/'+p+s for p in ['M47/Runtime/GameplayCommandPreparation.cs','Verification/CommandPreparation77Control.cs','Verification/Editor/CommandPreparation78Verification.cs','Verification/Editor/DenseSubmissionVerification.cs','Verification/Editor/ModelWork78Verification.cs','Verification/Execution78Probe.cs','Verification/Model77Control78.cs','Verification/ModelWork78Proof.cs'] for s in ['', '.meta']}
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
 baseline_proof=read('Baseline77.json')
 need(baseline_proof['status']=='PRESERVED_VERIFIED77_BASELINE' and baseline_proof['source_inputs']==len(old)==5125,'Baseline identity/count differs')
 need(baseline_proof['source_sha256']=='f16edd1b7872160e75a6c6da8b31a00f387cfb79d5eb3bb3e9a988a635c3fd2c' and baseline_proof['apk_sha256']=='d4bb4e66e454db223871c91d66de4ee8e87fec05268aa9a27a3cf86da7930072','Baseline is not verified77')
 need(baseline_proof['source_sha256']==sha(file('Baseline77_Source_SHA256.json'))==sha(BASE/'Source_SHA256.json'),'Baseline source binding differs')
 need(sha(BASE/'Summary.json')==baseline_proof['summary_sha256'],'Sealed77 summary changed')
 need(sha(file('Baseline77_Summary.json'))==baseline_proof['summary_sha256'],'Copied baseline77 summary changed')
 sealed77=json.loads((BASE/'Summary.json').read_text('utf-8-sig'))
 need(sealed77['source_checkpoint']==77 and sealed77['source_sha256']==baseline_proof['source_sha256'] and sealed77['apk_sha256']==baseline_proof['apk_sha256'],'Sealed77 identity differs')

 contexts=historical_chain(sealed77,baseline_proof)
 legacy75=historical_read(contexts,75,'Source_SHA256.json')['files']
 baseline_apk=(ROOT/baseline_proof['apk_archive']).resolve()
 need(baseline_apk.is_relative_to(ROOT.resolve()) and sha(baseline_apk)==baseline_proof['apk_sha256'],'Archived77 APK changed')
 archive=(ROOT/baseline_proof['source_archive']).resolve()
 for name in allowed:
  need(archive.is_relative_to(ROOT.resolve()) and sha(archive/name)==old[name],'Archived changed77 source differs: '+name)
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
 need(len(native)==32,'Missing one of32 native suites')
 native_runner=read('Native_Runner.json')
 need(native_runner['status']=='PASS_SELECTED_NATIVE_GAMEPLAY78_SUITES' and len(native_runner['runs'])==32 and {r['mode'] for r in native_runner['runs']}==set(native),'Native runner did not finish all32 suites')
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
  baseline=baseline_read('Android/Cascade/'+variant+'/Report.json',sealed77)
  hashes={r['baseCase']:(r['turnHash'],r['finalHash']) for r in baseline['rows']}
  timing[variant]=PROFILE['validate'](report,variant,hashes)
  for row in report['rows']:command_cost78(row,'Ordinary cascade '+row['name'])
 density={}
 for family in ['crate','stone','gate','tiles']:
  path='Android/Density/candidate_review-'+family+'/'
  report=read(path+'Report.json');installed=installation(path+'Installation.json');need(utc(report['utc'])>=utc(installed['utc']) and report['detailedDrawCosts'] is True,'Default density is stale or coarse')
  baseline=baseline_read(path+'Report.json',sealed77);hashes={r['name']:(r['turnHash'],r['finalHash']) for r in baseline['rows']}
  density[family]=PROFILE['validate_density'](report,family,hashes)
  for row in report['rows']:command_cost78(row,'Ordinary density '+row['name'])
 regression=read('Android/Regression/Regression.json');clean(regression,'Full Android regression');ri=installation('Android/Regression/Installation.json')
 need(regression['status']=='PASS_NATIVE_REGRESSION' and regression['boards']==50 and regression['checks']>=1716 and regression['clips']>=354 and regression['actions']>=408 and regression['labels']>=14105 and len(regression['damageFamilies'])==8 and utc(regression['utc'])>=utc(ri['utc']),'Campaign regression incomplete')
 need({'Native refill button spends 900 and fills all five lives','Repeated native refill callback charges exactly once','Confirmed decline charges exactly one life, no coins, and opens retry pre-level'}<=set(regression['passed']),'Life/Continue settlement proof missing')
 idle=read('Android/Regression/M70_Device.json');clean(idle,'Live idle')
 idle_controls=CONTRACT['idle_device_controls'](idle,regression,ri)
 need(idle_controls,'Bounded live idle proof missing')
 # All32 native scopes and both fresh paired device experiments are mandatory.
 history=historical_attempts(sealed77)+[current_failed_attempt(current)]
 targeted_native78(native,old,sealed77)
 power_fall_native(native,old,sealed77,contexts)
 device=power_fall_device(digest,sha(file('Source_SHA256.json')),utc(process['finishedUtc']),before,native,sealed77)
 execution=execution_device(digest,sha(file('Source_SHA256.json')),utc(process['finishedUtc']),before,sealed77)
 performance=read('Execution_Analysis.json')
 need(performance['status']=='ANALYZED_EXECUTION78_WITH_REMAINING_GATES' and performance['apk_sha256']==digest and performance['source_sha256']==sha(file('Source_SHA256.json')) and performance.get('remainingGates'),'Missing/bad power-fall analysis or remaining gates')
 analyzer=Path(__file__).with_name('analyze_execution78_performance.py')
 expected=runpy.run_path(str(analyzer),run_name='execution78_recompute')['build'](OUT)
 need({k:v for k,v in performance.items() if k!='utc'}=={k:v for k,v in expected.items() if k!='utc'},'Power-fall analysis differs from recomputed raw proof')
 bind_maps(performance,sealed77,baseline_proof)
 visual=read('Visual_Review.json')
 need(visual['status']=='REVIEWED_SAMPLED_GAMEPLAY78' and visual['apk_sha256']==digest and visual['source_sha256']==sha(file('Source_SHA256.json')) and visual['qa_serial']=='emulator-5556' and visual.get('scope') and visual.get('limitations'),'Actual final78 visual review missing/misbound')
 bind_maps(visual,sealed77,baseline_proof)
 need(visual['artifactSHA256'].get('Execution_Analysis.json')==sha(file('Execution_Analysis.json')),'Visual review omits final performance analysis')
 native_plate_review(visual,sha(file('Source_SHA256.json')),native,sealed77,baseline_proof)
 timing_review=timing_visual_review(visual,digest,sha(file('Source_SHA256.json')),installation,before,native['LocalContinuation'],sealed77,baseline_proof)
 manifest=read('RegressionVisual/Manifest.json')
 need(manifest['status']=='PRESENTED_FOR_VISUAL_REVIEW' and set(manifest['groups'])=={'BoardMasks','TilesTools','Powers','PowerPairs','ObstacleRoutes','ConnectedFlow'},'Regression gallery incomplete')
 inspected={p for group in manifest['sheets'].values() for p in group}
 originals={'Android/Regression/'+p for group in manifest['groups'].values() for p in group}
 need(len(inspected)==14 and all(visual['artifactSHA256'].get(p)==sha(file(p)) for p in inspected|originals),'Reviewed final regression sheets/originals incomplete')
 power_tool_review(visual,manifest,digest,sha(file('Source_SHA256.json')),sealed77,baseline_proof)
 result={'status':'PASS_TARGETED_EXECUTION78_WITH_REMAINING_PERFORMANCE_GATES','utc':datetime.now(timezone.utc).isoformat(),'source_checkpoint':78,'source_inputs':len(current),'source_sha256':sha(file('Source_SHA256.json')),'baseline_checkpoint':77,'baseline_summary_sha256':baseline_proof['summary_sha256'],'baseline_apk_sha256':baseline_proof['apk_sha256'],'baseline_source_sha256':baseline_proof['source_sha256'],'apk_sha256':digest,'apk_bytes':artifact['bytes'],'native_suites':len(native),'native_checks':sum(CONTRACT['BASE_CONTRACT']['checks'](r) for r in native.values()),'non_development_compile_build_passed':True,'qa_data_unchanged':True,'main_apk_updated':False,'android':{'stages':9,'boards':50,'checks':regression['checks'],'actions':regression['actions'],'clips':regression['clips'],'density_turns':40,'fluidity_phases':8,'touch_cases':8},'power_fall':device,'execution':execution,'native_preparation_android_raw_turn_hash_matches':native['PowerFallPreparation']['rawTurnHashMatchesAndroid'],'historical_attempts':history,'performance_analysis':performance,'visual_scope':visual['scope'],'limits':visual['limitations'],'collector_sha256':sha(Path(__file__)),'evidence_sha256':dict(sorted(evidence.items()))}
 if publish:
  for p in [OUT/'Summary.json',OUT.parent/'Verification_Summary.json']:p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  checkpoint={'utc':result['utc'],'status':result['status'],'source_checkpoint':78,'installed_checkpoint':64,'qa_installed_checkpoint':78,'source_sha256':result['source_sha256'],'android_apk_sha256':digest,'android_apk_matches_current_source':True,'main_installed_apk_matches_current_source':False,'review':'Codex_Handoff/Documentation/78_COMMAND_AND_SUBMISSION_REVIEW.md','summary':'Verification/Evidence/Gameplay78/Summary.json','scope':'Targeted command/resource/submission work verified on QA only; remaining performance, fresh-reference and physical-device gates stay explicit.'}
  (OUT.parent/'Native_Source_Checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ['performance_analysis','evidence_sha256']},indent=2))
 return result

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--publish',action='store_true');args=parser.parse_args();main(publish=args.publish)
