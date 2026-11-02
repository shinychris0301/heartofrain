using System.Collections.Generic;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.Profile {
    public static class DailyGiftDesignText {
        static readonly Dictionary<string,string[]> Values=new Dictionary<string,string[]> {
            {"title",new[]{"Daily Gift","Regalo diario","Cadeau du jour","Tagesgeschenk","\u0415\u0436\u0435\u0434\u043d\u0435\u0432\u043d\u044b\u0439 \u043f\u043e\u0434\u0430\u0440\u043e\u043a"}},
            {"intro",new[]{"A little help for your journey","Una peque\u00f1a ayuda para tu aventura","Un petit coup de pouce pour ton aventure","Eine kleine Hilfe f\u00fcr dein Abenteuer","\u041d\u0435\u0431\u043e\u043b\u044c\u0448\u0430\u044f \u043f\u043e\u043c\u043e\u0449\u044c \u0432 \u0442\u0432\u043e\u0451\u043c \u043f\u0440\u0438\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0438"}},
            {"todayGift",new[]{"Today\u2019s gift","Regalo de hoy","Cadeau d\u2019aujourd\u2019hui","Dein Geschenk heute","\u041f\u043e\u0434\u0430\u0440\u043e\u043a \u043d\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f"}},
            {"giftCollected",new[]{"Gift collected!","\u00a1Regalo recogido!","Cadeau r\u00e9cup\u00e9r\u00e9 !","Geschenk erhalten!","\u041f\u043e\u0434\u0430\u0440\u043e\u043a \u043f\u043e\u043b\u0443\u0447\u0435\u043d!"}},
            {"coins",new[]{"Coins","Monedas","Pi\u00e8ces","M\u00fcnzen","\u041c\u043e\u043d\u0435\u0442\u044b"}},
            {"rocket",new[]{"Rocket","Cohete","Fus\u00e9e","Rakete","\u0420\u0430\u043a\u0435\u0442\u0430"}},
            {"bomb",new[]{"Bomb","Bomba","Bombe","Bombe","\u0411\u043e\u043c\u0431\u0430"}},
            {"hammer",new[]{"Hammer","Martillo","Marteau","Hammer","\u041c\u043e\u043b\u043e\u0442"}},
            {"orb",new[]{"Rainbow Orb","Orbe arco\u00edris","Orbe arc-en-ciel","Regenbogenkugel","\u0420\u0430\u0434\u0443\u0436\u043d\u0430\u044f \u0441\u0444\u0435\u0440\u0430"}},
            {"bonusRewards",new[]{"Rainbow Orb + coins","Orbe arco\u00edris + monedas","Orbe arc-en-ciel + pi\u00e8ces","Regenbogenkugel + M\u00fcnzen","\u0420\u0430\u0434\u0443\u0436\u043d\u0430\u044f \u0441\u0444\u0435\u0440\u0430 + \u043c\u043e\u043d\u0435\u0442\u044b"}},
            {"day",new[]{"Day {n}","D\u00eda {n}","Jour {n}","Tag {n}","\u0414\u0435\u043d\u044c {n}"}},
            {"today",new[]{"Today","Hoy","Aujourd\u2019hui","Heute","\u0421\u0435\u0433\u043e\u0434\u043d\u044f"}},
            {"upcoming",new[]{"Upcoming","Pr\u00f3ximamente","\u00c0 venir","Demn\u00e4chst","\u0412\u043f\u0435\u0440\u0435\u0434\u0438"}},
            {"collected",new[]{"Collected","Recogido","R\u00e9cup\u00e9r\u00e9","Erhalten","\u041f\u043e\u043b\u0443\u0447\u0435\u043d\u043e"}},
            {"finalGift",new[]{"Final gift","Regalo final","Dernier cadeau","Letztes Geschenk","\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u043f\u043e\u0434\u0430\u0440\u043e\u043a"}},
            {"sevenGifts",new[]{"Seven little surprises","Siete peque\u00f1as sorpresas","Sept petites surprises","Sieben kleine \u00dcberraschungen","\u0421\u0435\u043c\u044c \u043c\u0430\u043b\u0435\u043d\u044c\u043a\u0438\u0445 \u0441\u044e\u0440\u043f\u0440\u0438\u0437\u043e\u0432"}},
            {"progress",new[]{"Day {n} of 7","D\u00eda {n} de 7","Jour {n} sur 7","Tag {n} von 7","\u0414\u0435\u043d\u044c {n} \u0438\u0437 7"}},
            {"missed",new[]{"Missed a day? Your next gift stays.","\u00bfFaltaste un d\u00eda? Tu pr\u00f3ximo regalo te espera.","Un jour manqu\u00e9 ? Ton prochain cadeau t\u2019attend.","Einen Tag verpasst? Dein n\u00e4chstes Geschenk wartet.","\u041f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u043b \u0434\u0435\u043d\u044c? \u0422\u0432\u043e\u0439 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u043f\u043e\u0434\u0430\u0440\u043e\u043a \u0436\u0434\u0451\u0442."}},
            {"claim",new[]{"Claim Gift","Recoger regalo","R\u00e9cup\u00e9rer","Abholen","\u0417\u0430\u0431\u0440\u0430\u0442\u044c \u043f\u043e\u0434\u0430\u0440\u043e\u043a"}},
            {"claiming",new[]{"Collecting\u2026","Recogiendo\u2026","R\u00e9cup\u00e9ration\u2026","Wird abgeholt\u2026","\u041f\u043e\u043b\u0443\u0447\u0435\u043d\u0438\u0435\u2026"}},
            {"done",new[]{"Done","Listo","Termin\u00e9","Fertig","\u0413\u043e\u0442\u043e\u0432\u043e"}},
            {"retry",new[]{"Try Again","Reintentar","R\u00e9essayer","Erneut versuchen","\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c"}},
            {"close",new[]{"Close","Cerrar","Fermer","Schlie\u00dfen","\u0417\u0430\u043a\u0440\u044b\u0442\u044c"}},
            {"nextGift",new[]{"Come back tomorrow for your next gift.","Vuelve ma\u00f1ana por tu pr\u00f3ximo regalo.","Reviens demain pour ton prochain cadeau.","Komm morgen f\u00fcr dein n\u00e4chstes Geschenk zur\u00fcck.","\u0412\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0439\u0441\u044f \u0437\u0430\u0432\u0442\u0440\u0430 \u0437\u0430 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u043c \u043f\u043e\u0434\u0430\u0440\u043a\u043e\u043c."}},
            {"allCollected",new[]{"All seven gifts collected!","\u00a1Has recogido los siete regalos!","Les sept cadeaux ont \u00e9t\u00e9 r\u00e9cup\u00e9r\u00e9s !","Alle sieben Geschenke erhalten!","\u0412\u0441\u0435 \u0441\u0435\u043c\u044c \u043f\u043e\u0434\u0430\u0440\u043a\u043e\u0432 \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u044b!"}},
            {"freeGift",new[]{"A gift from the village, just for you.","Un regalo del pueblo, solo para ti.","Un cadeau du village, rien que pour toi.","Ein Geschenk aus dem Dorf, nur f\u00fcr dich.","\u041f\u043e\u0434\u0430\u0440\u043e\u043a \u043e\u0442 \u0434\u0435\u0440\u0435\u0432\u043d\u0438 \u0441\u043f\u0435\u0446\u0438\u0430\u043b\u044c\u043d\u043e \u0434\u043b\u044f \u0442\u0435\u0431\u044f."}},
            {"error",new[]{"Couldn\u2019t collect. Your gift is still here.","No se pudo recoger. Tu regalo sigue aqu\u00ed.","\u00c9chec de la r\u00e9cup\u00e9ration. Ton cadeau t\u2019attend.","Abholen fehlgeschlagen. Dein Geschenk wartet.","\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c. \u0422\u0432\u043e\u0439 \u043f\u043e\u0434\u0430\u0440\u043e\u043a \u0436\u0434\u0451\u0442."}},
        };
        public static string T(string key)=>Values.TryGetValue(key,out var values)?values[GameLocale.Current]:DailyGiftText.T(key);
        public static string Day(int n)=>T("day").Replace("{n}",n.ToString());
    }
}
