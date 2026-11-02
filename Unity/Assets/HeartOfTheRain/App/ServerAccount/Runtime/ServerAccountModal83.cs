using System;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.ServerAccount;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.AccountDesign {
    public sealed partial class AccountModal {
        IManagedServerAccount83 managedObserved;string serverScreen="status",serverNotice="",recoveryPlayer="",recoveryEntry="",serverOwner="";
        InputField recoveryPlayerInput,recoveryCodeInput;
        IManagedServerAccount83 Managed=>service as IManagedServerAccount83;
        void AttachManagedAccount(){
            if(ReferenceEquals(managedObserved,Managed))return;
            if(managedObserved!=null)managedObserved.Changed-=ManagedAccountChanged;managedObserved=Managed;
            if(managedObserved!=null)managedObserved.Changed+=ManagedAccountChanged;
        }
        void ManagedAccountChanged(){
            if(!this||!IsVisible||Managed==null)return;
            string owner=Managed.Controls.playerId;
            if(serverOwner!=owner){ClearServerAccountInput();serverOwner=owner;}
            Refresh();Layout();Focus("Account close");
        }
        void CaptureServerAccountInput(){if(Managed==null)return;if(recoveryPlayerInput)recoveryPlayer=recoveryPlayerInput.text;if(recoveryCodeInput)recoveryEntry=recoveryCodeInput.text;recoveryPlayerInput=null;recoveryCodeInput=null;}
        void ClearServerAccountInput(){
            if(recoveryCodeInput)recoveryCodeInput.text="";if(recoveryPlayerInput)recoveryPlayerInput.text="";recoveryEntry=recoveryPlayer="";recoveryCodeInput=recoveryPlayerInput=null;serverScreen="status";serverNotice="";
        }
        void ReleaseManagedAccount(){ClearServerAccountInput();if(managedObserved!=null)managedObserved.Changed-=ManagedAccountChanged;managedObserved=null;}
        float AccountServerButton(string name,string action,string label,float y,float width,bool enabled=true,bool primary=false){var button=Button(body,name,action,ServerAccountText83.T(label),0,y,width,46,primary);button.interactable=enabled&&!busy&&!Managed.Controls.busy;return y+54;}
        InputField AccountInput(string name,string placeholder,string value,float y,float width,bool secret){
            var root=R(name,body);Place(root,0,y,width,46);var face=root.gameObject.AddComponent<Image>();face.color=new Color(.94f,.97f,1,1);
            var input=root.gameObject.AddComponent<InputField>();var text=Label(root,name+" text","",10,0,width-20,46,14);text.alignment=TextAnchor.MiddleLeft;text.supportRichText=false;
            var hint=Label(root,name+" placeholder",ServerAccountText83.T(placeholder),10,0,width-20,46,12);hint.color=new Color(.32f,.39f,.47f,1);hint.alignment=TextAnchor.MiddleLeft;
            input.textComponent=text;input.placeholder=hint;input.characterLimit=secret?43:32;input.contentType=secret?InputField.ContentType.Password:InputField.ContentType.Alphanumeric;input.lineType=InputField.LineType.SingleLine;input.text=value??"";
            input.interactable=!busy&&!Managed.Controls.busy;return input;
        }
        float LayoutServerAccount(float width,float y){
            var state=Managed.Controls;serverOwner=state.playerId;
            y=Paragraph("Server account explanation",ServerAccountText83.T(state.blocked?state.pending?"serverPending":"serverClosed":"serverIntro"),y,width,14);
            if(!string.IsNullOrEmpty(serverNotice))y=Paragraph("Server account notice",ServerAccountText83.T(serverNotice),y,width,14,true);
            if(serverScreen=="backup"){
                y=Paragraph("Recovery privacy warning",ServerAccountText83.T("serverBackupWarning"),y,width,14);
                if(!state.canCopyRecovery)y=Paragraph("VK recovery backup unavailable",ProviderText("This device does not hold the existing recovery code. Use VK to sign in again, or use a recovery code you previously saved.","Este dispositivo no tiene el código de recuperación. Usa VK o un código guardado anteriormente.","Cet appareil ne possède pas le code de récupération. Utilisez VK ou un code sauvegardé auparavant.","Dieses Gerät kennt den bestehenden Wiederherstellungscode nicht. Nutze VK oder einen zuvor gesicherten Code.","На этом устройстве нет прежнего кода восстановления. Войдите через VK или используйте код, сохранённый ранее."),y,width,12);
                return AccountServerButton("Copy recovery code","server-copy-code","serverCopyCode",y,width,state.ready&&state.canCopyRecovery,true);
            }
            if(serverScreen=="recover"){
                y=Paragraph("Recovery entry explanation",ServerAccountText83.T("serverRecoverIntro"),y,width,14);
                string selected=string.IsNullOrEmpty(recoveryPlayer)?state.recoveryTarget:recoveryPlayer;
                recoveryPlayerInput=AccountInput("Recovery player ID","serverPlayerId",selected,y,width,false);y+=54;
                recoveryCodeInput=AccountInput("Masked recovery code","serverRecoveryCode",recoveryEntry,y,width,true);y+=54;
                return AccountServerButton("Review account switch","server-review-switch","serverNext",y,width,true,true);
            }
            if(serverScreen=="switchConfirm"){
                y=Paragraph("Account switch warning",ServerAccountText83.T(Managed.Controls.canRestartRecovery?"serverAnotherRecoveryWarning":"serverSwitchWarning"),y,width,14);y=Paragraph("Recovery target ID",recoveryPlayer,y,width,12);
                return AccountServerButton("Confirm account switch","server-confirm-switch","serverConfirmSwitch",y,width,true,true);
            }
            if(serverScreen=="deleteWarning"||serverScreen=="deleteConfirm"){
                y=Paragraph("Deletion retention warning",ServerAccountText83.T(serverScreen=="deleteWarning"?"serverDeleteWarning":"serverDeleteConfirm"),y,width,14);
                return AccountServerButton("Confirm deletion","server-delete-next",serverScreen=="deleteWarning"?"serverNext":"serverDeleteNow",y,width,state.ready,true);
            }
            if(serverScreen=="logout"||serverScreen=="fresh"||serverScreen=="forfeit"){
                y=Paragraph("Account confirmation",ServerAccountText83.T(serverScreen=="logout"?"serverLogoutWarning":serverScreen=="fresh"?"serverFreshWarning":"serverForfeitWarning"),y,width,14);
                return AccountServerButton("Confirm server action","server-confirm-action",serverScreen=="logout"?"serverLogout":serverScreen=="fresh"?"serverFresh":"serverEndAttempt",y,width,true,true);
            }
            if(status.ServerSaved)y=Paragraph("Server confirmation time",ServerAccountText83.T("serverSaved")+"\n"+DateTimeOffset.FromUnixTimeSeconds(status.confirmedServerSaveUtc).UtcDateTime.ToString("yyyy-MM-dd HH:mm 'UTC'"),y,width,13);
            y=LayoutProviderAccount(width,y);
            y=AccountServerButton("Refresh server status","server-refresh","serverRefresh",y,width,!state.blocked||state.pending,true);
            if(state.pending&&!PinnedVkResume102)y=AccountServerButton("Resume server account","server-resume",state.needsRecoveryEntry?"serverRecover":"serverRetry",y,width);
            if(state.pending&&state.canRestartRecovery)y=AccountServerButton("Use another recovery code","server-recover","serverAnotherRecovery",y,width);
            if(state.ready){
                y=AccountServerButton("Back up account","server-backup","serverBackup",y,width);
                if(state.blocker!=null)y=Paragraph("Account transition blocker",ServerAccountText83.T("serverBlocked"),y,width,13);
                if(state.activeAttempt)y=AccountServerButton("Forfeit server attempt","server-forfeit","serverEndAttempt",y,width);
                y=AccountServerButton("Recover server account","server-recover","serverRecover",y,width,state.blocker==null);
                y=AccountServerButton("Sign out server account","server-logout","serverLogout",y,width,state.blocker==null);
                y=AccountServerButton("Delete server account","server-delete","serverDelete",y,width,state.blocker==null);
            }else if(state.blocked&&!state.pending){
                y=AccountServerButton("Recover server account","server-recover","serverRecover",y,width);
                y=AccountServerButton("Start new guest","server-fresh","serverFresh",y,width);
            }
            return y;
        }
        void RunServerAccount(Action<Action<bool,string>> operation){
            busy=true;int request=++generation;Layout();
            try{operation((ok,why)=>{
                if(!this||!IsVisible||generation!=request)return;busy=false;serverScreen="status";serverNotice=ok?"":"serverError";Refresh();Layout();Focus("Account close");
            });}catch(Exception){busy=false;serverNotice="serverError";Refresh();Layout();}
        }
        bool HandleServerAccount(string action){
            if(Managed==null||!action.StartsWith("server-",StringComparison.Ordinal))return false;
            if(busy||Managed.Controls.busy)return true;CaptureServerAccountInput();
            switch(action){
                case "server-refresh":RunServerAccount(done=>Managed.Refresh(done));return true;
                case "server-backup":serverScreen="backup";break;
                case "server-copy-code":if(serverScreen!="backup")return true;serverNotice=Managed.CopyRecovery()?"serverCodeCopied":"serverError";break;
                case "server-recover":serverScreen="recover";break;
                case "server-review-switch":
                    if(serverScreen!="recover")return true;
                    if(!IdentityProtocol82.Id(recoveryPlayer)||!IdentityProtocol82.Secret(recoveryEntry)){serverNotice="serverError";break;}serverScreen="switchConfirm";break;
                case "server-confirm-switch":
                    if(serverScreen!="switchConfirm")return true;
                    string target=recoveryPlayer,code=recoveryEntry;ClearServerAccountInput();RunServerAccount(done=>{if(Managed.Controls.canRestartRecovery)Managed.StartAnotherRecovery(target,code,true,done);else Managed.Recover(target,code,true,done);});return true;
                case "server-delete":serverScreen="deleteWarning";break;
                case "server-delete-next":if(serverScreen=="deleteWarning")serverScreen="deleteConfirm";else if(serverScreen=="deleteConfirm")RunServerAccount(done=>Managed.Delete(true,done));break;
                case "server-logout":serverScreen="logout";break;
                case "server-fresh":serverScreen="fresh";break;
                case "server-forfeit":serverScreen="forfeit";break;
                case "server-confirm-action":
                    if(serverScreen=="logout")RunServerAccount(done=>Managed.Logout(true,done));else if(serverScreen=="fresh")RunServerAccount(done=>Managed.StartFresh(true,done));else if(serverScreen=="forfeit")RunServerAccount(done=>Managed.EndAttempt(true,done));return true;
                case "server-resume":if(Managed.Controls.needsRecoveryEntry)serverScreen="recover";else RunServerAccount(done=>Managed.Resume(done));break;
            }
            Refresh();Layout();Focus("Account close");return true;
        }
    }
}
