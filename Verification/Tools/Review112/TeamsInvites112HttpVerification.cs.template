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
 public static class TeamsInvites112HttpVerification {
  [Serializable] sealed class Connection {public string runId,origin;public int pid;public long clock;public bool actualBackend,replayEnabled,providersEnabled,productionEnabled;}
  [Serializable] sealed class Control {public string dropInviteCommand="";}
  [Serializable] sealed class Bindings {public string recipient,sender,team,inviteId,code;}
  [Serializable] sealed class Report {
   public string status="RUNNING",utc,unity;
   public string scope="Actual Unity managed guest/device signatures, social HTTP and protected pending reconstruction against owned loopback backend/SQLite. Fixed clock and enabled invite policy are explicit private test fixtures; one real committed reply is suppressed with503. No OS share, device, external delivery or production acceptance.";
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
  static void Operate(string drop){File.WriteAllText(Path.Combine(temporary,"operator.json"),JsonUtility.ToJson(new Control{dropInviteCommand=drop}),new UTF8Encoding(false));}
  static IEnumerator Flow(){
   var vaults=new EditorEphemeralIdentity82[2];var owners=new ManagedIdentitySession82[2];var social=new SocialBackendClient82[2];
   for(int n=0;n<2;n++){vaults[n]=new EditorEphemeralIdentity82();cleanup.Add(vaults[n]);owners[n]=Manager(vaults[n],Path.Combine(vaultRoot,"identity_"+n+".sealed"));yield return Guest(owners[n]);social[n]=Client(owners[n],vaults[n],Path.Combine(vaultRoot,"social_"+n+".sealed"));yield return Wallet(owners[n],5);}
   string sender=owners[0].View.playerId,recipient=owners[1].View.playerId;Check(sender!=recipient,"Two actual managed internal players distinct");
   string request=null;yield return Call<SocialMutation82>(done=>social[0].RequestFriend(Id(),recipient,done),row=>{request=row.requestId;Check(row.state=="Pending","Explicit friend request recorded");});
   yield return Call<SocialMutation82>(done=>social[1].RespondFriend(Id(),request,"accept",done),row=>Check(row.state=="Accepted","Other player accepts friendship"));
   string team=null;yield return Call<SocialMutation82>(done=>social[0].CreateTeam(Id(),"Rain Invite112","Controlled loopback verification","drop",done),row=>team=row.teamId);
   SocialInviteFriends112 listed=null;yield return Call<SocialInviteFriends112>(done=>social[0].GetInvitableFriends112(team,"","",done),row=>listed=row);
   Check(listed.canInvite&&listed.friends.Length==1&&listed.friends[0].friendId==recipient&&listed.friends[0].inviteState=="Ready","Existing friend is eligible for explicit invite under test policy");string code=listed.publicTeamCode;Check(code.Length==12,"Public team code has expected length");
   yield return Call<SocialTeams82>(done=>social[1].GetTeams("",8,code,done),row=>Check(row.teams.Any(t=>t.teamId==team),"Exact public team code finds team without joining"));
   yield return Call<SocialTeam82>(done=>social[1].GetTeam(team,done),row=>Check(!row.isMember,"Recipient is not member before invitation"));
   string command=Id();Operate(command);SocialReply82<SocialMutation82> lost=null;social[0].SendInvitation112(command,team,recipient,x=>lost=x);while(lost==null)yield return null;
   Check(!lost.Succeeded&&lost.unknown&&social[0].PendingCommand?.commandId==command,"After-commit loss keeps original invite intent");string oldBody=social[0].PendingCommand.body;
   social[0].Dispose();social[0]=Client(owners[0],vaults[0],Path.Combine(vaultRoot,"social_0.sealed"));report.protectedReconstructionCount++;Check(social[0].PendingCommand?.body==oldBody,"Fresh protected client restores same invite intent");
   SocialMutation82 receipt=null;yield return Call<SocialMutation82>(done=>social[0].ResumePending(done),row=>{receipt=row;Check(row.state=="Invited"&&row.friendId==recipient,"Same exact invite recovers receipt");});
   yield return Call<SocialMutation82>(done=>social[0].SendInvitation112(command,team,recipient,done),row=>Check(JsonUtility.ToJson(row)==JsonUtility.ToJson(receipt),"Exact retry returns same receipt"));
   yield return Call<SocialMutation82>(done=>social[0].SendInvitation112(Id(),team,recipient,done),row=>Check(row.inviteId==receipt.inviteId,"Second explicit request cannot create duplicate active invite"));
   yield return Call<SocialInviteFriends112>(done=>social[0].GetInvitableFriends112(team,"","",done),row=>Check(row.friends.Single(x=>x.friendId==recipient).inviteState=="Invited","Sender sees confirmed invited state"));
   yield return Call<SocialInvitations112>(done=>social[1].GetReceivedInvitations112(0,done),row=>Check(row.invitations.Length==1&&row.invitations[0].inviteId==receipt.inviteId&&row.invitations[0].state=="Ready","Recipient sees owner-scoped incoming invitation"));
   yield return Call<SocialInvitationDetail112>(done=>social[1].GetInvitation112(receipt.inviteId,done),row=>Check(row.invitation.teamId==team&&row.invitation.state=="Ready","Recipient detail resolves current server state"));
   yield return Call<SocialTeam82>(done=>social[1].GetTeam(team,done),row=>Check(!row.isMember,"Reading invitation never joins team"));yield return Wallet(owners[0],5);yield return Wallet(owners[1],5);
   File.WriteAllText(Path.Combine(temporary,"ExpectedBindings.json"),JsonUtility.ToJson(new Bindings{sender=sender,recipient=recipient,team=team,inviteId=receipt.inviteId,code=code},true),new UTF8Encoding(false));Passed("Authenticated friendship, public-code lookup, lost-invite recovery and owner-only received detail without auto-join");
  }
  public static void Run(){
   output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW112_HTTP_OUT")??throw new InvalidOperationException("Explicit112output required"));temporary=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW112_HTTP_PRIVATE")??throw new InvalidOperationException("Explicit private111 fixture required"));CheckPath();report=new Report{unity=Application.unityVersion};connection=JsonUtility.FromJson<Connection>(File.ReadAllText(Path.Combine(temporary,"connection.json")));var uri=new Uri(connection.origin);Check(uri.Scheme=="http"&&uri.Host=="127.0.0.1"&&uri.Port>0&&connection.actualBackend&&!connection.replayEnabled&&!connection.providersEnabled&&!connection.productionEnabled,"Exact owned loopback actual service is required");if(!System.Text.RegularExpressions.Regex.IsMatch(connection.runId??"","\\A[a-f0-9]{32}\\z"))throw new InvalidOperationException("ExactRunIdRequired111");vaultRoot=Path.GetFullPath("../.verification-cache/Launch82/TeamInvites112/"+connection.runId);if(Directory.Exists(vaultRoot))throw new InvalidOperationException("FreshIgnoredVaultFixtureRequired111");Directory.CreateDirectory(vaultRoot);profiles=Digest(Path.Combine(Application.persistentDataPath,"Profiles"));server=Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));settings=Digest("ProjectSettings");hadLanguage=PlayerPrefs.HasKey(GameLocale.PreferenceKey);language=PlayerPrefs.GetInt(GameLocale.PreferenceKey,-1);deadline=EditorApplication.timeSinceStartup+300;stack.Push(Flow());EditorApplication.update+=Tick;
  }
  static void CheckPath(){string root=Path.GetFullPath("../.verification-cache/Review112/InviteHTTP")+Path.DirectorySeparatorChar;if(!temporary.StartsWith(root,StringComparison.OrdinalIgnoreCase)||!File.Exists(Path.Combine(temporary,"connection.json")))throw new InvalidOperationException("Fresh112privatefixture required");}
  static void Tick(){try{if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Bounded Help112actual HTTP suite timed out");if(waiting!=null){if(!waiting.isDone)return;waiting=null;}if(stack.Count==0){Finish();return;}var top=stack.Peek();if(!top.MoveNext()){stack.Pop();(top as IDisposable)?.Dispose();}else if(top.Current is IEnumerator child)stack.Push(child);else if(top.Current is AsyncOperation operation)waiting=operation;while(dispatched.Count>0)stack.Push(dispatched.Dequeue());}catch(Exception error){report.errors.Add(error.GetType().Name+": "+error.Message);Finish();}}
  static void Finish(){if(finished)return;finished=true;EditorApplication.update-=Tick;while(stack.Count>0)(stack.Pop()as IDisposable)?.Dispose();while(dispatched.Count>0)(dispatched.Dequeue()as IDisposable)?.Dispose();foreach(var client in clients){report.socialRequests+=client.VerificationRequests;report.socialStatuses.AddRange(client.VerificationStatuses);}foreach(var identity in identities){report.signedRequests+=identity.VerificationRequestCount;report.signedStatuses.AddRange(identity.VerificationStatuses);}for(int n=cleanup.Count-1;n>=0;n--)try{cleanup[n].Dispose();}catch(Exception){report.errors.Add("Owned HTTP cleanup failed");}try{report.ordinaryProfilesPreserved=profiles==Digest(Path.Combine(Application.persistentDataPath,"Profiles"));report.serverReviewPreserved=server==Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));report.settingsPreserved=settings==Digest("ProjectSettings");report.languagePreferencePreserved=hadLanguage==PlayerPrefs.HasKey(GameLocale.PreferenceKey)&&language==PlayerPrefs.GetInt(GameLocale.PreferenceKey,-1);Check(report.ordinaryProfilesPreserved&&report.serverReviewPreserved&&report.settingsPreserved&&report.languagePreferencePreserved,"Ordinary data/settings/language remain byte-identical");}catch(Exception){report.errors.Add("Preservation audit failed");}report.utc=DateTime.UtcNow.ToString("o");report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_INVITES112_HTTP":"FAIL_NATIVE_TEAMS_INVITES112_HTTP";Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native","TeamsInvites112_HTTP.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));EditorApplication.Exit(report.errors.Count==0?0:1);}
 }
}
#endif
