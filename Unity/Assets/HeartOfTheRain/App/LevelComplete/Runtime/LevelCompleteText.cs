using System.Collections.Generic;using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.LevelComplete {public static class LevelCompleteText {static readonly Dictionary<string,string[]> Entries=new Dictionary<string,string[]> {
{"Level complete!",new string[]{"Level complete!","¡Nivel completado!","Niveau réussi !","Level geschafft!","Уровень пройден!"}},
{"Chapter complete!",new string[]{"Chapter complete!","¡Capítulo completado!","Chapitre terminé !","Kapitel geschafft!","Глава завершена!"}},
{"Rewards earned",new string[]{"Rewards earned","Recompensas ganadas","Récompenses gagnées","Erhaltene Belohnungen","Полученные награды"}},
{"Already cleared",new string[]{"Already cleared","Ya completado","Déjà terminé","Bereits geschafft","Уже пройдено"}},
{"Continue",new string[]{"Continue","Continuar","Continuer","Weiter","Продолжить"}},
{"View story",new string[]{"View story","Ver historia","Voir l'histoire","Geschichte ansehen","Читать историю"}},
{"Home",new string[]{"Home","Inicio","Accueil","Startseite","Главная"}},
{"All targets cleared",new string[]{"All targets cleared","Todos los objetivos eliminados","Tous les objectifs éliminés","Alle Ziele erreicht","Все цели убраны"}},
{"Chapter {0} progress",new string[]{"Chapter {0} progress","Progreso del capítulo {0}","Progression du chapitre {0}","Fortschritt: Kapitel {0}","Прогресс главы {0}"}},
{"Chapter {0} restored",new string[]{"Chapter {0} restored","Capítulo {0} restaurado","Chapitre {0} restauré","Kapitel {0} wiederhergestellt","Глава {0} восстановлена"}},
{"No extra rewards for replays",new string[]{"No extra rewards for replays","Sin recompensas extra al repetir","Rejouer n'offre pas de récompenses","Keine weiteren Belohnungen beim Wiederholen","За повтор нет дополнительных наград"}},
{"Level {0}",new string[]{"Level {0}","Nivel {0}","Niveau {0}","Level {0}","Уровень {0}"}},
{"Next: Level {0}",new string[]{"Next: Level {0}","Siguiente: nivel {0}","Suite : niveau {0}","Weiter: Level {0}","Далее: уровень {0}"}},
{"Coins",new string[]{"Coins","Monedas","Pièces","Münzen","Монеты"}},
{"Stars",new string[]{"Stars","Estrellas","Étoiles","Sterne","Звёзды"}},
};public static string T(string source){string[] values;return Entries.TryGetValue(source,out values)?values[GameLocale.Current]:GameLocale.T(source);}public static string Format(string source,params object[] args)=>string.Format(T(source),args);}}
