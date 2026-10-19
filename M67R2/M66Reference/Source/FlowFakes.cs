// Fake engine/UI host for production HomeLevelFlow orchestration, NOT Unity API validation.
using System;using System.Collections;using System.Collections.Generic;using System.Text.Json;
namespace UnityEngine
{
 public class Object {public bool destroyed;public static implicit operator bool(Object o)=>o!=null&&!o.destroyed;}
 public class DisallowMultipleComponent:Attribute{}
 public class GameObject:Object
 {
  public string name;public bool active=true;public readonly List<Object> components=new List<Object>();public GameObject(string n="host"){name=n;}
  public T AddComponent<T>()where T:Object,new(){var c=new T();if(c is MonoBehaviour b)b.gameObject=this;components.Add(c);return c;}
  public T GetComponent<T>()where T:class {foreach(var c in components)if(c is T t)return t;return null;}
  public void SetActive(bool b){active=b;}
 }
 public class MonoBehaviour:Object
 {
  public bool enabled=true;public GameObject gameObject=new GameObject();public List<IEnumerator> running=new List<IEnumerator>();
  public T GetComponent<T>()where T:class=>gameObject.GetComponent<T>();
  protected void StartCoroutine(IEnumerator e){if(e.MoveNext())running.Add(e);}
  public void Tick(){foreach(var e in running.ToArray())if(!e.MoveNext())running.Remove(e);}
  protected static void Destroy(Object o){if(o==null)return;o.destroyed=true;if(o is GameObject g)foreach(var c in g.components)c.destroyed=true;}
 }
 public static class Resources {public static T Load<T>(string name)where T:new()=>new T();}
 public static class Time {public static float realtimeSinceStartup;}
 public static class Debug {public static void LogError(string s,Object context){throw new Exception(s);}}
 public static class JsonUtility {public static T FromJson<T>(string s)=>JsonSerializer.Deserialize<T>(s,new JsonSerializerOptions{IncludeFields=true});}
 public class TextAsset {public string text;}
}
namespace HeartOfTheRain.App.Home
{
 public class LevelEvent {event Action<int> listeners;public void AddListener(Action<int> f){listeners+=f;}public void RemoveListener(Action<int> f){listeners-=f;}public void Invoke(int n){listeners?.Invoke(n);}}
 public class HomePage:UnityEngine.MonoBehaviour {public HomeState State=new HomeState();public LevelEvent PreLevelRequested=new LevelEvent();public bool Visible,Interactive;public void ApplyState(HomeState s){State=s;}public void SetPresentation(bool v,bool i){Visible=v;Interactive=i;}}
}
namespace HeartOfTheRain.M47
{
 public class BoardAssets {public UnityEngine.TextAsset[] levels;}
 public class GameplayUIAssets:UnityEngine.Object {public BoardAssets boards;}
 public class GameplayScreen:UnityEngine.MonoBehaviour
 {
  public GameplayUIAssets uiAssets;public int initialLevel;public bool showLevelIntro,ReviewInputBlocked,InitializationComplete,HasStartedWithPowers;public bool Busy,Paused;public uint seed;public void SetPause(bool value){Paused=value;}public int[] pendingStartingPowers;public string StartingPowerError;public HeartOfTheRain.M46.BoardModel Model;public int CurrentLevel=>initialLevel;public bool Ready=>InitializationComplete&&HasStartedWithPowers;
  public void Initialize(bool fail=false){Model=new HeartOfTheRain.M46.BoardModel(UnityEngine.JsonUtility.FromJson<HeartOfTheRain.M46.LevelData>(uiAssets.boards.levels[initialLevel-1].text),seed);gameObject.AddComponent<GameplayHUD>();gameObject.AddComponent<GameplayFeedback>();HasStartedWithPowers=!fail&&Model.TryPlaceStartingPowers(pendingStartingPowers,out StartingPowerError);if(fail)StartingPowerError="forced failure";InitializationComplete=true;}
 }
}
namespace HeartOfTheRain.M47 {
 public class GameplayHUD:UnityEngine.MonoBehaviour {public Func<bool,int,bool> ResultRequested;public Func<bool> ExternalResultVisible;public int closes;public void Close(bool resume){closes++;}}
 public class GameplayFeedback:UnityEngine.MonoBehaviour {public string last;public void Play(string key,float gain,string haptic=null){last=key;}}
}
namespace HeartOfTheRain.App.LevelComplete {
 public class LevelCompleteAssets:UnityEngine.Object {}
 public class LevelCompleteModal:UnityEngine.MonoBehaviour {public LevelCompleteAssets assets;public HeartOfTheRain.App.Home.HomePage home;public Action<string> Requested;public bool IsVisible;public LevelCompleteViewData data;public void Show(LevelCompleteViewData d){data=d;IsVisible=true;}public void Hide(){IsVisible=false;}}
}
namespace HeartOfTheRain.App.Journey {
 public class JourneyPage:UnityEngine.MonoBehaviour {public int refreshes;public bool visible;public List<string> requests=new List<string>();public void UseHomeProgress(){refreshes++;}public void Show(){visible=true;}public void Request(string action){requests.Add(action);}}
}

namespace HeartOfTheRain.App.PreLevel
{
 public class PreLevelAssets:UnityEngine.Object {public UnityEngine.Object home=new UnityEngine.Object();public HeartOfTheRain.M47.GameplayUIAssets gameplay;public int[] initialStock={5,5,3,2};public int rewardCoins=50,rewardStars=1;}
 public class PreLevelModal:UnityEngine.MonoBehaviour {public HeartOfTheRain.App.Home.HomePage home;public PreLevelAssets assets;public Action<string> Requested;public bool IsVisible;public PreLevelViewData Data;public void Show(PreLevelViewData d){Data=d;IsVisible=true;}public void Hide(){IsVisible=false;}}
}
namespace HeartOfTheRain.App.EndLevel {public class EndLevelAssets:UnityEngine.Object{}}
namespace HeartOfTheRain.App.Settings
{
 public class GameplaySettingsAssets:UnityEngine.Object{}
 public class GameplaySettingsController:UnityEngine.MonoBehaviour {public Action<HeartOfTheRain.App.EndLevel.EndLevelDecision> Exit;public void Configure(HeartOfTheRain.M47.GameplayScreen s,GameplaySettingsAssets a,HeartOfTheRain.App.Home.HomePage h,Action<HeartOfTheRain.App.EndLevel.EndLevelDecision> e,HeartOfTheRain.App.EndLevel.EndLevelAssets end){Exit=e;}}
}
