using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace HeartOfTheRain.App.Home
{
    public enum NavigationEvent124 { HomeTeams, HomeLeaderboard, HomeJourney, HomeShop, TeamsShow, TeamsWarmReady, TeamsWarmUnavailable, TeamsReadTimeout, TeamsReflow, TeamsModel, TeamsClear, TeamsRender, TeamsCanvas, TeamsFrameReuse, TeamsView, TeamsLayout, TeamsHash, TeamsViewBase, TeamsViewChat, TeamsViewInvite, TeamsViewLeave, TeamsAssetsReady, TeamsShowPrepare, TeamsShowSession, TeamsShowPump, TeamsPumpSession, TeamsPumpAuthorization, TeamsPumpRefresh, TeamsPumpTick, TeamsPumpChat, TeamsPumpInvite, TeamsBodyMeasure, TeamsLayoutBase, TeamsLayoutInvite, TeamsLayoutLifecycle, TeamsChatHeader, TeamsChatContent, TeamsChatFooter, TeamsTimestamp, TeamsChatViewMail, TeamsChatViewLife, TeamsChatViewAvailability }

    // Small local performance record. Only fixed event codes and durations are
    // accepted: no account IDs, chat text, URLs, tokens, or raw Unity logs.
    public sealed class NavigationDiagnostics124
    {
        public readonly struct Sample {
            public readonly long utc; public readonly NavigationEvent124 eventCode; public readonly int milliseconds;
            public Sample(long utc,NavigationEvent124 eventCode,int milliseconds){this.utc=utc;this.eventCode=eventCode;this.milliseconds=milliseconds;}
        }
        const int Limit=256;
        const string Header="HOTR_NAV_V1";
        readonly string path;
        readonly List<Sample> samples=new List<Sample>();
        static NavigationDiagnostics124 shared;
        public static NavigationDiagnostics124 Shared {
            get {
                if(shared!=null)return shared;
#if UNITY_EDITOR
                string location=Path.GetFullPath("../.verification-cache/NavigationDiagnostics124/navigation.log");
#else
                string location=Path.Combine(Application.persistentDataPath,"Diagnostics","navigation.log");
#endif
                return shared=new NavigationDiagnostics124(location);
            }
        }
        public NavigationDiagnostics124(string path){this.path=path??throw new ArgumentNullException(nameof(path));Load();}
        public Sample[] Read()=>samples.ToArray();
        public void Record(NavigationEvent124 code,int milliseconds){
            // Event IDs are contiguous and append-only. Reflection here runs
            // on every navigation phase and can itself distort frame timing.
            if(code<NavigationEvent124.HomeTeams||code>NavigationEvent124.TeamsChatViewAvailability)return;
            samples.Add(new Sample(DateTimeOffset.UtcNow.ToUnixTimeSeconds(),code,Math.Max(0,Math.Min(60000,milliseconds))));
            if(samples.Count>Limit)samples.RemoveRange(0,samples.Count-Limit);
        }
        public bool Load(){
            try {
                if(!File.Exists(path))return true;
                if(new FileInfo(path).Length>32768)return false;
                var lines=File.ReadAllLines(path,Encoding.UTF8);if(lines.Length==0||lines[0]!=Header)return false;
                var loaded=new List<Sample>();
                for(int i=Math.Max(1,lines.Length-Limit);i<lines.Length;i++){
                    var fields=lines[i].Split('\t');long utc;int code,ms;
                    if(fields.Length!=3||!long.TryParse(fields[0],out utc)||!int.TryParse(fields[1],out code)||!int.TryParse(fields[2],out ms)||!Enum.IsDefined(typeof(NavigationEvent124),code)||ms<0||ms>60000)continue;
                    loaded.Add(new Sample(utc,(NavigationEvent124)code,ms));
                }
                samples.Clear();samples.AddRange(loaded);return true;
            }catch(Exception){return false;}
        }
        public bool Save(){
            try {
                string directory=Path.GetDirectoryName(path);if(string.IsNullOrEmpty(directory))return false;
                Directory.CreateDirectory(directory);
                var text=new StringBuilder(Header).Append('\n');
                foreach(var sample in samples)text.Append(sample.utc).Append('\t').Append((int)sample.eventCode).Append('\t').Append(sample.milliseconds).Append('\n');
                string temporary=path+".tmp";File.WriteAllText(temporary,text.ToString(),new UTF8Encoding(false));
                if(File.Exists(path)){
                    try{File.Replace(temporary,path,null);return true;}
                    catch(IOException){File.Delete(path);}
                    catch(PlatformNotSupportedException){File.Delete(path);}
                }
                File.Move(temporary,path);return true;
            }catch(Exception){return false;}
        }
    }
}
