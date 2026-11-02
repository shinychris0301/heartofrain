using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.App.Home;
using L=HeartOfTheRain.App.OnlineSocial.OnlineTeamsLayout82;

namespace HeartOfTheRain.App.OnlineSocial
{
    public static class OnlinePlayersText82 {
        static readonly Dictionary<string,string[]> Words=new Dictionary<string,string[]>(StringComparer.Ordinal){
            {"Unavailable",new[]{"Rankings and friends are unavailable. Please try again.","Clasificaciones y amigos no disponibles. Inténtalo de nuevo.","Classements et amis indisponibles. Réessayez.","Ranglisten und Freunde sind nicht verfügbar. Bitte erneut versuchen.","Рейтинг и друзья недоступны. Попробуйте ещё раз."}},
            {"Offline",new[]{"You're offline. Reconnect and try again.","Sin conexión. Vuelve a conectarte e inténtalo de nuevo.","Vous êtes hors ligne. Reconnectez-vous et réessayez.","Du bist offline. Verbinde dich erneut und versuche es noch einmal.","Нет соединения. Подключитесь и попробуйте ещё раз."}},
            {"Players",new[]{"Players","Jugadores","Joueurs","Spieler","Игроки"}},
            {"Friends",new[]{"Friends","Amigos","Amis","Freunde","Друзья"}},
            {"Requests",new[]{"Requests","Solicitudes","Demandes","Anfragen","Заявки"}},
            {"Find",new[]{"Find player","Buscar jugador","Trouver un joueur","Spieler suchen","Найти игрока"}},
            {"Code",new[]{"Player code","Código de jugador","Code du joueur","Spielercode","Код игрока"}},
            {"YourCode",new[]{"Your code: {0}","Tu código: {0}","Votre code : {0}","Dein Code: {0}","Ваш код: {0}"}},
            {"Cleared",new[]{"{0} levels cleared","{0} niveles completados","{0} niveaux terminés","{0} Level geschafft","Пройдено уровней: {0}"}},
            {"Add",new[]{"Add friend","Añadir amigo","Ajouter","Hinzufügen","Добавить"}},
            {"Remove",new[]{"Remove friend","Eliminar amigo","Retirer l’ami","Freund entfernen","Удалить друга"}},
            {"Accept",new[]{"Accept","Aceptar","Accepter","Annehmen","Принять"}},
            {"Decline",new[]{"Decline","Rechazar","Refuser","Ablehnen","Отклонить"}},
            {"Incoming",new[]{"Incoming request","Solicitud recibida","Demande reçue","Eingehende Anfrage","Входящая заявка"}},
            {"Outgoing",new[]{"Request sent","Solicitud enviada","Demande envoyée","Anfrage gesendet","Заявка отправлена"}},
            {"EmptyFriends",new[]{"Your friends will appear here.","Tus amigos aparecerán aquí.","Vos amis apparaîtront ici.","Hier erscheinen deine Freunde.","Здесь появятся ваши друзья."}},
            {"EmptyRequests",new[]{"No pending requests.","No hay solicitudes pendientes.","Aucune demande en attente.","Keine offenen Anfragen.","Ожидающих заявок нет."}},
            {"EmptyRanks",new[]{"No opted-in rankings yet.","Aún no hay clasificaciones públicas.","Aucun classement public.","Noch keine öffentlichen Ranglisten.","Публичных результатов пока нет."}},
            {"RankingNote",new[]{"Verified completed levels · shared ties","Niveles verificados · empates compartidos","Niveaux vérifiés · égalités partagées","Verifizierte Level · gleicher Rang bei Gleichstand","Проверенные уровни · равные результаты делят место"}},
            {"Block",new[]{"Block","Bloquear","Bloquer","Blockieren","Заблокировать"}},
            {"Report",new[]{"Report","Denunciar","Signaler","Melden","Пожаловаться"}},
            {"ReportTeam",new[]{"Report team","Denunciar equipo","Signaler l’équipe","Team melden","Жалоба на команду"}},
            {"ShowRanking",new[]{"Show my ranking","Mostrar mi clasificación","Afficher mon classement","Meinen Rang anzeigen","Показывать мой результат"}},
            {"HideRanking",new[]{"Hide my ranking","Ocultar mi clasificación","Masquer mon classement","Meinen Rang ausblenden","Скрыть мой результат"}},
            {"ReportReceived",new[]{"Report received for review.","Denuncia recibida para revisión.","Signalement reçu pour examen.","Meldung zur Prüfung erhalten.","Жалоба принята на рассмотрение."}},
            {"ReviewHint",new[]{"Send this report for review?","¿Enviar esta denuncia para revisión?","Envoyer ce signalement pour examen ?","Diese Meldung zur Prüfung senden?","Отправить жалобу на рассмотрение?"}},
            {"Back",new[]{"Back","Volver","Retour","Zurück","Назад"}},
            {"Blocked",new[]{"Blocked","Bloqueados","Bloqués","Blockiert","Блок"}},
            {"Unblock",new[]{"Unblock","Desbloquear","Débloquer","Entsperren","Разблокировать"}},
            {"EmptyBlocks",new[]{"No blocked players.","No hay jugadores bloqueados.","Aucun joueur bloqué.","Keine blockierten Spieler.","Нет заблокированных игроков."}},
            {"Older",new[]{"Older messages","Anteriores","Plus anciens","Ältere Nachrichten","Раньше"}},
            {"Latest",new[]{"Latest messages","Más recientes","Plus récents","Neueste Nachrichten","Последние"}},
            {"More",new[]{"More","Más","Suite","Mehr","Ещё"}},
            {"EmptyDirect",new[]{"Start a conversation with your friend.","Empieza a hablar con tu amigo.","Commencez à discuter avec votre ami.","Beginne ein Gespräch mit deinem Freund.","Начните разговор с другом."}},
        };
        public static string T(string key){string[] value;return Words.TryGetValue(key,out value)?value[HeartOfTheRain.App.Localization.GameLocale.ResolveStored(HeartOfTheRain.App.Localization.GameLocale.Current)]:OnlineTeamsText82.T(key);}
        public static string Status(SocialPageSession82.ViewStatus status){
            if(status==null||status.state==SocialViewState82.NotLoaded||status.state==SocialViewState82.Ready||status.state==SocialViewState82.Loading)return "";
            if(status.state==SocialViewState82.Offline)return T("Offline");
            if(status.state==SocialViewState82.Unavailable||status.state==SocialViewState82.Unauthenticated)return T("Unavailable");
            return OnlineTeamsText82.Status(status);
        }
        public static string F(string key,params object[] args)=>string.Format(System.Globalization.CultureInfo.InvariantCulture,T(key),args);
    }
    public sealed class OnlinePlayersView82 {
        public bool rowsReady136;public int tab,offset;public bool regional,teamRanking,countryLoaded,writing;public string regionCode="",countryError="",countryQuery="";public int countryPage;public SocialTeamLeaderboard89 teamRanks;public bool busy,pending,connected,direct,isFriend,ownOptIn,ownProfileLoaded;public string selfId,peerId,peerName="",status="",modal="",modalName="";
        public SocialBlocks82 blocks;public SocialRelationship82 relationship;public SocialLeaderboard82 ranks;public SocialFriends82 friends;public SocialRequests82 requests;public SocialProfile82 profile;public SocialMessages82 chat;
        public SocialRankRefresh115 ranks115;public SocialTeamRanksRefresh115 teamRanks115;public bool selfAvatarAvailable115,searchOpen115,friendsRank115,searchReady115,friendPending115,friendSecondary118,privacyMenuOpen118;public int friendsRankOffset115;public SocialLeaderboard82 friendsRanks115;public SocialPlayerSearch115 searchResults115;public string searchQuery115="",searchCursor115="";
#if UNITY_EDITOR
        // Review-only portraits are absent from every player build.
        public bool editorVisualFixture118;
#endif
    }
    public static class OnlinePlayersLayout82 {
        static string T(string key)=>OnlinePlayersText82.T(key);
        public static OnlineTeamsFrame82 Build(float width,float height,OnlinePlayersView82 v,float topInset=0){
            if(!v.direct)return LeaderboardRefresh115.Build(width,height,v,topInset);
            var r=new OnlineTeamsFrame82{width=Math.Max(320,width),height=Math.Max(568,height)};float w=r.width,h=r.height,cw=Math.Min(w-28,720),cx=(w-cw)/2,dh=MainNavigationLayout.ReservedHeight(w,h);
            foreach(var f in new[]{r.chrome,r.overlay}){f.width=w;f.height=h;}r.content.width=w;
            L.Art(r.chrome,"online-players-background","LB2_Background",0,0,w,h,"",false);L.Text(r.chrome,"online-players-title",v.direct?v.peerName:T("Players"),30,8,w-60,38,27,color:"#FFFFFF");
            float top;
            if(v.direct){L.Button(r.chrome,"online-direct-back","back",T("Back"),cx,55,110,42,!v.busy,neutral:true);top=112;}
            else {
                float fourth=(cw-12)/4;for(int i=0;i<4;i++)L.Button(r.chrome,"online-players-tab-"+i,"tab:"+i,T(new[]{"Players","Friends","Requests","Blocked"}[i]),cx+i*(fourth+4),59,fourth,44,!v.busy,neutral:v.tab!=i);
                if(v.tab==1){L.Input(r.chrome,"online-player-code-input",T("Code"),cx,116,cw-94,46);L.Button(r.chrome,"online-player-find","find",T("Find"),cx+cw-88,116,88,46,!v.busy&&!v.pending);top=195;}
                else if(v.tab==0){float half=(cw-6)/2;
                    L.Button(r.chrome,"online-rank-players","rank-players",T("Players"),cx,112,half,40,!v.busy,neutral:v.teamRanking);
                    L.Button(r.chrome,"online-rank-teams","rank-teams",CountryRegion89.T("Teams"),cx+half+6,112,half,40,!v.busy,neutral:!v.teamRanking);
                    top=CountryRegion89.Controls(r.chrome,cx,160,cw,v.regional,v.regionCode,!v.busy&&!v.pending,"players-region");
                    if(!v.teamRanking){L.Button(r.chrome,"online-ranking-consent","consent",T(v.ownOptIn?"HideRanking":"ShowRanking"),cx,top,cw,38,!v.busy&&!v.pending&&v.ownProfileLoaded,neutral:true);top+=46;}
                    top+=10;
                }
                else top=143;
                if(v.tab!=0)L.Text(r.chrome,"online-player-own-code",OnlinePlayersText82.F("YourCode",v.selfId??""),cx,top-25,cw,20,10,color:"#C8E1EE");
            }
            float statusHeight=v.pending?108:string.IsNullOrEmpty(v.status)?0:72,footer=v.direct?60:0;
            r.viewportY=top;r.viewportHeight=Math.Max(40,h-dh-statusHeight-footer-10-top);float y=4;
            if(v.direct){if(v.chat!=null&&(v.chat.hasOlder||v.chat.hasNewer)){HistoryControls(r.content,"online-direct",cx,ref y,cw,v.busy,v.chat.hasOlder);}foreach(var item in v.chat?.messages??new SocialMessage82[0]){float mh=L.Message(r.content,item,item.authorId==v.selfId,cx,y,cw,item.authorId!=v.selfId);if(item.authorId!=v.selfId)L.Button(r.content,"online-direct-menu-"+item.messageId,"message:"+item.messageId,"⋯",cx+cw-54,y+5,38,28,!v.busy&&!v.pending,neutral:true);y+=mh+8;}if(v.chat!=null&&v.chat.messages.Length==0)y+=L.Para(r.content,"online-direct-empty",T("EmptyDirect"),cx+8,y+15,cw-16,17,color:"#E7F6FC")+40;L.Button(r.chrome,"online-direct-compose","compose",T("Message"),cx,h-dh-statusHeight-54,cw,48,!v.busy&&!v.pending);}
            else if(v.tab==0&&v.regional&&CountryRegion89.Normalize(v.regionCode).Length==0){y+=L.Para(r.content,"online-country-required",(v.countryLoaded?CountryRegion89.T("SelectCountry"):T("Unavailable")),cx+8,y+15,cw-16,16,color:"#E7F6FC")+35;}
            else if(v.tab==0&&v.teamRanking){TeamRankingContent(r.content,v.teamRanks,v.regional,v.regionCode,cx,ref y,cw,v.busy);}
            else if(v.tab==0){foreach(var p in (v.ranks!=null&&(!v.regional||v.ranks.regionCode==v.regionCode)?v.ranks.entries:null)??new SocialRank82[0]){string id="online-rank-"+p.playerId;L.Art(r.content,id+"-base",p.playerId==v.selfId?"LB2_RowSelf":p.rank==1?"LB2_RowTop":"LB2_Row",cx,y,cw,87);if(p.rank<=3){L.Art(r.content,id+"-medal","LB2_Medal"+p.rank,cx+9,y+26,29,32,"",false);L.Text(r.content,id+"-rank",p.rank.ToString(System.Globalization.CultureInfo.InvariantCulture),cx+9,y+26,29,32,17,color:p.rank==1?"#805820":"#49677D");}else L.Text(r.content,id+"-rank",p.rank.ToString(System.Globalization.CultureInfo.InvariantCulture),cx+5,y+25,38,30,17);L.Text(r.content,id+"-name",p.playerId==v.selfId?T("You"):p.displayName,cx+51,y+10,cw-65,26,18,left:true);L.Text(r.content,id+"-score",OnlinePlayersText82.F("Cleared",p.score),cx+51,y+44,cw-65,22,12,left:true);var hit=L.Add(r.content,id,"group",cx,y,cw,87);hit.action="player:"+p.playerId;hit.label=p.displayName;y+=96;}if(v.ranks!=null&&v.ranks.entries.Length==0)y+=L.Para(r.content,"online-ranks-empty",T("EmptyRanks"),cx+8,y+15,cw-16,17,color:"#E7F6FC")+40;if(v.ranks!=null&&v.ranks.hasMore){L.Button(r.content,"online-ranks-more","more-ranks",T("More"),cx,y,cw,44,!v.busy);y+=54;}}
            else if(v.tab==1){foreach(var p in v.friends?.friends??new SocialProfile82[0]){string id="online-friend-"+p.playerId;L.Art(r.content,id+"-base","LB2_Row",cx,y,cw,86);L.Text(r.content,id+"-name",p.displayName,cx+13,y+10,cw-116,25,18,left:true);L.Text(r.content,id+"-score",OnlinePlayersText82.F("Cleared",p.completedLevels),cx+13,y+44,cw-116,22,11,left:true);L.Button(r.content,id+"-message","direct:"+p.playerId,T("Message"),cx+cw-101,y+22,89,45,!v.busy&&!v.pending);var hit=L.Add(r.content,id,"group",cx,y,cw-108,86);hit.action="player:"+p.playerId;hit.label=p.displayName;y+=95;}if(v.friends!=null&&v.friends.friends.Length==0)y+=L.Para(r.content,"online-friends-empty",T("EmptyFriends"),cx+8,y+15,cw-16,17,color:"#E7F6FC")+40;if(v.friends?.hasMore==true){L.Button(r.content,"online-friends-more","more-friends",T("More"),cx,y,cw,44,!v.busy);y+=54;}}
            else if(v.tab==2) {foreach(var p in v.requests?.requests??new SocialFriendRequest82[0]){string id="online-request-"+p.requestId;L.Art(r.content,id+"-base","LB2_Row",cx,y,cw,132);L.Text(r.content,id+"-name",p.profile.displayName,cx+12,y+9,cw-24,25,18,left:true);L.Text(r.content,id+"-direction",T(p.direction=="incoming"?"Incoming":"Outgoing"),cx+12,y+41,cw-24,22,11,left:true);float half=(cw-30)/2;if(p.direction=="incoming"){L.Button(r.content,id+"-accept","accept:"+p.requestId,T("Accept"),cx+12,y+76,half,44,!v.busy&&!v.pending);L.Button(r.content,id+"-decline","decline:"+p.requestId,T("Decline"),cx+18+half,y+76,half,44,!v.busy&&!v.pending,neutral:true);}else L.Button(r.content,id+"-cancel","cancel-request:"+p.requestId,T("Cancel"),cx+12,y+76,cw-24,44,!v.busy&&!v.pending,neutral:true);y+=142;}if(v.requests!=null&&v.requests.requests.Length==0)y+=L.Para(r.content,"online-requests-empty",T("EmptyRequests"),cx+8,y+15,cw-16,17,color:"#E7F6FC")+40;if(v.requests?.hasMore==true){L.Button(r.content,"online-requests-more","more-requests",T("More"),cx,y,cw,44,!v.busy);y+=54;}}
            else {foreach(var p in v.blocks?.blocks??new SocialBlock82[0]){string id="online-block-"+p.playerId;L.Art(r.content,id+"-base","LB2_Row",cx,y,cw,96);L.Text(r.content,id+"-id",p.playerId,cx+12,y+10,cw-24,20,10,left:true);L.Button(r.content,id,"unblock:"+p.playerId,T("Unblock"),cx+12,y+40,cw-24,43,!v.busy&&!v.pending,neutral:true);y+=106;}if(v.blocks!=null&&v.blocks.blocks.Length==0)y+=L.Para(r.content,"online-blocks-empty",T("EmptyBlocks"),cx+8,y+15,cw-16,17,color:"#E7F6FC")+40;if(v.blocks?.hasMore==true){L.Button(r.content,"online-blocks-more","more-blocks",T("More"),cx,y,cw,44,!v.busy);y+=54;}}
            r.content.height=Math.Max(r.viewportHeight,y+5);
            if(statusHeight>0){float sy=h-dh-statusHeight;L.Text(r.chrome,"online-players-status",v.pending?T("Pending"):v.status,cx+4,sy+1,cw-8,v.pending?42:32,11,color:"#E0EFF8");if(v.pending){float third=(cw-12)/3;L.Button(r.chrome,"online-players-check","check",T("Check"),cx,sy+49,third,44,!v.busy);L.Button(r.chrome,"online-players-resume","resume",T("Retry"),cx+third+6,sy+49,third,44,!v.busy);L.Button(r.chrome,"online-players-forget","forget",T("Forget"),cx+2*(third+6),sy+49,third,44,!v.busy,neutral:true);}else L.Button(r.chrome,"online-players-retry","retry",T("Retry"),cx,sy+34,cw,34,!v.busy);}
            MainNavigationLayout.AddDock(r.chrome,w,h,1);if(v.modal.Length>0)Modal(r,v);return r;
        }
        internal static void TeamRankingContent(HomeFrame f,SocialTeamLeaderboard89 ranks,bool regional,string region,float x,ref float y,float width,bool busy){
            y+=L.Para(f,"team-ranking-explanation",CountryRegion89.T("TeamCountryHint"),x+8,y+4,width-16,12,color:"#D5E7F2")+16;
            bool matching=ranks!=null&&ranks.scope==(regional?"regional":"global")&&(!regional||ranks.regionCode==region);
            foreach(var team in matching?ranks.entries:new SocialTeamRank89[0]){
                string id="online-team-rank-"+team.teamId;L.Art(f,id+"-base",team.rank==1?"LB2_RowTop":"LB2_Row",x,y,width,87);
                L.Text(f,id+"-rank",team.rank.ToString(System.Globalization.CultureInfo.InvariantCulture),x+7,y+24,37,31,17);
                L.Text(f,id+"-name",team.name,x+51,y+10,width-64,26,18,left:true);
                L.Text(f,id+"-score",string.Format(System.Globalization.CultureInfo.InvariantCulture,CountryRegion89.T("TeamScore"),team.score,team.memberCount),x+51,y+43,width-64,25,11,left:true);y+=96;
            }
            if(matching&&ranks.entries.Length==0)y+=L.Para(f,"team-ranking-empty",CountryRegion89.T("EmptyTeams"),x+8,y+15,width-16,17,color:"#E7F6FC")+40;
            if(matching&&ranks.hasMore){L.Button(f,"online-team-ranks-more","more-ranks",T("More"),x,y,width,44,!busy);y+=54;}
        }
        internal static void HistoryControls(HomeFrame f,string id,float x,ref float y,float width,bool busy,bool older) {
            float half=(width-6)/2;L.Button(f,id+"-older","older-messages",T("Older"),x,y,half,43,!busy&&older,neutral:true);L.Button(f,id+"-latest","latest-messages",T("Latest"),x+half+6,y,half,43,!busy,neutral:true);y+=53;
        }
        internal static void Modal(OnlineTeamsFrame82 r,OnlinePlayersView82 v){if(v.modal=="country"){CountryRegion89.Modal(r.overlay,r.width,r.height,v.busy,v.countryError,v.countryQuery,v.countryPage);return;}float mw=Math.Min(380,r.width-24),mx=(r.width-mw)/2;bool profile=v.modal=="profile",compose=v.modal=="compose",forget=v.modal=="forget";float mh=profile?385:compose?294:forget?Math.Max(300,145+L.Para(new HomeFrame(),"measure",T("ForgetWarning"),0,0,mw-40,14)):290,my=(r.height-mh)/2;var f=r.overlay;var shade=L.Add(f,"online-player-modal-shade","color",0,0,r.width,r.height);shade.color="#061423B8";var block=L.Add(f,"online-player-modal-block","group",0,0,r.width,r.height);block.action="disabled";block.label=T("Cancel");L.Art(f,"online-player-modal-base","LB2_Dialog",mx,my,mw,mh);
            L.Text(f,"online-player-modal-title",profile?v.profile?.displayName??(!string.IsNullOrEmpty(v.peerName)?v.peerName:T("Players")):T(compose?"Message":forget?"ForgetTitle":v.modal=="report"?"Report":v.modal=="block"?"Block":v.modal=="unblock"?"Unblock":"Remove"),mx+18,my+20,mw-36,36,22,left:true);
            if(profile){L.Text(f,"online-player-modal-code",v.peerId,mx+18,my+65,mw-36,26,11,left:true);if(v.profile!=null)L.Text(f,"online-player-modal-score",OnlinePlayersText82.F("Cleared",v.profile.completedLevels),mx+18,my+99,mw-36,27,15,left:true);float half=(mw-42)/2;string state=v.relationship?.state;bool incoming=state=="Incoming",outgoing=state=="Outgoing";L.Button(f,"online-player-main",v.isFriend?"open-direct":incoming?"accept:"+v.relationship.requestId:outgoing?"cancel-request:"+v.relationship.requestId:"add",T(v.isFriend?"Message":incoming?"Accept":outgoing?"Cancel":"Add"),mx+18,my+147,half,46,!v.busy&&!v.pending&&v.profile!=null&&v.relationship!=null&&v.peerId!=v.selfId);L.Button(f,"online-player-secondary",v.isFriend?"remove":"cancel",T(v.isFriend?"Remove":"Cancel"),mx+24+half,my+147,half,46,!v.busy&&!v.pending,neutral:true);L.Button(f,"online-player-block","block",T("Block"),mx+18,my+208,half,46,!v.busy&&!v.pending&&v.profile!=null&&v.peerId!=v.selfId,neutral:true);L.Button(f,"online-player-report","report-profile",T("Report"),mx+24+half,my+208,half,46,!v.busy&&!v.pending&&v.profile!=null&&v.peerId!=v.selfId,neutral:true);L.Button(f,"online-player-close","cancel",T("Back"),mx+18,my+mh-59,mw-36,44,!v.busy,neutral:true);}
            else {if(compose)L.Input(f,"online-direct-input",T("Write"),mx+16,my+73,mw-32,139);else L.Para(f,"online-player-confirmation",forget?T("ForgetWarning"):v.modal=="report"?T("ReviewHint"):v.modalName,mx+20,my+77,mw-40,14);float half=(mw-42)/2;L.Button(f,"online-player-cancel","cancel",T("Cancel"),mx+18,my+mh-57,half,44,!v.busy,neutral:true);L.Button(f,"online-player-confirm",compose?"send":"confirm",T(compose?"Send":"Confirm"),mx+24+half,my+mh-57,half,44,!v.busy);}
        }
    }
}
