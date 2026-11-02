#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.LevelComplete;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.Verification
{
    // Editor-only checks against real Unity imports and the live M46/M48 model.
    // No Configure, bake, importer changes, preview resets or save writes.
    public static class NativeVerification
    {
        sealed class StageStore:HeartOfTheRain.App.Settings.ISettingsStore
        {
            public int stage;
            public int Read(string key,int fallback)=>key==HeartOfTheRain.App.FirstStart.FirstStartSession.StageKey?stage:fallback;
            public void Write(string key,int value){}public void Flush(){}
        }
        [Serializable] sealed class ResourceCatalog { public ResourceSize[] textures; }
        [Serializable] sealed class ResourceSize { public string path; public int width, height; }
        // The delivered binding points Shop/Inventory at Sprite subassets, but
        // these four sources were imported as Default textures (no Sprite exists).
        public static void PrepareBindings()
        {
            HeartOfTheRain.App.Home.Editor.HomePageEditor.RefreshBindings();
            foreach (string name in new[] { "Hammer", "Axe", "Ram", "Atlas" })
            {
                string path = "Assets/HeartOfTheRain/Boosters/Art/" + name + ".png";
                var importer = (TextureImporter)AssetImporter.GetAtPath(path);
                if (importer.textureType == TextureImporterType.Sprite && importer.spriteImportMode == SpriteImportMode.Single) continue;
                importer.textureType = TextureImporterType.Sprite;
                importer.spriteImportMode = SpriteImportMode.Single;
                importer.SaveAndReimport();
            }
            var resources = JsonUtility.FromJson<ResourceCatalog>(File.ReadAllText("Assets/HeartOfTheRain/M48/Data/Resource_Catalog.json"));
            foreach (var resource in resources.textures.Where(r => Math.Max(r.width,r.height) > 2048))
            {
                var importer = (TextureImporter)AssetImporter.GetAtPath(resource.path);
                int size = Mathf.NextPowerOfTwo(Math.Max(resource.width,resource.height));
                bool changed = false;
                foreach (string platform in new[] { "DefaultTexturePlatform", "Standalone", "Android", "iPhone" })
                {
                    var settings = importer.GetPlatformTextureSettings(platform);
                    if (settings.maxTextureSize >= size) continue;
                    settings.maxTextureSize = size;
                    importer.SetPlatformTextureSettings(settings);
                    changed = true;
                }
                if (changed) importer.SaveAndReimport();
            }
            var ui = AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
            Require(ui != null && ui.boards != null, "Live M48 UI/board bindings must resolve first.");
            if (ui.bodyShader == null)
            {
                ui.bodyShader = Shader.Find("Sprites/Default");
                Require(ui.bodyShader != null, "Built-in Sprite shader not available.");
                EditorUtility.SetDirty(ui);
                AssetDatabase.SaveAssetIfDirty(ui);
            }
            Debug.Log("Prepared existing navigation/tool Sprite bindings, full-size fragment atlas imports and the existing fallback Sprite shader binding. No artwork, GUID, level or build-scene change.");
        }
        [Serializable] sealed class Binding { public string owner, property, target; }
        [Serializable] sealed class Bindings { public List<Binding> references = new List<Binding>(); }
        public static void InspectBindings()
        {
            var result = new Bindings();
            foreach (string guid in AssetDatabase.FindAssets("t:ScriptableObject", new[] { "Assets/HeartOfTheRain" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var asset = AssetDatabase.LoadMainAssetAtPath(path);
                if (!asset) continue;
                result.references.Add(new Binding { owner = path, property = "$managedType", target = asset.GetType().AssemblyQualifiedName });
                var serialized = new SerializedObject(asset);
                var property = serialized.GetIterator();
                while (property.Next(true))
                    if (property.propertyType == SerializedPropertyType.ObjectReference)
                        result.references.Add(new Binding { owner = path, property = property.propertyPath, target = property.objectReferenceValue ? AssetDatabase.GetAssetPath(property.objectReferenceValue) : "NULL" });
            }
            string output = Path.GetFullPath("../Verification/Evidence/Native/Imported_Bindings.json");
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            File.WriteAllText(output, JsonUtility.ToJson(result, true));
        }
        [Serializable] public sealed class Check
        {
            public string name, status, error;
        }
        [Serializable] public sealed class Report
        {
            public string status, utc, unity;
            public string scope = "Native Unity Editor imports and model checks; no device, touch, visual approval, performance or durable-save certification.";
            public int passed, failed;
            public List<Check> checks = new List<Check>();
            public CampaignValidationReport campaign;
        }

        [MenuItem("Heart of the Rain/Verification/Run Native Baseline Checks")]
        public static void Run()
        {
            var report = new Report { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion };
            RunCase(report, "Pinned editor", () => Require(Application.unityVersion == "2022.3.62f3", "Use the pinned editor."));
            RunCase(report, "Native effects and glow shaders draw visible pixels", NativeRenderProbe.RunAfter);
            RunCase(report, "Portrait lessons retain result and no-cost note in all five locales", () =>
            {
                var assets=AssetDatabase.LoadAssetAtPath<HeartOfTheRain.App.FirstStart.FirstStartAssets>("Assets/HeartOfTheRain/App/FirstStart/FirstStartAssets.asset");
                var lessons=assets.lessons.Select(t=>JsonUtility.FromJson<LevelData>(t.text)).ToArray();
                int original=HeartOfTheRain.App.Localization.GameLocale.Current;
                try
                {
                    for(int locale=0;locale<5;locale++)
                    {
                        HeartOfTheRain.App.Localization.GameLocale.Select(locale);
                        foreach(var size in new[]{new Vector2(393,698),new Vector2(393,852),new Vector2(768,1024)})
                            for(int stage=2;stage<=4;stage++)
                            {
                                var session=new HeartOfTheRain.App.FirstStart.FirstStartSession(new StageStore{stage=stage},lessons);
                                var frame=HeartOfTheRain.App.FirstStart.FirstStartLayout.Build(size.x,size.y,session,"");
                                var note=frame.content.elements.First(e=>e.id=="practice-note");
                                Require(note.y+note.height<=frame.viewportHeight+.51f,"Lesson note clipped: "+locale+" stage "+stage+" size "+size);
                                Require(frame.content.elements.First(e=>e.id=="practice-board").width>=220,"Practice board shrank below its readable size.");
                            }
                    }
                }
                finally{HeartOfTheRain.App.Localization.GameLocale.Select(original);}
            });
            RunCase(report, "Home layouts resolve every sprite including shared navigation", () =>
            {
                var assets = AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset");
                var header=new HomeHeaderSprites(assets.Find("R4_Header"));try {
                foreach (var size in new[] { new Vector2(360,800), new Vector2(768,1024), new Vector2(1280,720) })
                    foreach (bool drawer in new[] { false,true })
                        foreach (var element in HomeLayoutEngine.Build(size.x,size.y,new HomeState(),drawer).elements.Where(e=>e.kind=="sprite"))
                            Require((element.asset=="HomeHeaderPanel"?header.Panel:element.asset=="HomeHeaderDefaultAvatar"?header.DefaultAvatar:element.asset=="HomeHeaderConnector"?header.Connector:assets.Find(element.asset)) != null, "Missing Home sprite: " + element.asset);
                }finally{UnityEngine.Object.DestroyImmediate(header.Panel);UnityEngine.Object.DestroyImmediate(header.DefaultAvatar);UnityEngine.Object.DestroyImmediate(header.Connector);}
            });
            RunCase(report, "Pre-level lookup reaches all nine gameplay goal sprites", () =>
            {
                var assets = AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");
                foreach (string family in new[] { "crate","moss","stone","pail","case","gate","crystal","pod","rainlight" })
                    Require(assets.Find(GameplayHUD.GoalSprite(family)) != null, "Missing goal fallback: " + family);
                Require(assets.Find("Rocket") != null && assets.Find("Bomb") != null && assets.Find("R4_Start") != null, "Own/Home lookup regressed.");
            });
            var levels = new List<LevelData>();
            for (int n = 1; n <= 50; n++)
            {
                int number = n;
                RunCase(report, "Level " + n + " imported definition", () =>
                {
                    var asset = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/HeartOfTheRain/M47/Data/Levels/C01_L" + number.ToString("000") + ".json");
                    Require(asset != null, "Missing imported level.");
                    var level = JsonUtility.FromJson<LevelData>(asset.text);
                    Require(level.globalLevel == number, "Wrong level identity.");
                    new BoardModel(level).ValidateCampaignOpening();
                    levels.Add(level);
                });
            }
            RunCase(report, "Moss honors interval and lifetime growth limit", () =>
            {
                var data=JsonUtility.FromJson<LevelData>(JsonUtility.ToJson(levels[0]));
                data.mossRegrowth=new GrowthRule{enabled=true,undamagedMoves=3,maxNewClumps=1};
                var board=new BoardModel(data);
                var method=typeof(BoardModel).GetMethod("Regrow",BindingFlags.Instance|BindingFlags.NonPublic);
                var turn=new TurnResult();
                method.Invoke(board,new object[]{turn});method.Invoke(board,new object[]{turn});
                Require(board.GrowthUsed==0&&board.QuietMoves==2,"Growth ignored the configured quiet interval.");
                method.Invoke(board,new object[]{turn});
                Require(board.GrowthUsed==1&&board.QuietMoves==0,"Configured growth did not fire.");
                for(int i=0;i<12;i++)method.Invoke(board,new object[]{turn});
                Require(board.GrowthUsed==1,"Lifetime growth cap ignored.");board.Validate();
                // Checkpoint 60: a tool that damages moss breaks the quiet streak like a move would.
                board=new BoardModel(data);turn=new TurnResult();method.Invoke(board,new object[]{turn});method.Invoke(board,new object[]{turn});
                Require(board.QuietMoves==2,"Quiet streak did not build before the tool.");
                var moss=board.Pieces.Values.First(p=>p.family=="moss");var hammer=new BoosterInventory{hammer=1};
                Require(board.UseBooster(BoosterKind.Hammer,moss.x,moss.y,hammer).accepted,"Hammer on moss was rejected.");
                Require(board.QuietMoves==0&&board.GrowthUsed==0,"Tool damage to moss did not reset the quiet streak.");board.Validate();
                data.mossRegrowth.maxNewClumps=0;board=new BoardModel(data);turn=new TurnResult();
                for(int i=0;i<6;i++)method.Invoke(board,new object[]{turn});
                Require(board.GrowthUsed==0,"Zero growth budget produced a clump.");
                data.mossRegrowth.undamagedMoves=0;
                bool rejected=false;try{new BoardModel(data);}catch(ArgumentException){rejected=true;}
                Require(rejected,"Invalid enabled growth interval was accepted.");
                data.mossRegrowth=new GrowthRule{enabled=true,afterConsecutiveMovesWithoutMossDamage=1,maxNewCellsTotal=2};
                board=new BoardModel(data);turn=new TurnResult();
                for(int i=0;i<5;i++)method.Invoke(board,new object[]{turn});
                Require(board.GrowthUsed==2,"Legacy authored growth names were not honored.");
            });
            RunCase(report, "Pre-level refill price, timer, compact labels and all five locales", () => { PreLevelChecks98(); });
            RunCase(report, "Obstacle cards require1.5fully-visible foreground seconds with pause/resume anchors", () => { ObstacleTimingChecks99(); });
            RunCase(report, "Shipping build settings enable only Launch and First Start", () =>
            {
                var enabled=EditorBuildSettings.scenes.Where(s=>s.enabled).Select(s=>s.path).ToArray();
                Require(enabled.SequenceEqual(new[]{HeartOfTheRain.App.Launch.LaunchPage.ScenePath,HeartOfTheRain.App.Launch.LaunchPage.GameScenePath}),"Enabled build scenes: "+string.Join(", ",enabled));
                Require(EditorBuildSettings.scenes.Length==18,"Review scenes should stay listed (disabled), not removed.");
            });
            RunCase(report, "Failed reshuffle ends the turn as No legal moves", () =>
            {
                // 2x2 active corner of a 3x3 grid, one color, one crate: after the
                // rocket clears row 0 the three gems form an L, no swap can match
                // and recoloring cannot help.
                var data=new LevelData{id="VERIFY_DEADLOCK",name="Deadlock fixture",columns=3,rows=3,globalLevel=1,movesProposal=10,tileSeed=7,
                    activeCells=new[]{new Cell(0,0),new Cell(1,0),new Cell(0,1),new Cell(1,1)},spawnPoints=new[]{new Cell(0,1),new Cell(1,1)},deliveryExits=new Cell[0],
                    initialTiles=new[]{new GemCell{x=0,y=0,color=0},new GemCell{x=1,y=0,color=0},new GemCell{x=0,y=1,color=0}},
                    obstacles=new[]{new ObstacleCell{x=1,y=1,family="crate",hp=3}},goals=new[]{new Goal{family="crate",count=1}},activeColors=new[]{0}};
                var board=new BoardModel(data);
                Require(board.LegalSwaps().Count==0,"Deadlock fixture should start without a legal swap.");
                board.InjectReviewPower(0,0,4);var turn=board.Tap(0,0);
                Require(turn.accepted&&board.Moves==9,"Rocket tap on the deadlock fixture was rejected or charged wrongly.");
                Require(board.Status=="No legal moves","Failed reshuffle must end the turn as No legal moves, got "+board.Status);
                Require(turn.steps.Last().kind=="settled"&&turn.steps.Last().label=="No legal moves","Settled step must carry the terminal status.");
                board.Validate();
                bool rejected=false;try{board.VerificationForceStatus("Out of moves");}catch(InvalidOperationException){rejected=true;}
                Require(rejected,"An ended board accepted a forced status.");
                var fresh=new BoardModel(data);rejected=false;try{fresh.VerificationForceStatus("Won");}catch(ArgumentException){rejected=true;}
                Require(rejected,"The verification seam accepted a non-terminal status.");
                fresh.VerificationForceStatus("Resolution limit");Require(fresh.Status=="Resolution limit","Forced guard status not applied.");
                // Checkpoint 60: a thrown player command ends the board as an engine fault, once.
                fresh=new BoardModel(data);fresh.RecordFault("swap: InvalidOperationException: test");
                Require(fresh.Status=="Engine fault"&&fresh.FaultDetail=="swap: InvalidOperationException: test","Engine fault was not recorded.");
                fresh.RecordFault("tap: later");Require(fresh.FaultDetail=="swap: InvalidOperationException: test","A later fault overwrote the first diagnosis.");
                Require(!fresh.Swap(0,0,1,0).accepted&&!fresh.Tap(0,0).accepted,"A faulted board accepted a command.");
                fresh=new BoardModel(data);fresh.VerificationForceStatus("Engine fault");Require(fresh.Status=="Engine fault","Forced engine fault status not applied.");
            });
            RunCase(report, "Reservation rules carry their own reasons and a loss keeps the current level", () =>
            {
                var s=new ProfileService(new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2})));
                Func<string> id=()=>Guid.NewGuid().ToString("N");
                Action<Action,string> expect=(action,message)=>{try{action();}catch(InvalidOperationException e){Require(e.Message==message,"Expected '"+message+"', got '"+e.Message+"'.");return;}throw new InvalidOperationException("Expected rejection: "+message);};
                string first=id();s.Reserve(first,1,"cfg",new int[4],50,1);
                expect(()=>s.Reserve(id(),1,"cfg",new int[4],50,1),ProfileService.AttemptInProgress);
                s.CommitStart(first);s.Win(first);Require(s.Read().completed==1&&s.Read().currentLevel==2,"First clear did not advance.");
                expect(()=>s.Reserve(id(),3,"cfg",new int[4],50,1),ProfileService.LevelLocked);
                s.Change(p=>{p.starting[3]=0;return true;});expect(()=>s.Reserve(id(),2,"cfg",new[]{0,0,0,1},50,1),ProfileService.BoosterUnavailable);
                expect(()=>s.Reserve(id(),2,"cfg",new[]{0,0,0,2},50,1),"Cannot reserve this attempt");
                string replay=id();s.Reserve(replay,1,"cfg",new int[4],50,1);s.CommitStart(replay);s.Lose(replay);
                Require(s.Read().currentLevel==2&&s.Read().completed==1&&s.Read().lives==4,"A lost replay moved the current level or miscounted the life.");
                s.Change(p=>{p.lives=0;return true;});expect(()=>s.Reserve(id(),2,"cfg",new int[4],50,1),ProfileService.NoLives);
                Require(ProfileService.IsReservationRule(ProfileService.NoLives)&&ProfileService.IsReservationRule(ProfileService.LevelLocked)&&!ProfileService.IsReservationRule("Cannot reserve this attempt")&&!ProfileService.IsReservationRule("Unknown attempt"),"Rule classification is wrong.");
                s.Read().Validate();
            });
            RunCase(report, "Native font height fitting and contained artwork centering", () =>
            {
                var assets=AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset");
                var node=new GameObject("UI regression",typeof(RectTransform));
                try
                {
                    var rect=(RectTransform)node.transform;rect.sizeDelta=new Vector2(250,22);rect.pivot=new Vector2(0,1);
                    var text=node.AddComponent<UnityEngine.UI.Text>();text.font=assets.boldFont;text.text="Уровень 1";text.fontSize=24;
                    text.verticalOverflow=VerticalWrapMode.Truncate;LabelFit.Apply(text,250,22);
                    var gen=new TextGenerator();gen.Populate(text.text,text.GetGenerationSettings(rect.rect.size));
                    Require(gen.vertexCount>0&&text.preferredHeight<=22,"Fitted native label is invisible.");
                    UnityEngine.Object.DestroyImmediate(text);
                    var image=node.AddComponent<UnityEngine.UI.Image>();image.sprite=assets.Find("R4_Start");image.preserveAspect=true;
                    var corners=new Vector3[4];rect.GetWorldCorners(corners);SpriteFit.Center(image);var after=new Vector3[4];rect.GetWorldCorners(after);
                    Require(rect.pivot==new Vector2(.5f,.5f)&&corners.SequenceEqual(after),"Centering changed the layout rectangle.");
                    var position=rect.anchoredPosition;SpriteFit.Center(image);Require(rect.anchoredPosition==position,"Centering is not idempotent.");
                }
                finally{UnityEngine.Object.DestroyImmediate(node);}
            });
            RunCase(report, "Five recorded campaign clears and 50 openings", () =>
            {
                var replay = Resources.Load<TextAsset>("HOTR_Playtests/Campaign_Replays");
                Require(replay != null, "Missing replay resource.");
                report.campaign = CampaignValidation.Run(levels.ToArray(), JsonUtility.FromJson<CampaignReplaySet>(replay.text));
                Require(report.campaign.errors.Count == 0, string.Join("; ", report.campaign.errors));
            });
            foreach (var level in levels)
            {
                var current = level;
                RunCase(report, current.id + " rejected actions preserve state and tools", () =>
                {
                    var board = new BoardModel(current);
                    var before = JsonUtility.ToJson(board.Snapshot());
                    Require(!board.Swap(-1, -1, -2, -2).accepted, "Invalid swap accepted.");
                    Require(!board.Tap(-1, -1).accepted, "Invalid tap accepted.");
                    var stock = new BoosterInventory();
                    foreach (BoosterKind kind in Enum.GetValues(typeof(BoosterKind)))
                    {
                        if (kind == BoosterKind.Atlas) continue;
                        Require(!board.UseBooster(kind, -1, -1, stock).accepted, "Invalid tool target accepted.");
                        Require(stock.Count(kind) == 3, "Invalid action spent tool.");
                    }
                    Require(JsonUtility.ToJson(board.Snapshot()) == before, "Rejected action changed board/moves/goals.");
                });
                RunCase(report, current.id + " same seed and action reproduce state", () =>
                {
                    var a = new BoardModel(current);
                    var b = new BoardModel(current);
                    var move = a.LegalSwaps().First();
                    int before = a.Moves;
                    Require(a.Swap(move[0].x, move[0].y, move[1].x, move[1].y).accepted, "Legal move rejected.");
                    Require(b.Swap(move[0].x, move[0].y, move[1].x, move[1].y).accepted, "Repeated move rejected.");
                    a.Validate(); b.Validate();
                    Require(a.Moves == before - 1, "Legal action must cost one move.");
                    Require(a.Status != "Resolution limit", "Resolution guard exhausted.");
                    Require(JsonUtility.ToJson(a.Snapshot()) == JsonUtility.ToJson(b.Snapshot()), "Replay state differs.");
                });
                foreach (int power in new[] { 4, 5, 7, 11, 16, 21 })
                {
                    int kind = power;
                    RunCase(report, current.id + " standalone power " + kind, () =>
                    {
                        var board = new BoardModel(current);
                        var gem = board.Pieces.Values.First(p => p.family == "gem");
                        Require(board.InjectReviewPower(gem.x, gem.y, kind), "Could not stage power.");
                        int before = board.Moves;
                        Require(board.Tap(gem.x, gem.y).accepted, "Power tap rejected.");
                        board.Validate();
                        Require(board.Moves == before - 1 && board.Status != "Resolution limit", "Power charge/guard failure.");
                    });
                }
            }
            RunCase(report, "Golden + Golden remains undefined", () => Require(BoardModel.Combo(16, 16) == -1, "Unsupported pair acquired a rule."));
            if (levels.Count > 0)
            {
                int[][] pairs = {
                    new[] {4,4},new[] {4,21},new[] {21,21},new[] {7,4},new[] {7,21},new[] {7,7},
                    new[] {11,4},new[] {11,21},new[] {11,11},new[] {7,11},new[] {16,4},new[] {16,21},new[] {16,11},new[] {7,16}
                };
                foreach (var pair in pairs)
                    foreach (bool vertical in new[] {false,true})
                        foreach (bool reverse in new[] {false,true})
                        {
                            int first = pair[0] == 4 && vertical ? 5 : pair[0];
                            int second = pair[1] == 4 && vertical ? 5 : pair[1];
                            RunCase(report, "Pair " + first + "+" + second + " vertical=" + vertical + " reverse=" + reverse, () =>
                            {
                                var board = new BoardModel(levels[0]);
                                var a = board.Pieces.Values.First(p => p.family == "gem" && board.At(p.x+(vertical?0:1),p.y+(vertical?1:0)) != null && board.At(p.x+(vertical?0:1),p.y+(vertical?1:0)).family == "gem");
                                var b = board.At(a.x+(vertical?0:1),a.y+(vertical?1:0));
                                Require(board.InjectReviewPower(a.x,a.y,first) && board.InjectReviewPower(b.x,b.y,second), "Could not stage pair.");
                                int before = board.Moves;
                                var turn = reverse ? board.Swap(b.x,b.y,a.x,a.y) : board.Swap(a.x,a.y,b.x,b.y);
                                Require(turn.accepted, "Approved pair rejected: " + turn.reason);
                                board.Validate();
                                Require(board.Moves == before-1 && board.Status != "Resolution limit", "Pair charge/guard failure.");
                            });
                        }
            }
            RunCase(report, "Starting inventory reservation rollback and duplicate commit", () =>
            {
                var session = new PreLevelSession(new[] { 5, 4, 3, 2 });
                session.Open(1, 5, new PreLevelGoal[0], 50, 1);
                Require(session.Toggle(0) && session.Toggle(1), "Cannot select separate Rocket/Bomb.");
                PreLevelTicket ticket, duplicate;
                Require(session.TryBegin(out ticket), "Reservation failed.");
                Require(!session.TryBegin(out duplicate), "Duplicate reservation accepted.");
                Require(session.Count(0) == 5 && session.Count(1) == 4, "Reservation debited stock.");
                Require(session.Fail(ticket, "test failure"), "Failed launch did not roll back.");
                Require(!session.Complete(ticket), "Failed ticket committed.");
                Require(session.Count(0) == 5 && session.Count(1) == 4, "Failure debited stock.");
                Require(session.TryBegin(out ticket) && session.Complete(ticket), "Successful launch failed.");
                Require(!session.Complete(ticket), "Duplicate launch committed.");
                Require(session.Count(0) == 4 && session.Count(1) == 3, "Launch debit differs.");
            });
            RunCase(report, "First-clear receipt rejects duplicate and replay grants in one session", () =>
            {
                var home = new HomeState { currentLevel = 1, completedLevelsInChapter = 0, coins = 0, stars = 0 };
                var session = new LevelCompleteSession();
                Require(session.Arm(1, 1), "Arm failed.");
                Require(!session.TrySettle(1, "Won", true, home, 50, 50, 1), "Busy board settled.");
                Require(session.TrySettle(1, "Won", false, home, 50, 50, 1), "Win settlement failed.");
                Require(!session.TrySettle(1, "Won", false, home, 50, 50, 1), "Duplicate win settled.");
                Require(home.coins == 50 && home.stars == 1 && home.currentLevel == 2, "First-clear grant differs.");
                Require(session.Close() && session.Arm(2, 1), "Replay arm failed.");
                Require(session.TrySettle(1, "Won", false, home, 50, 50, 1), "Replay settlement failed.");
                Require(!session.View.firstClear && home.coins == 50 && home.stars == 1, "Replay granted another reward.");
            });
            // Call only existing non-mutating validators. Historical M46 validation is
            // excluded because its eager texture bindings differ from the live M48 set.
            var validators = new[] {
                "HeartOfTheRain.M48.M48ReviewMenu",
                "HeartOfTheRain.App.Celebrations.Editor.CelebrationEditor",
                "HeartOfTheRain.App.FirstStart.Editor.FirstStartReview",
                "HeartOfTheRain.App.AppSettings.Editor.AppSettingsReview",
                "HeartOfTheRain.App.EndLevel.Editor.EndLevelReview",
                "HeartOfTheRain.App.Journey.Editor.JourneyReview",
                "HeartOfTheRain.App.Leaderboard.Editor.LeaderboardReview",
                "HeartOfTheRain.App.LevelComplete.Editor.LevelCompleteEditor",
                "HeartOfTheRain.App.PreLevel.Editor.PreLevelReview",
                "HeartOfTheRain.App.Retry.Editor.RetryReview",
                "HeartOfTheRain.App.Settings.Editor.GameplaySettingsMenu",
                "HeartOfTheRain.App.Shop.Editor.ShopReview",
                "HeartOfTheRain.App.Teams.Editor.TeamsReview"
            };
            foreach (var name in validators)
                RunCase(report, name + ".Validate", () =>
                {
                    var type = typeof(NativeVerification).Assembly.GetType(name, true);
                    var method = type.GetMethod(name.EndsWith(".PreLevelReview", StringComparison.Ordinal) ? "ValidateArt" : "Validate", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
                    Require(method != null, "Validator method not found.");
                    method.Invoke(null, null);
                });
            report.status = report.failed == 0 ? "PASS_NATIVE_EDITOR_CHECKS" : "FAIL_NATIVE_EDITOR_CHECKS";
            string path = Path.Combine(Path.GetFullPath(System.Environment.GetEnvironmentVariable("HOTR_REVIEW93_OUT")??"../Verification/Evidence/Native"),"Native_Checks.json");
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, JsonUtility.ToJson(report, true));
            Debug.Log(report.status + ": " + report.passed + " passed, " + report.failed + " failed; " + path);
            if (Application.isBatchMode) EditorApplication.Exit(report.failed == 0 ? 0 : 1);
        }

        public static int ObstacleTimingChecks99()
        {
            int checks=0;Action<bool,string> check=(ok,message)=>{checks++;Require(ok,message);};
            var clock=new ObstacleIntroductionClock();clock.Reset(100,true);
            clock.Sample(100.17,true);check(!clock.Finished&&clock.FullyVisibleSeconds==0&&clock.RevealProgress<1,"Reveal frames do not count as fully visible card time");
            clock.Sample(100.18,true);check(!clock.Finished&&Math.Abs(clock.FullyVisibleSeconds)<1e-8,"Fully visible dwell begins after the approved reveal");
            clock.Sample(101.6799,true);check(!clock.Finished&&clock.FullyVisibleSeconds<1.5,"No dismissal before1.5fully visible foreground seconds");
            clock.Sample(101.68,true);check(clock.Finished&&clock.FullyVisibleSeconds>=1.5,"Exact visible-time boundary dismisses");
            clock.Reset(0,true);clock.Sample(.68,true);check(Math.Abs(clock.FullyVisibleSeconds-.5)<1e-8,"Monotonic time is independent of scaled gameplay time");
            clock.Sample(.8,false);double paused=clock.FullyVisibleSeconds;clock.Sample(60,false);check(!clock.Finished&&Math.Abs(clock.FullyVisibleSeconds-paused)<1e-8,"Background time does not advance the presentation clock");
            clock.Sample(120,true);check(!clock.Finished&&Math.Abs(clock.FullyVisibleSeconds-paused)<1e-8,"Resume anchors do not count background catch-up");
            clock.Sample(120+(1.5-paused)-.0001,true);check(!clock.Finished,"Resume retains the precise remaining dwell");
            clock.Sample(120+(1.5-paused)+.0001,true);check(clock.Finished,"Foreground remainder completes after resume");
            clock.Reset(10,false);clock.Sample(999,false);check(!clock.Finished&&clock.ForegroundSeconds==0,"An initially backgrounded card stays unstarted");
            clock.Sample(1000,true);clock.Sample(1000.1,true);double before=clock.ForegroundSeconds;clock.Sample(999,true);check(clock.ForegroundSeconds==before,"Backward samples never move or duplicate the clock");
            clock.Sample(double.NaN,true);clock.Sample(double.PositiveInfinity,true);check(clock.ForegroundSeconds==before,"Invalid samples cannot dismiss the card");
            clock.Reset(0,true);check(clock.ForegroundSeconds==0&&!clock.Finished,"A new card obtains a fresh full dwell");
            return checks;
        }

        public static int RefillPresentationChecks98()
        {
            int checks=0;Action<bool,string> check=(ok,message)=>{checks++;Require(ok,message);};
            var session=new PreLevelSession(new[]{5,4,3,2});PreLevelRefillTicket first,second;
            session.Open(1,1,new PreLevelGoal[0],50,1);
            check(!session.TryBeginRefill(out first),"Refill presentation refuses a level with remaining lives");
            session.Open(1,0,new PreLevelGoal[0],50,1);session.RefreshLifeTimer(1800,true,900);
            check(session.TryBeginRefill(out first)&&first.View.busy,"One asynchronous refill owns and locks its exact view");
            check(!session.TryBeginRefill(out second),"A repeated callback cannot dispatch another refill while one is pending");
            check(!session.Close()&&!session.Toggle(0),"Pending refill blocks close and synthetic booster callbacks");
            PreLevelTicket ticket;check(!session.TryBegin(out ticket),"Pending refill blocks synthetic Play callbacks");
            session.RefreshLives(5);session.RefreshLifeTimer(-1,false,0);check(first.View.lives==0&&first.View.refillCoins==900,"Synthetic refresh cannot replace in-flight refill state");
            bool refused=false;try{session.Open(2,0,new PreLevelGoal[0],50,1);}catch(InvalidOperationException){refused=true;}
            check(refused&&ReferenceEquals(first.View,session.View),"An in-flight refill cannot replace its modal view");
            check(!session.CompleteRefill(new PreLevelRefillTicket())&&first.View.busy,"An unrelated callback cannot unlock the pending view");
            check(session.CompleteRefill(first)&&!first.View.busy,"Matching asynchronous completion unlocks exactly once");
            check(!session.CompleteRefill(first),"Duplicate asynchronous completion is ignored");
            check(session.TryBeginRefill(out second)&&ReferenceEquals(first.View,second.View),"Retry can reuse the same view with a fresh request identity");
            check(!session.CompleteRefill(first)&&second.View.busy,"A delayed old callback cannot unlock a retry on the same view");
            check(session.CompleteRefill(second),"Current retry completion releases its own request only");
            session.Open(2,0,new PreLevelGoal[0],50,1);check(session.TryBeginRefill(out second),"A later independent refill obtains a new view");
            check(!session.CompleteRefill(first)&&second.View.busy,"Late old completion cannot unlock the newer refill");
            check(session.CompleteRefill(second)&&session.Close(),"Current completion allows explicit close again");
            check(!session.CompleteRefill(second)&&!session.IsOpen,"Late completion after close cannot reopen the modal");
            check(session.Count(0)==5&&session.Count(1)==4,"Presentation callbacks never spend boosters or grant wallet/life rewards");
            return checks;
        }

        // Also callable by an isolated-engine fixture without weakening the
        // baseline suite's explicit pinned-Editor assertion.
        public static int PreLevelChecks98()
        {
            int checks=RefillPresentationChecks98();
            Action<bool,string> check=(condition,message)=>{checks++;Require(condition,message);};
            int original=HeartOfTheRain.App.Localization.GameLocale.Current;
            var assets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");
            var probe=new GameObject("Pre-level98 native font probe",typeof(RectTransform),typeof(UnityEngine.UI.Text));
            probe.hideFlags=HideFlags.HideAndDontSave;
            var text=probe.GetComponent<UnityEngine.UI.Text>();text.font=assets.home.boldFont;text.supportRichText=false;
            text.horizontalOverflow=HorizontalWrapMode.Overflow;text.verticalOverflow=VerticalWrapMode.Truncate;
            try
            {
                for(int locale=0;locale<5;locale++)
                {
                    HeartOfTheRain.App.Localization.GameLocale.Select(locale);
                    foreach(var size in new[]{new Vector2(320,568),new Vector2(393,852),new Vector2(430,932),new Vector2(768,1024),new Vector2(844,390)})
                        foreach(int state in new[]{0,1,2,3})
                        {
                            bool zero=state<2,affordable=state!=0;
                            var view=new PreLevelViewData{lives=zero?0:state==2?1:5,nextLifeSeconds=1799,canRefill=zero&&affordable,refillCoins=LifeRules.RefillCoins,retry=state==3};
                            var f=PreLevelLayout.Build(size.x,size.y,view);var panel=f.elements.First(e=>e.id=="panel");var play=f.elements.First(e=>e.id=="play");
                            check(panel.width<=556&&panel.height==(f.landscape?316:452),"Approved pre-level shell geometry retained "+size);
                            check(!f.elements.Any(e=>e.id.StartsWith("booster-",StringComparison.Ordinal)&&e.id.EndsWith("-name",StringComparison.Ordinal)),"Booster names are absent "+size);
                            for(int i=0;i<4;i++)
                            {
                                check(f.elements.Any(e=>e.id=="booster-"+i+"-count")&&f.elements.Any(e=>e.id=="booster-"+i&&e.action=="toggle:"+i&&!string.IsNullOrEmpty(e.label)),"Icons/counts and named selection touch target retained "+i);
                            }
                            if(zero)
                            {
                                var timer=f.elements.First(e=>e.id=="life-timer");var lastBooster=f.elements.First(e=>e.id=="booster-3");
                                check(play.action=="refill"&&f.elements.First(e=>e.id=="play-text").text.Contains("900")&&play.label.Contains("900"),"Zero lives always shows the900-coin refill, including899wallet "+size);
                                check(timer.y>=lastBooster.y+lastBooster.height+4&&timer.y+timer.height<=play.y-4,"Timer is separate from booster touch area and primary button "+size);
                                check(f.elements.Any(e=>e.id=="refill-unaffordable")==!affordable,"Unavailable wallet has an explicit reason while retaining price "+size);
                            }
                            else check(play.action=="play"&&!f.elements.Any(e=>e.id=="life-timer"||e.id=="refill-unaffordable"),"Existing lives retain ordinary Play/retry without refill copy "+size);
                            foreach(var e in f.elements.Where(e=>e.parent=="panel"))
                            {
                                check(e.x>=-.01f&&e.y>=-.01f&&e.x+e.width<=panel.width+.01f&&e.y+e.height<=panel.height+.01f,"Contained pre-level element "+e.id+" "+size);
                                if(e.kind!="text")continue;
                                text.text=e.text;text.fontSize=e.fontSize;text.rectTransform.sizeDelta=new Vector2(e.width,e.height);LabelFit.Apply(text,e.width,e.height);
                                check(text.preferredWidth<=e.width+.5f&&text.preferredHeight<=e.height+.5f,"Native localized font fits "+e.id+" locale"+locale+" "+size);
                                check(e.text.All(c=>char.IsWhiteSpace(c)||text.font.HasCharacter(c)),"Native font includes localized glyphs "+e.id+" locale"+locale);
                            }
                        }
                    if(locale==0)continue;
                    check(HeartOfTheRain.App.Localization.GameLocale.T("Refill 900")!="Refill 900","Translated refill pattern "+locale);
                    check(HeartOfTheRain.App.Localization.GameLocale.T("Next life in 29:59")!="Next life in 29:59","Translated next-life pattern "+locale);
                    check(HeartOfTheRain.App.Localization.GameLocale.T("Not enough coins")!="Not enough coins","Translated insufficient-wallet reason "+locale);
                }
            }
            finally{UnityEngine.Object.DestroyImmediate(probe);HeartOfTheRain.App.Localization.GameLocale.Select(original);}
            return checks;
        }

        static void RunCase(Report report, string name, Action check)
        {
            var result = new Check { name = name, status = "PASS", error = "" };
            try { check(); report.passed++; }
            catch (Exception ex)
            {
                result.status = "FAIL";
                result.error = (ex.InnerException ?? ex).ToString();
                report.failed++;
            }
            report.checks.Add(result);
        }
        static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
#endif
