#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.EndLevel;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad]
    public static class NativePlaySmoke
    {
        const string Key = "HOTR.Verification.PlaySmoke";
        [Serializable] sealed class Result
        {
            public string status = "RUNNING", utc, unity;
            public string scope = "Native Editor lifecycle and programmatic app actions, including forced terminal statuses (failed reshuffle, resolution guard) and the launch-window pause guard on a transient in-memory profile. Default79 startup observes an actual own-camera witness or supplies an offscreen render in batchmode; this may show the active head or a held post-swap pose, while Lifecycle79 separately verifies the first head. Not physical touch, full win flow, onboarding completion, device performance or visual approval.";
            public string bootStage;
            public int bootLevel, width, height;
            public string startupMode;public bool startupWitnessed,startupExplicitOffscreenWitness;
            public int startupHeadSubmittedFrame,startupCameraWitnessFrame,startupJobStartedFrame;
            public GameplayScreen.StartupTrace79 startupTrace;
            public List<string> checks = new List<string>(), errors = new List<string>();
        }
        static Result report;
        static HomeLevelFlow flow;
        static HomePage home;
        static GameplayScreen screen;
        static int phase, moves, lives;
        static bool expectFault, faultLogged;
        static uint firstSeed;
        static double phaseAt;
        static string Output => Path.GetFullPath("../Verification/Evidence/Native");
        static NativePlaySmoke()
        {
            if (SessionState.GetBool(Key, false))
                Attach();
        }
        public static void Run()
        {
            if (!Application.isBatchMode) throw new InvalidOperationException("Use the batch runner to isolate this smoke test.");
            SessionState.SetBool(Key, true);
            SessionState.SetFloat(Key + ".started", (float)EditorApplication.timeSinceStartup);
            EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");
            // Use the delivered review memory store, preserving the user's real
            // tutorial preference keys while exercising the same page lifecycle.
            var firstStart = UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();
            if (firstStart) firstStart.reviewAlways = true;
            EditorApplication.isPlaying = true;
        }
        static void Attach()
        {
            report = new Result { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion };
            phaseAt = EditorApplication.timeSinceStartup;
            Application.logMessageReceived += OnLog;
            EditorApplication.update += Tick;
        }
        static void OnLog(string message, string stack, LogType type)
        {
            // The resolution-guard / engine-fault diagnostics are the expected output of the fault phases.
            if (type == LogType.Error && expectFault && (message.StartsWith("Resolution guard reached", StringComparison.Ordinal) || message.StartsWith("Engine fault (", StringComparison.Ordinal))) { faultLogged = true; return; }
            if (type == LogType.Exception && expectFault && message.Contains("Verification engine fault")) return;
            if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert)
                report.errors.Add(message + "\n" + stack);
        }
        static PlayerProfileHost Profile => home.GetComponent<PlayerProfileHost>();
        static AttemptRecord LastAttempt => Profile.Service.Read().attempts.Last();
        static void InvokePause(GameplayScreen target, bool suspended)
        {
            typeof(GameplayScreen).GetMethod("OnApplicationPause", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(target, new object[] { suspended });
        }
        static T ScreenField<T>(string name)=>(T)typeof(GameplayScreen).GetField(name,BindingFlags.Instance|BindingFlags.NonPublic).GetValue(screen);
        static void WitnessStartup()
        {
            if(!screen||report.startupWitnessed)return;var trace=screen.VerificationStartup;
            if(trace.jobStartedFrame>0||trace.cameraWitnessFrame>0){RecordStartupWitness(false);return;}
            if(!screen.VerificationStartupPending)return;
            if(typeof(GameplayScreen).GetField("current",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(screen)==null&&!trace.held)return;
            typeof(GameplayScreen).GetMethod("Render",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(screen,null);
            if(ScreenField<int>("startupSubmitted79")!=Time.frameCount)throw new InvalidOperationException("Connected startup has no submitted pose in the witness frame.");
            var camera=ScreenField<Camera>("view");var previous=camera.targetTexture;var active=RenderTexture.active;var target=new RenderTexture(720,1280,24);
            try{camera.targetTexture=target;camera.Render();}
            finally{camera.targetTexture=previous;RenderTexture.active=active;UnityEngine.Object.Destroy(target);}
            trace=screen.VerificationStartup;if(trace.cameraWitnessFrame!=Time.frameCount||trace.jobStartedFrame!=Time.frameCount)throw new InvalidOperationException("Connected offscreen own-camera render did not witness/start startup in its actual frame.");
            RecordStartupWitness(true);
        }
        static void RecordStartupWitness(bool offscreen)
        {
            var trace=screen.VerificationStartup;report.startupHeadSubmittedFrame=trace.headSubmittedFrame;report.startupCameraWitnessFrame=trace.cameraWitnessFrame;report.startupJobStartedFrame=trace.jobStartedFrame;
            report.startupWitnessed=trace.cameraWitnessFrame>0&&trace.cameraWitnessFrame==trace.jobStartedFrame;report.startupExplicitOffscreenWitness=offscreen;
            report.startupMode=offscreen?"default79-leading-swap-offscreen-own-camera":"default79-leading-swap-automatic-own-camera";
            if(!report.startupWitnessed||trace.headSubmittedTicks<=0||trace.headSubmittedTicks>trace.cameraWitnessTicks||trace.cameraWitnessTicks>trace.jobStartedTicks)throw new InvalidOperationException("Connected startup camera/submitted-pose chronology differs.");
            report.checks.Add("Actual own-camera onPostRender witnessed a submitted board pose before default managed startup work; no Editor tick is substituted for that witness.");
        }
        static void Tick()
        {
            try
            {
                if (EditorApplication.timeSinceStartup - SessionState.GetFloat(Key + ".started", 0) > 180)
                    throw new TimeoutException("Play smoke exceeded 180 seconds at phase " + phase);
                if (!EditorApplication.isPlaying || EditorApplication.isCompiling || EditorApplication.isUpdating) return;
                if (report.errors.Count > 0) throw new InvalidOperationException("Runtime error captured.");
                // Batchmode does not promise an automatically rendered GameView.
                // Observe/supply the own-camera witness before the phase delay
                // or Busy wait, including a head already held at its endpoint.
                if(phase==3)WitnessStartup();
                if (EditorApplication.timeSinceStartup - phaseAt < 1) return;
                switch (phase)
                {
                    case 0:
                        home = UnityEngine.Object.FindFirstObjectByType<HomePage>();
                        flow = UnityEngine.Object.FindFirstObjectByType<HomeLevelFlow>();
                        if (!home || !flow) return;
                        report.bootLevel = home.State.currentLevel;
                        var boot = UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();
                        report.bootStage = boot ? boot.Stage.ToString() : "NO_FIRST_START_PAGE";
                        report.width = Screen.width; report.height = Screen.height;
                        report.checks.Add("Boot scene created Home and HomeLevelFlow; initial level/stage recorded without changing saved preferences.");
                        if (boot && boot.IsVisible)
                        {
                            boot.Request("skip"); boot.Request("skip");
                            if (boot.IsVisible) throw new InvalidOperationException("Review-memory tutorial skip did not return Home.");
                            report.checks.Add("Review-memory first-start story/practice skip returned Home without writing tutorial preferences.");
                        }
                        // Deliberate in-memory fixture for connected gameplay; this is not
                        // a persisted new-player profile or a first-start completion test.
                        home.State.currentLevel = 1; home.State.completedLevelsInChapter = 0; home.State.cupVisible = true;
                        home.ApplyState(home.State);
                        // Checkpoint 60: a status badge is patched in place, not by rebuilding Home.
                        var badge = FindNode(home.transform, "cup-status");
                        if (!badge) throw new InvalidOperationException("Home has no cup-status label to patch.");
                        int nodesBefore = home.GetComponentsInChildren<RectTransform>(true).Length;
                        if (!home.UpdateLabel("cup-status", "1:02:03")) throw new InvalidOperationException("UpdateLabel found no cup-status label.");
                        if (!badge || badge.GetComponent<UnityEngine.UI.Text>().text != "1:02:03" || home.GetComponentsInChildren<RectTransform>(true).Length != nodesBefore) throw new InvalidOperationException("Patching the cup badge rebuilt Home or missed the label.");
                        report.checks.Add("A live event badge updates its label in place; Home keeps its nodes (no rebuild under a tap or scroll).");
                        flow.Open(1);
                        Next(); break;
                    case 1:
                        var modal = home.GetComponent<PreLevelModal>();
                        if (!modal || !modal.IsVisible) return;
                        int[] stock = flow.StartingStockSnapshot();
                        modal.Requested("play");
                        report.checks.Add("Pre-level opened and programmatic Play requested with no starting items selected; stock " + string.Join(",", stock));
                        Next(); break;
                    case 2:
                        screen = UnityEngine.Object.FindFirstObjectByType<GameplayScreen>();
                        if (!screen || !screen.InitializationComplete || !screen.Ready || screen.ReviewInputBlocked) return;
                        if (!screen.HasStartedWithPowers || !string.IsNullOrEmpty(screen.StartingPowerError))
                            throw new InvalidOperationException("Connected launch/grant did not complete.");
                        screen.Model.Validate(); moves = screen.Model.Moves;
                        firstSeed = screen.CurrentSeed;
                        if (firstSeed != ProfileService.AttemptSeed(LastAttempt.id) || firstSeed != (uint)LastAttempt.seed) throw new InvalidOperationException("Connected launch did not use the attempt's recorded seed.");
                        if (!screen.ReviewNaturalMove()) throw new InvalidOperationException("Programmatic legal action was rejected.");
                        report.startupMode="default79-leading-swap-awaiting-own-camera";
                        if(!screen.VerificationStartup.eligible)throw new InvalidOperationException("Connected smoke did not exercise the default leading-swap startup path.");
                        report.checks.Add("Connected launch completed with the attempt's recorded refill seed; real GameplayScreen accepted a natural model move.");
                        Next(); break;
                    case 3:
                        if (screen.Busy) return;
                        report.startupTrace=screen.VerificationStartup;
                        if(!report.startupWitnessed||screen.VerificationStartupPending||report.startupTrace.tailInstalledFrame<=0)throw new InvalidOperationException("Connected startup completed without its own-camera witness and installed tail.");
                        screen.Model.Validate();
                        if (screen.Model.Moves != moves - 1) throw new InvalidOperationException("Move charge differs after playback.");
                        report.checks.Add("Gameplay presentation settled with one move spent and valid occupancy/goals.");
                        foreach (var renderer in screen.GetComponentsInChildren<SpriteRenderer>().Where(r=>r.enabled && r.name=="Sampled sprite" && r.sprite))
                        {
                            var block = new MaterialPropertyBlock();
                            renderer.GetPropertyBlock(block);
                            if (block.GetFloat("_Glow")>0 && block.GetTexture("_MainTex") != renderer.sprite.texture)
                                throw new InvalidOperationException("Sprite texture missing from glow property block: " + renderer.sprite.name);
                        }
                        report.checks.Add("Glowing sprites retain their source texture; ordinary sprites use native automatic binding (also covered by the native render probe).");
                        Directory.CreateDirectory(Output);
                        CaptureFrame(Path.Combine(Output, "Connected_Gameplay.png"));
                        report.checks.Add("Saved a native camera-rendered gameplay/HUD frame; overlay canvases temporarily use that camera for capture. This is not a phone or approved portrait screenshot.");
                        var settings = screen.GetComponent<GameplaySettingsController>();
                        if (!settings) throw new InvalidOperationException("Connected settings controller missing.");
                        lives = home.State.lives; settings.ShowEndLevel();
                        Next(); break;
                    case 4:
                        var exit = screen.GetComponent<EndLevelModal>();
                        if (!exit || !exit.IsVisible) return;
                        exit.Requested("cancel");
                        if (home.State.lives != lives || screen.Paused) throw new InvalidOperationException("Cancel exit changed lives or left gameplay paused.");
                        report.checks.Add("Exit cancellation preserved lives and resumed gameplay.");
                        screen.GetComponent<GameplaySettingsController>().ShowEndLevel();
                        Next(); break;
                    case 5:
                        screen.GetComponent<EndLevelModal>().Requested("confirm");
                        Next(); break;
                    case 6:
                        if (!flow.RetryVisible) return;
                        if (home.State.lives != Math.Max(0, lives - 1)) throw new InvalidOperationException("Confirmed exit life charge differs.");
                        if (LastAttempt.state != "Lost") throw new InvalidOperationException("Confirmed exit did not settle the attempt as Lost: " + LastAttempt.state);
                        report.checks.Add("Confirmed exit charged one life, settled the attempt as Lost and opened the HomeLevelFlow retry pre-level.");
                        if (!Profile.IsTransient) throw new InvalidOperationException("Terminal-status phases require the transient review profile.");
                        home.GetComponent<PreLevelModal>().Requested("play");
                        Next(); break;
                    case 7:
                        screen = UnityEngine.Object.FindFirstObjectByType<GameplayScreen>();
                        if (!screen || !screen.InitializationComplete || !screen.Ready || screen.ReviewInputBlocked) return;
                        var hud = screen.GetComponent<GameplayHUD>();
                        var controller = screen.GetComponent<GameplaySettingsController>();
                        if (!controller) throw new InvalidOperationException("Connected settings controller missing on retry launch.");
                        if (screen.CurrentSeed != ProfileService.AttemptSeed(LastAttempt.id) || screen.CurrentSeed == firstSeed) throw new InvalidOperationException("Retry attempt did not get its own refill seed.");
                        report.checks.Add("The retry attempt plays with its own recorded refill seed, different from the first attempt's.");
                        // Launch-window guard: while the flow blocks input, backgrounding opens nothing.
                        screen.ReviewInputBlocked = true; InvokePause(screen, true);
                        if (hud.IsBlocking || screen.Paused || controller.IsVisible) throw new InvalidOperationException("Backgrounding while input was blocked opened a pause dialog.");
                        screen.ReviewInputBlocked = false;
                        report.checks.Add("Backgrounding while the flow blocks input opens no pause or restart dialog (launch-window guard).");
                        InvokePause(screen, true);
                        if (!controller.IsSettingsVisible) throw new InvalidOperationException("Backgrounding during play did not open the connected settings modal.");
                        hud.Close(true);
                        if (controller.IsVisible || screen.Paused) throw new InvalidOperationException("Closing the settings modal did not resume gameplay.");
                        report.checks.Add("Backgrounding during play routes to the connected settings modal, never the legacy restart dialog; closing it resumes.");
                        lives = home.State.lives; screen.Model.VerificationForceStatus("No legal moves");
                        Next(); break;
                    case 8:
                        var lossHud = screen ? screen.GetComponent<GameplayHUD>() : null;
                        if (lossHud && lossHud.LossPending)
                        {
                            if (lossHud.LossTitle != "No moves left") throw new InvalidOperationException("Failed reshuffle showed the wrong loss title: " + lossHud.LossTitle);
                            if (home.State.lives != lives || LastAttempt.state != "Started") throw new InvalidOperationException("Life charged before the loss dialog was acknowledged.");
                            report.checks.Add("A failed reshuffle shows the approved loss dialog titled 'No moves left' with the life still intact until acknowledged.");
                            lossHud.AcknowledgeLoss();
                            return;
                        }
                        if (!flow.RetryVisible) return;
                        if (UnityEngine.Object.FindFirstObjectByType<GameplayScreen>()) throw new InvalidOperationException("Failed-reshuffle end state left a GameplayScreen alive.");
                        if (home.State.lives != Math.Max(0, lives - 1)) throw new InvalidOperationException("No legal moves did not charge exactly one life.");
                        if (LastAttempt.state != "Lost") throw new InvalidOperationException("No legal moves did not settle the attempt as Lost: " + LastAttempt.state);
                        report.checks.Add("A failed reshuffle (No legal moves) settles through HomeLevelFlow: one life, attempt Lost, board destroyed, retry pre-level open, no legacy dialog.");
                        home.GetComponent<PreLevelModal>().Requested("play");
                        Next(); break;
                    case 9:
                        screen = UnityEngine.Object.FindFirstObjectByType<GameplayScreen>();
                        if (!screen || !screen.InitializationComplete || !screen.Ready || screen.ReviewInputBlocked) return;
                        lives = home.State.lives; expectFault = true; faultLogged = false;
                        screen.Model.VerificationForceStatus("Resolution limit");
                        Next(); break;
                    case 10:
                        if (!flow.RetryVisible) return;
                        expectFault = false;
                        if (UnityEngine.Object.FindFirstObjectByType<GameplayScreen>()) throw new InvalidOperationException("Resolution-guard end state left a GameplayScreen alive.");
                        if (home.State.lives != lives) throw new InvalidOperationException("Resolution guard charged a life.");
                        if (LastAttempt.state != "Released") throw new InvalidOperationException("Resolution guard did not release the attempt: " + LastAttempt.state);
                        if (!faultLogged) throw new InvalidOperationException("Resolution guard did not log its diagnostic.");
                        if (!Profile.Service.Read().starting.SequenceEqual(new[] { 5, 5, 3, 2 })) throw new InvalidOperationException("Released attempt left starting stock inconsistent: " + string.Join(",", Profile.Service.Read().starting));
                        report.checks.Add("The resolution guard (Resolution limit) is diagnosed, releases the attempt as Released without a life charge, keeps starting stock whole and reopens the pre-level.");
                        home.GetComponent<PreLevelModal>().Requested("play");
                        Next(); break;
                    case 11:
                        screen = UnityEngine.Object.FindFirstObjectByType<GameplayScreen>();
                        if (!screen || !screen.InitializationComplete || !screen.Ready || screen.ReviewInputBlocked || screen.Busy) return;
                        lives = home.State.lives; expectFault = true; faultLogged = false;
                        // Checkpoint 60: a player command that throws is an engine fault, not a lost input.
                        screen.VerificationFaultOnNextInput = true;
                        var swap = screen.Model.LegalSwaps()[0];
                        typeof(GameplayScreen).GetMethod("PlayerSwap", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(screen, new object[] { swap[0].x, swap[0].y, swap[1].x, swap[1].y });
                        if (screen.Model.Status != "Engine fault") throw new InvalidOperationException("The throwing command did not end the board as an engine fault: " + screen.Model.Status);
                        Next(); break;
                    case 12:
                        if (!flow.RetryVisible) return;
                        expectFault = false;
                        if (UnityEngine.Object.FindFirstObjectByType<GameplayScreen>()) throw new InvalidOperationException("Engine-fault end state left a GameplayScreen alive.");
                        if (home.State.lives != lives) throw new InvalidOperationException("Engine fault charged a life.");
                        if (LastAttempt.state != "Released") throw new InvalidOperationException("Engine fault did not release the attempt: " + LastAttempt.state);
                        if (!faultLogged) throw new InvalidOperationException("Engine fault did not log its diagnostic.");
                        if (!Profile.Service.Read().starting.SequenceEqual(new[] { 5, 5, 3, 2 })) throw new InvalidOperationException("Released attempt left starting stock inconsistent: " + string.Join(",", Profile.Service.Read().starting));
                        report.checks.Add("A player command that throws (injected) is diagnosed as an engine fault: logged with seed and turn, attempt Released without a life charge, starting stock whole, pre-level reopened.");
                        Finish(); break;
                }
            }
            catch (Exception ex) { report.errors.Add(ex.ToString()); Finish(); }
        }
        static void Next() { phase++; phaseAt = EditorApplication.timeSinceStartup; }
        // Reflow leaves the previous nodes inactive until Destroy runs at end of frame; only live nodes count.
        static Transform FindNode(Transform root, string name)
        {
            if (!root.gameObject.activeSelf) return null;
            if (root.name == name) return root;
            foreach (Transform child in root) { var found = FindNode(child, name); if (found) return found; }
            return null;
        }
        static void CaptureFrame(string path)
        {
            var camera = UnityEngine.Object.FindObjectsByType<Camera>(UnityEngine.FindObjectsSortMode.InstanceID).First(c => c.enabled && c.orthographic);
            var canvases = UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c => c.isActiveAndEnabled && c.renderMode == RenderMode.ScreenSpaceOverlay).ToArray();
            var previousCameras = canvases.Select(c => c.worldCamera).ToArray();
            var distances = canvases.Select(c => c.planeDistance).ToArray();
            var previousTarget = camera.targetTexture;
            var previousActive = RenderTexture.active;
            var target = RenderTexture.GetTemporary(Screen.width, Screen.height, 24, RenderTextureFormat.ARGB32);
            Texture2D pixels = null;
            try
            {
                camera.targetTexture = target;
                camera.Render();
                SavePixels(target,Path.Combine(Path.GetDirectoryName(path),"Connected_BoardOnly.png"));
                foreach (var canvas in canvases)
                {
                    canvas.renderMode = RenderMode.ScreenSpaceCamera;
                    canvas.worldCamera = camera;
                    canvas.planeDistance = 1;
                }
                Canvas.ForceUpdateCanvases();
                camera.Render();
                RenderTexture.active = target;
                pixels = new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);
                pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0,false);
                pixels.Apply(false,false);
                File.WriteAllBytes(path,pixels.EncodeToPNG());
            }
            finally
            {
                for (int i=0;i<canvases.Length;i++)
                {
                    canvases[i].renderMode = RenderMode.ScreenSpaceOverlay;
                    canvases[i].worldCamera = previousCameras[i];
                    canvases[i].planeDistance = distances[i];
                }
                camera.targetTexture = previousTarget;
                RenderTexture.active = previousActive;
                RenderTexture.ReleaseTemporary(target);
                if (pixels) UnityEngine.Object.Destroy(pixels);
            }
        }
        static void SavePixels(RenderTexture target,string path)
        {
            var previous = RenderTexture.active;
            var pixels = new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);
            try
            {
                RenderTexture.active = target;
                pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0,false);
                pixels.Apply(false,false);
                File.WriteAllBytes(path,pixels.EncodeToPNG());
            }
            finally { RenderTexture.active = previous; UnityEngine.Object.Destroy(pixels); }
        }
        static void Finish()
        {
            EditorApplication.update -= Tick;
            Application.logMessageReceived -= OnLog;
            SessionState.EraseBool(Key);
            report.status = report.errors.Count == 0 ? "PASS_NATIVE_PLAY_SMOKE" : "FAIL_NATIVE_PLAY_SMOKE";
            Directory.CreateDirectory(Output);
            File.WriteAllText(Path.Combine(Output, "Play_Smoke.json"), JsonUtility.ToJson(report, true));
            EditorApplication.Exit(report.errors.Count == 0 ? 0 : 1);
        }
    }
}
#endif
