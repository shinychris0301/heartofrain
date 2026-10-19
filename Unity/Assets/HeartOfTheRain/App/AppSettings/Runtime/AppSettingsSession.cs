using HeartOfTheRain.App.Localization;
using System;
using HeartOfTheRain.App.Settings;
namespace HeartOfTheRain.App.AppSettings
{
    [Serializable] public sealed class AppSettingsLinks
    {
        public string support="",instagram="",youtube="",facebook="",terms="",privacy="";
        public string Get(string key)
        {switch(key){case "support":return support;case "instagram":return instagram;case "youtube":return youtube;case "facebook":return facebook;case "terms":return terms;case "privacy":return privacy;default:return "";}}
        public AppSettingsLinks Copy(){return (AppSettingsLinks)MemberwiseClone();}
        public static bool ValidURL(string value)
        {Uri uri;return !string.IsNullOrWhiteSpace(value)&&value.IndexOfAny(new[]{'\r','\n','\t'})<0&&Uri.TryCreate(value,UriKind.Absolute,out uri)&&uri.Scheme==Uri.UriSchemeHttps&&uri.Host.Length>0&&uri.UserInfo.Length==0;}
    }
    public sealed class AppSettingsSession
    {
        const string LanguageKey=GameLocale.PreferenceKey;
        readonly ISettingsStore store;readonly AppSettingsLinks links;
        int[] starting=new int[4],tools=new int[4];string noticeReturn="main";
        public GameSettingsState Preferences {get;private set;}
        public string Page {get;private set;}="main";
        public string NoticeTitle {get;private set;}="";
        public string NoticeText {get;private set;}="";
        public int ExpandedHelp {get;private set;}=0;
        public int Language {get;private set;}
        public static readonly string[] LanguageNames=GameLocale.Names;
        public AppSettingsSession(ISettingsStore storage,AppSettingsLinks destinations)
        {store=storage??throw new ArgumentNullException(nameof(storage));links=(destinations??new AppSettingsLinks()).Copy();Refresh();}
        void Refresh(){Preferences=new GameSettingsState(store);Language=store.Read(LanguageKey,0);if(!GameLocale.Valid(Language))Language=0;GameLocale.Select(Language);}
        public void Open(int[] startingStock,int[] levelTools)
        {
            if(startingStock==null||startingStock.Length!=4||levelTools==null||levelTools.Length!=4)throw new ArgumentException("Four starting items and four level tools are required.");
            starting=(int[])startingStock.Clone();tools=(int[])levelTools.Clone();for(int i=0;i<4;i++){starting[i]=Math.Max(0,starting[i]);tools[i]=Math.Max(0,tools[i]);}
            Refresh();Page="main";ExpandedHelp=0;NoticeTitle=NoticeText="";
        }
        public int StartingCount(int i){return starting[i];}public int ToolCount(int i){return tools[i];}
        public bool Navigate(string page)
        {if(page!="main"&&page!="inventory"&&page!="language"&&page!="help"&&page!="follow")return false;Page=page;return true;}
        public void Back(){Page=Page=="notice"?noticeReturn:"main";}
        public bool Toggle(string key){return Page=="main"&&Preferences.Toggle(key);}
        public bool ChooseLanguage(int index)
        {
            // Persist the selected interface locale; indices are stable across releases.
            if(Page!="language"||!GameLocale.Valid(index))return false;
            Language=index;GameLocale.Select(index);store.Write(LanguageKey,index);store.Flush();return true;
        }
        public bool ToggleHelp(int index){if(Page!="help"||index<0||index>2)return false;ExpandedHelp=ExpandedHelp==index?-1:index;return true;}
        public bool LinkAvailable(string key){return AppSettingsLinks.ValidURL(links.Get(key));}
        public bool TryLink(string key,out string url)
        {
            url="";string title;
            switch(key){case "support":title="Contact Support";break;case "instagram":title="Instagram";break;case "youtube":title="YouTube";break;case "facebook":title="Facebook";break;case "terms":title="Terms of Service";break;case "privacy":title="Privacy Policy";break;default:return false;}
            if(LinkAvailable(key)){url=links.Get(key);return true;}
            noticeReturn=Page=="notice"?"main":Page;Page="notice";NoticeTitle=title;
            NoticeText=key=="terms"||key=="privacy"?"This document is not available yet.\nPlease check back later.":"This channel is not available yet.\nPlease check back later.";return false;
        }
    }
}
