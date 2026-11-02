"""Describe every matched power-fall sample and retain remaining limits; no approval."""
import hashlib,json,math,runpy,statistics
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/'Verification/Evidence/Gameplay77'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OUTER=['outerSetupMs','outerSampleMs','outerBeginMs','outerDrawMs','outerDisableMs','outerUploadMs','outerEndCollectionsMs','outerBankEndMs','outerSelectionMs','outerWrapperResidualMs']

def stats(values):
    values=list(values)
    if not values:return {'samples':0,'median':None,'p95':None,'max':None}
    assert all(isinstance(x,(int,float)) and math.isfinite(x) for x in values)
    ordered=sorted(values)
    return {'samples':len(values),'median':statistics.median(values),'p95':ordered[max(0,math.ceil(len(values)*.95)-1)],'max':max(values)}

def frame_summary(frames):
    result={'frames':len(frames),'intervalMs':stats(f['intervalMs'] for f in frames),
            'renderMs':stats(f['cost']['renderMs'] for f in frames),'updateMs':stats(f['cost']['updateMs'] for f in frames),
            'demandSpriteCreates':sum(f['cost']['spriteCreated'] for f in frames),
            'demandGeometryMisses':sum(f['cost']['geometryMisses'] for f in frames),
            'rendererCreates':sum(f['cost']['poolCreated'] for f in frames),'meshSlotCreates':sum(f['cost']['meshSlotsCreated'] for f in frames),
            'outerSpans':{k:stats(f['cost'][k] for f in frames) for k in OUTER},'completedGCWithinUpdate':{},'completedGCWithinRender':{}}
    for generation in range(3):
        supported=[f['cost'] for f in frames if f['cost']['gcMaxGeneration']>=generation]
        result['completedGCWithinUpdate'][str(generation)]=sum(c[f'gc{generation}AfterUpdate']-c[f'gc{generation}BeforeUpdate'] for c in supported) if supported else None
        result['completedGCWithinRender'][str(generation)]=sum(c[f'gc{generation}AfterRender']-c[f'gc{generation}BeforeRender'] for c in supported) if supported else None
    return result

def build(out=DEFAULT):
    out=Path(out).resolve();artifacts={};external={}
    def read(name):
        p=out/name;artifacts[name]=sha(p);return json.loads(p.read_text('utf-8-sig'))
    def historical(name):
        p=ROOT/name;external[name]=sha(p);return json.loads(p.read_text('utf-8-sig'))
    source=read('Source_SHA256.json');apk=read('APK_Artifact.json');report=read('PowerFall/Report.json');audit=read('PowerFall/Installation.json')
    runner=Path(__file__).with_name('run_power_fall77_device.py');validator=runpy.run_path(str(runner),run_name='contract_only')
    validated=validator['validate_report'](report)
    assert audit['status']=='PASS_POWER_FALL77_DEVICE_AUDIT' and audit['apk_sha256']==apk['sha256'] and audit['data_unchanged']
    native=read('Native/PowerFallSampling.json');preparation=read('Native/PowerFallPreparation.json')
    assert native['status']=='PASS_NATIVE_POWER_FALL_SAMPLING77' and preparation['status']=='PASS_NATIVE_POWER_FALL_PREPARATION77'
    old=historical('Verification/Evidence/Gameplay76/Paired_Performance.json')
    historical('Verification/Evidence/Gameplay76/Summary.json');historical('Verification/Evidence/Gameplay76/Source_SHA256.json')
    historical('Verification/Evidence/Gameplay76/PairedDensity/paired_1-stone/Report.json')
    for family in ('crate','stone'):
        historical('Verification/Evidence/Gameplay76/Android/Density/candidate_review-'+family+'/Report.json')
    natural=[]
    for index,row in enumerate(report['naturalRows']):
        frames=report['frames'][row['frameStart']:row['frameStart']+row['frameCount']]
        before=[f for f in frames if f['cost']['renderFinishedWall']<=row['commandStartedWall']]
        after=[f for f in frames if f['cost']['renderStartedWall']>=row['commandFinishedWall']]
        fall=[f for f in after if f['cost']['kind']=='powerFall']
        late=[f for f in fall if 2.44<=f['cost']['age']<=2.62]
        finished=[f for f in fall if not row['skipTurnPreparation'] and f['preparationFrames']>0 and not f['preparationPending']]
        batches={f['preparation']['frame']:f['preparation'] for f in frames if f['preparation']['frame']==f['frame'] and f['preparationBatches']>0}
        between={}
        for gen in range(3):
            counts=[]
            for a,b in zip(frames,frames[1:]):
                if a['cost']['gcMaxGeneration']>=gen and b['cost']['gcMaxGeneration']>=gen:
                    counts.append(b['cost'][f'gc{gen}BeforeUpdate']-a['cost'][f'gc{gen}AfterUpdate'])
            between[str(gen)]=sum(counts) if counts else None
        worst=max(after,key=lambda f:f['cost']['renderMs']) if after else None
        worst_interval=max(after,key=lambda f:f['intervalMs']) if after else None
        neighbors=[]
        if worst:
            at=frames.index(worst);neighbors=frames[max(0,at-2):at+3]
        def interval_attribution(frame):
            at=frames.index(frame);prior=frames[at-1] if at else None
            begin=prior['cost']['updateStartedWall'] if prior else None;end=frame['cost']['updateStartedWall']
            def overlaps(a,b):return begin is not None and a<end and b>begin
            return {'frame':frame['frame'],'reportedIntervalMs':frame['intervalMs'],'previousUpdateStartedWall':begin,'currentUpdateStartedWall':end,
                    'updateStartBracketMs':None if begin is None else (end-begin)*1000,
                    'commandOverlapsUpdateStartBracket':overlaps(row['commandStartedWall'],row['commandFinishedWall']),
                    'preparationBatchesOverlappingUpdateStartBracket':[b for b in batches.values() if overlaps(b['startedWall'],b['finishedWall'])],
                    'previousFrame':prior,'currentFrame':frame,
                    'scope':'Previous/current recorded Update starts bracket work preceding this frame. They are not exact engine deltaTime endpoints. Current Render belongs to this frame; intervalMs can include earlier command, preparation, engine or scheduler work.'}
        interval_neighbors=[]
        if worst_interval:
            at=frames.index(worst_interval);interval_neighbors=frames[max(0,at-2):at+3]
        natural.append({'name':row['name'],'family':row['family'],'count':row['count'],'repeat':row['repeat'],'skipTurnPreparation':row['skipTurnPreparation'],
                        'rawRow':row,'allRetained':frame_summary(frames),'preCommand':frame_summary(before),'postCommand':frame_summary(after),'powerFall':frame_summary(fall),
                        'latePowerFall2440To2620ms':frame_summary(late),'powerFallAfterPreparation':frame_summary(finished),
                        'preparationBatchesObserved':list(batches.values()),'betweenUpdateCompletedCollections':between,'worstPostCommandRenderNeighborhood':neighbors,
                        'worstPostCommandRenderIntervalAttribution':interval_attribution(worst) if worst else None,
                        'worstPostCommandIntervalNeighborhood':interval_neighbors,'worstPostCommandIntervalAttribution':interval_attribution(worst_interval) if worst_interval else None})
    natural_pairs=[]
    for a,b in zip(natural[::2],natural[1::2]):
        control=a if a['skipTurnPreparation'] else b;current=b if a['skipTurnPreparation'] else a
        assert (control['family'],control['count'],control['repeat'])==(current['family'],current['count'],current['repeat'])
        changes={}
        for scope in ['postCommand','powerFall','latePowerFall2440To2620ms','powerFallAfterPreparation']:
            changes[scope]={}
            for metric in ['renderMs','intervalMs','updateMs']:
                c=control[scope][metric];n=current[scope][metric]
                changes[scope][metric]={key:n[key]-c[key] if n[key] is not None and c[key] is not None else None for key in ['median','p95','max']}
        natural_pairs.append({'family':a['family'],'count':a['count'],'repeat':a['repeat'],'control':control['name'],'prepared':current['name'],'preparedMinusSkipped':changes})
    frozen=[]
    for row in report['frozenRows']:
        costs={branch:[p[branch+'Cost'] for p in row['pairs']] for branch in ['control','refined']}
        metrics={}
        for key in ['updateMs','renderMs','outerSampleMs','outerDrawMs','outerUploadMs']:
            control=stats(c[key] for c in costs['control']);refined=stats(c[key] for c in costs['refined'])
            metrics[key]={'control76Sampling':control,'refined77Sampling':refined,'differenceOfMedians':refined['median']-control['median'],
                          'pairedDifferences':[p['refinedCost'][key]-p['controlCost'][key] for p in row['pairs']],
                          'currentSlowerPairs':sum(p['refinedCost'][key]>p['controlCost'][key] for p in row['pairs'])}
        frozen.append({'name':row['name'],'family':row['family'],'count':row['count'],'age':row['age'],'metrics':metrics,'rawRow':row})
    # Maxima use all matching observed frames, never only the displayed neighborhood.
    prepared=[f for row in natural if not row['skipTurnPreparation'] for f in report['frames'][row['rawRow']['frameStart']:row['rawRow']['frameStart']+row['rawRow']['frameCount']] if f['cost']['renderStartedWall']>=row['rawRow']['commandFinishedWall']]
    skipped=[f for row in natural if row['skipTurnPreparation'] for f in report['frames'][row['rawRow']['frameStart']:row['rawRow']['frameStart']+row['rawRow']['frameCount']] if f['cost']['renderStartedWall']>=row['rawRow']['commandFinishedWall']]
    extremes={'preparedPostCommandMaxRenderMs':max(f['cost']['renderMs'] for f in prepared),'preparedPostCommandMaxIntervalMs':max(f['intervalMs'] for f in prepared),
              'skippedPostCommandMaxRenderMs':max(f['cost']['renderMs'] for f in skipped),'skippedPostCommandMaxIntervalMs':max(f['intervalMs'] for f in skipped),
              'preparedMaxWorkerBatchMs':max(r['maximumPreparationBatchMs'] for r in report['naturalRows'] if not r['skipTurnPreparation'])}
    fluidity=read('Android/Fluidity/Measurement.json');cascade=read('Android/Cascade/measure/Report.json')
    assert fluidity['status']=='RECORDED_NATIVE_FLUIDITY' and not fluidity['errors']
    assert cascade['status']=='PASS_CASCADE_PLAYBACK' and not cascade['errors']
    def bind_device(stage,installation_path,raw):
        installed=read(installation_path);guard=read('Android/'+stage+'_Data_Audit.json')
        assert installed['serial']=='emulator-5556' and installed.get('apk_sha256',installed.get('sha256'))==apk['sha256']
        if 'installed_apk_sha256' in installed:assert installed['installed_apk_sha256']==apk['sha256']
        assert guard['exit_code']==0 and guard['apk_sha256']==apk['sha256'] and guard['data_unchanged'] and guard['before']==guard['after']
        parse=lambda value:datetime.fromisoformat(value.replace('Z','+00:00'))
        assert parse(raw['utc'])>=parse(installed['utc'])
    bind_device('Fluidity','Android/Fluidity/Installation.json',fluidity)
    bind_device('Cascade','Android/Cascade/measure/Installation.json',cascade)
    density=[]
    for family in ('crate','stone','gate','tiles'):
        measured=read('Android/Density/candidate_review-'+family+'/Report.json')
        assert measured['status']=='PASS_OBSTACLE_DENSITY_PLAYBACK' and not measured['errors']
        bind_device('Density_'+family,'Android/Density/candidate_review-'+family+'/Installation.json',measured)
        post=[f for f in measured['frames'] if f['cost']['renderStartedWall']>=measured['rows'][f['phase']]['commandFinishedWall']]
        density.append({'family':family,'rows':measured['rows'],'allRetained':frame_summary(measured['frames']),
                        'postCommand':frame_summary(post),'worstPostCommandRender':max(post,key=lambda f:f['cost']['renderMs']),
                        'worstPostCommandInterval':max(post,key=lambda f:f['intervalMs'])})
    broader={'fluidityPhases':fluidity['phases'],'ordinaryCascadeRows':cascade['rows'],'density':density,
             'scope':'Separate current-APK ordinary QA probes, not same-bank paired sampler/preparation controls. Density uses detailed per-draw instrumentation; power-fall controls use coarse instrumentation. All primary samples stay in the hash-bound raw reports. Post-command Render does not isolate interval causality. Intentional 15fps intervals must not be compared with a 60fps budget.'}
    remaining=[
        f"Prepared natural frames whose Render starts after the command ends reach {extremes['preparedPostCommandMaxRenderMs']:.3f}ms Render and {extremes['preparedPostCommandMaxIntervalMs']:.3f}ms reported interval; separate skipped-control maxima are {extremes['skippedPostCommandMaxRenderMs']:.3f}/{extremes['skippedPostCommandMaxIntervalMs']:.3f}ms. Such intervals can still contain the preceding command or preparation; raw Update-start brackets and overlap tags are retained. Extrema from distinct calls do not prove exclusive causality.",
        f"The cooperative 1ms preparation threshold is checked after native work. Actual maximum batch is {extremes['preparedMaxWorkerBatchMs']:.3f}ms. Coroutine batches can occur after Update/Render; their wall intervals and whole-frame pacing remain separate from Render timing.",
        f"Separate ordinary QA still reaches {max(r['commandMs'] for r in cascade['rows']):.3f}ms command spans, while Fluidity reaches {max(r['commandMs'] for r in fluidity['phases']):.3f}ms command spans and {max(r['worstMs'] for r in fluidity['phases']):.3f}ms intervals. These are broader remaining costs, not a claim that the targeted preparation change improves every input or frame.",
        'Natural preparation controls vary only ahead-of-time sprite/geometry work. Frozen same-bank controls vary only sampler calculations after warming. They are distinct experiments; timing distributions from separately played natural turns are not aligned identical-frame CPU controls.',
        'Complete requested resident manifests are prepared, not every power texture. Short lead times, later eviction, the 2048 preparation cap and long-session cache churn retain the original demand fallback; zero misses in a targeted late window is not a universal no-allocation guarantee.',
        'Completed GC counters identify collection completion within/between Update brackets; they do not measure incremental-slice CPU, all allocations or prove GC caused a specific stall.',
        'The archived 76 sparse-stone 149.973ms interval/68.1597ms Render remains preserved historical evidence. New minima/maxima cannot retroactively assign its exclusive cause. Native Editor and Android raw-turn serialization are separate domains; device raw hashes compare with the Android baseline, while native replays prove same-domain immutability and exact final/late-key controls.',
        'No sustained 60fps, first-use input-to-display, GPU-completion, physical-device, long-session, rapid-next-input or fresh Match Villains parity certification. Ideal animation schedules and conservative continuation eligibility are unchanged.']
    return {'status':'ANALYZED_POWER_FALL77_WITH_REMAINING_GATES','utc':datetime.now(timezone.utc).isoformat(),'apk_sha256':apk['sha256'],'source_sha256':sha(out/'Source_SHA256.json'),
            'validated':validated,'naturalRows':natural,'naturalPairs':natural_pairs,'frozenRows':frozen,'observedPerformanceExtremes':extremes,'broaderCurrentQA':broader,
            'nativeSampling':native,'nativeOriginalClockPreparation':preparation,'archived 76PairedExtremes':old['pairedDensityExtremes'],
            'remainingGates':remaining,'artifactSHA256':dict(sorted(artifacts.items())),'externalEvidenceSHA256':dict(sorted(external.items())),
            'analyzerSHA256':sha(Path(__file__)),'validatorSHA256':sha(runner)}

def main():
    result=build();path=DEFAULT/'Performance_Analysis.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'validated':result['validated'],'extremes':result['observedPerformanceExtremes']}))
if __name__=='__main__':main()
