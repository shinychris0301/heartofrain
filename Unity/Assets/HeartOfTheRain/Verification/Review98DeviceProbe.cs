#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification
{
    // Exact, bounded opt-in before Home starts. Only the normal review memory
    // profile is changed; owner repositories and settings are never replaced.
    public sealed class Review98DeviceProbe : MonoBehaviour
    {
        public const string Marker = "HOTR_RunReview98";
        public const string StepMarker = "HOTR_Review98Step";
        public static string Output => Path.Combine(Application.persistentDataPath, "Review98Device");
        const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
        static string pending;
        [Serializable] public sealed class Report
        {
            public string status = "STARTING", utc, mode, error, unity, platform, family, attemptState;
            public int initialMoves;
            public string scope = "Development-only memory-profile fixture with actual Android taps. Header, refill and labels are measured in the real app; duplicate callbacks are synthetic. No owner save/preferences writes, provider, gameplay performance or visual approval.";
            public int checks, x, y, coins, lives, refillReceipts, attempts, width, height;
            public bool autoDismissed,focused,paused;public int backgroundEntries,resumes,rocketBefore,rocketAfter;public double visibleForegroundSeconds;public long startedRevision;
            public bool livesOnly,gameplayArtLoaded;public int[] starting;
            public List<string> passed = new List<string>();
        }
        Report report;
        HomePage home;
        PlayerProfileHost host;
        HomeLevelFlow flow;
        PreLevelModal modal;
        float deadline;
        int phase,introStartedFrame;bool applicationPaused;
        GameplayScreen introGame;
        int[] livesStarting;
        bool FullLives=>report.mode=="lives_full101";
        bool PartialLives=>report.mode=="lives_partial101";
        bool AffordableLives=>report.mode=="prelevel_900"||report.mode=="lives_900101";
        static T Field<T>(object value, string name) => (T)value.GetType().GetField(name, Private).GetValue(value);

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Boot()
        {
            string marker = Path.Combine(Application.persistentDataPath, Marker);
            try
            {
                if (!File.Exists(marker) || new FileInfo(marker).Length > 64) return;
                string mode = File.ReadAllText(marker).Trim();
                if (mode != "prelevel_899" && mode != "prelevel_900" && mode != "obstacle_intro" && mode!="lives_full101" && mode!="lives_partial101" && mode!="lives_899101" && mode!="lives_900101") return;
                pending = mode; File.Delete(marker); SceneManager.sceneLoaded += Attach;
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
        static void Attach(Scene scene, LoadSceneMode mode)
        {
            var first = FindFirstObjectByType<FirstStartPage>();
            if (!first) return;
            SceneManager.sceneLoaded -= Attach;
            first.reviewAlways = true;
            var profile = first.home.GetComponent<PlayerProfileHost>();
            if (!profile) profile = first.home.gameObject.AddComponent<PlayerProfileHost>();
            profile.VerificationLivesClock = () => 1000;
            profile.VerificationCupClock = () => 1000;
            var node = new GameObject("Opt-in Review98 memory-profile device fixture");
            DontDestroyOnLoad(node);
            var probe = node.AddComponent<Review98DeviceProbe>();
            probe.report = new Report { utc = DateTime.UtcNow.ToString("o"), mode = pending, unity = Application.unityVersion, platform = Application.platform.ToString() };
            pending = null;
        }
        void Start() { deadline = Time.realtimeSinceStartup + 180; }
        void Check(bool condition, string message)
        {
            report.checks++;
            if (!condition) throw new InvalidOperationException(message);
            report.passed.Add(message);
        }
        void Update()
        {
            if (report == null || report.status.StartsWith("PASS", StringComparison.Ordinal) || report.status.StartsWith("FAIL", StringComparison.Ordinal)) return;
            try
            {
                if (Time.realtimeSinceStartup > deadline) throw new TimeoutException("Review98 device fixture timed out waiting for its explicit tap/step");
                if (report.mode == "obstacle_intro") { UpdateIntroduction(); return; }
                if (phase == 0)
                {
                    var first = FindFirstObjectByType<FirstStartPage>();
                    if (!first || !first.Initialized) return;
                    home = first.home; host = home.GetComponent<PlayerProfileHost>();
                    if (!host || !host.Ready) return;
                    Check(host.IsTransient && !host.ServerSession && first.reviewAlways, "Disposable local review memory is selected before any balance mutation");
                    first.Request("skip"); first.Request("skip");
                    flow = home.GetComponent<HomeLevelFlow>(); modal = home.GetComponent<PreLevelModal>();
                    Check(home.PresentationInteractable && flow && flow.CanOpenAppSettings && modal, "Interactive Home is ready without a live attempt");
                    host.Service.Change(p => { p.coins = FullLives||PartialLives?1250:AffordableLives?900:899; p.lives = FullLives?5:PartialLives?3:0; p.livesRefillDueUnix = FullLives?0:2800; return true; });
                    Check(host.Refresh(), "Memory-profile lives fixture applied");livesStarting=(int[])host.Service.Read().starting.Clone();
                    var nodes = Field<Dictionary<string, RectTransform>>(home, "nodes");
                    var header = nodes["header"];
                    Vector2 point = RectTransformUtility.WorldToScreenPoint(null, header.TransformPoint(new Vector3(header.rect.width * .60f, -header.rect.height * .5f, 0)));
                    SetPoint(point, "READY_FOR_LIVES_TAP"); phase = 1; return;
                }
                if (phase == 1)
                {
                    if (!modal.IsVisible) return;
                    Check(flow.Preview.livesOnly&&flow.Preview.lives==(FullLives?5:PartialLives?3:0), "Actual header tap opens the dedicated lives-only panel");
                    var nodes = Field<Dictionary<string, RectTransform>>(modal, "nodes");
                    Check(!nodes.Keys.Any(k => k.StartsWith("booster-", StringComparison.Ordinal)||k.StartsWith("target-",StringComparison.Ordinal)||k.StartsWith("reward-",StringComparison.Ordinal))&&!nodes.ContainsKey("level"), "Lives panel contains no level, goals, rewards or booster selection");
                    Check(!flow.Loading.IsVisible&&!flow.Loading.art&&Field<ResourceRequest>(flow,"artRequest")==null,"Header information tap does not prepare gameplay loading artwork");
                    Check(nodes["lives-heart"].GetComponent<Image>().sprite==HomeLivesAssets.Load().heart,"Existing healthy-heart artwork is displayed");
                    modal.Requested("play");modal.Requested("toggle:0");var unchanged=host.Service.Read();
                    Check(!flow.Playing&&!flow.Preview.busy&&!flow.Preview.selected.Any(v=>v)&&unchanged.attempts.Count==0&&unchanged.starting.SequenceEqual(livesStarting),"Hidden Play and booster callbacks cannot launch or spend inventory");
                    if(FullLives||PartialLives){
                        Check(!nodes.ContainsKey("play")&&nodes.ContainsKey("lives-clock")==PartialLives,"Full/partial lives show status without Play or purchase controls");
                        Check(nodes["lives-count"].GetComponent<Text>().text==(FullLives?"5 / 5":"3 / 5"),"Actual count includes the life cap");
                        Check(nodes["lives-status"].GetComponent<Text>().text==(FullLives?HomeLivesText.T("full"):HomeLivesText.T("nextLife").Replace("{time}","30:00")),"Full or next-life timer matches memory authority");
                        report.status="READY_FOR_LIVES_VERIFY";Save();phase=2;return;
                    }
                    Check(flow.Preview.refillCoins==900,"Zero-only refill keeps its approved price");
                    Check(nodes["play-text"].GetComponent<Text>().text.Contains("900"), "Refill900 price stays visible for both wallet balances");
                    var buy = nodes["play"].GetComponent<Button>();
                    Check(buy.interactable == AffordableLives, "Refill availability respects899/900 boundary");
                    Canvas.ForceUpdateCanvases();
                    var timer = nodes["lives-status"]; var button = nodes["play"];
                    Check(timer.anchoredPosition.y - timer.rect.height > button.anchoredPosition.y, "Countdown is above the primary action instead of inside its artwork");
                    SetPoint(RectTransformUtility.WorldToScreenPoint(null, button.TransformPoint(button.rect.center)), AffordableLives ? "READY_FOR_REFILL_TAP" : "READY_FOR_DISABLED_REFILL_TAP");
                    phase = 2; return;
                }
                if (phase == 2)
                {
                    var profile = host.Service.Read();
                    if (AffordableLives)
                    {
                        if (profile.lives == 0) return;
                        Check(profile.coins == 0 && profile.lives == 5 && profile.lifeRefills.Count == 1 && profile.lifeRefills[0].coins == 900, "Actual refill tap debits900 and grants all five lives once");
                        modal.Requested("refill"); modal.Requested("refill");
                        profile = host.Service.Read();
                        Check(profile.coins == 0 && profile.lives == 5 && profile.lifeRefills.Count == 1, "Synthetic duplicate refill callbacks cannot double debit");
                    }
                    else
                    {
                        string step = Path.Combine(Application.persistentDataPath, StepMarker);
                        if (!File.Exists(step) || new FileInfo(step).Length > 64 || File.ReadAllText(step).Trim() != "verify") return;
                        File.Delete(step);
                        Check(profile.coins == (FullLives||PartialLives?1250:899) && profile.lives == (FullLives?5:PartialLives?3:0) && profile.lifeRefills.Count == 0, "Verification leaves informational or insufficient lives and wallet unchanged");
                        if(!FullLives&&!PartialLives)Check(Field<Dictionary<string, RectTransform>>(modal, "nodes").ContainsKey("refill-unaffordable"), "Insufficient wallet has a visible explanatory note");
                    }
                    Check(!flow.Playing && profile.attempts.Count == 0 && modal.IsVisible, "Refill never starts a level or creates an attempt");
                    Check(profile.starting.SequenceEqual(livesStarting)&&flow.Preview.livesOnly,"Lives interactions keep booster inventory and lives-only route");
                    if(AffordableLives)Check(!Field<Dictionary<string,RectTransform>>(modal,"nodes").ContainsKey("play"),"Completed refill shows Full without offering Play or automatic start");
                    report.status = report.mode.StartsWith("prelevel_",StringComparison.Ordinal)?"PASS_NATIVE_REVIEW98_PRELEVEL_FIXTURE":"PASS_NATIVE_LIVES101_FIXTURE"; Save(); phase = 3;
                }
            }
            catch (Exception error) { report.status = "FAIL_REVIEW98_PRELEVEL_FIXTURE"; report.error = error.GetType().Name + ": " + error.Message; Save(); }
        }
        void UpdateIntroduction()
        {
            if (phase == 0)
            {
                var first = FindFirstObjectByType<FirstStartPage>();
                if (!first || !first.Initialized) return;
                home = first.home; host = home.GetComponent<PlayerProfileHost>();
                if (!host || !host.Ready) return;
                Check(host.IsTransient && !host.ServerSession && first.reviewAlways, "Introduction fixture uses disposable memory only");
                first.Request("skip"); first.Request("skip");
                flow = home.GetComponent<HomeLevelFlow>(); modal = home.GetComponent<PreLevelModal>();
                host.Service.Change(p => { p.completed = 6; p.currentLevel = 7; return true; });
                Check(host.Refresh(), "First stone level is available in isolated progression");
                report.scope="Memory-only actual Android timed obstacle card and optional OS pause/resume. No manual introduction action. Reserved/input/wallet/move checks precede automatic dismissal; not owner data, human campaign or performance acceptance.";
                flow.Open(7);modal.Requested("toggle:0");Check(flow.Preview.selected[0]&&host.Service.Read().starting[0]==5,"Selecting a Rocket reserves it without a debit");report.rocketBefore=5;modal.Requested("play");phase=1;return;
            }
            if (phase == 1)
            {
                introGame = FindFirstObjectByType<GameplayScreen>();
                if (!introGame || !introGame.InitializationComplete) return;
                var hud = introGame.GetComponent<GameplayHUD>();
                if (!hud || !hud.ObstacleIntroductionVisible) return;
                var profile = host.Service.Read(); var attempt = profile.attempts.Last();
                Check(hud.ObstacleIntroductionFamily == "stone" && introGame.CurrentLevel == 7, "First actual stone encounter opens its introduction");
                Check(attempt.state == "Reserved" && introGame.ReviewInputBlocked, "Introduction blocks input before committed start");
                Check(profile.coins == 1250 && profile.lives == 5 && profile.starting.SequenceEqual(new[]{5,5,3,2}), "Introduction spends no life, coins or starting items");
                Check(!home.PresentationVisible && !flow.Loading.IsVisible, "Ready board introduction replaces loading without an extra timed wait");
                var dialog = Field<RectTransform>(hud,"modal").Find("Dialog");
                Check(dialog.GetComponentsInChildren<Button>().Length == 0, "Timed introduction has no Continue button");
                report.family = hud.ObstacleIntroductionFamily; report.attemptState = attempt.state; report.initialMoves = introGame.Model.Moves;
                report.status="OBSERVING_OBSTACLE_AUTO";Save();phase = 2; return;
            }
            if (phase == 2)
            {
                var hud = introGame.GetComponent<GameplayHUD>();var profile = host.Service.Read();var attempt = profile.attempts.Last();
                if (hud.ObstacleIntroductionVisible)
                {
                    Check(attempt.state == "Reserved" && introGame.ReviewInputBlocked && !introGame.CanAct, "Visible timed card remains Reserved and blocks all player input");
                    Check(introGame.Model.Moves == report.initialMoves && profile.coins == 1250 && profile.lives == 5 && profile.starting.SequenceEqual(new[]{5,5,3,2}), "Visible dwell cannot spend moves, balance, lives or starting items");
                    Save();return;
                }
                if (introGame.ReviewInputBlocked) return;
                Check(hud.LastObstacleIntroductionFamily == "stone" && hud.LastObstacleIntroductionVisibleSeconds >= 1.5 && hud.LastObstacleIntroductionVisibleSeconds < 2, "Automatic card completion follows1.5fully visible foreground seconds");
                Check(attempt.state == "Started" && flow.Playing && introGame.Model.Moves == report.initialMoves, "Automatic dismissal commits start without using a move");
                Check(profile.coins == 1250 && profile.lives == 5 && profile.starting.SequenceEqual(new[]{4,5,3,2}), "Timed dismissal commits exactly one selected Rocket debit with no coin or life charge");report.rocketAfter=profile.starting[0];
                report.autoDismissed=true;report.visibleForegroundSeconds=hud.LastObstacleIntroductionVisibleSeconds;report.attemptState=attempt.state;report.startedRevision=profile.revision;introStartedFrame=Time.frameCount;phase=3;return;
            }
            if (phase == 3)
            {
                if(Time.frameCount<=introStartedFrame+2)return;var profile=host.Service.Read();
                Check(profile.revision==report.startedRevision&&profile.attempts.Count==1&&profile.attempts[0].state=="Started", "Repeated settled frames cannot commit another start or debit");
                report.status="PASS_NATIVE_REVIEW99_OBSTACLE_FIXTURE";Save();phase=4;
            }
        }
        void OnApplicationPause(bool paused)
        {
            if(applicationPaused==paused)return;applicationPaused=paused;
            if(report!=null&&report.mode=="obstacle_intro"){if(paused)report.backgroundEntries++;else report.resumes++;Save();}
        }
        void OnApplicationFocus(bool focused){if(report!=null&&report.mode=="obstacle_intro"){report.focused=focused;Save();}}
        void SetPoint(Vector2 point, string status)
        {
            report.x = Mathf.RoundToInt(point.x); report.y = Screen.height - Mathf.RoundToInt(point.y); report.status = status; Save();
        }
        void Save()
        {
            report.width = Screen.width; report.height = Screen.height;
            report.focused=Application.isFocused;report.paused=applicationPaused;
            if(report.mode=="obstacle_intro"&&introGame){var hud=introGame.GetComponent<GameplayHUD>();if(hud)report.visibleForegroundSeconds=hud.ObstacleIntroductionVisible?hud.ObstacleIntroductionFullyVisibleSeconds:hud.LastObstacleIntroductionVisibleSeconds;}

            if (host && host.Ready) { var profile = host.Service.Read(); report.coins = profile.coins; report.lives = profile.lives; report.refillReceipts = profile.lifeRefills.Count; report.attempts = profile.attempts.Count; }
            if(report.mode!="obstacle_intro"&&flow){report.livesOnly=flow.Preview!=null&&flow.Preview.livesOnly;report.gameplayArtLoaded=flow.Loading&&(flow.Loading.art||Field<ResourceRequest>(flow,"artRequest")!=null);if(host&&host.Ready)report.starting=(int[])host.Service.Read().starting.Clone();}
            Directory.CreateDirectory(Output); File.WriteAllText(Path.Combine(Output, "Report.json"), JsonUtility.ToJson(report, true));
        }
        void OnDestroy() { SceneManager.sceneLoaded -= Attach; }
    }
}
#endif
