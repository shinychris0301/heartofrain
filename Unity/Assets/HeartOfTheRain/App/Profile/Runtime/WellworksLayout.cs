using System;
using System.Collections.Generic;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.Profile {
    public static class WellworksText {
        static readonly Dictionary<string,string[]> Text=new Dictionary<string,string[]> {
            {"Complete new levels to reach each milestone.",new[]{"Complete new levels to reach each milestone.","Completa nuevos niveles para alcanzar cada meta.","Terminez de nouveaux niveaux pour atteindre chaque étape.","Schließe neue Level ab, um Meilensteine zu erreichen.","Проходи новые уровни и достигай вех."}},
            {"Your progress stays. No timer.",new[]{"Your progress stays. No timer.","Tu progreso se conserva. Sin límite de tiempo.","Votre progression est conservée. Sans limite de temps.","Dein Fortschritt bleibt. Ohne Zeitlimit.","Прогресс сохраняется. Без таймера."}},
            {"{0} levels",new[]{"{0} levels","{0} niveles","{0} niveaux","{0} Level","{0} уровней"}},
            {"Locked",new[]{"Locked","Bloqueado","Verrouillé","Gesperrt","Закрыто"}},
            {"Rewards coming soon",new[]{"Rewards coming soon","Pronto habrá recompensas","Récompenses à venir","Belohnungen kommen bald","Скоро появятся награды"}}
        };
        public static string T(string key){string[] values;return Text.TryGetValue(key,out values)?values[GameLocale.Current]:DailyGiftText.T(key);}
    }
    public sealed class WellworksView {
        public WellworksSchedule schedule;public PlayerProfile player;public bool enabled,received,error,claimError;
    }
    public static class WellworksLayout {
        public static HomeFrame Build(float width,float height,WellworksView view)=>WellworksDesignLayout.Build(width,height,view);
    }
}
