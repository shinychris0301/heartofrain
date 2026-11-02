using System;
using System.Collections.Generic;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.Profile {
    public static class DailyGiftText {
        static readonly Dictionary<string,string[]> Text=new Dictionary<string,string[]> {
            {"Daily Gift",new[]{"Daily Gift","Regalo diario","Cadeau quotidien","Tagesgeschenk","Ежедневный подарок"}},
            {"A little help for your journey",new[]{"A little help for your journey","Una ayuda para tu aventura","Un coup de pouce pour votre aventure","Eine Hilfe für deine Reise","Помощь в твоём путешествии"}},
            {"Day {0}",new[]{"Day {0}","Día {0}","Jour {0}","Tag {0}","День {0}"}},
            {"Claim",new[]{"Claim","Recoger","Récupérer","Abholen","Получить"}},
            {"Claimed",new[]{"Claimed","Recogido","Récupéré","Abgeholt","Получено"}},
            {"Tomorrow",new[]{"Tomorrow","Mañana","Demain","Morgen","Завтра"}},
            {"Come back tomorrow",new[]{"Come back tomorrow","Vuelve mañana","Revenez demain","Komm morgen wieder","Возвращайся завтра"}},
            {"Missed a day? Your next gift stays.",new[]{"Missed a day? Your next gift stays.","Si faltas un día, tu próximo regalo te espera.","Un jour manqué ? Votre prochain cadeau reste.","Ein Tag verpasst? Dein nächstes Geschenk bleibt.","Пропустил день? Следующий подарок тебя ждёт."}},
            {"Preview rewards",new[]{"Preview rewards","Recompensas de prueba","Récompenses de test","Testbelohnungen","Тестовые награды"}},
            {"Daily Gift is unavailable. Please try again later.",new[]{"Daily Gift is unavailable. Please try again later.","El regalo diario no está disponible. Inténtalo más tarde.","Le cadeau quotidien est indisponible. Réessayez plus tard.","Das Tagesgeschenk ist nicht verfügbar. Versuch es später.","Ежедневный подарок недоступен. Попробуй позже."}},
            {"The game could not reach the server. Check your connection and try again.",new[]{"The game could not reach the server. Check your connection and try again.","El juego no pudo conectar con el servidor. Comprueba la conexión e inténtalo de nuevo.","Le jeu n'a pas pu joindre le serveur. Vérifie ta connexion et réessaie.","Das Spiel konnte den Server nicht erreichen. Prüfe deine Verbindung und versuche es erneut.","Не удалось связаться с сервером. Проверь подключение и попробуй ещё раз."}},
            {"Please try again",new[]{"Please try again","Inténtalo de nuevo","Veuillez réessayer","Bitte erneut versuchen","Попробуй ещё раз"}},
            {"Your saved game could not be loaded. Please try again.",new[]{"Your saved game could not be loaded. Please try again.","No se pudo cargar la partida guardada. Inténtalo de nuevo.","Impossible de charger la sauvegarde. Veuillez réessayer.","Dein Spielstand konnte nicht geladen werden. Versuch es erneut.","Не удалось загрузить сохранение. Попробуй ещё раз."}},
            {"Your reward is saved",new[]{"Your reward is saved","Tu recompensa está guardada","Votre récompense est enregistrée","Deine Belohnung ist gespeichert","Награда сохранена"}},
            {"Please wait",new[]{"Please wait","Espera","Veuillez patienter","Bitte warten","Подождите"}},
            {"Checking your gift...",new[]{"Checking your gift...","Comprobando tu regalo...","Vérification du cadeau...","Geschenk wird geprüft...","Проверяем подарок..."}},
            {"Claiming your gift...",new[]{"Claiming your gift...","Recogiendo tu regalo...","Récupération du cadeau...","Geschenk wird abgeholt...","Получаем подарок..."}},
            {"Your gift could not be confirmed. Please try again.",new[]{"Your gift could not be confirmed. Please try again.","No se pudo confirmar tu regalo. Inténtalo de nuevo.","Impossible de confirmer le cadeau. Veuillez réessayer.","Dein Geschenk konnte nicht bestätigt werden. Versuch es erneut.","Не удалось подтвердить подарок. Попробуй ещё раз."}}
        };
        public static string T(string key){string[] values;return Text.TryGetValue(key,out values)?values[GameLocale.Current]:GameLocale.T(key);}
        public static string Day(int n)=>string.Format(T("Day {0}"),n);
    }
    public sealed class DailyGiftView {
        public bool errorDismissible,errorConnection;
        public GiftSchedule schedule;public GiftOffer offer;public int claims;public bool pending,development,received,error,loading,claiming,networkError;
    }
    public static class DailyGiftLayout {
        public static HomeFrame Build(float width,float height,DailyGiftView state)=>DailyGiftDesignLayout.Build(width,height,state);
    }
}
