using System;using System.Collections.Generic;using System.Linq;
using HeartOfTheRain.App.Home;using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.Profile {
    public static class RainCupText {
        static readonly Dictionary<string,string[]> Text=new Dictionary<string,string[]> {
            {"Practice event · Simulated rivals",new[]{"Practice event · Simulated rivals","Evento de práctica · Rivales simulados","Événement d’entraînement · Rivaux simulés","Übungsevent · Simulierte Gegner","Тренировка · Соперники-боты"}},
            {"One point per new level. Replays do not count.",new[]{"One point per new level. Replays do not count.","Un punto por nivel nuevo. Repetir no cuenta.","Un point par nouveau niveau. Rejouer ne compte pas.","Ein Punkt pro neuem Level. Wiederholungen zählen nicht.","Одно очко за новый уровень. Повторы не считаются."}},
            {"Complete {0} levels to unlock",new[]{"Complete {0} levels to unlock","Completa {0} niveles para desbloquear","Terminez {0} niveaux pour débloquer","Schließe {0} Level zum Freischalten ab","Пройди {0} уровней для открытия"}},
            {"Join to start {0} hours",new[]{"Join to start {0} hours","Únete para iniciar {0} horas","Rejoignez pour commencer {0} heures","Beitreten und {0} Stunden starten","Вступи и начни {0} часов"}},
            {"Join",new[]{"Join","Unirse","Rejoindre","Beitreten","Вступить"}},
            {"Standings",new[]{"Standings","Clasificación","Classement","Rangliste","Места"}},
            {"Rewards",new[]{"Rewards","Premios","Récompenses","Belohnungen","Награды"}},
            {"Simulated {0}",new[]{"Simulated {0}","Simulado {0}","Simulé {0}","Simuliert {0}","Бот {0}"}},
            {"You",new[]{"You","Tú","Vous","Du","Ты"}},
            {"Cup finished",new[]{"Cup finished","Copa terminada","Coupe terminée","Pokal beendet","Кубок завершён"}},
            {"Cup in progress",new[]{"Cup in progress","Copa en curso","Coupe en cours","Pokal läuft","Кубок идёт"}},
            {"Current rank {0}",new[]{"Current rank {0}","Puesto actual {0}","Rang actuel {0}","Aktueller Rang {0}","Текущее место: {0}"}},
            {"Final rank {0}",new[]{"Final rank {0}","Puesto final {0}","Rang final {0}","Endrang {0}","Итоговое место: {0}"}},
            {"New cup",new[]{"New cup","Nueva copa","Nouvelle coupe","Neuer Pokal","Новый кубок"}},
            {"All levels completed",new[]{"All levels completed","Todos los niveles completados","Tous les niveaux terminés","Alle Level abgeschlossen","Все уровни пройдены"}},
            {"Rain Cup is unavailable",new[]{"Rain Cup is unavailable","La copa no está disponible","La coupe est indisponible","Regenpokal nicht verfügbar","Кубок недоступен"}},
            {"Saved progress could not be confirmed. Please try again.",new[]{"Saved progress could not be confirmed. Please try again.","No se pudo confirmar el progreso guardado. Inténtalo de nuevo.","Impossible de confirmer la progression enregistrée. Réessayez.","Gespeicherter Fortschritt konnte nicht bestätigt werden. Versuch es erneut.","Не удалось подтвердить сохранённый прогресс. Попробуй ещё раз."}},
            {"Ties share rank. Rewards stay until claimed.",new[]{"Ties share rank. Rewards stay until claimed.","Los empates comparten puesto. Los premios no caducan.","Les ex æquo partagent le rang. Les récompenses restent.","Bei Gleichstand gleicher Rang. Belohnungen bleiben verfügbar.","При равенстве очков место общее. Награды не сгорают."}}
        };
        public static string T(string key){string[] values;return Text.TryGetValue(key,out values)?values[GameLocale.Current]:DailyGiftText.T(key);}
        public static string Timer(long remaining)=>(remaining/3600).ToString("00")+":"+(remaining%3600/60).ToString("00")+":"+(remaining%60).ToString("00");
    }
    public sealed class RainCupView {public RainCupSnapshot snapshot;public long remaining;public bool error,showPrizes,actionError,received;public string playerName,avatarId;}
    public static class RainCupLayout {
        public static HomeFrame Build(float width,float height,RainCupView v)=>RainCupDesignLayout.Build(width,height,v);
    }
}
