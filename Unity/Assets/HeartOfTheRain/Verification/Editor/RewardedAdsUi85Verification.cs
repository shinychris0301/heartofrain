#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Shop;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class RewardedAdsUi85Verification {
        const string Key="HOTR.AdUi85";const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REWARDED_ADS85_OUTPUT")??"../Verification/Evidence/ShopAds85");
        [Serializable] sealed class Report {public string status="RUNNING",utc,unity,scope="Actual Unity UGUI Shop renderer/design fonts. Disabled ordinary placement and explicitly constructed consent layout fixture in15 size/locale states. No configured publisher, SDK request, impression, reward grant, Android or live revenue claim.";public int checks,cases;public List<string> errors=new List<string>(),captures=new List<string>();}
        static Report report;static HomePage home;static ShopPage shop;static int index,phase;static double began,next;static string before;
        static RewardedAdsUi85Verification(){if(SessionState.GetBool(Key,false))Attach();}
        public static void Run(){SessionState.SetBool(Key,true);SessionState.SetInt(Key+".locale",GameLocale.Current);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/Shop/Scenes/M63_Shop_Review.unity");var fixtureHome=UnityEngine.Object.FindFirstObjectByType<HomePage>();var review=fixtureHome.gameObject.AddComponent<HeartOfTheRain.App.FirstStart.FirstStartPage>();review.reviewAlways=true;review.enabled=false;typeof(ProfileM71Verification).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);EditorApplication.isPlaying=true;}
        static void Attach(){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};began=EditorApplication.timeSinceStartup;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
        static void Check(bool condition,string code){report.checks++;if(!condition)throw new InvalidOperationException(code);}
        static T Field<T>(object value,string key)=>(T)value.GetType().GetField(key,Private).GetValue(value);
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static void Size(int size){View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),SessionState.GetInt("HOTR.M71.Verification.first",0)+size);}
        static void Case(){
            GameLocale.Select(index%5);shop.Show();home.State.reduceMotion=true;typeof(ShopPage).GetMethod("Reflow",Private).Invoke(shop,new object[]{1f});Canvas.ForceUpdateCanvases();
            var nodes=Field<Dictionary<string,RectTransform>>(shop,"nodes");var button=nodes["ad-action"].GetComponent<Button>();
            Check(!button.interactable&&nodes["ad-action-label"].GetComponent<Text>().text==AdText85.T("unavailable"),"No SDK/publisher does not pretend an available ad");
            Check(nodes["ad-card"].rect.height==162&&nodes["ad-action"].rect.height>=44,"Actual card/button retains touch bounds");
            var policy=nodes["ad-policy"].GetComponent<Text>();
            Check(policy.text==AdText85.T("policy")&&policy.text.Contains("3")&&!policy.text.Contains("UTC")&&!policy.text.Contains("10"),"Shop explains three free daily rewards without timezone/cooldown schedule");
            string cooldown=AdText85.T("cooldown");
            Check(!policy.text.Contains("?")&&!cooldown.Contains("?"),"New policy and cooldown translations contain no replacement question marks");
            string[] policyWords={"Free rewards","día","Récompenses","täglich","Бесплатная награда"},cooldownWords={"Next free reward","Próximo","récompense","Nächste","Следующая награда"};
            Check(policy.text.Contains(policyWords[index%5])&&cooldown.Contains(cooldownWords[index%5]),"Translated policy and cooldown retain actual accented/Cyrillic words");
            policy.font.RequestCharactersInTexture(policy.text,policy.fontSize,policy.fontStyle);
            Check(policy.preferredHeight<=policy.rectTransform.rect.height+.5f,"Local-day policy text fits actual card");
            if(index==4||index==9||index==14)Capture("Unavailable_Russian_"+Screen.width+"x"+Screen.height);
            var overlay=Field<RectTransform>(shop,"overlay");foreach(Transform child in overlay){child.gameObject.SetActive(false);UnityEngine.Object.Destroy(child.gameObject);}
            var consent=new HomeFrame{width=Screen.width,height=Screen.height};RewardedAdsLayout85.AddConsent(consent,Screen.width,Screen.height);
            typeof(ShopPage).GetMethod("Render",Private).Invoke(shop,new object[]{consent,overlay});Canvas.ForceUpdateCanvases();
            nodes=Field<Dictionary<string,RectTransform>>(shop,"nodes");
            foreach(var text in shop.GetComponentsInChildren<Text>().Where(t=>t.gameObject.activeInHierarchy&&t.name.StartsWith("ad-",StringComparison.Ordinal))){
                text.font.RequestCharactersInTexture(text.text,text.fontSize,text.fontStyle);
                Check(text.text.All(c=>char.IsWhiteSpace(c)||text.font.HasCharacter(c)),"Actual ad text font glyphs "+index+"/"+text.name);
                Check(text.preferredHeight<=text.rectTransform.rect.height+.5f,"Actual ad text height "+index+"/"+text.name);
                if(text.horizontalOverflow!=HorizontalWrapMode.Wrap)Check(text.preferredWidth<=text.rectTransform.rect.width+.5f,"Actual ad text width "+index+"/"+text.name);
                Check(text.fontSize>=9,"Ad labels remain legible "+index+"/"+text.name);
            }
            var panel=nodes["ad-consent-panel"];foreach(var id in new[]{"ad-consent-privacy","ad-consent-watch","ad-consent-cancel"}){
                var rt=nodes[id];Check(rt.rect.height>=44&&rt.anchoredPosition.x>=panel.anchoredPosition.x&&rt.anchoredPosition.x+rt.rect.width<=panel.anchoredPosition.x+panel.rect.width+.1f,"Consent button contained "+id);
                Check(rt.GetComponent<Button>().interactable,"Consent explicit action available "+id);
            }
            Check(nodes["ad-consent-body"].GetComponent<Text>().horizontalOverflow==HorizontalWrapMode.Wrap,"Privacy explanation wraps rather than clipping");
            if(index==4||index==9||index==14)Capture("ConsentLayoutFixture_Russian_"+Screen.width+"x"+Screen.height);
            Check(JsonUtility.ToJson(home.State)==before,"UI inspection leaves economy unchanged");report.cases++;
        }
        static void Capture(string name){string relative="Native/RewardedAdsUi85/"+name+".png",path=Path.Combine(Output,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));
            var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var go=new GameObject("Ad UI capture camera");go.transform.position=new Vector3(-10000,0,-10);var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var prior=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D pixels=null;
            try{camera.targetTexture=target;foreach(var canvas in canvases){canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());report.captures.Add(relative);}
            finally{for(int n=0;n<canvases.Length;n++){canvases[n].renderMode=RenderMode.ScreenSpaceOverlay;canvases[n].worldCamera=cameras[n];canvases[n].planeDistance=distances[n];}camera.targetTexture=null;RenderTexture.active=prior;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(go);Canvas.ForceUpdateCanvases();}
        }
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-began>150)throw new TimeoutException("Ad UI native timeout");if(report.errors.Count>0)throw new InvalidOperationException(report.errors[0]);
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
            if(phase==0){home=UnityEngine.Object.FindFirstObjectByType<HomePage>();shop=UnityEngine.Object.FindFirstObjectByType<ShopPage>();if(!home||!shop||!shop.IsVisible||Screen.width!=393||Screen.height!=852)return;home.State.reduceMotion=true;before=JsonUtility.ToJson(home.State);phase=1;}
            int size=index/5;int[] widths={393,320,768},heights={852,480,1024};if(Screen.width!=widths[size]||Screen.height!=heights[size])return;Case();index++;
            if(index==15){Check(report.cases==15&&report.captures.Count==6,"All UI cases/captures complete");Finish(0);return;}if(index%5==0)Size(index/5);next=EditorApplication.timeSinceStartup+.08;
        }catch(Exception error){report.errors.Add(error.ToString());Finish(1);}}
        static void Finish(int code){GameLocale.Select(SessionState.GetInt(Key+".locale",4));report.status=code==0?"PASS_NATIVE_REWARDED_ADS85_UI":"FAIL_NATIVE_REWARDED_ADS85_UI";Directory.CreateDirectory(Path.Combine(Output,"Native"));File.WriteAllText(Path.Combine(Output,"Native/RewardedAdsUi85.json"),JsonUtility.ToJson(report,true));EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SessionState.EraseBool(Key);
            try{View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),SessionState.GetInt("HOTR.M71.Verification.previous",0));var group=typeof(ProfileM71Verification).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);for(int n=4;n>=0;n--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.M71.Verification.first",0)+n});}catch{}EditorApplication.Exit(code);}
    }
}
#endif
