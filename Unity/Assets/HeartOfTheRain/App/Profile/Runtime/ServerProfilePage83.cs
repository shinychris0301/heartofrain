using System;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Localization;
using UnityEngine;

namespace HeartOfTheRain.App.Profile {
    public sealed partial class ProfilePage {
        ServerGameSession onlineGateway;ServerProfileController83 onlineProfile;bool onlineAuthorizing;int onlineGeneration;
        bool ServerSelected {get{var host=home?home.GetComponent<PlayerProfileHost>():null;return host&&host.ServerSession;}}
        ServerGameSession ProfileGateway=>home?home.GetComponent<PlayerProfileHost>()?.ServerSession:null;
        ProfileData ViewSnapshot(){
            var value=store==null?new ProfileData():store.Snapshot;
            if(ServerSelected)value.displayName=onlineProfile?.Profile?.displayName??"—";
            return value;
        }
        void OpenServerProfile(){
            var gateway=ProfileGateway;if(!gateway)return;
            if(onlineGateway!=gateway){CloseServerProfile();onlineGateway=gateway;gateway.IdentityChanged+=ServerProfileIdentityChanged;}
            if(onlineAuthorizing||onlineProfile?.Busy==true)return;onlineAuthorizing=true;int ticket=++onlineGeneration;
            gateway.WithAuthenticatedSession((context,why)=>{
                if(!this||ticket!=onlineGeneration||onlineGateway!=gateway)return;onlineAuthorizing=false;
                if(context==null||!gateway.SocialEnabled){OnlineProfileChanged();return;}
                if(onlineProfile==null){
                    IDisposable protectedStore=null;
                    try{var storage=gateway.CreateProtectedSocialStore();protectedStore=storage;var client=gateway.CreateSocialClient(r=>StartCoroutine(r),storage);onlineProfile=new ServerProfileController83(client,protectedStore,()=>gateway?gateway.SessionGeneration:long.MinValue);onlineProfile.Changed+=OnlineProfileChanged;}
                    catch(Exception){protectedStore?.Dispose();OnlineProfileChanged();return;}
                }
                onlineProfile.Refresh();OnlineProfileChanged();
            });
        }
        void OnlineProfileChanged(){
            if(!this)return;
            ProfileChanged?.Invoke(Snapshot);
            if(!IsVisible)return;RefreshText();RenderCollection();
        }
        void PaintServerRename(){
            if(ServerSelected&&renameOpen){bool pending=onlineProfile?.PendingRename==true;nameInput.interactable=!onlineAuthorizing&&onlineProfile?.Busy!=true&&!pending;
                save.interactable=!onlineAuthorizing&&onlineProfile!=null&&!onlineProfile.Busy&&onlineProfile.Profile!=null;
                save.GetComponentInChildren<UnityEngine.UI.Text>().text=pending?OnlineProfileText83.T("Retry"):ProfileText.T("Save");
                if(pending)errorLabel.text=OnlineProfileText83.T("Pending");else if(onlineAuthorizing||onlineProfile?.Busy==true)errorLabel.text=OnlineProfileText83.T("Loading");
                else if((onlineProfile==null||onlineProfile.Error!=null)&&string.IsNullOrEmpty(error))errorLabel.text=ProfileText.T("save-failed");
                while(errorLabel.preferredHeight>errorLabel.rectTransform.rect.height&&errorLabel.fontSize>12)errorLabel.fontSize--;
            }
        }
        void SaveServerName(){
            if(onlineProfile==null||onlineAuthorizing){OpenServerProfile();return;}
            bool started=onlineProfile.Rename(nameInput.text,(ok,why)=>{
                if(!this)return;if(ok&&IsVisible&&renameOpen)CancelRename();else if(IsVisible&&renameOpen){error=why!=null&&why.StartsWith("name-",StringComparison.Ordinal)?why:"save-failed";errorLabel.text=ProfileText.T(error);}
                OnlineProfileChanged();
            });
            if(!started){errorLabel.text=ProfileText.T("save-failed");OpenServerProfile();}
        }
        void ServerProfileIdentityChanged(){onlineGeneration++;onlineAuthorizing=false;onlineProfile?.Dispose();onlineProfile=null;if(IsVisible){CancelRename();RefreshText();RenderCollection();}}
        void CloseServerProfile(){onlineGeneration++;onlineAuthorizing=false;if(onlineGateway)onlineGateway.IdentityChanged-=ServerProfileIdentityChanged;onlineGateway=null;onlineProfile?.Dispose();onlineProfile=null;}
        string ServerStatsKey(){var value=onlineProfile?.Records;return ServerSelected?"|server|"+(value==null?"unavailable":value.completedLevels+"|"+value.attempts.Won+"|"+value.attempts.Lost)+"|"+(onlineProfile?.Error??""):"";}
        string ServerRecordsSummary(){var value=onlineProfile?.Records;if(value==null)return onlineProfile?.Busy==true||onlineAuthorizing?OnlineProfileText83.T("Loading"):OnlineProfileText83.T("Unavailable");return string.Format(OnlineProfileText83.T("Records"),value.completedLevels,value.attempts.Won);}
    }
    public static class OnlineProfileText83 {
        public static string T(string key){string[] values;
            switch(key){
                case "Retry":values=new[]{"Retry","Reintentar","Réessayer","Wiederholen","Повторить"};break;
                case "Pending":values=new[]{"Confirm the previous name change.","Confirma el cambio anterior.","Confirmez le changement précédent.","Vorherige Änderung bestätigen.","Подтвердите предыдущее изменение."};break;
                case "Loading":values=new[]{"Updating…","Actualizando…","Actualisation…","Wird aktualisiert…","Обновление…"};break;
                case "Records":values=new[]{"First clears: {0} · Wins: {1}","Primeras victorias: {0} · Total: {1}","Niveaux terminés : {0} · Victoires : {1}","Erstabschlüsse: {0} · Siege: {1}","Первых побед: {0} · Всего побед: {1}"};break;
                default:values=new[]{"Records unavailable. Reopen to retry.","Registros no disponibles. Vuelve a abrir.","Statistiques indisponibles. Rouvrez.","Statistik nicht verfügbar. Erneut öffnen.","Статистика недоступна. Откройте снова."};break;
            }return values[GameLocale.Current];
        }
    }
}
