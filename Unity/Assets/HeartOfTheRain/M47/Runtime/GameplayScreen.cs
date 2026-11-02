using System;
using System.Collections;
using HeartOfTheRain.M48;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.M46;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
using EnhancedTouch = UnityEngine.InputSystem.EnhancedTouch.Touch;
using EnhancedTouchSupport = UnityEngine.InputSystem.EnhancedTouch.EnhancedTouchSupport;
#endif
namespace HeartOfTheRain.M47 {
    [DisallowMultipleComponent]
    public sealed partial class GameplayScreen:MonoBehaviour {
        public GameplayUIAssets uiAssets;[Range(1,50)]public int initialLevel=1;public bool showLevelIntro=true;public bool boardRecoil=true;public float playbackSpeed=1;
        // Refill seed for the first load; 0 keeps the authored tileSeed (review
        // scenes, fixtures). The connected flow passes the attempt's seed.
        [NonSerialized] public uint initialSeed;
        // Exact authored configuration of a resumable pre-update attempt.
        // Its checkpoint and purchase receipt must retain this geometry.
        [NonSerialized] public LevelData RestoredLevelConfiguration;
        // While a launch or a paid tool's round trip is unresolved, Settings stays shut.
        [NonSerialized] public Func<bool> SettingsBlocked;
        // A server attempt can't release a fault only this device saw. Keep the player's board
        // by snapping to the model's settled state, once; a second fault ends as before.
        [NonSerialized] public bool RecoverFirstPresentationFault;bool presentationFaultRecovered;
        [NonSerialized] public HeartOfTheRain.App.Profile.LegacyLevelGraphics117 RestoredLevelGraphics;
        [NonSerialized] public int[] pendingStartingPowers;
        public string StartingPowerError {get;private set;}
        public bool InitializationComplete {get;private set;}
        public bool HasStartedWithPowers {get;private set;}
        readonly BoardGestureGate gestureGate=new BoardGestureGate();bool touchFrame;Vector2 pressScreenPoint;
        readonly BoardGestureBuffer pendingGesture=new BoardGestureBuffer();float inputStableAt;bool inputTail;
        bool preparing;Rect fittedSafe;int fittedWidth,fittedHeight;
        bool awaitingPlaybackPose,playbackPoseAnchor;double playbackPoseAt;
        M46Assets assets;GameplayHUD hud;GameplayFeedback feedback;SpriteRenderer backdrop;string uiHint="";bool resultShown;int previousMoves;
        BoosterInventory inventory=new BoosterInventory();int boosterSelection=-1,sampleKind;BoardModel board;BoardPresentation presentation;M46AtlasBank bank;Camera view;Transform root;Material bodyMaterial;EffectMeshBatcher effects;
        readonly List<SpriteRenderer> pool=new List<SpriteRenderer>();readonly List<BoardStep> queue=new List<BoardStep>();
        sealed class RenderState {public Transform node;public bool enabled;public Sprite sprite;public Texture2D texture;public Material material;public int order=int.MinValue;public SpriteMaskInteraction mask;public Vector3 position,scale;public Quaternion rotation;public float angle=float.NaN;public Color color;public float glow=float.NaN;}
        readonly List<RenderState> renderStates=new List<RenderState>();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        [NonSerialized] public bool VerificationSkipWarmup;
        [NonSerialized] public bool VerificationSkipFastCache;
        [NonSerialized] public bool VerificationSkipCratePreparation;
        [NonSerialized] public bool VerificationUseLegacyDensityWork;
        // Same-APK control: draw effects through one SpriteRenderer each, as before checkpoint 60.
        [NonSerialized] public bool VerificationUseSpriteRenderersForEffects;
        bool verificationUseCheckpoint77Submission;
        public bool VerificationUseCheckpoint77Submission {
            get=>verificationUseCheckpoint77Submission;
            set {verificationUseCheckpoint77Submission=value;if(effects!=null)effects.VerificationUseCheckpoint77Submission=value;}
        }
        // The next player command throws, as an engine bug would.
        [NonSerialized] public bool VerificationFaultOnNextInput;
        [NonSerialized] public LevelData VerificationLevelOverride;
        [NonSerialized] public int VerificationRendererCapacity;
        [NonSerialized] public bool MeasureFrameCosts;
        [NonSerialized] public bool MeasureDetailedDrawCosts=true;
        [Serializable] public struct FrameCost {public int frame,poolCreated,spriteCreated,draws,crateDraws,meshQuads,meshes,geometryMisses,meshSlotsCreated;public string kind;public float clock,age;public double updateMs,renderMs,sampleMs,bodySampleMs,effectsSampleMs,sortMs,lookupMs,batchAddMs,batchUploadMs,spriteUpdateMs,bankEndMs,updateStartedWall,renderStartedWall,renderFinishedWall,updateFinishedWall;
            // Outer Render spans are disjoint. Legacy sample/per-draw costs are
            // nested inside them and must never be summed into this total again.
            public double outerSetupMs,outerSampleMs,outerBeginMs,outerDrawMs,outerDisableMs,outerUploadMs,outerEndCollectionsMs,outerBankEndMs,outerSelectionMs,outerSpanMs,outerWrapperResidualMs;
            public int gcMaxGeneration,gc0BeforeUpdate,gc1BeforeUpdate,gc2BeforeUpdate,gc0BeforeRender,gc1BeforeRender,gc2BeforeRender,gc0AfterRender,gc1AfterRender,gc2AfterRender,gc0AfterUpdate,gc1AfterUpdate,gc2AfterUpdate;
        }
        public FrameCost LastFrameCost {get;private set;}
        [Serializable] public struct CommandCost {public int frame,phases;public double buildMs,resourcePlanMs,nextMs,dependenciesMs,prefetchMs,totalMs;}
        public CommandCost LastCommandCost {get;private set;}
        public float VerificationPlaybackAge=>clock-started;
        public string VerificationPlaybackKind=>current==null?"idle":current.kind;
        public float VerificationPlaybackClock=>clock;
        public bool VerificationPreparing=>preparing;
        double sampleMilliseconds,lookupMilliseconds,batchAddMilliseconds,batchUploadMilliseconds,spriteUpdateMilliseconds,bankEndMilliseconds;int renderedCrates;
        double outerSetupMilliseconds,outerSampleMilliseconds,outerBeginMilliseconds,outerDrawMilliseconds,outerDisableMilliseconds,outerUploadMilliseconds,outerEndCollectionsMilliseconds,outerBankEndMilliseconds,outerSelectionMilliseconds,outerSpanMilliseconds;
        struct CollectionCounts {public int maximum,g0,g1,g2;}
        static CollectionCounts ReadCollections(){int maximum=GC.MaxGeneration;return new CollectionCounts{maximum=maximum,g0=GC.CollectionCount(0),g1=maximum>=1?GC.CollectionCount(1):-1,g2=maximum>=2?GC.CollectionCount(2):-1};}
        static double CloseOuterSpan(ref long cursor){long end=Stamp();double elapsed=Milliseconds(end-cursor);cursor=end;return elapsed;}
        static long Stamp()=>System.Diagnostics.Stopwatch.GetTimestamp();
        static double Milliseconds(long ticks)=>ticks*1000.0/System.Diagnostics.Stopwatch.Frequency;
#endif
        bool EffectBatchingEnabled {get{
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            return !VerificationUseSpriteRenderersForEffects;
#else
            return true;
#endif
        }}
        bool PresentationWarmupEnabled {get{
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            return !VerificationSkipWarmup;
#else
            return true;
#endif
        }}
        public int RendererPoolCount=>pool.Count;
        // Named for the checkpoint-44 crate repair; it now gates the
        // preparation of every obstacle family present on the board.
        bool CratePreparationEnabled {get{
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            return !VerificationSkipCratePreparation;
#else
            return true;
#endif
        }}
        public static int WarmRendererCapacity(int columns,int rows)=>Math.Max(400,columns*rows*5);
        public static int WarmRendererCapacity(int columns,int rows,BoardSnapshot snapshot)=>WarmRendererCapacity(columns,rows,snapshot,null);
        public static int WarmRendererCapacity(int columns,int rows,BoardSnapshot snapshot,IDictionary<string,DebrisProfile> profiles){
            int target=WarmRendererCapacity(columns,rows);
            // Each surviving layer sheds its fragments plus one accent. Include
            // every layer: successive power waves can overlap before earlier
            // debris leaves the screen. Crates shed four chips per surviving
            // layer and eight on the final one; the other families list their
            // pieces per HP layer in the debris profile.
            foreach(var p in snapshot.pieces){
                if(p.family=="crate"){target+=4*(Math.Max(1,p.hp)+1)+Math.Max(1,p.hp);continue;}
                DebrisProfile profile;if(p.family=="gem"||p.family=="power"||profiles==null||!profiles.TryGetValue(p.family,out profile))continue;
                for(int layer=1;layer<=Math.Max(1,p.hp);layer++){int pieces=0;foreach(var piece in profile.pieces)if(piece.beforeHP==layer)pieces++;target+=pieces+1;}
            }
            return target;
        }
        // 48 native sprites per preparation frame keeps a four-family board
        // (about 1,860 authored frames) under 40 frames behind the launch wait.
        const int ObstacleWarmBatch=48;
        LevelData LevelDataForLoad(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationLevelOverride!=null)return VerificationLevelOverride;
#endif
            if(RestoredLevelConfiguration!=null&&RestoredLevelConfiguration.globalLevel==levelIndex+1)return RestoredLevelConfiguration;
            return JsonUtility.FromJson<LevelData>(assets.levels[levelIndex].text);
        }
        MaterialPropertyBlock lightBlock;
        void Awake(){lightBlock=new MaterialPropertyBlock();}
        SpriteRenderer selection;Texture2D selectionTexture;Sprite selectionSprite;BoardStep current;BoardSnapshot idle;float clock,started,playbackDebt;const float MaxPlaybackDebt=.25f;int levelIndex,queueIndex,inject=-1;Cell selected,pressed;bool pause;string message="Swap adjacent gems. Tap a selected power-up to activate it.";
        bool hintsEnabled=true,startingCreationPending;
        readonly HeartOfTheRain.App.Settings.IdleHintGate hintGate=new HeartOfTheRain.App.Settings.IdleHintGate();
        readonly SpriteRenderer[] hintSprites=new SpriteRenderer[2];Cell[] hintCells;
        public bool HintsEnabled {get{return hintsEnabled;}set{hintsEnabled=value;ResetHint();}}
        void ResetHint(){hintGate.Reset();hintCells=null;foreach(var sr in hintSprites)if(sr)sr.enabled=false;}
        void UpdateHint()
        {
            bool eligible=hintsEnabled&&CanAct&&selected==null&&pressed==null&&boosterSelection<0;
            if(!eligible){ResetHint();return;}
            if(hintGate.Tick(Time.unscaledDeltaTime,true))
            {
                var swaps=board.LegalSwaps();
                if(swaps.Count>0)hintCells=swaps[0];
                else {var p=board.Pieces.Values.FirstOrDefault(v=>v.family=="power");if(p!=null)hintCells=new[]{new Cell(p.x,p.y)};}
            }
            if(hintCells==null)return;
            for(int i=0;i<hintCells.Length;i++)
            {
                if(!hintSprites[i]){var sr=Make("Idle hint",14);sr.sprite=selectionSprite;sr.transform.localScale=Vector3.one*(.97f/selectionSprite.bounds.size.x);hintSprites[i]=sr;}
                hintSprites[i].enabled=true;hintSprites[i].transform.localPosition=Position(hintCells[i].x,hintCells[i].y);
                hintSprites[i].color=new Color(1,1,1,.55f+.3f*Mathf.Sin(Time.unscaledTime*4));
            }
        }
        public BoardModel Model=>board;public bool Busy=>current!=null||preparing||StartupPending79;
        public BoosterInventory SharedToolInventory {get;set;}
        public Func<BoosterKind,int,int,bool> CommitToolSpend {get;set;}
        // The spend went to the server and this tool retries when it confirms. That first
        // refusal is not a failure, so it shows no error text and plays no invalid sound.
        public bool ToolSpendDeferred {get;set;}
        public event Action<TurnResult> ModelTurnAccepted;
        public bool ReviewInputBlocked {get;set;}
        public bool ManualPlaytestProtected {get;set;}
        public uint CurrentSeed {get;private set;}
        public bool Ready=>board!=null&&hud!=null;
        public bool Paused=>pause;
        public bool CanAct=>InteractionGate.CanAct(Ready,Busy,pause,ReviewInputBlocked||(hud!=null&&hud.IsBlocking),board==null?"":board.Status);
        bool CanBuffer=>Ready&&Busy&&!StartupPending79&&current!=null&&(current.kind=="gravity"||current.kind=="powerFall"||current.kind=="settled")&&!preparing&&!pause&&!ReviewInputBlocked&&!hud.IsBlocking&&board.Status=="Playing"&&inputTail&&boosterSelection<0&&inject<0&&!pendingGesture.HasPending&&clock-started>=inputStableAt;
        public int CurrentLevel=>levelIndex+1;
        // Reuse the board bank and its lifetime: introductions show actual obstacles,
        // including unopened pods/cabinets, rather than their collected reward icons.
        public Sprite ObstacleIntroductionSprite(string key)=>bank==null?null:bank.Get(new DrawSprite{bank="body",key=key});
        public int ActiveSpriteCount {get;private set;}
        public int CachedSpriteCount=>bank==null?0:bank.SpriteCount;
        public int CachedTextureCount=>bank==null?0:bank.TextureCount;
        public long CachedTextureBytes=>bank==null?0:bank.TextureBytes;
        public int SynchronousTextureLoads=>bank==null?0:bank.SynchronousLoads;
        public int HistoryCount=>presentation==null?0:presentation.history.Count;
        public event Action<int> LevelLoaded;
        public event Action<string> LevelLeaving;
        public event Action<PlayerActionRecord> PlayerActionCompleted;
        public Func<bool> BeforePlayerCommand;
        public BoardCheckpoint pendingCheckpoint;
        public bool DeferTerminalPresentation;
        public event Action<BoardStep> StepStarted;
        public event Action<string> TurnSettled;
        void OnEnable(){
            SubscribeStartupCamera79();
#if ENABLE_INPUT_SYSTEM
            EnhancedTouchSupport.Enable();
#endif
            gestureGate.Interrupt();
        }
        void OnDisable(){UnsubscribeStartupCamera79();pendingGesture.Clear();CancelPointer();
#if ENABLE_INPUT_SYSTEM
            EnhancedTouchSupport.Disable();
#endif
        }
        void CancelPointer(){ResetHint();pressed=null;selected=null;boosterSelection=-1;gestureGate.Interrupt();}
        void OnApplicationFocus(bool focused){if(!focused){pendingGesture.Clear();CancelPointer();if(Ready&&!ReviewInputBlocked){if(!hud.IsBlocking)hud.ShowPause();else SetPause(true);}}}
        void Start(){Application.targetFrameRate=60;QualitySettings.vSyncCount=0;Screen.orientation=ScreenOrientation.Portrait;assets=uiAssets==null?null:uiAssets.boards;if(assets==null){Debug.LogError("Assign the supplied M46Assets.asset.");enabled=false;return;}bank=new M46AtlasBank(assets);var cameraObject=new GameObject("M46 Review Camera");cameraObject.transform.SetParent(transform,false);view=cameraObject.AddComponent<Camera>();view.orthographic=true;view.clearFlags=CameraClearFlags.SolidColor;view.backgroundColor=new Color(.055f,.09f,.14f);view.transform.localPosition=new Vector3(0,0,-10);bodyMaterial=new Material(uiAssets.bodyShader!=null?uiAssets.bodyShader:Shader.Find("Sprites/Default"));feedback=gameObject.AddComponent<GameplayFeedback>();feedback.assets=uiAssets;hud=gameObject.AddComponent<GameplayHUD>();hud.assets=uiAssets;hud.feedback=feedback;hud.BoosterPressed=SelectBooster;hud.PauseChanged=SetPause;hud.RetryPressed=()=>Load(levelIndex,0,"retry");hud.ContinuePressed=()=>Load(Mathf.Min(49,levelIndex+1),0,"continue");hud.Build();
            var bg=new GameObject("Courtyard background");bg.transform.SetParent(transform,false);backdrop=bg.AddComponent<SpriteRenderer>();backdrop.sprite=uiAssets.Get("Gameplay_Backdrop");backdrop.sortingOrder=-100;backdrop.sharedMaterial=bodyMaterial;
            var listener=cameraObject.AddComponent<AudioListener>();if(FindObjectsByType<AudioListener>(UnityEngine.FindObjectsSortMode.InstanceID).Length>1)listener.enabled=false;
            Load(initialLevel-1,initialSeed);}
        public void Load(int index,uint replaySeed=0,string reason="external"){
            LevelLeaving?.Invoke(reason);CancelStartup79(true);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            startupQueue79=Array.Empty<BoardStep>();startupResources79=null;
#endif
            pendingGesture.Clear();ResetHint();gestureGate.Interrupt();touchFrame=false;
            StopAllCoroutines();powerPreparationOwner=null;powerPreparationGeometry=null;queuePresentationPrefetches=0;preparing=false;if(root!=null)root.gameObject.SetActive(false);if(board!=null){bank.Dispose();bank=new M46AtlasBank(assets);}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            bank.VerificationSkipCachedLookup=VerificationSkipFastCache;
#endif
            feedback.ResetFeedback();hud.Close(false);resultShown=false;uiHint="";
            inventory=SharedToolInventory??new BoosterInventory();boosterSelection=-1;levelIndex=Mathf.Clamp(index,0,assets.levels.Length-1);queue.Clear();queueIndex=0;current=null;clock=0;started=0;playbackDebt=0;pause=false;inject=-1;selected=null;pressed=null;awaitingPlaybackPose=playbackPoseAnchor=false;
            ResetCommandPreparation();
            if(PresentationWarmupEnabled){
                for(int i=0;i<pool.Count;i++){var sr=pool[i];sr.enabled=false;sr.sprite=null;sr.SetPropertyBlock(null);sr.transform.SetParent(transform,false);
                    renderStates[i]=new RenderState{node=sr.transform,position=new Vector3(float.PositiveInfinity,0,0),rotation=new Quaternion(0,0,0,0),mask=(SpriteMaskInteraction)(-1)};}
            }else {pool.Clear();renderStates.Clear();}
            if(effects!=null){effects.Dispose();effects=null;}
            if(root!=null){root.gameObject.SetActive(false);Destroy(root.gameObject);}root=new GameObject("Live board").transform;root.SetParent(transform,false);
            foreach(var sr in pool)sr.transform.SetParent(root,false);
            board=pendingCheckpoint==null?new BoardModel(LevelDataForLoad(),replaySeed):BoardModel.FromCheckpoint(LevelDataForLoad(),pendingCheckpoint);pendingCheckpoint=null;StartingPowerError=null;HasStartedWithPowers=false;if(pendingStartingPowers!=null){string grantError;HasStartedWithPowers=board.TryPlaceStartingPowers(pendingStartingPowers,out grantError);if(!HasStartedWithPowers)StartingPowerError=grantError;pendingStartingPowers=null;}CurrentSeed=replaySeed==0?(uint)Math.Max(1,board.Level.tileSeed):replaySeed;idle=board.Snapshot();presentation=new BoardPresentation{columns=board.Level.columns,rows=board.Level.rows};startingCreationPending=HasStartedWithPowers&&idle.pieces.Any(p=>p.family=="power");foreach(var p in assets.debrisProfiles){var profile=JsonUtility.FromJson<DebrisProfile>(p.metadata.text);foreach(var piece in profile.pieces){if(piece.scaleMultiplier<=0)piece.scaleMultiplier=1;if(piece.spinMultiplier<=0)piece.spinMultiplier=1;}presentation.profiles.Add(p.family,profile);}
            presentation.PrepareDebrisGeometry();
            // Fragments fly past the mask and below the viewport; keep the batch bounds generous so nothing is culled mid-flight.
            effects=new EffectMeshBatcher(root,assets.effectsMaterial,new Bounds(Vector3.zero,new Vector3(board.Level.columns+16,board.Level.rows+20,2)));
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            effects.VerificationUseCheckpoint77Submission=verificationUseCheckpoint77Submission;
            presentation.VerificationUseLegacyDensityWork=VerificationUseLegacyDensityWork;presentation.MeasureSamplingCosts=MeasureFrameCosts;presentation.VerificationUseCheckpoint76Sampling=verificationUseCheckpoint76Sampling;
#endif
            var oldGraphics=RestoredLevelGraphics!=null&&RestoredLevelGraphics.level==levelIndex+1?RestoredLevelGraphics:null;
            var surface=Make("Approved R2 board",0);surface.sprite=oldGraphics==null?bank.BoardSurface(levelIndex):bank.BoardSurface(levelIndex,oldGraphics.surface,oldGraphics.width,oldGraphics.height);surface.sharedMaterial=bodyMaterial;
            var maskObject=new GameObject("Active-cell mask");maskObject.transform.SetParent(root,false);var mask=maskObject.AddComponent<SpriteMask>();mask.sprite=oldGraphics==null?bank.BoardMask(levelIndex):bank.BoardMask(levelIndex,oldGraphics.mask,oldGraphics.width,oldGraphics.height);mask.isCustomRangeActive=true;mask.frontSortingOrder=15;mask.backSortingOrder=5;
            foreach(var exit in board.Level.deliveryExits??new Cell[0]){var sr=Make("Jar exit",4);sr.sprite=bank.Whole("exit",assets.exitMarker,.78f,true);sr.transform.localPosition=Position(exit.x,exit.y-.39f);}
            selection=Make("Selected cell",14);selectionSprite=uiAssets.Get("Focus_Cell");selection.sprite=selectionSprite;selection.color=Color.white;selection.transform.localScale=Vector3.one*(.94f/selectionSprite.bounds.size.x);selection.enabled=false;
            InitializationComplete=false;previousMoves=board.Moves;fittedWidth=-1;Fit();Render();UpdateHUD();preparing=true;StartCoroutine(PrepareLevel());
        }
        IEnumerator PrepareLevel(){
            yield return bank.Prewarm(bank.CommonResources(idle));
            if(bank.LoadError==null&&startingCreationPending){var visual=new BoardStep{before=idle,after=idle};visual.created.AddRange(idle.pieces.Where(p=>p.family=="power"));yield return bank.Prewarm(bank.RequiredResources(new[]{visual}));}
            if(bank.LoadError!=null){StartingPowerError=bank.LoadError;uiHint="Unable to load effects. Restart this level.";InitializationComplete=true;hud.ShowPause();yield break;}
            if(PresentationWarmupEnabled){yield return bank.WarmCommonFrames();if(CratePreparationEnabled)yield return bank.WarmObstacleFrames(idle,ObstacleWarmBatch);yield return WarmRenderers();
                yield return effects.Prepare(bank.CachedEffectSpritesSnapshot(EffectMeshBatcher.PreparedGeometryLimit));}
            preparing=false;InitializationComplete=true;if(showLevelIntro)hud.ShowIntro(board.Level.globalLevel,idle.goals,board.Level.introductionTitle,board.Level.introductionInstruction);LevelLoaded?.Invoke(CurrentLevel);
        }
        IEnumerator WarmRenderers(){
            int target=CratePreparationEnabled?WarmRendererCapacity(board.Level.columns,board.Level.rows,idle,presentation.profiles):WarmRendererCapacity(board.Level.columns,board.Level.rows),batch=0;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            target=Math.Max(target,VerificationRendererCapacity);
#endif
            while(pool.Count<target){var sr=Make("Sampled sprite",10);sr.enabled=false;pool.Add(sr);renderStates.Add(new RenderState{node=sr.transform});if(++batch==16){if(CratePreparationEnabled)presentation.ReserveDrawCapacity(pool.Count);batch=0;yield return null;}}
            if(CratePreparationEnabled)presentation.ReserveDrawCapacity(pool.Count);
        }
        Vector3 Position(float x,float y){return new Vector3(x-(board.Level.columns-1)*.5f,y-(board.Level.rows-1)*.5f,0);}
        SpriteRenderer Make(string label,int order){var go=new GameObject(label);go.transform.SetParent(root,false);var sr=go.AddComponent<SpriteRenderer>();sr.sharedMaterial=assets.effectsMaterial;sr.sortingOrder=order;return sr;}
        void Fit(){var safe=Screen.safeArea;if(safe.width<=0||safe.height<=0)safe=new Rect(0,0,Screen.width,Screen.height);if(safe==fittedSafe&&Screen.width==fittedWidth&&Screen.height==fittedHeight)return;fittedSafe=safe;fittedWidth=Screen.width;fittedHeight=Screen.height;var layout=ReviewLayout.Compute(safe.width,safe.height,board.Level.columns,board.Level.rows);float h=layout.height,cell=layout.cell;float safeHalfHeight=h/(2*cell),aspect=safe.width/safe.height;
            // Clear and paint the whole display without moving the board or its input coordinates.
            var full=FullDisplayBoardView.Compute(Screen.width,Screen.height,safe,safeHalfHeight,20/cell);
            view.rect=new Rect(0,0,1,1);view.orthographicSize=full.halfHeight;view.transform.localPosition=new Vector3(full.center.x,full.center.y,-10);
            // Off-board effects keep their approved safe-area exit bounds.
            presentation.bottom=(board.Level.rows-1)*.5f+20/cell-safeHalfHeight;presentation.left=(board.Level.columns-1)*.5f-safeHalfHeight*aspect;presentation.right=(board.Level.columns-1)*.5f+safeHalfHeight*aspect;
            if(backdrop!=null){backdrop.transform.localPosition=new Vector3(full.center.x,full.center.y,1);backdrop.transform.localScale=new Vector3(2*full.halfHeight*Screen.width/Screen.height/backdrop.sprite.bounds.size.x,2*full.halfHeight/backdrop.sprite.bounds.size.y,1);}}
        void Enqueue(IEnumerable<BoardStep> steps){
            if(TryEnqueueStartup79(ref steps))return;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            long commandStamp=MeasureFrameCosts?Stamp():0;
#endif
            queue.AddRange(BoardPlayback.Build(steps,board.Level));
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            double buildMs=MeasureFrameCosts?Milliseconds(Stamp()-commandStamp):0;long resourcePlanStamp=MeasureFrameCosts?Stamp():0;
#endif
            PrepareCommandResources();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            startupQueue79=queue.ToArray();startupResources79=commandResourcePlan;
            double resourcePlanMs=MeasureFrameCosts?Milliseconds(Stamp()-resourcePlanStamp):0;long nextStamp=MeasureFrameCosts?Stamp():0;
#endif
            awaitingPlaybackPose=queue.Count>queueIndex;playbackPoseAnchor=false;selected=null;pressed=null;Next();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            double nextMs=MeasureFrameCosts?Milliseconds(Stamp()-nextStamp):0;long dependencyStamp=MeasureFrameCosts?Stamp():0;
#endif
            var resources=WholeQueueResources();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            double dependenciesMs=MeasureFrameCosts?Milliseconds(Stamp()-dependencyStamp):0;long prefetchStamp=MeasureFrameCosts?Stamp():0;
#endif
            StartCoroutine(PrefetchQueuePresentation(resources));
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)LastCommandCost=new CommandCost{frame=Time.frameCount,phases=queue.Count,buildMs=buildMs,resourcePlanMs=resourcePlanMs,nextMs=nextMs,dependenciesMs=dependenciesMs,prefetchMs=Milliseconds(Stamp()-prefetchStamp),totalMs=Milliseconds(Stamp()-commandStamp)};
#endif
        }
        IEnumerator PrepareQueue(){
            var owner=board;var resources=bank;preparing=true;uiHint="";
            yield return resources.Prewarm(CurrentPhaseResources());
            // A late resource completion belongs only to the board/bank that requested it.
            if(owner!=board||resources!=bank)yield break;
            // Release a failed presentation through the existing fault path. A pause dialog
            // alone leaves preparing set forever and makes an engine resource fault cost a life.
            if(resources.LoadError!=null){FailStartup79(new InvalidOperationException(resources.LoadError),owner);yield break;}
            preparing=false;if(current==null)Next();
        }
        void Next(){var completed=current;if(current!=null)idle=current.after;if(queueIndex>=queue.Count){if(HoldStartupTail79())return;current=null;idle=board.Snapshot();queue.Clear();queueIndex=0;ClearCommandResources();if(completed==null||completed.kind!="reject")TurnSettled?.Invoke(board.Status);message=board.Status=="Playing"?"Ready · "+board.Moves+" moves remaining":board.Status;return;}if(!bank.Ready(CurrentPhaseResources())){current=null;if(!preparing)StartCoroutine(PrepareQueue());return;}current=queue[queueIndex++];inputStableAt=BoardPlayback.InputStableAt(current);inputTail=true;for(int i=queueIndex;i<queue.Count;i++)if(queue[i].kind!="settled"){inputTail=false;break;}started=clock;presentation.Add(current,started);message=current.label;feedback.Begin(current);feedback.Sample(0);StepStarted?.Invoke(current);}
        void Accept(TurnResult result){var owner=board;if(!result.accepted){uiHint=result.reason;feedback.Play("ui_invalid",.65f);return;}ModelTurnAccepted?.Invoke(result);if(owner!=board)return;uiHint="";Enqueue(result.steps);}
        void AcceptPlayer(TurnResult result,string kind,int x,int y,int toX=-1,int toY=-1,int booster=-1){
            var owner=board;PlayerActionCompleted?.Invoke(new PlayerActionRecord{kind=kind,x=x,y=y,toX=toX,toY=toY,booster=booster,accepted=result.accepted,reason=result.reason});
            if(owner==board)Accept(result);
        }
        // Every player command runs through one guard: an exception is an engine
        // fault, diagnosed here and settled by the flow without a life charge
        // instead of leaving a half-mutated board accepting input.
        TurnResult Command(Func<TurnResult> run){
            if(BeforePlayerCommand!=null&&!BeforePlayerCommand())return new TurnResult{reason="Save unavailable"};
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationFaultOnNextInput){VerificationFaultOnNextInput=false;throw new InvalidOperationException("Verification engine fault");}
#endif
            return run();
        }
        void Fault(Exception e,string kind){
            Debug.LogException(e,this);board.RecordFault(kind+": "+e.GetType().Name+": "+e.Message);
            uiHint="";selected=pressed=null;boosterSelection=-1;pendingGesture.Clear();feedback.Play("ui_invalid",.65f);
        }
        void PlayerSwap(int x,int y,int targetX,int targetY){
            if(Busy){if(CanBuffer&&pendingGesture.Capture(board,x,y,targetX,targetY)){selected=pressed=null;gestureGate.Interrupt();feedback.Play("ui_select",.45f);}return;}
            var commandOwner=board;TurnResult result;try{result=Command(()=>board.Swap(x,y,targetX,targetY));}catch(Exception e){Fault(e,"swap");return;}
            AcceptPlayer(result,"swap",x,y,targetX,targetY);
            if(commandOwner!=board)return;
            if(!result.accepted&&result.reason=="No match"){
                var a=board.At(x,y);var b=board.At(targetX,targetY);var snapshot=board.Snapshot();var reject=new BoardStep{kind="reject",label="Invalid swap",duration=.22f,before=snapshot,after=snapshot};
                reject.motion.Add(new HeartOfTheRain.M46.Motion{id=a.id,fromX=x,fromY=y,toX=targetX,toY=targetY});reject.motion.Add(new HeartOfTheRain.M46.Motion{id=b.id,fromX=targetX,fromY=targetY,toX=x,toY=y});Enqueue(new[]{reject});
            }
        }
        void PlayerTap(int x,int y){if(Busy){if(CanBuffer&&pendingGesture.Capture(board,x,y)){selected=pressed=null;gestureGate.Interrupt();feedback.Play("ui_select",.45f);}return;}
            TurnResult result;try{result=Command(()=>board.Tap(x,y));}catch(Exception e){Fault(e,"tap");return;}AcceptPlayer(result,"tap",x,y);}
        void ConsumeBufferedGesture(){
            if(!pendingGesture.HasPending)return;if(pause||ReviewInputBlocked||hud.IsBlocking||board.Status!="Playing"){pendingGesture.Clear();return;}
            Cell from,to;if(CanAct&&pendingGesture.Take(board,out from,out to)){gestureGate.Interrupt();if(to==null)PlayerTap(from.x,from.y);else PlayerSwap(from.x,from.y,to.x,to.y);}
        }
        public void SelectBooster(int kind){if(!CanAct||kind<0||kind>3||inventory.Count((BoosterKind)kind)<=0)return;
            feedback.Play("ui_select",.65f,"select");if(kind==3){boosterSelection=-1;UseBooster(BoosterKind.Atlas,0,0);return;}
            boosterSelection=boosterSelection==kind?-1:kind;selected=null;uiHint=boosterSelection<0?"":new[]{"Hammer: choose a tile","Axe: choose a column","Ram: choose a row"}[kind];}
        public void UseBooster(BoosterKind kind,int x,int y){if(!CanAct)return;
            TurnResult result;try{result=Command(()=>board.UseBooster(kind,x,y,inventory,CommitToolSpend==null?(Func<bool>)null:()=>CommitToolSpend(kind,x,y)));}catch(Exception e){Fault(e,"booster");return;}
            if(ToolSpendDeferred){ToolSpendDeferred=false;if(!result.accepted)return;}
            AcceptPlayer(result,"booster",x,y,booster:(int)kind);}
        public void SetPause(bool value){pause=value;if(value){pendingGesture.Clear();CancelPointer();}else pressed=null;if(feedback!=null)feedback.Pause(value);}
        public void ResumeReview(){if(hud!=null)hud.Close(true);}
        // Same guard as focus loss: while the flow still blocks input (launch
        // window, settlement, celebration) no dialog may open.
        void OnApplicationPause(bool suspended){if(suspended&&Ready&&!ReviewInputBlocked){pressed=null;if(!hud.IsBlocking)hud.ShowPause();else SetPause(true);}}
        void UpdateHUD(){var visible=presentation.DisplayGoalsLive(current,idle,clock-started,clock);int shownMoves=current!=null?current.after.moves:idle.moves;hud.UpdateState(board.Level.globalLevel,shownMoves,visible,inventory,boosterSelection,Busy,uiHint);
            if(shownMoves==5&&previousMoves>5)feedback.Play("moves_low",.7f);previousMoves=shownMoves;
            if(!Busy&&!resultShown&&!DeferTerminalPresentation&&board.Status!="Playing"&&!presentation.GoalFlightsPending(clock)){resultShown=true;hud.ShowResult(board.Status=="Won",board.Level.globalLevel,board.Status);}}
        // Commands can spend a whole frame solving/preparing before Render
        // exposes their first pose. That work belongs to input latency, not
        // visible playback. Discount it once; ongoing phase clocks stay intact.
        float PlaybackOnsetAdvance(float advance,double now,float scale){
            if(awaitingPlaybackPose)return 0;
            if(!playbackPoseAnchor)return advance;
            playbackPoseAnchor=false;return Mathf.Min(advance,(float)Math.Max(0,now-playbackPoseAt)*Mathf.Max(0,scale));
        }
        void AdvancePlayback(float advance){
            advance=PlaybackOnsetAdvance(advance,Time.realtimeSinceStartupAsDouble,Time.timeScale*playbackSpeed);
            // Pose protection may shorten a stalled frame, but effects share this
            // clock: repay that time gradually so debris never runs slow afterwards.
            float repaid=Mathf.Min(playbackDebt,advance*.5f);playbackDebt-=repaid;advance+=repaid;
            while(current!=null&&advance>0){float allowed=BoardPlayback.VisibleAdvance(current,advance,clock-started);playbackDebt=Mathf.Min(MaxPlaybackDebt,playbackDebt+advance-allowed);advance=allowed;float remaining=current.duration-(clock-started);if(advance<remaining){clock+=advance;feedback.Sample(clock-started);advance=0;}else{clock+=remaining;feedback.Sample(current.duration);advance-=remaining;Next();}}
            // A tail still preparing on its worker holds the board pose only. Next
            // anchors that tail to this clock, so flying debris can keep moving.
            if(current==null)clock+=advance;
        }
        void Update(){if(board==null)return;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            var gcBeforeUpdate=MeasureFrameCosts?ReadCollections():default(CollectionCounts);
            long frameStamp=MeasureFrameCosts?Stamp():0;double updateWall=MeasureFrameCosts?Time.realtimeSinceStartupAsDouble:0;int poolBefore=pool.Count,createdBefore=bank.SpriteCreates;
#endif
            PollStartup79();Fit();if(!pause&&preparing)clock+=Time.deltaTime*playbackSpeed;if(!pause&&!preparing)AdvancePlayback(Time.deltaTime*playbackSpeed);
            // A finished board's result dialog pauses input and audio. The last hit's
            // debris has no model effect, so let it land behind the dialog.
            if(pause&&!preparing&&current==null&&!StartupPending79&&board.Status!="Playing")clock+=Time.deltaTime*playbackSpeed;
            if(startingCreationPending&&CanAct){foreach(var piece in idle.pieces)if(piece.family=="power")presentation.RegisterPowerCreation(piece,clock);startingCreationPending=false;}
            ConsumeBufferedGesture();ReadPointer();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            var gcBeforeRender=MeasureFrameCosts?ReadCollections():default(CollectionCounts);
            long renderStamp=MeasureFrameCosts?Stamp():0;double renderWall=MeasureFrameCosts?Time.realtimeSinceStartupAsDouble:0;
#endif
            Render();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            double renderMs=MeasureFrameCosts?Milliseconds(Stamp()-renderStamp):0;double renderDone=MeasureFrameCosts?Time.realtimeSinceStartupAsDouble:0;
            var gcAfterRender=MeasureFrameCosts?ReadCollections():default(CollectionCounts);
#endif
            UpdateHUD();UpdateHint();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts){var gcAfterUpdate=ReadCollections();LastFrameCost=new FrameCost{frame=Time.frameCount,kind=VerificationPlaybackKind,clock=clock,age=VerificationPlaybackAge,updateStartedWall=updateWall,renderStartedWall=renderWall,renderFinishedWall=renderDone,updateFinishedWall=Time.realtimeSinceStartupAsDouble,poolCreated=pool.Count-poolBefore,spriteCreated=bank.SpriteCreates-createdBefore,draws=ActiveSpriteCount,crateDraws=renderedCrates,meshQuads=effects==null?0:effects.Quads,meshes=effects==null?0:effects.Meshes,geometryMisses=effects==null?0:effects.GeometryMisses,meshSlotsCreated=effects==null?0:effects.SlotCreates,renderMs=renderMs,sampleMs=sampleMilliseconds,bodySampleMs=presentation.LastSamplingCosts.bodiesMs,effectsSampleMs=presentation.LastSamplingCosts.effectsMs,sortMs=presentation.LastSamplingCosts.sortMs,lookupMs=lookupMilliseconds,batchAddMs=batchAddMilliseconds,batchUploadMs=batchUploadMilliseconds,spriteUpdateMs=spriteUpdateMilliseconds,bankEndMs=bankEndMilliseconds,updateMs=Milliseconds(Stamp()-frameStamp),outerSetupMs=outerSetupMilliseconds,outerSampleMs=outerSampleMilliseconds,outerBeginMs=outerBeginMilliseconds,outerDrawMs=outerDrawMilliseconds,outerDisableMs=outerDisableMilliseconds,outerUploadMs=outerUploadMilliseconds,outerEndCollectionsMs=outerEndCollectionsMilliseconds,outerBankEndMs=outerBankEndMilliseconds,outerSelectionMs=outerSelectionMilliseconds,outerSpanMs=outerSpanMilliseconds,outerWrapperResidualMs=renderMs-outerSpanMilliseconds,
                gcMaxGeneration=gcBeforeUpdate.maximum,gc0BeforeUpdate=gcBeforeUpdate.g0,gc1BeforeUpdate=gcBeforeUpdate.g1,gc2BeforeUpdate=gcBeforeUpdate.g2,gc0BeforeRender=gcBeforeRender.g0,gc1BeforeRender=gcBeforeRender.g1,gc2BeforeRender=gcBeforeRender.g2,gc0AfterRender=gcAfterRender.g0,gc1AfterRender=gcAfterRender.g1,gc2AfterRender=gcAfterRender.g2,gc0AfterUpdate=gcAfterUpdate.g0,gc1AfterUpdate=gcAfterUpdate.g1,gc2AfterUpdate=gcAfterUpdate.g2};}
#endif
        }
        void Render(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            long outerStart=MeasureFrameCosts?Stamp():0,outerCursor=outerStart;
            presentation.VerificationUseLegacyDensityWork=VerificationUseLegacyDensityWork;presentation.MeasureSamplingCosts=MeasureFrameCosts;renderedCrates=0;
            bool detailedDrawCosts=MeasureFrameCosts&&MeasureDetailedDrawCosts;
            lookupMilliseconds=batchAddMilliseconds=batchUploadMilliseconds=spriteUpdateMilliseconds=bankEndMilliseconds=0;
#endif
            hud.BeginCollections();foreach(var goal in board.Goals.Keys){Vector2 point;if(hud.TryGoalScreenPoint(goal,out point)){var w=view.ScreenToWorldPoint(new Vector3(point.x,point.y,10));w=root.InverseTransformPoint(w);presentation.goalTargets[goal]=new Vector2(w.x+(board.Level.columns-1)*.5f,w.y+(board.Level.rows-1)*.5f);}}
            bank.BeginFrame();presentation.PruneHistory(clock);var kick=BoosterTimeline.BoardKick(presentation.history,clock,boardRecoil?1:0);root.localPosition=new Vector3(kick.x,kick.y,0);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)outerSetupMilliseconds=CloseOuterSpan(ref outerCursor);
            long sampleStamp=MeasureFrameCosts?Stamp():0;
#endif
            var draws=presentation.SampleLive(current,idle,clock,started);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)outerSampleMilliseconds=CloseOuterSpan(ref outerCursor);
#endif
            int count=0,overlays=0;bool batchEffects=EffectBatchingEnabled&&effects!=null;if(effects!=null)effects.Begin();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)sampleMilliseconds=Milliseconds(Stamp()-sampleStamp);
#endif
            bool cacheRotation=true;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            cacheRotation=!VerificationUseLegacyDensityWork;
            if(MeasureFrameCosts)outerBeginMilliseconds=CloseOuterSpan(ref outerCursor);
#endif
            foreach(var d in draws){
                if(startingCreationPending&&d.bank=="power"&&d.order==10)continue;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                long lookupStamp=detailedDrawCosts?Stamp():0;
#endif
                var sprite=bank.Get(d);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(detailedDrawCosts)lookupMilliseconds+=Milliseconds(Stamp()-lookupStamp);
#endif
                if(sprite==null||d.alpha<=0)continue;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(MeasureFrameCosts&&d.bank=="obstacle"&&d.key.StartsWith("crate/",StringComparison.Ordinal))renderedCrates++;
#endif
                if(d.uiOverlay){var point=view.WorldToScreenPoint(root.TransformPoint(Position(d.x,d.y)));float pixels=view.pixelHeight/(2*view.orthographicSize);hud.DrawCollection(sprite,new Vector2(point.x,point.y),new Vector2(sprite.bounds.size.x*d.sx*pixels,sprite.bounds.size.y*d.sy*pixels),d.angle,new Color(d.red,d.green,d.blue,d.alpha));overlays++;continue;}
                // Masked bodies keep their SpriteRenderer (sprite mask interaction) and glowing
                // tiles keep theirs (per-renderer property block); every other effect is batched.
                if(batchEffects&&!d.masked&&d.glow<=0){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    long batchStamp=detailedDrawCosts?Stamp():0;
#endif
                    effects.Add(sprite,d.order,Position(d.x,d.y),d.angle,d.sx,d.sy,new Color(d.red,d.green,d.blue,d.alpha));
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    if(detailedDrawCosts)batchAddMilliseconds+=Milliseconds(Stamp()-batchStamp);
#endif
                    continue;
                }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                long spriteStamp=detailedDrawCosts?Stamp():0;
#endif
                if(count>=pool.Count){var added=Make("Sampled sprite",d.order);pool.Add(added);renderStates.Add(new RenderState{node=added.transform});}
                var sr=pool[count];var previous=renderStates[count++];
                if(!previous.enabled){sr.enabled=true;previous.enabled=true;}
                bool spriteChanged=previous.sprite!=sprite;if(spriteChanged){sr.sprite=sprite;previous.sprite=sprite;}
                if(previous.order!=d.order){sr.sortingOrder=d.order;previous.order=d.order;}
                var material=d.glow>0?assets.tileGlowMaterial:d.masked?bodyMaterial:assets.effectsMaterial;
                if(previous.material!=material){sr.sharedMaterial=material;previous.material=material;}
                var mask=d.masked?SpriteMaskInteraction.VisibleInsideMask:SpriteMaskInteraction.None;
                if(previous.mask!=mask){sr.maskInteraction=mask;previous.mask=mask;}
                var position=Position(d.x,d.y);bool moved=previous.position!=position;
                var rotation=previous.rotation;bool turned=false;
                // Sprite-sheet fragments usually keep one angle. Avoid a native
                // Euler conversion for every fragment when that angle is unchanged.
                if(!cacheRotation||previous.angle!=d.angle){rotation=Quaternion.Euler(0,0,d.angle);turned=previous.rotation!=rotation;previous.angle=d.angle;}
                if(cacheRotation&&moved&&turned)previous.node.SetLocalPositionAndRotation(position,rotation);
                else {if(moved)previous.node.localPosition=position;if(turned)previous.node.localRotation=rotation;}
                if(moved)previous.position=position;if(turned)previous.rotation=rotation;
                var scale=new Vector3(d.sx,d.sy,1);if(previous.scale!=scale){previous.node.localScale=scale;previous.scale=scale;}
                var color=new Color(d.red,d.green,d.blue,d.alpha);if(previous.color!=color){sr.color=color;previous.color=color;}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(VerificationUseLegacyDensityWork){
                    if(d.glow>0){if(previous.texture!=sprite.texture||previous.glow!=d.glow){sr.GetPropertyBlock(lightBlock);lightBlock.SetTexture("_MainTex",sprite.texture);lightBlock.SetFloat("_Glow",d.glow);sr.SetPropertyBlock(lightBlock);}}
                    else if(previous.glow>0)sr.SetPropertyBlock(null);previous.texture=sprite.texture;
                }else
#endif
                if(d.glow>0){var texture=spriteChanged||previous.glow<=0?sprite.texture:previous.texture;if(previous.texture!=texture||previous.glow!=d.glow||previous.glow<=0){sr.GetPropertyBlock(lightBlock);lightBlock.SetTexture("_MainTex",texture);lightBlock.SetFloat("_Glow",d.glow);sr.SetPropertyBlock(lightBlock);}previous.texture=texture;}
                else if(previous.glow>0){sr.SetPropertyBlock(null);previous.texture=null;}
                previous.glow=d.glow;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(detailedDrawCosts)spriteUpdateMilliseconds+=Milliseconds(Stamp()-spriteStamp);
#endif
            }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)outerDrawMilliseconds=CloseOuterSpan(ref outerCursor);
#endif
            for(int i=count;i<pool.Count;i++)if(renderStates[i].enabled){pool[i].enabled=false;pool[i].sprite=null;renderStates[i].enabled=false;renderStates[i].sprite=null;renderStates[i].texture=null;}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)outerDisableMilliseconds=CloseOuterSpan(ref outerCursor);
            long uploadStamp=MeasureFrameCosts?Stamp():0;
#endif
            int batched=0;if(effects!=null){effects.End();batched=effects.Quads;}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)batchUploadMilliseconds=Milliseconds(Stamp()-uploadStamp);
            if(MeasureFrameCosts)outerUploadMilliseconds=CloseOuterSpan(ref outerCursor);
#endif
            hud.EndCollections();ActiveSpriteCount=count+overlays+batched;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)outerEndCollectionsMilliseconds=CloseOuterSpan(ref outerCursor);
            long bankEndStamp=MeasureFrameCosts?Stamp():0;
#endif
            bank.EndFrame(!Busy);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts)bankEndMilliseconds=Milliseconds(Stamp()-bankEndStamp);
            if(MeasureFrameCosts)outerBankEndMilliseconds=CloseOuterSpan(ref outerCursor);
#endif
            StartupPoseSubmitted79();
            selection.enabled=pendingGesture.HasPending||selected!=null&&!Busy;if(selection.enabled)selection.transform.localPosition=pendingGesture.HasPending?Position(pendingGesture.FromX,pendingGesture.FromY):Position(selected.x,selected.y);
            if(awaitingPlaybackPose&&current!=null){awaitingPlaybackPose=false;playbackPoseAnchor=true;playbackPoseAt=Time.realtimeSinceStartupAsDouble;}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureFrameCosts){outerSelectionMilliseconds=CloseOuterSpan(ref outerCursor);outerSpanMilliseconds=Milliseconds(outerCursor-outerStart);}
#endif
        }
        Cell ScreenCell(Vector2 screen){var w=view.ScreenToWorldPoint(new Vector3(screen.x,screen.y,10));w=root.InverseTransformPoint(w);int x=Mathf.RoundToInt(w.x+(board.Level.columns-1)*.5f),y=Mathf.RoundToInt(w.y+(board.Level.rows-1)*.5f);return board.Inside(x,y)?new Cell(x,y):null;}
        bool OverControls(Vector2 p){var safe=Screen.safeArea;float s=safe.width/720;return p.y>safe.yMax-240*s||p.y<safe.y+200*s||!safe.Contains(p)||hud.IsBlocking;}
        void ReadPointer(){
            if(!CanAct&&!CanBuffer){CancelPointer();return;}
            int contacts=0,id=-1;bool isTouch=false,endedAlso=false;GesturePhase phase=GesturePhase.None;Vector2 position=default(Vector2);
#if ENABLE_INPUT_SYSTEM
            // EnhancedTouch retains transitions that low-level Touchscreen polling can miss.
            var touches=EnhancedTouch.activeTouches;
            if(touches.Count>0){
                contacts=touches.Count;isTouch=true;var contact=touches[0];id=contact.touchId;position=contact.screenPosition;
                var state=contact.phase;
                phase=state==UnityEngine.InputSystem.TouchPhase.Began?GesturePhase.Began:state==UnityEngine.InputSystem.TouchPhase.Ended?GesturePhase.Ended:state==UnityEngine.InputSystem.TouchPhase.Canceled?GesturePhase.Canceled:GesturePhase.Held;
            }else if(!touchFrame&&Mouse.current!=null){
                var button=Mouse.current.leftButton;endedAlso=button.wasPressedThisFrame&&button.wasReleasedThisFrame;position=Mouse.current.position.ReadValue();
                contacts=button.isPressed||button.wasPressedThisFrame||button.wasReleasedThisFrame?1:0;
                phase=button.wasPressedThisFrame?GesturePhase.Began:button.wasReleasedThisFrame?GesturePhase.Ended:button.isPressed?GesturePhase.Held:GesturePhase.None;
            }
#else
            if(Input.touchCount>0){
                contacts=Input.touchCount;isTouch=true;var contact=Input.GetTouch(0);id=contact.fingerId;position=contact.position;
                phase=contact.phase==TouchPhase.Began?GesturePhase.Began:contact.phase==TouchPhase.Ended?GesturePhase.Ended:contact.phase==TouchPhase.Canceled?GesturePhase.Canceled:GesturePhase.Held;
            }else if(!touchFrame){
                position=Input.mousePosition;bool began=Input.GetMouseButtonDown(0),ended=Input.GetMouseButtonUp(0),held=Input.GetMouseButton(0);
                endedAlso=began&&ended;contacts=began||ended||held?1:0;phase=began?GesturePhase.Began:ended?GesturePhase.Ended:held?GesturePhase.Held:GesturePhase.None;
            }
#endif
            // Drain the first no-touch frame before accepting a mouse stream.
            touchFrame=isTouch;if(phase!=GesturePhase.None)ResetHint();
            var decision=gestureGate.Advance(contacts,id,isTouch,phase,true);
            if(decision==GestureDecision.Cancel){CancelPointer();return;}
            bool down=decision==GestureDecision.Begin,up=decision==GestureDecision.Commit;
            if(down&&endedAlso)up=gestureGate.Advance(1,id,isTouch,GesturePhase.Ended,true)==GestureDecision.Commit;
            if(down)pressed=null;
            if(down&&!OverControls(position)){pressed=ScreenCell(position);pressScreenPoint=position;if(boosterSelection>=0)selected=pressed;}
            // Commit a directional drag at a quarter-cell threshold, rather than
            // waiting for finger-up (which adds the rest of the swipe duration).
            if(!up&&phase==GesturePhase.Held&&pressed!=null&&boosterSelection<0&&inject<0&&!OverControls(position)){
                var w=view.ScreenToWorldPoint(new Vector3(position.x,position.y,10));var origin=view.ScreenToWorldPoint(new Vector3(pressScreenPoint.x,pressScreenPoint.y,10));var delta=w-origin;
                if(Mathf.Max(Mathf.Abs(delta.x),Mathf.Abs(delta.y))>=.26f){var target=new Cell(pressed.x+(Mathf.Abs(delta.x)>=Mathf.Abs(delta.y)?(delta.x>0?1:-1):0),pressed.y+(Mathf.Abs(delta.y)>Mathf.Abs(delta.x)?(delta.y>0?1:-1):0));
                    var from=pressed;pressed=null;gestureGate.Interrupt();if(board.Inside(target.x,target.y))PlayerSwap(from.x,from.y,target.x,target.y);return;}
            }
            if(up&&pressed!=null){var from=pressed;pressed=null;if(OverControls(position))return;var to=ScreenCell(position);if(to==null)return;
                if(boosterSelection>=0){var kind=(BoosterKind)boosterSelection;boosterSelection=-1;UseBooster(kind,to.x,to.y);return;}
                if(inject>=0){if(ManualPlaytestProtected){inject=-1;return;}if(board.InjectReviewPower(to.x,to.y,inject)){idle=board.Snapshot();message="Review placement: "+ReviewScenario.Name(inject);inject=-1;}else message="Place a review power-up on an ordinary gem.";return;}
                if(Math.Abs(from.x-to.x)+Math.Abs(from.y-to.y)==1){PlayerSwap(from.x,from.y,to.x,to.y);return;}
                if(selected!=null&&Math.Abs(selected.x-to.x)+Math.Abs(selected.y-to.y)==1){PlayerSwap(selected.x,selected.y,to.x,to.y);selected=null;return;}
                if(from.x==to.x&&from.y==to.y&&board.At(to.x,to.y)?.family=="power"){PlayerTap(to.x,to.y);return;}var piece=board.At(to.x,to.y);selected=piece!=null&&piece.Swappable?to:null;
            }
        }
        public bool ReviewObstacleHit(string family){
            if(ManualPlaytestProtected||!CanAct)return false;var p=board.Pieces.Values.FirstOrDefault(q=>q.IsAnchor&&q.family==family);if(p==null)return false;
            // Development drawer only: a staged hit retains the player's booster stock.
            var stock=new BoosterInventory();Accept(board.UseBooster(BoosterKind.Hammer,p.x,p.y,stock));return true;
        }
        public bool ReviewNaturalMove(){if(ManualPlaytestProtected||!CanAct)return false;var moves=board.LegalSwaps();if(moves.Count==0)return false;var p=moves[0];Accept(board.Swap(p[0].x,p[0].y,p[1].x,p[1].y));return true;}
        public bool ReviewReplayMove(ReplayMove move,out string error){
            error="Replay is waiting for the board.";if(ManualPlaytestProtected){error="End manual logging before starting a replay.";return false;}
            // The replay owns ReviewInputBlocked while player input is disabled.
            if(!InteractionGate.CanAct(Ready,Busy,pause,hud!=null&&hud.IsBlocking,board==null?"":board.Status))return false;
            TurnResult result;bool verified=CampaignReplayRules.Apply(board,move,out result,out error);if(result!=null&&result.accepted)Accept(result);return verified;
        }
        public bool ReviewActivate(int first,int second=-1){
            if(ManualPlaytestProtected||!CanAct)return false;
            var p=board.Pieces.Values.Where(q=>q.family=="gem"&&(second<0||board.At(q.x+1,q.y)?.family=="gem"))
                .OrderBy(q=>Math.Abs(q.x-board.Level.columns/2)+Math.Abs(q.y-board.Level.rows/2)).FirstOrDefault();
            if(p==null)return false;int x=p.x,y=p.y;
            if(!board.InjectReviewPower(x,y,first))return false;
            if(second>=0&&!board.InjectReviewPower(x+1,y,second))return false;
            idle=board.Snapshot();Accept(second<0?board.Tap(x,y):board.Swap(x,y,x+1,y));return true;
        }
        [ContextMenu("Show tutorial")] public void ReviewTutorial(){if(!ManualPlaytestProtected&&hud!=null)hud.ShowTutorial();}
        [ContextMenu("Preview success UI")] public void ReviewSuccess(){if(!ManualPlaytestProtected&&hud!=null)hud.ShowResult(true,board.Level.globalLevel);}
        [ContextMenu("Preview loss UI")] public void ReviewLoss(){if(!ManualPlaytestProtected&&hud!=null)hud.ShowResult(false,board.Level.globalLevel);}
        void OnDestroy(){Camera.onPostRender-=StartupCameraRendered79;CancelStartup79(true);if(effects!=null)effects.Dispose();if(bank!=null)bank.Dispose();if(bodyMaterial!=null)Destroy(bodyMaterial);if(selectionTexture!=null)Destroy(selectionTexture);}
    }
}
