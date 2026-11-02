"""Run the explicit checkpoint77 power-fall fixture on QA without changing real saves."""
import argparse,hashlib,json,re,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from qa_android_target import validate_qa_target
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Gameplay77/PowerFall'
ADB=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
APK=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
PKG='com.heartoftherain.verification';BASE=f'/sdcard/Android/data/{PKG}/files'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def validate_report(report, baseline_hashes=None):
    """Strict read-only raw proof; no device execution or speedup acceptance."""
    import math
    number=lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    nonnegative=lambda v:number(v) and v>=0
    integer=lambda v:isinstance(v,int) and not isinstance(v,bool) and v>=0
    digest=lambda v:isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v)
    outer=('outerSetupMs','outerSampleMs','outerBeginMs','outerDrawMs','outerDisableMs',
           'outerUploadMs','outerEndCollectionsMs','outerBankEndMs','outerSelectionMs')
    durations=('updateMs','renderMs','outerSpanMs','outerWrapperResidualMs','sampleMs',
               'bodySampleMs','effectsSampleMs','sortMs','lookupMs','batchAddMs',
               'batchUploadMs','spriteUpdateMs','bankEndMs')
    def cost(v):
        assert all(nonnegative(v[k]) for k in outer+durations),'Invalid CPU duration'
        assert abs(sum(v[k] for k in outer)-v['outerSpanMs'])<.001,'Outer spans are not disjoint/accounted'
        assert v['outerSpanMs']<=v['renderMs']+.15 and abs(v['renderMs']-v['outerSpanMs']-v['outerWrapperResidualMs'])<.001,'Render wrapper accounting differs'
        assert v['bodySampleMs']+v['effectsSampleMs']+v['sortMs']<=v['outerSampleMs']+.15,'Sampling spans escaped owner'
        assert v['lookupMs']+v['batchAddMs']+v['spriteUpdateMs']<=v['outerDrawMs']+.15,'Per-draw spans escaped owner'
        assert v['batchUploadMs']<=v['outerUploadMs']+.15 and v['bankEndMs']<=v['outerBankEndMs']+.15,'Upload/cache span escaped owner'
        assert v['sampleMs']<=v['outerSampleMs']+v['outerBeginMs']+.15 and v['renderMs']<=v['updateMs']+.15,'Nested spans escaped Update/Render'
        times=[v[k] for k in ('updateStartedWall','renderStartedWall','renderFinishedWall','updateFinishedWall')]
        assert all(nonnegative(x) for x in times) and times==sorted(times),'Cost wall chronology differs'
        assert integer(v['frame']) and integer(v['gcMaxGeneration']),'Invalid frame/GC support'
        for gen in range(3):
            values=[v['gc'+str(gen)+p] for p in ('BeforeUpdate','BeforeRender','AfterRender','AfterUpdate')]
            if gen>v['gcMaxGeneration']:assert values==[-1]*4,'Unsupported generation has fabricated counts'
            else:assert all(integer(x) for x in values) and values==sorted(values),'Completed collection counts regress'
        assert all(integer(v[k]) for k in ('poolCreated','spriteCreated','draws','crateDraws','meshQuads','meshes','geometryMisses','meshSlotsCreated')),'Invalid resource/draw counts'
        assert number(v['clock']) and number(v['age']),'Invalid playback clock'
        assert v['crateDraws']<=v['draws'] and v['meshQuads']<=v['draws'],'Impossible draw counts'
        return v
    assert report['status']=='PASS_NATIVE_POWER_FALL77' and report['profilingSchemaVersion']==2 and not report['errors'],'Power-fall fixture failed or stale schema'
    assert report['detailedDrawCosts'] is False and report['isolatedProfile'] is True and report['launchCleared'] is True,'Wrong observer mode or hidden/unisolated fixture'
    assert len(report['naturalRows'])==16 and len(report['frozenRows'])==4,'Matched power-fall scope incomplete'
    assert report['bufferCapacity']==16384 and 0<len(report['frames'])<=report['bufferCapacity'],'Frame buffer incomplete/overflowed'
    if baseline_hashes is None:
        baseline_hashes={}
        for family in ('crate','stone'):
            old=json.loads((ROOT/('Verification/Evidence/Gameplay76/Android/Density/candidate_review-'+family+'/Report.json')).read_text('utf-8-sig'))
            assert old['status']=='PASS_OBSTACLE_DENSITY_PLAYBACK'
            for count in (1,45):
                values={(r['turnHash'],r['finalHash']) for r in old['rows'] if r['crates']==count}
                assert len(values)==1,'Historical deterministic density hashes disagree'
                baseline_hashes[(family,count)]=values.pop()
    expected=[]
    for family in ('crate','stone'):
        for count in (1,45):
            for repeat in (0,1):
                for branch in (0,1):expected.append((family,count,repeat,(branch==0)==(repeat%2==0)))
    offset=0;last_frame=-1;actual_costs=0;observed_after_preparation=0;late_demand_rows=[]
    for index,(row,spec) in enumerate(zip(report['naturalRows'],expected)):
        family,count,repeat,skipped=spec
        assert all(integer(row[k]) for k in ('count','repeat','commandFrame','frameStart','frameCount')) and isinstance(row['skipTurnPreparation'],bool)
        assert (row['family'],row['count'],row['repeat'],row['skipTurnPreparation'])==spec,'Natural AB/BA order/flags changed'
        assert row['name']==family+'_'+str(count)+'_'+str(repeat)+('_skipped' if skipped else '_prepared')
        assert (row['turnHash'],row['finalHash'])==baseline_hashes[(family,count)],'Natural model outcome changed'
        assert row['frameStart']==offset and integer(row['frameCount']) and row['frameCount']>2,'Natural frame slice incomplete'
        frames=report['frames'][offset:offset+row['frameCount']];offset+=row['frameCount']
        assert len(frames)==row['frameCount'] and all(f['row']==index for f in frames),'Natural frame ownership differs'
        assert all(nonnegative(row[k]) for k in ('preparationSeconds','commandStartedWall','commandFinishedWall','modelMs','acceptMs','commandMs','settleSeconds','maximumPreparationBatchMs'))
        assert row['commandStartedWall']<=row['commandFinishedWall'] and abs((row['commandFinishedWall']-row['commandStartedWall'])*1000-row['commandMs'])<.01
        assert row['commandMs']+.15>=row['modelMs']+row['acceptMs'] and row['settleSeconds']*1000+.15>=row['commandMs']
        command=row['enqueueCost'];assert command['frame']==row['commandFrame'] and integer(command['phases']) and command['phases']>0
        assert all(nonnegative(command[k]) for k in ('buildMs','nextMs','dependenciesMs','prefetchMs','totalMs'))
        assert sum(command[k] for k in ('buildMs','nextMs','dependenciesMs','prefetchMs'))<=command['totalMs']+.15 and command['totalMs']<=row['acceptMs']+.15
        assert frames[0]['frame']==row['commandFrame'],'Natural command-frame observer sample is missing'
        previous=None;tail=False;late=[]
        for f in frames:
            v=cost(f['cost']);actual_costs+=1
            assert f['frame']==v['frame']>last_frame and nonnegative(f['absoluteWall']) and nonnegative(f['intervalMs'])
            last_frame=f['frame'];assert v['updateFinishedWall']<=f['absoluteWall']+.001,'LateUpdate snapshot predates Update'
            assert all(integer(f[k]) for k in ('spriteCreates','spriteEvictions','synchronousLoads','cachedSprites','cachedTextures','preparationBatches','preparationFrames','preparationCreates'))
            assert f['preparationCreates']<=f['preparationFrames'] and isinstance(f['preparationPending'],bool)
            if f['frame']==row['commandFrame']:
                assert v['updateFinishedWall']<=row['commandStartedWall']+.001 and row['commandFinishedWall']<=f['absoluteWall']+.001,'Command-frame prior Render/tail misattributed'
                tail=True
            if previous:
                assert f['frame']==previous['frame']+1,'A primary natural Update frame was removed'
                assert previous['absoluteWall']<=f['absoluteWall']
                assert all(previous[k]<=f[k] for k in ('spriteCreates','spriteEvictions','synchronousLoads','preparationBatches','preparationFrames','preparationCreates')),'Cumulative resource/preparation counts regress'
                for gen in range(min(2,v['gcMaxGeneration'])+1):assert previous['cost']['gc'+str(gen)+'AfterUpdate']<=v['gc'+str(gen)+'BeforeUpdate'],'Collection count regresses between frames'
            if f['preparationBatches']:
                b=f['preparation'];assert integer(b['frame']) and b['frame']<=f['frame'] and integer(b['frames']) and b['frames']<=16 and integer(b['spriteCreates']) and b['spriteCreates']<=b['frames']
                assert all(nonnegative(b[k]) for k in ('startedWall','finishedWall','milliseconds')) and b['startedWall']<=b['finishedWall']<=f['absoluteWall']+.001
                assert b['milliseconds']<=row['maximumPreparationBatchMs']+.001
            if v['kind']=='powerFall' and not f['preparationPending'] and f['preparationFrames']>0:observed_after_preparation+=1
            if v['kind']=='powerFall' and 2.44<=v['age']<=2.62:late.append({'frame':f['frame'],'age':v['age'],'spriteCreated':v['spriteCreated'],'geometryMisses':v['geometryMisses'],'preparationPending':f['preparationPending']})
            previous=f
        assert tail,'Command-frame pre-command cost and tail were lost'
        assert frames[-1]['preparationPending'] is False,'Natural fixture ended with resource preparation pending'
        assert all(integer(row[k]) for k in ('spriteCreates','spriteEvictions','synchronousLoads','preparationBatches','preparationFrames','preparationCreates','preparationSkippedAtlases'))
        for k in ('spriteCreates','spriteEvictions','synchronousLoads','preparationBatches','preparationFrames','preparationCreates'):assert row[k]>=frames[-1][k]
        if skipped:assert row['preparationBatches']==row['preparationFrames']==row['preparationCreates']==0 and not any(f['preparationPending'] for f in frames),'Skipped control performed preparation'
        else:assert row['preparationBatches']>0 and row['preparationFrames']>0,'Prepared branch never performed native work'
        late_demand_rows.append({'name':row['name'],'samples':late})
    assert offset==len(report['frames']),'Unowned extra natural frames'
    assert observed_after_preparation>0,'No actual post-preparation powerFall frame'
    assert {(r['family'],r['count']) for r in report['frozenRows']}==set(baseline_hashes) and len({r['name'] for r in report['frozenRows']})==4
    for row in report['frozenRows']:
        assert row['name']==row['family']+'_'+str(row['count']) and (row['turnHash'],row['finalHash'])==baseline_hashes[(row['family'],row['count'])]
        assert digest(row['queueHash']) and row['resourcesReady'] is True and row['preparationPending'] is False and abs(row['age']-2.5761446952819824)<.000001 and row['phaseDuration']>=row['age'] and integer(row['phaseIndex'])
        draws=[row[p+'DrawHash'] for p in ('beforeControl','beforeRefined','afterControl','afterRefined')]
        meshes=[row[p+'MeshHash'] for p in ('beforeControl','beforeRefined','afterControl','afterRefined')]
        assert all(digest(v) for v in draws+meshes) and len(set(draws))==len(set(meshes))==1,'Frozen same-pose draw/upload parity failed'
        assert len(row['pairs'])==4
        last_wall=-1;last_pair_frame=None
        for index,pair in enumerate(row['pairs']):
            assert integer(pair['index']) and pair['index']==index and pair['controlFirst'] is (index%2==0),'Frozen AB/BA order differs'
            a,b=('control','refined') if pair['controlFirst'] else ('refined','control')
            assert last_wall<=pair[a+'StartedWall']<=pair[a+'FinishedWall']<=pair[b+'StartedWall']<=pair[b+'FinishedWall'],'Frozen timed calls overlap/reorder'
            last_wall=pair[b+'FinishedWall']
            for branch in ('control','refined'):
                assert nonnegative(pair[branch+'StartedWall']) and nonnegative(pair[branch+'FinishedWall'])
                v=cost(pair[branch+'Cost']);assert pair[branch+'StartedWall']<=v['updateStartedWall']<=v['updateFinishedWall']<=pair[branch+'FinishedWall']+.001
                assert v['kind']=='powerFall' and abs(v['age']-row['age'])<.00001 and abs(v['clock']-row['clock'])<.00001,'Frozen pose advanced during paired calls'
                assert v['poolCreated']==v['spriteCreated']==v['geometryMisses']==v['meshSlotsCreated']==0,'Frozen control is not warmed'
            assert all(pair['controlCost'][k]==pair['refinedCost'][k] for k in ('draws','crateDraws','meshQuads','meshes')),'Frozen draw count changed'
            assert pair['controlCost']['frame']==pair['refinedCost']['frame'],'Frozen paired calls did not share an actual Unity frame'
            if last_pair_frame is not None:assert pair['controlCost']['frame']==last_pair_frame+1,'Frozen pair frame ordering differs'
            last_pair_frame=pair['controlCost']['frame']
            for gen in range(min(2,pair[a+'Cost']['gcMaxGeneration'])+1):assert pair[a+'Cost']['gc'+str(gen)+'AfterUpdate']<=pair[b+'Cost']['gc'+str(gen)+'BeforeUpdate']
    return {'natural_turns':16,'natural_frames':actual_costs,'frozen_fixtures':4,'frozen_pairs':16,'timed_render_calls':32,
            'post_preparation_fall_frames':observed_after_preparation,'late_demand_rows':late_demand_rows,
            'scope':'Same-APK AB/BA preparation controls on fresh banks and same-bank/same-pose sampling controls. '
                    'All primary rows and GC counts retained; elapsed spans include observer/host scheduling. '
                    'Command-frame prior Render is distinct from command tail. No universal speedup, cache-flush, '
                    'exclusive GC/OS cause or physical-device claim.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serial',required=True);parser.add_argument('--install',action='store_true');parser.add_argument('--out',type=Path,default=OUT);args=parser.parse_args()
    qa_target=validate_qa_target(args.serial,args.out)
    folder=args.out.resolve();assert folder.is_relative_to((ROOT/'Verification/Evidence').resolve());folder.mkdir(parents=True,exist_ok=True)
    def adb(*cmd,check=True):return subprocess.run([str(ADB),'-s',args.serial,*map(str,cmd)],capture_output=True,check=check,timeout=180).stdout
    def state():
        names=adb('shell','run-as',PKG,'ls','shared_prefs').decode().split()
        prefs={n:adb('shell','run-as',PKG,'sha256sum','shared_prefs/'+n).decode().split()[0] for n in names if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',n)}
        names=adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json').decode().splitlines()
        saves={n.removeprefix(BASE+'/'):adb('shell','sha256sum',n).decode().split()[0] for n in names if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',n)}
        return {'preferences':prefs,'saves':saves}
    assert adb('get-state').strip()==b'device'
    profile=json.loads(json.loads(adb('shell','cat',BASE+'/Profiles/Development-v1/profile.json'))['payload'])
    assert not any(a['state'] in ['Reserved','Started'] for a in profile['attempts']),'Preserve an active QA attempt'
    adb('shell','am','force-stop',PKG);before=state();started=datetime.now(timezone.utc).isoformat();digest=sha(APK)
    result={'utc':started,'serial':args.serial,'qa_target':qa_target,'apk_sha256':digest,'before':before,'scope':'Opt-in memory profile and isolated fixture board, no attempt/progression callbacks or screen taps. Real saves/preferences are hash-audited; no reset or physical-device claim.'}
    error=None
    try:
        if args.install:
            result['install']=adb('install','-r',APK).decode().strip();assert 'Success' in result['install'] and state()==before,'Install failed or changed saves'
        remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip();result['installed_apk_sha256']=adb('shell','sha256sum',remote).decode().split()[0];assert result['installed_apk_sha256']==digest,'Wrong QA APK installed'
        request=ROOT/'.verification-cache/Gameplay77/PowerFallRequest';request.parent.mkdir(parents=True,exist_ok=True);request.write_text('all','ascii')
        adb('shell','mkdir','-p',BASE);adb('shell','rm','-f',BASE+'/PowerFall77/Report.json');adb('push',request,BASE+'/HOTR_RunPowerFall77')
        result['launch']=adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity').decode().strip()
        deadline=time.monotonic()+900
        while time.monotonic()<deadline:
            raw=adb('shell','cat',BASE+'/PowerFall77/Report.json',check=False)
            try:report=json.loads(raw)
            except (ValueError,UnicodeError):time.sleep(3);continue
            if report['status']!='RUNNING':break
            time.sleep(3)
        else:raise TimeoutError('Power-fall report unavailable; preserve logs and installed data')
        (folder/'Report.json').write_bytes(raw);result['validated']=validate_report(report)
        assert datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(started),'Stale power-fall report'
        pid=adb('shell','pidof',PKG).decode().strip();result['pid']=pid
        logs=adb('logcat','-d','--pid='+pid,'-v','brief').decode(errors='replace');(folder/'Runtime.log').write_text(logs,encoding='utf-8')
        result['runtime_errors']=len(re.findall(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException',logs));assert result['runtime_errors']==0,'Native runtime error'
    except Exception as e:error=e;result['error']=str(e)
    finally:
        result['after']=state();result['data_unchanged']=result['after']==before;result['finishedUtc']=datetime.now(timezone.utc).isoformat();result['status']='PASS_POWER_FALL77_DEVICE_AUDIT' if error is None and result['data_unchanged'] else 'FAIL_POWER_FALL77_DEVICE_AUDIT'
        (folder/'Installation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    assert result['data_unchanged'],'Power-fall fixture changed real saved data'
    if error is not None:raise error
    print(json.dumps({k:result[k] for k in ['status','apk_sha256','data_unchanged','validated']}),flush=True)

if __name__=='__main__':main()
