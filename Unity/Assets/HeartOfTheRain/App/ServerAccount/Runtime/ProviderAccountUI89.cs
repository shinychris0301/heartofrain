using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.ServerAccount;
using HeartOfTheRain.App.Localization;

namespace HeartOfTheRain.App.AccountDesign {
    public sealed partial class AccountModal {
        IProviderAccount89 Providers=>service as IProviderAccount89;
        string ProviderText(string en,string es,string fr,string de,string ru)=>new[]{en,es,fr,de,ru}[GameLocale.Current];
        float LayoutProviderAccount(float width,float y){
            if(service is IProviderSignin102)return LayoutVkSignin102(width,y);
            var providers=Providers;var vk=providers?.VkStatus;
            bool enabled=providers!=null&&vk!=null&&vk.available&&!vk.linked&&vk.phase!="Exchanging"&&!busy&&!providers.ProviderBusy&&Managed.Controls.ready&&!Managed.Controls.busy;
            var button=Button(body,"Server provider VK","vk-signup",vk!=null&&vk.linked?ProviderText("VK connected","VK conectado","VK connecté","VK verbunden","VK подключён"):AccountText.T("vk"),0,y,width,46,true);button.interactable=enabled;y+=54;
            if(vk==null||!vk.available)y=Paragraph("VK provider availability",ProviderText("VK signup requires a configured online service.","El registro con VK requiere el servicio en línea.","L’inscription VK nécessite le service en ligne configuré.","VK erfordert den eingerichteten Onlinedienst.","Для регистрации через VK нужен настроенный онлайн-сервис."),y,width,12);
            else if(vk.linked)y=Paragraph("VK link status",ProviderText("VK is linked to this journey. Keep your recovery code for another device.","VK está vinculado. Guarda el código de recuperación para otro dispositivo.","VK est lié. Conservez le code de récupération pour un autre appareil.","VK ist verknüpft. Behalte den Wiederherstellungscode für ein anderes Gerät.","VK привязан к этому прогрессу. Сохраните код восстановления для другого устройства."),y,width,12);
            else if(vk.Pending){
                y=Paragraph("VK browser return",ProviderText("Finish in your browser, return here, then check the result.","Termina en el navegador, vuelve aquí y comprueba el resultado.","Terminez dans le navigateur, revenez et vérifiez le résultat.","Schließe den Browser-Schritt ab, kehre zurück und prüfe das Ergebnis.","Завершите вход в браузере, вернитесь в игру и проверьте результат."),y,width,12);
                var cancel=Button(body,"Cancel VK signup","vk-cancel",ProviderText("Cancel VK signup","Cancelar registro VK","Annuler l’inscription VK","VK-Registrierung abbrechen","Отменить регистрацию VK"),0,y,width,42);cancel.interactable=!busy&&!providers.ProviderBusy;y+=50;
            }else if(vk.phase=="Conflict")y=Paragraph("VK account conflict",ProviderText("This VK account belongs to another journey. Use its recovery code to open that journey.","Esta cuenta VK pertenece a otra partida. Usa su código de recuperación.","Ce compte VK appartient à une autre partie. Utilisez son code de récupération.","Dieses VK-Konto gehört zu einem anderen Spielstand. Nutze dessen Wiederherstellungscode.","Этот аккаунт VK привязан к другому прогрессу. Для входа используйте его код восстановления."),y,width,12);
            else if(vk.phase=="Failed"||vk.phase=="Expired")y=Paragraph("VK retry explanation",ProviderText("VK signup did not finish. Please try again.","El registro VK no se completó. Inténtalo de nuevo.","L’inscription VK n’a pas abouti. Réessayez.","VK-Registrierung nicht abgeschlossen. Bitte erneut versuchen.","Регистрация через VK не завершена. Повторите попытку."),y,width,12);
            var refresh=Button(body,"Refresh VK signup","vk-refresh",ProviderText("Check VK status","Comprobar VK","Vérifier VK","VK-Status prüfen","Проверить статус VK"),0,y,width,42);refresh.interactable=providers!=null&&!providers.ProviderBusy&&!busy&&Managed.Controls.ready&&!Managed.Controls.busy;return y+50;
        }
        bool HandleProviderAccount(string action){
            if(HandleVkSignin102(action))return true;
            if(action=="VK")return true; // Local mode cannot claim a cloud link.
            if(action!="vk-signup"&&action!="vk-cancel"&&action!="vk-refresh")return false;
            if(Providers==null||busy||Providers.ProviderBusy)return true;
            if(action=="vk-refresh"){Providers.RefreshProviders();return true;}
            busy=true;int request=++generation;Layout();
            System.Action<bool,string> done=(ok,why)=>{if(!this||!IsVisible||generation!=request)return;busy=false;serverNotice=ok?"":"serverError";Refresh();Layout();Focus("Account close");};
            if(action=="vk-signup")Providers.BeginVk(done);else Providers.CancelVk(done);return true;
        }
        void OnApplicationFocus(bool focused){if(focused&&IsVisible)Providers?.RefreshProviders();}
    }
}
