#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.TeamsAccess;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    // The transport below never advances Exchange and therefore never constructs
    // a UnityWebRequest. It feeds labelled synthetic JSON through the actual
    // response parser, session, protected outbox and component action handlers.
    // Snapshot-only visual states are checked separately from those actions.
    public static class TeamsAccess109Verification {
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        const string Player="11111111111111111111111111111111",Team="22222222222222222222222222222222",Other="33333333333333333333333333333333";
        const string Origin="https://staging.hotr-native-fixture.net";
        [Serializable] sealed class Row {public string state;public int locale,width,height;public bool safeInsets,passed;}
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity;
            public string scope="Actual Unity2022 Editor parser/outbox/session/component actions with explicit in-memory scripted transport, plus separately labelled synthetic UGUI snapshots. No HTTP/DNS, real membership, backend, APK/device or production acceptance.";
            public int checks,cases,layouts,layoutsAttempted,scriptedExchanges,actualHttpRequests,authoredDarkPixels,capturedSentinelPixels;
            public bool ordinaryProfilesPreserved,serverReviewPreserved,languagePreferencePreserved,settingsPreserved;
            public bool rawJsonUtilityNullMembershipBecomesEmpty;
            public List<Row> rows=new List<Row>();public List<string> captures=new List<string>(),errors=new List<string>();
        }
        sealed class MemoryStore:IProtectedSessionStore82 {
            byte[] bytes;public int writes;
            public byte[] Read()=>bytes==null?null:(byte[])bytes.Clone();
            public void CompareExchange(string digest,byte[] next){if((bytes==null||bytes.Length==0?"":IdentityProtocol82.Sha(bytes))!=digest)throw new InvalidOperationException("SyntheticCASConflict109");bytes=(byte[])next.Clone();writes++;}
            public void Dispose(){if(bytes!=null)Array.Clear(bytes,0,bytes.Length);bytes=null;}
        }
        sealed class Scripted:IDisposable {
            public readonly MemoryStore store=new MemoryStore();public SocialBackendClient82 client;public SocialPageSession82 session;
            public readonly List<string> paths=new List<string>();public int exchanges,posts;public string lastPath,lastBody,lastMethod;public bool unknownNext,rejectNext,invalidBadgeNext,emptyMembershipNext,omitBadge,member;
            public string badge="drop";public List<string> postBodies=new List<string>();
            public Scripted(){var access=new SocialAccess82(Player,IdentityProtocol82.NewSecret());client=new SocialBackendClient82(Origin,()=>access,Dispatch,store,true,false);session=new SocialPageSession82(client,null,()=>1,()=>0);}
            static object IteratorField(IEnumerator value,string name){var field=value.GetType().GetFields(Private|BindingFlags.Public).FirstOrDefault(f=>f.Name==name);if(field==null)throw new InvalidOperationException("ScriptedIteratorBoundaryMissing109:"+name);return field.GetValue(value);}
            public void Dispatch(IEnumerator value){
                if(value.GetType().Name.StartsWith("<Exchange>",StringComparison.Ordinal)){
                    string method=(string)IteratorField(value,"method"),path=(string)IteratorField(value,"path"),body=(string)IteratorField(value,"body");
                    object pending=typeof(SocialBackendClient82).GetField("active",Private).GetValue(client);Check(pending!=null,"Actual client owns captured scripted request");
                    exchanges++;lastMethod=method;lastPath=path;paths.Add(path);lastBody=body;if(method=="POST"){posts++;postBodies.Add(body);}
                    string error=null,json=null;bool unknown=false;
                    if(unknownNext&&method=="POST"){unknownNext=false;error="SyntheticLostReply109";unknown=true;}
                    else if(rejectNext&&method=="POST"){rejectNext=false;error="SocialHttp409";}
                    else json=Response(method,path,body);
                    typeof(SocialBackendClient82).GetMethod("Complete",Private).Invoke(client,new[]{pending,json,error,(object)unknown});
                    pending.GetType().GetMethod("Release",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).Invoke(pending,null);
                    (value as IDisposable)?.Dispose();return;
                }
                // Only the actual page's bounded refresh orchestration is advanced.
                int steps=0;try{while(value.MoveNext()){Check(++steps<100,"Scripted component coroutine remains bounded");if(value.Current is IEnumerator child)Dispatch(child);else Check(value.Current==null,"No native asynchronous/network operation is yielded");}}finally{(value as IDisposable)?.Dispose();}
            }
            string Response(string method,string path,string body){
                if(method=="POST"){
                    if(path=="/v1/teams"){var input=JsonUtility.FromJson<CreateBody>(body);badge=string.IsNullOrEmpty(input.badgeId)?"drop":input.badgeId;member=true;return "{\"teamId\":\""+Team+"\",\"state\":\"Joined\"}";}
                    if(path.EndsWith("/join",StringComparison.Ordinal)){member=true;return "{\"teamId\":\""+Team+"\",\"state\":\"Joined\"}";}
                    if(path.EndsWith("/leave",StringComparison.Ordinal)){member=false;return "{\"teamId\":\""+Team+"\",\"state\":\"Left\"}";}
                    throw new InvalidOperationException("UnexpectedScriptedWrite109");
                }
                if(path.StartsWith("/v1/teams?",StringComparison.Ordinal)){
                    var row=FixtureTeam(false,badge);string json=JsonUtility.ToJson(new SocialTeams82{teams=new[]{row},myTeamId=member?Team:null,nextCursor="",hasMore=false});if(!member)json=json.Replace("\"myTeamId\":\"\"","\"myTeamId\":null");
                    if(omitBadge)json=json.Replace(",\"badgeId\":\""+badge+"\"","");if(invalidBadgeNext){invalidBadgeNext=false;json=json.Replace("\"badgeId\":\""+badge+"\"","\"badgeId\":\"unknown\"");}if(emptyMembershipNext){emptyMembershipNext=false;json=json.Replace("\"myTeamId\":null","\"myTeamId\":\"\"");}return json;
                }
                if(path=="/v1/teams/"+Team)return JsonUtility.ToJson(FixtureTeam(member,badge));
                if(path.StartsWith("/v1/messages/Team/",StringComparison.Ordinal))return "{\"messages\":[],\"nextCursor\":0,\"olderCursor\":0,\"unreadCount\":0,\"hasMore\":false,\"hasOlder\":false,\"hasNewer\":false}";
                throw new InvalidOperationException("UnexpectedScriptedRead109");
            }
            public void Dispose(){report.scriptedExchanges+=exchanges;report.actualHttpRequests+=client.VerificationRequests;session.Dispose();store.Dispose();}
        }
        [Serializable] sealed class CreateBody {public string commandId,name,description,badgeId;}
        static Report report;static string output;static TeamsAssets assets;
        static void Check(bool yes,string text){report.checks++;if(!yes)throw new InvalidOperationException(text);}
        static T Field<T>(object value,string name)=>(T)value.GetType().GetField(name,Private).GetValue(value);
        static void Set(object value,string name,object replacement)=>value.GetType().GetField(name,Private).SetValue(value,replacement);
        static void Invoke(object value,string name)=>value.GetType().GetMethod(name,Private).Invoke(value,null);
        static string Words(string text)=>string.Join(" ",(text??"").Split((char[])null,StringSplitOptions.RemoveEmptyEntries));
        static string Digest(string path){if(!Directory.Exists(path))return "Absent";using(var sha=SHA256.Create()){string rows=string.Join("\n",Directory.GetFiles(path,"*",SearchOption.AllDirectories).OrderBy(v=>v,StringComparer.Ordinal).Select(file=>file.Substring(path.Length)+":"+BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(file)))));return IdentityProtocol82.Sha(Encoding.UTF8.GetBytes(rows));}}
        static SocialTeam82 FixtureTeam(bool member,string badge="drop")=>new SocialTeam82{teamId=Team,ownerId=Other,name="Хранители дождя",description="Дружная команда деревни. Играем вместе!",badgeId=badge,memberCount=2,capacity=30,isMember=member,membershipVersion=member?new string('4',32):"",leaveRestrictionReason="",leaveClosesTeam=false,members=member?new[]{new SocialTeamMember82{playerId=Player,displayName="Иван",isOwner=false},new SocialTeamMember82{playerId=Other,displayName="Дарья",isOwner=true}}:null};
        static void Protocol(){
            var cloned=JsonUtility.FromJson<SocialTeams82>(JsonUtility.ToJson(new SocialTeams82{myTeamId=null}));report.rawJsonUtilityNullMembershipBecomesEmpty=cloned.myTeamId=="";
            Check(cloned.myTeamId==null||report.rawJsonUtilityNullMembershipBecomesEmpty,"Actual JsonUtility nullable membership clone is explicitly characterized");
            string cleanName,cleanDescription;string emoji32=string.Concat(Enumerable.Repeat("\U0001F327",32));
            Check(SocialBackendClient82.TryTeamDraft109("  "+emoji32+"  ","  hello  ",out cleanName,out cleanDescription)&&cleanName==emoji32&&cleanDescription=="hello"&&SocialBackendClient82.TeamTextLength109(emoji32)==32,"Actual draft rule counts Unicode scalars and preserves the server32 limit");
            foreach(var pair in new[]{new[]{"x",""},new[]{new string('x',33),""},new[]{"Valid",new string('d',161)},new[]{"Bad\nName",""},new[]{"\ud800",""}})Check(!SocialBackendClient82.TryTeamDraft109(pair[0],pair[1],out cleanName,out cleanDescription),"Invalid scalar/name/description draft is rejected");
            using(var fake=new Scripted()){
                foreach(string badge in TeamsAccessBadges109.Ids){SocialReply82<SocialMutation82> reply=null;string command=Guid.NewGuid().ToString("N");fake.client.CreateTeam(command,"Rain Keepers","",badge,r=>reply=r);var body=JsonUtility.FromJson<CreateBody>(fake.lastBody);Check(reply!=null&&reply.Succeeded&&body.badgeId==badge&&body.commandId==command,"Actual command parser/outbox preserves each approved cosmetic badge");Check(fake.client.PendingCommand==null,"Successful badge command clears only its exact outbox");report.cases++;}
                foreach(string invalid in new[]{"Drop","unknown","",null}){int before=fake.exchanges;SocialReply82<SocialMutation82> reply=null;fake.client.CreateTeam(Guid.NewGuid().ToString("N"),"Valid team","",invalid,r=>reply=r);Check(reply!=null&&!reply.Succeeded&&fake.exchanges==before&&fake.client.PendingCommand==null,"Invalid badge rejected before dispatch or durable mutation");report.cases++;}
                SocialReply82<SocialTeams82> read=null;fake.client.GetTeams("",20,"  Дождь & друзья  ",r=>read=r);Check(read!=null&&read.Succeeded&&fake.lastPath.EndsWith("&query="+Uri.EscapeDataString("Дождь & друзья"),StringComparison.Ordinal),"Actual search is normalized, URL encoded and sent to backend");
                fake.omitBadge=true;read=null;fake.client.GetTeams("",20,r=>read=r);Check(read!=null&&read.Succeeded&&TeamsAccessBadges109.Resolve(read.value.teams[0].badgeId)=="drop","Legacy server payload without badge retains drop fallback");fake.omitBadge=false;
                fake.invalidBadgeNext=true;read=null;fake.client.GetTeams("",20,r=>read=r);Check(read!=null&&!read.Succeeded,"Unknown server badge is rejected by actual response validation");
                fake.member=false;fake.emptyMembershipNext=true;read=null;fake.client.GetTeams("",20,r=>read=r);Check(read!=null&&!read.Succeeded,"Literal empty-string wire membership is rejected; local clone handling does not weaken transport");fake.session.Show(SocialPane82.Teams);fake.session.RefreshTeams();Check(fake.session.SelectedTeamId==null&&string.IsNullOrEmpty(fake.session.Snapshot<SocialTeams82>(SocialPane82.Teams)?.myTeamId),"Actual session preserves nonmembership through nullable projection cloning");
                int count=fake.exchanges;foreach(string bad in new[]{"Rain\nFriends",new string('x',129),"\ud800"}){read=null;fake.client.GetTeams("",20,bad,r=>read=r);Check(read!=null&&!read.Succeeded&&fake.exchanges==count,"Malformed/oversized search rejected without a request");}
                fake.unknownNext=true;SocialReply82<SocialMutation82> mutation=null;fake.client.CreateTeam(Guid.NewGuid().ToString("N"),"Durable team","Saved draft","moon",r=>mutation=r);Check(mutation!=null&&!mutation.Succeeded&&mutation.unknown&&fake.client.PendingCommand!=null,"Unknown badge-create outcome remains durably pending");string first=fake.lastBody;
                fake.client.ResumePending(r=>mutation=r);Check(mutation.Succeeded&&fake.lastBody==first&&fake.client.PendingCommand==null,"Exact retry preserves badge/name/command and clears the confirmed outbox");
                Check(fake.client.VerificationRequests==0,"Scripted protocol never constructs or sends an HTTP request");report.cases+=6;
            }
        }
        static void ImportRoles(){
            Check(assets&&assets.Find("TA_Background")&&assets.access&&assets.access.sprites.Length==37,"Actual lazy Teams lookup resolves the 37 imported R4 roles");
            string[] all=Directory.GetFiles("Assets/HeartOfTheRain/App/TeamsAccess/Art","*.png");Check(all.Length==69,"All 69 authored R4 PNGs are imported without deletion");
            foreach(string path in all){
                var importer=AssetImporter.GetAtPath(path) as TextureImporter;var sprite=AssetDatabase.LoadAssetAtPath<Sprite>(path);Check(importer&&sprite&&importer.alphaIsTransparency&&!importer.isReadable,"Actual R4 PNG imports as a non-readable alpha sprite "+Path.GetFileName(path));
                bool panel=importer.spriteBorder.sqrMagnitude>0;Check(panel?!importer.mipmapEnabled&&importer.filterMode==FilterMode.Bilinear:importer.mipmapEnabled&&importer.filterMode==FilterMode.Trilinear,"All imported roles use border-aware filtering "+Path.GetFileName(path));
                Check(importer.textureCompression==TextureImporterCompression.Uncompressed,"R4 fine artwork retains uncompressed import "+Path.GetFileName(path));
            }
            var sliced=new HashSet<string>(assets.access.slices.Select(s=>s.id),StringComparer.Ordinal);
            foreach(var item in assets.access.sprites){
                Check(item.sprite&&assets.Find(item.id)==item.sprite,"Live Teams lookup uses exact imported R4 sprite "+item.id);string path=AssetDatabase.GetAssetPath(item.sprite);var importer=AssetImporter.GetAtPath(path) as TextureImporter;
                Check(importer&&importer.textureType==TextureImporterType.Sprite&&importer.alphaIsTransparency&&!importer.isReadable,"R4 asset is a non-readable alpha sprite "+item.id);
                byte[] png=File.ReadAllBytes(path);int sourceWidth=png[16]<<24|png[17]<<16|png[18]<<8|png[19],sourceHeight=png[20]<<24|png[21]<<16|png[22]<<8|png[23];
                Check(importer.maxTextureSize>=Math.Max(sourceWidth,sourceHeight),"R4 import retains its authored PNG pixel budget "+item.id);
                if(sliced.Contains(item.id))Check(!importer.mipmapEnabled&&importer.filterMode==FilterMode.Bilinear&&item.sprite.border.sqrMagnitude>0,"Sliced R4 chrome keeps no mipmaps, bilinear filtering and nonzero border "+item.id);
                else Check(importer.mipmapEnabled&&importer.filterMode==FilterMode.Trilinear,"Minified detailed R4 artwork has mipmaps and trilinear filtering "+item.id);
            }
            foreach(string badge in TeamsAccessBadges109.Ids)Check(assets.Find(TeamsAccessBadges109.Asset(badge)),"All twelve durable badge IDs resolve authored sprites");report.cases++;
            var source=new Texture2D(2,2,TextureFormat.RGBA32,false);try{Check(source.LoadImage(File.ReadAllBytes(AssetDatabase.GetAssetPath(assets.Find("TA_Background")))),"Authored R4 backdrop is decoded without importer mutation");var pixels=source.GetPixels32();Check(pixels.All(p=>p.a==255),"Approved R4 backdrop is fully opaque; black authored details are valid artwork");report.authoredDarkPixels=pixels.Count(p=>p.r+p.g+p.b<=24);}finally{UnityEngine.Object.DestroyImmediate(source);}
            Check(!Painted(new Color32(255,0,255,255))&&!Painted(new Color32(250,0,250,255))&&Painted(new Color32(0,0,0,255))&&Painted(new Color32(0,30,100,255)),"Framebuffer coverage rejects unpainted magenta and accepts authored dark/blue pixels");
        }
        static void OrdinaryRoute(){
            GameObject owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));
            try{
                var home=owner.GetComponent<HomePage>();home.enabled=false;home.State.reduceMotion=true;var appearance=owner.AddComponent<ProfilePage>();appearance.enabled=false;Set(appearance,"home",home);
                var local=owner.AddComponent<TeamsPage>();local.enabled=false;local.home=home;local.assets=assets;Invoke(local,"Start");var page=owner.GetComponent<OnlineTeamsPage82>();page.enabled=false;
                Check(!assets.Access109Loaded,"Home and closed Teams initialization do not eagerly load the R4 resource");
                home.NavigationRequested.Invoke("teams");Check(page.IsVisible&&local.IsVisible&&!home.PresentationVisible,"Actual Home route opens R4 unavailable Teams");Check(local.ReviewSession==null&&page.VerificationSession==null&&!page.VerificationPending,"Ordinary local mode fabricates no membership/session/pending command");
                Check(assets.Access109Loaded,"Actual first Teams rendering lazily loads the R4 resource");
                string state=JsonUtility.ToJson(home.State);foreach(string action in new[]{"access-find","access-create","create-submit","badge-open","badge:moon","badge-confirm","search","join:"+Team,"detail:"+Team,"invite","leave","confirm","resume-pending"})page.Request(action);
                Check(page.VerificationSession==null&&!page.VerificationPending&&local.ReviewSession==null&&JsonUtility.ToJson(home.State)==state,"Unavailable R4 actions cannot mutate membership or the local game");
                page.Request("home");Check(!page.IsVisible&&home.PresentationVisible,"Actual R4 Home action restores Home");report.cases++;
            }finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
        // Remaining action/layout checks use the same actual page and renderer;
        // no profile-host initialization or ordinary identity store is involved.
        static void ComponentActions(){
            using(var fake=new Scripted()){
                var owner=new GameObject("Teams109 actual component scripted-service fixture");var eventOwner=new GameObject("Teams109 isolated EventSystem");var previousEvents=EventSystem.current;var previousSelection=previousEvents?previousEvents.currentSelectedGameObject:null;var events=eventOwner.AddComponent<EventSystem>();
                // EventSystem lacks ExecuteAlways: explicit edit-mode lifecycle
                // registration is required before its public current setter.
                if(EventSystem.current!=events)typeof(EventSystem).GetMethod("OnEnable",Private).Invoke(events,null);EventSystem.current=events;Check(EventSystem.current==events,"Isolated Editor EventSystem is registered before focus checks");
                try{
                    var page=owner.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,fake.session,fake.Dispatch);page.Show();page.VerificationPump();Check(fake.session.Snapshot<SocialTeams82>(SocialPane82.Teams)!=null,"Actual page loads directory through actual session/parser");
                    page.Request("access-create");Check(page.VerificationFrame.content.elements.Any(e=>e.id=="online-team-name-input"),"Actual Create tab exposes editable name");
                    events.SetSelectedGameObject(page.VerificationNodes["online-team-name-input"].gameObject);page.Request("badge-open");Check(page.VerificationFrame.overlay.elements.Count(e=>e.action!=null&&e.action.StartsWith("badge:",StringComparison.Ordinal))==12,"Actual badge picker exposes twelve bound actions");Check(events.currentSelectedGameObject==page.VerificationNodes["online-badge-confirm"].gameObject,"Badge modal focuses its own confirm instead of blocked form input");page.VerificationNodes["online-badge-moon"].GetComponent<Button>().onClick.Invoke();page.Request("badge-cancel");
                    Check(Field<string>(page,"badgeId")=="drop"&&events.currentSelectedGameObject==page.VerificationNodes["online-badge-choose"].gameObject,"Cancelling badge draft preserves selection and restores a safe Button focus");page.Request("badge-open");page.Request("badge:moon");page.Request("badge-confirm");Check(Field<string>(page,"badgeId")=="moon"&&events.currentSelectedGameObject==page.VerificationNodes["online-badge-choose"].gameObject,"Confirming picker applies cosmetic badge and restores Button focus");
                    Set(page,"nameDraft","   ");int writes=fake.posts;page.Request("create-submit");Check(fake.posts==writes,"Invalid blank create name cannot write");
                    Set(page,"nameDraft","Native Rain");foreach(string invalidDescription in new[]{new string('x',161),"\ud800"}){Set(page,"descriptionDraft",invalidDescription);page.Request("create-submit");Check(fake.posts==writes&&Field<string>(page,"descriptionDraft")==invalidDescription&&Field<string>(page,"inputErrorField")=="description","Invalid description preserves its draft and cannot write");var error=page.VerificationFrame.content.elements.Single(e=>e.id=="online-description-error");var input=page.VerificationFrame.content.elements.Single(e=>e.id=="online-team-description-input");Check(error.y>=input.y+input.height&&error.y-input.y-input.height<50&&Words(error.text)==Words(TeamsAccessText109.T("service_invalid_description")),"Description error retains exact localized words next to its own input");}
                    Set(page,"nameDraft","Native Rain");Set(page,"descriptionDraft","Synthetic component fixture");page.Request("create-submit");Check(fake.posts==writes+1&&fake.badge=="moon"&&fake.member,"Actual Create action sends selected badge once");page.VerificationPump();
                    Check(fake.session.SelectedTeamId==Team&&fake.session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.isMember==true,"Successful create refresh binds server-projected member state");
                    page.Request("tab-info");page.VerificationPump();Check(page.VerificationFrame.content.elements.Any(e=>e.action=="leave"),"Actual member info retains Leave");
                    writes=fake.posts;page.Request("invite");Check(fake.posts==writes&&page.VerificationFrame.overlay.elements.Count>0&&events.currentSelectedGameObject==page.VerificationNodes["invite-close"].gameObject,"Current112 invitation dialog focuses its close action without a backend mutation");page.Request("cancel");Check(events.currentSelectedGameObject==page.VerificationNodes["online-invite"].gameObject,"Cancelling Invite restores its Button without clipboard access");
                    page.Request("leave");Check(fake.posts==writes,"Leave requires explicit confirmation");page.Request("cancel");Check(fake.posts==writes&&fake.member,"Cancel leave preserves membership");Set(page,"leaveMotionAt113",(double)-1000000);page.VerificationPump();Check(Field<string>(page,"modal")==""&&events.currentSelectedGameObject==page.VerificationNodes["online-leave"].gameObject,"Completed current113 cancel restores Leave focus without mutation");page.Request("leave");fake.unknownNext=true;page.Request("leave-confirm113");Check(fake.member&&fake.session.PendingCommand!=null,"Unknown Leave does not optimistically remove authoritative membership");string leaveBody=fake.lastBody;fake.session.RefreshTeam();Check(fake.member&&fake.session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.isMember==true&&fake.session.PendingCommand?.body==leaveBody,"Authoritative refresh preserves uncertain Leave and its exact intent");page.Request("leave-close113");Set(page,"leaveMotionAt113",(double)-1000000);Set(page,"leaveAutoChecked113",true);page.VerificationPump();page.Request("resume-pending");page.VerificationPump();Check(!fake.member&&fake.posts==writes+2&&fake.postBodies.Last()==leaveBody,"Confirmed Leave retry sends the same intent once per explicit retry");
                    page.Request("access-find");Set(page,"searchDraft","  Rain & friends  ");page.Request("search");page.VerificationPump();Check(fake.paths.Any(p=>p.Contains("query="+Uri.EscapeDataString("Rain & friends"))),"Actual search action forwards normalized query");
                    page.Request("detail:"+Team);Check(page.VerificationFrame.chrome.elements.Any(e=>e.action=="close-details"),"Actual directory detail action displays fetched team body with pinned close");
                    writes=fake.posts;fake.rejectNext=true;page.Request("join:"+Team);var rejected=fake.session.PendingCommand;string notice=Field<string>(page,"mutationNotice109");Check(!fake.member&&rejected!=null&&notice.Length>0,"Rejected Join retains nonmember authority, failure and pending command");fake.session.RefreshTeam();Check(fake.session.PendingCommand?.body==rejected.body&&Field<string>(page,"mutationNotice109")==notice&&page.VerificationFrame.chrome.elements.Any(e=>(e.text??"").Contains(notice)),"Rejected Join feedback remains rendered after authoritative refresh while pending intent remains");string discardError;Check(fake.client.AcknowledgeAndDiscardPending(rejected.commandId,true,out discardError),"Explicit synthetic owner acknowledgement clears rejected intent for next test");
                    writes=fake.posts;fake.unknownNext=true;page.Request("join:"+Team);Check(fake.posts==writes+1&&fake.session.PendingCommand!=null,"Uncertain Join remains pending");page.Request("create-submit");page.Request("join:"+Team);Check(fake.posts==writes+1,"Pending command prevents unrelated/double enrollment");string pendingBody=fake.lastBody;page.Request("resume-pending");page.VerificationPump();Check(fake.member&&fake.session.PendingCommand==null&&fake.postBodies[fake.postBodies.Count-1]==pendingBody,"Actual pending recovery retries exact enrollment intent");
                    page.Request("leave");fake.rejectNext=true;page.Request("leave-confirm113");rejected=fake.session.PendingCommand;fake.session.RefreshTeam();Check(rejected!=null&&fake.member&&fake.session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.isMember==true&&fake.session.PendingCommand?.body==rejected.body&&page.VerificationFrame.overlay.elements.Any(e=>e.action=="leave-check113"),"Current113 rejected transport preserves membership, exact intent and visible status-check recovery");Check(fake.client.AcknowledgeAndDiscardPending(rejected.commandId,true,out discardError),"Explicit synthetic acknowledgement clears rejected Leave intent");page.Request("leave-close113");Set(page,"leaveMotionAt113",(double)-1000000);page.VerificationPump();page.Request("leave");page.Request("leave-confirm113");page.VerificationPump();Check(!fake.member&&!Field<bool>(page,"inspectDetails")&&page.VerificationFrame.chrome.elements.Any(e=>e.action=="access-find"),"Details to Join to confirmed Leave returns to Find without stale detail state: member="+fake.member+" inspected="+Field<bool>(page,"inspectDetails")+" selected="+(fake.session.SelectedTeamId??"NULL"));
                    Check(fake.client.VerificationRequests==0,"Component script never opens a network request");report.cases+=12;page.Hide(false);
                }finally{events.SetSelectedGameObject(null);UnityEngine.Object.DestroyImmediate(owner);typeof(EventSystem).GetMethod("OnDisable",Private).Invoke(events,null);UnityEngine.Object.DestroyImmediate(eventOwner);if(previousEvents){EventSystem.current=previousEvents;previousEvents.SetSelectedGameObject(previousSelection);}Check(EventSystem.current==(previousEvents?previousEvents:null)&&(!previousEvents||previousEvents.currentSelectedGameObject==previousSelection),"Isolated focus fixture restores prior EventSystem and selection");}
            }
        }
        static void OfflineBadgeDraft(){
            var owner=new GameObject("Teams badge offline draft verification");
            try{
                var page=owner.AddComponent<OnlineTeamsPage82>();page.enabled=false;
                page.ConfigureViewForVerification(assets,new OnlineTeamsView82{connected=false,unconfigured=true,unavailableReason=OnlineTeamsText82.T("OnlineSetup")});
                page.ClearViewForVerification();page.VerificationViewport(360,640);page.Show();page.Request("access-create");
                Check(page.VerificationNodes["online-badge-choose"].GetComponent<Button>().interactable,"Offline Create permits local badge selection");
                Check(page.VerificationNodes["online-team-name-input"].GetComponent<InputField>().interactable&&page.VerificationNodes["online-team-description-input"].GetComponent<InputField>().interactable,"Offline Create permits local draft editing");
                Check(!page.VerificationNodes["online-create-submit"].GetComponent<Button>().interactable,"Offline Create never submits without a social service");
                page.Request("badge-open");Check(page.VerificationNodes.ContainsKey("online-badge-grid"),"Offline badge picker opens without a session");
                page.Request("badge:well");page.Request("badge-confirm");
                Check(Field<string>(page,"badgeId")=="well"&&page.VerificationFrame.content.elements.Single(e=>e.id=="online-draft-badge").asset=="TA_Badge_well","Offline badge choice updates the Create preview without a network request");
                page.Hide(false);report.cases++;
            }finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
        static void SetView(object view,string name,object value){var field=view.GetType().GetField(name);if(field==null)throw new InvalidOperationException("R4VisualFieldMissing109:"+name);field.SetValue(view,value);}
        static OnlineTeamsView82 Visual(string state){
            var view=new OnlineTeamsView82{connected=true,selfId=Player,directory=new SocialTeams82{teams=new[]{FixtureTeam(false,"drop"),new SocialTeam82{teamId=Other,ownerId=Other,name="Village Friends",description="A synthetic directory fixture.",badgeId="well",memberCount=30,capacity=30}},nextCursor="",hasMore=false},status=""};
            SetView(view,"badgeId","moon");SetView(view,"badgeDraft","moon");SetView(view,"nameDraft","Хранители дождя");SetView(view,"descriptionDraft","Играем вместе и бережём деревню.");SetView(view,"nameCount",14);SetView(view,"searchQuery","");
            SetView(view,"inviteText","Хранители дождя\n"+Team);
            if(state=="Unavailable"){view.connected=false;view.unconfigured=true;view.directory=null;view.unavailableReason=OnlineTeamsText82.T("OnlineSetup");}
            if(state=="Create"||state=="Badges"){SetView(view,"accessCreate",true);if(state=="Badges")view.modal="badge";}
            if(state=="Details")SetView(view,"details",FixtureTeam(false,"lantern"));
            if(state=="Member"||state=="Invite"||state=="Leave"){view.team=FixtureTeam(true,"moon");view.tab=1;view.confirmationName=view.team.name;if(state=="Invite")view.modal="invite";if(state=="Leave")view.modal="leave";}
            if(state=="Pending"){view.pending=true;SetView(view,"mutationError",OnlineTeamsText82.T("Rejected"));}return view;
        }
        static void Layouts(){
            var owner=new GameObject("Teams109 synthetic visual-only snapshots");bool firstFailureCaptured=false;
            try{
                var page=owner.AddComponent<OnlineTeamsPage82>();page.enabled=false;
                foreach(int locale in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2Int(360,800),new Vector2Int(720,1600),new Vector2Int(768,1024)})foreach(string state in new[]{"Unavailable","Find","Create","Badges","Details","Member","Invite","Leave","Pending"}){
                    GameLocale.Select(locale);page.ConfigureViewForVerification(assets,Visual(state));bool insets=size.x==360;page.VerificationViewport(size.x,size.y);page.VerificationSafeArea(insets?new Rect(0,24,size.x,size.y-54):new Rect(0,0,size.x,size.y));page.Show();PrepareCanvas(page,size);
                    page.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();Field<ScrollRect>(page,"scroll").verticalNormalizedPosition=1;Canvas.ForceUpdateCanvases();
                    var row=new Row{state=state,locale=locale,width=size.x,height=size.y,safeInsets=insets};report.rows.Add(row);report.layoutsAttempted++;
                    try{
                        ValidateGeometry(page,state,locale);
                        if(locale==4&&((size.x==720&&new[]{"Unavailable","Find","Create","Badges","Details","Member"}.Contains(state))||(size.x==768&&new[]{"Find","Badges"}.Contains(state))))Capture(page,size,state+"_ru_"+size.x+".png");
                        row.passed=true;report.layouts++;
                    }catch(Exception error){report.errors.Add("Visual-only "+state+"/locale"+locale+"/"+size+": "+error.Message);if(!firstFailureCaptured){firstFailureCaptured=true;try{Capture(page,size,"FirstFailure_"+state+"_locale"+locale+"_"+size.x+".png");}catch(Exception captureError){report.errors.Add("Bounded first-failure Editor capture: "+captureError.Message);}}}
                    finally{page.Hide(false);page.ClearViewForVerification();}
                }
            }finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
        static void PrepareCanvas(OnlineTeamsPage82 page,Vector2Int size){var canvas=page.VerificationCanvas;canvas.renderMode=RenderMode.WorldSpace;canvas.GetComponent<CanvasScaler>().enabled=false;float scale=canvas.scaleFactor;var rect=(RectTransform)canvas.transform;rect.anchorMin=rect.anchorMax=rect.pivot=Vector2.one*.5f;rect.localPosition=Vector3.zero;rect.localScale=Vector3.one;rect.sizeDelta=new Vector2(size.x/scale,size.y/scale);}
        static void ValidateGeometry(OnlineTeamsPage82 page,string state,int locale){
            var frame=page.VerificationFrame;Check(frame.width>0&&frame.height>0&&frame.viewportHeight>0,"Actual safe-area frame has positive budget");
            foreach(var layer in new[]{frame.chrome,frame.content,frame.overlay})foreach(var e in layer.elements){
                Check(e.width>0&&e.height>0&&!float.IsNaN(e.x+e.y+e.width+e.height),"Finite positive R4 element "+e.id);
                if(!page.VerificationNodes.TryGetValue(e.id,out var node))throw new InvalidOperationException("R4NodeMissing109:"+e.id);
                if(e.kind=="text"||e.kind=="lefttext"){
                    var text=node.GetComponent<Text>();Check(text&&!text.supportRichText&&text.font&&text.preferredWidth<=text.rectTransform.rect.width+1.5f&&text.preferredHeight<=text.rectTransform.rect.height+1.5f,"Actual localized text fits "+state+"/"+locale+"/"+e.id+" preferred="+text.preferredWidth+"x"+text.preferredHeight+" box="+text.rectTransform.rect.size);
                }
                if(!string.IsNullOrEmpty(e.asset)&&e.asset.StartsWith("TA_",StringComparison.Ordinal)){
                    if(e.kind=="cover109"){var raw=node.GetComponent<RawImage>();Check(raw&&raw.texture==assets.Find(e.asset).texture&&raw.uvRect.x>=0&&raw.uvRect.y>=0&&raw.uvRect.xMax<=1.001f&&raw.uvRect.yMax<=1.001f,"Actual cropped background binds imported texture with contained UVs");}
                    else{var image=node.GetComponent<Image>();Check(image&&image.sprite&&image.sprite==assets.Find(e.asset),"Actual R4 Image binds imported sprite "+e.id);if(e.sliced)Check(image.type==Image.Type.Sliced&&image.sprite.border.sqrMagnitude>0,"Actual R4 sliced panel has a valid imported border "+e.id);}
                }
                if(!string.IsNullOrEmpty(e.parent)){
                    var parent=layer.elements.Single(v=>v.id==e.parent);var parentScroll=node.parent?node.parent.GetComponent<ScrollRect>():null;bool scrollContent=parentScroll&&parentScroll.content==node;
                    Check(e.x>=-.2f&&e.x+e.width<=parent.width+.2f&&e.y>=-.2f&&(scrollContent||e.y+e.height<=parent.height+.2f),"Nested art/hit box fits its parent, or is explicit ScrollRect content "+e.id);
                }
                else if(layer!=frame.content&&e.id!="online-teams-background"&&e.id!="online-modal-shade"&&e.id!="country-shade")Check(e.x>=-.2f&&e.y>=-.2f&&e.x+e.width<=frame.width+.2f&&e.y+e.height<=frame.height+.2f,"Pinned/dialog node stays within actual safe frame "+state+"/"+e.id);
            }
            var buttons=page.VerificationNodes.Values.Select(n=>n.GetComponent<Button>()).Where(b=>b).ToArray();Check(buttons.Length>0,"Actual R4 state retains interactable renderer controls");
            var title=frame.chrome.elements.First(e=>e.id=="online-teams-title");var close=frame.chrome.elements.FirstOrDefault(e=>e.action=="close-details");if(close!=null)Check(title.x+title.width<=close.x+.1f||title.y+title.height<=close.y+.1f||close.y+close.height<=title.y+.1f,"Localized team title box reserves the pinned close control");
            foreach(var transfer in frame.content.elements.Where(e=>e.action!=null&&e.action.StartsWith("transfer:",StringComparison.Ordinal))){var name=frame.content.elements.Single(e=>e.id==transfer.id+"-name");var role=frame.content.elements.Single(e=>e.id==transfer.id+"-role");var panel=frame.content.elements.Single(e=>e.id==transfer.id+"-base");var open=frame.content.elements.Single(e=>e.id==transfer.id+"-open");Check(transfer.width>=panel.width-32.1f&&transfer.height>=48&&name.width>=panel.width-72.1f&&role.width>=panel.width-72.1f&&Math.Max(name.y+name.height,role.y+role.height)<transfer.y&&open.y+open.height<transfer.y,"Transfer action has its own full-width row below the complete member name/role/open region");}
            if(state=="Badges")Check(frame.overlay.elements.Count(e=>e.action!=null&&e.action.StartsWith("badge:",StringComparison.Ordinal))==12,"Visual picker renders twelve badges in actual UGUI");
            if(state=="Pending")Check(!buttons.Any(b=>b.interactable&&b.GetComponent<HomeControlLabel>()?.action=="create-submit"),"Pending visual state cannot expose active Create");
            if(state=="Pending")foreach(string id in new[]{"online-check","online-resume","online-forget"}){
                var hit=frame.chrome.elements.Single(e=>e.id==id);var label=frame.chrome.elements.Single(e=>e.id==id+"-label");var text=page.VerificationNodes[label.id].GetComponent<Text>();Check(Words(text.text)==Words(hit.label)&&label.fontSize==14&&text.fontSize>=9&&text.fontSize<=14&&hit.height>=48,"Recovery caption retains complete accessible words, adaptive14pt budget and full48-unit control");Check(text.cachedTextGenerator.lineCount>=1&&text.cachedTextGenerator.lineCount<=2,"Actual recovery caption has at most two generated lines");var mesh=text.canvasRenderer.GetMesh();Check(mesh&&mesh.vertexCount>=4,"Actual recovery glyph mesh is generated");var bounds=text.rectTransform.rect;Check(mesh.vertices.All(v=>v.x>=bounds.xMin-.5f&&v.x<=bounds.xMax+.5f&&v.y>=bounds.yMin-.5f&&v.y<=bounds.yMax+.5f),"Actual recovery glyph vertices remain inside caption bounds "+GameLocale.Current+"/"+id);
            }
        }
        static void Capture(OnlineTeamsPage82 page,Vector2Int size,string name){
            var canvas=page.VerificationCanvas;var rect=(RectTransform)canvas.transform;float scale=canvas.scaleFactor;rect.sizeDelta=new Vector2(size.x/scale,size.y/scale);Canvas.ForceUpdateCanvases();
            var background=page.VerificationNodes["online-teams-background"];Check(!background.GetComponent<RawImage>().maskable,"Full R4 background bypasses safe-content clipping");var corners=new Vector3[4];rect.GetWorldCorners(corners);foreach(var corner in corners){var p=background.InverseTransformPoint(corner);Check(p.x>=background.rect.xMin-.1f&&p.x<=background.rect.xMax+.1f&&p.y>=background.rect.yMin-.1f&&p.y<=background.rect.yMax+.1f,"Actual R4 background covers fixed capture canvas corners");}
            var root=new GameObject("Teams109 fixed offscreen camera");var camera=root.AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.magenta;camera.orthographic=true;camera.orthographicSize=size.y/(2*scale);camera.aspect=size.x/(float)size.y;camera.transform.position=canvas.transform.position-new Vector3(0,0,10);camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(size.x,size.y,24);target.Create();var oldActive=RenderTexture.active;var oldCamera=canvas.worldCamera;Texture2D pixels=null;
            try{camera.targetTexture=target;canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;pixels=new Texture2D(size.x,size.y,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,size.x,size.y),0,0);pixels.Apply();var data=pixels.GetPixels32();report.capturedSentinelPixels+=data.Count(p=>!Painted(p));
                string relative="Native/TeamsAccess109/"+name;File.WriteAllBytes(Path.Combine(output,relative),pixels.EncodeToPNG());report.captures.Add(relative);
                Check(Enumerable.Range(0,size.x).All(x=>Painted(data[x])&&Painted(data[(size.y-1)*size.x+x])),"R4 GPU top/bottom edges contain no unpainted sentinel");Check(Enumerable.Range(0,size.y).All(y=>Painted(data[y*size.x])&&Painted(data[y*size.x+size.x-1])),"R4 GPU side edges contain no unpainted sentinel");Check(data.All(Painted),"Opaque full-canvas R4 background leaves zero unpainted sentinel pixels");
            }finally{canvas.worldCamera=oldCamera;camera.targetTexture=null;RenderTexture.active=oldActive;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(root);}
        }
        static bool Painted(Color32 p)=>!(p.r>245&&p.g<10&&p.b>245);
        static Rect In(RectTransform child,RectTransform parent){var corners=new Vector3[4];child.GetWorldCorners(corners);var p=corners.Select(parent.InverseTransformPoint).ToArray();return Rect.MinMaxRect(p.Min(v=>v.x),p.Min(v=>v.y),p.Max(v=>v.x),p.Max(v=>v.y));}
        static bool Contains(Rect a,Rect b)=>b.xMin>=a.xMin-.25f&&b.xMax<=a.xMax+.25f&&b.yMin>=a.yMin-.25f&&b.yMax<=a.yMax+.25f;
        static void ScrollTo(ScrollRect scroll,float position){Canvas.ForceUpdateCanvases();scroll.Rebuild(CanvasUpdate.Prelayout);scroll.Rebuild(CanvasUpdate.PostLayout);scroll.verticalNormalizedPosition=position;Canvas.ForceUpdateCanvases();}
        static void ScrollReachability(){
            var owner=new GameObject("Teams109 independent actual ScrollRect reachability snapshots");
            try{
                var page=owner.AddComponent<OnlineTeamsPage82>();page.enabled=false;
                foreach(int locale in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2Int(720,1600),new Vector2Int(768,1024)})foreach(string state in new[]{"Create","Badges"}){
                    GameLocale.Select(locale);page.ConfigureViewForVerification(assets,Visual(state));page.VerificationViewport(size.x,size.y);page.VerificationSafeArea(size.x==720?new Rect(0,32,size.x,size.y-64):new Rect(0,0,size.x,size.y));page.Show();PrepareCanvas(page,size);page.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();
                    var canvas=(RectTransform)page.VerificationCanvas.transform;var fixedNodes=page.VerificationNodes.Where(p=>p.Key=="dock-bg"||p.Key.StartsWith("nav-",StringComparison.Ordinal)||p.Key.StartsWith("online-badge-confirm",StringComparison.Ordinal)||p.Key.StartsWith("online-badge-selection",StringComparison.Ordinal)).ToDictionary(p=>p.Key,p=>In(p.Value,canvas));
                    if(state=="Create"){
                        var scroll=Field<ScrollRect>(page,"scroll");var viewport=scroll.viewport;Check(scroll.enabled&&scroll.vertical&&!scroll.horizontal&&scroll.content.rect.height>viewport.rect.height,"Actual Create has enabled vertical scrolling and nonzero content range");ScrollTo(scroll,1);Check(Contains(viewport.rect,In(page.VerificationNodes["online-team-name-input"],viewport)),"Actual Create name input is fully visible at top");ScrollTo(scroll,0);var submit=page.VerificationNodes["online-create-submit"];Check(Contains(viewport.rect,In(submit,viewport))&&submit.GetComponent<Button>(),"Actual Create submit control is fully visible after bottom scroll");
                    }else{
                        var grid=page.VerificationNodes["online-badge-grid"];var scroll=grid.GetComponent<ScrollRect>();Check(scroll&&scroll.enabled&&scroll.vertical&&!scroll.horizontal&&scroll.content==page.VerificationNodes["online-badge-grid-content"]&&grid.GetComponent<RectMask2D>(),"Actual nested badge grid has its own clipped vertical ScrollRect");var seen=new HashSet<string>();
                        foreach(float position in new[]{1f,.5f,0f}){ScrollTo(scroll,position);foreach(string badge in TeamsAccessBadges109.Ids){var hit=page.VerificationNodes["online-badge-"+badge];if(Contains(grid.rect,In(hit,grid))){Check(hit.GetComponent<Button>()&&hit.GetComponent<Button>().interactable&&hit.GetComponent<HomeControlLabel>().action=="badge:"+badge,"Each reached actual badge button retains its exact action");seen.Add(badge);}}}
                        Check(seen.SetEquals(TeamsAccessBadges109.Ids),"Every one of twelve actual badge controls is fully reachable through real top/middle/bottom scrolling");Check(Contains(grid.rect,In(page.VerificationNodes["online-badge-raincloud"],grid)),"Final badge row is fully visible at actual bottom position");
                    }
                    foreach(var node in fixedNodes){var after=In(page.VerificationNodes[node.Key],canvas);Check(Math.Abs(after.x-node.Value.x)<.1f&&Math.Abs(after.y-node.Value.y)<.1f&&Math.Abs(after.width-node.Value.width)<.1f&&Math.Abs(after.height-node.Value.height)<.1f,"Actual scrolling leaves chrome/footer/navigation fixed: "+node.Key);}
                    report.cases++;report.layouts++;if(locale==4&&size.x==720)Capture(page,size,state+"_Bottom_ru_720.png");page.Hide(false);page.ClearViewForVerification();
                }
            }finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
        public static void Run()=>RunCore(false);
        public static void RunImport()=>RunCore(true);
        public static void RunScroll()=>RunCore(false,true);
        static void RunCore(bool importOnly,bool scrollOnly=false){
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW109_OUT")??"../Verification/Evidence/Review109");Directory.CreateDirectory(Path.Combine(output,"Native","TeamsAccess109"));report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};int locale=GameLocale.Current;bool hadLanguage=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int savedLanguage=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);string profiles=null,server=null,settings=null;Application.logMessageReceived+=Log;
            try{
                profiles=Digest(Path.Combine(Application.persistentDataPath,"Profiles"));server=Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));settings=Digest("ProjectSettings");Check(Application.unityVersion=="2022.3.62f3","Pinned main Editor remains Unity2022");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets&&!assets.Access109Loaded,"Reading ordinary TeamsAssets alone has no R4 dependency load");if(importOnly){report.scope="Actual Unity2022 first-import/role/resource verification only. New importer-meta normalization is retained separately by runner; no routing, service, rendering matrix, Android or provider acceptance.";ImportRoles();}else if(scrollOnly){report.scope="Actual Unity2022 component ScrollRect top/middle/bottom visibility in controlled synthetic Create/picker snapshots across five locales and phone/tablet. No HTTP, session, real team mutation, app/device or production acceptance.";ScrollReachability();}else{Protocol();OrdinaryRoute();ImportRoles();ComponentActions();OfflineBadgeDraft();Layouts();}Check(report.actualHttpRequests==0,"All actual-client fixtures remain HTTP/DNS free");
            }catch(Exception error){report.errors.Add(error.ToString());}
            finally{
                GameLocale.Select(locale);try{report.ordinaryProfilesPreserved=profiles!=null&&profiles==Digest(Path.Combine(Application.persistentDataPath,"Profiles"));Check(report.ordinaryProfilesPreserved,"Ordinary profiles remain byte-identical");report.serverReviewPreserved=server!=null&&server==Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));Check(report.serverReviewPreserved,"Ordinary managed stores remain byte-identical");report.settingsPreserved=settings!=null&&settings==Digest("ProjectSettings");Check(report.settingsPreserved,"Project settings remain byte-identical");report.languagePreferencePreserved=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==hadLanguage&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==savedLanguage;Check(report.languagePreferencePreserved,"Saved language key presence/value unchanged");}catch(Exception error){report.errors.Add(error.ToString());}Application.logMessageReceived-=Log;report.status=(report.errors.Count==0?"PASS_NATIVE_TEAMS_ACCESS":"FAIL_NATIVE_TEAMS_ACCESS")+(importOnly?"_IMPORT109":scrollOnly?"_SCROLL109":"109");File.WriteAllText(Path.Combine(output,"Native",importOnly?"TeamsAccess109_Import.json":scrollOnly?"TeamsAccess109_Scroll.json":"TeamsAccess109.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            }EditorApplication.Exit(report.errors.Count==0?0:1);
        }
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
    }
}
#endif
