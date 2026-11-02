#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;using System.Collections;using System.Collections.Generic;using System.IO;using System.Linq;
using UnityEngine;using UnityEngine.UI;
using HeartOfTheRain.App.Profile;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.App.FirstStart;using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.Verification {
    // Explicit opt-in fixture; progress is simulated through the real attempt
    // service, not claimed as natural gameplay. Ordinary player saves untouched.
    public sealed class WellworksVerificationProbe:MonoBehaviour {
        public const string RequestName="HOTR_RunWellworks";
        [Serializable] public sealed class Request {public string runId,mode;}
        [Serializable] public sealed class Report {public string utc,status="RUNNING",mode,runId,unity,scope="Native connected Wellworks with isolated file profiles. First clears simulated through attempt services; not natural-play campaign certification. Input programmatic except recorded Android taps.";public int checks,x,y;public List<string> passed=new List<string>(),frames=new List<string>(),failures=new List<string>();}
        sealed class FaultRepository:IProfileRepository {
            public IProfileRepository inner;public bool Unavailable,FailBefore,FailAfter;
            public PlayerProfile Read(){if(Unavailable)throw new IOException("Injected unavailable profile");return inner.Read();}
            public PlayerProfile Commit(long revision,PlayerProfile next){if(FailBefore){FailBefore=false;throw new IOException("Injected before commit");}var p=inner.Commit(revision,next);if(FailAfter){FailAfter=false;throw new IOException("Injected after commit");}return p;}
        }
        public Report report;Request request;PlayerProfileHost host;HomePage home;WellworksPage page;FaultRepository client;float deadline;int locale;
        public static string Folder(string id,string mode)=>Path.Combine(Application.persistentDataPath,"WellworksVerification",id,"Evidence",mode);
        string folder=>Folder(request.runId,request.mode);
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){
            var path=Path.Combine(Application.persistentDataPath,RequestName);if(!File.Exists(path))return;var r=JsonUtility.FromJson<Request>(File.ReadAllText(path));File.Delete(path);Guid id;if(r==null||!Guid.TryParseExact(r.runId,"N",out id)||!new[]{"Auto","Tap","Restart"}.Contains(r.mode))throw new InvalidOperationException("Invalid Wellworks fixture");
            var first=FindFirstObjectByType<FirstStartPage>();first.reviewAlways=true;var probe=new GameObject("Opt-in isolated Wellworks verification").AddComponent<WellworksVerificationProbe>();probe.request=r;probe.home=first.home;probe.host=first.home.gameObject.AddComponent<PlayerProfileHost>();
            string root=Path.Combine(Application.persistentDataPath,"WellworksVerification",r.runId);probe.client=new FaultRepository{inner=new FileProfileRepository(Path.Combine(root,"Client"),()=>{var p=PlayerProfile.New(first.home.GetComponent<HomeLevelFlow>().assets.initialStock);if(r.mode=="Tap"){p.completed=9;p.currentLevel=10;p.stars=9;}return p;})};probe.host.VerificationRepository=probe.client;
            probe.host.VerificationAuthorityFactory=player=>new DevelopmentGiftAuthority(new FileProfileRepository(Path.Combine(root,"GiftAuthority"),()=>new PlayerProfile{playerId=player,coins=0,starting=new int[4],tools=new int[4]}),()=>100,GiftSchedule.Preview());
        }
        IEnumerator Start(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),mode=request.mode,runId=request.runId,unity=Application.unityVersion};Directory.CreateDirectory(folder);Application.logMessageReceived+=Log;deadline=Time.realtimeSinceStartup+240;locale=GameLocale.Current;
            yield return Wait(()=>FindFirstObjectByType<FirstStartPage>().IsVisible);var first=FindFirstObjectByType<FirstStartPage>();first.Request("skip");first.Request("skip");yield return null;page=home.GetComponent<WellworksPage>();Check(host.Ready&&!host.IsTransient,"Isolated durable profile attached");
            if(request.mode=="Tap"){
                Advance(10);host.Refresh();Check(home.State.wellworksStatus=="Ready","First-clear threshold updates Home badge");yield return Capture("Home_Ready");Point(home.GetComponentsInChildren<HomeControlLabel>().First(l=>l.action=="wellworks"));State("READY_HOME_TAP");yield return Wait(()=>page.IsVisible);yield return Capture("Wellworks_Ready");Point(page.GetComponentsInChildren<HomeControlLabel>().First(l=>l.action=="claim-10"));State("READY_CLAIM_TAP");yield return Wait(()=>WellworksService.Claimed(host.Service.Read(),10));yield return Wait(()=>!home.RewardRevealPlaying);Check(host.Service.Read().coins==1400&&host.Service.Read().stars==10,"Actual tap grants approved coins without spending stars");yield return Capture("Wellworks_Claimed");Point(page.GetComponentsInChildren<HomeControlLabel>().First(l=>l.action=="close"));State("READY_CLOSE_TAP");yield return Wait(()=>!page.IsVisible);Check(home.PresentationVisible,"Close returns interactive Home");yield return Capture("Home_Claimed");
            }else if(request.mode=="Restart"){
                var p=host.Service.Read();Check(p.completed==10&&p.coins==1400&&p.stars==10&&p.rewards.Count==1,"Claim and first clear survive process restart");Check(home.State.wellworksStatus=="10/20","Saved badge targets next milestone");page.Show();yield return null;page.Request("claim-10");Check(host.Service.Read().coins==1400&&host.Service.Read().rewards.Count==1,"Replay cannot credit saved milestone twice");yield return Capture("Wellworks_Restart");
            }else{
                Check(home.State.wellworksStatus=="0/10","Home no longer uses fixed demo status");page.Show();yield return Capture("Wellworks_Locked");Check(!page.GetComponentsInChildren<Button>().Any(b=>b.interactable&&b.name.StartsWith("claim-")),"Unreached milestones disabled");page.Request("close");Advance(10);host.Refresh();page.Show();client.FailBefore=true;page.Request("claim-10");Check(host.Service.Read().coins==1750&&!WellworksService.Claimed(host.Service.Read(),10),"Precommit failure grants nothing");Check(page.transform.Find("Wellworks Canvas").GetComponentsInChildren<Button>().Any(b=>b.name=="claim-0"&&b.interactable),"Precommit UI keeps reached row available");Check(page.transform.Find("Wellworks Canvas").GetComponentsInChildren<Text>().First(t=>t.name=="status").text==WellworksDesignText.T("error"),"Precommit error offers accurate retry copy");yield return Capture("Wellworks_Save_Error");page.Request("retry");page.Request("claim-10");Check(host.Service.Read().coins==1850&&WellworksService.Claimed(host.Service.Read(),10),"Retry grants once");page.Request("close");
                Advance(20);host.Refresh();page.Show();client.FailAfter=true;page.Request("claim-20");Check(host.Service.Read().starting[0]==6&&host.Service.Read().starting[1]==6,"Lost save reply still committed exactly once");Check(!page.transform.Find("Wellworks Canvas").GetComponentsInChildren<Button>().Any(b=>b.name=="claim-1"),"Lost reply reconciles collected row from durable receipt");Check(page.transform.Find("Wellworks Canvas").GetComponentsInChildren<Text>().First(t=>t.name=="status").text==WellworksDesignText.T("collectedNotice"),"Durable confirmation is not shown as an uncollected error");yield return Capture("Wellworks_Lost_Reply");page.Request("retry");page.Request("claim-20");Check(host.Service.Read().starting[0]==6&&host.Service.Read().rewards.Count==2,"Retry reconciles receipt without another item");page.Request("close");
                Advance(50);host.Refresh();page.Show();for(int l=0;l<5;l++){GameLocale.Select(l);yield return null;yield return Capture("Wellworks_Locale_"+GameLocale.Codes[l]);}GameLocale.Select(locale);
                foreach(int level in new[]{30,40,50}){page.Request("claim-"+level);yield return null;}var saved=host.Service.Read();Check(saved.coins==4250&&saved.stars==50&&saved.completed==50&&saved.lives==5,"All approved milestone and campaign rewards persist");Check(saved.starting.SequenceEqual(new[]{6,6,4,3})&&saved.tools.SequenceEqual(new[]{4,3,3,3})&&saved.rewards.Count==5,"All rewards share existing inventory");Check(home.State.wellworksStatus=="✓","Chapter complete badge");yield return Capture("Wellworks_Complete");
                page.Request("close");yield return Wait(()=>!home.RewardRevealPlaying);home.NavigationRequested.Invoke("daily");yield return null;Check(home.GetComponent<DailyGiftPage>().IsVisible&&!page.IsVisible,"Daily Gift route closes Wellworks");home.NavigationRequested.Invoke("wellworks");yield return null;Check(page.IsVisible&&!home.GetComponent<DailyGiftPage>().IsVisible,"Wellworks route closes Daily Gift");page.Request("close");
                client.Unavailable=true;page.Show();yield return Capture("Wellworks_Read_Error");client.Unavailable=false;page.Request("retry");Check(page.IsVisible&&host.Service.Read().rewards.Count==5,"Read recovery preserves receipts");page.Request("close");yield return Capture("Home_Complete");
            }
            Finish(null);
        }
        void Advance(int target){for(int level=host.Service.Read().completed+1;level<=target;level++){string id=Guid.NewGuid().ToString("N");host.Service.Reserve(id,level,"fixture-first-clear",new int[4],50,1);host.Service.CommitStart(id);host.Service.Win(id);}}
        IEnumerator Wait(Func<bool> ready){while(!ready())yield return null;}
        void Point(Component component){var rt=(RectTransform)component.transform;var c=RectTransformUtility.WorldToScreenPoint(null,rt.TransformPoint(rt.rect.center));report.x=Mathf.RoundToInt(c.x);report.y=Screen.height-Mathf.RoundToInt(c.y);}
        IEnumerator Capture(string name){yield return new WaitForSecondsRealtime(.25f);if(Application.isEditor)yield break;yield return new WaitForEndOfFrame();var pixels=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(Path.Combine(folder,name+".png"),pixels.EncodeToPNG());Destroy(pixels);report.frames.Add(name+".png");}
        void Check(bool ok,string name){report.checks++;if(!ok)throw new InvalidOperationException(name);report.passed.Add(name);}
        void State(string status){report.status=status;Save();}
        void Save(){File.WriteAllText(Path.Combine(folder,"Report.json"),JsonUtility.ToJson(report,true));}
        void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)Finish(message+"\n"+stack);}
        void Update(){if(report!=null&&!report.status.StartsWith("PASS")&&!report.status.StartsWith("FAIL")&&Time.realtimeSinceStartup>deadline)Finish("Timed out at "+report.status);}
        void Finish(string error){if(report.status.StartsWith("PASS")||report.status.StartsWith("FAIL"))return;Application.logMessageReceived-=Log;report.status=error==null?"PASS_NATIVE_WELLWORKS":"FAIL_NATIVE_WELLWORKS";if(error!=null)report.failures.Add(error);GameLocale.Select(locale);Save();}
        void OnDestroy(){Application.logMessageReceived-=Log;}
    }
}
#endif
