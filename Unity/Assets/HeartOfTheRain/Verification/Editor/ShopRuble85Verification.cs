#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Shop;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    // Explicit native harness only. The ordinary app never starts this suite.
    [InitializeOnLoad] public static class ShopRuble85Verification {
        const string Key="HOTR.ShopRuble85";
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly int[] Quantities={1000,5000,10000,25000,50000,100000};
        static readonly int[] Rubles={99,299,499,899,1599,2999};
        static readonly string[] BundleIds={"wellkeeper","rainy-day","rainlight","village","festival","keepers"};
        static readonly int[] BundleCoins={2000,3500,6000,5000,10000,25000},BundleRubles={99,199,299,399,599,999};
        static readonly int[] BundleToolsEach={1,2,3,2,4,8},BundleStartingEach={1,2,3,3,6,12};
        static readonly int[] Locales={4,0,1,2,3};
        static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,480),new Vector2Int(768,1024)};
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_SHOP_RUBLE85_OUTPUT")??"../Verification/Evidence/ShopRuble85");
        [Serializable] sealed class ProposalProduct {public string shopOfferId;public int coins;public long proposedPriceMinor;}
        [Serializable] sealed class Proposal {public string status,currency;public bool checkoutEnabled;public ProposalProduct[] products;}
        [Serializable] sealed class PreviewProduct {public string id,priceLabel;public int coins;}
        [Serializable] sealed class Preview {public bool isPreview,checkoutEnabled;public string source,currency;public PreviewProduct[] products;}
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity;
            public string scope="Native Unity Play Mode using the actual imported Shop catalog, ShopPage button listeners, ShopLayout, NoMovesPage and design fonts. Fifteen phone/tablet/locale states, all twelve offer detail views per state, camera-rendered UGUI. RUB values are launch-proposal preview prices, not Console/GetProducts quotations. No checkout, SDK activation, grant, Android, physical touch or production-payment claim.";
            public int checks,coinMappings,bundlePriceMappings,layoutCases,detailCases,noMovesPacks;
            public bool checkoutUnavailable,previewOnly,noMovesCheckoutDisabled,previewHomeUnchanged,languagePreferenceUnchanged;
            public List<string> passed=new List<string>(),errors=new List<string>(),captures=new List<string>();
        }
        static Report report;static HomePage home;static ShopPage shop;static NoMovesPage noMoves;
        static int index,phase;static double began,next;static string homeBefore;
        static ShopRuble85Verification(){if(SessionState.GetBool(Key,false))Attach();}
        public static void Run(){
            if(!Application.isBatchMode)throw new InvalidOperationException("Use isolated batch native verification.");
            SessionState.SetBool(Key,true);SessionState.SetInt(Key+".locale",GameLocale.Current);
            SessionState.SetBool(Key+".preferencePresent",PlayerPrefs.HasKey(GameLocale.PreferenceKey));SessionState.SetInt(Key+".preference",PlayerPrefs.GetInt(GameLocale.PreferenceKey,0));
            EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/Shop/Scenes/M63_Shop_Review.unity");
            var fixtureHome=UnityEngine.Object.FindFirstObjectByType<HomePage>();var review=fixtureHome.gameObject.AddComponent<HeartOfTheRain.App.FirstStart.FirstStartPage>();review.reviewAlways=true;review.enabled=false;
            typeof(ProfileM71Verification).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
            EditorApplication.isPlaying=true;
        }
        static void Attach(){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};began=EditorApplication.timeSinceStartup;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
        static void Check(bool condition,string message){report.checks++;if(!condition)throw new InvalidOperationException(message);report.passed.Add(message);}
        static T Field<T>(object target,string name)=>(T)target.GetType().GetField(name,Private).GetValue(target);
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static void Size(int value){View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),SessionState.GetInt("HOTR.M71.Verification.first",0)+value);}
        static bool NoUsd(string text)=>!text.Contains("$")&&text.IndexOf("USD",StringComparison.OrdinalIgnoreCase)<0;
        static void Contracts(){
            var hosts=UnityEngine.Object.FindObjectsByType<PlayerProfileHost>(UnityEngine.FindObjectsSortMode.InstanceID);
            Check(hosts.All(h=>h.IsTransient&&!h.ServerSession),"Shop review uses only the existing transient memory profile host, never a durable or server profile");
            var actual=AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/HeartOfTheRain/App/Shop/Data/ShopCatalog.json");
            Check(shop.assets&&shop.assets.catalog==actual,"Live Shop and imported catalog share the actual bound asset");
            var catalog=JsonUtility.FromJson<ShopCatalog>(actual.text);var proposal=JsonUtility.FromJson<Proposal>(File.ReadAllText(Path.GetFullPath("../Release/RuStore/pricing.proposal.json")));
            var preview=JsonUtility.FromJson<Preview>(AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/HeartOfTheRain/App/NoMovesDesign/Data/Shop_Preview_Products.json").text);
            Check(proposal.currency=="RUB"&&!proposal.checkoutEnabled&&proposal.status=="CONFIGURABLE_LAUNCH_PROPOSAL_NOT_CONSOLE_PRICES","External RUB proposal stays explicitly disabled/non-Console");
            Check(catalog.isPreview&&shop.ReviewSession.IsPreview&&preview.isPreview&&!preview.checkoutEnabled&&preview.currency=="RUB","Both data surfaces remain RUB preview-only without checkout");
            Check(catalog.offers.Length==12&&shop.ReviewSession.Coins.Length==6&&proposal.products.Length==6&&preview.products.Length==6,"Six coin packs and six approved-price preview bundles retained");
            for(int n=0;n<Quantities.Length;n++){
                string id="coins-"+Quantities[n],label=Rubles[n].ToString(CultureInfo.InvariantCulture)+" \u20bd";
                var offer=shop.ReviewSession.Coins.Single(o=>o.id==id);var planned=proposal.products.Single(p=>p.shopOfferId==id);var mirrored=preview.products.Single(p=>p.id==id);
                Check(planned.coins==Quantities[n]&&planned.proposedPriceMinor==Rubles[n]*100L,"Approved proposal preserves exact quantity/minor price "+id);
                Check(offer.coins==Quantities[n]&&offer.priceLabel==label&&shop.ReviewSession.Price(offer)==label&&mirrored.coins==offer.coins&&mirrored.priceLabel==label,"Live and NoMoves preview data agree on exact RUB display "+id);
                Check(offer.boostersEach==0&&Enumerable.Range(0,4).All(i=>offer.StartingCount(i)==0),"Coin contents unchanged "+id);report.coinMappings++;
            }
            var unconfiguredLive=new ShopSession(new ShopCatalog{schemaVersion=2,isPreview=false,offers=catalog.offers});
            for(int n=0;n<BundleIds.Length;n++){
                var offer=shop.ReviewSession.Specials.Concat(shop.ReviewSession.Mega).Single(o=>o.id==BundleIds[n]);
                string label=BundleRubles[n].ToString(CultureInfo.InvariantCulture)+" \u20bd";
                Check(!offer.available&&offer.priceLabel==label&&shop.ReviewSession.Price(offer)==label,"Approved bundle price is visible without enabling delivery "+offer.id);
                Check(offer.coins==BundleCoins[n]&&offer.boostersEach==BundleToolsEach[n]&&Enumerable.Range(0,4).All(i=>offer.StartingCount(i)==BundleStartingEach[n]),"Existing coin/tool/starting rewards remain exact "+offer.id);
                Check(unconfiguredLive.Price(offer)=="Unavailable","Unconfigured live bundle never falls back to a preview quotation "+offer.id);
                Check(shop.ReviewSession.Open(offer.id),"Bundle detail can be inspected "+offer.id);
                var frame=ShopLayout.Build(393,852,shop.ReviewSession,home.State.coins);
                HeartOfTheRain.App.ShopCheckout86.ShopCheckoutUi86.Apply(frame,shop.ReviewSession,new HeartOfTheRain.App.ShopCheckout86.CheckoutUiState86{configured=true,price=id=>HeartOfTheRain.App.ShopCheckout86.CheckoutCatalogRules86.Ids.Contains(id)?"999 RUB":null,canBuy=id=>HeartOfTheRain.App.ShopCheckout86.CheckoutCatalogRules86.Ids.Contains(id)});
                Check(frame.overlay.elements.Where(e=>!string.IsNullOrEmpty(e.action)).All(e=>e.action=="close"||e.action=="disabled"),"Coin-only configured quotes cannot purchase an unquoted inventory bundle "+offer.id);
                shop.ReviewSession.Close();report.bundlePriceMappings++;
            }
            Check(catalog.offers.All(o=>NoUsd(o.priceLabel))&&preview.products.All(p=>NoUsd(p.priceLabel)),"No USD remains in either current preview catalog");
            report.previewOnly=true;report.checkoutUnavailable=true;
        }
        static void PriceFit(Text text,string name){
            Check(text&&text.gameObject.activeInHierarchy,"Actual visible price text exists "+name);Canvas.ForceUpdateCanvases();
            text.font.RequestCharactersInTexture(text.text,text.fontSize,text.fontStyle);
            Check(text.text.All(c=>char.IsWhiteSpace(c)||text.font.HasCharacter(c)),"Actual design font contains price glyphs "+name);
            Check(text.preferredWidth<=text.rectTransform.rect.width+1&&text.preferredHeight<=text.rectTransform.rect.height+1,"Actual fitted price occupies its bounds "+name);
            Check(NoUsd(text.text),"Actual rendered price contains no USD "+name);
        }
        static void LayoutCase(){
            int locale=Locales[index%5],size=index/5;GameLocale.Select(locale);shop.Show();home.State.reduceMotion=true;Canvas.ForceUpdateCanvases();
            var nodes=Field<Dictionary<string,RectTransform>>(shop,"nodes");
            foreach(var offer in shop.ReviewSession.Coins){string id="offer-"+offer.id+"-view";var button=nodes[id].GetComponent<Button>();var text=nodes[id+"-label"].GetComponent<Text>();
                Check(text.text==offer.priceLabel&&button.interactable,"Actual coin list exposes RUB preview details "+index+"/"+offer.id);PriceFit(text,index+"/"+offer.id);
                Check(nodes[id].GetComponent<HomeControlLabel>().action=="offer:"+offer.id&&nodes[id].GetComponent<Image>().color.a==0,"Coin interaction is a transparent detail hit target, not checkout "+index+"/"+offer.id);
            }
            if(index==0){Field<ScrollRect>(shop,"scroll").verticalNormalizedPosition=0;Capture("Shop_Coins_Russian_Phone");}
            var offers=shop.ReviewSession.Specials.Concat(shop.ReviewSession.Mega).Concat(shop.ReviewSession.Coins).ToArray();
            foreach(var offer in offers){
                nodes=Field<Dictionary<string,RectTransform>>(shop,"nodes");string buttonId="offer-"+offer.id+"-view";
                if(offer.section=="special"){
                    shop.Request("offer:"+offer.id); // Carousel has one active card; the same production dispatcher handles selection.
                }else nodes[buttonId].GetComponent<Button>().onClick.Invoke();
                Check(shop.ReviewSession.Modal&&shop.ReviewSession.OpenOfferId==offer.id,"Actual offer opens only its detail modal "+index+"/"+offer.id);
                nodes=Field<Dictionary<string,RectTransform>>(shop,"nodes");var price=nodes["detail-price"].GetComponent<Text>();
                Check(price.text==GameLocale.T(shop.ReviewSession.Price(offer)),"Actual detail uses exact preview or unavailable text "+index+"/"+offer.id);PriceFit(price,index+"/detail/"+offer.id);
                Check(nodes["detail-price-note"].GetComponent<Text>().text==GameLocale.T(shop.ReviewSession.HasDisplayPrice(offer)?"Sample price":"Store unavailable"),"Detail labels every approved preview price without implying checkout "+index+"/"+offer.id);
                Check(ShopLayout.Build(Sizes[size].x,Sizes[size].y,shop.ReviewSession,home.State.coins).overlay.elements.Where(e=>!string.IsNullOrEmpty(e.action)).All(e=>e.action=="close"||e.action=="disabled"),"Detail has no purchase action "+index+"/"+offer.id);
                if(offer.id=="coins-100000"&&(index==0||index==1||index==5||index==10))Capture("Coin100000_"+GameLocale.Codes[locale]+"_"+Sizes[size].x+"x"+Sizes[size].y);
                if(offer.id=="wellkeeper"&&index==0)Capture("ApprovedBundle_Russian_Phone");
                nodes["detail-close"].GetComponent<Button>().onClick.Invoke();Check(!shop.ReviewSession.Modal,"Actual close returns to browsing "+index+"/"+offer.id);report.detailCases++;
            }
            Check(JsonUtility.ToJson(home.State)==homeBefore,"Browsing and all detail interactions leave preview economy/inventory unchanged "+index);report.layoutCases++;
        }
        static void Capture(string name){
            string relative="Native/ShopRuble85/"+name+".png",path=Path.Combine(Output,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));
            var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var go=new GameObject("Shop RUB native capture camera");go.transform.position=new Vector3(-10000,0,-10);var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var prior=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D pixels=null;
            try{camera.targetTexture=target;foreach(var canvas in canvases){canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());report.captures.Add(relative);}
            finally{for(int n=0;n<canvases.Length;n++){canvases[n].renderMode=RenderMode.ScreenSpaceOverlay;canvases[n].worldCamera=cameras[n];canvases[n].planeDistance=distances[n];}camera.targetTexture=null;RenderTexture.active=prior;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(go);Canvas.ForceUpdateCanvases();}
        }
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-began>180)throw new TimeoutException("Shop RUB native verification timeout");if(report.errors.Count>0)throw new InvalidOperationException(report.errors[0]);
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
            if(phase==0){home=UnityEngine.Object.FindFirstObjectByType<HomePage>();shop=UnityEngine.Object.FindFirstObjectByType<ShopPage>();if(!home||!shop||!shop.IsVisible||Screen.width!=393||Screen.height!=852)return;
                Contracts();home.State.reduceMotion=true;homeBefore=JsonUtility.ToJson(home.State);phase=1;return;}
            if(phase==1){int size=index/5;if(Screen.width!=Sizes[size].x||Screen.height!=Sizes[size].y)return;LayoutCase();index++;
                if(index==15){Size(0);phase=2;}else if(index%5==0)Size(index/5);next=EditorApplication.timeSinceStartup+.08;return;}
            if(phase==2){if(Screen.width!=393||Screen.height!=852)return;GameLocale.Select(4);shop.Hide(false);noMoves=home.gameObject.AddComponent<NoMovesPage>();noMoves.home=home;noMoves.art=Resources.Load<NoMovesAssets>("HOTR_NoMoves/Design");Check(noMoves.art,"Actual NoMoves design imported");
                noMoves.Show("shop",null,home.State.coins,false);Canvas.ForceUpdateCanvases();var buttons=noMoves.GetComponentsInChildren<Button>().Where(b=>b.gameObject.activeInHierarchy&&b.name=="Unavailable store purchase").ToArray();
                Check(buttons.Length==6&&buttons.All(b=>!b.interactable),"All six actual NoMoves store buttons remain disabled");
                Check(noMoves.GetComponentsInChildren<Text>().Where(t=>t.gameObject.activeInHierarchy).All(t=>NoUsd(t.text)),"Actual NoMoves shop displays no USD or fabricated cash checkout");
                int calls=0;noMoves.Requested=_=>calls++;foreach(var button in buttons)if(button.IsInteractable())button.onClick.Invoke();Check(calls==0,"Disabled NoMoves buttons cannot dispatch checkout");
                Check(JsonUtility.ToJson(home.State)==homeBefore,"NoMoves preview does not mutate balance/inventory");report.noMovesPacks=buttons.Length;report.noMovesCheckoutDisabled=true;report.previewHomeUnchanged=true;Capture("NoMoves_StoreUnavailable_Russian_Phone");phase=3;return;}
            if(phase==3){Check(report.layoutCases==15&&report.detailCases==180&&report.captures.Count==7,"Complete price/layout/actual capture matrix recorded");Finish(0);}
        }catch(Exception error){report.errors.Add(error.ToString());Finish(1);}}
        static void Finish(int code){
            try{report.languagePreferenceUnchanged=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==SessionState.GetBool(Key+".preferencePresent",false)&&(!PlayerPrefs.HasKey(GameLocale.PreferenceKey)||PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==SessionState.GetInt(Key+".preference",0));Check(report.languagePreferenceUnchanged,"Ordinary persisted language preference unchanged");GameLocale.Select(SessionState.GetInt(Key+".locale",4));}
            catch(Exception error){report.errors.Add(error.ToString());code=1;}
            report.status=code==0?"PASS_NATIVE_SHOP_RUBLE85_PREVIEW":"FAIL_NATIVE_SHOP_RUBLE85_PREVIEW";Directory.CreateDirectory(Path.Combine(Output,"Native"));File.WriteAllText(Path.Combine(Output,"Native/ShopRuble85.json"),JsonUtility.ToJson(report,true));
            EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SessionState.EraseBool(Key);
            try{View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),SessionState.GetInt("HOTR.M71.Verification.previous",0));var group=typeof(ProfileM71Verification).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);for(int n=4;n>=0;n--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.M71.Verification.first",0)+n});}
            catch(Exception error){Debug.LogWarning(error.Message);}EditorApplication.Exit(code);
        }
    }
}
#endif
