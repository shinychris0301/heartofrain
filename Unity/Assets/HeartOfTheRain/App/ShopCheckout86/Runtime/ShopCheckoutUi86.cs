using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Shop;

namespace HeartOfTheRain.App.ShopCheckout86 {
    public static class CheckoutText86 {
        static readonly Dictionary<string,string[]> Words=new Dictionary<string,string[]> {
            {"buy",new[]{"Buy","Comprar","Acheter","Kaufen","Купить"}},
            {"retry",new[]{"Continue purchase","Continuar compra","Continuer l’achat","Kauf fortsetzen","Продолжить покупку"}},
            {"reload",new[]{"Try again","Reintentar","Réessayer","Erneut versuchen","Повторить"}},
            {"sandbox",new[]{"Sandbox purchases","Compras de prueba","Achats de test","Testk\u00e4ufe","\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0435 \u043f\u043e\u043a\u0443\u043f\u043a\u0438"}},
            {"ready",new[]{"Purchase through RuStore","Comprar con RuStore","Acheter via RuStore","Über RuStore kaufen","Покупка через RuStore"}},
            {"pending",new[]{"A purchase needs checking.","Hay una compra pendiente.","Un achat reste à vérifier.","Ein Kauf wird noch geprüft.","Нужно проверить покупку."}},
            {"busy",new[]{"Checking purchase…","Comprobando compra…","Vérification de l’achat…","Kauf wird geprüft…","Проверяем покупку…"}},
            {"success",new[]{"Purchase confirmed","Compra confirmada","Achat confirmé","Kauf bestätigt","Покупка подтверждена"}},
            {"closed",new[]{"Purchase not completed","Compra no completada","Achat non effectué","Kauf nicht abgeschlossen","Покупка не завершена"}},
            {"unavailable",new[]{"Store unavailable","Tienda no disponible","Boutique indisponible","Shop nicht verfügbar","Магазин недоступен"}},
            {"once",new[]{"Once per account","Una vez por cuenta","Une fois par compte","Einmal pro Konto","\u041e\u0434\u0438\u043d \u0440\u0430\u0437 \u043d\u0430 \u0430\u043a\u043a\u0430\u0443\u043d\u0442"}},
            {"purchased",new[]{"Already purchased","Ya comprado","D\u00e9j\u00e0 achet\u00e9","Bereits gekauft","\u0423\u0436\u0435 \u043a\u0443\u043f\u043b\u0435\u043d\u043e"}},
            {"explicit",new[]{"Extra moves require a separate Play On tap.","Pulsa Jugar para comprar movimientos.","Touchez Jouer pour acheter des coups.","Extra-Züge separat mit Weiterspielen kaufen.","Ходы покупаются отдельно кнопкой «Играть»."}}
        };
        static readonly Dictionary<string,string> Russian=new Dictionary<string,string> {
            {"buy","Купить"},{"retry","Продолжить покупку"},{"reload","Повторить"},
            {"sandbox","Тестовые покупки"},{"ready","Покупка через RuStore"},
            {"pending","Покупку нужно проверить."},{"busy","Проверяем покупку…"},
            {"success","Покупка подтверждена"},{"closed","Покупка не завершена"},
            {"unavailable","Магазин недоступен"},{"once","Один раз на аккаунт"},
            {"purchased","Уже куплено"},{"explicit","Дополнительные ходы покупаются отдельным нажатием «Играть»."}
        };
        public static string T(string key)=>GameLocale.Current==4&&Russian.TryGetValue(key,out var value)?value:Words.TryGetValue(key,out var values)?values[GameLocale.Current]:key;
        public static string DeviceOnly()=>new[]{"This device only","Solo en este dispositivo","Sur cet appareil","Nur auf diesem Gerat","\u0422\u043e\u043b\u044c\u043a\u043e \u043d\u0430 \u044d\u0442\u043e\u043c \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0435"}[GameLocale.Current];
        public static string DeviceOnlyNote()=>new[]{"Purchases stay on this device","Las compras quedan en este dispositivo","Achats conserves sur cet appareil","Kaufe bleiben auf diesem Gerat","\u041f\u043e\u043a\u0443\u043f\u043a\u0438 \u043e\u0441\u0442\u0430\u044e\u0442\u0441\u044f \u043d\u0430 \u044d\u0442\u043e\u043c \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0435"}[GameLocale.Current];
        public static string Buy(string amount)=>T("buy")+" · "+amount;
    }
    public sealed class CheckoutUiState86 {
        public bool configured,busy,pending,credited,deviceOnly;public bool sandbox=true;public string pendingProduct,error;
        public Func<string,string> price,eligibility;public Func<string,bool> canBuy;
        public string Status=>busy?CheckoutText86.T("busy"):credited?CheckoutText86.T("success"):pending?CheckoutText86.T("pending"):error=="CheckoutResolvedWithoutDelivery"?CheckoutText86.T("closed"):error!=null?CheckoutText86.T("unavailable"):CheckoutText86.T("ready");
        public static CheckoutUiState86 From(ShopCheckoutHost86 host)=>host?new CheckoutUiState86{configured=host.Configured,sandbox=host.Sandbox,busy=host.Busy,pending=host.Pending,credited=host.Credited,pendingProduct=host.PendingProduct,error=host.Error,price=host.Price,eligibility=host.Eligibility,canBuy=host.CanBuy}:null;
        public static CheckoutUiState86 From(DirectShopCheckoutHost132 host)=>host?new CheckoutUiState86{configured=host.Configured,sandbox=DirectSandbox132,deviceOnly=true,busy=host.Busy,pending=host.Pending,credited=host.Credited,pendingProduct=host.PendingProduct,error=host.Error,price=host.Price,eligibility=host.Eligibility,canBuy=host.CanBuy}:null;
        static bool DirectSandbox132 {
            get {
#if HOTR_DIRECT_SANDBOX132
                return true;
#else
                return false;
#endif
            }
        }
    }
    // Reuses the existing approved controls and geometry. Default preview
    // frames are untouched when explicit sandbox checkout is not selected.
    public static class ShopCheckoutUi86 {
        public static void Apply(ShopFrame frame,ShopSession session,CheckoutUiState86 state){
            if(state==null||!state.configured)return;
            foreach(var offer in session.Coins.Concat(session.Specials).Concat(session.Mega)){
                string suffix="offer-"+offer.id+"-view-label";string price=state.price?.Invoke(offer.id)??CheckoutText86.T("unavailable");
                foreach(var container in new[]{frame.content,frame.specials})foreach(var label in container.elements.Where(e=>e.id.EndsWith(suffix,StringComparison.Ordinal)))label.text=price;
            }
            var note=frame.chrome.elements.FirstOrDefault(e=>e.id=="preview-note");if(note!=null)note.text=state.deviceOnly?
                (state.sandbox?CheckoutText86.T("sandbox")+" · ":"")+CheckoutText86.DeviceOnlyNote():state.sandbox?CheckoutText86.T("sandbox"):"";
            var selected=session.OpenOffer;if(selected==null||!CheckoutCatalogRules86.Known(selected.id))return;
            string amount=state.price?.Invoke(selected.id);foreach(var element in frame.overlay.elements){
                if(element.id=="detail-price")element.text=amount??CheckoutText86.T("unavailable");
                if(element.id=="detail-price-note")element.text=state.sandbox?CheckoutText86.T("sandbox"):"";
                if(element.id=="detail-status-1")element.text=state.eligibility?.Invoke(selected.id)=="Purchased"&&!state.pending&&!state.busy?CheckoutText86.T("purchased"):state.Status;
                if(element.id=="detail-status-2")element.text=state.deviceOnly?CheckoutText86.DeviceOnly():selected.section=="special"?CheckoutText86.T("once"):"";
                bool retry=state.pending&&state.pendingProduct==selected.id;bool reload=!retry&&!state.busy&&amount==null;bool eligible=state.canBuy?.Invoke(selected.id)==true;
                bool enabled=!state.busy&&(retry||reload||amount!=null&&eligible);
                string label=retry?CheckoutText86.T("retry"):reload?CheckoutText86.T("reload"):amount==null||!eligible?CheckoutText86.T("unavailable"):CheckoutText86.Buy(amount);
                if(element.id=="detail-back"){element.action=enabled?(retry||reload?"checkout:retry":"checkout:buy:"+selected.id):"disabled";element.label=label;}
                if(element.id=="detail-back-label")element.text=label;
            }
        }
    }
}
