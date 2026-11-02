#if UNITY_EDITOR
using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.NoMovesUI;
using HeartOfTheRain.ContinueReference;
namespace HeartOfTheRain.NoMovesEditor
{
    public static class NoMovesPrefabValidator
    {
        [MenuItem("Tools/Heart of the Rain/Validate Continue R3 Prefab")]
        public static void Validate()
        {
            string path="Assets/HeartOfTheRain/App/NoMovesDesign/Generated/ContinueOverlay_R3.prefab";
            var go=PrefabUtility.LoadPrefabContents(path);
            try
            {
                var v=go.GetComponent<NoMovesOverlayView>();Need(v!=null,"Missing NoMovesOverlayView");
                var q=new Quote{CoinCost=900,ExtraMoves=5};
                foreach(int wallet in new[]{0,700,900,1600})
                {
                    v.Render(ContinueOfferViewModel.Ready(q),wallet,NoMovesPrefabBuilder.PreviewLabels(),"en");
                    Canvas.ForceUpdateCanvases();v.Relayout();
                    Need(v.Price.text=="900"&&v.Amount.text=="+5","Balance incorrectly hides offer");
                    Need(v.PlayButton.interactable,"Low balance disables Play On");
                    Need(v.Primary.type==Image.Type.Sliced,"Primary must be sliced");
                    Need(v.Primary.rectTransform.rect.width<v.Band.rect.width-45,"Primary stretched to footer width");
                    Need(Mathf.Abs(v.Primary.rectTransform.rect.height-57)<.1f,"Incorrect primary height");
                    Need(v.Dariya.preserveAspect&&v.Badge.preserveAspect,"Artwork aspect lost");
                    Need(v.Pack.gameObject.activeSelf,"Preview pack missing");
                    Need(v.WalletImage.rectTransform.anchoredPosition.x<20,"Wallet moved to right");
                    float ratio=v.Primary.sprite.pixelsPerUnit/v.Primary.canvas.referencePixelsPerUnit*v.Primary.pixelsPerUnitMultiplier;
                    Need(Mathf.Abs(ratio-300f/35)<.01f,"Primary corner density mismatch");
                }
                v.Render(ContinueOfferViewModel.Error(),700,NoMovesPrefabBuilder.PreviewLabels(),"en");
                Need(v.PlayLabel.text=="Try again","Network error falsely ends level");
                Debug.Log("Continue R3 prefab structure validated in this Editor. Next: compare rendered Game view and exercise live shop/board bindings on devices.");
            }
            finally{PrefabUtility.UnloadPrefabContents(go);}
        }
        static void Need(bool value,string message){if(!value)throw new InvalidOperationException(message);}
    }
}
#endif
