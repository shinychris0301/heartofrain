using System;
using System.Collections.Generic;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.Celebrations
{
    public static class CelebrationText
    {
        static readonly Dictionary<string,string[]> Text=new Dictionary<string,string[]> {
            {"Well done!",new[]{"Well done!","¡Muy bien!","Bravo !","Gut gemacht!","Отлично!"}},
            {"Wonderful!",new[]{"Wonderful!","¡Maravilloso!","Magnifique !","Wunderbar!","Прекрасно!"}},
            {"You did it!",new[]{"You did it!","¡Lo lograste!","Tu as réussi !","Geschafft!","Получилось!"}},
            {"The village well is restored.",new[]{"The village well is restored.","El pozo del pueblo está restaurado.","Le puits du village est restauré.","Der Dorfbrunnen ist wiederhergestellt.","Деревенский колодец восстановлен."}},
            {"You did it! The well is working again.",new[]{"You did it! The well is working again.","¡Lo lograste! El pozo vuelve a funcionar.","Tu as réussi ! Le puits fonctionne à nouveau.","Geschafft! Der Brunnen funktioniert wieder.","Получилось! Колодец снова работает."}},
            {"A messenger arrives: the Heart of Ancient Moscow is faltering.",new[]{"A messenger arrives: the Heart of Ancient Moscow is faltering.","Llega un mensajero: el Corazón de la Antigua Moscú late de forma irregular.","Un messager arrive : le Cœur de l’ancienne Moscou bat irrégulièrement.","Ein Bote trifft ein: Das Herz des Alten Moskaus schlägt unregelmäßig.","Прибывает гонец: Сердце Древней Москвы бьётся неровно."}},
            {"Watch celebration",new[]{"Watch celebration","Ver celebración","Voir la célébration","Feier ansehen","Смотреть празднование"}},
            {"Village restored",new[]{"Village restored","Pueblo restaurado","Village restauré","Dorf wiederhergestellt","Деревня восстановлена"}},
            {"A message from the city",new[]{"A message from the city","Un mensaje de la ciudad","Un message de la ville","Eine Nachricht aus der Stadt","Весть из города"}},
            {"Daria",new[]{"Daria","Daria","Daria","Daria","Дарья"}},
            {"Levels {0}–{1}",new[]{"Levels {0}–{1}","Niveles {0}–{1}","Niveaux {0}–{1}","Level {0}–{1}","Уровни {0}–{1}"}},
            {"Chapter {0} complete",new[]{"Chapter {0} complete","Capítulo {0} completado","Chapitre {0} terminé","Kapitel {0} abgeschlossen","Глава {0} завершена"}},
            {"Skip",new[]{"Skip","Omitir","Passer","Überspringen","Пропустить"}},
            {"Continue",new[]{"Continue","Continuar","Continuer","Weiter","Продолжить"}}
        };
        public static string T(string key) {string[] row;return Text.TryGetValue(key,out row)?row[GameLocale.Current]:GameLocale.T(key);}
        public static string Format(string key,params object[] args) {return string.Format(T(key),args);}
        public static string Praise(int level) {return T(new[]{"Well done!","Wonderful!","You did it!"}[Math.Abs(level%3)]);}
        public static IEnumerable<KeyValuePair<string,string[]>> Entries=>Text;
    }
}
