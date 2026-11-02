#if UNITY_EDITOR
using System;using System.IO;using System.Linq;using System.Collections.Generic;
using UnityEngine;using UnityEngine.UI;using UnityEditor;
using HeartOfTheRain.App.Profile;using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.Verification {
    public static class WellworksVerification {
        [Serializable] sealed class Report {public string utc,status,unity,scope="Native Unity transactions, file fault recovery, campaign first-clear integration, assets/layout/font checks. Android rendering and input are separate.";public int checks;public List<string> cases=new List<string>(),failures=new List<string>();}
        static Report report;static WellworksSchedule schedule;static string root;
        static void Check(bool ok,string message){report.checks++;if(!ok)throw new Exception(message);}
        static void Reject(Action action){try{action();}catch(InvalidOperationException){Check(true,"Invalid claim/config rejected");return;}throw new Exception("Expected rejection");}
        static void Case(string name,Action action){try{action();report.cases.Add(name);}catch(Exception e){report.failures.Add(name+": "+e);}}
        static ProfileService Memory(int completed=0){var p=PlayerProfile.New(new[]{5,5,3,2});p.completed=completed;p.currentLevel=Math.Min(50,completed+1);return new ProfileService(new MemoryProfileRepository(p));}
        static void Win(ProfileService s,int level){string id=Guid.NewGuid().ToString("N");s.Reserve(id,level,"authored-config-fixture",new int[4],50,1);s.CommitStart(id);s.Win(id);s.Win(id);}
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};root=Path.GetFullPath("../.verification-cache/Wellworks/Native-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
            schedule=JsonUtility.FromJson<WellworksSchedule>(Resources.Load<TextAsset>("HOTR_Wellworks/Schedule").text);
            Case("Approved config, defensive ownership and production gate",()=>{
                schedule.Validate();Check(schedule.milestones.Select(m=>m.level).SequenceEqual(new[]{10,20,30,40,50}),"Approved thresholds");Check(schedule.milestones[0].grant.coins==100&&schedule.milestones[1].grant.starting.SequenceEqual(new[]{1,1,0,0})&&schedule.milestones[2].grant.coins==150&&schedule.milestones[2].grant.tools[0]==1&&schedule.milestones[3].grant.starting[2]==1&&schedule.milestones[4].grant.coins==250&&schedule.milestones[4].grant.starting[3]==1,"Approved quantities");
                var s=Memory(50);var config=schedule.Copy();var w=new WellworksService(s,config,true);config.milestones[0].grant.coins=999;w.Schedule.milestones[0].grant.coins=888;Check(w.Claim(10).coins==100,"No mutable configuration alias");var off=new WellworksService(s,schedule,false);Check(!off.Enabled&&off.Badge(s.Read())=="Unavailable","Release adapter unavailable");Reject(()=>off.Claim(20));Reject(()=>new WellworksService(s,new WellworksSchedule(),true).Claim(10));
            });
            Case("Fifty first clears, replay protection, shared stock and permanent receipts",()=>{
                var s=Memory();var w=new WellworksService(s,schedule,true);Reject(()=>w.Claim(10));Reject(()=>w.Claim(9));Check(w.Badge(s.Read())=="0/10","Saved initial badge");
                for(int level=1;level<=50;level++){
                    Win(s,level);int n=s.Read().completed;Win(s,level);Check(s.Read().completed==n,"Replay cannot advance milestone "+level);
                    if(level%10==9)Reject(()=>w.Claim(level+1));
                    if(level%10==0){Check(w.Badge(s.Read())=="Ready","Eligible saved first clear "+level);Check(w.Claim(level)!=null,"First claim "+level);Check(w.Claim(level)==null,"Duplicate claim "+level);}
                }
                var p=s.Read();Check(p.completed==50&&p.coins==4250&&p.stars==50&&p.lives==5,"Only first-clear coins plus approved grants; stars/lives preserved");Check(p.starting.SequenceEqual(new[]{6,6,4,3})&&p.tools.SequenceEqual(new[]{4,3,3,3})&&p.rewards.Count==5,"Shared inventories and five receipts");Check(w.Badge(p)=="✓","Permanent completion badge");
            });
            Case("Any reached milestone can be claimed; config revisions do not reopen receipts",()=>{
                var s=Memory(50);var w=new WellworksService(s,schedule,true);w.Claim(50);w.Claim(10);var changed=schedule.Copy();changed.milestones[0].grant.coins=900;w=new WellworksService(s,changed,true);Check(w.Claim(10)==null&&s.Read().coins==1600,"Changed quantity cannot recredit saved milestone");Check(s.Read().rewards.Find(r=>r.key==WellworksService.Key(10)).grant.coins==100,"Original receipt retained");
            });
            Case("Atomic overflow and malformed configuration",()=>{
                var s=Memory(50);s.Change(p=>p.coins=int.MaxValue);var w=new WellworksService(s,schedule,true);try{w.Claim(10);throw new Exception("Expected overflow");}catch(OverflowException){}Check(s.Read().rewards.Count==0&&s.Read().coins==int.MaxValue,"No partial reward/receipt after overflow");
                foreach(int variant in Enumerable.Range(0,5)){var config=schedule.Copy();if(variant==0)config.milestones[1].level=10;if(variant==1)config.milestones[0].level=0;if(variant==2)config.milestones[4].level=51;if(variant==3)config.milestones[0].grant.stars=1;if(variant==4)config.milestones[0].grant.coins=-1;Reject(()=>config.Validate());}
            });
            Case("Pre/post commit failures and reopen retry preserve one durable grant",()=>{
                foreach(string phase in new[]{"TempFlushed","Committed"}){
                    string dir=Path.Combine(root,phase);Func<PlayerProfile> create=()=>{var p=PlayerProfile.New(new[]{5,5,3,2});p.completed=10;p.currentLevel=11;return p;};var repo=new FileProfileRepository(dir,create);var s=new ProfileService(repo);s.Read();repo.Checkpoint=p=>{if(p==phase)throw new IOException("Injected claim failure");};try{new WellworksService(s,schedule,true).Claim(10);throw new Exception("Expected injected failure");}catch(IOException){}
                    s=new ProfileService(new FileProfileRepository(dir,create));Check(s.Read().coins==(phase=="Committed"?1350:1250),"Atomic failure boundary "+phase);var w=new WellworksService(s,schedule,true);w.Claim(10);w.Claim(10);Check(s.Read().coins==1350&&s.Read().rewards.Count==1,"Recovered exactly one credit "+phase);
                }
            });
            Case("Existing profile schema, Daily Gift and campaign rewards remain compatible",()=>{
                var s=Memory(10);var w=new WellworksService(s,schedule,true);s.Grant("daily/control","daily",new RewardGrant{coins=50});w.Claim(10);Check(s.Read().coins==1400&&s.Read().schemaVersion==1&&s.Read().giftClaims==0,"Reward journals coexist without migration");Check(ProfileJson.Copy(s.Read()).rewards.Count==2,"Receipts survive native JsonUtility roundtrip");
            });
            Case("Native assets, text bounds and glyphs across all locales and states",()=>{
                var assets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");var go=new GameObject("Wellworks font verification",typeof(RectTransform),typeof(Text));var text=go.GetComponent<Text>();text.font=assets.home.boldFont;text.verticalOverflow=VerticalWrapMode.Truncate;text.supportRichText=false;int old=GameLocale.Current;
                try{for(int locale=0;locale<5;locale++){GameLocale.Select(locale);foreach(int width in new[]{320,393,768})foreach(int state in Enumerable.Range(0,8)){
                    var s=Memory(state==0?0:state==1?9:state==2?10:state==3?29:50);var w=new WellworksService(s,schedule,true);if(state==4)foreach(var m in schedule.milestones)w.Claim(m.level);var view=new WellworksView{schedule=state==6?new WellworksSchedule():schedule,player=s.Read(),enabled=state!=5,error=state==7,received=state==4};var f=WellworksLayout.Build(width,568,view);var panel=f.elements.First(e=>e.id=="panel");
                    // Every element under the panel (the R1 frame nests header/viewport/body/footer), measured as WellworksPage renders it; scroll-body rows may run past the panel height.
                    var design=WellworksDesignAssets.Load();var byId=f.elements.ToDictionary(e=>e.id);
                    foreach(var e in f.elements){if(e.id=="panel")continue;float ax=e.x,ay=e.y;bool inPanel=false,scrolls=e.id=="body";for(var p=e;!string.IsNullOrEmpty(p.parent)&&byId.TryGetValue(p.parent,out p);){if(p.id=="panel"){inPanel=true;break;}if(p.id=="body")scrolls=true;ax+=p.x;ay+=p.y;}if(!inPanel)continue;
                        bool overhang=e.id=="close"||e.parent=="close";// the round close button straddles the panel corner by design
                        Check(overhang||ax>=-.01f&&ax+e.width<=panel.width+.01f&&(scrolls||ay>=-.01f&&ay+e.height<=panel.height+.01f),"Contained element "+e.id);if(e.kind=="sprite")Check(design.Find(e.asset)!=null||assets.Find(e.asset)!=null,"Bound approved artwork "+e.asset);if(e.kind!="text")continue;
                        bool bold=e.id=="title"||e.id.Contains("label")||e.id.Contains("title")||e.id.Contains("quantity")||e.id=="heading"||e.id=="progress-count",claimLabel=e.id.StartsWith("claim-",StringComparison.Ordinal)&&e.id.EndsWith("-label",StringComparison.Ordinal);text.font=bold?design.shared.titleFont:design.shared.bodyFont;text.text=e.text;text.fontSize=e.fontSize;((RectTransform)text.transform).sizeDelta=new Vector2(e.width,e.height);
                        text.horizontalOverflow=claimLabel?HorizontalWrapMode.Overflow:HorizontalWrapMode.Wrap;if(claimLabel){while(text.fontSize>12&&text.preferredWidth>e.width+.01f)text.fontSize--;}else while(text.fontSize>9&&text.preferredHeight>e.height+.01f)text.fontSize--;bool paragraph=!claimLabel;text.font.RequestCharactersInTexture(text.text,text.fontSize);Check((paragraph||text.preferredWidth<=e.width+.5f)&&text.preferredHeight<=e.height+.5f,"Native text bounds "+locale+"/"+width+"/"+state+"/"+e.id);Check(e.text.All(c=>char.IsWhiteSpace(c)||text.font.HasCharacter(c)),"Glyphs "+e.id);}
                }}}finally{GameLocale.Select(old);UnityEngine.Object.DestroyImmediate(go);}
            });
            report.status=report.failures.Count==0?"PASS_NATIVE_WELLWORKS":"FAIL_NATIVE_WELLWORKS";string output=Path.GetFullPath("../Verification/Evidence/Wellworks");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native_Checks.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.failures.Count==0?0:1);
        }
    }
}
#endif
