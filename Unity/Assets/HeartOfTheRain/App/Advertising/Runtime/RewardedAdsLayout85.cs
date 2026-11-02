using System;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;

namespace HeartOfTheRain.App.Advertising {
    public static class AdText85 {
        public static string T(string key){int n=GameLocale.Current;string[] text;
            switch(key){
                case "title":text=new[]{"Video reward · 400 coins","Vídeo · 400 monedas","Vidéo · 400 pièces","Video · 400 Münzen","Видео · 400 монет"};break;
                case "policy":text=new[]{"Free rewards: 3 times a day","Premios gratis: 3 veces al día","Récompenses gratuites : 3 fois par jour","Gratis-Belohnungen: 3-mal täglich","Бесплатная награда — 3 раза в день"};break;
                case "unavailable":text=new[]{"Video ads are currently unavailable.","Los vídeos no están disponibles.","Les vidéos sont indisponibles.","Videos sind derzeit nicht verfügbar.","Рекламные видео пока недоступны."};break;
                case "watch":text=new[]{"Watch video","Ver vídeo","Voir la vidéo","Video ansehen","Смотреть видео"};break;
                case "ready":text=new[]{"Optional video. Gameplay is unaffected.","Vídeo opcional. No afecta a la partida.","Vidéo facultative, sans effet sur la partie.","Freiwilliges Video, ohne Einfluss aufs Spiel.","Видео по желанию. Игра не прерывается."};break;
                case "retry":text=new[]{"Check again","Comprobar","Vérifier","Erneut prüfen","Проверить"};break;
                case "pending":text=new[]{"Checking your pending video reward.","Comprobando el premio pendiente.","Vérification de la récompense en attente.","Ausstehende Belohnung wird geprüft.","Проверяем ожидающую награду за видео."};break;
                case "checking":text=new[]{"Checking video rewards…","Comprobando premios de vídeo…","Vérification des récompenses vidéo…","Videobelohnungen werden geprüft…","Проверяем награды за видео…"};break;
                case "checkFailed":text=new[]{"Could not check rewards. Please try again.","No se pudieron comprobar los premios. Inténtalo de nuevo.","Impossible de vérifier les récompenses. Réessayez.","Belohnungen konnten nicht geprüft werden. Erneut versuchen.","Не удалось проверить награды. Попробуйте ещё раз."};break;
                case "loading":text=new[]{"Loading the video…","Cargando el vídeo…","Chargement de la vidéo…","Video wird geladen…","Загружаем видео…"};break;
                case "blocked":text=new[]{"Please finish your current game action first.","Termina primero la acción actual del juego.","Terminez d’abord l’action en cours.","Beende zuerst die aktuelle Spielaktion.","Сначала завершите текущее действие в игре."};break;
                case "cooldownIn":text=new[]{"Next free reward in {0}","Próximo premio gratis en {0}","Prochaine récompense dans {0}","Nächste Gratis-Belohnung in {0}","Следующая награда через {0}"};break;
                case "busy":text=new[]{"Please wait…","Espera…","Veuillez patienter…","Bitte warten…","Подождите…"};break;
                case "failed":text=new[]{"No reward confirmed. Please try again.","Premio no confirmado. Inténtalo de nuevo.","Récompense non confirmée. Réessayez.","Keine Belohnung bestätigt. Erneut versuchen.","Награда не подтверждена. Попробуйте ещё раз."};break;
                case "received":text=new[]{"400 coins added to your wallet.","400 monedas añadidas al monedero.","400 pièces ajoutées au portefeuille.","400 Münzen wurden gutgeschrieben.","На баланс зачислено 400 монет."};break;
                case "limit":text=new[]{"Today's three rewards have been collected.","Ya has recibido los tres premios de hoy.","Les trois récompenses du jour sont reçues.","Die drei Tagesbelohnungen sind abgeholt.","Все три награды за сегодня уже получены."};break;
                case "cooldown":text=new[]{"Next free reward available soon.","Próximo premio gratis disponible pronto.","Prochaine récompense bientôt disponible.","Nächste Gratis-Belohnung bald verfügbar.","Следующая награда скоро появится."};break;
                case "consent":text=new[]{"Optional advertising","Publicidad opcional","Publicité facultative","Freiwillige Werbung","Реклама по желанию"};break;
                case "privacy":text=new[]{"Privacy policy","Privacidad","Confidentialité","Datenschutz","Политика конфиденциальности"};break;
                case "cancel":text=new[]{"Cancel","Cancelar","Annuler","Abbrechen","Отмена"};break;
                case "consentBody":text=new[]{"Yandex processes technical device data to deliver this optional video. We request non-personalized ads. Watch to completion for 400 coins; closing early gives no reward.","Yandex procesa datos técnicos del dispositivo para mostrar este vídeo opcional. Solicitamos anuncios no personalizados. Complétalo para recibir 400 monedas; si lo cierras antes no hay premio.","Yandex traite des données techniques pour diffuser cette vidéo facultative. Nous demandons des publicités non personnalisées. Regardez jusqu'au bout pour 400 pièces ; fermer avant ne donne rien.","Yandex verarbeitet technische Gerätedaten für dieses freiwillige Video. Wir fordern nicht personalisierte Werbung an. Bis zum Ende ansehen für 400 Münzen; vorzeitiges Schließen gibt keine Belohnung.","Яндекс обрабатывает технические данные устройства для показа этого видео. Мы запрашиваем неперсонализированную рекламу. Досмотрите видео, чтобы получить 400 монет. При досрочном закрытии награды нет."};break;
                default:return key;
            }return text[Math.Max(0,Math.Min(4,n))];
        }
    }
    // What the card needs from its host, so the wording rules stay plain data.
    public sealed class AdCardState85 {public bool present,consent,pending,installed,busy,reading,loading,ready,idle,readFailed,rewarded;public string error;public AdStatus85 status;public long now;}
    public sealed class AdShopView85 {
        public string message,button,action;public bool consent;
        public static AdShopView85 From(RewardedShop85 host)=>Build(host?host.Card():new AdCardState85());
        public static AdShopView85 Build(AdCardState85 s){
            var v=new AdShopView85{message=AdText85.T("unavailable"),button=AdText85.T("unavailable"),action="disabled",consent=s.consent};
            if(!s.present)return v;
            // An uninstalled provider cannot open a video. Keep any durable
            // pending claim recoverable, but do not show a transient wait while
            // the unavailable staging offer reconciles in the background.
            if(s.pending&&!s.busy){v.message=AdText85.T("pending");v.button=AdText85.T("retry");v.action="ad:retry";return v;}
            if(!s.installed)return v;
            if(s.busy){v.message=AdText85.T(s.loading?"loading":s.pending&&!s.reading?"pending":"checking");v.button=AdText85.T("busy");return v;}
            if(!s.ready)return v;
            v.button=AdText85.T("retry");v.action="ad:retry";
            if(s.readFailed){v.message=AdText85.T("checkFailed");return v;}
            if(s.status==null){v.message=AdText85.T(s.rewarded?"received":s.error!=null?"failed":"checking");return v;}
            if(s.status.available){v.message=AdText85.T(s.error!=null?"failed":"ready");v.button=AdText85.T("watch");v.action="ad:watch";if(!s.idle){v.message=AdText85.T("blocked");v.action="disabled";}}
            else if(s.status.reason=="daily_limit")v.message=AdText85.T("limit");
            else if(s.status.reason=="cooldown"){long left=s.status.nextEligibleAt-s.now;v.message=s.now>0&&left>0?string.Format(AdText85.T("cooldownIn"),left/60+":"+(left%60).ToString("00")):s.now>0?AdText85.T("checking"):AdText85.T("cooldown");}
            return v;
        }
        public static bool Expired(AdStatus85 status,long now)=>status!=null&&now>0&&(status.reason=="cooldown"&&now>=status.nextEligibleAt||status.reason=="daily_limit"&&now>=status.nextDayAt);
        // The Home plate, from the last status and the server clock. A failed read is never shown as Ready.
        public static string HomePlate(bool visible,bool installed,bool busy,bool pending,bool readFailed,AdStatus85 status,long now,out bool eligible){
            eligible=visible&&status!=null&&status.enabled&&status.available&&!busy&&installed&&!readFailed;
            if(!visible)return "";if(eligible)return "Ready";if(busy||pending||Expired(status,now))return "...";if(readFailed||status==null)return "-";
            return status.reason=="daily_limit"?status.remainingToday+"/"+status.dailyLimit:status.reason=="cooldown"?"Later":"-";
        }
    }
    public static class RewardedAdsLayout85 {
        static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string text="",int size=14,string asset="",string action=""){
            var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,text=text,fontSize=size,asset=asset,color=kind=="text"||kind=="subtext"?"#21465E":"#FFFFFF",action=action,sliced=kind=="sprite"};f.elements.Add(e);return e;
        }
        public static float AddCard(HomeFrame f,float x,float y,float w,AdShopView85 v){
            Add(f,"ad-card","sprite",x,y,w,162,asset:"SP_Mega");
            Add(f,"ad-title","text",x+12,y+10,w-24,26,AdText85.T("title"),19);
            Add(f,"ad-policy","subtext",x+12,y+39,w-24,22,AdText85.T("policy"),12);
            Add(f,"ad-status","subtext",x+12,y+64,w-24,30,v.message,13);
            float bw=Math.Min(w-24,244),bx=x+(w-bw)/2;
            Add(f,"ad-action-art","sprite",bx,y+104,bw,46,asset:v.action=="disabled"?"LB2_ButtonNeutral":"TM_Green");
            var label=Add(f,"ad-action-label","text",bx+8,y+109,bw-16,34,v.button,16);if(v.action!="disabled")label.color="#FFFFFF";
            var hit=Add(f,"ad-action","group",bx,y+104,bw,46,action:v.action);hit.label=v.button;return 174;
        }
        public static void AddConsent(HomeFrame f,float w,float h){
            Add(f,"ad-shade","color",0,0,w,h).color="#061423D9";Add(f,"ad-block","group",0,0,w,h,action:"disabled");
            float cw=Math.Min(w-24,420),ch=Math.Min(h-24,430),x=(w-cw)/2,y=(h-ch)/2;
            Add(f,"ad-consent-panel","sprite",x,y,cw,ch,asset:"LB2_Dialog");
            Add(f,"ad-consent-title","text",x+16,y+16,cw-32,34,AdText85.T("consent"),22);
            Add(f,"ad-consent-body","adparagraph",x+20,y+60,cw-40,ch-244,AdText85.T("consentBody"),17).color="#21465E";
            string[] keys={"privacy","watch","cancel"},actions={"ad:privacy","ad:accept","ad:close"};
            for(int i=0;i<3;i++){float by=y+ch-174+i*53;string id="ad-consent-"+keys[i];
                Add(f,id+"-art","sprite",x+20,by,cw-40,46,asset:i==1?"TM_Green":"LB2_ButtonNeutral");
                var label=Add(f,id+"-label","text",x+28,by+4,cw-56,36,AdText85.T(keys[i]),16);if(i==1)label.color="#FFFFFF";
                Add(f,id,"group",x+20,by,cw-40,46,action:actions[i]).label=AdText85.T(keys[i]);}
        }
    }
}
