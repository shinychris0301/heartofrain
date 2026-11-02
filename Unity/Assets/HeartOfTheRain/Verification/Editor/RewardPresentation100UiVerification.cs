#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class RewardPresentation100UiVerification {
        const string Key="HOTR.Reward100.Ui";const BindingFlags Hidden=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,480),new Vector2Int(768,1024)};
        [Serializable] sealed class Geometry116 {
            public int index,locale,width,height,selectedGameViewIndex;
            public Rect safeArea,receiptRect,parentSafeViewportRect;
            public Vector2 anchoredPosition,anchorMin,anchorMax,pivot;
            public Vector3 localScale,parentLossyScale;
            public Vector3[] worldCorners;public Vector2[] screenCorners;
            public string canvasRenderMode,homeSourceSHA256;public float canvasScaleFactor,homeUIScale,unscaledDeltaTime;
        }
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity,error;
            public string scope="Actual Editor PlayMode imported Home/PreLevel sprites and UGUI,15locale-size states with a synthetic ten-dimension model grant. Editor foreground is explicitly simulated; lifecycle ordering/cancellation and read-only actual counters are checked. Not Android, real payment, HTTP or human visual acceptance.";
            public int checks,layouts,lifecycleCases;public bool syntheticEditorForeground=true;
            public List<string> captures=new List<string>();
            public List<Geometry116> geometry116=new List<Geometry116>();
        }
        static Report report;static HomePage home;static PlayerProfileHost host;static PreLevelAssets icons;static int phase,index,completions;static double began,next,at;static string digest;static RewardGrant grant;
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW100_OUT"));
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static object Group(){var a=typeof(Editor).Assembly;var t=a.GetType("UnityEditor.GameViewSizes");var instance=typeof(ScriptableSingleton<>).MakeGenericType(t).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return t.GetMethod("GetGroup").Invoke(instance,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":"Standalone")});}
        static RewardPresentation100UiVerification(){if(SessionState.GetBool(Key,false)){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};began=EditorApplication.timeSinceStartup;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        public static void Run(){
            if(!Application.isBatchMode)throw new InvalidOperationException("Explicit batch-only memory fixture");
            SessionState.SetBool(Key,true);SessionState.SetInt(Key+".locale",GameLocale.Current);
            var group=Group();int first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);
            SessionState.SetInt(Key+".first",first);SessionState.SetInt(Key+".previous",(int)View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).GetValue(View()));
            var a=typeof(Editor).Assembly;foreach(var size in Sizes){var value=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),size.x,size.y,"HOTR reward100"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{value});}
            SetSize(0);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;EditorApplication.isPlaying=true;
        }
        static void SetSize(int n){View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(View(),SessionState.GetInt(Key+".first",0)+n);View().Repaint();next=EditorApplication.timeSinceStartup+.3;}
        static void Need(bool value,string code){report.checks++;if(!value)throw new InvalidOperationException(code);}
        static void Log(string message,string stack,LogType type){if(type==LogType.Exception||type==LogType.Error||type==LogType.Assert)report.error=message+"\n"+stack;}
        static RectTransform Receipt=>home?(RectTransform)typeof(HomePage).GetField("receiptVisual",Hidden).GetValue(home):null;
        static string Digest()=>ProfileJson.Hash(JsonUtility.ToJson(host.Service.Read()));
        static void Focus(bool value)=>home.SendMessage("OnApplicationFocus",value,SendMessageOptions.RequireReceiver);
        static void Pause(bool value)=>home.SendMessage("OnApplicationPause",value,SendMessageOptions.RequireReceiver);
        static void StartReveal(){completions=0;Focus(true);Pause(false);Need(home.RewardPresentationForeground,"Explicit Editor foreground ready");home.PlayCommittedReward(grant,icons,()=>completions++);at=EditorApplication.timeSinceStartup;}
        static void InspectReceipt(){
            Canvas.ForceUpdateCanvases();var root=Receipt;Need(root&&root.gameObject.activeInHierarchy,"Actual shared receipt is visible");var labels=root.GetComponentsInChildren<Text>();Need(labels.Length==10,"All ten nonzero dimensions have quantity labels");
            var expected=new Dictionary<string,int>{{"RewardCoin",2000},{"RewardStar_R2",1},{"Rocket",1},{"Bomb",2},{"RainbowOrb_R2",3},{"GoldenSeeker_R2",4},{"boosterHammer",4},{"boosterAxe",3},{"boosterRam",2},{"boosterAtlas",1}};
            foreach(var pair in expected){var quantity=labels.Single(t=>t.name=="Receipt quantity "+pair.Key);Need(quantity.text=="+"+pair.Value,"Exact frozen quantity "+pair.Key);Need(quantity.preferredWidth<=quantity.rectTransform.rect.width+1.5f&&quantity.preferredHeight<=quantity.rectTransform.rect.height+1.5f,"Quantity text fits "+pair.Key);Need(!quantity.raycastTarget,"Receipt label does not block input");var image=root.Find("Receipt "+pair.Key).GetComponent<Image>();Need(image.sprite==icons.Find(pair.Key)&&image.preserveAspect&&!image.raycastTarget,"Actual approved sprite and input behavior "+pair.Key);}
            var panel=root.GetComponent<Image>();Need(panel.type==Image.Type.Sliced&&panel.pixelsPerUnitMultiplier==4,"Approved small sliced panel border density retained");
            var alpha=root.GetComponent<CanvasGroup>();Need(!alpha.blocksRaycasts&&!alpha.interactable,"Receipt overlay does not block Home");
            var corners=new Vector3[4];root.GetWorldCorners(corners);var points=corners.Select(corner=>RectTransformUtility.WorldToScreenPoint(null,corner)).ToArray();var owner=root.GetComponentInParent<Canvas>();string homeHash;using(var hash=System.Security.Cryptography.SHA256.Create())homeHash=BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes("Assets/HeartOfTheRain/App/Home/Runtime/HomePage.cs"))).Replace("-","").ToLowerInvariant();
            report.geometry116.Add(new Geometry116{index=index,locale=GameLocale.Current,width=Screen.width,height=Screen.height,selectedGameViewIndex=(int)View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).GetValue(View()),safeArea=Screen.safeArea,receiptRect=root.rect,parentSafeViewportRect=((RectTransform)root.parent).rect,anchoredPosition=root.anchoredPosition,anchorMin=root.anchorMin,anchorMax=root.anchorMax,pivot=root.pivot,localScale=root.localScale,parentLossyScale=root.parent.lossyScale,worldCorners=corners,screenCorners=points,canvasRenderMode=owner.renderMode.ToString(),canvasScaleFactor=owner.scaleFactor,homeUIScale=home.CurrentUIScale,unscaledDeltaTime=Time.unscaledDeltaTime,homeSourceSHA256=homeHash});
            if(points.Any(point=>point.x<Screen.safeArea.xMin-1||point.x>Screen.safeArea.xMax+1||point.y<Screen.safeArea.yMin-1||point.y>Screen.safeArea.yMax+1))Capture("Failure_"+index+"_"+GameLocale.Codes[GameLocale.Current]+"_"+Screen.width+"x"+Screen.height);
            foreach(var point in points)Need(point.x>=Screen.safeArea.xMin-1&&point.x<=Screen.safeArea.xMax+1&&point.y>=Screen.safeArea.yMin-1&&point.y<=Screen.safeArea.yMax+1,"Whole receipt remains within safe area");
            Need(Digest()==digest&&home.PresentationInteractable,"Rendering leaves already committed model unchanged and Home usable");
        }
        static void Capture(string name){
            string relative="Native/RewardUi100/"+name+".png",path=Path.Combine(Output,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));
            var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var node=new GameObject("Reward100 native capture");node.transform.position=new Vector3(-10000,0,-10);var camera=node.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;var prior=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D pixels=null;
            try{camera.targetTexture=target;foreach(var canvas in canvases){canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());report.captures.Add(relative);}
            finally{for(int n=0;n<canvases.Length;n++){canvases[n].renderMode=RenderMode.ScreenSpaceOverlay;canvases[n].worldCamera=cameras[n];canvases[n].planeDistance=distances[n];}camera.targetTexture=null;RenderTexture.active=prior;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(node);}
        }
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-began>240)throw new TimeoutException("RewardUiNativeDeadline");if(report.error!=null)throw new InvalidOperationException("Native logged error");if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
            if(phase==0){var first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(!first||!first.Initialized)return;home=first.home;host=home.GetComponent<PlayerProfileHost>();if(!host||!host.Ready)return;Need(first.reviewAlways&&host.IsTransient&&!host.ServerSession,"Only disposable memory profile selected");first.Request("skip");first.Request("skip");icons=home.GetComponent<PreLevelModal>().assets;Need(icons,"Actual imported PreLevel icon bank");phase=1;next=EditorApplication.timeSinceStartup+.3;return;}
            if(phase==1){int size=index/5;if(Screen.width!=Sizes[size].x||Screen.height!=Sizes[size].y)return;GameLocale.Select(index%5);grant=new RewardGrant{coins=2000,stars=1,starting=new[]{1,2,3,4},tools=new[]{4,3,2,1}};Need(host.Service.Grant("verification100/ui/"+index,"controlled-ui-ten-dimensions",grant),"Model grant precedes UI");Need(host.Refresh(),"Committed projection refresh succeeds");digest=Digest();phase=2;next=EditorApplication.timeSinceStartup+.2;return;}
            if(phase==2){StartReveal();phase=3;next=EditorApplication.timeSinceStartup+.35;return;}
            if(phase==3){InspectReceipt();if(index==4||index==14)Capture("AllDimensions_"+GameLocale.Codes[index%5]+"_"+Screen.width+"x"+Screen.height);phase=4;return;}
            if(phase==4){Need(Digest()==digest,"No financial mutation while UI ticks");if(completions==0)return;Need(completions==1&&!Receipt,"Auto completion occurs once and closes receipt");report.layouts++;index++;if(index==15){phase=5;return;}if(index%5==0)SetSize(index/5);phase=1;return;}
            if(phase==5){Focus(false);Pause(true);Pause(false);Need(!home.RewardPresentationForeground,"Pausefalse cannot override still-unfocused state");completions=0;home.PlayCommittedReward(grant,icons,()=>completions++);phase=6;next=EditorApplication.timeSinceStartup+.1;return;}
            if(phase==6){Need(!Receipt&&completions==0,"Unfocused Home cannot start or acknowledge receipt");report.lifecycleCases++;StartReveal();phase=7;next=EditorApplication.timeSinceStartup+.3;return;}
            if(phase==7){Need(Receipt,"Receipt began in explicit foreground");Focus(false);phase=8;next=EditorApplication.timeSinceStartup+.1;return;}
            if(phase==8){Need(!Receipt&&completions==0&&Digest()==digest,"Focus loss cancels without completing or granting");report.lifecycleCases++;StartReveal();phase=9;next=EditorApplication.timeSinceStartup+.3;return;}
            if(phase==9){home.SetPresentation(false,false);phase=10;next=EditorApplication.timeSinceStartup+.1;return;}
            if(phase==10){Need(!Receipt&&completions==0&&Digest()==digest,"Hiding Home cancels cosmetic completion only");report.lifecycleCases++;home.SetPresentation(true,true);home.State.reduceMotion=true;StartReveal();phase=11;return;}
            if(phase==11){if(completions==0)return;Need(completions==1&&!Receipt&&Digest()==digest,"Reduced motion completes once without model mutation");report.lifecycleCases++;Finish(true);}
        }catch(Exception error){if(report.error==null)report.error=error.GetType().Name+": "+error.Message;Finish(false);}}
        static void Finish(bool ok){
            EditorApplication.update-=Tick;Application.logMessageReceived-=Log;GameLocale.Select(SessionState.GetInt(Key+".locale",4));
            try{View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(View(),SessionState.GetInt(Key+".previous",0));var group=Group();int first=SessionState.GetInt(Key+".first",0);for(int i=0;i<Sizes.Length;i++)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{first});}catch(Exception error){report.error=report.error??error.GetType().Name;ok=false;}
            report.status=ok?"PASS_NATIVE_REWARD100_UI":"FAIL_NATIVE_REWARD100_UI";SessionState.EraseBool(Key);Directory.CreateDirectory(Path.Combine(Output,"Native"));File.WriteAllText(Path.Combine(Output,"Native/RewardUi100.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(ok?0:1);
        }
    }
}
#endif
