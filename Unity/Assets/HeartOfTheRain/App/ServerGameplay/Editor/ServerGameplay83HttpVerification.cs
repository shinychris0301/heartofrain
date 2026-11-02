#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.EndLevel;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ServerVerification;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.ServerRewards;
using HeartOfTheRain.App.Celebrations;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class ServerGameplay83HttpVerification {
        const string Key="HOTR.ServerGameplay83.Http";static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Report {
            public string status,utc,unity,scope,playerIdHash,firstAttemptId,continueAttemptId,continueFixtureSHA256,ordinaryProfilesBefore,ordinaryProfilesAfter;
            public int checks,playerActions,paidTools,paidContinues,restoredShopBoards,finalCoins,finalStars,finalLives,finalCompleted;
            public bool serverProfileRenameAndRecords,localAppearanceUnchanged;
            public bool controlledForegroundLifecycle116;public bool naturalVictoryObserved,naturalHomeRevealObserved,dailyRevealObserved,ordinaryRewardPages,portraitSettingsRestored;
            public int afterWinCoins,dailyClaimCoins,portraitWidth,portraitHeight;
            public bool readonlyHomeRewardBadges;public int homeMetadataBatches;
            public List<string> captures=new List<string>();
            public bool actualHttp=true,actualPinnedWorker=true,editorIdentityEphemeral=true,android=false,productionEnabled=false;
            public List<string> passed=new List<string>(),errors=new List<string>();
        }
        static Report report;static HomePage home;static HomeLevelFlow flow;static PlayerProfileHost host;static ServerGameSession server;static GameplayScreen game;
        static ReplayJob continuation;static int phase,index;static bool launched,finished,done,ok;static string why,output;static double deadline;static float oldTime;
        static ProfilePage profilePage;static string appearanceBefore;static bool leaderboardOptIn;
        static DailyGiftPage daily;static WellworksPage works;static RainCupPage cup;static ServerRewardsCoordinator rewards;
        static double pageAt;static bool victoryCaptured;static long rewardRevision;static Action settledDialogCheck;static string sleepToken,heldAttempt;static bool lastFocus=true,lastPause;
        static bool firstBadgeReadChecked;static int initialBadgeBatches;static int interstitialShows;static bool interstitialHomeLocked;
        // A scripted interstitial through the real level start. Everything after it must show none.
        sealed class ScriptedInterstitial:HeartOfTheRain.App.Advertising.IInterstitialProvider129 {
            public bool Installed=>true;public void Load(Action<bool> done)=>done(true);public void Dispose(){}
            public void Show(Action shown,Action done){interstitialShows++;interstitialHomeLocked=home&&home.PresentationVisible&&!home.PresentationInteractable;shown();done();}
        }
        static ServerGameplay83HttpVerification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        static T Field<T>(object owner,string name)=>(T)owner.GetType().GetField(name,Private).GetValue(owner);
        static object Call(object owner,string name,params object[] values)=>owner.GetType().GetMethod(name,Private).Invoke(owner,values);
        static Dictionary<string,RectTransform> Nodes(object page)=>Field<Dictionary<string,RectTransform>>(page,"nodes");
        static void Click(object page,string node){var button=Nodes(page)[node].GetComponent<Button>();Check(button&&button.isActiveAndEnabled&&button.interactable,"Actual reward button enabled: "+node);button.onClick.Invoke();}
        static object SizeGroup(){var assembly=typeof(UnityEditor.Editor).Assembly;var type=assembly.GetType("UnityEditor.GameViewSizes");var singleton=typeof(ScriptableSingleton<>).MakeGenericType(type).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return type.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(assembly.GetType("UnityEditor.GameViewSizeGroupType"),EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":"Standalone")});}
        static EditorWindow GameView()=>EditorWindow.GetWindow(typeof(UnityEditor.Editor).Assembly.GetType("UnityEditor.GameView"));
        static void SetPortrait(){
            var group=SizeGroup();var view=GameView();int first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);int previous=(int)view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).GetValue(view);
            var assembly=typeof(UnityEditor.Editor).Assembly;var size=Activator.CreateInstance(assembly.GetType("UnityEditor.GameViewSize"),BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic,null,new object[]{Enum.Parse(assembly.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),900,1600,"HOTR Gateway83 portrait"},null);
            group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{size});SessionState.SetInt(Key+".portraitFirst",first);SessionState.SetInt(Key+".portraitPrevious",previous);SessionState.SetBool(Key+".portrait",true);view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,first);view.Repaint();
        }
        static void RestorePortrait(){if(!SessionState.GetBool(Key+".portrait",false))return;var view=GameView();view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt(Key+".portraitPrevious",0));var group=SizeGroup();group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt(Key+".portraitFirst",0)});SessionState.EraseBool(Key+".portrait");}
        static void Capture(string name){
            Check(Screen.width==900&&Screen.height==1600,"Actual connected page capture uses portrait900x1600");
            var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).OrderBy(c=>c.sortingOrder).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();var node=new GameObject("Connected rewards native capture camera");node.transform.position=new Vector3(-10000,0,-10);var camera=node.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;Texture2D image=null;
            try{camera.targetTexture=target;foreach(var canvas in canvases){canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;image=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);image.ReadPixels(new Rect(0,0,target.width,target.height),0,0);image.Apply();string relative="Native/RewardPages/"+name+".png";Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(output,relative)));File.WriteAllBytes(Path.Combine(output,relative),image.EncodeToPNG());report.captures.Add(relative);}
            finally{for(int n=0;n<canvases.Length;n++){canvases[n].renderMode=RenderMode.ScreenSpaceOverlay;canvases[n].worldCamera=cameras[n];canvases[n].planeDistance=distances[n];}RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(image)UnityEngine.Object.Destroy(image);UnityEngine.Object.Destroy(node);Canvas.ForceUpdateCanvases();}
        }
        static void PageText(object page){var canvas=Field<Canvas>(page,"canvas");var text=canvas.GetComponentsInChildren<Text>().Where(t=>t.isActiveAndEnabled&&!string.IsNullOrEmpty(t.text)).ToArray();Check(text.Length>5,"Actual reward page has visible text");foreach(var label in text){Check(!label.supportRichText,"Reward text is literal: "+label.name);Check(label.preferredHeight<=label.rectTransform.rect.height+1.5f,"Actual reward text fits: "+label.name);}}
        static void HomeBadge(string id,string expected){Check((id=="daily"?home.State.dailyStatus:id=="wellworks"?home.State.wellworksStatus:home.State.cupStatus)==expected,"Authoritative Home "+id+" badge: "+expected);var nodes=Field<Dictionary<string,RectTransform>>(home,"nodes");RectTransform node;Check(nodes.TryGetValue(id+"-status",out node)&&node.GetComponent<Text>().text==GameLocale.Element(id+"-status",expected),"Actual Home "+id+" badge label matches metadata");}
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);report.passed.Add(label);}
        static string ProfileDigest(){
            string root=Path.Combine(Application.persistentDataPath,"Profiles");if(!Directory.Exists(root))return IdentityProtocol82.Sha("absent");
            var values=Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(path=>path.Substring(root.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(path)));
            return IdentityProtocol82.Sha(string.Join("\n",values));
        }
        public static void Run(){
            string origin=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_HTTP_ORIGIN");
            if(Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_HTTP_ALLOWED")!="1"||!HeartOfTheRain.App.RuStore.RuStoreBackendClient.IsAllowedOrigin(origin,true)||!new Uri(origin).IsLoopback)throw new InvalidOperationException("ExplicitIsolatedGatewayFixtureRequired");
            string fixture=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONTINUE_JOB");if(!File.Exists(fixture))throw new InvalidOperationException("SealedContinueFixtureRequired");
            string directory=Path.GetFullPath("../.verification-cache/ServerGameplay83/Client/"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);string config=Path.Combine(directory,"configuration.json");
            File.WriteAllText(config,JsonUtility.ToJson(new ServerGameplayConfiguration{version=1,mode="ManagedGuestServer",origin=origin,identityScope="review-native-http-83",allowDevelopmentLoopback=true,socialEnabled=true}),new UTF8Encoding(false));
            SessionState.SetString(Key+".previousConfig",Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG")??"");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",config);
            SessionState.SetBool(Key,true);SetPortrait();EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;
        }
        static void Launch(){
            launched=true;oldTime=Time.timeScale;Time.timeScale=1;deadline=EditorApplication.timeSinceStartup+720;
            report=new Report{utc=DateTime.UtcNow.ToString("O"),unity=Application.unityVersion,scope="Actual Editor Play Mode ordinary gameplay, Profile and reward pages selected by external configuration; real managed guest HTTP/server wallet/pinned Windows replay worker. Labelled operator L8 unlock/seed, paid Hammer, Swap, Quit, natural OutOfMoves/Shop durable-board reconstruction/900+5/verified win, natural M67 return and Home reveal, actual Daily Gift claim, authenticated locked Wellworks/practice Cup at completed8. Portrait UGUI captures are actual ordinary page state, not injected page views. Editor identity is ephemeral; no process-restart, Android, physical input, live payments/competition, visual approval or performance certification."};
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_OUTPUT")??"../Verification/Evidence/ServerGameplay83");Directory.CreateDirectory(Path.Combine(output,"Native"));
            report.ordinaryProfilesBefore=ProfileDigest();string path=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONTINUE_JOB");continuation=JsonUtility.FromJson<ReplayJob>(File.ReadAllText(path));report.continueFixtureSHA256=IdentityProtocol82.Sha(File.ReadAllBytes(path));
            Check(continuation.level==8&&continuation.actions.Any(a=>a.kind=="Continue")&&continuation.starting.All(n=>n==0),"sealed real natural L8 Continue history");
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");var owner=UnityEngine.Object.Instantiate(prefab);home=owner.GetComponent<HomePage>();flow=owner.AddComponent<HomeLevelFlow>();flow.home=home;flow.assets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");
        }
        static void Complete(bool value,string message){done=true;ok=value;why=message;}
        static bool Idle=>game&&game.Ready&&!game.Busy;
        static void Tick(){
            if(finished||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            try{
                if(!launched){Launch();return;}
                if(game&&Application.isFocused!=lastFocus){lastFocus=Application.isFocused;report.passed.Add("diag focus "+lastFocus+" phase "+phase+" index "+index);}
                if(game&&Field<bool>(game,"pause")!=lastPause){lastPause=!lastPause;report.passed.Add("diag board pause "+lastPause+" phase "+phase+" index "+index+" settings "+(game.GetComponent<GameplaySettingsController>()?.IsVisible)+" hudBlocking "+game.GetComponent<GameplayHUD>().IsBlocking);}if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Gateway stage "+phase+" index "+index+" game "+(game?game.Model.Status+" moves "+game.Model.Moves+" ready "+game.Ready+" busy "+game.Busy+" blocked "+game.ReviewInputBlocked:"gone")+" "+Diag(game)+" server busy "+server.Busy+" pending "+server.HasPending+" dialog "+home.GetComponent<DailyGiftPage>().IsVisible+" error "+server.LastError);
                if(Screen.width!=900||Screen.height!=1600)return;
                if(game&&game.Ready){var camera=Field<Camera>(game,"view");if(camera)camera.Render();}
                if(phase==11||phase==30){var victory=home.GetComponent<VictoryCelebrationPlayer>();if(victory&&victory.IsVisible){report.naturalVictoryObserved=true;if(!victoryCaptured&&Field<VictoryPlaybackSession>(victory,"clock").Elapsed>=.45f){Capture("VerifiedWin_M67");victoryCaptured=true;}}if(home.RewardRevealPlaying)report.naturalHomeRevealObserved=true;}
                if(phase==32||phase==33||phase==39||phase==43)report.dailyRevealObserved|=home.RewardRevealPlaying;
                switch(phase){
                    case 0:
                        host=home.GetComponent<PlayerProfileHost>();if(!host||!host.Ready||!flow.Loading)return;server=host.ServerSession;if(!server||server.Busy)return;
                        Check(!host.IsTransient&&server.Ready&&host.Events==null,"real explicitly selected server factory");Check(server.Wallet.coins==1250&&server.Wallet.lives==5&&server.Wallet.completed==7,"server genesis and labelled operator unlock");report.playerIdHash=IdentityProtocol82.Sha(server.PlayerId);
                        bool rejected=false;try{host.Service.Change(p=>{p.coins+=1000;return true;});}catch(InvalidOperationException){rejected=true;}Check(rejected&&server.Wallet.coins==1250,"legacy profile cannot grant beside server wallet");
                        phase=40;return;
                    case 40:
                        var initialBadges=home.GetComponent<ServerRewardsSession>();if(initialBadges&&initialBadges.HomeMetadataBusy&&!initialBadges.HomeMetadataReady&&!firstBadgeReadChecked){firstBadgeReadChecked=true;Check(initialBadges.HomeDailyBadge=="\u2026"&&initialBadges.HomeWellworksBadge=="\u2026"&&initialBadges.HomeCupBadge=="\u2026","Home shows waiting, not Unavailable, during the first reward read");}if(!flow.CanOpenAppSettings||!home.PresentationInteractable||server.Busy||!initialBadges||initialBadges.HomeMetadataBusy||!initialBadges.HomeMetadataReady||home.State.dailyStatus!="Ready"||home.State.wellworksStatus!="7/10"||home.State.cupStatus!="7/10")return;
                        HomeBadge("daily","Ready");HomeBadge("wellworks","7/10");HomeBadge("cup","7/10");Capture("Home_ServerRewardsReady");initialBadgeBatches=initialBadges.HomeMetadataBatches;rewardRevision=server.Wallet.revision;pageAt=EditorApplication.timeSinceStartup+.6;phase=41;return;
                    case 41:
                        if(EditorApplication.timeSinceStartup<pageAt)return;var stableBadges=home.GetComponent<ServerRewardsSession>();Check(stableBadges.HomeMetadataBatches==initialBadgeBatches&&server.Wallet.revision==rewardRevision&&!stableBadges.Coordinator.HasPending,"Idle metadata patches do not create a per-frame request loop, claim intent, or wallet revision");
                        int readEvents=0;Action changed=()=>readEvents++;server.Changed+=changed;ServerAuthorizedContext readContext;bool hasReadContext=server.TryGetReadContext(out readContext);server.Changed-=changed;Check(hasReadContext&&readContext!=null&&readContext.PlayerId==server.PlayerId&&!string.IsNullOrEmpty(readContext.CurrentAccess)&&readEvents==0&&!server.Busy,"Read context uses existing managed access without wallet publication or operation gate");
                        // Review 136. A tap while the wallet is unknown opens the player's real level, not the placeholder.
                        home.State.walletUnavailable=true;flow.Open(1);
                        Check(!home.State.walletUnavailable&&Field<PreLevelSession>(flow,"session").IsOpen&&Field<PreLevelSession>(flow,"session").View.level==home.State.currentLevel&&home.State.currentLevel==8,"Tap while the wallet is unknown opens the real current level, never the Level 1 placeholder");
                        home.GetComponent<PreLevelModal>().Requested("close");
                        // Review 136. The error dialog over Home can be closed, and Try Again can't leave Home dead.
                        var dialog=home.GetComponent<DailyGiftPage>();host.ShowHomeError(()=>{});Check(dialog.IsVisible&&!home.PresentationInteractable,"Connection dialog covers Home");
                        dialog.Request("close");Check(!dialog.IsVisible&&home.PresentationInteractable,"Close on the connection dialog returns to a working Home");
                        host.ShowHomeError(()=>{});dialog.Request("claim");Check(!dialog.IsVisible&&home.PresentationInteractable,"Try Again that opens nothing leaves Home working");
                        bool autoRetried=false;host.ShowHomeError(()=>autoRetried=true,()=>true);Check(dialog.IsVisible,"Connection dialog waits for the account");pageAt=EditorApplication.timeSinceStartup+.2;
                        settledDialogCheck=()=>{Check(autoRetried&&!dialog.IsVisible&&home.PresentationInteractable,"Connection dialog clears itself once the account is ready");};phase=142;return;
                    case 142:
                        if(EditorApplication.timeSinceStartup<pageAt)return;settledDialogCheck();
                        // Review 136. A long sleep ages the token even if the monotonic clock stopped.
                        var slept=Field<ManagedIdentitySession82>(server,"identity");Check(slept.HasAccess,"Token valid before the simulated sleep");string sleptToken=slept.AccessToken;slept.AdjustForSleep(901);Check(!slept.HasAccess&&slept.KnownPlayerId==server.PlayerId,"Token counted as expired after the sleep, player still known without it");
                        done=false;server.Refresh(Complete);sleepToken=sleptToken;phase=143;return;
                    case 143:
                        if(!done||server.Busy)return;var renewed=Field<ManagedIdentitySession82>(server,"identity");Check(ok&&renewed.HasAccess&&renewed.AccessToken!=sleepToken,"The next read renews after a sleep instead of sending an expired token");
                        profilePage=ProfilePage.Attach(home);appearanceBefore=JsonUtility.ToJson(Field<ProfileStore>(profilePage,"store").Snapshot);profilePage.Show();phase=20;return;
                    case 20:
                        var profileController=Field<ServerProfileController83>(profilePage,"onlineProfile");if(profileController==null||profileController.Busy||profileController.Profile==null||profileController.Records==null)return;
                        Check(profileController.Profile.playerId==server.PlayerId&&profileController.Records.completedLevels==7,"ordinary Profile page loads actual server metadata and private records");leaderboardOptIn=profileController.Profile.leaderboardOptIn;
                        Call(profilePage,"BeginRename");Field<InputField>(profilePage,"nameInput").text="Rain Reviewer 83";Call(profilePage,"SaveName");phase=21;return;
                    case 21:
                        var renamed=Field<ServerProfileController83>(profilePage,"onlineProfile");if(renamed==null||renamed.Busy||profilePage.IsRenaming)return;
                        Check(renamed.Profile?.displayName=="Rain Reviewer 83"&&profilePage.Snapshot.displayName=="Rain Reviewer 83","ordinary rename Save displays committed server name");
                        Check(JsonUtility.ToJson(Field<ProfileStore>(profilePage,"store").Snapshot)==appearanceBefore,"server rename does not persist local appearance name");profilePage.Hide();profilePage.Show();phase=22;return;
                    case 22:
                        var reopenedProfile=Field<ServerProfileController83>(profilePage,"onlineProfile");if(reopenedProfile==null||reopenedProfile.Busy||reopenedProfile.Records==null||server.Busy)return;
                        Call(profilePage,"SelectTab",3);Check(profilePage.Snapshot.displayName=="Rain Reviewer 83"&&reopenedProfile.Profile.leaderboardOptIn==leaderboardOptIn&&reopenedProfile.Records.completedLevels==7,"reopened Profile name/records retain existing opt-in");
                        report.serverProfileRenameAndRecords=true;report.localAppearanceUnchanged=JsonUtility.ToJson(Field<ProfileStore>(profilePage,"store").Snapshot)==appearanceBefore;profilePage.Hide();
                        // This fixture's player has cleared levels, so the override stands in for a first start.
                        HeartOfTheRain.App.Advertising.InterstitialAds129.VerificationAnyLevel=true;HeartOfTheRain.App.Advertising.InterstitialAds129.VerificationFactory=_=>new ScriptedInterstitial();PlayerPrefs.DeleteKey(HeartOfTheRain.App.Advertising.InterstitialPolicy129.LastLevelKey);
                        flow.Open(1);home.GetComponent<PreLevelModal>().Requested("toggle:0");home.GetComponent<PreLevelModal>().Requested("play");Check(interstitialShows==1&&interstitialHomeLocked,"The level-start ad runs from the Play tap with Home locked");phase=1;return;
                    case 1:
                        game=Field<GameplayScreen>(flow,"gameplay");if(!Idle||game.ReviewInputBlocked||flow.Loading.IsVisible||server.Busy)return;
                        report.firstAttemptId=server.Attempt.attemptId;Check(server.Attempt.state=="Started"&&server.Wallet.starting[0]==4&&server.Wallet.lives==5,"actual Play starts and spends one selected Rocket once");Check(game.CurrentSeed==(uint)server.Attempt.seed,"actual board uses server seed");
                        var target=game.Model.Pieces.Values.Where(p=>p.family=="gem").OrderBy(p=>p.y).ThenBy(p=>p.x).First();game.UseBooster(BoosterKind.Hammer,target.x,target.y);
                        // Review 136. Settings can't open over a paid tool that is still confirming.
                        var toolHud=game.GetComponent<GameplayHUD>();toolHud.ShowPause();Check(!toolHud.IsBlocking,"Settings stays shut while a paid tool is confirming");phase=2;return;
                    case 2:
                        if(!Idle||server.Busy||game.ReviewInputBlocked||server.LastOperation==null)return;
                        Check(server.Wallet.tools[0]==2&&server.LastOperation.model.checkpointSHA256==ProfileJson.Hash(JsonUtility.ToJson(game.Model.Checkpoint())),"broker-paid Hammer applied once with exact full checkpoint");report.paidTools++;
                        var move=game.Model.LegalSwaps().First(c=>game.Model.At(c[0].x,c[0].y).family=="gem"&&game.Model.At(c[1].x,c[1].y).family=="gem");Call(game,"PlayerSwap",move[0].x,move[0].y,move[1].x,move[1].y);report.playerActions++;phase=3;return;
                    case 3:
                        if(!Idle||server.Busy)return;done=false;server.Verify(game.Model.Checkpoint(),Complete);phase=4;return;
                    case 4:
                        if(!done)return;Check(ok,"ordinary action prefix verified by actual worker: "+(why??""));Check(server.LastOperation.acceptedActions==2,"paid Tool plus accepted Swap global prefix");
                        var exit=new EndLevelSession();EndLevelDecision decision;bool opened=exit.Open(1,home.State.lives),confirmed=exit.Confirm(home.State.lives,out decision);Check(opened&&confirmed,"existing explicit exit decision");Call(flow,"ConfirmExit",game,decision);phase=5;return;
                    case 5:
                        if(Field<GameplayScreen>(flow,"gameplay")||server.Busy)return;
                        Check(server.Wallet.lives==4&&server.Attempt.state=="Lost"&&server.Wallet.tools[0]==2&&server.Wallet.starting[0]==4,"confirmed Quit loses one life and keeps actual spent items");
                        home.GetComponent<PreLevelModal>().Requested("close");
                        // Review 136. An attempt still held by the server is settled before the next one starts.
                        done=false;server.Reserve(1,new[]{0,0,0,0},Complete);phase=50;return;
                    case 50:
                        if(!done||server.Busy)return;Check(ok&&server.Attempt.state=="Reserved","First reservation for the forfeit-before-Play check");heldAttempt=server.Attempt.attemptId;
                        done=false;server.Reserve(1,new[]{0,0,0,0},Complete);phase=51;return;
                    case 51:
                        if(!done||server.Busy)return;Check(ok&&server.Attempt.state=="Reserved"&&server.Attempt.attemptId!=heldAttempt&&server.Wallet.lives==4,"Play settles an attempt the server still holds, then reserves, with no life for an unstarted one");
                        done=false;server.CancelReservation(Complete);phase=52;return;
                    case 52:
                        if(!done||server.Busy)return;Check(ok&&server.Wallet.activeAttempt==null,"Reservation cancelled before the next stage");
                        flow.Open(8);home.GetComponent<PreLevelModal>().Requested("play");phase=6;return;
                    case 6:
                        game=Field<GameplayScreen>(flow,"gameplay");if(!Idle||game.ReviewInputBlocked||server.Busy||flow.Loading.IsVisible)return;
                        report.continueAttemptId=server.Attempt.attemptId;
                        // Review 136 diagnostics: who pauses the board, and whether the Editor loses focus.
                        {var hudDiag=game.GetComponent<GameplayHUD>();var prevPause=hudDiag.PauseChanged;hudDiag.PauseChanged=v=>{report.passed.Add("diag pause "+v+" phase "+phase+" index "+index+" focused "+Application.isFocused+" via "+new System.Diagnostics.StackTrace(1,false).ToString().Replace("\n"," | ").Substring(0,Math.Min(600,new System.Diagnostics.StackTrace(1,false).ToString().Length)));prevPause?.Invoke(v);};
                        var prevSettings=hudDiag.SettingsRequested;hudDiag.SettingsRequested=()=>{report.passed.Add("diag settings requested phase "+phase+" index "+index+" focused "+Application.isFocused+" via "+new System.Diagnostics.StackTrace(1,false).ToString().Replace("\n"," | ").Substring(0,Math.Min(600,new System.Diagnostics.StackTrace(1,false).ToString().Length)));prevSettings?.Invoke();};}
                        Check(game.CurrentSeed==continuation.seed&&server.Attempt.starting.All(n=>n==0),"operator-owned L8 fixture seed and no starting power override");phase=7;return;
                    case 7:
                        if(index>=continuation.actions.Length){phase=11;return;}if(!Idle||server.Busy)return;
                        var action=continuation.actions[index];
                        if(action.kind=="Continue"){
                            var controller=game.GetComponent<NoMovesController>();if(!controller.Active||controller.Offer==null||controller.Page.Screen!="offer")return;
                            Check(game.Model.Moves==0&&server.Attempt.state=="AwaitingContinuation"&&server.Wallet.lives==4,"natural zero-move board is verified without loss");controller.Request("shop");Check(controller.Page.Screen=="shop"&&server.ContinueView=="shop","approved Shop preserves pending board");
                            // Reopen the actual durable journal and actual board owner,
                            // retaining the same live managed identity (Editor key is ephemeral).
                            var journal=Field<ServerAttemptJournal>(server,"journal");string path=Field<string>(journal,"path");var reopened=new ServerAttemptJournal(path,server.Origin,server.PlayerId);
                            typeof(ServerGameSession).GetField("journal",Private).SetValue(server,reopened);typeof(ServerGameSession).GetField("document",Private).SetValue(server,reopened.Read());
                            UnityEngine.Object.Destroy(game.gameObject);typeof(HomeLevelFlow).GetField("gameplay",Private).SetValue(flow,null);flow.StartCoroutine((IEnumerator)Call(flow,"RestoreContinueAttempt"));phase=8;return;
                        }
                        // Review 136. The winning move is made with the network down: its command must be on disk at once.
                        if(index==continuation.actions.Length-1)ServerGameSession.VerificationBrokerOffline=true;
                        if(action.kind=="Swap")Call(game,"PlayerSwap",action.ax,action.ay,action.bx,action.by);else if(action.kind=="Tap")Call(game,"PlayerTap",action.ax,action.ay);else throw new InvalidOperationException("Unexpected sealed fixture action");
                        report.playerActions++;index++;phase=10;return;
                    case 8:
                        game=Field<GameplayScreen>(flow,"gameplay");if(!Idle)return;var restored=game.GetComponent<NoMovesController>();if(!restored||!restored.Active||restored.Page.Screen!="shop")return;
                        Check(server.Attempt.attemptId==report.continueAttemptId&&server.Wallet.lives==4&&server.Wallet.coins==1250,"actual Shop/board restoration reserves no new attempt or life");report.restoredShopBoards++;restored.Request("back");restored.Request("play");phase=9;return;
                    case 9:
                        if(!Idle||server.Busy||game.GetComponent<NoMovesController>().Active||game.ReviewInputBlocked)return;
                        Check(game.Model.Moves==5&&server.Attempt.moves==continuation.initialMoves+5&&server.Wallet.coins==350&&server.Wallet.lives==4,"900 coins buys five remaining moves; total budget is not granted as remaining");
                        Check(ProfileJson.Hash(JsonUtility.ToJson(game.Model.Checkpoint()))==server.LastOperation.model.checkpointSHA256,"restored paid continuation matches real worker full checkpoint");report.paidContinues++;index++;phase=7;return;
                    case 10:
                        if(!Idle)return;
                        if(ServerGameSession.VerificationBrokerOffline){
                            var saveDialog=home.GetComponent<DailyGiftPage>();if(game.Model.Status!="Won"||!server.HasPending||!saveDialog.IsVisible)return;
                            var durable=Field<ServerAttemptJournal>(server,"journal");var onDisk=new ServerAttemptJournal(Field<string>(durable,"path"),server.Origin,server.PlayerId).Read();
                            Check(onDisk.hasPending&&onDisk.pending.operation=="Verify"&&onDisk.pending.payload.Contains("actions")&&server.Wallet.completed==7,"An offline win is saved with its moves before any network call, and nothing is settled yet");
                            ServerGameSession.VerificationBrokerOffline=false;saveDialog.Request("claim");phase=7;return;
                        }
                        phase=7;return;
                    case 11:
                        if(server.Busy||server.CompletionReceipt()?.state!="Won")return;
                        Check(server.Wallet.coins==400&&server.Wallet.stars==1&&server.Wallet.lives==4&&server.Wallet.completed==8,"real worker verified win grants actual50/1 once after900 continuation");
                        report.afterWinCoins=server.Wallet.coins;phase=30;return;
                    case 30:
                        if(Field<GameplayScreen>(flow,"gameplay")||server.Busy||VictoryCelebrationPlayer.IsPlaying(home)||!flow.CanOpenAppSettings||!home.PresentationInteractable||home.RewardRevealPlaying)return;
                        var wonBadges=home.GetComponent<ServerRewardsSession>();if(!wonBadges.HomeMetadataReady||wonBadges.HomeMetadataBusy||home.State.wellworksStatus!="8/10"||home.State.cupStatus!="8/10")return;
                        Check(report.naturalVictoryObserved&&report.naturalHomeRevealObserved,"Verified win naturally plays M67 then returns to interactive Home and completes reward reveal");
                        Check(interstitialShows==1,"Winning levels and starting non-milestone levels show no interstitial");
                        HomeBadge("daily","Ready");HomeBadge("wellworks","8/10");HomeBadge("cup","8/10");Check(server.Wallet.coins==400&&!wonBadges.Coordinator.HasPending,"Progress metadata refresh has no reward or claim side effect");
                        Check(home.State.coins==400&&home.State.stars==1&&home.State.completedLevelsInChapter==8,"Natural Home displays authoritative verified win balances");report.portraitWidth=Screen.width;report.portraitHeight=Screen.height;Capture("Home_AfterVerifiedWin");
                        daily=home.GetComponent<DailyGiftPage>();Check(daily!=null,"Ordinary host installs actual DailyGiftPage");daily.Show();pageAt=EditorApplication.timeSinceStartup+.35;phase=31;return;
                    case 31:
                        rewards=home.GetComponent<ServerRewardsSession>()?.Coordinator;if(server.Busy||daily.IsNetworkBusy||rewards==null||rewards.Busy||EditorApplication.timeSinceStartup<pageAt)return;
                        var gift=Field<DailyGiftView>(daily,"view");Check(daily.IsVisible&&!gift.error&&!gift.loading&&!gift.networkError&&gift.offer!=null&&!gift.offer.claimed&&gift.offer.grant.coins==50,"Ordinary Daily Gift page shows actual authenticated unclaimed50 offer");
                        Check(host.BackendGifts==null&&!gift.development&&rewards.PlayerId==server.PlayerId,"Ordinary reward page uses account-bound server adapter without legacy local-credit backend session");PageText(daily);
                        Check(Nodes(daily)["claim"].GetComponent<Image>().color.a==0,"Actual Daily Gift clear hit image remains transparent");Capture("DailyGift_Offer");Click(daily,"claim");Check(daily.IsNetworkBusy,"Actual Claim button starts asynchronous durable server claim");phase=32;return;
                    case 32:
                        if(server.Busy||daily.IsNetworkBusy||rewards.Busy)return;
                        var claimed=Field<DailyGiftView>(daily,"view");Check(claimed.offer!=null&&claimed.offer.claimed&&claimed.received&&!claimed.loading&&!claimed.networkError&&!rewards.HasPending,"Ordinary Daily Gift confirmation reconciles server offer and clears exact durable intent");
                        Check(server.Wallet.coins==450&&server.Wallet.stars==1&&server.Wallet.lives==4&&server.Wallet.completed==8&&home.State.coins==450,"Actual page claim adds exactly50 in authoritative wallet and displayed projection");report.dailyClaimCoins=50;rewardRevision=server.Wallet.revision;pageAt=EditorApplication.timeSinceStartup+.2;phase=33;return;
                    case 33:
                        if(EditorApplication.timeSinceStartup<pageAt)return;PageText(daily);Capture("DailyGift_Collected");var deferred116=RewardPresentationJournal.ForPlayer(server.Origin,server.PlayerId).Peek();Check(!home.PresentationInteractable&&!home.RewardRevealPlaying&&deferred116!=null&&deferred116.channel=="reward"&&deferred116.grant.coins==50&&server.Wallet.revision==rewardRevision,"Confirmed gift is durably deferred while actual modal blocks Home, with unchanged credited wallet");
                        phase=34;return;
                    case 34:
                        if(server.Busy||daily.IsNetworkBusy||rewards.Busy||home.RewardRevealPlaying)return;
                        // Let the ordinary cosmetic sequence finish before a
                        // negative repeated public action refreshes the view.
                        daily.Request("claim");phase=39;return;
                    case 39:
                        if(server.Busy||daily.IsNetworkBusy||rewards.Busy)return;
                        Check(server.Wallet.coins==450&&server.Wallet.revision==rewardRevision&&!rewards.HasPending,"Repeated collected page action leaves authoritative gift credit final");Click(daily,"close");Check(!daily.IsVisible&&home.PresentationInteractable,"Actual Daily Gift Close restores interactive Home");
                        // Explicit native fixture lifecycle: a batch Editor
                        // does not represent foreground application focus.
                        Call(home,"OnApplicationFocus",true);Call(home,"OnApplicationPause",false);report.controlledForegroundLifecycle116=true;pageAt=EditorApplication.timeSinceStartup+12;phase=43;return;
                    case 43:
                        var pendingReveal116=RewardPresentationJournal.ForPlayer(server.Origin,server.PlayerId).Peek();
                        if(home.RewardRevealPlaying||!report.dailyRevealObserved||pendingReveal116!=null){if(EditorApplication.timeSinceStartup>pageAt)throw new InvalidOperationException("Bounded idle-Home reveal/ack did not complete: "+home.GetComponent<RewardReceiptPresenter>()?.LastError);return;}
                        Check(report.dailyRevealObserved&&home.PresentationInteractable&&server.Wallet.coins==450&&server.Wallet.revision==rewardRevision&&!rewards.HasPending,"Actual foreground idle Home reveals and acknowledges one deferred receipt without another grant");phase=42;return;
                    case 42:
                        if(server.Busy||home.State.dailyStatus!=DailyGiftText.T("Tomorrow"))return;
                        HomeBadge("daily",DailyGiftText.T("Tomorrow"));HomeBadge("wellworks","8/10");HomeBadge("cup","8/10");Check(server.Wallet.coins==450&&server.Wallet.revision==rewardRevision,"Collected Home badges reuse successful page metadata without another credit");Capture("Home_AfterDailyGift");
                        works=home.GetComponent<WellworksPage>();works.Show();pageAt=EditorApplication.timeSinceStartup+.35;phase=35;return;
                    case 35:
                        if(server.Busy||Field<bool>(works,"serverBusy")||rewards.Busy||rewards.Wellworks==null||EditorApplication.timeSinceStartup<pageAt)return;
                        var milestones=Field<WellworksView>(works,"view");Check(works.IsVisible&&!milestones.error&&milestones.enabled&&milestones.player.completed==8&&milestones.schedule.milestones[0].level==10,"Actual Wellworks page projects authenticated completed8 against first milestone10");
                        Check(milestones.schedule.milestones.All(m=>!WellworksService.Claimed(milestones.player,m.level))&&!works.GetComponentsInChildren<HomeControlLabel>().Any(c=>c.action!=null&&c.action.StartsWith("claim-",StringComparison.Ordinal)),"Locked ordinary milestone page has no enabled or fabricated claim control");PageText(works);Capture("Wellworks_Locked8of10");rewardRevision=server.Wallet.revision;works.Request("claim-10");phase=36;return;
                    case 36:
                        if(Field<bool>(works,"serverBusy")||rewards.Busy||server.Busy)return;Check(server.Wallet.coins==450&&server.Wallet.revision==rewardRevision&&!rewards.HasPending,"Locked page's direct action guard cannot mint a milestone or queue an ineligible claim");Click(works,"close");Check(!works.IsVisible&&home.PresentationInteractable,"Actual Wellworks Close restores Home");
                        cup=home.GetComponent<RainCupPage>();cup.Show();pageAt=EditorApplication.timeSinceStartup+.35;phase=37;return;
                    case 37:
                        if(server.Busy||Field<bool>(cup,"serverBusy")||rewards.Busy||rewards.Cup==null||EditorApplication.timeSinceStartup<pageAt)return;
                        var practice=Field<RainCupView>(cup,"view");Check(cup.IsVisible&&!practice.error&&practice.snapshot.state=="Locked"&&practice.snapshot.completed==8&&practice.snapshot.rules.unlockClears==10&&practice.snapshot.run==null&&!practice.snapshot.canJoin,"Actual Rain Cup page remains locked8of10 with no fabricated run");
                        Check(rewards.Cup.practice&&rewards.Cup.simulatedRivals&&!rewards.Cup.realCompetition&&practice.snapshot.development,"Connected Cup keeps explicit practice/simulated-rival semantics");Check(!Nodes(cup)["primary"].GetComponent<Button>().interactable,"Locked ordinary Cup primary button is disabled");
                        Check(Nodes(cup)["intro"].GetComponent<Text>().text==RainCupDesignText.T("practice"),"Actual ordinary Cup labels the practice event");PageText(cup);Capture("RainCup_Locked8of10_Practice");rewardRevision=server.Wallet.revision;cup.Request("join");phase=38;return;
                    case 38:
                        if(Field<bool>(cup,"serverBusy")||rewards.Busy||server.Busy)return;Check(server.Wallet.coins==450&&server.Wallet.revision==rewardRevision&&!rewards.HasPending&&rewards.Cup.run==null,"Locked Cup direct action cannot create an enrollment or alter authoritative balances");Click(cup,"close");Check(!cup.IsVisible&&home.PresentationInteractable,"Actual Cup Close restores Home");
                        report.ordinaryRewardPages=true;report.localAppearanceUnchanged=JsonUtility.ToJson(Field<ProfileStore>(profilePage,"store").Snapshot)==appearanceBefore;Check(report.localAppearanceUnchanged,"Ordinary server reward pages leave local appearance preferences unchanged");
                        var finalBadges=home.GetComponent<ServerRewardsSession>();report.homeMetadataBatches=finalBadges.HomeMetadataBatches;report.readonlyHomeRewardBadges=true;
                        report.finalCoins=server.Wallet.coins;report.finalStars=server.Wallet.stars;report.finalLives=server.Wallet.lives;report.finalCompleted=server.Wallet.completed;report.ordinaryProfilesAfter=ProfileDigest();Check(report.ordinaryProfilesAfter==report.ordinaryProfilesBefore,"ordinary local profile files unchanged");Finish();return;
                }
            }catch(Exception e){report.errors.Add("Stage "+phase+": "+e.GetType().Name+": "+e.Message);Finish();}
        }
        static string Diag(object g){if(g==null)return "";var sb=new StringBuilder();foreach(var n in new[]{"current","preparing","StartupPending79","queue","queueIndex","awaitingPlaybackPose","playbackPoseAnchor","pause","ReviewInputBlocked"}){object v=null;try{var f=g.GetType().GetField(n,Private|BindingFlags.Public);if(f!=null)v=f.GetValue(g);else{var pr=g.GetType().GetProperty(n,Private|BindingFlags.Public);if(pr!=null)v=pr.GetValue(g);}}catch(Exception e){v="!"+e.GetType().Name;}sb.Append(n).Append('=').Append(v==null?"null":v is System.Collections.ICollection c?"count "+c.Count:v is UnityEngine.Object?v.GetType().Name:v.ToString()).Append(' ');}return sb.ToString();}
        static void Finish(){
            if(finished)return;finished=true;EditorApplication.update-=Tick;SessionState.SetBool(Key,false);Time.timeScale=oldTime;
            string old=SessionState.GetString(Key+".previousConfig","");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",string.IsNullOrEmpty(old)?null:old);
            try{RestorePortrait();report.portraitSettingsRestored=true;}catch(Exception e){report.errors.Add("Portrait restoration: "+e.GetType().Name);}
            report.status=report.errors.Count==0?"PASS_NATIVE_SERVER_GAMEPLAY83_CONNECTED_HTTP":"FAIL_NATIVE_SERVER_GAMEPLAY83_CONNECTED_HTTP";
            Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native","ConnectedHTTP.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            if(home)UnityEngine.Object.Destroy(home.gameObject);if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);else EditorApplication.isPlaying=false;
        }
    }
}
#endif
