using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.NoMovesUI;
using HeartOfTheRain.ContinueReference;
namespace HeartOfTheRain.App.NoMoves {
    public sealed partial class NoMovesPage {
        NoMovesOverlayView r3;
        public NoMovesOverlayView R3=>r3;
        bool UseR3=>art&&art.continuePrefab&&(Screen=="offer"||Screen=="loading"||Screen=="error");
        void RenderR3(){
            if(!r3){
                r3=Instantiate(art.continuePrefab,transform,false).GetComponent<NoMovesOverlayView>();
                r3.PlayRequested+=()=>Requested?.Invoke("play");r3.ShopRequested+=()=>Requested?.Invoke("shop");
                r3.PackRequested+=()=>Requested?.Invoke("shop");r3.EndConfirmationRequested+=()=>Requested?.Invoke("back");
                r3.RetryQuoteRequested+=()=>Requested?.Invoke("retryQuote");
            }
            canvas.gameObject.SetActive(false);
            float aspect=UnityEngine.Screen.width/(float)Mathf.Max(1,UnityEngine.Screen.height);
            r3.GetComponent<ContinueCanvasProfile>().tabletLayout=aspect>=.68f&&aspect<=1.8f;
            var model=Screen=="loading"?ContinueOfferViewModel.Loading():Screen=="error"?ContinueOfferViewModel.Error():quote==null?ContinueOfferViewModel.Unavailable():ContinueOfferViewModel.Ready(new Quote{CoinCost=quote.cost,ExtraMoves=quote.moves});
            var labels=new ContinueLabels{Title=NoMovesText.T("continue"),AddMoves=NoMovesText.T("addMoves"),PlayOn=NoMovesText.T("play"),EndLevel=NoMovesText.T("end"),Loading=NoMovesText.T("loadingOffer"),Unavailable=NoMovesText.T("unavailable"),Error=NoMovesText.T("offerError"),Retry=GameLocale.T("Try again"),PackName=NoMovesText.T("purse"),PackAmount=NoMovesText.T("coinAmount").Replace("{n}",1000.ToString("N0")),PackPrice=NoMovesText.T("shop")};
            // The existing catalog is a preview. Browse the 1,000-coin entry;
            // no fabricated cash price, store purchase or automatic coin grant.
            var shop=home.GetComponent<HeartOfTheRain.App.Shop.ShopPage>();
            if(!shop||!shop.assets||!shop.assets.catalog)labels.PackPrice="";
            r3.Render(model,coins,labels,GameLocale.Codes[GameLocale.Current],busy);
            Nodes.Clear();Nodes["Play on"]=(RectTransform)r3.PlayButton.transform;Nodes["Continue close"]=(RectTransform)r3.CloseButton.transform;
            Nodes["Wallet"]=(RectTransform)r3.WalletButton.transform;Nodes["Coin offer"]=(RectTransform)r3.PackButton.transform;
            if(EventSystem.current)EventSystem.current.SetSelectedGameObject(r3.PlayButton.gameObject);
            size=new Vector2Int(UnityEngine.Screen.width,UnityEngine.Screen.height);safeRect=UnityEngine.Screen.safeArea;locale=GameLocale.Revision;
        }
    }
}
