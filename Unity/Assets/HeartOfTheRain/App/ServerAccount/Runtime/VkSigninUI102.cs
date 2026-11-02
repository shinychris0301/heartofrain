using System;
using UnityEngine;
using HeartOfTheRain.App.ServerAccount;

namespace HeartOfTheRain.App.AccountDesign {
    public sealed partial class AccountModal {
        string vkShownTarget="";
        IProviderSignin102 VkSigninService=>service as IProviderSignin102;
        bool PinnedVkResume102=>serverScreen=="status"&&VkSigninService!=null&&Managed!=null&&Managed.Controls.pending&&Managed.Controls.purpose=="vk";
        bool LayoutVkFooter102(float width){
            if(PinnedVkResume102){
                var resume=Button(footer,"Resume confirmed VK sign in","server-resume",ProviderText("Resume VK sign-in","Reanudar acceso VK","Reprendre la connexion VK","VK-Anmeldung fortsetzen","Продолжить вход через VK"),0,0,width,46,true);resume.interactable=!busy&&!Managed.Controls.busy;return true;
            }
            var state=VkSigninService?.VkSignin;
            if(serverScreen!="status"||state==null||state.phase!="Ready"||Managed==null||state.targetPlayerId!=vkShownTarget||!HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(vkShownTarget))return false;
            var finish=Button(footer,"Confirm VK saved game","vk102-complete",state.requiresConfirmation?ProviderText("Switch to this saved game","Cambiar a esta partida","Ouvrir cette partie","Diesen Spielstand öffnen","Перейти к этому прогрессу"):ProviderText("Finish VK registration","Finalizar registro VK","Finaliser l’inscription VK","VK-Registrierung abschließen","Завершить регистрацию VK"),0,0,width,46,true);
            finish.interactable=!busy&&!Managed.Controls.busy&&Managed.Controls.ready&&HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(vkShownTarget);return true;
        }
        float LayoutVkSignin102(float width,float y){
            var provider=Providers;var signin=VkSigninService;var state=signin.VkSignin;var account=Managed.Controls;
            vkShownTarget="";bool idle=!busy&&!account.busy&&provider!=null&&!provider.ProviderBusy;
            bool pending=state!=null&&(state.Pending||state.phase=="Prepared"||state.phase=="Ready"||state.phase=="Committing");
            bool available=provider?.VkStatus!=null&&provider.VkStatus.available;
            var begin=Button(body,"VK registration or sign in","vk102-begin",ProviderText("Register / sign in with VK","Registrarse / entrar con VK","S’inscrire / se connecter avec VK","Mit VK registrieren / anmelden","Регистрация / вход через VK"),0,y,width,46,true);
            begin.interactable=idle&&account.ready&&account.blocker==null&&available&&!pending;y+=54;
            if(!available)y=Paragraph("VK signup availability",ProviderText("VK sign-in is unavailable until the online service is configured.","El acceso VK requiere el servicio en línea configurado.","La connexion VK nécessite le service en ligne configuré.","VK-Anmeldung benötigt den eingerichteten Onlinedienst.","Вход через VK будет доступен после настройки онлайн-сервиса."),y,width,12);
            if(state!=null&&state.phase=="Ready"){
                vkShownTarget=state.targetPlayerId;
                string copy=state.requiresConfirmation?ProviderText("This VK account has another saved game. Confirm switching to it. Your current game stays separate; progress and purchases are not merged.","Esta cuenta VK tiene otra partida. Confirma el cambio. Tu partida actual se conserva por separado.","Ce compte VK possède une autre partie. Confirmez le changement. Votre partie actuelle reste séparée.","Dieses VK-Konto hat einen anderen Spielstand. Bestätige den Wechsel. Dein bisheriger Spielstand bleibt getrennt.","У этого аккаунта VK есть другой прогресс. Подтвердите переход. Текущий прогресс сохранится отдельно; покупки и прогресс не объединяются."):
                    ProviderText("VK authorization is complete. Finish registration to connect this saved game.","La autorización VK está lista. Finaliza el registro para vincular esta partida.","L’autorisation VK est terminée. Finalisez l’inscription pour lier cette partie.","VK ist bestätigt. Schließe die Registrierung für diesen Spielstand ab.","Авторизация VK завершена. Завершите регистрацию, чтобы привязать этот прогресс.");
                y=Paragraph("VK account confirmation",copy,y,width,13);
                y=Paragraph("VK confirmed target",state.targetPlayerId,y,width,11);
            }else if(state!=null&&(state.Pending||state.phase=="Prepared"))y=Paragraph("VK browser authorization",ProviderText("Finish authorization in your browser, return to the game, and check the result.","Autoriza en el navegador, vuelve al juego y comprueba el resultado.","Autorisez dans le navigateur, revenez au jeu et vérifiez le résultat.","Bestätige im Browser, kehre zurück und prüfe das Ergebnis.","Завершите вход в браузере, вернитесь в игру и проверьте результат."),y,width,12);
            else if(state!=null&&state.phase=="Committing")y=Paragraph("VK confirmation pending",ProviderText("Your confirmed sign-in is being recovered. Resume the pending account action below.","Se está recuperando tu acceso confirmado. Reanuda la acción pendiente.","Votre connexion confirmée est en cours de reprise. Reprenez l’action en attente.","Die bestätigte Anmeldung wird wiederhergestellt. Setze den Vorgang unten fort.","Восстанавливается подтверждённый вход. Продолжите незавершённое действие ниже."),y,width,12);
            else if(state!=null&&state.phase=="Completed"||state==null&&provider?.VkStatus!=null&&provider.VkStatus.linked)y=Paragraph("VK account connected",ProviderText("VK is connected. You can use VK to sign in on another device.","VK está vinculado. Puedes entrar con VK en otro dispositivo.","VK est lié. Connectez-vous avec VK sur un autre appareil.","VK ist verbunden. Du kannst dich auf einem anderen Gerät mit VK anmelden.","VK подключён. Теперь можно войти через VK на другом устройстве."),y,width,12);
            else if(state!=null&&state.Terminal)y=Paragraph("VK sign in interrupted",ProviderText("VK sign-in did not finish. Your current saved game is unchanged. You can try again.","El acceso VK no terminó. Tu partida no cambió. Puedes reintentarlo.","La connexion VK n’a pas abouti. Votre partie est inchangée. Réessayez.","VK-Anmeldung wurde nicht beendet. Dein Spielstand ist unverändert. Versuche es erneut.","Вход через VK не завершён. Текущий прогресс не изменился. Можно повторить попытку."),y,width,12);
            if(pending&&state.phase!="Committing"){
                var cancel=Button(body,"Cancel VK sign in","vk102-cancel",ProviderText("Cancel VK sign-in","Cancelar acceso VK","Annuler la connexion VK","VK-Anmeldung abbrechen","Отменить вход через VK"),0,y,width,42);cancel.interactable=idle&&account.ready;y+=50;
            }
            var check=Button(body,"Check VK sign in","vk102-check",ProviderText("Check VK status","Comprobar VK","Vérifier VK","VK-Status prüfen","Проверить статус VK"),0,y,width,42);check.interactable=idle&&(account.ready||account.pending);return y+50;
        }
        bool HandleVkSignin102(string action){
            if(action==null||!action.StartsWith("vk102-",StringComparison.Ordinal))return false;
            var signin=VkSigninService;if(signin==null||busy||Managed==null||Managed.Controls.busy||Providers!=null&&Providers.ProviderBusy)return true;
            string approvedTarget=vkShownTarget;
            if(action=="vk102-complete"&&!HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(approvedTarget))return true;
            if(action!="vk102-begin"&&action!="vk102-check"&&action!="vk102-cancel"&&action!="vk102-complete")return true;
            busy=true;int request=++generation;Layout();
            Action<bool,string> done=(ok,why)=>{if(!this||!IsVisible||generation!=request)return;busy=false;serverNotice=ok?"":"serverError";Refresh();Layout();Focus("Account close");};
            if(action=="vk102-begin")signin.BeginVkSignin(done);
            else if(action=="vk102-check")signin.RefreshVkSignin(done);
            else if(action=="vk102-cancel")signin.CancelVkSignin(done);
            else signin.CompleteVkSignin(approvedTarget,true,done);
            return true;
        }
    }
}
