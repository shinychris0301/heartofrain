#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.App.PreLevel;

namespace HeartOfTheRain.Verification
{
    public static class ObstacleIntroduction98Verification
    {
        [Serializable] sealed class Report
        {
            public string status="RUNNING",utc,error;
            public int checks,levels,descriptors,localeCases;
            public string scope="Native Unity Editor actual imported campaign/obstacle selection and font/art binding checks. No gameplay interaction, UI render, Android/device or persistence/attempt-settlement certification.";
        }
        static Report report;
        static void Check(bool value,string message){report.checks++;if(!value)throw new InvalidOperationException(message);}
        static string[] Families(ObstacleIntroductionCard[] cards)=>cards.Select(c=>c.Family).ToArray();

        public static int Verify()
        {
            report=new Report{utc=DateTime.UtcNow.ToString("o")};
            var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
            Check(ui&&ui.boards&&ui.regular&&ui.bold,"Actual live UI/board assets and approved fonts exist");
            var levels=ui.boards.levels.Select(a=>JsonUtility.FromJson<LevelData>(a.text)).ToArray();
            Check(levels.Length==50&&levels.Select(l=>l.globalLevel).OrderBy(n=>n).SequenceEqual(Enumerable.Range(1,50)),"Actual referenced campaign has fifty unique ordered level numbers");
            var all=ObstacleIntroductionRules.All;report.levels=levels.Length;report.descriptors=all.Length;
            Check(all.Length==9&&all.Select(c=>c.Family).Distinct().Count()==9,"Nine unique live obstacle families have descriptors");
            foreach(var card in all)
            {
                int first=levels.Where(l=>l.obstacles.Any(o=>o.family==card.Family)).Min(l=>l.globalLevel);
                Check(card.FirstLevel==first,"Runtime index agrees with actual first appearance: "+card.Family);
                var body=ui.boards.bodies.FirstOrDefault(b=>b.key==card.ArtKey);
                Check(body!=null&&(body.texture||!string.IsNullOrEmpty(body.resource)),"Existing approved board obstacle binding exists: "+card.Family);
                for(int locale=0;locale<5;locale++)
                {
                    string title=card.Title(locale),instruction=card.Instruction(locale);report.localeCases++;
                    Check(!string.IsNullOrWhiteSpace(title)&&title.Length<=80&&!title.Any(char.IsControl),"Bounded localized title: "+card.Family+"/"+locale);
                    Check(!string.IsNullOrWhiteSpace(instruction)&&instruction.Length<=180&&!instruction.Any(char.IsControl),"Bounded localized instruction: "+card.Family+"/"+locale);
                    Check(title.All(c=>char.IsWhiteSpace(c)||ui.bold.HasCharacter(c)),"Approved title font covers locale: "+card.Family+"/"+locale);
                    Check(instruction.All(c=>char.IsWhiteSpace(c)||ui.regular.HasCharacter(c)),"Approved body font covers locale: "+card.Family+"/"+locale);
                }
                Check(card.Title(-1)==card.Title(4)&&card.Instruction(5)==card.Instruction(4),"Invalid locale falls back to Russian: "+card.Family);
            }
            foreach(var level in levels)
            {
                string before=JsonUtility.ToJson(level);
                var expected=all.Where(c=>c.Family!="crate"&&c.Family!="moss"&&c.FirstLevel==level.globalLevel).Select(c=>c.Family).ToArray();
                Check(Families(ObstacleIntroductionRules.Plan(level,level.globalLevel-1,false,false)).SequenceEqual(expected),"Exact newcomer queue on actual level "+level.globalLevel);
                Check(Families(ObstacleIntroductionRules.Plan(level,levels,level.globalLevel-1,false,false)).SequenceEqual(expected),"Actual-data-derived first appearance agrees on level "+level.globalLevel);
                Check(Families(ObstacleIntroductionRules.Plan(level,levels.Reverse(),level.globalLevel-1,false,false)).SequenceEqual(expected),"Campaign enumeration order cannot change queue "+level.globalLevel);
                Check(ObstacleIntroductionRules.Plan(level,level.globalLevel,false,false).Length==0,"Completed level replay has no introduction "+level.globalLevel);
                Check(ObstacleIntroductionRules.Plan(level,level.globalLevel-1,true,false).Length==0,"Explicit retry has no introduction "+level.globalLevel);
                Check(ObstacleIntroductionRules.Plan(level,level.globalLevel-1,false,true).Length==0,"Previously started level has no repeated introduction "+level.globalLevel);
                Check(JsonUtility.ToJson(level)==before,"Selection never mutates actual level data "+level.globalLevel);
            }
            Check(ObstacleIntroductionRules.Plan(null,0,false,false).Length==0,"Missing current level does not block launch");
            Check(ObstacleIntroductionRules.Plan(levels[6],null,0,false,false).Length==0,"Missing campaign cannot invent a data-derived introduction");
            Check(ObstacleIntroductionRules.Plan(new LevelData{globalLevel=7,obstacles=new[]{new ObstacleCell{family="crate"}}},0,false,false).Length==0,"Introduction requires actual obstacle occupancy, not scheduled level alone");
            Check(ObstacleIntroductionRules.Plan(new LevelData{globalLevel=36,goals=new[]{new Goal{family="rainlight",count=4}}},0,false,false).Length==0,"Goal-only family does not invent an absent cabinet");
            Check(ObstacleIntroductionRules.Plan(new LevelData{globalLevel=7,obstacles=new[]{new ObstacleCell{family="stone"},new ObstacleCell{family="stone"},new ObstacleCell{family="unknown"},null}},0,false,false).Length==1,"Duplicate cells and unknown families cannot duplicate or invent cards");
            var returned=ObstacleIntroductionRules.All;returned[0]=null;
            Check(ObstacleIntroductionRules.All[0]!=null,"Caller cannot replace registry entries through returned array");
            report.status="PASS_NATIVE_OBSTACLE_INTRODUCTION98_RULES";
            return report.checks;
        }

        public static void Run()
        {
            int exit=0;
            try{Verify();}
            catch(Exception error){exit=1;if(report==null)report=new Report();report.status="FAIL_NATIVE_OBSTACLE_INTRODUCTION98_RULES";report.error=error.Message;}
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW98_OUT")??"../Verification/Evidence/Review98/ObstacleIntroduction";
            Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"ObstacleIntroduction98.json"),JsonUtility.ToJson(report,true));
            Debug.Log(report.status+" checks="+report.checks);EditorApplication.Exit(exit);
        }
    }
}
#endif
