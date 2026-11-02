#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.Verification {
    // Identical source in two fresh model-only projects; never import into main.
    public static class SerializationPayload94 {
        [Serializable] sealed class Payload {public string name,file,sha256;public int bytes;}
        [Serializable] sealed class InheritedFixture:Cell {public int sentinel=23;}
        [Serializable] sealed class Report {
            public string status="FAIL_ACTUAL_SERIALIZATION_PAYLOAD94",utc,unity,project,levelSHA256,error;
            public string scope="Actual native Editor model-only diagnostic. Exact authoredL1 seed and explicit swap, raw JsonUtility turn/snapshot/checkpoint plus minimal inherited-field fixtures. No server/worker execution or repinning, UI, device, semantic-parity waiver, performance or release acceptance.";
            public int level,seed,ax,ay,bx,by,firstLegalAx,firstLegalAy,firstLegalBx,firstLegalBy,checks;
            public bool explicitCoordinates,selectedFirstLegal,accepted;
            public List<Payload> payloads=new List<Payload>();
        }
        static string Hash(byte[] bytes){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
        static void Check(Report r,bool value,string reason){r.checks++;if(!value)throw new InvalidOperationException(reason);}
        static void Write(string path,string body){using(var f=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read))using(var w=new StreamWriter(f,new UTF8Encoding(false)))w.Write(body);}
        static void Export(Report r,string output,string name,object value){string text=JsonUtility.ToJson(value);byte[] bytes=Encoding.UTF8.GetBytes(text);Write(Path.Combine(output,name+".json"),text);r.payloads.Add(new Payload{name=name,file=name+".json",sha256=Hash(bytes),bytes=bytes.Length});}
        public static void Run(){
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};string output=null;
            try{
                string project=Path.GetFullPath(Path.Combine(Application.dataPath,"..")).TrimEnd(Path.DirectorySeparatorChar);report.project=project;
                var folder=new DirectoryInfo(project);var model=folder.Parent;var migration=model==null?null:model.Parent;var cache=migration==null?null:migration.Parent;var workspace=cache==null?null:cache.Parent;
                Check(report,(folder.Name=="Baseline2022"||folder.Name=="Candidate6")&&model!=null&&model.Name=="ModelProbe"&&migration!=null&&migration.Name=="Unity6Migration94"&&cache!=null&&cache.Name==".verification-cache"&&workspace!=null&&File.Exists(Path.Combine(workspace.FullName,"AGENTS.md")),"Only exact isolated model-probe projects are permitted");
                string expected=Environment.GetEnvironmentVariable("HOTR_SERIALIZATION94_VERSION");Check(report,report.unity==expected&&(expected=="2022.3.62f3"||expected=="6000.6.6f1"),"Exact native probe engine required");
                Check(report,folder.Name=="Baseline2022"?expected=="2022.3.62f3":expected=="6000.6.6f1","Project and engine must agree");
                string supplied=Environment.GetEnvironmentVariable("HOTR_SERIALIZATION94_OUT");Check(report,!string.IsNullOrEmpty(supplied)&&Path.IsPathRooted(supplied),"Explicit output required");
                output=Path.GetFullPath(supplied);string allowed=Path.Combine(workspace.FullName,"Verification","Evidence","Unity6Migration94","Serialization")+Path.DirectorySeparatorChar;
                Check(report,output.StartsWith(allowed,StringComparison.OrdinalIgnoreCase),"Contained new94 payload output required");Directory.CreateDirectory(output);
                string source=Path.Combine(project,"ProbeInputs","C01_L001.json");byte[] raw=File.ReadAllBytes(source);report.levelSHA256=Hash(raw);
                var level=JsonUtility.FromJson<LevelData>(Encoding.UTF8.GetString(raw));Check(report,level!=null&&level.globalLevel==1,"Authored level1 required");report.level=level.globalLevel;report.seed=Math.Max(1,level.tileSeed);
                Export(report,output,"LevelRoundtrip",level);
                var board=new BoardModel(level,(uint)report.seed);board.Validate();var first=board.LegalSwaps().First();report.firstLegalAx=first[0].x;report.firstLegalAy=first[0].y;report.firstLegalBx=first[1].x;report.firstLegalBy=first[1].y;
                string coordinates=Environment.GetEnvironmentVariable("HOTR_SERIALIZATION94_COORDINATES");int[] move;
                if(!string.IsNullOrEmpty(coordinates)){move=coordinates.Split(',').Select(v=>int.Parse(v,System.Globalization.CultureInfo.InvariantCulture)).ToArray();Check(report,move.Length==4&&move.All(v=>v>=0&&v<=100),"Four bounded explicit coordinates required");report.explicitCoordinates=true;}
                else move=new[]{first[0].x,first[0].y,first[1].x,first[1].y};
                report.ax=move[0];report.ay=move[1];report.bx=move[2];report.by=move[3];report.selectedFirstLegal=move.SequenceEqual(new[]{report.firstLegalAx,report.firstLegalAy,report.firstLegalBx,report.firstLegalBy});
                Export(report,output,"InitialSnapshot",board.Snapshot());Export(report,output,"InitialCheckpoint",board.Checkpoint());
                Export(report,output,"ObservedInitialPiece",board.Pieces.Values.OrderBy(p=>p.id).First().Copy());
                Export(report,output,"PlainPiece",new Piece{x=3,y=4,id=17,color=2,hp=3,power=-1,ownerId=17,family="gem"});
                Export(report,output,"PlainCell",new Cell(3,4));Export(report,output,"InheritedFixture",new InheritedFixture{x=3,y=4,sentinel=23});
                var turn=board.Swap(move[0],move[1],move[2],move[3]);report.accepted=turn.accepted;Check(report,turn.accepted,"Explicit model swap must be accepted");board.Validate();
                Export(report,output,"RawTurn",turn);Export(report,output,"FinalSnapshot",board.Snapshot());Export(report,output,"FinalCheckpoint",board.Checkpoint());
                Export(report,output,"ObservedFinalPiece",board.Pieces.Values.OrderBy(p=>p.id).First().Copy());
                Check(report,report.payloads.Count==11,"Complete raw diagnostic payload set required");report.status="PASS_ACTUAL_SERIALIZATION_PAYLOAD94";
            }catch(Exception error){report.error=error.ToString();}
            if(output!=null)Write(Path.Combine(output,"Native.json"),JsonUtility.ToJson(report,true));else Debug.LogError("Payload probe refused before safe output was available");
            EditorApplication.Exit(report.status=="PASS_ACTUAL_SERIALIZATION_PAYLOAD94"?0:1);
        }
    }
}
#endif
