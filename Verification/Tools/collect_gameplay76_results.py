"""Fail closed on current-source native, build, QA, paired-performance and visual proof."""
import hashlib,json,math,re,runpy,statistics
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Gameplay76';BASE=ROOT/'Verification/Evidence/Gameplay75'
CONTRACT=runpy.run_path(str(Path(__file__).with_name('collect_gameplay75_results.py')),run_name='contracts_only')
PROFILE=CONTRACT['PROFILE_CONTRACT'];NATIVE=dict(CONTRACT['NATIVE'])|{'SmoothnessCommand':'PASS_NATIVE_SMOOTHNESS_COMMAND76'}
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
def main(publish=True):
 evidence.clear()
 frozen=read('Source_SHA256.json');current={p.relative_to(ROOT).as_posix():sha(p) for d in ['Assets','Packages','ProjectSettings'] for p in (ROOT/'Unity'/d).rglob('*') if p.is_file()}
 need(frozen['files']==current,'Current Unity inputs changed after freeze')
 old=read('Baseline75_Source_SHA256.json')['files'];delta=read('Source_Delta.json')
 allowed={'Unity/Assets/HeartOfTheRain/'+p for p in ['M46/Runtime/BoardPlayback.cs','M46/Runtime/LocalCascadeContinuation.cs','M47/Runtime/EffectMeshBatcher.cs','M47/Runtime/GameplayScreen.cs','Verification/Editor/EffectBatchVerification.cs','Verification/Editor/LocalContinuationVerification.cs','Verification/ObstacleDensityProbe.cs']}
 added={'Unity/Assets/HeartOfTheRain/'+p+s for p in ['Verification/Smoothness75Control.cs','Verification/SmoothnessCommandProbe.cs','Verification/Editor/SmoothnessCommandVerification.cs'] for s in ['', '.meta']}
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
 baseline_proof=read('Baseline75.json')
 need(baseline_proof['source_sha256']==sha(file('Baseline75_Source_SHA256.json'))==sha(BASE/'Source_SHA256.json'),'Baseline source binding differs')
 need(sha(BASE/'Summary.json')==baseline_proof['summary_sha256'],'Sealed75 summary changed')
 sealed75=json.loads((BASE/'Summary.json').read_text('utf-8-sig'))
 need(sealed75['source_checkpoint']==75 and sealed75['source_sha256']==baseline_proof['source_sha256'] and sealed75['apk_sha256']==baseline_proof['apk_sha256'],'Sealed75 identity differs')
 need(read('Build_Source_SHA256.json')['files']==current,'Build did not start with frozen inputs')
 build=read('Android_Build.json');process=read('AndroidBuild_Process.json');artifact=read('APK_Artifact.json');pack=read('APK_Packaging.json')
 clean(build,'Development build');need(build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['unity']=='2022.3.62f3' and build['errors']==0 and process['exitCode']==0 and not process['timedOut'],'Development build failed')
 apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk';digest=sha(apk)
 need(digest==artifact['sha256']==pack['afterSHA256'] and apk.stat().st_size==artifact['bytes']==pack['afterBytes'],'APK identity differs')
 need(all(artifact[k] for k in ['zipalign4KiBPass','developmentSignatureVerifies','elf16KiBLoadSegmentsPass']) and pack['sameSignerCertificate'] and not pack['changedNonSignatureEntries'],'APK packaging failed')
 need('Errors: 0' in file('Build_Import_Audit.txt').read_text('utf-8-sig'),'Import guard failed')
 release=read('Android_Release_Build.json');rp=read('AndroidReleaseBuild_Process.json');ra=read('Release_APK_Artifact.json')
 clean(release,'Nondevelopment build');need(release['status']=='PASS_ANDROID_RELEASE_COMPILE_BUILD' and release['unity']=='2022.3.62f3' and release['errors']==0 and rp['exitCode']==0 and not rp['timedOut'] and sha(ROOT/ra['path'])==ra['sha256'],'Nondevelopment build failed')
 need(read('Release_Source_SHA256.json')['files']==current,'Release source differs')
 need('Errors: 0' in file('Release_Build_Import_Audit.txt').read_text('utf-8-sig'),'Release import guard failed')
 native={}
 for name,status in NATIVE.items():
  report,run=read('Native/'+name+'.json'),read('Native/'+name+'_Process.json');clean(report,name)
  need(report['status']==status and run['exitCode']==0 and not run['timedOut'] and run['version'].startswith('2022.3.62f3'),name+' failed/stale/unpinned')
  need(utc(frozen['utc'])<=utc(run['startedUtc'])<=utc(report['utc'])<=utc(run['finishedUtc']),name+' source/report chronology differs')
  need(read(run['sourceManifest'])['files']==current and sha(file(run['sourceManifest']))==run['sourceSHA256'],name+' ran different inputs')
  need(CONTRACT['BASE_CONTRACT']['checks'](report)>0,name+' ran no checks');native[name]=report
 need(len(native)==26,'Missing native suite')
 need(utc(process['startedUtc'])>=max(utc(read('Native/'+name+'_Process.json')['finishedUtc']) for name in native) and utc(process['startedUtc'])<=utc(build['utc'])<=utc(process['finishedUtc']),'Native/build chronology differs')
 need(utc(frozen['utc'])<=utc(rp['startedUtc'])<=utc(release['utc'])<=utc(rp['finishedUtc']),'Release chronology differs')
 need(max(utc(read('Native/'+name+'_Process.json')['finishedUtc']) for name in native)<=utc(rp['startedUtc'])<=utc(rp['finishedUtc'])<=utc(process['startedUtc']),'Native/release/development order differs')
 command=native['SmoothnessCommand']
 need(command['modelCases']==350 and command['queueComparisons']==1400 and command['sourceFiles']==3 and all(command[k] for k in ['exactQueueParity','rawInputUnchanged','rawTurnParity','finalSnapshotParity','compiledSourceMatchesArchive']),'Command construction parity coverage missing')
 need(len(command['sourceBindings'])==3 and all(b['compiledExactAdaptation'] and b['sha256']==old[b['path']] for b in command['sourceBindings']),'Archived75 command control source binding differs')
 need(len(command['timings'])==8 and all(len(r['pairs'])==12 for r in command['timings']),'Native paired construction controls missing')
 effects=native['EffectBatchChecks']
 need(effects['transformParityFrames']==len(effects['transformParityRows'])==65 and len(effects['transformPixelRows'])==2 and all(r['differingPixels']==r['maxChannelDelta']==0 for r in effects['transformPixelRows']) and len(effects['transformRows'])==15 and all(r['iterations']==64 for r in effects['transformRows']),'Archived75 mesh/pixel/CPU proof incomplete')
 need(effects['frozen75SourceSHA256']==old['Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs'],'Archived75 effect source differs')
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
  baseline=json.loads((BASE/('Android/Cascade/'+variant+'/Report.json')).read_text('utf-8-sig'))
  hashes={r['baseCase']:(r['turnHash'],r['finalHash']) for r in baseline['rows']}
  timing[variant]=PROFILE['validate'](report,variant,hashes)
 density={}
 for family in ['crate','stone','gate','tiles']:
  path='Android/Density/candidate_review-'+family+'/'
  report=read(path+'Report.json');installed=installation(path+'Installation.json');need(utc(report['utc'])>=utc(installed['utc']) and report['detailedDrawCosts'] is True,'Default density is stale or coarse')
  baseline=json.loads((BASE/(path+'Report.json')).read_text('utf-8-sig'));hashes={r['name']:(r['turnHash'],r['finalHash']) for r in baseline['rows']}
  density[family]=PROFILE['validate_density'](report,family,hashes)
 regression=read('Android/Regression/Regression.json');clean(regression,'Full Android regression');ri=installation('Android/Regression/Installation.json')
 need(regression['status']=='PASS_NATIVE_REGRESSION' and regression['boards']==50 and regression['checks']>=1716 and regression['clips']>=354 and regression['actions']>=408 and regression['labels']>=14105 and len(regression['damageFamilies'])==8 and utc(regression['utc'])>=utc(ri['utc']),'Campaign regression incomplete')
 need({'Native refill button spends 900 and fills all five lives','Repeated native refill callback charges exactly once','Confirmed decline charges exactly one life, no coins, and opens retry pre-level'}<=set(regression['passed']),'Life/Continue settlement proof missing')
 idle=read('Android/Regression/M70_Device.json');clean(idle,'Live idle')
 idle_controls=CONTRACT['idle_device_controls'](idle,regression,ri)
 pair_runner=runpy.run_path(str(Path(__file__).with_name('run_smoothness_command_device.py')),run_name='command_contract_only')
 pair_runner['validate_report'](read('CommandPairs/Report.json'));installation('CommandPairs/Installation.json')
 paired=read('Paired_Performance.json');need(paired['status']=='ANALYZED_SAME_APK_SMOOTHNESS76' and paired['apk_sha256']==digest,'Paired analysis missing/different APK')
 analyzer=runpy.run_path(str(Path(__file__).with_name('analyze_gameplay76_performance.py')),run_name='recompute_contract_only')
 expected_pair,expected_gates=analyzer['build'](OUT)
 need({k:v for k,v in paired.items() if k!='utc'}=={k:v for k,v in expected_pair.items() if k!='utc'},'Saved paired analysis differs from independently recomputed canonical raw proof')
 for name,d in paired['artifactSHA256'].items():need(sha(file(name))==d,'Paired analysis artifact changed: '+name)
 sealed_external={}
 for name,d in paired['externalEvidenceSHA256'].items():
  p=(ROOT/name).resolve();need(p.is_relative_to(ROOT.resolve()) and p.is_file() and sha(p)==d,'Paired external artifact changed: '+name)
  if p.is_relative_to(BASE.resolve()):
   relative=p.relative_to(BASE.resolve()).as_posix()
   if relative=='Summary.json':expected=baseline_proof['summary_sha256']
   elif relative=='Source_SHA256.json':expected=baseline_proof['source_sha256']
   else:expected=sealed75['evidence_sha256'].get(relative)
   need(expected==d,'Archived75 raw comparison differs from sealed Summary: '+relative)
   sealed_external[name]=d
 visual=read('Visual_Review.json');need(visual['status']=='REVIEWED_SAMPLED_GAMEPLAY76' and visual['apk_sha256']==digest and visual['source_sha256']==sha(file('Source_SHA256.json')) and visual.get('limitations'),'Visual review missing/misbound')
 for name,d in visual['artifactSHA256'].items():need(sha(file(name))==d,'Visual artifact changed: '+name)
 def bound_review(path,status):
  report=read(path)
  need(report['status']==status and report['apk_sha256']==digest and report['source_sha256']==sha(file('Source_SHA256.json')) and report['qa_serial']=='emulator-5556',path+' is not a final76 review')
  need(visual['artifactSHA256'].get(path)==sha(file(path)),path+' absent from parent review')
  for name,d in report['artifactSHA256'].items():
   need(sha(file(name))==d and visual['artifactSHA256'].get(name)==d,path+' artifact changed or absent from parent review: '+name)
  for name,d in report.get('externalEvidenceSHA256',{}).items():
   p=(ROOT/name).resolve();need(p.is_relative_to(ROOT.resolve()) and p.is_file() and sha(p)==d,path+' external context changed: '+name)
  return report
 timing_review=bound_review('Timing_Visual_Notes.json','REVIEWED_SMOOTHNESS76_WITH_REMAINING_GATES')
 need(timing_review['source_inputs']==len(current) and len(timing_review['recordedCurrentCases'])==4 and {r['level'] for r in timing_review['continuationCases']}=={14,31,33} and timing_review['remainingGates'],'Timing review coverage/gates missing')
 swap=timing_review['acceptedSwap'];need(swap['nativeScheduledMs']==120 and swap['visibleDurationBoundMs'][0]<=120<=swap['visibleDurationBoundMs'][1],'Swap schedule/review discrepancy')
 need(timing_review['nativeScheduleParity']['exactQueueParity'] and timing_review['nativeScheduleParity']['queueComparisons']==1400,'Timing review schedule parity missing')
 powers=bound_review('RegressionVisual/Power_Tool_Review.json','REVIEWED_FINAL_ANDROID_POWER_PAIRS_AND_TOOLS_WITH_OPEN_GAMEPLAY_GATES')
 need(powers['capture_counts']=={'power_pairs':56,'tiles_tools':33,'sheets':8,'full_originals':2} and powers['limitations'] and powers['remaining_gameplay_defects'] and not powers['new_confirmed_rendering_discrepancies'],'Power/tool visual scope changed')
 manifest=read('RegressionVisual/Manifest.json')
 power_method=powers['inspection_method'];need(power_method['contact_sheets']==manifest['sheets']['PowerPairs']+manifest['sheets']['TilesTools'] and power_method['constituent_originals']==['Android/Regression/'+n for group in ['PowerPairs','TilesTools'] for n in manifest['groups'][group]] and len(power_method['full_originals_also_inspected'])==2,'Power/tool sheet/original coverage differs')
 parent=visual['parentInspection'];need(len(parent['nativeFullPlates'])==6 and len(parent['timingSheets'])==6 and len(parent['timingFullOriginals'])==2 and len(parent['regressionSheets'])==6 and len(parent['regressionConstituents'])==68 and len(parent['regressionFullOriginals'])==5,'Parent inspection scope differs')
 for name in parent['nativeFullPlates']+parent['timingSheets']+parent['timingFullOriginals']+parent['regressionSheets']+parent['regressionConstituents']+parent['regressionFullOriginals']:
  need(visual['artifactSHA256'].get(name)==sha(file(name)),'Inspected parent artifact missing: '+name)
 gates=read('Performance_Gates.json');need(gates['apk_sha256']==digest and gates.get('remainingGates'),'Remaining gates missing')
 need({k:v for k,v in gates.items() if k!='utc'}=={k:v for k,v in expected_gates.items() if k!='utc'},'Performance gates differ from recomputed measurements')
 result={'status':'PASS_TARGETED_SMOOTHNESS76_WITH_REMAINING_PERFORMANCE_GATES','utc':datetime.now(timezone.utc).isoformat(),'source_checkpoint':76,'source_inputs':len(current),'source_sha256':sha(file('Source_SHA256.json')),'baseline_checkpoint':75,'baseline_summary_sha256':baseline_proof['summary_sha256'],'baseline_external_sha256':sealed_external,'apk_sha256':digest,'apk_bytes':artifact['bytes'],'native_suites':len(native),'native_checks':sum(CONTRACT['BASE_CONTRACT']['checks'](r) for r in native.values()),'non_development_compile_build_passed':True,'qa_data_unchanged':True,'main_apk_updated':False,'android':{'stages':9,'boards':50,'checks':regression['checks'],'actions':regression['actions'],'clips':regression['clips'],'density_turns':40,'fluidity_phases':8,'touch_cases':8},'paired_performance':paired,'performance_gates':gates,'visual_scope':visual['scope'],'limits':visual['limitations'],'collector_sha256':sha(Path(__file__)),'evidence_sha256':dict(sorted(evidence.items()))}
 if publish:
  for p in [OUT/'Summary.json',OUT.parent/'Verification_Summary.json']:p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  checkpoint={'utc':result['utc'],'status':result['status'],'source_checkpoint':76,'installed_checkpoint':64,'qa_installed_checkpoint':76,'source_sha256':result['source_sha256'],'android_apk_sha256':digest,'android_apk_matches_current_source':True,'main_installed_apk_matches_current_source':False,'review':'Codex_Handoff/Documentation/76_COMMAND_CONSTRUCTION_SMOOTHNESS_REVIEW.md','summary':'Verification/Evidence/Gameplay76/Summary.json','scope':'Targeted smoothness verified on QA only. Main deployment64 preserved; remaining performance/physical-device gates stay explicit.'}
  (OUT.parent/'Native_Source_Checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ['paired_performance','performance_gates','evidence_sha256']},indent=2))
if __name__=='__main__':main()
