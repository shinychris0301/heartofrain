using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
namespace HeartOfTheRain.App.Localization
{
    // Indices are persisted; keep this order stable. v2 never interprets the old Korean placeholder as Russian.
    public static partial class GameLocale
    {
        public const string PreferenceKey="HeartOfTheRain.Settings.v2.language";
        public static readonly string[] Codes={"en","es","fr","de","ru"};
        public static readonly string[] Names={"English","Español","Français","Deutsch","Русский"};
        public static int Current {get;private set;}
        public static int Revision {get;private set;}
        public static bool Valid(int index){return index>=0&&index<Codes.Length;}
        public static bool Select(int index){if(!Valid(index))return false;if(Current!=index){Current=index;Revision++;}return true;}
        static string Normalize(string value){return Regex.Replace(value??"",@"\s+"," ").Trim();}
        static readonly Dictionary<string,string[]> Catalog=CreateCatalog();
        sealed class Pattern {public Regex regex;public string[] text;public int count;}
        static readonly List<Pattern> Patterns=CreatePatterns();
        static List<Pattern> CreatePatterns()
        {
            var result=new List<Pattern>();
            foreach(var pair in Catalog)
            {
                int count=0;string pattern=Regex.Escape(pair.Key);
                while(pattern.Contains(Regex.Escape("{"+count+"}"))){pattern=pattern.Replace(Regex.Escape("{"+count+"}"),"(.+?)");count++;}
                if(count>0)result.Add(new Pattern{regex=new Regex("^"+pattern+"$",RegexOptions.CultureInvariant),text=pair.Value,count=count});
            }
            return result;
        }
        public static string T(string source)
        {
            if(Current==0||string.IsNullOrEmpty(source))return source??"";
            string key=Normalize(source);string[] values;
            if(Catalog.TryGetValue(key,out values))return values[Current];
            foreach(var p in Patterns)
            {
                var m=p.regex.Match(key);if(!m.Success)continue;var args=new object[p.count];
                for(int i=0;i<args.Length;i++)args[i]=m.Groups[i+1].Value;
                return string.Format(CultureInfo.InvariantCulture,p.text[Current],args);
            }
            return source;
        }
        public static string Format(string key,params object[] args){return string.Format(CultureInfo.InvariantCulture,T(key),args);}
        // Names, messages and team descriptions are user content. Call T explicitly only for their surrounding UI.
        public static string Element(string id,string value)
        {
            if(id=="team-name"||id=="confirm-name"||(id.EndsWith("-name",StringComparison.Ordinal)&&(id.StartsWith("player-",StringComparison.Ordinal)||id.StartsWith("friend-",StringComparison.Ordinal)||id.StartsWith("member-",StringComparison.Ordinal)||id.StartsWith("team-",StringComparison.Ordinal)||id.StartsWith("chat-",StringComparison.Ordinal)))||id.EndsWith("-team",StringComparison.Ordinal)||id.EndsWith("-sender",StringComparison.Ordinal)||id.EndsWith("-subject",StringComparison.Ordinal)||id.EndsWith("-summary",StringComparison.Ordinal))return value=="You"?T(value):value;
            return T(value);
        }
        public static bool HasTranslation(string key){return Catalog.ContainsKey(Normalize(key));}
        public static IEnumerable<KeyValuePair<string,string[]>> Entries {get{return Catalog;}}
    }
}
