"""Compare same-APK opt-in controls; do not infer physical-device frame rates."""
import datetime as dt,json,statistics
from pathlib import Path
from measure_fluidity import ROOT
OUT=ROOT/'Verification/Evidence/PowerWarmup'

def percentile(values,q):
    values=sorted(values);return values[min(len(values)-1,int(len(values)*q))] if values else None

def run():
    rows=[];recordings={}
    for folder in ['Baseline','WarmOnly','CacheOnly','Candidate','CandidateRepeat','BaselineRepeat']:
        path=OUT/folder
        if not (path/'Measurement.json').exists():continue
        report=json.loads((path/'Measurement.json').read_text());install=json.loads((path/'Installation.json').read_text())
        recordings[folder]=report
        assert report['status']=='RECORDED_NATIVE_FLUIDITY' and not report['errors']
        for kind in ['orb_rocket','golden_bomb']:
            indices=[n for n,p in enumerate(report['phases']) if p['name'].startswith(kind)]
            phases=[report['phases'][n] for n in indices]
            samples=[s for s in report['frameSamples'] if s['phase'] in indices]
            rows.append({'variant':report['variant'],'folder':folder,'kind':kind,'repeats':len(phases),'frames':sum(p['frames'] for p in phases),'over33ms':sum(p['over33ms'] for p in phases),'over50ms':sum(p['over50ms'] for p in phases),'p95IntervalMs':percentile([s['intervalMs'] for s in samples],.95),'worstIntervalMs':max(p['worstMs'] for p in phases),'medianCommandMs':statistics.median(p['commandMs'] for p in phases),'medianPreparationSeconds':statistics.median(p['preparationSeconds'] for p in phases),'poolGrowth':sum(p['poolAtEnd']-p['poolAtReady'] for p in phases),'combatSpriteCreates':sum(p['spriteCreates'] for p in phases),'gen0Collections':sum(p['gen0Collections'] for p in phases),'p50RenderMs':percentile([s['renderMs'] for s in samples],.5),'p95RenderMs':percentile([s['renderMs'] for s in samples],.95),'p95SampleMs':percentile([s['sampleMs'] for s in samples],.95),'p95UpdateMs':percentile([s['updateMs'] for s in samples],.95),'worstUpdateMs':max(s['updateMs'] for s in samples),'textureBytes':max(p['textureBytes'] for p in phases),'cachedSpriteRuntimeBytes':max(p['cachedSpriteRuntimeBytes'] for p in phases),'apk_sha256':install['sha256']})
            # Use thresholds between refresh multiples:33.34/50ms straddle
            # the emulator's slightly drifting two/three-refresh clocks.
            rows[-1].update(twoPlusRefreshIntervals=sum(s['intervalMs']>25 for s in samples),threePlusRefreshIntervals=sum(s['intervalMs']>41.7 for s in samples),sixPlusRefreshIntervals=sum(s['intervalMs']>91.7 for s in samples))
            rows[-1]['p95BindingMs']=percentile([max(0,s['renderMs']-s['sampleMs']) for s in samples],.95)
    aggregates=[]
    for control,names in [('Baseline',['Baseline','BaselineRepeat']),('Candidate',['Candidate','CandidateRepeat'])]:
        if not all(n in recordings for n in names):continue
        for kind in ['orb_rocket','golden_bomb']:
            samples=[];phases=[]
            for n in names:
                report=recordings[n];indices=[i for i,p in enumerate(report['phases']) if p['name'].startswith(kind)];phases.extend(report['phases'][i] for i in indices);samples.extend(s for s in report['frameSamples'] if s['phase'] in indices)
            aggregates.append({'control':control,'kind':kind,'processRuns':2,'comboRepetitions':len(phases),'frames':sum(p['frames'] for p in phases),'p95RenderMs':percentile([s['renderMs'] for s in samples],.95),'p95BindingMs':percentile([max(0,s['renderMs']-s['sampleMs']) for s in samples],.95),'twoPlusRefreshIntervals':sum(s['intervalMs']>25 for s in samples),'threePlusRefreshIntervals':sum(s['intervalMs']>41.7 for s in samples),'worstIntervalMs':max(p['worstMs'] for p in phases),'poolGrowth':sum(p['poolAtEnd']-p['poolAtReady'] for p in phases),'medianPreparationSeconds':statistics.median(p['preparationSeconds'] for p in phases)})
    result={'status':'RECORDED_SAME_APK_CONTROLLED_COMPARISON','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'Three repetitions per combo per control in separate native Android runs; baseline/candidate repeated in reverse order (six combo repetitions over two app processes each), same APK and fixture seed; no video/readback during measurement. Frame intervals include emulator scheduling/GPU waits. CPU samples describe current Update; its cost affects the following frame interval. Command CPU runs after Update and is measured separately. Strict33.34/50ms counts are sensitive to display-clock rounding; counts at25/41.7ms are between refresh multiples. WarmOnly/CacheOnly have much slower unchanged sampler code too; do not infer isolated causality from those single process runs. No claim of zero allocations or physical-device performance.','rows':rows,'aggregatedControls':aggregates}
    result['scope']+=' CPU-section Stopwatch values are elapsed durations including scheduling/preemption, not per-thread OS CPU utilization.'
    (OUT/'Performance_Comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(rows,indent=2))

if __name__=='__main__':run()
