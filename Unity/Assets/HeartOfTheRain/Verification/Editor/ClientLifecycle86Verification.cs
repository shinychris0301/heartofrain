#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.ServerAccount;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ServerRewards;

namespace HeartOfTheRain.Verification {
    // Actual Editor Play Mode coroutines/ordinary ProfileHost refresh, isolated
    // protected files and a scripted loopback503. Not Android or live services.
    [InitializeOnLoad] public static class ClientLifecycle86Verification {
        const string Key="HOTR.ClientLifecycle86";
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Row {public string name;public int notifications,identityRequests,walletRequests,explicitRetries;public bool passed;}
        [Serializable] sealed class Report {
            public string status,utc,unity,scope,ordinaryProfilesBefore,ordinaryProfilesAfter;
            public int checks,cases;public bool actualPlayMode=true,actualLoopbackWalletHttp=true,scriptedIdentity=true,android=false;
            public List<Row> rows=new List<Row>();public List<string> errors=new List<string>();
        }
        static Report report;static IEnumerator tests;static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();
        static bool started,finished;static double deadline;static string directory,output;static Fixture fixture;static WalletServer server;
        static ClientLifecycle86Verification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        static void Set(object owner,string name,object value)=>owner.GetType().GetField(name,Private).SetValue(owner,value);
        static T Get<T>(object owner,string name)=>(T)owner.GetType().GetField(name,Private).GetValue(owner);
        static void Property(object owner,string name,object value)=>owner.GetType().GetProperty(name).GetSetMethod(true).Invoke(owner,new[]{value});
        static void Need(bool value,string code){report.checks++;if(!value)throw new InvalidOperationException(code);}
        static IEnumerator Frames(int count){int until=Time.frameCount+count;while(Time.frameCount<until)yield return null;}
        static IEnumerator Until(Func<bool> predicate){double until=EditorApplication.timeSinceStartup+20;while(!predicate()){if(EditorApplication.timeSinceStartup>until)throw new InvalidOperationException("BoundedLifecycleWait");yield return null;}}
        static string Profiles(){string root=Path.Combine(Application.persistentDataPath,"Profiles");return IdentityProtocol82.Sha(!Directory.Exists(root)?"absent":string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p.Substring(root.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(p)))));}

        sealed class ScriptedIdentity:IIdentityTransport82 {
            public readonly List<string> requests=new List<string>();
            IdentityChallengeRequest82 request;Action<IdentityReply82<IdentityChallenge82>> waiting;
            public void Challenge(IdentityChallengeRequest82 value,Action<IdentityReply82<IdentityChallenge82>> done){if(waiting!=null)throw new InvalidOperationException("FixtureChallengeAlreadyPending");request=value;requests.Add(value.requestId);waiting=done;}
            public void Fail(){var callback=waiting;waiting=null;callback(IdentityReply82<IdentityChallenge82>.Fail("IdentityHttp503",true));}
            public void Succeed(){
                var challenge=new IdentityChallenge82{challengeId=Guid.NewGuid().ToString("N"),purpose=request.purpose,requestId=request.requestId,keyFingerprint=IdentityProtocol82.Fingerprint(request.publicKey),payloadDigest=request.payloadDigest,nonce=IdentityProtocol82.NewSecret(),algorithm="ES256-DER",serverUtc=DateTimeOffset.UtcNow.ToUnixTimeSeconds()};challenge.expiresAt=challenge.serverUtc+60;
                string json="{\"challengeId\":\""+challenge.challengeId+"\",\"expiresAt\":"+challenge.expiresAt+",\"keyFingerprint\":\""+challenge.keyFingerprint+"\",\"nonce\":\""+challenge.nonce+"\",\"payloadDigest\":\""+challenge.payloadDigest+"\",\"purpose\":\""+challenge.purpose+"\",\"requestId\":\""+challenge.requestId+"\"}";
                challenge.signingBytes=Convert.ToBase64String(Encoding.ASCII.GetBytes(IdentityProtocol82.Protocol+"\n"+json));var callback=waiting;waiting=null;callback(IdentityReply82<IdentityChallenge82>.Ok(challenge));
            }
            public void Submit(IdentityIntent82 intent,string challengeId,string signature,Action<IdentityReply82<IdentitySessionResponse82>> done){
                long now=DateTimeOffset.UtcNow.ToUnixTimeSeconds();done(IdentityReply82<IdentitySessionResponse82>.Ok(new IdentitySessionResponse82{requestId=intent.requestId,playerId=new string('a',32),familyId=new string('b',32),keyFingerprint=IdentityProtocol82.Fingerprint(intent.publicKey),accessToken=IdentityProtocol82.NewSecret(),accountState="Active",expiresAt=now+900,refreshExpiresAt=now+86400}));
            }
            public void Cancel(){waiting=null;}
        }
        sealed class WalletServer:IDisposable {
            readonly HttpListener listener=new HttpListener();readonly ManualResetEventSlim release=new ManualResetEventSlim(false);readonly Thread worker;
            int requests;volatile bool closed;public int Requests=>Volatile.Read(ref requests);public readonly string Origin;
            public WalletServer(){
                int port;var allocation=new TcpListener(IPAddress.Loopback,0);allocation.Start();port=((IPEndPoint)allocation.LocalEndpoint).Port;allocation.Stop();
                Origin="http://127.0.0.1:"+port;listener.Prefixes.Add(Origin+"/");listener.Start();worker=new Thread(Serve){IsBackground=true,Name="HOTR86 isolated wallet503"};worker.Start();
            }
            void Serve(){try{while(!closed){var context=listener.GetContext();Interlocked.Increment(ref requests);release.Wait(10000);if(closed){context.Response.Abort();break;}var bytes=Encoding.UTF8.GetBytes("{\"error\":\"fixture_wallet_unavailable\"}");context.Response.StatusCode=503;context.Response.ContentType="application/json";context.Response.ContentLength64=bytes.Length;context.Response.OutputStream.Write(bytes,0,bytes.Length);context.Response.Close();}}catch(Exception){/* Listener is stopped only by this fixture's Dispose. */}}
            public void Release()=>release.Set();
            public void Dispose(){closed=true;release.Set();listener.Stop();listener.Close();if(worker.IsAlive)worker.Join(1000);release.Dispose();}
        }
        sealed class Fixture:IDisposable {
            public readonly GameObject node;public readonly ServerGameSession session;public readonly PlayerProfileHost host;
            public readonly ServerGameplayConfiguration config;public EditorEphemeralIdentity82 vault;public ManagedIdentitySession82 identity;public ScriptedIdentity transport;
            public int notifications,suppressed;readonly Action changed;
            public Fixture(string name,string origin){
                node=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));node.name="Isolated Client86 "+name;
                var home=node.GetComponent<HomePage>();home.Build();host=node.AddComponent<PlayerProfileHost>();
                var assets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");
                host.VerificationRepository=new MemoryProfileRepository(PlayerProfile.New(assets.initialStock));host.VerificationAuthorityFactory=id=>new UnavailableGiftAuthority();host.Initialize(home,assets);
                session=node.AddComponent<ServerGameSession>();config=new ServerGameplayConfiguration{version=1,mode="ManagedGuestServer",origin=origin,identityScope="review-native-lifecycle-86",allowDevelopmentLoopback=true};Set(session,"config",config);
                Property(host,"ServerSession",session);Property(host,"Service",new ProfileService(session.Projection));Set(host,"serverRewards",ServerRewardsSession.Select(session));
                // Match the real Changed -> ApplyServerView -> Refresh caller.
                // Cap the old recursion in a regression run instead of crashing
                // the Editor. The corrected implementation never hits the cap.
                changed=()=>{notifications++;if(notifications>4){suppressed++;return;}typeof(PlayerProfileHost).GetMethod("ApplyServerView",Private).Invoke(host,null);};session.Changed+=changed;
            }
            public void Identity(){
                vault=new EditorEphemeralIdentity82();Set(session,"editorVault",vault);string own=Path.Combine(directory,Guid.NewGuid().ToString("N"));
                var selector=new AccountSelection83(new OriginBoundIdentityStore82(vault.CreateStore(Path.Combine(own,"selector.sealed")),config.origin+"|account-selector"),config.origin,config.identityScope);Set(session,"accountSelector",selector);Set(session,"accountSelection",selector.Read());
                transport=new ScriptedIdentity();identity=new ManagedIdentitySession82(vault.CreateKey(),new OriginBoundIdentityStore82(vault.CreateStore(Path.Combine(own,"identity.sealed")),config.origin),transport);Set(session,"identity",identity);
            }
            public void Unavailable(string code){
                Need(!session.Ready&&!session.Busy&&!Get<bool>(session,"bootstrapping")&&!host.Ready,code+"_FailsClosedAndReleasesGuards");
                var projection=session.Projection.Read();Need(projection.coins==0&&projection.stars==0&&projection.lives==0&&host.Service.Read().coins==0,code+"_NoLocalWalletFallback");
                Need(suppressed==0,code+"_NoBoundedLegacyRecursion");
            }
            public void Dispose(){session.Changed-=changed;UnityEngine.Object.DestroyImmediate(node);}
        }
        static IEnumerator Cases(){
            var row=new Row{name="SynchronousProtectedStoreFailureDoesNotReenter"};report.rows.Add(row);report.cases++;
            fixture=new Fixture("protected-store","http://127.0.0.1:18686");fixture.vault=new EditorEphemeralIdentity82();fixture.vault.Dispose();Set(fixture.session,"editorVault",fixture.vault);
            fixture.session.RetryInitialize();yield return Frames(5);
            fixture.Unavailable("ProtectedStoreFailure");Need(fixture.notifications==1&&fixture.session.LastError=="ServerIdentityUnavailable","OneSynchronousFailureNotificationOnly");
            fixture.session.RetryInitialize();yield return Frames(5);
            Need(fixture.notifications==2,"LaterExplicitProtectedStoreRetryRunsOnce");fixture.Unavailable("ProtectedStoreExplicitRetry");row.notifications=fixture.notifications;row.explicitRetries=1;row.passed=true;fixture.Dispose();fixture=null;

            row=new Row{name="AsyncIdentityFailureWaitsForExplicitExactRetry"};report.rows.Add(row);report.cases++;
            fixture=new Fixture("identity","http://127.0.0.1:18686");fixture.Identity();fixture.session.RetryInitialize();yield return Until(()=>fixture.transport.requests.Count==1);yield return Frames(3);
            Need(fixture.session.Busy&&Get<bool>(fixture.session,"bootstrapping")&&fixture.notifications==0,"IdentityRequestOwnsStartupUntilResponse");fixture.session.RetryInitialize();Need(fixture.transport.requests.Count==1,"BusyStartupCannotDispatchAnotherIdentityRequest");
            fixture.transport.Fail();yield return Until(()=>fixture.notifications>0);yield return Frames(5);fixture.Unavailable("AsyncIdentityFailure");Need(fixture.transport.requests.Count==1&&fixture.notifications==1&&fixture.identity.View.hasPending,"IdentityFailureRetainsOnePendingIntentWithoutAutoRetry");
            fixture.session.RetryInitialize();yield return Until(()=>fixture.transport.requests.Count==2);Need(fixture.transport.requests[0]==fixture.transport.requests[1],"ExplicitIdentityRetryRetainsImmutableRequestId");fixture.transport.Fail();yield return Until(()=>fixture.notifications==2);yield return Frames(5);fixture.Unavailable("AsyncIdentityExplicitRetry");Need(fixture.transport.requests.Count==2,"NoIdentityRetryLoopAfterSecondFailure");
            row.notifications=fixture.notifications;row.identityRequests=fixture.transport.requests.Count;row.explicitRetries=1;row.passed=true;fixture.Dispose();fixture=null;

            row=new Row{name="AsyncWalletFailureWaitsForExplicitRetry"};report.rows.Add(row);report.cases++;server=new WalletServer();fixture=new Fixture("wallet",server.Origin);fixture.Identity();
            IdentityReply82<IdentityView82> identified=null;fixture.identity.CreateGuest(Guid.NewGuid().ToString("N"),value=>identified=value);fixture.transport.Succeed();Need(identified?.Succeeded==true&&fixture.identity.HasAccess,"ScriptedIdentityPrimeOwnsRealProtectedSuccessor");
            fixture.session.RetryInitialize();yield return Until(()=>server.Requests==1);yield return Frames(3);Need(fixture.session.Busy&&fixture.notifications==0,"ActualWalletHttpOwnsStartupUntilResponse");fixture.session.RetryInitialize();Need(server.Requests==1,"BusyStartupCannotDispatchAnotherWalletRequest");
            server.Release();yield return Until(()=>fixture.notifications>0);yield return Frames(6);fixture.Unavailable("AsyncWalletFailure");Need(server.Requests==1&&fixture.notifications==1,"Wallet503DoesNotAutomaticallyLoopRequests");
            fixture.session.RetryInitialize();yield return Until(()=>server.Requests==2&&fixture.notifications==2);yield return Frames(6);fixture.Unavailable("AsyncWalletExplicitRetry");Need(server.Requests==2,"LaterExplicitWalletRetrySendsExactlyOneRequest");
            row.notifications=fixture.notifications;row.identityRequests=fixture.transport.requests.Count;row.walletRequests=server.Requests;row.explicitRetries=1;row.passed=true;fixture.Dispose();fixture=null;server.Dispose();server=null;
        }
        public static void Run(){
            if(EditorApplication.isPlayingOrWillChangePlaymode)throw new InvalidOperationException("Client86RequiresOwnedEditorPlayMode");
            SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;
        }
        static void Tick(){
            if(finished){if(!EditorApplication.isPlayingOrWillChangePlaymode){EditorApplication.update-=Tick;if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);}return;}
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            try{
                if(!started){started=true;deadline=EditorApplication.timeSinceStartup+120;directory=Path.GetFullPath("../.verification-cache/Launch82/ClientLifecycle86/"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);
                    report=new Report{status="FAIL_NATIVE_CLIENT_LIFECYCLE86",utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,scope="Actual pinned Editor Play Mode ServerGameSession and ordinary PlayerProfileHost Changed/Refresh callback; synchronous unavailable native ephemeral protected store, held scripted managed-identity replies with real isolated encrypted files/CNG key, and real Unity HTTP receiving a delayed in-process loopback503. Requires one failure notification/request per explicit attempt, unchanged identity retry ID and zero local wallet fallback. Not Android Keystore/restart, hosted auth/backend, live provider, full startup route, visual approval or performance proof."};report.ordinaryProfilesBefore=Profiles();Need(Application.unityVersion=="2022.3.62f3","PinnedEditor");tests=Cases();stack.Push(tests);
                }
                if(EditorApplication.timeSinceStartup>deadline)throw new InvalidOperationException("Client86Deadline");
                for(int budget=0;budget<512;budget++){
                    if(stack.Count==0){Finish();return;}var top=stack.Peek();if(!top.MoveNext()){(stack.Pop() as IDisposable)?.Dispose();continue;}if(top.Current is IEnumerator nested)stack.Push(nested);else return;
                }throw new InvalidOperationException("Client86NestedWorkBound");
            }catch(Exception error){report?.errors.Add(error is InvalidOperationException?error.Message:error.GetType().Name);Finish();}
        }
        static void Finish(){
            if(finished)return;finished=true;
            while(stack.Count>0)try{(stack.Pop() as IDisposable)?.Dispose();}catch(Exception){}
            try{fixture?.Dispose();server?.Dispose();}catch(Exception){report.errors.Add("Client86FixtureCleanup");}
            report.ordinaryProfilesAfter=Profiles();try{Need(report.ordinaryProfilesBefore==report.ordinaryProfilesAfter,"OrdinaryProfileFilesUnchanged");}catch(Exception){report.errors.Add("OrdinaryProfileFilesChanged");}
            if(report.errors.Count==0)report.status="PASS_NATIVE_CLIENT_LIFECYCLE86";
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_CLIENT86_OUTPUT")??"../Verification/Evidence/ClientLifecycle86");Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native","ClientLifecycle86.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));SessionState.EraseBool(Key);EditorApplication.update-=Tick;
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);else EditorApplication.isPlaying=false;
        }
    }
}
#endif
