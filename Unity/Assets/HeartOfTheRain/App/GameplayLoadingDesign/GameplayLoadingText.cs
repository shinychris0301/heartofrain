using System.Collections.Generic;using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.GameplayLoading {public static class GameplayLoadingText {
static readonly Dictionary<string,string[]> Values=new Dictionary<string,string[]> {
{"rain",new[]{"Rain Seeker","Buscador de lluvia","Chercheur de pluie","Regensucher","\u0418\u0441\u043a\u0430\u0442\u0435\u043b\u044c \u0434\u043e\u0436\u0434\u044f"}},
{"orb",new[]{"Rainbow Orb","Orbe arco\u00edris","Orbe arc-en-ciel","Regenbogenkugel","\u0420\u0430\u0434\u0443\u0436\u043d\u0430\u044f \u0441\u0444\u0435\u0440\u0430"}},
{"loading",new[]{"Loading","Cargando","Chargement","Wird geladen","\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430"}},
{"slow",new[]{"Still loading","Cargando todav\u00eda","Chargement en cours","Wird noch geladen","\u0412\u0441\u0451 \u0435\u0449\u0451 \u0437\u0430\u0433\u0440\u0443\u0436\u0430\u0435\u0442\u0441\u044f"}},
{"error",new[]{"Unable to load","No se pudo cargar","Chargement impossible","Laden fehlgeschlagen","\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c"}},
{"detail",new[]{"Please try again.","Vuelve a intentarlo.","Veuillez r\u00e9essayer.","Bitte versuche es erneut.","\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0451 \u0440\u0430\u0437."}},
{"retry",new[]{"Try again","Reintentar","R\u00e9essayer","Erneut versuchen","\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c"}},
{"back",new[]{"Back to level","Volver al nivel","Retour au niveau","Zur\u00fcck zum Level","\u041a \u0432\u044b\u0431\u043e\u0440\u0443 \u0443\u0440\u043e\u0432\u043d\u044f"}},
{"ready",new[]{"Gameplay ready","Partida lista","Partie pr\u00eate","Spiel bereit","\u0418\u0433\u0440\u0430 \u0433\u043e\u0442\u043e\u0432\u0430"}},
{"returned",new[]{"Returned to pre-level","De vuelta a la pantalla previa","Retour \u00e0 la pr\u00e9paration du niveau","Zur\u00fcck zur Levelvorbereitung","\u0412\u043e\u0437\u0432\u0440\u0430\u0442 \u043a \u043f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0435 \u0443\u0440\u043e\u0432\u043d\u044f"}},
{"rainAlt",new[]{"A Rain Seeker flies to a highlighted target tile.","Un buscador de lluvia vuela hacia una ficha objetivo resaltada.","Un chercheur de pluie vole vers une tuile cible en surbrillance.","Ein Regensucher fliegt zu einem markierten Zielfeld.","\u0418\u0441\u043a\u0430\u0442\u0435\u043b\u044c \u0434\u043e\u0436\u0434\u044f \u043b\u0435\u0442\u0438\u0442 \u043a \u0432\u044b\u0434\u0435\u043b\u0435\u043d\u043d\u043e\u0439 \u0446\u0435\u043b\u0435\u0432\u043e\u0439 \u0444\u0438\u0448\u043a\u0435."}},
{"orbAlt",new[]{"A Rainbow Orb selects all three purple tiles in this example.","Un orbe arco\u00edris selecciona las tres fichas moradas de este ejemplo.","Un orbe arc-en-ciel s\u00e9lectionne les trois tuiles violettes de cet exemple.","Eine Regenbogenkugel w\u00e4hlt alle drei violetten Steine in diesem Beispiel aus.","\u0420\u0430\u0434\u0443\u0436\u043d\u0430\u044f \u0441\u0444\u0435\u0440\u0430 \u0432\u044b\u0431\u0438\u0440\u0430\u0435\u0442 \u0432\u0441\u0435 \u0442\u0440\u0438 \u0444\u0438\u043e\u043b\u0435\u0442\u043e\u0432\u044b\u0435 \u0444\u0438\u0448\u043a\u0438 \u0432 \u044d\u0442\u043e\u043c \u043f\u0440\u0438\u043c\u0435\u0440\u0435."}},
};public static string T(string k)=>Values.TryGetValue(k,out var v)?v[GameLocale.Current]:k;
}}
