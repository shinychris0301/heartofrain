#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Settings;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;

namespace HeartOfTheRain.Verification {
    // Explicit development-only phone diagnostic. Real touches are required;
    // no direct cell requests, synthetic event dispatch or ordinary save writes.
    public sealed class Tutorial88DeviceProbe : MonoBehaviour {
        public const string Marker="HOTR_RunTutorial88";
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static bool pending;
        sealed class Settings : ISettingsStore {
            readonly Dictionary<string,int> values=new Dictionary<string,int>();
            public int Read(string key,int fallback)=>values.TryGetValue(key,out int value)?value:fallback;
            public void Write(string key,int value){values[key]=value;}public void Flush(){}
        }
        [Serializable] public sealed class Point {public int x,y;public string cell;}
        [Serializable] public sealed class Sample {
            public int frame,fingerId,owner,clickOwner,pointerCount;public string observation,phase,stage,selected,raycast;
            public float x,y,localX,localY,pressX,pressY;public bool dragged,multiTouch,busy,solved;
        }
        [Serializable] public sealed class Lesson {
            public string stage;public bool solved;public int turns;public Point[] hint;
        }
        [Serializable] public sealed class Report {
            public string status="STARTING",utc,unity,platform,error,stage;
            public string scope="Development opt-in memory-only campaign/tutorial/settings, actual native input required. Hint and Next coordinates are Android top-left pixels derived from live transforms. A BaseInput pass-through returns untouched native Input.GetTouch and records before EventSystem dispatch; LateUpdate records after dispatch. Touch observations do not assert a swipe succeeded; live lesson completion does. No synthetic touches, performance certification or ordinary onboarding mutation.";
            public bool isolatedProfile;public int width,height;public List<Lesson> lessons=new List<Lesson>();public List<Sample> samples=new List<Sample>();
            public bool busy,solved,canContinue;public Point next;public Sample gesture;
        }
        FirstStartPage first;FirstStartSession session;Report report;string playerId,lastStage,lastState;double deadline,lastSaved;int sampleFrame=-1;bool finished,dirty;
        StandaloneInputModule inputModule;BaseInput previousInput;Tutorial88NativeInput observationInput;
        static string Output=>Path.Combine(Application.persistentDataPath,"Tutorial88","Report.json");
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)] static void Boot(){
            SceneManager.sceneLoaded-=Attach;pending=false;var path=Path.Combine(Application.persistentDataPath,Marker);if(!File.Exists(path))return;
            if(new FileInfo(path).Length>128)return;string mode=File.ReadAllText(path).Trim();File.Delete(path);if(mode!="touch")return;
            pending=true;SceneManager.sceneLoaded+=Attach;
        }
        static void Attach(Scene scene,LoadSceneMode mode){
            if(!pending)return;var page=FindFirstObjectByType<FirstStartPage>();if(!page)return;pending=false;SceneManager.sceneLoaded-=Attach;page.reviewAlways=true;
            var host=page.home.GetComponent<PlayerProfileHost>();if(!host)host=page.home.gameObject.AddComponent<PlayerProfileHost>();
            var profile=PlayerProfile.New(new[]{5,5,3,2});host.VerificationRepository=new MemoryProfileRepository(profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;
            foreach(var settings in FindObjectsByType<AppSettingsPage>(UnityEngine.FindObjectsSortMode.InstanceID))settings.VerificationStore=new Settings();
            var node=new GameObject("Opt-in tutorial gesture88 diagnostic");DontDestroyOnLoad(node);var probe=node.AddComponent<Tutorial88DeviceProbe>();probe.playerId=profile.playerId;
        }
        void Start(){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,platform=Application.platform.ToString()};deadline=Time.realtimeSinceStartupAsDouble+600;Application.logMessageReceived+=Log;StartCoroutine(Ready());}
        IEnumerator Ready(){
            while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized||FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;
            var host=first.home.GetComponent<PlayerProfileHost>();report.isolatedProfile=host&&host.Ready&&!host.ServerSession&&host.VerificationRepository is MemoryProfileRepository&&host.Service.Read().playerId==playerId;
            if(!report.isolatedProfile){Finish("Memory-profile isolation failed");yield break;}
            first.Request("skip");yield return null;session=Field<FirstStartSession>(first,"session");if(first.Stage!=FirstStartStage.Match){Finish("Isolated tutorial did not reach Match");yield break;}
            inputModule=EventSystem.current?EventSystem.current.currentInputModule as StandaloneInputModule:null;
            if(!inputModule||inputModule.inputOverride){Finish("Expected ordinary StandaloneInputModule with no input override");yield break;}
            previousInput=inputModule.inputOverride;observationInput=inputModule.gameObject.AddComponent<Tutorial88NativeInput>();observationInput.owner=this;inputModule.inputOverride=observationInput;ObserveStage();
        }
        static T Field<T>(object value,string name)=>(T)value.GetType().GetField(name,Private).GetValue(value);
        Point NodePoint(string key){
            var nodes=Field<Dictionary<string,RectTransform>>(first,"nodes");var node=nodes[key];Vector2 p=RectTransformUtility.WorldToScreenPoint(null,node.TransformPoint(node.rect.center));
            return new Point{x=Mathf.RoundToInt(p.x),y=Screen.height-Mathf.RoundToInt(p.y),cell=key};
        }
        Point HintPoint(HeartOfTheRain.M46.Cell cell)=>NodePoint("cell:"+cell.x+","+cell.y);
        void ObserveStage(){
            Canvas.ForceUpdateCanvases();lastStage=first.Stage.ToString();report.width=Screen.width;report.height=Screen.height;
            if(session.Practice)report.lessons.Add(new Lesson{stage=lastStage,hint=session.Hint.Select(HintPoint).ToArray()});report.stage=lastStage;report.next=NodePoint("next");report.status="READY_FOR_TOUCH_"+lastStage.ToUpperInvariant();dirty=true;
        }
        void LateUpdate(){
            if(finished||report==null)return;
            try{
                if(Time.realtimeSinceStartupAsDouble>deadline){Finish("Timed out waiting for actual tutorial touches");return;}
                if(session==null)return;
                if(!first||!first.IsVisible){Finish(report.lessons.Count==3&&report.lessons.All(l=>l.solved)?null:"Tutorial disappeared before all three actual-touch lessons completed");return;}
                if(first.Stage.ToString()!=lastStage)ObserveStage();
                if(first.Stage==FirstStartStage.Ready){report.busy=session.Busy;report.solved=session.Solved;report.canContinue=session.CanContinue;report.gesture=Gesture();Finish(null);return;}
                if(report.samples.Count<4096&&sampleFrame!=Time.frameCount){
                    sampleFrame=Time.frameCount;for(int i=0;i<Input.touchCount;i++)Record(Input.GetTouch(i),"after-dispatch");
                }
                if(session.Solved){
                    var lesson=report.lessons.Last();lesson.solved=true;lesson.turns=session.Board.Turn;report.status="SOLVED_"+lastStage.ToUpperInvariant();
                }
                report.busy=session.Busy;report.solved=session.Solved;report.canContinue=session.CanContinue;report.gesture=Gesture();
                string state=report.stage+"|"+report.busy+"|"+report.solved+"|"+report.canContinue+"|"+report.gesture.owner+"|"+report.gesture.dragged+"|"+report.gesture.pointerCount;
                if(state!=lastState){lastState=state;dirty=true;}
                if(dirty&&Time.realtimeSinceStartupAsDouble-lastSaved>=.5)Save();
            }catch(Exception error){Finish(error.ToString());}
        }
        Sample Gesture(){var selected=Field<HeartOfTheRain.M46.Cell>(first,"selected");var press=Field<Vector2>(first,"press");return new Sample{frame=Time.frameCount,stage=lastStage,pressX=press.x,pressY=press.y,
            owner=Field<int>(first,"dragOwner"),clickOwner=Field<int>(first,"allowedClick"),pointerCount=Field<HashSet<int>>(first,"pointers").Count,dragged=Field<bool>(first,"dragged"),multiTouch=Field<bool>(first,"multiTouch"),busy=session.Busy,solved=session.Solved,selected=selected==null?"":selected.x+","+selected.y};}
        public void Record(Touch touch,string observation){
            if(finished||session==null||report.samples.Count>=4096)return;
            var nodes=Field<Dictionary<string,RectTransform>>(first,"nodes");RectTransform board;if(!nodes.TryGetValue("practice-board",out board))return;Vector2 local;RectTransformUtility.ScreenPointToLocalPointInRectangle(board,touch.position,null,out local);
            string hit="";if(EventSystem.current){var data=new PointerEventData(EventSystem.current){position=touch.position,pointerId=touch.fingerId};var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(data,hits);hit=hits.Count>0?hits[0].gameObject.name:"";}
            var sample=Gesture();sample.fingerId=touch.fingerId;sample.observation=observation;sample.phase=touch.phase.ToString();sample.x=touch.position.x;sample.y=touch.position.y;sample.localX=local.x;sample.localY=local.y;sample.raycast=hit;
            report.samples.Add(sample);dirty=true;
        }
        void Log(string message,string trace,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)Finish(message+"\n"+trace);}
        void Finish(string error){if(finished)return;finished=true;report.error=error;report.status=error==null&&report.lessons.Count==3&&report.lessons.All(l=>l.solved)?"PASS_NATIVE_TUTORIAL_TOUCH88":"FAIL_NATIVE_TUTORIAL_TOUCH88";Save();Application.logMessageReceived-=Log;RestoreInput();}
        void Save(){Directory.CreateDirectory(Path.GetDirectoryName(Output));File.WriteAllText(Output,JsonUtility.ToJson(report,true));lastSaved=Time.realtimeSinceStartupAsDouble;dirty=false;}
        void RestoreInput(){if(inputModule&&inputModule.inputOverride==observationInput)inputModule.inputOverride=previousInput;if(observationInput)Destroy(observationInput);observationInput=null;}
        void OnDestroy(){Application.logMessageReceived-=Log;RestoreInput();}
    }
    public sealed class Tutorial88NativeInput : BaseInput {
        public Tutorial88DeviceProbe owner;
        public override Touch GetTouch(int index){var touch=base.GetTouch(index);if(owner)owner.Record(touch,"before-dispatch");return touch;}
    }
}
#endif
