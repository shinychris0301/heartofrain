#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.Teams;

namespace HeartOfTheRain.Verification
{
    public static partial class Social82Verification
    {
        [Serializable] sealed class Report {
            public string status, utc, unity, firstPlayerHash, secondPlayerHash, ordinaryProfilesBefore, ordinaryProfilesAfter, scope;
            public int checks, cases, socialRequests, signedRequests, walletReads, duplicateMessageReceipts, protectedResumeCount, receiptReconciliationCount, explicitDiscardCount, cachedViewChecks, layoutCases, actualPageCaptures, rankGlyphChecks, rankFixtureChecks, paragraphGlyphChecks, reportPromptChecks, pagingTransportChecks, visibleReadChecks, blockedPageChecks;
            public List<int> socialStatuses = new List<int>(), signedStatuses = new List<int>();
            public bool rawNullSelfMaterializesAsEmptyDto115;public bool ordinaryProfilesUnchanged, languagePreferenceUnchanged, normalProfileIntegrated = false, localEconomyMutated = false;
            public bool androidKeystore = false, actualHttp = true, gameplayPlayMode = false;
            public List<string> passed = new List<string>(), errors = new List<string>();
            public List<string> captures = new List<string>();
        }
        sealed class CleanupAction : IDisposable { Action action;public CleanupAction(Action action){this.action=action;}public void Dispose(){var value=action;action=null;value?.Invoke();} }
        static Report report;
        static readonly Stack<IEnumerator> stack = new Stack<IEnumerator>();
        static readonly Queue<IEnumerator> dispatched = new Queue<IEnumerator>();
        static readonly List<IDisposable> cleanup = new List<IDisposable>();
        static readonly List<SocialBackendClient82> clients = new List<SocialBackendClient82>();
        static readonly List<IdentityHttpTransport82> identities = new List<IdentityHttpTransport82>();
        static AsyncOperation waiting; static double deadline; static bool finished, hadLanguage; static int language;
        static string temporary;
        static string Root => Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_SOCIAL82_OUTPUT") ?? "../Verification/Evidence/Launch82");
        static string Id() => Guid.NewGuid().ToString("N");
        static void Check(bool valid, string label) { report.checks++; if(!valid) throw new InvalidOperationException(label); }
        static void Passed(string label) { report.cases++; report.passed.Add(label); }
        static void Dispatch(IEnumerator value) { dispatched.Enqueue(value); }
        static string ProfilesHash() {
            string root = Path.Combine(Application.persistentDataPath, "Profiles");
            if(!Directory.Exists(root)) return IdentityProtocol82.Sha("absent");
            string value = string.Join("\n", Directory.GetFiles(root, "*", SearchOption.AllDirectories).OrderBy(x => x, StringComparer.Ordinal)
                .Select(path => path.Substring(root.Length).Replace('\\', '/') + ":" + IdentityProtocol82.Sha(File.ReadAllBytes(path))));
            return IdentityProtocol82.Sha(Encoding.UTF8.GetBytes(value));
        }
        static void Tick() {
            try {
                if(EditorApplication.timeSinceStartup > deadline) throw new TimeoutException("Bounded social HTTP suite timed out");
                if(waiting != null) { if(!waiting.isDone) return; waiting = null; }
                if(stack.Count == 0) { Finish(); return; }
                var value = stack.Peek(); bool advanced = value.MoveNext();
                if(!advanced) { stack.Pop(); (value as IDisposable)?.Dispose(); }
                else if(value.Current is IEnumerator child) stack.Push(child); else if(value.Current is AsyncOperation operation) waiting = operation;
                while(dispatched.Count != 0) stack.Push(dispatched.Dequeue());
            } catch(Exception error) { report.errors.Add("Social HTTP: " + error.GetType().Name + ": " + error.Message); Finish(); }
        }
        static void Finish() {
            if(finished) return; finished = true; EditorApplication.update -= Tick;
            while(stack.Count != 0) (stack.Pop() as IDisposable)?.Dispose();
            while(dispatched.Count != 0) (dispatched.Dequeue() as IDisposable)?.Dispose();
            foreach(var value in clients) { report.socialRequests += value.VerificationRequests; report.socialStatuses.AddRange(value.VerificationStatuses); }
            foreach(var value in identities) { report.signedRequests += value.VerificationRequestCount; report.signedStatuses.AddRange(value.VerificationStatuses); }
            for(int n = cleanup.Count - 1; n >= 0; n--) try { cleanup[n].Dispose(); } catch(Exception) { }
            cleanup.Clear(); clients.Clear(); identities.Clear(); waiting = null;
            try {
                report.ordinaryProfilesAfter = ProfilesHash(); report.ordinaryProfilesUnchanged = report.ordinaryProfilesBefore == report.ordinaryProfilesAfter;
                report.languagePreferenceUnchanged = PlayerPrefs.HasKey(GameLocale.PreferenceKey) == hadLanguage && PlayerPrefs.GetInt(GameLocale.PreferenceKey, -1) == language;
                Check(report.ordinaryProfilesUnchanged && report.languagePreferenceUnchanged, "Ordinary local profile files and language preference unchanged");
            } catch(Exception) { report.errors.Add("Local profile/preference audit failed"); }
            report.utc = DateTime.UtcNow.ToString("o"); report.status = report.errors.Count == 0 ? "PASS_NATIVE_SOCIAL82_HTTP" : "FAIL_NATIVE_SOCIAL82_HTTP";
            string folder = Path.Combine(Root, "Native"); Directory.CreateDirectory(folder);
            File.WriteAllText(Path.Combine(folder, "Social82_HTTP.json"), JsonUtility.ToJson(report, true), new UTF8Encoding(false));
            if(Application.isBatchMode) EditorApplication.Exit(report.errors.Count == 0 ? 0 : 1);
        }
        static IEnumerator Call<T>(Action<Action<SocialReply82<T>>> call, Action<T> check) where T : class {
            SocialReply82<T> reply = null; bool complete = false; call(value => { reply = value; complete = true; });
            while(!complete) yield return null;
            Check(reply != null && reply.Succeeded, "Actual typed social HTTP response succeeds"); check?.Invoke(reply.value);
        }
        static IEnumerator Guest(ManagedIdentitySession82 session) {
            IdentityReply82<IdentityView82> reply = null; bool complete = false;
            session.CreateGuest(Id(), value => { reply = value; complete = true; }); while(!complete) yield return null;
            Check(reply != null && reply.Succeeded && session.HasAccess && session.View.hasSession, "Actual managed guest with protected device-key journal");
        }
        static ManagedIdentitySession82 Manager(string origin, EditorEphemeralIdentity82 vault, string path) {
            var transport = new IdentityHttpTransport82(origin, Dispatch, true); identities.Add(transport); cleanup.Add(transport);
            var session = new ManagedIdentitySession82(vault.CreateKey(), vault.CreateStore(path), transport); cleanup.Add(session); return session;
        }
        static SocialBackendClient82 Client(string origin, ManagedIdentitySession82 session, EditorEphemeralIdentity82 vault, string path) {
            var store = vault.CreateStore(path); cleanup.Add(store);
            var client = new SocialBackendClient82(origin, () => session.HasAccess ? new SocialAccess82(session.View.playerId, session.AccessToken) : null,
                Dispatch, store, true, true); clients.Add(client); cleanup.Add(client); return client;
        }
        static IEnumerator Wallet(string origin, ManagedIdentitySession82 session, Action<RuStoreServerWallet> check) {
            var client = new RuStoreBackendClient(origin, session.AccessToken, session.View.playerId, true, true, Dispatch); cleanup.Add(client);
            PayReply<RuStoreServerWallet> reply = null; bool complete = false; client.GetWallet(value => { reply = value; complete = true; });
            while(!complete) yield return null; report.walletReads++;
            Check(reply != null && reply.Succeeded && reply.value.coins == 1250 && reply.value.lives == 5 && reply.value.revision == 1 && !reply.value.localProfileMutated && !reply.value.normalUnityProfileIntegrated,
                "Social operations leave authoritative genesis wallet unchanged"); check?.Invoke(reply.value);
        }
        static void ParserChecks() {
            var type=typeof(SocialBackendClient82).Assembly.GetType("HeartOfTheRain.App.OnlineSocial.SocialJson82",true);var read=type.GetMethod("Read");var flag=type.GetMethod("Flag");
            var good=read.Invoke(null,new object[]{"{\"flag\":false,\"text\":\"\\ud83d\\ude00\"}"});
            Check(good!=null&&!(bool)flag.Invoke(null,new[]{good,(object)"flag"}),"Strict parser retains actual false and valid surrogate pairs");
            foreach(string json in new[]{"null","[]","{\"flag\":true,\"flag\":false}","{\"value\":NaN}","{\"value\":1.0}","{\"text\":\"\\ud800\"}","{\"text\":\"\\u  41\"}","{}x"}) {
                bool rejected=false;try{read.Invoke(null,new object[]{json});}catch(System.Reflection.TargetInvocationException error){rejected=error.InnerException is FormatException;}
                Check(rejected,"Malformed/ambiguous bounded JSON is rejected");
            }
            foreach(string json in new[]{"{}","{\"flag\":null}","{\"flag\":\"false\"}","{\"flag\":0}"}) {
                bool rejected=false;try{flag.Invoke(null,new[]{read.Invoke(null,new object[]{json}),(object)"flag"});}catch(System.Reflection.TargetInvocationException error){rejected=error.InnerException is FormatException;}
                Check(rejected,"Missing/null/nonboolean flags never become JsonUtility false defaults");
            }
            Passed("Native strict JSON parser negative controls");
            int selected=GameLocale.Current;try{for(int n=0;n<5;n++){GameLocale.Select(n);var prompt=OnlinePlayersText82.T("ReviewHint");Check(prompt==new[]{"Send this report for review?","¿Enviar esta denuncia para revisión?","Envoyer ce signalement pour examen ?","Diese Meldung zur Prüfung senden?","Отправить жалобу на рассмотрение?"}[n],"Report confirmation asks for submission without promising configured staff");report.reportPromptChecks++;}}finally{GameLocale.Select(selected);}
        }
        static void Click(OnlineTeamsPage82 page,string id) {
            RectTransform node;Check(page.VerificationNodes.TryGetValue(id,out node),"Actual connected button exists: "+id);var button=node.GetComponent<Button>();Check(button&&button.interactable,"Actual connected button is enabled");button.onClick.Invoke();
        }
        static IEnumerator PageReady(OnlineTeamsPage82 page) {
            do{page.VerificationPump();yield return null;}while(page.VerificationPending);
            Check(page.IsVisible,"Actual connected Teams page remains visible");
        }
        static OnlinePlayersPage82 Players(string origin,ManagedIdentitySession82 owner,EditorEphemeralIdentity82 vault,string outbox) {
            var assets=AssetDatabase.LoadAssetAtPath<HeartOfTheRain.App.Leaderboard.LeaderboardAssets>("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset");Check(assets,"Approved ranking artwork is bound");
            var go=new GameObject("Actual connected Players82");var page=go.AddComponent<OnlinePlayersPage82>();cleanup.Add(new CleanupAction(()=>{if(go)UnityEngine.Object.DestroyImmediate(go);}));
            var service=new SocialPageSession82(Client(origin,owner,vault,outbox));cleanup.Add(service);page.ConfigureForVerification(assets,service,Dispatch);return page;
        }
        static void MedalCounterexamples(){
            var assets=AssetDatabase.LoadAssetAtPath<HeartOfTheRain.App.Leaderboard.LeaderboardAssets>("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset");var go=new GameObject("Explicit medal1-3 layout fixture");
            try{var surface=new OnlineSocialSurface82(go.transform,assets.Find,assets.journey.home.regularFont,assets.journey.home.boldFont,_=>{},_=>"",(_,__)=>{});
                var values=new[]{1L,2L,3L}.Select(value=>new SocialRank82{playerId=value.ToString("x32"),displayName="Fixture",score=4-(int)value,rank=value}).ToArray();
                var view=new OnlinePlayersView82{connected=true,selfId=Id(),ranks=new SocialLeaderboard82{entries=values},ranks115=new SocialRankRefresh115{scope="global",regionCode="",scoreSource="server_verified_completed_levels",tiesShareRank=true,entries=values,nextOffset=values.Length}};var frame=OnlinePlayersLayout82.Build(420,900,view);surface.Apply(420,900,1,new Rect(0,0,420,900),900,frame.viewportY,frame.viewportHeight,frame.chrome,frame.content,frame.overlay,false,true);Canvas.ForceUpdateCanvases();
                foreach(var value in values){string id="online-rank-"+value.playerId;CheckRankGlyph(surface.nodes,id,value.rank);report.rankFixtureChecks++;}
            }finally{UnityEngine.Object.DestroyImmediate(go);}Passed("Explicit native medal1–3 fixture preserves numeric text/glyph/rectangle ownership");
        }
        static void Click(OnlinePlayersPage82 page,string id){RectTransform node;Check(page.VerificationNodes.TryGetValue(id,out node),"Actual player/friend button exists");var button=node.GetComponent<Button>();Check(button&&button.interactable,"Actual player/friend button is enabled");button.onClick.Invoke();}
        static IEnumerator PageReady(OnlinePlayersPage82 page){do{page.VerificationPump();yield return null;}while(page.VerificationPending);Check(page.IsVisible,"Actual connected player component remains visible");}
        static void CapturePage(OnlinePlayersPage82 page,string name){
            int w=720,h=1280;page.VerificationViewport(w,h);var cameraObject=new GameObject("Social Players verification camera");var camera=cameraObject.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.025f,.07f,.12f);camera.orthographic=true;cameraObject.transform.position=new Vector3(0,0,-10);
            var target=new RenderTexture(w,h,24,RenderTextureFormat.ARGB32);var old=RenderTexture.active;Texture2D pixels=null;
            try{target.Create();camera.targetTexture=target;page.VerificationCanvas.renderMode=RenderMode.ScreenSpaceCamera;page.VerificationCanvas.worldCamera=camera;page.VerificationCanvas.planeDistance=1;Canvas.ForceUpdateCanvases();camera.Render();PlayerGlyphChecks(page);RenderTexture.active=target;pixels=new Texture2D(w,h,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,w,h),0,0);pixels.Apply();string relative="Native/SocialPlayers82/"+name+".png",path=Path.Combine(Root,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllBytes(path,pixels.EncodeToPNG());report.captures.Add(relative);report.actualPageCaptures++;Check(page.GetComponentsInChildren<Text>(true).All(value=>!value.supportRichText),"All actual friend/direct-message user text disables rich text");}
            finally{RenderTexture.active=old;page.VerificationCanvas.worldCamera=null;page.VerificationCanvas.renderMode=RenderMode.ScreenSpaceOverlay;camera.targetTexture=null;target.Release();UnityEngine.Object.DestroyImmediate(target);if(pixels)UnityEngine.Object.DestroyImmediate(pixels);UnityEngine.Object.DestroyImmediate(cameraObject);}
        }
        static void PlayerGlyphChecks(OnlinePlayersPage82 page){
            foreach(var row in page.VerificationSession.Snapshot<SocialRankRefresh115>(SocialPane82.GlobalRanks115)?.entries??new SocialRank82[0]){
                string id="online-rank-"+row.playerId;RectTransform node;if(!page.VerificationNodes.TryGetValue(id+"-rank",out node))continue;CheckRankGlyph(page.VerificationNodes,id,row.rank);report.rankGlyphChecks++;
            }
            RectTransform paragraph;if(page.VerificationNodes.TryGetValue("online-direct-empty",out paragraph)){
                var label=paragraph.GetComponent<Text>();var generator=new TextGenerator();generator.Populate(label.text,label.GetGenerationSettings(label.rectTransform.rect.size));
                Check(label.text.Replace('\n',' ')==OnlinePlayersText82.T("EmptyDirect")&&label.preferredHeight<=paragraph.rect.height+1&&generator.characterCountVisible>=label.text.Count(c=>!char.IsWhiteSpace(c)),"Actual multi-line direct empty-state retains the full copy, fits and generates its final word");
                Check(label.text.All(c=>char.IsWhiteSpace(c)||label.font.HasCharacter(c)),"Actual direct empty-state font covers every character");report.paragraphGlyphChecks++;
            }
        }
        static void CheckRankGlyph(IReadOnlyDictionary<string,RectTransform> nodes,string id,long rank){
            RectTransform node;Check(nodes.TryGetValue(id+"-rank",out node),"Numeric rank overlay exists for every medal/card");var label=node.GetComponent<Text>();
            Check(label&&label.text==rank.ToString(System.Globalization.CultureInfo.InvariantCulture),"Numeric overlay equals the supplied rank, including medals1–3");
            var generator=new TextGenerator();generator.Populate(label.text,label.GetGenerationSettings(label.rectTransform.rect.size));Check(generator.characterCountVisible>=label.text.Length&&label.text.All(c=>label.font.HasCharacter(c)),"Native numeric rank glyphs are generated");
            var owner=nodes[rank<=3?id+"-medal":id+"-base"];var bounds=owner.rect;var corners=new Vector3[4];node.GetWorldCorners(corners);Check(corners.All(point=>{var local=owner.InverseTransformPoint(point);return local.x>=bounds.xMin-1&&local.x<=bounds.xMax+1&&local.y>=bounds.yMin-1&&local.y<=bounds.yMax+1;}),"Native numeric rank rectangle remains inside its approved medal/card");
        }
        static void CapturePage(OnlineTeamsPage82 page,string name) {
            int w=720,h=1280;page.VerificationViewport(w,h);var cameraObject=new GameObject("Social Teams verification camera");var camera=cameraObject.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.025f,.07f,.12f);camera.orthographic=true;cameraObject.transform.position=new Vector3(0,0,-10);
            var target=new RenderTexture(w,h,24,RenderTextureFormat.ARGB32);var old=RenderTexture.active;Texture2D pixels=null;
            try {
                target.Create();camera.targetTexture=target;page.VerificationCanvas.renderMode=RenderMode.ScreenSpaceCamera;page.VerificationCanvas.worldCamera=camera;page.VerificationCanvas.planeDistance=1;Canvas.ForceUpdateCanvases();camera.Render();
                RenderTexture.active=target;pixels=new Texture2D(w,h,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,w,h),0,0);pixels.Apply();
                string relative="Native/SocialTeams82/"+name+".png",path=Path.Combine(Root,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllBytes(path,pixels.EncodeToPNG());report.captures.Add(relative);report.actualPageCaptures++;
                Check(page.GetComponentsInChildren<Text>(true).All(value=>!value.supportRichText),"All actual connected user text disables rich-text interpretation");
            } finally {RenderTexture.active=old;page.VerificationCanvas.worldCamera=null;page.VerificationCanvas.renderMode=RenderMode.ScreenSpaceOverlay;camera.targetTexture=null;target.Release();UnityEngine.Object.DestroyImmediate(target);if(pixels)UnityEngine.Object.DestroyImmediate(pixels);UnityEngine.Object.DestroyImmediate(cameraObject);}
        }
        static void LayoutChecks(OnlineTeamsPage82 page) {
            var service=page.VerificationSession;var team=service.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);var directory=service.Snapshot<SocialTeams82>(SocialPane82.Teams);var chat=service.Snapshot<SocialMessages82>(SocialPane82.TeamChat);int before=GameLocale.Current;
            try {for(int locale=0;locale<5;locale++){GameLocale.Select(locale);foreach(var size in new[]{new Vector2(320,568),new Vector2(420,900),new Vector2(720,1280),new Vector2(900,2000),new Vector2(1200,1600)})foreach(string mode in new[]{"chat","info","create","compose","forget","pending","directory"}) {
                var model=new OnlineTeamsView82{connected=true,selfId=service.PlayerId,team=mode=="directory"?null:team,directory=directory,chat=chat,tab=mode=="info"?1:0,modal=new[]{"create","compose","forget"}.Contains(mode)?mode:"",pending=mode=="pending",status=mode=="pending"?OnlineTeamsText82.T("Pending"):""};
                var frame=OnlineTeamsLayout82.Build(size.x,size.y,model);report.layoutCases++;
                var ids=new HashSet<string>();foreach(var section in new[]{frame.chrome,frame.content,frame.overlay})foreach(var item in section.elements){Check(ids.Add(item.id),"Connected layout IDs are unique");Check(!float.IsNaN(item.x)&&!float.IsNaN(item.y)&&item.width>0&&item.height>0&&item.x>=-.01f&&item.y>=-.01f&&item.x+item.width<=frame.width+.01f&&item.y+item.height<=(section==frame.content?frame.content.height:frame.height)+.01f,"Connected cards/buttons/text remain inside assigned content");}
                Check(frame.viewportY>=0&&frame.viewportHeight>0&&frame.viewportY+frame.viewportHeight<=frame.height,"Connected scroll viewport remains bounded");
                if(mode=="forget"){var warning=frame.overlay.elements.First(row=>row.id=="online-forget-warning");var confirm=frame.overlay.elements.First(row=>row.id=="online-modal-confirm");Check(warning.y+warning.height<=confirm.y-5,"Explicit discard warning stays above confirmation buttons");}
            }}}finally{GameLocale.Select(before);}
            Passed("Five-locale connected Teams layout bounds at five portrait sizes");
        }
        static IEnumerator Checks(string origin) {
            ParserChecks();MedalCounterexamples();
            var aVault = new EditorEphemeralIdentity82(); var bVault = new EditorEphemeralIdentity82(); cleanup.Add(aVault); cleanup.Add(bVault);
            var a = Manager(origin, aVault, Path.Combine(temporary, "first-identity.sealed"));
            var b = Manager(origin, bVault, Path.Combine(temporary, "second-identity.sealed"));
            yield return Guest(a); yield return Guest(b);
            string first = a.View.playerId, second = b.View.playerId;
            Check(first != second && a.View.keyFingerprint != b.View.keyFingerprint, "Two independent actual managed identities");
            report.firstPlayerHash = IdentityProtocol82.Sha(first); report.secondPlayerHash = IdentityProtocol82.Sha(second);
            string aOutbox = Path.Combine(temporary, "first-social.sealed"), bOutbox = Path.Combine(temporary, "second-social.sealed");
            var one = Client(origin, a, aVault, aOutbox); var two = Client(origin, b, bVault, bOutbox);PagingParserChecks(one);
            yield return Wallet(origin, a, null); yield return Wallet(origin, b, null);
            yield return Call<SocialMutation82>(done => one.UpdateProfile(Id(), "Хранитель дождя", true, done), value => Check(value.displayName == "Хранитель дождя" && value.leaderboardOptIn, "Russian public name and explicit ranking opt-in bound"));
            yield return Call<SocialMutation82>(done => two.UpdateProfile(Id(), "Друг дождя", true, done), value => Check(value.displayName == "Друг дождя", "Second profile updated through real HTTP"));
            yield return Call<SocialProfile82>(done => one.GetProfile(second, done), value => Check(value.playerId == second && value.completedLevels == 0, "Public peer profile excludes unverified records"));
            yield return Call<SocialRelationship82>(done=>one.GetRelationship(second,done),value=>Check(value.state=="None"&&value.playerId==second&&value.requestId==null,"Exact-ID relationship does not infer from a partial friend list"));
            Passed("Actual managed guests and public profiles");

            int playersLocale=GameLocale.Current;cleanup.Add(new CleanupAction(()=>GameLocale.Select(playersLocale)));GameLocale.Select(4);
            var firstPlayers=Players(origin,a,aVault,Path.Combine(temporary,"first-team-page.sealed"));
            var secondPlayers=Players(origin,b,bVault,Path.Combine(temporary,"second-team-page.sealed"));
            firstPlayers.Show();yield return PageReady(firstPlayers);CapturePage(firstPlayers,"Players_Russian");
            Click(firstPlayers,"online-privacy118");Click(firstPlayers,"online-ranking-consent");yield return PageReady(firstPlayers);var optedOut115=firstPlayers.VerificationSession.Snapshot<SocialRankRefresh115>(SocialPane82.GlobalRanks115);Check(optedOut115!=null&&!optedOut115.hasSelfEntry&&optedOut115.entries.All(row=>row.playerId!=first),"Actual115 opt-out removes own public rank without changing name");
            yield return Call<SocialRankRefresh115>(done=>one.GetRanksRefresh115("global",0,20,done),value=>{report.rawNullSelfMaterializesAsEmptyDto115|=value.selfEntry!=null&&string.IsNullOrEmpty(value.selfEntry.playerId);Check(!value.hasSelfEntry&&string.IsNullOrEmpty(value.selfEntry?.playerId)&&!value.rewardGranted&&value.entries.All(row=>row.playerId!=first),"Strict actual115 wire false/null self entry retains typed absence, explicit opt-out and no reward");});
            Click(firstPlayers,"online-privacy118");Click(firstPlayers,"online-ranking-consent");yield return PageReady(firstPlayers);
            yield return Call<SocialRankRefresh115>(done=>one.GetRanksRefresh115("global",0,20,done),value=>Check(value.hasSelfEntry&&value.selfEntry!=null&&value.selfEntry.playerId==first&&value.selfEntry.score==0&&!value.rewardGranted,"Actual115 wire pinned self row is owner-bound and uses verified zero progression without reward"));
            yield return Call<SocialTeamRanksRefresh115>(done=>one.GetTeamRanksRefresh115("global",0,20,done),value=>{report.rawNullSelfMaterializesAsEmptyDto115|=value.selfEntry!=null&&string.IsNullOrEmpty(value.selfEntry.teamId);Check(!value.hasTeam&&!value.hasSelfEntry&&string.IsNullOrEmpty(value.selfEntry?.teamId)&&!value.rewardGranted,"Strict actual115 wire no-team false/null fields retain typed absence and fabricate no team or reward");});
            Click(firstPlayers,"online-primary-friends");yield return PageReady(firstPlayers);firstPlayers.VerificationNodes["online-player-code-input"].GetComponent<InputField>().text=second;Click(firstPlayers,"online-player-find");yield return PageReady(firstPlayers);CapturePage(firstPlayers,"FindPlayer_Russian");Click(firstPlayers,"online-player-main");yield return PageReady(firstPlayers);
            string requestId = null;
            yield return Call<SocialRequests82>(done=>two.GetRequests("",20,done),value=>{var incoming=value.requests.Single(row=>row.profile.playerId==first&&row.direction=="incoming");requestId=incoming.requestId;Check(IdentityProtocol82.Id(requestId),"Only authenticated recipient sees actual incoming request");});
            firstPlayers.Hide(false);secondPlayers.Show();yield return PageReady(secondPlayers);Click(secondPlayers,"online-primary-friends");yield return PageReady(secondPlayers);Click(secondPlayers,"online-friends-requests");yield return PageReady(secondPlayers);CapturePage(secondPlayers,"IncomingRequest_Russian");Click(secondPlayers,"online-request-"+requestId+"-accept");yield return PageReady(secondPlayers);secondPlayers.Hide(false);
            yield return Call<SocialFriends82>(done => one.GetFriends("", 20, done), value => Check(value.friends.Count(row => row.playerId == second) == 1, "Mutual friend appears once"));
            firstPlayers.Show();yield return PageReady(firstPlayers);CapturePage(firstPlayers,"Friends_Russian");Click(firstPlayers,"online-friend-"+second+"-message");yield return PageReady(firstPlayers);Click(firstPlayers,"online-direct-compose");for(int checkLocale=0;checkLocale<5;checkLocale++){GameLocale.Select(checkLocale);firstPlayers.VerificationViewport(720,1280);Canvas.ForceUpdateCanvases();PlayerGlyphChecks(firstPlayers);}GameLocale.Select(4);CapturePage(firstPlayers,"DirectComposer_Russian");firstPlayers.VerificationNodes["online-direct-input"].GetComponent<InputField>().text="Проверка личного сообщения";Click(firstPlayers,"online-player-confirm");yield return PageReady(firstPlayers);CapturePage(firstPlayers,"DirectChat_Russian");string uiMessageCommand=firstPlayers.VerificationLastCommand;firstPlayers.Hide(false);GameLocale.Select(playersLocale);
            yield return Call<SocialRelationship82>(done=>one.GetRelationship(second,done),value=>Check(value.state=="Friends"&&value.requestId==null,"Accepted relationship is independent of list pagination"));
            Passed("Actual friend request and recipient acceptance");

            string messageCommand = uiMessageCommand, message = null; long sequence = 0;
            yield return Call<SocialMutation82>(done => one.SendMessage(messageCommand, "Direct", second, "Проверка личного сообщения", done), value => { message = value.messageId; sequence = value.sequence; });
            yield return Call<SocialMutation82>(done => one.SendMessage(messageCommand, "Direct", second, "Проверка личного сообщения", done), value => { Check(value.messageId == message && value.sequence == sequence, "Exact HTTP duplicate returns one message receipt"); report.duplicateMessageReceipts++; });
            yield return Call<SocialMessages82>(done => two.GetMessages("Direct", first, 0, 20, done), value => Check(value.messages.Count(row => row.messageId == message) == 1 && value.unreadCount == 1, "Receiver sees one real direct message"));
            yield return Call<SocialMutation82>(done => two.MarkRead(Id(), "Direct", first, sequence, done), value => Check(value.through >= sequence, "Server read cursor advances"));
            yield return Call<SocialMessages82>(done => two.GetMessages("Direct", first, 0, 20, done), value => Check(value.unreadCount == 0, "Actual read cursor clears unread count"));
            yield return Call<SocialMutation82>(done => two.ReportMessage(Id(), message, "Other", "Verification fixture report", done), value => Check(IdentityProtocol82.Id(value.reportId), "Unprivileged report queues human review only"));
            Passed("Direct message, duplicate, read state and report");

            // Force a real remote commit followed by a protected local-confirm
            // failure. The encrypted pending intent must survive owner reopen.
            int writes = 0; aVault.VerificationCheckpoint = stage => { if(stage == "BeforeCommit" && ++writes == 2) throw new IOException("Controlled social confirmation failure"); };
            bool complete = false; SocialReply82<SocialMutation82> lost = null;
            one.SendMessage(Id(), "Direct", second, "Защищённое восстановление", value => { lost = value; complete = true; }); while(!complete) yield return null;
            Check(lost != null && !lost.Succeeded && one.PendingCommand != null, "Remote success remains pending when local confirmation fails");
            string savedCommand = one.PendingCommand.commandId;
            aVault.VerificationCheckpoint = null; one.Dispose(); one = Client(origin, a, aVault, aOutbox);
            Check(one.PendingCommand != null && one.PendingCommand.commandId == savedCommand, "Encrypted outbox retains exact immutable ID after reopen");
            yield return Call<SocialMutation82>(done => one.ResumePending(done), value => { Check(value.sequence > sequence, "Exact pending message receipt recovered"); report.protectedResumeCount++; });
            Check(one.PendingCommand == null, "Validated recovery clears protected pending flag");
            yield return Call<SocialMessages82>(done => two.GetMessages("Direct", first, 0, 20, done), value => Check(value.messages.Length == 2, "Lost local reply never adds a duplicate server message"));
            string ciphertext = Encoding.UTF8.GetString(File.ReadAllBytes(aOutbox));
            Check(!ciphertext.Contains(a.AccessToken) && !ciphertext.Contains("Защищённое восстановление"), "Protected social journal contains neither plaintext bearer nor message");
            Passed("Actual message commit and encrypted-outbox recovery");

            writes = 0; aVault.VerificationCheckpoint = stage => { if(stage == "BeforeCommit" && ++writes == 2) throw new IOException("Controlled receipt confirmation failure"); };
            complete = false; lost = null;
            one.SendMessage(Id(), "Direct", second, "Проверка квитанции", value => { lost = value; complete = true; }); while(!complete) yield return null;
            Check(lost != null && !lost.Succeeded && one.PendingCommand != null, "Second committed send retains pending ownership after local save failure");
            aVault.VerificationCheckpoint = null; complete = false; SocialReply82<SocialOperationReceipt82> receipt = null;
            one.ReconcilePending(value => { receipt = value; complete = true; }); while(!complete) yield return null;
            Check(receipt != null && receipt.Succeeded && receipt.value.status == "Committed" && receipt.value.response.sequence > sequence && one.PendingCommand == null,
                "Actual owner receipt GET confirms exact pending send without resubmitting"); report.receiptReconciliationCount++;
            yield return Call<SocialMessages82>(done => two.GetMessages("Direct", first, 0, 20, done), value => Check(value.messages.Length == 3, "Receipt recovery creates no second message"));
            complete = false; SocialReply82<SocialMutation82> rejected = null;
            one.RequestFriend(Id(), first, value => { rejected = value; complete = true; }); while(!complete) yield return null;
            Check(rejected != null && !rejected.Succeeded && one.PendingCommand != null, "Rejected write never silently forgets protected intent");
            savedCommand = one.PendingCommand.commandId; complete = false; receipt = null;
            one.ReconcilePending(value => { receipt = value; complete = true; }); while(!complete) yield return null;
            Check(receipt != null && receipt.Succeeded && receipt.value.status == "Absent" && one.PendingCommand != null, "Absent receipt is not treated as proof of failed submission");
            string discardError;
            Check(!one.AcknowledgeAndDiscardPending(savedCommand, false, out discardError) && one.PendingCommand != null, "Discard requires caller acknowledgement");
            Check(!one.AcknowledgeAndDiscardPending(Id(), true, out discardError) && one.PendingCommand != null, "Discard requires exact current pending ID");
            Check(one.AcknowledgeAndDiscardPending(savedCommand, true, out discardError) && one.PendingCommand == null, "Explicit acknowledged discard only clears local retry intent"); report.explicitDiscardCount++;
            Passed("Actual owner receipt reconciliation and explicit pending discard");

            long ownerGeneration = 1;
            var pageClient = Client(origin, b, bVault, Path.Combine(temporary, "second-page.sealed"));
            var page = new SocialPageSession82(pageClient, currentOwnerGeneration: () => ownerGeneration); cleanup.Add(page);
            Check(page.OpenDirect(first), "Controller explicitly opens selected direct channel"); while(page.Busy) yield return null;
            Check(page.Snapshot<SocialMessages82>(SocialPane82.DirectChat)?.messages.Length == 3 && page.Status(SocialPane82.DirectChat).state == SocialViewState82.Ready,
                "Controller caches actual typed messages without demo substitution"); report.cachedViewChecks++;

            GameLocale.Select(4);secondPlayers.ShowPlayer(first,true);yield return PageReady(secondPlayers);yield return VisibleReadChecks(secondPlayers,two,first);Click(secondPlayers,"online-direct-menu-"+message);CapturePage(secondPlayers,"ReportMessage_Russian");Click(secondPlayers,"online-player-confirm");yield return PageReady(secondPlayers);secondPlayers.Hide(false);
            firstPlayers.ShowPlayer(second);yield return PageReady(firstPlayers);Click(firstPlayers,"online-player-block");CapturePage(firstPlayers,"BlockPlayer_Russian");Click(firstPlayers,"online-player-confirm");yield return PageReady(firstPlayers);firstPlayers.Hide(false);GameLocale.Select(playersLocale);
            yield return Call<SocialMutation82>(done => one.Block(Id(), second, done), value => Check(value.blocked, "Actual connected block plus durable duplicate confirmed"));
            complete = false; SocialReply82<SocialMessages82> denied = null;
            two.GetMessages("Direct", first, 0, 20, value => { denied = value; complete = true; }); while(!complete) yield return null;
            Check(denied != null && !denied.Succeeded && denied.error == "SocialHttp404", "Blocked direct channel rejected by actual HTTP404");
            Check(page.RefreshDirectMessages(), "Controller rechecks existing cached channel"); while(page.Busy) yield return null;
            Check(page.Snapshot<SocialMessages82>(SocialPane82.DirectChat) == null && page.Status(SocialPane82.DirectChat).state == SocialViewState82.Rejected,
                "Permission rejection removes old private cached message bodies"); report.cachedViewChecks++;
            ownerGeneration++;
            Check(page.Snapshot<SocialMessages82>(SocialPane82.DirectChat) == null && page.Status(SocialPane82.DirectChat).state == SocialViewState82.Unauthenticated,
                "Changed managed identity generation invalidates all cached private views"); report.cachedViewChecks++; page.Dispose();
            yield return BlockedPageChecks(firstPlayers,second);
            yield return Call<SocialMutation82>(done => one.Unblock(Id(), second, done), value => Check(!value.blocked, "Explicit unblock commits without refriending"));
            yield return Call<SocialFriends82>(done => one.GetFriends("", 20, done), value => Check(value.friends.All(row => row.playerId != second), "Unblock never silently restores friendship"));
            Passed("Actual block rejection and explicit unblock");

            var art=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(art,"Approved Teams artwork is bound");
            var pageObject=new GameObject("Actual connected Teams82");var connected=pageObject.AddComponent<OnlineTeamsPage82>();cleanup.Add(new CleanupAction(()=>{if(pageObject)UnityEngine.Object.DestroyImmediate(pageObject);}));
            var connectedClient=Client(origin,a,aVault,Path.Combine(temporary,"first-team-page.sealed"));var connectedSession=new SocialPageSession82(connectedClient);cleanup.Add(connectedSession);
            connected.ConfigureForVerification(art,connectedSession,Dispatch);int localeBefore=GameLocale.Current;cleanup.Add(new CleanupAction(()=>GameLocale.Select(localeBefore)));GameLocale.Select(4);
            connected.Show();yield return PageReady(connected);CapturePage(connected,"NoTeam_Russian");
            Click(connected,"online-create");CapturePage(connected,"CreateTeam_Russian");
            connected.VerificationNodes["online-team-name-input"].GetComponent<InputField>().text="Команда дождя";
            connected.VerificationNodes["online-team-description-input"].GetComponent<InputField>().text="Проверка сервера";
            Click(connected,"online-create-submit");yield return PageReady(connected);
            string team=connectedSession.SelectedTeamId;Check(IdentityProtocol82.Id(team)&&connectedSession.Snapshot<SocialTeam82>(SocialPane82.TeamInfo).isMember,"Actual Create button creates and opens server membership");
            yield return Call<SocialMutation82>(done => two.JoinTeam(Id(), team, done), value => Check(value.teamId == team && value.state == "Joined", "Second identity joins actual team"));
            yield return Call<SocialTeam82>(done => one.GetTeam(team, done), value => Check(value.ownerId == first && value.memberCount == 2 && value.members.Length == 2, "Real team membership and owner bound"));
            yield return Call<SocialMutation82>(done => two.SendMessage(Id(), "Team", team, "Проверка командного чата", done), value => message = value.messageId);
            yield return Call<SocialMessages82>(done => one.GetMessages("Team", team, 0, 20, done), value => Check(value.messages.Any(row => row.messageId == message && row.authorId == second), "Real team chat visible to current member"));
            connected.Request("retry");yield return PageReady(connected);Click(connected,"online-details-close");yield return PageReady(connected);CapturePage(connected,"TeamChat_Russian");
            Click(connected,"online-tab-info");yield return PageReady(connected);CapturePage(connected,"TeamInfo_Russian");LayoutChecks(connected);
            Click(connected,"online-details-close");yield return PageReady(connected);Click(connected,"online-compose");CapturePage(connected,"Composer_Russian");
            connected.VerificationNodes["online-message-input"].GetComponent<InputField>().text="Сообщение из команды";Click(connected,"online-compose-send");yield return PageReady(connected);
            yield return Call<SocialMessages82>(done=>two.GetMessages("Team",team,0,20,done),value=>Check(value.messages.Count(row=>row.authorId==first&&row.text=="Сообщение из команды")==1,"Actual composer sends one server-owned team message"));
            Click(connected,"online-tab-info");yield return PageReady(connected);int beforeRestrictedLeave116=connectedClient.VerificationRequests;Click(connected,"online-leave");
            Check(!connected.VerificationNodes.ContainsKey("leave-action113")&&connectedSession.PendingCommand==null&&connectedClient.VerificationRequests==beforeRestrictedLeave116,"Current113 owner transfer restriction prevents every leave POST and pending write");
            Click(connected,"leave-close113");typeof(OnlineTeamsPage82).GetField("leaveMotionAt113",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).SetValue(connected,(double)-1000000);connected.VerificationPump();
            connected.VerificationNodes["online-summary-base"].GetComponentInParent<ScrollRect>().verticalNormalizedPosition=1;Canvas.ForceUpdateCanvases();
            // An explicit legacy-session command solely retains the original
            // real HTTP rejection/outbox/discard fixture; the current113 UI
            // above correctly prevents this request from being dispatched.
            Check(connectedSession.LeaveTeam(Id()),"Explicit legacy-session owner leave reaches the real HTTP refusal");while(connectedSession.Busy)yield return null;yield return PageReady(connected);
            Check(connectedSession.PendingCommand==null&&connectedSession.Snapshot<SocialTeam82>(SocialPane82.TeamInfo).ownerId==first,"A rejected owner leave is final: no durable intent remains, and the team and membership are unchanged");
            connected.Hide(false);GameLocale.Select(localeBefore);Passed("Actual current Teams buttons,113 no-write owner restriction, explicit legacy-session final refusal and enumerated native UGUI captures");
            yield return Call<SocialMutation82>(done => one.ManageMember("transfer", Id(), team, second, done), value => Check(value.action == "transfer", "Explicit ownership transfer is server-authorized"));
            yield return Call<SocialMutation82>(done => one.LeaveTeam(Id(), team, done), value => Check(value.state == "Left", "Former owner can leave after transfer"));
            Passed("Actual team membership, chat, transfer and leave");

            yield return Call<SocialRecords82>(done => one.GetRecords(0, 20, done), value => Check(value.completedLevels == 0 && value.firstClears.Length == 0 && !value.clientScoresAccepted, "Personal records use trusted progression only"));
            yield return Call<SocialLeaderboard82>(done => one.GetLeaderboard("global", 0, 100, done), value => Check(value.entries.Any(row => row.playerId == first) && value.entries.Any(row => row.playerId == second) && !value.rewardGranted, "Explicitly opted-in server standings with no prize grant"));
            yield return Call<SocialMutation82>(done => one.ReportPublicText(Id(), "Profile", second, "Other", "Verification fixture UGC report", done), value => Check(!value.automatedDecision && IdentityProtocol82.Id(value.reportId), "Profile report is human review, not automated enforcement"));
            string nonBmpName=string.Concat(Enumerable.Repeat("😀",20))+new string('\u0301',236),nonBmpMessage=string.Concat(Enumerable.Repeat("😀",999))+"Я",nonBmpMessageId=null;
            yield return Call<SocialMutation82>(done=>two.UpdateProfile(Id(),nonBmpName,true,done),value=>Check(value.displayName==nonBmpName,"Actual256-scalar non-BMP/combining name is accepted without a UTF16 cap regression"));
            yield return Call<SocialProfile82>(done=>two.GetProfile(second,done),value=>Check(value.displayName==nonBmpName,"Actual non-BMP public name round-trips"));
            yield return Call<SocialMutation82>(done=>two.SendMessage(Id(),"Team",team,nonBmpMessage,done),value=>nonBmpMessageId=value.messageId);
            yield return Call<SocialMessages82>(done=>two.GetMessages("Team",team,0,20,done),value=>Check(value.messages.Any(row=>row.messageId==nonBmpMessageId&&row.text==nonBmpMessage),"Actual1000-scalar non-BMP message round-trips"));
            int sentBefore=two.VerificationRequests;complete=false;rejected=null;
            two.SendMessage(Id(),"Team",team,"bad\ud800",value=>{rejected=value;complete=true;});while(!complete)yield return null;
            Check(rejected!=null&&!rejected.Succeeded&&two.VerificationRequests==sentBefore&&two.PendingCommand==null,"Malformed surrogate is rejected before dispatch and protected intent creation");
            yield return BoundedHistoryChecks(origin,b,bVault,two,team,nonBmpMessage);
            yield return Call<SocialMutation82>(done=>two.UpdateProfile(Id(),"Друг дождя",true,done),null);Passed("Actual Unicode scalar boundaries and malformed-input counterexample");
            yield return Wallet(origin, a, null); yield return Wallet(origin, b, null);
            Passed("Actual personal records, opt-in standings and unchanged economy");
        }
        public static void RunHttp() {
            report = new Report { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion,
                scope = "Actual native Editor UnityWebRequest HTTP with two independent managed guests, real ephemeral Windows P256 signatures and protected CAS social outboxes. Actual connected Players/Friends/Blocked/direct-message and Teams component button/render proof, bounded eight-row UI reads with explicit latest/older chat and rendered-current read acknowledgement, atomic ranking consent, mutual request acceptance, duplicate/protected lost-reply and owner-receipt recovery, explicit pending discard and controller privacy. Five-locale Teams layout bounds are separate from actual Russian camera captures enumerated in captures. No normal-selected-app Android/Keystore, gameplay Play Mode, production social hosting, moderator grant, real payment or local-profile/economy mutation claim." };
            try {
                string origin = Environment.GetEnvironmentVariable("HOTR_SOCIAL82_HTTP_ORIGIN");
                if(Environment.GetEnvironmentVariable("HOTR_SOCIAL82_HTTP_ALLOWED") != "1" || !RuStoreBackendClient.IsAllowedOrigin(origin, true) || !new Uri(origin).IsLoopback) throw new InvalidOperationException();
                temporary = Path.GetFullPath("../.verification-cache/Launch82/Social/" + Id()); Directory.CreateDirectory(temporary);
                report.ordinaryProfilesBefore = ProfilesHash(); hadLanguage = PlayerPrefs.HasKey(GameLocale.PreferenceKey); language = PlayerPrefs.GetInt(GameLocale.PreferenceKey, -1);
                finished = false; stack.Clear(); dispatched.Clear(); deadline = EditorApplication.timeSinceStartup + 300; stack.Push(Checks(origin)); EditorApplication.update += Tick;
            } catch(Exception) { report.errors.Add("Explicit isolated social HTTP fixture unavailable"); Finish(); }
        }
    }
}
#endif
