#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.RuStore;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
 public static class TeamsLifecycle113HttpVerification {
  [Serializable] sealed class Connection {public string runId,origin;public int pid;public long clock;public bool actualBackend,replayEnabled,providersEnabled,productionEnabled;}
  [Serializable] sealed class Control {public string dropLeaveCommand="";}
  [Serializable] sealed class Bindings {public string owner,member,team;}
  [Serializable] sealed class Report {
   public string status="RUNNING",utc,unity;
   public string scope="Actual Unity managed guest/device signatures, social HTTP and protected pending reconstruction against owned loopback backend/SQLite. Fixed clock; one actual committed leave reply is suppressed with503. No gameplay, device, external delivery or production acceptance.";
   public int checks,cases,managedGuests,signedRequests,socialRequests,walletReads,protectedReconstructionCount;
   public bool actualHttp=true,ordinaryProfilesPreserved,serverReviewPreserved,settingsPreserved,languagePreferencePreserved;
   public List<int> signedStatuses=new List<int>(),socialStatuses=new List<int>();public List<string> passed=new List<string>(),errors=new List<string>();
  }
  static Report report;static Connection connection;static string temporary,vaultRoot,output,profiles,server,settings;static bool hadLanguage;static int language;
  static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();static readonly Queue<IEnumerator> dispatched=new Queue<IEnumerator>();static readonly List<IDisposable> cleanup=new List<IDisposable>();static readonly List<SocialBackendClient82> clients=new List<SocialBackendClient82>();static readonly List<IdentityHttpTransport82> identities=new List<IdentityHttpTransport82>();static AsyncOperation waiting;static double deadline;static bool finished;
  static string Id()=>Guid.NewGuid().ToString("N");
  static void Check(bool valid,string label){report.checks++;if(!valid)throw new InvalidOperationException(label);}
  static void Passed(string label){report.cases++;report.passed.Add(label);}
  static void Dispatch(IEnumerator value){dispatched.Enqueue(value);}
  static string Digest(string path){if(!Directory.Exists(path))return "Absent";return IdentityProtocol82.Sha(string.Join("\n",Directory.GetFiles(path,"*",SearchOption.AllDirectories).OrderBy(v=>v,StringComparer.Ordinal).Select(p=>p.Substring(path.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(p)))));}
  static IEnumerator Call<T>(Action<Action<SocialReply82<T>>> call,Action<T> assertion)where T:class{SocialReply82<T> reply=null;call(x=>reply=x);while(reply==null)yield return null;Check(reply.Succeeded,"Real typed social response succeeds");assertion?.Invoke(reply.value);}
  static ManagedIdentitySession82 Manager(EditorEphemeralIdentity82 vault,string path){var transport=new IdentityHttpTransport82(connection.origin,Dispatch,true);identities.Add(transport);cleanup.Add(transport);var manager=new ManagedIdentitySession82(vault.CreateKey(),vault.CreateStore(path),transport);cleanup.Add(manager);return manager;}
  static SocialBackendClient82 Client(ManagedIdentitySession82 owner,EditorEphemeralIdentity82 vault,string path){var store=vault.CreateStore(path);cleanup.Add(store);var client=new SocialBackendClient82(connection.origin,()=>owner.HasAccess?new SocialAccess82(owner.View.playerId,owner.AccessToken):null,Dispatch,store,true,true);clients.Add(client);cleanup.Add(client);return client;}
  static IEnumerator Guest(ManagedIdentitySession82 owner){IdentityReply82<IdentityView82> reply=null;owner.CreateGuest(Id(),x=>reply=x);while(reply==null)yield return null;Check(reply.Succeeded&&owner.HasAccess&&owner.View.hasSession,"Real managed guest enrollment succeeds with signed device challenge");report.managedGuests++;}
  static IEnumerator Wallet(ManagedIdentitySession82 owner,int expected,int coins=1250,Action<RuStoreServerWallet> extra=null){var wallet=new RuStoreBackendClient(connection.origin,owner.AccessToken,owner.View.playerId,true,true,Dispatch);cleanup.Add(wallet);PayReply<RuStoreServerWallet> reply=null;wallet.GetWallet(x=>reply=x);while(reply==null)yield return null;report.walletReads++;Check(reply.Succeeded&&reply.value.coins==coins&&reply.value.lives==expected&&!reply.value.localProfileMutated&&!reply.value.normalUnityProfileIntegrated,"Authoritative wallet fetch has expected lives and unchanged coins/local-profile isolation");extra?.Invoke(reply.value);}
  static void Operate(string drop){File.WriteAllText(Path.Combine(temporary,"operator.json"),JsonUtility.ToJson(new Control{dropLeaveCommand=drop}),new UTF8Encoding(false));}
  static IEnumerator Flow(){
   var vaults=new EditorEphemeralIdentity82[2];var owners=new ManagedIdentitySession82[2];var social=new SocialBackendClient82[2];
   for(int n=0;n<2;n++){vaults[n]=new EditorEphemeralIdentity82();cleanup.Add(vaults[n]);owners[n]=Manager(vaults[n],Path.Combine(vaultRoot,"identity_"+n+".sealed"));yield return Guest(owners[n]);social[n]=Client(owners[n],vaults[n],Path.Combine(vaultRoot,"social_"+n+".sealed"));yield return Wallet(owners[n],5);}
   string owner=owners[0].View.playerId,member=owners[1].View.playerId;Check(owner!=member,"Two actual managed internal players distinct");
   string team=null;yield return Call<SocialMutation82>(done=>social[0].CreateTeam(Id(),"Rain Leave113","Controlled leave verification","drop",done),row=>team=row.teamId);
   yield return Call<SocialMutation82>(done=>social[1].JoinTeam(Id(),team,done),row=>Check(row.state=="Joined","Other player joins test team"));
   SocialTeam82 old=null;yield return Call<SocialTeam82>(done=>social[1].GetTeam(team,done),row=>old=row);Check(old.isMember&&!string.IsNullOrEmpty(old.membershipVersion)&&!old.leaveClosesTeam,"Member has stable membership version");string priorVersion=old.membershipVersion;
   string command=Id();Operate(command);SocialReply82<SocialMutation82> lost=null;social[1].LeaveTeam113(command,team,priorVersion,x=>lost=x);while(lost==null)yield return null;
   Check(!lost.Succeeded&&lost.unknown&&social[1].PendingCommand?.commandId==command,"After-commit loss retains exact leave command");string oldBody=social[1].PendingCommand.body;
   social[1].Dispose();social[1]=Client(owners[1],vaults[1],Path.Combine(vaultRoot,"social_1.sealed"));report.protectedReconstructionCount++;Check(social[1].PendingCommand?.body==oldBody,"Reconstructed protected client restores leave body");
   SocialMutation82 receipt=null;yield return Call<SocialMutation82>(done=>social[1].ResumePending(done),row=>{receipt=row;Check(row.state=="Left"&&row.teamId==team,"Original command recovers committed leave receipt");});
   yield return Call<SocialTeams82>(done=>social[1].GetTeams("",8,done),row=>Check(string.IsNullOrEmpty(row.myTeamId),"Authoritative directory confirms member left"));
   yield return Call<SocialMutation82>(done=>social[1].JoinTeam(Id(),team,done),row=>Check(row.state=="Joined","Player can explicitly rejoin same team"));
   SocialTeam82 current=null;yield return Call<SocialTeam82>(done=>social[1].GetTeam(team,done),row=>current=row);Check(current.isMember&&current.membershipVersion!=priorVersion,"Rejoining same team obtains a fresh membership version");
   yield return Call<SocialMutation82>(done=>social[1].LeaveTeam113(command,team,priorVersion,done),row=>Check(JsonUtility.ToJson(row)==JsonUtility.ToJson(receipt),"Exact old command returns immutable prior receipt"));
   yield return Call<SocialTeam82>(done=>social[1].GetTeam(team,done),row=>Check(row.isMember&&row.membershipVersion==current.membershipVersion,"Replayed prior command cannot remove new membership"));
   string stale=Id();Operate(stale);SocialReply82<SocialMutation82> lostReject=null;social[1].LeaveTeam113(stale,team,priorVersion,x=>lostReject=x);while(lostReject==null)yield return null;
   Check(!lostReject.Succeeded&&lostReject.unknown&&social[1].PendingCommand?.commandId==stale,"Lost rejected receipt remains unknown and preserves intent");
   social[1].Dispose();social[1]=Client(owners[1],vaults[1],Path.Combine(vaultRoot,"social_1.sealed"));report.protectedReconstructionCount++;yield return Call<SocialMutation82>(done=>social[1].ResumePending(done),row=>Check(row.state=="Rejected"&&row.reason=="team_membership_changed","Original guarded stale command recovers definitive rejected receipt"));
   yield return Call<SocialTeam82>(done=>social[1].GetTeam(team,done),row=>Check(row.isMember&&row.membershipVersion==current.membershipVersion,"Lost rejected receipt cannot remove rejoined membership"));
   yield return Wallet(owners[0],5);yield return Wallet(owners[1],5);File.WriteAllText(Path.Combine(temporary,"ExpectedBindings.json"),JsonUtility.ToJson(new Bindings{owner=owner,member=member,team=team},true),new UTF8Encoding(false));Passed("Lost leave reply, exact retry, same-team rejoin and stale receipt preserve current membership and wallets");
  }

  public static void Run(){
   output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW113_HTTP_OUT")??throw new InvalidOperationException("Explicit113output required"));temporary=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW113_HTTP_PRIVATE")??throw new InvalidOperationException("Explicit private111 fixture required"));CheckPath();report=new Report{unity=Application.unityVersion};connection=JsonUtility.FromJson<Connection>(File.ReadAllText(Path.Combine(temporary,"connection.json")));var uri=new Uri(connection.origin);Check(uri.Scheme=="http"&&uri.Host=="127.0.0.1"&&uri.Port>0&&connection.actualBackend&&!connection.replayEnabled&&!connection.providersEnabled&&!connection.productionEnabled,"Exact owned loopback actual service is required");if(!System.Text.RegularExpressions.Regex.IsMatch(connection.runId??"","\\A[a-f0-9]{32}\\z"))throw new InvalidOperationException("ExactRunIdRequired111");vaultRoot=Path.GetFullPath("../.verification-cache/Launch82/TeamLeave113/"+connection.runId);if(Directory.Exists(vaultRoot))throw new InvalidOperationException("FreshIgnoredVaultFixtureRequired111");Directory.CreateDirectory(vaultRoot);profiles=Digest(Path.Combine(Application.persistentDataPath,"Profiles"));server=Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));settings=Digest("ProjectSettings");hadLanguage=PlayerPrefs.HasKey(GameLocale.PreferenceKey);language=PlayerPrefs.GetInt(GameLocale.PreferenceKey,-1);deadline=EditorApplication.timeSinceStartup+300;stack.Push(Flow());EditorApplication.update+=Tick;
  }
  static void CheckPath(){string root=Path.GetFullPath("../.verification-cache/Review113/LeaveHTTP")+Path.DirectorySeparatorChar;if(!temporary.StartsWith(root,StringComparison.OrdinalIgnoreCase)||!File.Exists(Path.Combine(temporary,"connection.json")))throw new InvalidOperationException("Fresh113privatefixture required");}
  static void Tick(){try{if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Bounded Help113actual HTTP suite timed out");if(waiting!=null){if(!waiting.isDone)return;waiting=null;}if(stack.Count==0){Finish();return;}var top=stack.Peek();if(!top.MoveNext()){stack.Pop();(top as IDisposable)?.Dispose();}else if(top.Current is IEnumerator child)stack.Push(child);else if(top.Current is AsyncOperation operation)waiting=operation;while(dispatched.Count>0)stack.Push(dispatched.Dequeue());}catch(Exception error){report.errors.Add(error.GetType().Name+": "+error.Message);Finish();}}
  static void Finish(){if(finished)return;finished=true;EditorApplication.update-=Tick;while(stack.Count>0)(stack.Pop()as IDisposable)?.Dispose();while(dispatched.Count>0)(dispatched.Dequeue()as IDisposable)?.Dispose();foreach(var client in clients){report.socialRequests+=client.VerificationRequests;report.socialStatuses.AddRange(client.VerificationStatuses);}foreach(var identity in identities){report.signedRequests+=identity.VerificationRequestCount;report.signedStatuses.AddRange(identity.VerificationStatuses);}for(int n=cleanup.Count-1;n>=0;n--)try{cleanup[n].Dispose();}catch(Exception){report.errors.Add("Owned HTTP cleanup failed");}try{report.ordinaryProfilesPreserved=profiles==Digest(Path.Combine(Application.persistentDataPath,"Profiles"));report.serverReviewPreserved=server==Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));report.settingsPreserved=settings==Digest("ProjectSettings");report.languagePreferencePreserved=hadLanguage==PlayerPrefs.HasKey(GameLocale.PreferenceKey)&&language==PlayerPrefs.GetInt(GameLocale.PreferenceKey,-1);Check(report.ordinaryProfilesPreserved&&report.serverReviewPreserved&&report.settingsPreserved&&report.languagePreferencePreserved,"Ordinary data/settings/language remain byte-identical");}catch(Exception){report.errors.Add("Preservation audit failed");}report.utc=DateTime.UtcNow.ToString("o");report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_LIFECYCLE113_HTTP":"FAIL_NATIVE_TEAMS_LIFECYCLE113_HTTP";Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native","TeamsLifecycle113_HTTP.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));EditorApplication.Exit(report.errors.Count==0?0:1);}
 }
}
#endif
