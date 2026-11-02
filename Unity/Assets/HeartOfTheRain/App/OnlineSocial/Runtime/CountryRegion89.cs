using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using UnityEngine;

namespace HeartOfTheRain.App.OnlineSocial
{
    // Optional country preference. Language and time zone do not establish a
    // player's country. No location permission, GPS or address-book access.
    public static class CountryRegion89
    {
        public const string PreferenceKey="HeartOfTheRain.CountryRegion89";
        static readonly HashSet<string> Codes=new HashSet<string>(("AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW").Split(' '),StringComparer.Ordinal);
        public static string Normalize(string value){value=(value??"").Trim().ToUpperInvariant();return Codes.Contains(value)?value:"";}
        public static string Saved=>Normalize(PlayerPrefs.GetString(PreferenceKey,""));
        public static bool DialogAction(string action)=>action=="cancel-country"||action=="search-country"||action=="country-prev"||action=="country-next"||action=="save-country"||action.StartsWith("country:",StringComparison.Ordinal);
        public static bool Save(string value){value=Normalize(value);if(value.Length==0)return false;PlayerPrefs.SetString(PreferenceKey,value);PlayerPrefs.Save();return true;}
        public static string T(string key){int language=GameLocale.ResolveStored(GameLocale.Current);string[] text;return Copy.TryGetValue(key,out text)?text[language]:GameLocale.T(key);}
        static readonly Dictionary<string,string[]> Copy=new Dictionary<string,string[]>(StringComparer.Ordinal){
            {"Global",new[]{"Global","Global","Monde","Global","Мир"}},
            {"Regional",new[]{"My region","Mi región","Ma région","Meine Region","Мой регион"}},
            {"Country",new[]{"Choose country","Elegir país","Choisir un pays","Land wählen","Выбрать страну"}},
            {"CountryHint",new[]{"Choose your country for regional rankings. No location access is needed.","Elige tu país para la clasificación regional. No usamos tu ubicación.","Choisissez votre pays pour le classement régional. Sans géolocalisation.","Wähle dein Land für regionale Ranglisten. Ohne Standortzugriff.","Выберите страну для регионального рейтинга. Геолокация не используется."}},
            {"CountrySearch",new[]{"Find a country…","Buscar un país…","Chercher un pays…","Land suchen…","Найти страну…"}},
            {"Search",new[]{"Search","Buscar","Chercher","Suchen","Найти"}},
            {"Previous",new[]{"Previous","Anterior","Précédent","Zurück","Назад"}},
            {"Next",new[]{"Next","Siguiente","Suivant","Weiter","Далее"}},
            {"NoCountries",new[]{"No matching countries. Try another name.","No hay países. Prueba otro nombre.","Aucun pays trouvé. Essayez un autre nom.","Keine Länder gefunden. Versuche einen anderen Namen.","Страна не найдена. Попробуйте другое название."}},
            {"SelectCountry",new[]{"Choose your country to see regional rankings.","Elige tu país para ver la clasificación regional.","Choisissez votre pays pour voir le classement régional.","Wähle dein Land für regionale Ranglisten.","Выберите страну для просмотра регионального рейтинга."}},
            {"InvalidCountry",new[]{"Enter a valid two-letter country code.","Introduce un código de país válido de dos letras.","Entrez un code pays valide à deux lettres.","Gib einen gültigen zweistelligen Ländercode ein.","Введите действительный код страны из двух латинских букв."}},
            {"Save",new[]{"Save","Guardar","Enregistrer","Speichern","Сохранить"}},
            {"Rankings",new[]{"Rankings","Clasificación","Classements","Ranglisten","Рейтинг"}},
            {"Teams",new[]{"Teams","Equipos","Équipes","Teams","Команды"}},
            {"EmptyTeams",new[]{"No opted-in teams in this ranking yet.","Aún no hay equipos públicos en esta clasificación.","Aucune équipe publique dans ce classement.","Noch keine öffentlichen Teams in dieser Rangliste.","В этом рейтинге пока нет открытых команд."}},
            {"TeamScore",new[]{"{0} clears · {1} ranked members","{0} niveles · {1} miembros","{0} niveaux · {1} membres","{0} Abschlüsse · {1} Mitglieder","{0} уровней · {1} участников в рейтинге"}},
            {"TeamCountryHint",new[]{"Team region follows the leader's selected country. Scores include opted-in members' verified clears.","La región sigue el país del líder. Puntúan los niveles verificados de miembros públicos.","La région suit le pays du chef. Scores des niveaux vérifiés des membres publics.","Teamregion nach dem Land der Leitung. Verifizierte Abschlüsse öffentlicher Mitglieder zählen.","Регион команды определяется страной лидера. Учитываются подтверждённые уровни участников, открывших свой рейтинг."}}
        };
        static readonly Dictionary<string,string[]> CountryNames=new Dictionary<string,string[]>(StringComparer.Ordinal){
            {"RU",new[]{"Russia","Rusia","Russie","Russland","Россия"}},
            {"US",new[]{"United States","Estados Unidos","États-Unis","Vereinigte Staaten","США"}},
            {"GB",new[]{"United Kingdom","Reino Unido","Royaume-Uni","Vereinigtes Königreich","Великобритания"}},
            {"DE",new[]{"Germany","Alemania","Allemagne","Deutschland","Германия"}},
            {"FR",new[]{"France","Francia","France","Frankreich","Франция"}},
            {"ES",new[]{"Spain","España","Espagne","Spanien","Испания"}},
            {"KZ",new[]{"Kazakhstan","Kazajistán","Kazakhstan","Kasachstan","Казахстан"}},
            {"BY",new[]{"Belarus","Bielorrusia","Biélorussie","Belarus","Беларусь"}},
            {"CA",new[]{"Canada","Canadá","Canada","Kanada","Канада"}},
            {"AU",new[]{"Australia","Australia","Australie","Australien","Австралия"}},
            {"BR",new[]{"Brazil","Brasil","Brésil","Brasilien","Бразилия"}},
            {"UA",new[]{"Ukraine","Ucrania","Ukraine","Ukraine","Украина"}}
        };
        static readonly Dictionary<string,string> EnglishNames=Codes.ToDictionary(code=>code,code=>{try{return new RegionInfo(code).EnglishName;}catch(ArgumentException){return code;}},StringComparer.Ordinal);
        public static string CountryName(string code){code=Normalize(code);if(code.Length==0)return T("Country");string[] names;return CountryNames.TryGetValue(code,out names)?names[GameLocale.ResolveStored(GameLocale.Current)]:EnglishNames[code];}
        public static string[] Countries(string query=""){
            query=(query??"").Trim();var preferred=new[]{"RU","US","GB","DE","FR","ES","KZ","BY","CA","AU","BR","UA"};
            return Codes.Where(code=>query.Length==0||code.Equals(query,StringComparison.OrdinalIgnoreCase)||EnglishNames[code].IndexOf(query,StringComparison.OrdinalIgnoreCase)>=0||CountryName(code).IndexOf(query,StringComparison.OrdinalIgnoreCase)>=0)
                .OrderBy(code=>Array.IndexOf(preferred,code)<0?int.MaxValue:Array.IndexOf(preferred,code)).ThenBy(code=>CountryName(code),StringComparer.OrdinalIgnoreCase).ThenBy(code=>code,StringComparer.Ordinal).ToArray();
        }
        public static string ScopeLabel(string country)=>Normalize(country).Length>0?CountryName(country):T("Regional");
        internal static float Controls(HomeFrame f,float x,float y,float width,bool local,string country,bool enabled,string prefix="region"){
            if(Normalize(country).Length>0){
                float half=(width-6)/2;
                OnlineTeamsLayout82.Button(f,prefix+"-global","scope-global",T("Global"),x,y,half,42,enabled,neutral:local);
                OnlineTeamsLayout82.Button(f,prefix+"-local","scope-regional",ScopeLabel(country),x+half+6,y,half,42,enabled,neutral:!local);
            }else OnlineTeamsLayout82.Button(f,prefix+"-global","scope-global",T("Global"),x,y,width,42,enabled);
            return y+49;
        }
        internal static void Modal(HomeFrame f,float width,float height,bool busy,string error="",string query="",int page=0){
            float w=Math.Min(380,width-24),x=(width-w)/2,h=Math.Min(520,height-24),y=Math.Max(8,(height-h)/2);
            var shade=OnlineTeamsLayout82.Add(f,"country-shade","color",0,0,width,height);shade.color="#061423B8";
            var block=OnlineTeamsLayout82.Add(f,"country-block","group",0,0,width,height);block.action="disabled";
            OnlineTeamsLayout82.Art(f,"country-panel","LB2_Dialog",x,y,w,h);
            OnlineTeamsLayout82.Text(f,"country-title",T("Country"),x+18,y+17,w-36,35,22);
            float hintHeight=OnlineTeamsLayout82.Para(f,"country-hint",error.Length>0?error:T("CountryHint"),x+20,y+58,w-40,12);
            float inputY=Math.Max(110,58+hintHeight+8),rowsY=inputY+59,navigationY=rowsY+213;
            OnlineTeamsLayout82.Input(f,"country-code-input",T("CountrySearch"),x+20,y+inputY,w-126,44);
            OnlineTeamsLayout82.Button(f,"country-search","search-country",T("Search"),x+w-100,y+inputY,80,44,!busy);
            var countries=Countries(query);page=Math.Max(0,Math.Min(page,Math.Max(0,(countries.Length-1)/4)));int start=page*4;
            for(int i=start;i<Math.Min(start+4,countries.Length);i++)OnlineTeamsLayout82.Button(f,"country-option-"+countries[i],"country:"+countries[i],CountryName(countries[i]),x+20,y+rowsY+(i-start)*51,w-40,44,!busy,neutral:true);
            if(countries.Length==0)OnlineTeamsLayout82.Para(f,"country-empty",T("NoCountries"),x+20,y+rowsY+13,w-40,14);
            float half=(w-46)/2;OnlineTeamsLayout82.Button(f,"country-previous","country-prev",T("Previous"),x+20,y+navigationY,half,44,!busy&&page>0,neutral:true);
            OnlineTeamsLayout82.Button(f,"country-next","country-next",T("Next"),x+26+half,y+navigationY,half,44,!busy&&start+4<countries.Length,neutral:true);
            OnlineTeamsLayout82.Button(f,"country-cancel","cancel-country",GameLocale.T("Cancel"),x+20,y+h-60,w-40,44,!busy,neutral:true);
        }
    }
}
