#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.Advertising;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    public static class RewardedAdsJournal85Verification {
        const string Origin="https://journal-fixture.invalid",Player="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REWARDED_ADS85_OUTPUT")??"../Verification/Evidence/AdsRub85");
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity;
            public string scope="Native Unity Editor execution of real temporary-file ad intent journals, atomic replacement, actual exclusive file contention, corruption/shape rejection, simulated before/after-commit exceptions and process-object reinstantiation. Synthetic public correlation metadata only; no ad SDK, actual process kill/OS power-loss proof, credentials, HTTP, wallet grant, Android or provider verification claim.";
            public int checks,cases;public bool credentialsAbsent,ownerBound,completionDurable,stableCommands,corruptionFailClosed,resolutionRequired;
            public List<string> passed=new List<string>(),errors=new List<string>();
            public List<UnderlyingException116> underlyingExceptions=new List<UnderlyingException116>();
            public List<JournalDiagnostic116> journalDiagnostics=new List<JournalDiagnostic116>();public List<ReplaceProbe116> replaceProbes=new List<ReplaceProbe116>();
        }
        [Serializable] sealed class Envelope {public int version=1;public string payload,sha256;}
        static Report report;static string temporaryRoot;
        static void Check(bool condition,string message){report.checks++;if(!condition)throw new InvalidOperationException(message);report.passed.Add(message);}
        static void Reject(Action action,string message){bool rejected=false;try{action();}catch(InvalidOperationException){rejected=true;}Check(rejected,message);}
        static string Sha(string text){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
        static AdIntent85 Intent()=>new AdIntent85{origin=Origin,playerId=Player,state="Reserving",reserveCommandId=new string('1',32),reportCommandId=new string('2',32),claimCommandId=new string('3',32),cancelCommandId=new string('4',32)};
        static AdIntent85 Copy(AdIntent85 value)=>JsonUtility.FromJson<AdIntent85>(JsonUtility.ToJson(value));
        static string FileFor(string name)=>Path.Combine(temporaryRoot,name,"ads.json");
        static void Case(string name,Action body){caseName116=name;body();report.cases++;report.passed.Add("Case: "+name);}
        static AdIntent85 Read(RewardedAdsJournal85 journal){AdIntent85 value;string error;Check(journal.TryLoad(Origin,Player,out value,out error)&&value!=null&&error==null,"Restart reads an intact owned intent");return value;}
        static bool SameCommands(AdIntent85 a,AdIntent85 b)=>a.reserveCommandId==b.reserveCommandId&&a.reportCommandId==b.reportCommandId&&a.claimCommandId==b.claimCommandId&&a.cancelCommandId==b.cancelCommandId;
        static void Unchanged(string path,byte[] before,string message)=>Check(File.ReadAllBytes(path).SequenceEqual(before),message);
        [Serializable] sealed class UnderlyingException116 {public int operation,hresult;public string exceptionType,kind,state,caseName;}
        [Serializable] sealed class JournalDiagnostic116 {public int operation;public string kind,state,stage,caseName,exceptionType,exceptionCode,beforeSha,afterSha;public int targetLength,lockLength,tempLength,targetBytes,tempCount;public bool targetExists,lockExists;}
        [Serializable] sealed class ReplaceProbe116 {public string context,status,exceptionType;public int hresult,targetLength,tempLength;public bool priorBytesConfirmed,replacementConfirmed;}
        static int diagnosticOperation116;static string caseName116;
        static string FileSha116(string path){try{if(!File.Exists(path))return "Absent";using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}catch(Exception e){return "Unavailable:"+e.GetType().Name;}}
        static string JournalPath116(RewardedAdsJournal85 journal)=>(string)typeof(RewardedAdsJournal85).GetField("path",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).GetValue(journal);
        static JournalDiagnostic116 Diagnostic116(string path,int operation,string kind,string state,string stage,string before,Exception error=null){
            var temps=Directory.GetFiles(Path.GetDirectoryName(path),"*.tmp");return new JournalDiagnostic116{operation=operation,kind=kind,state=state,stage=stage,caseName=caseName116,targetLength=path.Length,lockLength=(path+".lock").Length,tempLength=temps.Length>0?temps.Max(v=>v.Length):Path.Combine(Path.GetDirectoryName(path),"ad-"+new string('0',32)+".tmp").Length,tempCount=temps.Length,targetExists=File.Exists(path),lockExists=File.Exists(path+".lock"),targetBytes=File.Exists(path)?(int)new FileInfo(path).Length:0,beforeSha=before,afterSha=FileSha116(path),exceptionType=error?.GetType().FullName,exceptionCode=error is InvalidOperationException?error.Message:null};
        }
        static void Probe116(string context){
            var row=new ReplaceProbe116{context=context,status="RUNNING"};report.replaceProbes.Add(row);string root=Path.Combine(temporaryRoot,"direct-replace-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);string target=Path.Combine(root,"target.json"),temporary=Path.Combine(root,"ad-"+Guid.NewGuid().ToString("N")+".tmp");row.targetLength=target.Length;row.tempLength=temporary.Length;
            try{File.WriteAllBytes(target,new byte[]{1,2,3});row.priorBytesConfirmed=File.ReadAllBytes(target).SequenceEqual(new byte[]{1,2,3});using(var file=new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(new byte[]{4,5,6},0,3);file.Flush(true);}File.Replace(temporary,target,null);row.replacementConfirmed=File.ReadAllBytes(target).SequenceEqual(new byte[]{4,5,6})&&!File.Exists(temporary);row.status=row.priorBytesConfirmed&&row.replacementConfirmed?"PASS_ACTUAL_FILE_REPLACE":"FAIL_BYTES";}catch(Exception e){row.status="FAIL_EXCEPTION";row.exceptionType=e.GetType().FullName;row.hresult=e.HResult;}
        }
        static void Operation116(RewardedAdsJournal85 journal,string kind,string state,Action action){
            int operation=++diagnosticOperation116;string path=JournalPath116(journal),before=FileSha116(path);var originalException=journal.VerificationException116;journal.VerificationException116=(type,hresult)=>{report.underlyingExceptions.Add(new UnderlyingException116{operation=operation,hresult=hresult,exceptionType=type,kind=kind,state=state,caseName=caseName116});originalException?.Invoke(type,hresult);};var original=journal.VerificationCheckpoint;report.journalDiagnostics.Add(Diagnostic116(path,operation,kind,state,"BeforeCall",before));journal.VerificationCheckpoint=stage=>{report.journalDiagnostics.Add(Diagnostic116(path,operation,kind,state,stage,before));original?.Invoke(stage);};
            try{action();report.journalDiagnostics.Add(Diagnostic116(path,operation,kind,state,"Returned",before));}catch(Exception error){report.journalDiagnostics.Add(Diagnostic116(path,operation,kind,state,"Threw",before,error));if(error is InvalidOperationException&&error.Message=="AdJournalSaveUnavailable"&&original==null)Probe116("Unexpected masked save failure operation "+operation);throw;}finally{journal.VerificationCheckpoint=original;journal.VerificationException116=originalException;}
        }
        static void Save116(RewardedAdsJournal85 journal,AdIntent85 value)=>Operation116(journal,"Save",value?.state,()=>journal.Save(value));
        static void Clear116(RewardedAdsJournal85 journal,string origin,string player)=>Operation116(journal,"Clear","",()=>journal.Clear(origin,player));
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};temporaryRoot=Path.Combine(Path.GetTempPath(),"hotr-adjournal116-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(temporaryRoot);
            diagnosticOperation116=0;Probe116("Before actual journal lifecycle");int code=0;
            try{
                Case("Missing file and complete durable lifecycle",()=>{
                    string path=FileFor("lifecycle");var journal=new RewardedAdsJournal85(path);AdIntent85 value;string error;
                    Check(!journal.TryLoad(Origin,Player,out value,out error)&&value==null&&error==null,"Missing journal is absent without an invented failure");Clear116(journal,Origin,Player);
                    var first=Intent();Save116(journal,first);first.claimCommandId=new string('5',32);var loaded=Read(new RewardedAdsJournal85(path));
                    Check(loaded.state=="Reserving"&&loaded.opportunityId==""&&!loaded.CompletionReported&&loaded.claimCommandId==new string('3',32),"Reservation command is durable before reserve and caller mutation cannot edit it");
                    var baseline=Copy(loaded);loaded.state="Reserved";loaded.opportunityId=new string('b',32);Save116(journal,loaded);loaded=Read(new RewardedAdsJournal85(path));
                    Check(loaded.opportunityId==new string('b',32)&&SameCommands(loaded,baseline),"Opportunity and all command IDs survive reconstruction before any SDK dispatch");
                    loaded.state="CompletionReported";loaded.CompletionReported=true;Save116(journal,loaded);loaded=Read(new RewardedAdsJournal85(path));
                    Check(loaded.CompletionReported&&SameCommands(loaded,baseline),"Completion record and exact report/claim identifiers survive reconstruction before network report");
                    loaded.state="Claiming";Save116(journal,loaded);loaded.state="Resolved";Save116(journal,loaded);Clear116(journal,Origin,Player);
                    Check(!journal.TryLoad(Origin,Player,out value,out error)&&error==null&&!File.Exists(path),"Resolved file is removed without restoring an old pending backup");
                    Check(Directory.GetFiles(Path.GetDirectoryName(path),"*.bak").Length==0&&Directory.GetFiles(Path.GetDirectoryName(path),"*.tmp").Length==0,"Lifecycle leaves neither pending backup nor temporary record");
                    report.stableCommands=report.completionDurable=report.resolutionRequired=true;
                });
                Case("Owner and immutable one-outstanding intent",()=>{
                    string path=FileFor("binding");var journal=new RewardedAdsJournal85(path);var value=Intent();Save116(journal,value);byte[] before=File.ReadAllBytes(path);AdIntent85 other;string error;
                    Check(!journal.TryLoad("https://other-fixture.invalid",Player,out other,out error)&&other==null&&error=="AdJournalOwnerMismatch","Another origin cannot consume the journal");
                    Check(!journal.TryLoad(Origin,new string('c',32),out other,out error)&&other==null&&error=="AdJournalOwnerMismatch","Another player cannot consume the journal");
                    var changed=Copy(value);changed.origin="https://other-fixture.invalid";Reject(()=>Save116(journal,changed),"Another origin cannot overwrite pending metadata");
                    changed=Copy(value);changed.playerId=new string('c',32);Reject(()=>Save116(journal,changed),"Another player cannot overwrite pending metadata");
                    foreach(string field in new[]{"reserveCommandId","reportCommandId","claimCommandId","cancelCommandId"}){changed=Copy(value);typeof(AdIntent85).GetField(field).SetValue(changed,new string('e',32));var candidate=changed;Reject(()=>Save116(journal,candidate),"Changing an outstanding command identity is rejected");}
                    Reject(()=>Clear116(journal,Origin,Player),"Unresolved reservation cannot be forgotten");Reject(()=>Clear116(journal,Origin,new string('c',32)),"Wrong owner cannot delete the file");Unchanged(path,before,"Owner/identity/clear denials preserve exact original bytes");report.ownerBound=true;
                });
                Case("Strict validated fields and no hidden credentials",()=>{
                    foreach(var mutate in new Action<AdIntent85>[] {
                        v=>v.playerId=Player+"\n",v=>v.reserveCommandId=new string('A',32),v=>v.reportCommandId=v.claimCommandId,
                        v=>v.origin="https://name:secret@journal-fixture.invalid",v=>v.origin=Origin+"/?token=secret",v=>v.origin=Origin+"/private",v=>v.origin="http://non-loopback.invalid",
                        v=>v.state="Claimed",v=>v.opportunityId=new string('a',32),v=>v.CompletionReported=true
                    }){string path=FileFor(Guid.NewGuid().ToString("N"));var journal=new RewardedAdsJournal85(path);var value=Intent();mutate(value);Reject(()=>Save116(journal,value),"Malformed/credential-bearing/noninitial metadata cannot be created");Check(!File.Exists(path),"Rejected initial metadata does not create a journal");}
                    var fields=typeof(AdIntent85).GetFields().Select(f=>f.Name).OrderBy(x=>x).ToArray();Check(fields.SequenceEqual(new[]{"CompletionReported","cancelCommandId","claimCommandId","opportunityId","origin","playerId","reportCommandId","reserveCommandId","state"}.OrderBy(x=>x)),"Persistable intent contains only the explicitly public correlation fields");report.credentialsAbsent=true;
                });
                Case("Known opportunity, completion and terminal state cannot regress",()=>{
                    string path=FileFor("monotonic");var journal=new RewardedAdsJournal85(path);var value=Intent();Save116(journal,value);value.state="Reserved";value.opportunityId=new string('b',32);Save116(journal,value);
                    var changed=Copy(value);changed.opportunityId=new string('c',32);Reject(()=>Save116(journal,changed),"Known opportunity cannot be replaced");changed=Copy(value);changed.state="Reserving";changed.opportunityId="";Reject(()=>Save116(journal,changed),"Known opportunity cannot be erased or SDK-ready state reset");
                    value.state="CompletionReported";value.CompletionReported=true;Save116(journal,value);changed=Copy(value);changed.state="Reserved";changed.CompletionReported=false;Reject(()=>Save116(journal,changed),"Durable completion cannot be erased by a stale writer");
                    value.state="Claiming";Save116(journal,value);changed=Copy(value);changed.state="CompletionReported";Reject(()=>Save116(journal,changed),"Claiming cannot regress into a fresh report dispatch");value.state="Resolved";Save116(journal,value);var pending=Copy(value);pending.state="Claiming";Reject(()=>Save116(journal,pending),"Resolved state remains terminal until clear");
                    var fresh=Intent();fresh.reserveCommandId=new string('e',32);Reject(()=>Save116(journal,fresh),"A second ad requires clearing the resolved record first");Clear116(journal,Origin,Player);
                    Save116(journal,fresh);Check(Read(new RewardedAdsJournal85(path)).reserveCommandId==fresh.reserveCommandId,"Clear permits a new independent intent only afterward");
                });
                Case("Actual precommit and lost commit acknowledgement recovery",()=>{
                    string path=FileFor("commit");var journal=new RewardedAdsJournal85(path);var value=Intent();Save116(journal,value);value.state="Reserved";value.opportunityId=new string('b',32);Save116(journal,value);byte[] before=File.ReadAllBytes(path);
                    value.state="CompletionReported";value.CompletionReported=true;journal.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException("Synthetic before-commit failure");};Reject(()=>Save116(journal,value),"Injected before-commit failure reaches the caller");Unchanged(path,before,"Before-commit failure preserves exact prior journal");
                    Check(Directory.GetFiles(Path.GetDirectoryName(path),"*.tmp").Length==0,"Failed precommit removes only its temporary sibling");
                    journal.VerificationCheckpoint=stage=>{if(stage=="AfterCommit")throw new IOException("Synthetic lost acknowledgement");};Reject(()=>Save116(journal,value),"Lost commit acknowledgement is not silently reported as success");
                    var recovered=Read(new RewardedAdsJournal85(path));Check(recovered.state=="CompletionReported"&&recovered.CompletionReported&&SameCommands(value,recovered),"A fresh journal recovers actually committed completion and exact IDs after unknown response");
                    journal.VerificationCheckpoint=null;Save116(journal,recovered);Check(SameCommands(Read(journal),recovered),"Exact saved-intent retry preserves stable command identities");
                });
                Case("Actual exclusive contention fails safely",()=>{
                    string path=FileFor("contention");var journal=new RewardedAdsJournal85(path);var value=Intent();Save116(journal,value);byte[] before=File.ReadAllBytes(path);
                    using(var held=new FileStream(path+".lock",FileMode.Open,FileAccess.ReadWrite,FileShare.None)){AdIntent85 loaded;string error;Check(!journal.TryLoad(Origin,Player,out loaded,out error)&&loaded==null&&error=="AdJournalUnavailable","An actual held exclusive lock is unavailable, not absent");Reject(()=>Save116(journal,value),"Concurrent save cannot bypass the lock");Reject(()=>Clear116(journal,Origin,Player),"Concurrent clear cannot bypass the lock");}
                    Unchanged(path,before,"Contention does not change pending bytes");Check(Read(journal).state=="Reserving","Journal remains readable after release of actual file lock");
                });
                Case("Actual destination sharing failure preserves completion for retry126",()=>{
                    string path=FileFor("target-held126");var journal=new RewardedAdsJournal85(path);var value=Intent();journal.Save(value);value.state="Reserved";value.opportunityId=new string('b',32);journal.Save(value);byte[] before=File.ReadAllBytes(path);
                    value.state="CompletionReported";value.CompletionReported=true;
                    using(var held=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read))Reject(()=>journal.Save(value),"Actual reader without delete sharing blocks atomic destination replacement");
                    Unchanged(path,before,"Destination sharing fault retains exact prior pending bytes");Check(Directory.GetFiles(Path.GetDirectoryName(path),"*.tmp").Length==0,"Destination sharing fault removes only own uncommitted sibling");
                    journal.Save(value);var saved=Read(new RewardedAdsJournal85(path));Check(saved.CompletionReported&&SameCommands(saved,value),"Released destination permits durable exact-completion retry");
                });
                Case("Repeated actual durable lifecycle126",()=>{
                    string path=FileFor("repeat126");
                    for(int i=0;i<128;i++){
                        var journal=new RewardedAdsJournal85(path);var value=Intent();journal.Save(value);value.state="Reserved";value.opportunityId=new string('b',32);journal.Save(value);value.state="CompletionReported";value.CompletionReported=true;journal.Save(value);value.state="Claiming";journal.Save(value);
                        var reconstructed=Read(new RewardedAdsJournal85(path));Check(reconstructed.state=="Claiming"&&reconstructed.CompletionReported&&SameCommands(reconstructed,value),"Repeated canonical completion and claim survive reconstruction");
                        value.state="Resolved";journal.Save(value);journal.Clear(Origin,Player);Check(!File.Exists(path)&&Directory.GetFiles(Path.GetDirectoryName(path),"*.tmp").Length==0,"Repeated resolved lifecycle leaves no pending or temporary file");
                    }
                });
                Case("Corruption and canonical-shape rejection preserve evidence",()=>{
                    string path=FileFor("corrupt");var journal=new RewardedAdsJournal85(path);var value=Intent();Save116(journal,value);string original=File.ReadAllText(path);var envelope=JsonUtility.FromJson<Envelope>(original);
                    var variants=new List<byte[]> {Encoding.UTF8.GetBytes(original.Replace(envelope.sha256,new string('0',64))),new byte[]{0xff,0xfe,0xfd},new byte[8193],Encoding.UTF8.GetBytes(original.Replace("\"version\":1","\"version\":2")),Encoding.UTF8.GetBytes(original.Replace("\"version\":1","\"version\":1,\"version\":1"))};
                    var changed=JsonUtility.FromJson<Envelope>(original);changed.payload=changed.payload.Substring(0,changed.payload.Length-1)+",\"accessToken\":\"not-a-real-token\"}";changed.sha256=Sha(changed.payload);variants.Add(Encoding.UTF8.GetBytes(JsonUtility.ToJson(changed)));
                    foreach(byte[] bytes in variants){File.WriteAllBytes(path,bytes);AdIntent85 loaded;string error;Check(!journal.TryLoad(Origin,Player,out loaded,out error)&&loaded==null&&!string.IsNullOrEmpty(error),"Corrupt/noncanonical data is an explicit failure, never an absent intent");Reject(()=>Save116(journal,value),"Save cannot overwrite unknown or corrupt pending data");Reject(()=>Clear116(journal,Origin,Player),"Clear cannot erase unknown or corrupt pending data");Unchanged(path,bytes,"Failed operations retain exact corrupt bytes for safe recovery");}
                    File.WriteAllText(path,original,new UTF8Encoding(false));Check(Read(journal).state=="Reserving","Restoring the exact original bytes recovers the original intent");report.corruptionFailClosed=true;
                });
                Case("Cancellation, absent reservation resolution and lost clear acknowledgement",()=>{
                    string path=FileFor("cancel");var journal=new RewardedAdsJournal85(path);var value=Intent();Save116(journal,value);value.state="Reserved";value.opportunityId=new string('b',32);Save116(journal,value);value.state="Cancelling";Save116(journal,value);
                    Check(Read(new RewardedAdsJournal85(path)).cancelCommandId==value.cancelCommandId,"Cancellation remains recoverable with its original command");value.state="Resolved";Save116(journal,value);journal.VerificationCheckpoint=stage=>{if(stage=="AfterClear")throw new IOException("Synthetic lost clear acknowledgement");};Reject(()=>Clear116(journal,Origin,Player),"Lost clear acknowledgement is surfaced");AdIntent85 absent;string error;Check(!new RewardedAdsJournal85(path).TryLoad(Origin,Player,out absent,out error)&&error==null,"Actual clear remains absent after its acknowledgement is lost");
                    journal.VerificationCheckpoint=null;value=Intent();Save116(journal,value);value.state="Resolved";Save116(journal,value);Clear116(journal,Origin,Player);Check(!File.Exists(path),"A definitively absent/denied reservation can be marked resolved without inventing an opportunity");
                });
                Case("Long bound filename does not repeat into temporary name",()=>{
                    string path=FileFor("bound-"+new string('x',90));var journal=new RewardedAdsJournal85(path);var value=Intent();Save116(journal,value);value.state="Reserved";value.opportunityId=new string('b',32);Save116(journal,value);Check(Read(new RewardedAdsJournal85(path)).opportunityId==value.opportunityId,"Bound long-directory replacement uses a short sibling and remains recoverable");
                });
            }catch(Exception error){report.errors.Add(error.ToString());code=1;}
            report.status=code==0?"PASS_NATIVE_REWARDED_ADS_JOURNAL85":"FAIL_NATIVE_REWARDED_ADS_JOURNAL85";Directory.CreateDirectory(Path.Combine(Output,"Native"));File.WriteAllText(Path.Combine(Output,"Native/RewardedAdsJournal85.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(code);
        }
    }
}
#endif
