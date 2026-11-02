using System.Collections.Generic;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.Profile {
    public static class WellworksDesignText {
        static readonly Dictionary<string,string[]> Values=new Dictionary<string,string[]> {
            {"title",new[]{"Wellworks","El pozo","Le puits","Brunnenwerk","\u041a\u043e\u043b\u043e\u0434\u0435\u0446"}},
            {"intro",new[]{"Complete new levels. Collect milestone gifts.","Supera nuevos niveles y recoge tus regalos.","Termine de nouveaux niveaux pour gagner des cadeaux.","Schlie\u00dfe neue Level ab und sammle Geschenke.","\u041f\u0440\u043e\u0445\u043e\u0434\u0438 \u043d\u043e\u0432\u044b\u0435 \u0443\u0440\u043e\u0432\u043d\u0438 \u0438 \u043f\u043e\u043b\u0443\u0447\u0430\u0439 \u043d\u0430\u0433\u0440\u0430\u0434\u044b."}},
            {"completedLevels",new[]{"New levels completed","Nuevos niveles superados","Nouveaux niveaux termin\u00e9s","Neue Level abgeschlossen","\u041f\u0440\u043e\u0439\u0434\u0435\u043d\u043e \u043d\u043e\u0432\u044b\u0445 \u0443\u0440\u043e\u0432\u043d\u0435\u0439"}},
            {"oneReady",new[]{"{n} gift ready to collect","{n} regalo para recoger","{n} cadeau \u00e0 r\u00e9cup\u00e9rer","{n} Geschenk bereit","\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e \u043d\u0430\u0433\u0440\u0430\u0434: {n}"}},
            {"manyReady",new[]{"{n} gifts ready to collect","{n} regalos para recoger","{n} cadeaux \u00e0 r\u00e9cup\u00e9rer","{n} Geschenke bereit","\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e \u043d\u0430\u0433\u0440\u0430\u0434: {n}"}},
            {"next",new[]{"{n} more levels to the next gift","{n} niveles para el pr\u00f3ximo regalo","Encore {n} niveaux avant le prochain cadeau","Noch {n} Level bis zum n\u00e4chsten Geschenk","\u0414\u043e \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u0439 \u043d\u0430\u0433\u0440\u0430\u0434\u044b: {n} \u0443\u0440."}},
            {"complete",new[]{"All rewards collected!","\u00a1Has recogido todas las recompensas!","Toutes les r\u00e9compenses ont \u00e9t\u00e9 r\u00e9cup\u00e9r\u00e9es !","Alle Belohnungen abgeholt!","\u0412\u0441\u0435 \u043d\u0430\u0433\u0440\u0430\u0434\u044b \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u044b!"}},
            {"rewards",new[]{"Milestone rewards","Recompensas","R\u00e9compenses","Belohnungen","\u041d\u0430\u0433\u0440\u0430\u0434\u044b \u0437\u0430 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441"}},
            {"collectionCount",new[]{"{n}/{m} collected","{n}/{m} recogidas","{n}/{m} r\u00e9cup\u00e9r\u00e9es","{n}/{m} abgeholt","\u041f\u043e\u043b\u0443\u0447\u0435\u043d\u043e: {n}/{m}"}},
            {"levels",new[]{"levels","niveles","niveaux","Level","\u0443\u0440\u043e\u0432\u043d\u0435\u0439"}},
            {"levelThreshold",new[]{"{n} levels","{n} niveles","{n} niveaux","{n} Level","{n} \u0443\u0440\u043e\u0432\u043d\u0435\u0439"}},
            {"locked",new[]{"Locked","Bloqueado","Verrouill\u00e9","Gesperrt","\u0417\u0430\u043a\u0440\u044b\u0442\u043e"}},
            {"collected",new[]{"Collected","Recogido","R\u00e9cup\u00e9r\u00e9","Abgeholt","\u041f\u043e\u043b\u0443\u0447\u0435\u043d\u043e"}},
            {"ready",new[]{"Ready","Disponible","Disponible","Bereit","\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e"}},
            {"claim",new[]{"Claim","Recoger","R\u00e9cup\u00e9rer","Abholen","\u0417\u0430\u0431\u0440\u0430\u0442\u044c"}},
            {"close",new[]{"Close","Cerrar","Fermer","Schlie\u00dfen","\u0417\u0430\u043a\u0440\u044b\u0442\u044c"}},
            {"persistent",new[]{"Your progress stays. No timer.","Tu progreso se guarda. Sin l\u00edmite de tiempo.","Ta progression reste. Pas de limite de temps.","Dein Fortschritt bleibt. Kein Zeitlimit.","\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f. \u0411\u0435\u0437 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f \u0432\u0440\u0435\u043c\u0435\u043d\u0438."}},
            {"collectedNotice",new[]{"Reward collected! Your progress stays.","\u00a1Recompensa recogida! Tu progreso se guarda.","R\u00e9compense r\u00e9cup\u00e9r\u00e9e ! Ta progression reste.","Belohnung abgeholt! Dein Fortschritt bleibt.","\u041d\u0430\u0433\u0440\u0430\u0434\u0430 \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u0430! \u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f."}},
            {"error",new[]{"Couldn\u2019t collect. Your reward is still here.","No se pudo recoger. Tu recompensa sigue aqu\u00ed.","\u00c9chec de la r\u00e9cup\u00e9ration. Ta r\u00e9compense t\u2019attend.","Abholen fehlgeschlagen. Deine Belohnung wartet.","\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c. \u0422\u0432\u043e\u044f \u043d\u0430\u0433\u0440\u0430\u0434\u0430 \u0436\u0434\u0451\u0442."}},
            {"coins",new[]{"Coins","Monedas","Pi\u00e8ces","M\u00fcnzen","\u041c\u043e\u043d\u0435\u0442\u044b"}},
            {"rocket",new[]{"Rocket","Cohete","Fus\u00e9e","Rakete","\u0420\u0430\u043a\u0435\u0442\u0430"}},
            {"bomb",new[]{"Bomb","Bomba","Bombe","Bombe","\u0411\u043e\u043c\u0431\u0430"}},
            {"hammer",new[]{"Hammer","Martillo","Marteau","Hammer","\u041c\u043e\u043b\u043e\u0442"}},
            {"orb",new[]{"Rainbow Orb","Orbe arco\u00edris","Orbe arc-en-ciel","Regenbogenkugel","\u0420\u0430\u0434\u0443\u0436\u043d\u0430\u044f \u0441\u0444\u0435\u0440\u0430"}},
            {"seeker",new[]{"Golden Seeker","Buscador dorado","Chercheur dor\u00e9","Goldener Sucher","\u0417\u043e\u043b\u043e\u0442\u043e\u0439 \u0438\u0441\u043a\u0430\u0442\u0435\u043b\u044c"}},
        };
        public static string T(string key)=>Values.TryGetValue(key,out var values)?values[GameLocale.Current]:WellworksText.T(key);
        public static string N(string key,int n)=>T(key).Replace("{n}",n.ToString());
        public static string N(string key,int n,int m)=>N(key,n).Replace("{m}",m.ToString());
    }
}
