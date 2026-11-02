#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.M46;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class TutorialGesture88Verification {
        const string Key="HOTR.TutorialGesture88";
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly string[] PreferenceKeys={FirstStartSession.StageKey,FirstStartSession.CompleteKey,GameLocale.PreferenceKey};
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_TUTORIAL88_OUTPUT")??"../Verification/Evidence/Display88/TutorialNative");
        sealed class Store:ISettingsStore {
            public readonly Dictionary<string,int> values=new Dictionary<string,int>();
            public int Read(string key,int fallback)=>values.TryGetValue(key,out int value)?value:fallback;
            public void Write(string key,int value){values[key]=value;}public void Flush(){}
        }
        [Serializable] sealed class Case {
            public string name,stage,error;public bool passed,accepted,animationCompleted;public int checks,turns,compiledSteps,timedFallMotions,finitePoses;public List<string> assertions=new List<string>();
        }
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity,activeSizeGroup,waitingFor,progressUtc;public int phase,staleOwnSizesRemoved;
            public string scope="Native pinned-Unity Editor Play Mode, actual M65 FirstStartPage/PracticeBoardView, UGUI ExecuteEvents pointer callbacks and live model/animation. Actual queued fall timings and finite start/mid/end poses are checked with a separate BoardPresentation, preserving the live presenter and authoritative board. All tutorial/campaign/settings storage is memory-only. Explicit pointer dispatch tests recognizer behavior including release without an intermediate Drag event; it is not physical touch, Android input-delivery, performance or visual certification.";
            public bool isolatedProfile,ordinaryPreferencesPreserved;public int checks,width,height;
            public List<Case> cases=new List<Case>();public List<string> errors=new List<string>();
        }
        static readonly string[] Names={"match_standard_drag","rocket_standard_drag","match_release_without_moved","rocket_release_without_moved","ten_pixel_drag_is_not_swap","below_cell_threshold_is_not_swap","wrong_owner_cannot_release","focus_cancels_then_valid_drag","disable_cancels_then_valid_drag","multitouch_drains_then_valid_drag","two_taps_still_match"};
        static Report report;static Case current;static FirstStartPage first;static FirstStartSession session;static PlayerProfileHost host;static string profileId;
        static int phase,index;static double began,next,actionAt,playBegan,lastProgress;static bool finished;
        static TutorialGesture88Verification(){if(SessionState.GetBool(Key,false))Attach();}
        public static void Run(){
            SessionState.SetBool(Key,true);SessionState.SetInt(Key+".locale",GameLocale.Current);
            for(int i=0;i<PreferenceKeys.Length;i++){SessionState.SetBool(Key+".pref."+i,PlayerPrefs.HasKey(PreferenceKeys[i]));SessionState.SetInt(Key+".value."+i,PlayerPrefs.GetInt(PreferenceKeys[i],int.MinValue));}
            EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");
            UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;SetSize();EditorApplication.isPlaying=true;
        }
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static string ActiveGroup=>EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":EditorUserBuildSettings.activeBuildTarget==BuildTarget.iOS?"iOS":"Standalone";
        static object Group(string requested=null){var a=typeof(Editor).Assembly;var sizes=a.GetType("UnityEditor.GameViewSizes");var singleton=typeof(ScriptableSingleton<>).MakeGenericType(sizes).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return sizes.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),requested??SessionState.GetString(Key+".group",ActiveGroup))});}
        static void CleanupStaleSizes(){
            var view=View();var selected=view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance);int previous=(int)selected.GetValue(view),removed=0;
            foreach(string key in new[]{"Standalone","Android","iOS"}){var group=Group(key);var names=(string[])group.GetType().GetMethod("GetDisplayTexts").Invoke(group,null);for(int i=names.Length-1;i>=0;i--){
                if(names[i]!="HOTR Tutorial88"&&!names[i].StartsWith("HOTR Tutorial88 (",StringComparison.Ordinal))continue;
                if(key==ActiveGroup){if(previous==i)previous=0;else if(previous>i)previous--;}
                group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{i});removed++;
            }}selected.SetValue(view,previous);SessionState.SetInt(Key+".staleRemoved",removed);
        }
        static void SetSize(){SessionState.SetString(Key+".group",ActiveGroup);CleanupStaleSizes();var group=Group();var view=View();var p=view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance);int count=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".previous",(int)p.GetValue(view));SessionState.SetInt(Key+".custom",count);var a=typeof(Editor).Assembly;var size=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),720,1600,"HOTR Tutorial88"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{size});p.SetValue(view,count);}
        static void Attach(){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,activeSizeGroup=SessionState.GetString(Key+".group",ActiveGroup),staleOwnSizesRemoved=SessionState.GetInt(Key+".staleRemoved",0),waitingFor="Enter Play Mode"};began=EditorApplication.timeSinceStartup;Save();SceneManager.sceneLoaded+=Loaded;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}
        static void Loaded(Scene scene,LoadSceneMode mode){
            var page=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(!page)return;page.reviewAlways=true;page.VerificationStore=new Store();
            host=page.home.GetComponent<PlayerProfileHost>();if(!host)host=page.home.gameObject.AddComponent<PlayerProfileHost>();var profile=PlayerProfile.New(new[]{5,5,3,2});profileId=profile.playerId;host.VerificationRepository=new MemoryProfileRepository(profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;
            foreach(var settings in UnityEngine.Object.FindObjectsByType<AppSettingsPage>(UnityEngine.FindObjectsSortMode.InstanceID))settings.VerificationStore=new Store();
        }
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(message+"\n"+stack);}
        static T Field<T>(object owner,string name)=>(T)owner.GetType().GetField(name,Private).GetValue(owner);
        static void Call(string name,params object[] args)=>typeof(FirstStartPage).GetMethod(name,Private).Invoke(first,args);
        static Dictionary<string,RectTransform> Nodes=>Field<Dictionary<string,RectTransform>>(first,"nodes");
        static void Check(bool ok,string message){report.checks++;if(current!=null){current.checks++;current.assertions.Add(message);}if(!ok)throw new InvalidOperationException(message);}
        static Vector2 Centre(Cell cell){var r=Nodes["cell:"+cell.x+","+cell.y];return RectTransformUtility.WorldToScreenPoint(null,r.TransformPoint(r.rect.center));}
        static PointerEventData Data(int id,Vector2 from,Cell source){var go=Nodes["cell:"+source.x+","+source.y].gameObject;return new PointerEventData(EventSystem.current){pointerId=id,button=PointerEventData.InputButton.Left,position=from,pressPosition=from,pointerPress=go,pointerDrag=go,pointerPressRaycast=new RaycastResult{gameObject=go,module=Field<Canvas>(first,"canvas").GetComponent<GraphicRaycaster>()},eligibleForClick=true};}
        static void Down(PointerEventData e){ExecuteEvents.Execute(e.pointerPress,e,ExecuteEvents.pointerDownHandler);ExecuteEvents.Execute(e.pointerDrag,e,ExecuteEvents.initializePotentialDrag);}
        static void Move(PointerEventData e,Vector2 to){e.position=to;ExecuteEvents.Execute(e.pointerDrag,e,ExecuteEvents.beginDragHandler);e.dragging=true;ExecuteEvents.Execute(e.pointerDrag,e,ExecuteEvents.dragHandler);}
        static void Up(PointerEventData e,Vector2 to){e.position=to;var press=e.pointerPress;ExecuteEvents.Execute(press,e,ExecuteEvents.pointerUpHandler);if(e.dragging)ExecuteEvents.Execute(e.pointerDrag,e,ExecuteEvents.endDragHandler);}
        static void Standard(int id=101){var hint=session.Hint;var from=Centre(hint[0]);var to=Centre(hint[1]);var e=Data(id,from,hint[0]);Down(e);Move(e,Vector2.Lerp(from,to,.7f));Up(e,to);}
        static void ResetLesson(string name){
            int stage=name.StartsWith("rocket",StringComparison.Ordinal)?3:2;var store=new Store();store.values[FirstStartSession.StageKey]=stage;var lessons=first.assets.lessons.Select(a=>JsonUtility.FromJson<LevelData>(a.text)).ToArray();session=new FirstStartSession(store,lessons);
            typeof(FirstStartPage).GetField("session",Private).SetValue(first,session);Call("OnApplicationFocus",true);Call("ShowStage");Canvas.ForceUpdateCanvases();current=new Case{name=name,stage=session.Stage.ToString()};report.cases.Add(current);
        }
        static void ExecuteCase(){
            var hint=session.Hint;var from=Centre(hint[0]);var to=Centre(hint[1]);float unit=Vector2.Distance(from,to);var e=Data(101,from,hint[0]);
            Check(unit>40,"Actual highlighted cells have distinct positive screen centres");
            switch(current.name){
                case "match_standard_drag":case "rocket_standard_drag":Standard();break;
                case "match_release_without_moved":case "rocket_release_without_moved":
                    Down(e);Check(!Field<bool>(first,"dragged"),"Began starts without a cached Drag event");Up(e,to);break;
                case "ten_pixel_drag_is_not_swap":
                    Down(e);Move(e,from+Vector2.down*10);Up(e,from+Vector2.down*10);Check(session.Board.Turn==0&&!session.Busy,"Ten-pixel movement does not swap");Standard(102);break;
                case "below_cell_threshold_is_not_swap":
                    Down(e);Move(e,Vector2.Lerp(from,to,.34f));Up(e,Vector2.Lerp(from,to,.34f));Check(session.Board.Turn==0&&!session.Busy,"Movement below .35 cell does not swap");Standard(102);break;
                case "wrong_owner_cannot_release":
                    Down(e);Move(e,to);var wrong=Data(102,from,hint[0]);Up(wrong,to);Check(session.Board.Turn==0&&Field<int>(first,"dragOwner")==101,"Other pointer cannot release the owning gesture");Up(e,to);break;
                case "focus_cancels_then_valid_drag":
                    Down(e);Move(e,to);Call("OnApplicationFocus",false);Up(e,to);Check(session.Board.Turn==0&&Field<int>(first,"dragOwner")==int.MinValue,"Lost focus cancels pending swipe without a turn");Call("OnApplicationFocus",true);Standard(102);break;
                case "disable_cancels_then_valid_drag":
                    Down(e);Move(e,to);first.enabled=false;Up(e,to);Check(session.Board.Turn==0&&Field<int>(first,"dragOwner")==int.MinValue,"Disabling cancels pending swipe without a turn");first.enabled=true;Call("OnApplicationFocus",true);Standard(102);break;
                case "multitouch_drains_then_valid_drag":
                    Down(e);var second=Data(102,to,hint[1]);Down(second);Up(e,to);Check(session.Board.Turn==0&&Field<bool>(first,"multiTouch"),"First release cannot commit or clear a remaining second contact");Up(second,to);Check(!Field<bool>(first,"multiTouch")&&Field<HashSet<int>>(first,"pointers").Count==0,"All contacts drain before a new gesture");Standard(103);break;
                case "two_taps_still_match":
                    Down(e);Up(e,from);ExecuteEvents.Execute(e.pointerPress,e,ExecuteEvents.pointerClickHandler);Check(session.Board.Turn==0&&Field<Cell>(first,"selected")!=null,"First actual UGUI click selects without a turn");
                    var tap=Data(102,to,hint[1]);Down(tap);Up(tap,to);ExecuteEvents.Execute(tap.pointerPress,tap,ExecuteEvents.pointerClickHandler);break;
                default:throw new InvalidOperationException("Unknown tutorial fixture");
            }
            current.turns=session.Board.Turn;current.accepted=current.turns==1&&session.Busy;Check(current.accepted,"Exactly one live tutorial turn is accepted");ValidateCompiledQueue();actionAt=EditorApplication.timeSinceStartup;
        }
        static bool Finite(float value)=>!float.IsNaN(value)&&!float.IsInfinity(value);
        static void ValidateCompiledQueue(){
            var practice=Field<PracticeBoardView>(first,"practice");var queue=Field<List<BoardStep>>(practice,"queue");
            Check(queue!=null&&queue.Count>0,"Live PracticeBoardView owns a non-empty prepared playback queue");current.compiledSteps=queue.Count;
            var live=Field<BoardPresentation>(practice,"presentation");var sampled=new BoardPresentation{columns=live.columns,rows=live.rows,left=live.left,right=live.right,bottom=live.bottom};
            // An independent sampler exercises the exact queued steps. Sampling
            // must never register future births/history in the live presenter.
            foreach(var asset in first.assets.Gameplay.boards.debrisProfiles){var profile=JsonUtility.FromJson<DebrisProfile>(asset.metadata.text);foreach(var piece in profile.pieces){if(piece.scaleMultiplier<=0)piece.scaleMultiplier=1;if(piece.spinMultiplier<=0)piece.spinMultiplier=1;}sampled.profiles.Add(asset.family,profile);}
            string modelBefore=JsonUtility.ToJson(session.Board.Checkpoint());float clock=0;
            for(int stepIndex=0;stepIndex<queue.Count;stepIndex++){
                var step=queue[stepIndex];Check(Finite(step.duration)&&step.duration>=0,"Queued step has a finite non-negative duration: "+stepIndex+"/"+step.kind);
                if(step.kind=="gravity"||step.kind=="powerFall")foreach(var motion in step.motion){
                    Check(Finite(motion.delay)&&motion.delay>=0&&Finite(motion.seconds)&&motion.seconds>0,"Actual queued fall motion has positive finite timing: "+stepIndex+"/"+motion.id);current.timedFallMotions++;
                    if(motion.path!=null)foreach(var leg in motion.path)Check(Finite(leg.delay)&&leg.delay>=0&&Finite(leg.seconds)&&leg.seconds>0,"Actual queued fall leg has positive finite timing: "+stepIndex+"/"+motion.id);
                }
                sampled.Add(step,clock);var ages=step.duration>0?new[]{0f,step.duration*.5f,step.duration}:new[]{0f};
                foreach(float age in ages){
                    sampled.PruneHistory(clock+age);var draws=sampled.SampleLive(step,step.before,clock+age,clock);
                    var invalid=draws.FirstOrDefault(d=>!Finite(d.x)||!Finite(d.y)||!Finite(d.sx)||!Finite(d.sy)||!Finite(d.angle)||!Finite(d.alpha)||!Finite(d.age));
                    Check(invalid==null,"Queued pose is finite at start/mid/end: "+stepIndex+"/"+step.kind+"/"+age+(invalid==null?"":"; invalid="+invalid.bank+"/"+invalid.key));current.finitePoses++;
                }
                clock+=step.duration;
            }
            Check(current.timedFallMotions>0,"Accepted tutorial match includes positively timed refill motion");
            Check(JsonUtility.ToJson(session.Board.Checkpoint())==modelBefore,"Independent queued-pose sampling preserves the authoritative board checkpoint");
        }
        static void Tick(){
            if(finished)return;
            try{
                if(EditorApplication.timeSinceStartup-began>600)throw new TimeoutException("Tutorial gesture88 suite timeout");if(report.errors.Count>0)throw new InvalidOperationException(report.errors[0]);
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
                if(playBegan==0)playBegan=EditorApplication.timeSinceStartup;report.phase=phase;report.width=Screen.width;report.height=Screen.height;
                if(phase==0){first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();report.waitingFor=!first?"M65 FirstStartPage":!first.Initialized?"FirstStart initialization":!first.IsVisible?"Visible isolated tutorial":Screen.width!=720||Screen.height!=1600?"Exact720x1600 GameView":"Memory-profile isolation";
                    if(EditorApplication.timeSinceStartup-lastProgress>=2)Save();
                    if(EditorApplication.timeSinceStartup-playBegan>45)throw new TimeoutException("Phase0 readiness exceeded45seconds: "+report.waitingFor+"; observed="+Screen.width+"x"+Screen.height+"; group="+report.activeSizeGroup);
                    if(!first||!first.Initialized||!first.IsVisible||Screen.width!=720||Screen.height!=1600)return;host=first.home.GetComponent<PlayerProfileHost>();report.isolatedProfile=host&&host.Ready&&!host.ServerSession&&host.VerificationRepository is MemoryProfileRepository&&host.Service.Read().playerId==profileId;Check(report.isolatedProfile,"Campaign explicitly uses own memory profile with no backend session");report.waitingFor="Recognizer cases";GameLocale.Select(4);phase=1;}
                if(EditorApplication.timeSinceStartup-lastProgress>=2)Save();
                if(phase==1){if(index>=Names.Length){Finish();return;}ResetLesson(Names[index]);phase=2;next=EditorApplication.timeSinceStartup+.25;return;}
                if(phase==2){try{ExecuteCase();phase=3;}catch(Exception error){current.error=error.ToString();current.passed=false;index++;phase=1;}next=EditorApplication.timeSinceStartup+.1;return;}
                if(phase==3){if(session.Busy){if(EditorApplication.timeSinceStartup-actionAt>40){current.error="Live practice animation did not settle within40seconds";index++;phase=1;}return;}try{Check(session.Solved,"Live PracticeBoardView finishes animation and solves intended lesson");Check(Field<int>(first,"dragOwner")==int.MinValue&&Field<HashSet<int>>(first,"pointers").Count==0,"Accepted gesture leaves no owning pointer");current.animationCompleted=true;current.passed=true;}catch(Exception error){current.error=error.ToString();current.passed=false;}index++;phase=1;}
            }catch(Exception error){report.errors.Add(error.ToString());Finish();}
        }
        static void Finish(){
            if(finished)return;finished=true;report.ordinaryPreferencesPreserved=Enumerable.Range(0,PreferenceKeys.Length).All(i=>PlayerPrefs.HasKey(PreferenceKeys[i])==SessionState.GetBool(Key+".pref."+i,false)&&PlayerPrefs.GetInt(PreferenceKeys[i],int.MinValue)==SessionState.GetInt(Key+".value."+i,int.MinValue));
            if(!report.ordinaryPreferencesPreserved)report.errors.Add("Ordinary tutorial/locale preferences changed");GameLocale.Select(SessionState.GetInt(Key+".locale",4));
            bool ok=report.errors.Count==0&&report.cases.Count==Names.Length&&report.cases.All(c=>c.passed)&&report.ordinaryPreferencesPreserved;report.status=ok?"PASS_NATIVE_TUTORIAL_GESTURE88":"FAIL_NATIVE_TUTORIAL_GESTURE88";report.waitingFor="";Save();
            EditorApplication.update-=Tick;SceneManager.sceneLoaded-=Loaded;Application.logMessageReceived-=Log;SessionState.EraseBool(Key);
            try{var view=View();view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(view,SessionState.GetInt(Key+".previous",0));var group=Group();group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt(Key+".custom",0)});}catch(Exception error){Debug.LogWarning(error.Message);}
            EditorApplication.Exit(ok?0:1);
        }
        static void Save(){report.progressUtc=DateTime.UtcNow.ToString("o");report.phase=phase;Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Report.json"),JsonUtility.ToJson(report,true));lastProgress=EditorApplication.timeSinceStartup;}
    }
}
#endif
