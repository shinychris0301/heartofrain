using System;
using System.Collections.Generic;
using HeartOfTheRain.App.Localization;

namespace HeartOfTheRain.App.OnlineSocial
{
    public static class OnlineTeamsText82
    {
        // UI copy only. User-authored names, descriptions and messages never
        // pass through this table or a rich-text interpreter.
        static readonly Dictionary<string,string[]> Copy = new Dictionary<string,string[]>(StringComparer.Ordinal) {
            {"Teams",new[]{"Teams","Equipos","Équipes","Teams","Команды"}},
            {"Chat",new[]{"Chat","Chat","Discussion","Chat","Чат"}},
            {"Info",new[]{"Team info","Información","Informations","Teaminfo","О команде"}},
            {"NoTeam",new[]{"Find your team","Encuentra tu equipo","Trouvez votre équipe","Finde dein Team","Найдите свою команду"}},
            {"NoTeamHint",new[]{"Join a team or create one together.","Únete a un equipo o crea uno.","Rejoignez ou créez une équipe.","Tritt einem Team bei oder gründe eins.","Вступите в команду или создайте свою."}},
            {"Create",new[]{"Create team","Crear equipo","Créer une équipe","Team gründen","Создать команду"}},
            {"Join",new[]{"Join","Unirme","Rejoindre","Beitreten","Вступить"}},
            {"JoinTeam",new[]{"Join a team","Unirse a un equipo","Rejoindre une équipe","Team beitreten","Вступить в команду"}},
            {"OnlineRequired",new[]{"Online service required","Se necesita el servicio en línea","Service en ligne requis","Onlinedienst erforderlich","Нужен онлайн-сервис"}},
            {"OnlineSetup",new[]{"Online teams are not connected yet. Creating or joining a team is unavailable.","Los equipos en línea aún no están conectados. No se puede crear ni unirse a un equipo.","Les équipes en ligne ne sont pas encore connectées. La création et l’adhésion sont indisponibles.","Online-Teams sind noch nicht verbunden. Teams können nicht gegründet oder betreten werden.","Онлайн-команды ещё не подключены. Создание команды и вступление пока недоступны."}},
            {"SocialDisabled",new[]{"Online teams are currently disabled.","Los equipos en línea están desactivados.","Les équipes en ligne sont actuellement désactivées.","Online-Teams sind derzeit deaktiviert.","Онлайн-команды сейчас отключены."}},
            {"Full",new[]{"Full","Completo","Complet","Voll","Заполнена"}},
            {"Members",new[]{"Members","Miembros","Membres","Mitglieder","Участники"}},
            {"Leader",new[]{"Leader","Líder","Responsable","Leitung","Лидер"}},
            {"Member",new[]{"Member","Miembro","Membre","Mitglied","Участник"}},
            {"You",new[]{"You","Tú","Vous","Du","Вы"}},
            {"Leave",new[]{"Leave team","Salir del equipo","Quitter l’équipe","Team verlassen","Покинуть команду"}},
            {"Transfer",new[]{"Make leader","Dar liderazgo","Nommer responsable","Leitung geben","Назначить лидером"}},
            {"TransferTitle",new[]{"Transfer leadership?","¿Transferir liderazgo?","Transférer la direction ?","Leitung übertragen?","Передать лидерство?"}},
            {"LeaveTitle",new[]{"Leave this team?","¿Salir del equipo?","Quitter cette équipe ?","Dieses Team verlassen?","Покинуть эту команду?"}},
            {"Message",new[]{"Message","Mensaje","Message","Nachricht","Сообщение"}},
            {"EmptyChat",new[]{"Say hello to your team","Saluda a tu equipo","Saluez votre équipe","Sag deinem Team Hallo","Поздоровайтесь с командой"}},
            {"EmptyTeams",new[]{"No teams yet. Create the first one.","Aún no hay equipos. Crea uno.","Aucune équipe. Créez la première.","Noch keine Teams. Gründe das erste.","Команд пока нет. Создайте первую."}},
            {"Send",new[]{"Send","Enviar","Envoyer","Senden","Отправить"}},
            {"Name",new[]{"Team name","Nombre del equipo","Nom de l’équipe","Teamname","Название команды"}},
            {"Description",new[]{"Description","Descripción","Description","Beschreibung","Описание"}},
            {"Write",new[]{"Write a message…","Escribe un mensaje…","Écrivez un message…","Nachricht schreiben…","Напишите сообщение…"}},
            {"Cancel",new[]{"Cancel","Cancelar","Annuler","Abbrechen","Отмена"}},
            {"Confirm",new[]{"Confirm","Confirmar","Confirmer","Bestätigen","Подтвердить"}},
            {"Retry",new[]{"Try again","Reintentar","Réessayer","Erneut versuchen","Повторить"}},
            {"Loading",new[]{"Loading…","Cargando…","Chargement…","Laden…","Загрузка…"}},
            {"Offline",new[]{"Could not connect. Your last view is kept.","Sin conexión. Conservamos la vista anterior.","Connexion impossible. Vue précédente conservée.","Keine Verbindung. Letzte Ansicht bleibt erhalten.","Нет соединения. Последние данные сохранены."}},
            {"Unavailable",new[]{"Teams are unavailable. Please try again.","Equipos no disponibles. Reinténtalo.","Équipes indisponibles. Réessayez.","Teams nicht verfügbar. Bitte erneut versuchen.","Команды недоступны. Попробуйте ещё раз."}},
            {"Rejected",new[]{"This action is unavailable. Refresh and try again.","Acción no disponible. Actualiza e inténtalo.","Action indisponible. Actualisez et réessayez.","Aktion nicht verfügbar. Bitte aktualisieren.","Действие недоступно. Обновите и повторите."}},
            {"Pending",new[]{"An action needs checking before you continue.","Hay que comprobar una acción pendiente.","Une action doit être vérifiée avant de continuer.","Eine Aktion muss zuerst geprüft werden.","Сначала нужно проверить предыдущее действие."}},
            {"Check",new[]{"Check action","Comprobar","Vérifier","Aktion prüfen","Проверить"}},
            {"Forget",new[]{"Forget retry","Olvidar reintento","Oublier la reprise","Wiederholung verwerfen","Убрать повтор"}},
            {"ForgetTitle",new[]{"Forget this retry?","¿Olvidar este reintento?","Oublier cette reprise ?","Wiederholung verwerfen?","Убрать этот повтор?"}},
            {"ForgetWarning",new[]{"The action may already have completed. This only removes its retry from this device; it cannot undo a sent message or a team change.","La acción puede haberse completado. Solo se elimina su reintento de este dispositivo; no se deshace un mensaje ni un cambio de equipo.","L’action a peut-être déjà abouti. Cela retire seulement sa reprise de cet appareil, sans annuler un message ou un changement d’équipe.","Die Aktion kann bereits abgeschlossen sein. Nur die Wiederholung auf diesem Gerät wird entfernt; Nachrichten und Teamänderungen werden nicht rückgängig gemacht.","Действие уже могло выполниться. Будет убран только его повтор на этом устройстве. Это не отменяет отправленное сообщение или изменение команды."}},
            {"Count",new[]{"{0} / {1} members","{0} / {1} miembros","{0} / {1} membres","{0} / {1} Mitglieder","Участники: {0} / {1}"}},
            {"More",new[]{"More teams","Más equipos","Autres équipes","Weitere Teams","Другие команды"}},
            {"Refresh",new[]{"Refresh","Actualizar","Actualiser","Aktualisieren","Обновить"}},
            {"RefusedShortly",new[]{"Too many actions. Please try again shortly.","Demasiadas acciones. Inténtalo en un momento.","Trop d’actions. Réessayez dans un instant.","Zu viele Aktionen. Bitte gleich erneut versuchen.","Слишком много действий. Попробуйте чуть позже."}},
            {"RefusedTeamFull",new[]{"This team is full.","Este equipo está completo.","Cette équipe est complète.","Dieses Team ist voll.","В этой команде нет свободных мест."}},
            {"RefusedInTeam",new[]{"You are already in a team.","Ya estás en un equipo.","Vous êtes déjà dans une équipe.","Du bist bereits in einem Team.","Вы уже состоите в команде."}},
            {"RefusedHelp",new[]{"This request no longer needs help.","Esta petición ya no necesita ayuda.","Cette demande n’a plus besoin d’aide.","Diese Anfrage braucht keine Hilfe mehr.","Этой просьбе помощь уже не нужна."}},
            {"RefusedLifeRequest",new[]{"You can ask for lives again later.","Podrás pedir vidas más tarde.","Vous pourrez redemander des vies plus tard.","Du kannst später wieder Leben anfragen.","Попросить жизни снова можно будет позже."}},
            {"RefusedLifeClaim",new[]{"These lives can’t be collected yet.","Aún no puedes recoger estas vidas.","Ces vies ne peuvent pas encore être récupérées.","Diese Leben können noch nicht abgeholt werden.","Эти жизни пока нельзя забрать."}},
            {"RefusedFriendLater",new[]{"A friend request can’t be sent right now. Try again later.","Ahora no se puede enviar la solicitud. Inténtalo más tarde.","Impossible d’envoyer la demande pour l’instant. Réessayez plus tard.","Die Anfrage kann gerade nicht gesendet werden. Bitte später erneut versuchen.","Сейчас нельзя отправить заявку в друзья. Попробуйте позже."}},
            {"RefusedFriendLimit",new[]{"The friend limit has been reached.","Se ha alcanzado el límite de amigos.","La limite d’amis est atteinte.","Das Freundeslimit ist erreicht.","Достигнут лимит друзей."}},
            {"RefusedIncoming",new[]{"This player has already sent you a request.","Este jugador ya te ha enviado una solicitud.","Ce joueur vous a déjà envoyé une demande.","Dieser Spieler hat dir bereits eine Anfrage geschickt.","Этот игрок уже отправил вам заявку."}},
            {"RefusedText",new[]{"This text can’t be sent. Please edit it.","Este texto no se puede enviar. Edítalo.","Ce texte ne peut pas être envoyé. Modifiez-le.","Dieser Text kann nicht gesendet werden. Bitte ändern.","Такой текст нельзя отправить. Измените его."}},
        };
        public static string T(string key) { string[] values; return Copy.TryGetValue(key,out values) ? values[GameLocale.ResolveStored(GameLocale.Current)] : GameLocale.T(key); }
        public static string Format(string key,params object[] values) => string.Format(System.Globalization.CultureInfo.InvariantCulture,T(key),values);
        // What a final server refusal means to the player. Anything else keeps the general refresh message.
        public static string Refusal(string code) {
            switch(code) {
                case "rate_limited": case "message_rate_limited": case "team_creation_limited": case "report_rate_limited": return T("RefusedShortly");
                case "team_full": return T("RefusedTeamFull");
                case "already_in_team": return T("RefusedInTeam");
                case "life_help_unavailable": return T("RefusedHelp");
                case "life_request_cooldown": return T("RefusedLifeRequest");
                case "life_claim_unavailable": return T("RefusedLifeClaim");
                case "friend_request_unavailable": return T("RefusedFriendLater");
                case "friend_limit": case "friend_request_limit": return T("RefusedFriendLimit");
                case "incoming_friend_request_exists": return T("RefusedIncoming");
                case "invalid_text": return T("RefusedText");
                default: return T("Rejected");
            }
        }
        public static string Status(SocialPageSession82.ViewStatus status) {
            if(status == null || status.state == SocialViewState82.NotLoaded || status.state == SocialViewState82.Ready) return "";
            if(!string.IsNullOrEmpty(status.reason)) return Refusal(status.reason);
            if(status.state == SocialViewState82.Loading) return T("Loading");
            if(status.state == SocialViewState82.Offline) return T("Offline");
            if(status.state == SocialViewState82.CommitUnknown) return T("Pending");
            if(status.state == SocialViewState82.Rejected) return T("Rejected");
            return T("Unavailable");
        }
    }
}
