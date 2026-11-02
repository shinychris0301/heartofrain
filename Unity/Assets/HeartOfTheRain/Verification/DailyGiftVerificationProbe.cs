#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;using System.Collections;using System.Collections.Generic;using System.IO;using System.Linq;
using UnityEngine;using UnityEngine.UI;
using HeartOfTheRain.App.Profile;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.App.FirstStart;using HeartOfTheRain.App.Localization;using HeartOfTheRain.App.Celebrations;using HeartOfTheRain.M46;using HeartOfTheRain.M47;using HeartOfTheRain.M48;
namespace HeartOfTheRain.Verification {
    // Explicit opt-in, isolated file profiles. Never resets or edits player saves.
    public sealed class DailyGiftVerificationProbe:MonoBehaviour {
        public const string RequestName="HOTR_RunDailyGift";
        [Serializable] public sealed class Request {public string runId,mode;}
        [Serializable] public sealed class Report {public string utc,status="RUNNING",mode,runId,unity,scope="Native connected Home/Daily Gift/gameplay with an isolated file profile and LOCAL simulated authority. Programmatic actions except explicitly recorded Android taps; no production-server or physical-device certification.";public int checks,x,y,coins,lives,claims;public List<string> passed=new List<string>(),frames=new List<string>(),failures=new List<string>();}
        public static string Folder(string runId,string mode)=>Path.Combine(Application.persistentDataPath,"DailyGiftVerification",runId,"Evidence",mode);
        sealed class FaultRepository:IProfileRepository {
            public IProfileRepository inner;public bool Unavailable,FailAfterCommit;
            public PlayerProfile Read(){if(Unavailable)throw new IOException("Injected unavailable save read");return inner.Read();}
            public PlayerProfile Commit(long revision,PlayerProfile next){var saved=inner.Commit(revision,next);if(FailAfterCommit){FailAfterCommit=false;Unavailable=true;throw new IOException("Injected lost save confirmation");}return saved;}
        }
        public Report report;Request request;PlayerProfileHost host;HomePage home;HomeLevelFlow flow;DailyGiftPage page;DevelopmentGiftAuthority authority;FaultRepository client;long day=100;float deadline;int locale;
        string folder=>Folder(request.runId,request.mode);
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){var path=Path.Combine(Application.persistentDataPath,RequestName);if(!File.Exists(path))return;var request=JsonUtility.FromJson<Request>(File.ReadAllText(path));File.Delete(path);Guid id;if(request==null||!Guid.TryParseExact(request.runId,"N",out id)||!new[]{"Auto","Tap","Restart","StartAttempt","Recover","RecoverAgain","WonRestart"}.Contains(request.mode))throw new InvalidOperationException("Invalid gift verification request");
            var first=FindFirstObjectByType<FirstStartPage>();first.reviewAlways=true;var probe=new GameObject("Opt-in isolated Daily Gift verification").AddComponent<DailyGiftVerificationProbe>();probe.request=request;probe.home=first.home;probe.host=first.home.gameObject.AddComponent<PlayerProfileHost>();
            string root=Path.Combine(Application.persistentDataPath,"DailyGiftVerification",request.runId);probe.client=new FaultRepository{inner=new FileProfileRepository(Path.Combine(root,"Client"),()=>PlayerProfile.New(first.home.GetComponent<HomeLevelFlow>().assets.initialStock))};probe.host.VerificationRepository=probe.client;
            probe.host.VerificationAuthorityFactory=player=>probe.authority=new DevelopmentGiftAuthority(new FileProfileRepository(Path.Combine(root,"Authority"),()=>new PlayerProfile{playerId=player,coins=0,starting=new int[4],tools=new int[4]}),()=>probe.day,GiftSchedule.Preview());
        }
        IEnumerator Start(){report=new Report{utc=DateTime.UtcNow.ToString("o"),mode=request.mode,runId=request.runId,unity=Application.unityVersion};Directory.CreateDirectory(folder);Application.logMessageReceived+=Log;deadline=Time.realtimeSinceStartup+300;locale=GameLocale.Current;
            yield return Wait(()=>FindFirstObjectByType<FirstStartPage>().IsVisible);var first=FindFirstObjectByType<FirstStartPage>();first.Request("skip");first.Request("skip");yield return null;
            flow=home.GetComponent<HomeLevelFlow>();page=home.GetComponent<DailyGiftPage>();Check(host.Ready&&!host.IsTransient,"Connected file profile is ready and isolated");Check(home.State.currentLevel==host.Service.Read().currentLevel,"Home uses saved progression instead of preview level18");
            if(request.mode=="Tap"){
                Point(home.GetComponentsInChildren<HomeControlLabel>().First(l=>l.action=="daily"));State("READY_HOME_TAP");yield return Wait(()=>page.IsVisible);yield return new WaitForSecondsRealtime(.4f);yield return Capture("Daily_Ready");Point(page.GetComponentsInChildren<HomeControlLabel>().First(l=>l.action=="claim"));State("READY_CLAIM_TAP");yield return Wait(()=>host.Service.Read().giftClaims==1);yield return new WaitForSecondsRealtime(1.2f);Check(host.Service.Read().coins==1300,"Actual tap committed one gift");yield return Capture("Daily_Claimed");
            }else if(request.mode=="Restart"){
                var p=host.Service.Read();Check(p.coins==1300&&p.giftClaims==1&&p.pendingGift==null,"Claim survives process restart");page.Show();yield return null;page.Request("claim");Check(host.Service.Read().coins==1300&&host.Service.Read().giftClaims==1,"Repeated claim cannot credit twice");yield return Capture("Daily_Restart_Claimed");
            }else if(request.mode=="Recover"||request.mode=="RecoverAgain"){
                var p=host.Service.Read();Check(p.lives==4&&p.starting[0]==4&&p.tools[0]==2,"Interrupted attempt charges one life; starting item and tool remain spent");Check(p.attempts.Last().state=="Interrupted"&&p.attempts.Count==1,"One durable interruption receipt");yield return Capture("Home_Interrupted_"+request.mode);
            }else if(request.mode=="WonRestart"){
                var p=host.Service.Read();Check(p.completed==1&&p.currentLevel==2&&p.coins==1725&&p.stars==1&&p.lives==4,"Restart preserves settled win without another loss or reward");yield return Capture("Home_Won_Restart");
            }else if(request.mode=="StartAttempt"){
                yield return StartLevel(true);var game=FindFirstObjectByType<GameplayScreen>();var target=game.Model.Pieces.Values.First(p=>p.family=="gem");game.UseBooster(BoosterKind.Hammer,target.x,target.y);yield return Wait(()=>!game.Busy);Check(host.Service.Read().tools[0]==2,"Connected tool debit persisted before effects");Check(host.Service.Read().attempts.Last().state=="Started"&&host.Service.Read().starting[0]==4,"Successful initialization debits selected Rocket once");yield return Capture("Gameplay_Before_ForceStop");
            }else{
                for(int step=0;step<7;step++){
                    day=100+step+(step>=2?3:0);host.Refresh();page.Show();yield return null;yield return Capture("Daily_Day"+(step+1));page.Request("claim");Check(host.Service.Read().giftClaims==step+1,"Connected claim step "+step);page.Request("claim");Check(host.Service.Read().giftClaims==step+1,"Connected duplicate click step "+step);yield return null;page.Request("close");yield return null;
                }
                var saved=host.Service.Read();Check(saved.coins==1625&&saved.starting.SequenceEqual(new[]{6,6,4,2})&&saved.tools.SequenceEqual(new[]{4,3,3,3}),"All approved quantities reach shared wallet and inventory");
                for(int l=0;l<5;l++){GameLocale.Select(l);page.Show();yield return null;yield return Capture("Daily_Locale_"+GameLocale.Codes[l]);page.Request("close");yield return null;}GameLocale.Select(locale);
                authority.Offline=true;page.Show();yield return null;Check(!page.GetComponentsInChildren<Button>().Any(b=>b.name=="claim"&&b.interactable),"Unavailable authority disables claim");yield return Capture("Daily_Offline");page.Request("close");authority.Offline=false;
                day++;authority.Checkpoint=_=>throw new IOException("Injected lost development-service reply");page.Show();page.Request("claim");Check(host.Service.Read().pendingGift!=null&&host.Service.Read().coins==1625,"Lost confirmation leaves durable retry intent without credit");yield return null;yield return Capture("Daily_Pending_Retry");authority.Checkpoint=null;page.Request("claim");Check(host.Service.Read().coins==1675&&host.Service.Read().pendingGift==null,"Retry applies original confirmation once");page.Request("close");yield return null;
                // One normal connected exit, then natural moves on authored L1. No
                // reward, inventory or loss is credited by animation callbacks.
                yield return StartLevel(true);var game=FindFirstObjectByType<GameplayScreen>();var target=game.Model.Pieces.Values.First(p=>p.family=="gem");string before=JsonUtility.ToJson(game.Model.Snapshot());client.FailAfterCommit=true;game.UseBooster(BoosterKind.Hammer,target.x,target.y);Check(game.ReviewInputBlocked&&game.Paused&&page.IsVisible,"Unknown tool commit blocks conflicting input and exposes recovery");Check(JsonUtility.ToJson(game.Model.Snapshot())==before,"Unknown tool commit leaves board unchanged");yield return Capture("Tool_Save_Recovery");client.Unavailable=false;Check(host.Service.Read().tools[0]==3&&host.Service.Read().attempts.Last().toolCommands.Count==1,"Tool debit committed despite lost confirmation");page.Request("claim");yield return Wait(()=>!game.Busy);Check(host.Service.Read().tools[0]==3&&host.Service.Read().attempts.Last().toolCommands.Count==1,"Retry uses original tool command without a second debit");Check(JsonUtility.ToJson(game.Model.Snapshot())!=before&&!game.ReviewInputBlocked&&!game.Paused,"Reconciled tool action plays and restores input");Check(host.Service.Read().tools[0]==3,"Gift Hammer shares durable gameplay stock");
                game.GetComponent<HeartOfTheRain.App.Settings.GameplaySettingsController>().ShowEndLevel();yield return null;game.GetComponent<HeartOfTheRain.App.EndLevel.EndLevelModal>().Requested("confirm");yield return Wait(()=>flow.RetryVisible);Check(host.Service.Read().lives==4&&home.State.lives==4,"Connected exit settles one loss");home.GetComponent<PreLevelModal>().Requested("close");yield return null;
                yield return StartLevel(false);game=FindFirstObjectByType<GameplayScreen>();game.playbackSpeed=12;
                while(game&&game.Model.Status=="Playing"){Check(game.ReviewNaturalMove(),"Natural authored L1 move accepted");if(game.Model.Status=="Won"){var p=host.Service.Read();Check(p.completed==1&&p.coins==1725&&p.stars==1,"Win persisted while presentation is still active");}yield return Wait(()=>!game||!game.Busy);}
                Check(game&&game.Model.Status=="Won","Authored L1 natural sequence wins");
                yield return Wait(()=>VictoryCelebrationPlayer.IsPlaying(home));yield return Capture("Connected_Win_Celebration");yield return Wait(()=>!VictoryCelebrationPlayer.IsPlaying(home));yield return Wait(()=>!home.RewardRevealPlaying);Check(!flow.Playing&&!home.GetComponent<PreLevelModal>().IsVisible&&home.PresentationVisible,"Celebration returns to interactive Home without next-level modal");Check(host.Service.Read().coins==1725&&home.State.coins==1725,"Celebration cannot award the win twice");yield return Capture("Home_After_Win");
            }
            Finish(null);
        }
        IEnumerator StartLevel(bool rocket){flow.Open(1);var modal=home.GetComponent<PreLevelModal>();Check(modal.IsVisible,"Connected pre-level visible");if(rocket)modal.Requested("toggle:0");modal.Requested("play");yield return Wait(()=>flow.Playing&&!FindFirstObjectByType<GameplayScreen>().ReviewInputBlocked);Check(host.Service.Read().attempts.Last().state=="Started","Attempt start committed before player input");}
        IEnumerator Wait(Func<bool> ready){while(!ready())yield return null;}
        void Point(Component component){var rt=(RectTransform)component.transform;var c=RectTransformUtility.WorldToScreenPoint(null,rt.TransformPoint(rt.rect.center));report.x=Mathf.RoundToInt(c.x);report.y=Screen.height-Mathf.RoundToInt(c.y);}
        IEnumerator Capture(string name){yield return new WaitForSecondsRealtime(.2f);if(Application.isEditor)yield break;yield return new WaitForEndOfFrame();var pixels=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(Path.Combine(folder,name+".png"),pixels.EncodeToPNG());Destroy(pixels);report.frames.Add(name+".png");}
        void Check(bool ok,string name){report.checks++;if(!ok)throw new InvalidOperationException(name);report.passed.Add(name);}
        void State(string status){report.status=status;Save();}
        void Save(){var p=host.Service.Read();report.coins=p.coins;report.lives=p.lives;report.claims=p.giftClaims;File.WriteAllText(Path.Combine(folder,"Report.json"),JsonUtility.ToJson(report,true));}
        void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)Finish(message+"\n"+stack);}
        void Update(){if(report!=null&&!report.status.StartsWith("PASS")&&!report.status.StartsWith("FAIL")&&Time.realtimeSinceStartup>deadline)Finish("Verification timed out at "+report.status);}
        void Finish(string error){if(report.status.StartsWith("PASS")||report.status.StartsWith("FAIL"))return;Application.logMessageReceived-=Log;report.status=error==null?"PASS_NATIVE_DAILY_GIFT":"FAIL_NATIVE_DAILY_GIFT";if(error!=null)report.failures.Add(error);GameLocale.Select(locale);Save();}
        void OnDestroy(){Application.logMessageReceived-=Log;}
    }
}
#endif
