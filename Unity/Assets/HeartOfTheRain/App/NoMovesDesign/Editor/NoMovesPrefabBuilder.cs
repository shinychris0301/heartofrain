// Import first, then Tools > Heart of the Rain > Build Continue R3 Prefab.
// Creates an isolated prefab; never edits the existing scene, shared Canvas or shop.
#if UNITY_EDITOR
using System;
using System.IO;

using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.NoMovesUI;
using HeartOfTheRain.ContinueReference;
namespace HeartOfTheRain.NoMovesEditor
{
    public static class NoMovesPrefabBuilder
    {
        const string Root = "Assets/HeartOfTheRain/App/NoMovesDesign";
        const string Shared = "Assets/HeartOfTheRain/App/AccountDesign/Art/";
        static UnityEngine.Font title, body;

        static Color Ink = new Color32(24,59,98,255), Cream = new Color32(255,246,220,255);
        [MenuItem("Tools/Heart of the Rain/Build Continue R3 Prefab")]
        public static void Build()
        {
            Directory.CreateDirectory(Root + "/Generated"); AssetDatabase.Refresh();
            title = Font("AccountTitle"); body = Font("AccountBody");

            var root = Node("ContinueOverlay_R3", null);
            var canvas = root.gameObject.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 200; canvas.referencePixelsPerUnit = 100;
            var scaler = root.gameObject.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(393,852); scaler.matchWidthOrHeight = 0;
            scaler.referencePixelsPerUnit = 100;
            root.gameObject.AddComponent<GraphicRaycaster>();
            root.gameObject.AddComponent<ContinueCanvasProfile>();
            var v = root.gameObject.AddComponent<NoMovesOverlayView>();
            v.Scrim = Image("Scrim",root,null); Stretch(v.Scrim.rectTransform);
            v.Scrim.color = new Color32(2,10,24,189); v.Scrim.raycastTarget = true;
            v.SafeArea = Node("SafeArea",root); Stretch(v.SafeArea);
            v.Viewport = Node("Viewport",v.SafeArea); var hit = Image("Blocker",v.Viewport,null);
            Stretch(hit.rectTransform); hit.color=Color.clear; hit.raycastTarget=true;
            v.Viewport.gameObject.AddComponent<RectMask2D>();
            v.Content = Node("Content",v.Viewport);
            v.Scroll = v.SafeArea.gameObject.AddComponent<ScrollRect>(); v.Scroll.viewport=v.Viewport;
            v.Scroll.content=v.Content; v.Scroll.horizontal=false; v.Scroll.movementType=ScrollRect.MovementType.Clamped;
            v.Scroll.inertia=true; v.Scroll.scrollSensitivity=20;
            v.WalletImage=Image("Wallet",v.Content,"NM_Wallet_Pill.png");
            v.WalletButton=Button(v.WalletImage);
            v.WalletCoin=Image("Coin",v.WalletImage.rectTransform,"NM_Coin_Glyph.png",true);
            v.Balance=Text("Balance",v.WalletImage.rectTransform,title,21,Cream);
            v.WalletPlus=Image("ShopPlus",v.WalletImage.rectTransform,"NM_Wallet_Plus.png",true);
            // Plus stays inside the same wallet touch target; no independent 26px button.
            v.BandImage=Image("Band",v.Content,"NM_Continue_Band.png");v.Band=v.BandImage.rectTransform;
            v.Title=Text("Title",v.Band,title,30,Cream);
            v.Hero=Node("Hero",v.Band);
            v.Dariya=Image("Dariya",v.Hero,"NM_Dariya_Continue.png",true);
            v.Offer=Node("MoveOffer",v.Hero);
            v.Halo=Image("Halo",v.Offer,"NM_Offer_Halo.png",true);
            v.Badge=Image("Badge",v.Offer,"NM_Moves_Badge.png",true);
            v.Amount=Text("Moves",v.Badge.rectTransform,title,44,Cream);
            v.Copy=Text("OfferCopy",v.Offer,title,19,Ink);v.Copy.horizontalOverflow=HorizontalWrapMode.Wrap;
            v.Primary=Image("PlayOn",v.Band,"Primary.png");v.PlayButton=Button(v.Primary);
            v.PlayLabel=Text("Label",v.Primary.rectTransform,title,24,Cream);
            v.PriceGroup=Node("Price",v.Primary.rectTransform);
            v.PriceCoin=Image("Coin",v.PriceGroup,"NM_Coin_Glyph.png",true);
            v.Price=Text("Cost",v.PriceGroup,title,23,Cream);
            var close=Node("CloseHit",v.Band);var closeHit=Image("Hit",close,null);Stretch(closeHit.rectTransform);
            closeHit.color=Color.clear;closeHit.raycastTarget=true;
            v.CloseButton=close.gameObject.AddComponent<Button>();v.CloseButton.targetGraphic=closeHit;v.CloseButton.transition=Selectable.Transition.None;
            v.CloseImage=Image("CloseArt",close,"Close.png",true);
            v.PackImage=Image("CoinOffer",v.Content,"SP_Mega.png");v.Pack=v.PackImage.rectTransform;
            v.PackIcon=Image("Pouch",v.Pack,"SP_CoinPouch.png",true);
            v.PackName=Text("Name",v.Pack,title,17,Ink);
            v.PackAmount=Text("Coins",v.Pack,body,14,new Color32(91,107,115,255));
            v.PackButtonImage=Image("PriceButton",v.Pack,"Primary.png");v.PackButton=Button(v.PackButtonImage);
            v.PackPrice=Text("Price",v.PackButtonImage.rectTransform,title,19,Cream);
            Canvas.ForceUpdateCanvases();
            v.Render(ContinueOfferViewModel.Ready(new Quote{CoinCost=900,ExtraMoves=5}),700,PreviewLabels(),"en");
            // No production example data can become an active offer just by importing the prefab.
            root.gameObject.SetActive(false);
            string path=Root+"/Generated/ContinueOverlay_R3.prefab";
            PrefabUtility.SaveAsPrefabAsset(root.gameObject,path);UnityEngine.Object.DestroyImmediate(root.gameObject);
            AssetDatabase.SaveAssets();HeartOfTheRain.App.NoMoves.Editor.NoMovesSetup.Configure();Selection.activeObject=AssetDatabase.LoadAssetAtPath<GameObject>(path);
            Debug.Log("Created " + path + ". Bind live quote/wallet/events before Render. Test in the current project; native rendering was not validated by the package producer.");
        }
        static UnityEngine.Font Font(string name) {
            var font=name=="AccountTitle"?HeartOfTheRain.App.AccountDesign.AccountDesignAssets.Load().titleFont:HeartOfTheRain.App.AccountDesign.AccountDesignAssets.Load().bodyFont;
            if(!font)throw new InvalidOperationException("Missing existing dynamic font: "+name);return font;
        }
        static RectTransform Node(string name,Transform parent)
        {var go=new GameObject(name,typeof(RectTransform));var r=(RectTransform)go.transform;if(parent!=null)r.SetParent(parent,false);return r;}
        static Image Image(string name,Transform parent,string asset,bool preserve=false)
        {
            var r=Node(name,parent);var image=r.gameObject.AddComponent<Image>();
            if(asset!=null)
            {
                string path=asset=="Primary.png"?"Assets/HeartOfTheRain/App/Profile/Art/Primary.png":(asset=="Close.png"?Shared:Root+"/Art/")+asset;
                image.sprite=AssetDatabase.LoadAssetAtPath<Sprite>(path);
                if(image.sprite==null)throw new InvalidOperationException("Missing Sprite: "+path);
            }
            image.color=Color.white;image.raycastTarget=false;image.preserveAspect=preserve;
            image.type=preserve?UnityEngine.UI.Image.Type.Simple:UnityEngine.UI.Image.Type.Sliced;
            return image;
        }
        static Button Button(Image image)
        {var b=image.gameObject.AddComponent<Button>();b.targetGraphic=image;image.raycastTarget=true;b.transition=Selectable.Transition.None;return b;}
        static UnityEngine.UI.Text Text(string name,Transform parent,UnityEngine.Font font,float size,Color color)
        {
            var r=Node(name,parent);var t=r.gameObject.AddComponent<UnityEngine.UI.Text>();t.font=font;t.fontSize=Mathf.RoundToInt(size);
            if(color == Cream){var shadow=r.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color32(9,41,70,255);shadow.effectDistance=new Vector2(0,-1.3f);}
            t.color=color;t.alignment=TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Wrap;
            t.raycastTarget=false;t.supportRichText=false;t.verticalOverflow=VerticalWrapMode.Truncate;
            // Keep the font's material and padding. Never use a low-resolution flattened text sprite.
            return t;
        }
        static void Stretch(RectTransform r)
        {r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;}
        public static ContinueLabels PreviewLabels()
        {return new ContinueLabels {Title="Continue?",AddMoves="Add {n} moves to continue!",PlayOn="Play On",EndLevel="End level",Loading="Loading offer…",Unavailable="No extra moves available.",Error="Could not load the offer.",Retry="Try again",PackName="Village Purse",PackAmount="1,000 coins",PackPrice="Shop"};}
    }
}
#endif
