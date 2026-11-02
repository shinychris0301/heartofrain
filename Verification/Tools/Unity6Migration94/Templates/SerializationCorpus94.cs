#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Collections;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.Verification {
    // Diagnostic only: copy into the two private minimal model projects.
    public static class SerializationCorpus94 {
        [Serializable] public sealed class Payload {public string name,file,sha256,typedSHA256;public int bytes,typedNodes,typedFields,float32Values,float64Values;public string[] traversedTypes;}
        [Serializable] public sealed class Row {
            public string name,levelSHA256;public int level,kind,seed,ax,ay,bx,by,sourceId;public bool accepted;
            public List<Payload> payloads=new List<Payload>();
        }
        [Serializable] public sealed class Report {
            public string status="FAIL_ACTUAL_SERIALIZATION_CORPUS94",utc,unity,project,error;
            public string scope="Actual native model-only350-command raw export: exact LocalCascade50x7 construction and action-selection algorithm, source-bound authored levels. Native hashes and every raw payload remain unmodified. No acceptance waiver, backend execution, full campaign, pixel, device or performance proof.";
            public string typedSignature="Typed94/v1: exact complete public instance serializable fields, inherited included; ordinal DeclaringType.FullName::Name order; type/null tags; length-prefixed UTF8 strings; exact little-endian primitive and IEEE754 float32/64 bytes; list order/count. Static and NonSerialized fields excluded explicitly. Any private serialized field, unsupported value type, dictionary or depth>128 fails. No numeric tolerance or normalization. Raw JSON hashes remain separate and strict.";
            public int checks,typedNegativeControls;public bool explicitBaselineCommands;public List<Row> rows=new List<Row>();
        }
        static string Hash(byte[] bytes){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
        static void Check(Report r,bool value,string reason){r.checks++;if(!value)throw new InvalidOperationException(reason);}
        static void Write(string path,string text){using(var f=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read))using(var w=new StreamWriter(f,new UTF8Encoding(false)))w.Write(text);}
        static void Text(BinaryWriter writer,string text){byte[] bytes=Encoding.UTF8.GetBytes(text);writer.Write(bytes.Length);writer.Write(bytes);}
        static void Typed(BinaryWriter writer,object value,Payload payload,HashSet<string> types,int depth){
            if(depth>128)throw new InvalidOperationException("Typed94 recursion depth exceeded");payload.typedNodes++;
            if(value==null){writer.Write((byte)0);return;}writer.Write((byte)1);var type=value.GetType();Text(writer,type.FullName);types.Add(type.FullName);
            if(type==typeof(string)){Text(writer,(string)value);return;}if(type==typeof(bool)){writer.Write((bool)value);return;}
            if(type==typeof(int)){writer.Write((int)value);return;}if(type==typeof(uint)){writer.Write((uint)value);return;}
            if(type==typeof(long)){writer.Write((long)value);return;}if(type==typeof(ulong)){writer.Write((ulong)value);return;}
            if(type==typeof(short)){writer.Write((short)value);return;}if(type==typeof(ushort)){writer.Write((ushort)value);return;}
            if(type==typeof(byte)){writer.Write((byte)value);return;}if(type==typeof(sbyte)){writer.Write((sbyte)value);return;}
            if(type==typeof(float)){writer.Write((float)value);payload.float32Values++;return;}
            if(type==typeof(double)){writer.Write((double)value);payload.float64Values++;return;}
            if(type.IsEnum){Typed(writer,Convert.ChangeType(value,Enum.GetUnderlyingType(type)),payload,types,depth+1);return;}
            if(value is IDictionary)throw new InvalidOperationException("Typed94 refuses dictionary "+type.FullName);
            if(value is IList){var list=(IList)value;writer.Write(list.Count);foreach(var item in list)Typed(writer,item,payload,types,depth+1);return;}
            if(!type.IsSerializable)throw new InvalidOperationException("Typed94 requires serializable model type "+type.FullName);
            for(var declaring=type;declaring!=null;declaring=declaring.BaseType)foreach(var hidden in declaring.GetFields(BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.DeclaredOnly))
                if(hidden.IsDefined(typeof(SerializeField),false)||hidden.IsDefined(typeof(SerializeReference),false))throw new InvalidOperationException("Typed94 refuses untraversed private serialized field "+hidden.Name);
            var fields=type.GetFields(BindingFlags.Public|BindingFlags.Instance).Where(f=>!f.IsStatic&&!f.IsNotSerialized).OrderBy(f=>f.DeclaringType.FullName+"::"+f.Name,StringComparer.Ordinal).ToArray();
            if(fields.Length==0)throw new InvalidOperationException("Typed94 refuses empty or unsupported model type "+type.FullName);
            writer.Write(fields.Length);foreach(var field in fields){payload.typedFields++;Text(writer,field.DeclaringType.FullName+"::"+field.Name);Text(writer,field.FieldType.FullName);Typed(writer,field.GetValue(value),payload,types,depth+1);}
        }
        static Payload Signature(object value){
            var payload=new Payload();var types=new HashSet<string>(StringComparer.Ordinal);
            using(var buffer=new MemoryStream()){using(var writer=new BinaryWriter(buffer,Encoding.UTF8,true)){Text(writer,"Typed94/v1");Typed(writer,value,payload,types,0);writer.Flush();}payload.typedSHA256=Hash(buffer.ToArray());}
            payload.traversedTypes=types.OrderBy(t=>t,StringComparer.Ordinal).ToArray();return payload;
        }
        static void SignatureControls(Report report){
            Action<object,object,string> different=(a,b,reason)=>{report.typedNegativeControls++;Check(report,Signature(a).typedSHA256!=Signature(b).typedSHA256,"Typed exact-value negative control: "+reason);};
            different(.18f,BitConverter.ToSingle(BitConverter.GetBytes(BitConverter.ToInt32(BitConverter.GetBytes(.18f),0)+1),0),"one IEEE754 float32 ULP");
            different(1d,BitConverter.ToDouble(BitConverter.GetBytes(BitConverter.DoubleToInt64Bits(1d)+1),0),"one IEEE754 float64 ULP");
            different(new Piece{x=1,y=2,id=3},new Piece{x=2,y=2,id=3},"inherited Cell.x");
            different(new[]{1,2},new[]{2,1},"list order");different(null,"","null versus empty");different("a\u0000b","a\u0000c","UTF8 embedded NUL");
            different(1,1u,"integer signedness/type");different(false,true,"Boolean value");
            var a=new BoardStep();var b=new BoardStep();b.playbackTracks=new List<PlaybackTrack>();
            Check(report,Signature(a).typedSHA256==Signature(b).typedSHA256,"Explicit NonSerialized playbackTracks exclusion matches JsonUtility");
        }
        static void Export(Row row,string output,string name,object value){
            string text=JsonUtility.ToJson(value);byte[] bytes=Encoding.UTF8.GetBytes(text);string file=row.name+"_"+name+".json";Write(Path.Combine(output,file),text);
            var payload=Signature(value);payload.name=name;payload.file=file;payload.sha256=Hash(bytes);payload.bytes=bytes.Length;row.payloads.Add(payload);
        }
        public static void Run(){
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};string output=null;
            try{
                string project=Path.GetFullPath(Path.Combine(Application.dataPath,"..")).TrimEnd(Path.DirectorySeparatorChar);report.project=project;
                var folder=new DirectoryInfo(project);var model=folder.Parent;var migration=model==null?null:model.Parent;var cache=migration==null?null:migration.Parent;var workspace=cache==null?null:cache.Parent;
                Check(report,(folder.Name=="Baseline2022"||folder.Name=="Candidate6")&&model!=null&&model.Name=="ModelProbe"&&migration!=null&&migration.Name=="Unity6Migration94"&&cache!=null&&cache.Name==".verification-cache"&&workspace!=null&&File.Exists(Path.Combine(workspace.FullName,"AGENTS.md")),"Only exact isolated model-probe projects permitted");
                string expected=Environment.GetEnvironmentVariable("HOTR_CORPUS94_VERSION");Check(report,report.unity==expected&&(folder.Name=="Baseline2022"?expected=="2022.3.62f3":expected=="6000.6.6f1"),"Exact native engine and project required");
                string supplied=Environment.GetEnvironmentVariable("HOTR_CORPUS94_OUT");Check(report,!string.IsNullOrEmpty(supplied)&&Path.IsPathRooted(supplied),"Explicit output required");output=Path.GetFullPath(supplied);
                string allowed=Path.Combine(workspace.FullName,"Verification","Evidence","Unity6Migration94","SerializationCorpus")+Path.DirectorySeparatorChar;
                Check(report,output.StartsWith(allowed,StringComparison.OrdinalIgnoreCase),"Contained fresh94 corpus output required");Directory.CreateDirectory(output);
                SignatureControls(report);
                string controls=Environment.GetEnvironmentVariable("HOTR_CORPUS94_BASELINE");Report baseline=null;
                if(folder.Name=="Candidate6"){
                    Check(report,!string.IsNullOrEmpty(controls)&&Path.GetFullPath(controls).StartsWith(allowed,StringComparison.OrdinalIgnoreCase),"Actual baseline commands required");
                    baseline=JsonUtility.FromJson<Report>(File.ReadAllText(controls));Check(report,baseline.status=="PASS_ACTUAL_SERIALIZATION_CORPUS94"&&baseline.unity=="2022.3.62f3"&&baseline.rows.Count==350,"Complete actual2022 commands required");report.explicitBaselineCommands=true;
                }
                for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){
                    byte[] authored=File.ReadAllBytes(Path.Combine(project,"ProbeInputs","Corpus94","C01_L"+(level+1).ToString("D3")+".json"));
                    var data=JsonUtility.FromJson<LevelData>(Encoding.UTF8.GetString(authored));Check(report,data!=null&&data.globalLevel==level+1,"Exact authored level index required");
                    var row=new Row{name="L"+(level+1)+"_"+(kind<0?"match":"power"+kind),level=level+1,kind=kind,seed=Math.Max(1,data.tileSeed),levelSHA256=Hash(authored)};
                    // These construction/selection expressions intentionally match LocalCascadeVerification.Run exactly.
                    var board=new BoardModel(data);TurnResult turn;
                    if(kind<0){var move=board.LegalSwaps().First();row.ax=move[0].x;row.ay=move[0].y;row.bx=move[1].x;row.by=move[1].y;}
                    else {var source=board.Pieces.Values.First(p=>p.family=="gem");row.ax=source.x;row.ay=source.y;row.bx=source.x;row.by=source.y;row.sourceId=source.id;}
                    if(baseline!=null){var old=baseline.rows[report.rows.Count];Check(report,old.name==row.name&&old.kind==row.kind&&old.seed==row.seed&&old.levelSHA256==row.levelSHA256&&old.ax==row.ax&&old.ay==row.ay&&old.bx==row.bx&&old.by==row.by&&old.sourceId==row.sourceId,"Candidate selection must equal explicit actual2022 command "+row.name);}
                    if(kind<0)turn=board.Swap(row.ax,row.ay,row.bx,row.by);
                    else {board.InjectReviewPower(row.ax,row.ay,kind);turn=board.Tap(row.ax,row.ay);}
                    row.accepted=turn.accepted;Check(report,row.accepted,"Command accepted "+row.name);board.Validate();
                    Export(row,output,"RawTurn",turn);Export(row,output,"FinalSnapshot",board.Snapshot());Export(row,output,"FinalCheckpoint",board.Checkpoint());report.rows.Add(row);
                }
                Check(report,report.rows.Count==350&&report.rows.Select(r=>r.name).Distinct().Count()==350&&report.rows.All(r=>r.payloads.Count==3),"Complete unique350-command/1050-payload export required");report.status="PASS_ACTUAL_SERIALIZATION_CORPUS94";
            }catch(Exception error){report.error=error.ToString();}
            if(output!=null)Write(Path.Combine(output,"Native.json"),JsonUtility.ToJson(report,true));else Debug.LogError("Corpus probe refused before safe output available");
            EditorApplication.Exit(report.status=="PASS_ACTUAL_SERIALIZATION_CORPUS94"?0:1);
        }
    }
}
#endif
