#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    // Observe the normal Editor first-use callback outside Play, as reviewed94.
    // No Search internals, cache mutation, preference change or error filtering.
    public static class SearchFirstUse101 {
        [Serializable] sealed class Index {public string name=null,type=null;public string[] roots=null;public Options options=null;}
        [Serializable] sealed class Options {public bool disabled=false,types=false,properties=false,dependencies=false;}
        [Serializable] sealed class Report {
            public string status="FAIL_NATIVE_SEARCH_PREPARATION101",utc,unity,error,indexSHA256,settingsBefore,settingsAfter,playerSettingsBefore,playerSettingsAfter;
            public bool indexExistedBefore,stayedOutOfPlay=true,engineGeneratedSearchSettings;public int checks,stableTicks;public long indexBytes;
            public string scope="Actual isolated Unity6.3 normal idle Editor first-use observation. Unity itself creates its default Assets index/settings; this method only reads them and records generated local UserSettings defaults. No Play, product/runtime/device acceptance, cache deletion, manual Search preference write or ignored error.";
            public List<string> errors=new List<string>();
        }
        static Report report;static string output,index,settings,playerSettings,stamp;static double began,stable;
        static string Sha(string path){if(!File.Exists(path))return null;using(var file=File.OpenRead(path))using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(file)).Replace("-","").ToLowerInvariant();}
        static void Need(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static void Preference(){if(File.Exists(settings)&&Regex.IsMatch(File.ReadAllText(settings),"[\"']?indexOnEditorStartup[\"']?\\s*[:=]\\s*false\\b",RegexOptions.IgnoreCase))throw new InvalidOperationException("SearchStartupWasExplicitlyDisabled");}
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};output=Path.Combine(Environment.GetEnvironmentVariable("HOTR_REVIEW101_OUT"),"SearchPreparation101.json");
            try{
                string project=Path.GetFullPath(Path.Combine(Application.dataPath,".."));
                Need(project.Replace('\\','/').EndsWith("/.verification-cache/Review98/Game",StringComparison.Ordinal)&&Application.unityVersion=="6000.3.27f1","Approved exact isolated Editor/project required");
                Need(!EditorApplication.isPlayingOrWillChangePlaymode,"First-use preparation starts outside Play");
                index=Path.Combine(project,"UserSettings/Search.index");settings=Path.Combine(project,"UserSettings/Search.settings");playerSettings=Path.Combine(project,"ProjectSettings/ProjectSettings.asset");
                report.indexExistedBefore=File.Exists(index);report.settingsBefore=Sha(settings);report.playerSettingsBefore=Sha(playerSettings);Preference();
                began=stable=EditorApplication.timeSinceStartup;Application.logMessageReceived+=Log;EditorApplication.update+=Tick;
            }catch(Exception error){report.error=error.ToString();Finish(false);}
        }
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(message+"\n"+stack);}
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-began>120)throw new TimeoutException("NormalSearchStartupDeadline");
            if(report.errors.Count>0)throw new InvalidOperationException("UnfilteredEditorErrorDuringSearchStartup");
            if(EditorApplication.isPlayingOrWillChangePlaymode){report.stayedOutOfPlay=false;throw new InvalidOperationException("PreparationEnteredPlay");}
            if(EditorApplication.isCompiling||EditorApplication.isUpdating||!File.Exists(index)||new FileInfo(index).Length<2){report.stableTicks=0;return;}
            string value=new FileInfo(index).Length+":"+File.GetLastWriteTimeUtc(index).Ticks;
            if(stamp!=value){stamp=value;report.stableTicks=0;stable=EditorApplication.timeSinceStartup;return;}
            report.stableTicks++;if(report.stableTicks<8||EditorApplication.timeSinceStartup-stable<.75)return;
            // Unity6.3 uses one default Assets index and can omit the default
            // type/disabled fields. Validate its actual generated roots/options.
            var document=JsonUtility.FromJson<Index>(File.ReadAllText(index));Need(document!=null&&document.name=="Assets"&&(string.IsNullOrEmpty(document.type)||document.type=="asset")&&document.roots!=null&&Array.IndexOf(document.roots,"Assets")>=0&&document.options!=null&&!document.options.disabled&&document.options.types&&document.options.properties&&document.options.dependencies,"Normal startup created valid enabled default Assets index settings");Preference();
            report.indexBytes=new FileInfo(index).Length;report.indexSHA256=Sha(index);Finish(true);
        }catch(Exception error){report.error=error.ToString();Finish(false);}}
        static void Finish(bool success){
            EditorApplication.update-=Tick;Application.logMessageReceived-=Log;
            report.settingsAfter=settings==null?null:Sha(settings);report.playerSettingsAfter=playerSettings==null?null:Sha(playerSettings);
            report.engineGeneratedSearchSettings=report.settingsBefore!=report.settingsAfter;
            if(report.playerSettingsBefore!=report.playerSettingsAfter){success=false;report.error=(report.error==null?"":report.error+"\n")+"PlayerSettingsChanged";}
            report.status=success&&report.errors.Count==0?"PASS_NATIVE_SEARCH_PREPARATION101":"FAIL_NATIVE_SEARCH_PREPARATION101";
            Directory.CreateDirectory(Path.GetDirectoryName(output));File.WriteAllText(output,JsonUtility.ToJson(report,true),new UTF8Encoding(false));EditorApplication.Exit(report.status.StartsWith("PASS",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif
