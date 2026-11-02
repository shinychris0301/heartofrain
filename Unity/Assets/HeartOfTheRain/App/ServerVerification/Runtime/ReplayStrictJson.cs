using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace HeartOfTheRain.App.ServerVerification {
    // Bounded duplicate-key/type validation before JsonUtility, whose permissive
    // defaults must not silently accept a malformed server job.
    internal static class ReplayStrictJson {
        internal sealed class Number {public string value;}
        sealed class Reader {
            readonly string text;int at,nodes;
            internal Reader(string value){text=value;}
            void Space(){while(at<text.Length&&(text[at]==' '||text[at]=='\n'||text[at]=='\r'||text[at]=='\t'))at++;}
            char Take(){if(at>=text.Length)throw new ReplayRejected("invalid_json");return text[at++];}
            internal object Read(int depth=0){
                if(depth>32||++nodes>50000)throw new ReplayRejected("invalid_json");Space();if(at>=text.Length)throw new ReplayRejected("invalid_json");
                char c=text[at];if(c=='"')return String();
                if(c=='{'){at++;var result=new Dictionary<string,object>(StringComparer.Ordinal);Space();if(at<text.Length&&text[at]=='}'){at++;return result;}
                    while(true){Space();if(at>=text.Length||text[at]!='"')throw new ReplayRejected("invalid_json");string key=String();Space();if(Take()!=':'||result.ContainsKey(key))throw new ReplayRejected("invalid_json");result.Add(key,Read(depth+1));Space();char end=Take();if(end=='}')return result;if(end!=',')throw new ReplayRejected("invalid_json");}}
                if(c=='['){at++;var result=new List<object>();Space();if(at<text.Length&&text[at]==']'){at++;return result;}while(true){result.Add(Read(depth+1));Space();char end=Take();if(end==']')return result;if(end!=',')throw new ReplayRejected("invalid_json");}}
                foreach(string literal in new[]{"true","false","null"})if(text.Length-at>=literal.Length&&string.CompareOrdinal(text,at,literal,0,literal.Length)==0){at+=literal.Length;return literal=="null"?null:(object)(literal=="true");}
                int start=at;if(c=='-')at++;if(at>=text.Length)throw new ReplayRejected("invalid_json");if(text[at]=='0')at++;else{if(text[at]<'1'||text[at]>'9')throw new ReplayRejected("invalid_json");while(at<text.Length&&text[at]>='0'&&text[at]<='9')at++;}
                if(at<text.Length&&text[at]=='.'){at++;int digits=at;while(at<text.Length&&char.IsDigit(text[at]))at++;if(at==digits)throw new ReplayRejected("invalid_json");}
                if(at<text.Length&&(text[at]=='e'||text[at]=='E')){at++;if(at<text.Length&&(text[at]=='+'||text[at]=='-'))at++;int digits=at;while(at<text.Length&&char.IsDigit(text[at]))at++;if(at==digits)throw new ReplayRejected("invalid_json");}
                if(at-start>32)throw new ReplayRejected("invalid_json");return new Number{value=text.Substring(start,at-start)};
            }
            string String(){
                if(Take()!='"')throw new ReplayRejected("invalid_json");var result=new StringBuilder();
                while(true){char c=Take();if(c=='"')break;if(c<32)throw new ReplayRejected("invalid_json");if(c=='\\'){char escape=Take();switch(escape){case '"':c='"';break;case '\\':c='\\';break;case '/':c='/';break;case 'b':c='\b';break;case 'f':c='\f';break;case 'n':c='\n';break;case 'r':c='\r';break;case 't':c='\t';break;case 'u':int number=0;for(int i=0;i<4;i++){char h=Take();int n=h>='0'&&h<='9'?h-'0':h>='a'&&h<='f'?h-'a'+10:h>='A'&&h<='F'?h-'A'+10:-1;if(n<0)throw new ReplayRejected("invalid_json");number=number*16+n;}c=(char)number;break;default:throw new ReplayRejected("invalid_json");}}result.Append(c);if(result.Length>4096)throw new ReplayRejected("invalid_json");}
                string value=result.ToString();for(int i=0;i<value.Length;i++)if(char.IsSurrogate(value[i])){if(!char.IsHighSurrogate(value[i])||i+1>=value.Length||!char.IsLowSurrogate(value[++i]))throw new ReplayRejected("invalid_json");}return value;
            }
            internal void End(){Space();if(at!=text.Length)throw new ReplayRejected("invalid_json");}
        }
        static Dictionary<string,object> Fields(object value,string names){var row=value as Dictionary<string,object>;string[] expected=names.Split(',');if(row==null||row.Count!=expected.Length)throw new ReplayRejected("invalid_job_shape");foreach(string name in expected)if(!row.ContainsKey(name))throw new ReplayRejected("invalid_job_shape");return row;}
        static void Text(Dictionary<string,object> row,params string[] names){foreach(string name in names)if(!(row[name] is string))throw new ReplayRejected("invalid_job_type");}
        static void Int(Dictionary<string,object> row,params string[] names){foreach(string name in names){var n=row[name] as Number;long parsed;if(n==null||!long.TryParse(n.value,NumberStyles.AllowLeadingSign,CultureInfo.InvariantCulture,out parsed)||parsed<int.MinValue||parsed>int.MaxValue)throw new ReplayRejected("invalid_job_type");}}
        internal static void ValidateJob(string text){
            var reader=new Reader(text);var row=Fields(reader.Read(),"version,level,initialMoves,seed,jobId,playerId,attemptId,pinsSHA256,levelSHA256,startReceiptId,starting,actions,receipts");reader.End();
            Text(row,"jobId","playerId","attemptId","pinsSHA256","levelSHA256","startReceiptId");Int(row,"version","level","initialMoves");var seed=row["seed"] as Number;uint number;if(seed==null||!uint.TryParse(seed.value,NumberStyles.None,CultureInfo.InvariantCulture,out number))throw new ReplayRejected("invalid_job_type");
            var starting=row["starting"] as List<object>;var actions=row["actions"] as List<object>;var receipts=row["receipts"] as List<object>;if(starting==null||starting.Count!=4||actions==null||actions.Count>1000||receipts==null||receipts.Count>1000)throw new ReplayRejected("invalid_job_shape");
            foreach(object item in starting){var n=item as Number;if(n==null||(n.value!="0"&&n.value!="1"))throw new ReplayRejected("invalid_job_type");}
            foreach(object item in actions){var action=Fields(item,"index,ax,ay,bx,by,tool,movesAfter,kind,receiptId");Int(action,"index","ax","ay","bx","by","tool","movesAfter");Text(action,"kind","receiptId");}
            foreach(object item in receipts){var receipt=Fields(item,"receiptId,attemptId,kind,actionIndex,tool,coins,quantity,movesAfter");Text(receipt,"receiptId","attemptId","kind");Int(receipt,"actionIndex","tool","coins","quantity","movesAfter");}
        }
    }
}
