#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;

namespace HeartOfTheRain.Verification
{
    // Opt-in observer of the ordinary app. Unlike replay fixtures, this never
    // replaces profile/settings services, drives input or changes presentation.
    // Its JSON is geometry evidence paired with actual OS screenshots, never a
    // visual PASS or performance sample. All work is limited to one Hz/ten min.
    public sealed class PageBackdrop90DeviceProbe : MonoBehaviour
    {
        public const string Request = "HOTR_RunPageBackdrop90";
        const float DurationSeconds = 600;
        const int MaximumSnapshots = 64;
        const int MaximumObjects = 64;
        static readonly BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
        static readonly HashSet<string> OverlayTypes = new HashSet<string> {
            "FirstStartPage", "LaunchPage", "GameplayLoadingPage", "NoMovesPage",
            "GameplaySettingsModal", "GameplaySettingsController", "EndLevelModal", "AppSettingsPage",
            "PreLevelModal", "ProfilePage", "DailyGiftPage", "WellworksPage", "RainCupPage",
            "AccountModal", "ServerAccountModal83", "VictoryCelebrationPlayer", "ChapterCelebrationPlayer",
            "ShopPage", "LeaderboardPage", "TeamsPage", "JourneyPage", "OnlinePlayersPage82", "OnlineTeamsPage82", "ServerProfilePage83"
        };

        [Serializable] public sealed class CameraGeometry
        {
            public string name, scene, clearFlags;
            public Rect rect, pixelRect;
            public float depth, orthographicSize, aspect;
            public int cullingMask, targetWidth, targetHeight;
            public bool orthographic, hasTargetTexture;
        }
        [Serializable] public sealed class RectGeometry
        {
            public string role, parent;
            public bool present, active, graphicEnabled;
            public Rect localRect;
            public Vector3[] worldCorners;
            public Vector2[] screenCorners;
            public Color color;
        }
        [Serializable] public sealed class HomeGeometry
        {
            public bool present, presentationVisible;
            public RectGeometry background, safeViewport;
        }
        [Serializable] public sealed class CanvasGeometry
        {
            public string name, renderMode;
            public int sortingOrder;
            public float scaleFactor, groupAlpha;
            public RectGeometry bounds;
        }
        [Serializable] public sealed class DecorationGeometry {
            public string name, graphicType, canvas;public bool maskable,raycastTarget;public RectGeometry bounds;
        }
        [Serializable] public sealed class Geometry
        {
            public int width, height, enabledCameraCount, activeCanvasCount;
            public string orientation, activeScene;
            public Rect safeArea;
            public bool focused, paused, cameraListTruncated, canvasListTruncated, decorationsTruncated, safeAreasTruncated, controlsTruncated;
            public int decorationCount, safeAreaCount, controlCount;
            public List<DecorationGeometry> decorations = new List<DecorationGeometry>();
            public List<RectGeometry> safeAreas = new List<RectGeometry>();
            public List<RectGeometry> controls = new List<RectGeometry>();
            public HomeGeometry home;
            public List<CameraGeometry> cameras = new List<CameraGeometry>();
            public List<CanvasGeometry> canvases = new List<CanvasGeometry>();
            public List<string> visibleOverlayTypes = new List<string>();
        }
        [Serializable] public sealed class Snapshot
        {
            public string utc;
            public float observerSeconds;
            public int frame;
            public Geometry geometry;
        }
        [Serializable] public sealed class Report
        {
            public string status = "OBSERVING_PAGE_BACKDROP90", startedUtc, lastSampleUtc, finishedUtc, unity, platform, runId;
            public string scope = "Opt-in ordinary-runtime read-only screen/camera/canvas geometry, at most one sample per second for ten minutes. No profile/preferences access, service replacement, input, rendering changes, screenshots, timing acceptance or visual PASS. Decoration bounds/masking and safe control geometry are observations; actual OS screenshots and separate visual assessment remain required. Pair with the actual Android OS framebuffer.";
            public int snapshotLimit = MaximumSnapshots, droppedOldSnapshots, samples, changes;
            public List<Snapshot> snapshots = new List<Snapshot>();
            public List<string> errorTypes = new List<string>();
        }

        Report report;
        float began, nextSample, lastSave;
        bool paused;
        string previousGeometry;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Boot()
        {
            var marker = Path.Combine(Application.persistentDataPath, Request);
            try
            {
                if (!File.Exists(marker) || new FileInfo(marker).Length > 64) return;
                var request = File.ReadAllText(marker).Trim();
                // Consume only this observer's exact opt-in command.
                if (request != "observe") return;
                File.Delete(marker);
                var node = new GameObject("Opt-in page backdrop90 geometry observer");
                DontDestroyOnLoad(node);
                node.AddComponent<PageBackdrop90DeviceProbe>();
            }
            catch (IOException) { /* A missing/unreadable opt-in cannot alter ordinary startup. */ }
            catch (UnauthorizedAccessException) { }
        }

        void Start()
        {
            began = Time.realtimeSinceStartup;
            nextSample = began;
            report = new Report { startedUtc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion, platform = Application.platform.ToString(), runId=Guid.NewGuid().ToString("N") };
        }

        void OnApplicationPause(bool value) { paused = value; }

        void LateUpdate()
        {
            if (report == null || report.status != "OBSERVING_PAGE_BACKDROP90" || Time.realtimeSinceStartup < nextSample) return;
            float now = Time.realtimeSinceStartup;
            nextSample = now + 1;
            bool completed = now - began >= DurationSeconds;
            bool save = now - lastSave >= 10;
            report.lastSampleUtc = DateTime.UtcNow.ToString("o");
            try
            {
                var geometry = Observe();
                report.samples++;
                var signature = JsonUtility.ToJson(geometry);
                if (signature != previousGeometry)
                {
                    previousGeometry = signature;
                    report.changes++;
                    if (report.snapshots.Count == MaximumSnapshots) { report.snapshots.RemoveAt(0); report.droppedOldSnapshots++; }
                    report.snapshots.Add(new Snapshot { utc = DateTime.UtcNow.ToString("o"), observerSeconds = now - began, frame = Time.frameCount, geometry = geometry });
                    save = true;
                }
            }
            catch (Exception error)
            {
                // Do not export exception messages/stacks containing runtime
                // paths or user text. Diagnostics must not break the app.
                if (report.errorTypes.Count < 16) report.errorTypes.Add(error.GetType().Name);
                save = true;
            }
            if (completed)
            {
                report.status = "RECORDED_PAGE_BACKDROP90_OBSERVATION";
                report.finishedUtc = DateTime.UtcNow.ToString("o");
                save = true;
                enabled = false;
            }
            if (save) { Save(); lastSave = now; }
        }

        static Geometry Observe()
        {
            var result = new Geometry {
                width = Screen.width, height = Screen.height, safeArea = Screen.safeArea,
                orientation = Screen.orientation.ToString(), focused = Application.isFocused,
                activeScene = SceneManager.GetActiveScene().name
            };
            var observer = FindFirstObjectByType<PageBackdrop90DeviceProbe>();
            result.paused = observer && observer.paused;
            var cameras = FindObjectsByType<Camera>(UnityEngine.FindObjectsSortMode.InstanceID).Where(value => value.isActiveAndEnabled)
                .OrderBy(value => value.depth).ThenBy(value => value.name, StringComparer.Ordinal).ToArray();
            result.enabledCameraCount = cameras.Length;
            result.cameraListTruncated = cameras.Length > MaximumObjects;
            foreach (var value in cameras.Take(MaximumObjects)) result.cameras.Add(new CameraGeometry {
                name = value.name, scene = value.gameObject.scene.name, rect = value.rect, pixelRect = value.pixelRect,
                depth = value.depth, clearFlags = value.clearFlags.ToString(), cullingMask = value.cullingMask,
                orthographic = value.orthographic, orthographicSize = value.orthographicSize, aspect = value.aspect,
                hasTargetTexture = value.targetTexture, targetWidth = value.targetTexture ? value.targetTexture.width : 0,
                targetHeight = value.targetTexture ? value.targetTexture.height : 0
            });
            var home = FindFirstObjectByType<HomePage>();
            result.home = new HomeGeometry { present = home, presentationVisible = home && home.PresentationVisible };
            if (home)
            {
                var image = typeof(HomePage).GetField("background", Private)?.GetValue(home) as RawImage;
                var safe = typeof(HomePage).GetField("safeViewport", Private)?.GetValue(home) as RectTransform;
                result.home.background = Bounds("Home background", image ? image.rectTransform : null);
                result.home.safeViewport = Bounds("Home safe viewport", safe);
            }
            var canvases = FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(value => value.isActiveAndEnabled)
                .OrderBy(value => value.sortingOrder).ThenBy(value => value.name, StringComparer.Ordinal).ToArray();
            result.activeCanvasCount = canvases.Length;
            result.canvasListTruncated = canvases.Length > MaximumObjects;
            foreach (var value in canvases.Take(MaximumObjects))
            {
                var group = value.GetComponent<CanvasGroup>();
                result.canvases.Add(new CanvasGeometry { name = value.name, renderMode = value.renderMode.ToString(),
                    sortingOrder = value.sortingOrder, scaleFactor = value.scaleFactor, groupAlpha = group ? group.alpha : 1,
                    bounds = Bounds("Canvas", value.transform as RectTransform) });
            }
            foreach (var value in FindObjectsByType<MonoBehaviour>(UnityEngine.FindObjectsSortMode.InstanceID))
            {
                var type = value.GetType();
                if (!value.isActiveAndEnabled || !OverlayTypes.Contains(type.Name) || type.Namespace == null || !type.Namespace.StartsWith("HeartOfTheRain.", StringComparison.Ordinal)) continue;
                var property = type.GetProperty("IsVisible") ?? type.GetProperty("Visible");
                if (property == null || property.PropertyType != typeof(bool) || property.GetIndexParameters().Length != 0) continue;
                try { if ((bool)property.GetValue(value, null)) result.visibleOverlayTypes.Add(type.FullName); }
                catch (TargetInvocationException) { }
            }
            var graphics=FindObjectsByType<MaskableGraphic>(UnityEngine.FindObjectsSortMode.InstanceID).Where(g=>g.isActiveAndEnabled&&DecorationName(g.name)).OrderBy(g=>g.canvas?g.canvas.sortingOrder:0).ThenBy(g=>g.name,StringComparer.Ordinal).ToArray();
            result.decorationCount=graphics.Length;result.decorationsTruncated=graphics.Length>128;
            foreach(var graphic in graphics.Take(128))result.decorations.Add(new DecorationGeometry{name=graphic.name,graphicType=graphic.GetType().Name,canvas=graphic.canvas?graphic.canvas.name:"",maskable=graphic.maskable,raycastTarget=graphic.raycastTarget,bounds=Bounds(graphic.name,graphic.rectTransform)});
            var safeRects=FindObjectsByType<RectTransform>(UnityEngine.FindObjectsSortMode.InstanceID).Where(r=>r.gameObject.activeInHierarchy&&r.name.IndexOf("safe",StringComparison.OrdinalIgnoreCase)>=0&&r.GetComponent<RectMask2D>()).OrderBy(r=>r.name,StringComparer.Ordinal).ToArray();
            result.safeAreaCount=safeRects.Length;result.safeAreasTruncated=safeRects.Length>64;
            foreach(var safe in safeRects.Take(64))result.safeAreas.Add(Bounds(safe.name,safe));
            var buttons=FindObjectsByType<Button>(UnityEngine.FindObjectsSortMode.InstanceID).Where(b=>b.isActiveAndEnabled&&b.gameObject.activeInHierarchy).OrderBy(b=>b.name,StringComparer.Ordinal).ToArray();
            result.controlCount=buttons.Length;result.controlsTruncated=buttons.Length>256;
            foreach(var button in buttons.Take(256))result.controls.Add(Bounds(button.name,button.transform as RectTransform));
            result.visibleOverlayTypes = result.visibleOverlayTypes.Distinct().OrderBy(value => value, StringComparer.Ordinal).ToList();
            return result;
        }

        static bool DecorationName(string name){
            string value=name.ToLowerInvariant();return value.Contains("backdrop")||value.Contains("background")||value.Contains("matte")||value.Contains("scrim")||value.Contains("shade")||value=="scene-art"||value=="top-bar"||value=="chapter artwork"||value=="raindrops";
        }
        static RectGeometry Bounds(string role, RectTransform value)
        {
            var result = new RectGeometry { role = role, present = value };
            if (!value) return result;
            result.parent = value.parent ? value.parent.name : "";
            result.active = value.gameObject.activeInHierarchy;
            result.localRect = value.rect;
            result.worldCorners = new Vector3[4];
            result.screenCorners = new Vector2[4];
            value.GetWorldCorners(result.worldCorners);
            var canvas = value.GetComponentInParent<Canvas>();
            var camera = canvas && canvas.renderMode != RenderMode.ScreenSpaceOverlay ? canvas.worldCamera : null;
            for (int i = 0; i < 4; i++) result.screenCorners[i] = RectTransformUtility.WorldToScreenPoint(camera, result.worldCorners[i]);
            var graphic = value.GetComponent<Graphic>();
            result.graphicEnabled = graphic && graphic.enabled;
            result.color = graphic ? graphic.color : Color.clear;
            return result;
        }

        void Save()
        {
            try
            {
                var directory = Path.Combine(Application.persistentDataPath, "PageBackdrop90");
                Directory.CreateDirectory(directory);
                File.WriteAllText(Path.Combine(directory, "Report.json"), JsonUtility.ToJson(report, true));
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
    }
}
#endif
