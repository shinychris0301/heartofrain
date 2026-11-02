using System;
using System.Collections;
using HeartOfTheRain.App.ShopCheckout86;
using HeartOfTheRain.App.Home;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.App.NoMoves {
    public sealed partial class NoMovesPage {
        ShopCheckoutHost86 checkout86;DirectShopCheckoutHost132 directCheckout132;bool checkout86Open,checkout86Credited;CheckoutUiState86 checkout86View;
#if UNITY_EDITOR
        public Func<CheckoutUiState86> VerificationCheckout86;
#endif
        public bool CheckoutBusy86=>checkout86&&checkout86.Busy||directCheckout132&&directCheckout132.Busy;
        CheckoutUiState86 CheckoutView86(){
#if UNITY_EDITOR
            if(VerificationCheckout86!=null)return checkout86View=VerificationCheckout86();
#endif
            if(!checkout86&&!directCheckout132){directCheckout132=DirectShopCheckoutHost132.Select(home);if(directCheckout132)directCheckout132.Changed+=CheckoutChanged86;else{checkout86=ShopCheckoutHost86.Select(home);if(checkout86)checkout86.Changed+=CheckoutChanged86;}}
            if((checkout86||directCheckout132)&&!checkout86Open){checkout86Open=true;checkout86Credited=directCheckout132?directCheckout132.Credited:checkout86.Credited;StartCoroutine(OpenCheckout86());}
            return checkout86View=directCheckout132?CheckoutUiState86.From(directCheckout132):CheckoutUiState86.From(checkout86);
        }
        IEnumerator OpenCheckout86(){yield return null;if(Visible&&Screen=="shop"){if(directCheckout132)directCheckout132.Show();else if(checkout86)checkout86.Show(true);}}
        void CheckoutChanged86(){
            if(!Visible||Screen!="shop"||(!checkout86&&!directCheckout132))return;
            bool credited=directCheckout132?directCheckout132.Credited:checkout86.Credited;if(credited&&!checkout86Credited){checkout86Credited=true;Requested?.Invoke("checkout:complete");return;}checkout86Credited=credited;Layout();
        }
        public void CheckoutRequest86(string action){if(directCheckout132)directCheckout132.Request(action);else if(checkout86)checkout86.Request(action);}
        // The existing gold/green button face has a smaller usable interior.
        // Keep the SDK amount on one line; retain full localized Buy semantics.
        void FitCheckoutPrice86(Button button,string fullLabel,string action){
            var label=button.GetComponentInChildren<Text>();if(label){
                var area=((RectTransform)button.transform).rect;Place(label.rectTransform,13,8,area.width-26,area.height-16);
                label.resizeTextForBestFit=false;label.horizontalOverflow=HorizontalWrapMode.Overflow;label.verticalOverflow=VerticalWrapMode.Truncate;
                LabelFit.Apply(label,area.width-26,area.height-16,8);
            }
            var semantic=button.gameObject.AddComponent<HomeControlLabel>();semantic.label=fullLabel;semantic.action=action;
        }
        void CheckoutButtons86(){
            var view=checkout86View;if(Screen!="shop"||view==null||!view.configured)return;
            if(view.busy){foreach(var button in canvas.GetComponentsInChildren<Button>())button.interactable=false;return;}
            foreach(string id in CheckoutCatalogRules86.Ids){RectTransform node;if(Nodes.TryGetValue("Checkout purchase "+id,out node))node.GetComponent<Button>().interactable=!busy&&(view.canBuy?.Invoke(id)==true||view.pending&&view.pendingProduct==id);}
        }
        void OnDestroy(){if(checkout86)checkout86.Changed-=CheckoutChanged86;if(directCheckout132)directCheckout132.Changed-=CheckoutChanged86;}
    }
}
