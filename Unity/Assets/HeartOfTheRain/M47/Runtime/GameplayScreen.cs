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
    public sealed class GameplayScreen:MonoBehaviour {
        public GameplayUIAssets uiAssets;[Range(1,50)]public int initialLevel=1;public bool showLevelIntro=true;public bool boardRecoil=true;public float playbackSpeed=1;
        [NonSerialized] public int[] pendingStartingPowers;
        public string StartingPowerError {get;private set;}
        public bool InitializationComplete {get;private set;}
        public bool HasStartedWithPowers {get;private set;}
        readonly BoardGestureGate gestureGate=new BoardGestureGate();bool touchFrame;
        bool preparing;Rect fittedSafe;int fittedWidth,fittedHeight;
        M46Assets assets;GameplayHUD hud;GameplayFeedback feedback;SpriteRenderer backdrop;string uiHint="";bool resultShown;int previousMoves;
        BoosterInventory inventory=new BoosterInventory();int boosterSelection=-1,sampleKind;BoardModel board;BoardPresentation presentation;M46AtlasBank bank;Camera view;Transform root;Material bodyMaterial;
        readonly List<SpriteRenderer> pool=new List<SpriteRenderer>();readonly List<BoardStep> queue=new List<BoardStep>();
        readonly MaterialPropertyBlock lightBlock=new MaterialPropertyBlock();
        SpriteRenderer selection;Texture2D selectionTexture;Sprite selectionSprite;BoardStep current;BoardSnapshot idle;float clock,started;int levelIndex,queueIndex,inject=-1;Cell selected,pressed;bool pause;string message="Swap adjacent gems. Tap a selected power-up to activate it.";
        bool hintsEnabled=true;
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
        public BoardModel Model=>board;public bool Busy=>current!=null||preparing;
        public bool ReviewInputBlocked {get;set;}
        public bool ManualPlaytestProtected {get;set;}
        public uint CurrentSeed {get;private set;}
        public bool Ready=>board!=null&&hud!=null;
        public bool Paused=>pause;
        public bool CanAct=>InteractionGate.CanAct(Ready,Busy,pause,ReviewInputBlocked||(hud!=null&&hud.IsBlocking),board==null?"":board.Status);
        public int CurrentLevel=>levelIndex+1;
        public int ActiveSpriteCount {get;private set;}
        public int CachedSpriteCount=>bank==null?0:bank.SpriteCount;
        public int CachedTextureCount=>bank==null?0:bank.TextureCount;
        public long CachedTextureBytes=>bank==null?0:bank.TextureBytes;
        public int SynchronousTextureLoads=>bank==null?0:bank.SynchronousLoads;
        public int HistoryCount=>presentation==null?0:presentation.history.Count;
        public event Action<int> LevelLoaded;
        public event Action<string> LevelLeaving;
        public event Action<PlayerActionRecord> PlayerActionCompleted;
        public event Action<BoardStep> StepStarted;
        public event Action<string> TurnSettled;
        void OnEnable(){
#if ENABLE_INPUT_SYSTEM
            EnhancedTouchSupport.Enable();
#endif
            gestureGate.Interrupt();
        }
        void OnDisable(){CancelPointer();
#if ENABLE_INPUT_SYSTEM
            EnhancedTouchSupport.Disable();
#endif
        }
        void CancelPointer(){ResetHint();pressed=null;selected=null;boosterSelection=-1;gestureGate.Interrupt();}
        void OnApplicationFocus(bool focused){if(!focused){CancelPointer();if(Ready&&!ReviewInputBlocked){if(!hud.IsBlocking)hud.ShowPause();else SetPause(true);}}}
        void Start(){Application.targetFrameRate=60;QualitySettings.vSyncCount=0;Screen.orientation=ScreenOrientation.Portrait;assets=uiAssets==null?null:uiAssets.boards;if(assets==null){Debug.LogError("Assign the supplied M46Assets.asset.");enabled=false;return;}bank=new M46AtlasBank(assets);var cameraObject=new GameObject("M46 Review Camera");cameraObject.transform.SetParent(transform,false);view=cameraObject.AddComponent<Camera>();view.orthographic=true;view.clearFlags=CameraClearFlags.SolidColor;view.backgroundColor=new Color(.055f,.09f,.14f);view.transform.localPosition=new Vector3(0,0,-10);bodyMaterial=new Material(uiAssets.bodyShader!=null?uiAssets.bodyShader:Shader.Find("Sprites/Default"));feedback=gameObject.AddComponent<GameplayFeedback>();feedback.assets=uiAssets;hud=gameObject.AddComponent<GameplayHUD>();hud.assets=uiAssets;hud.feedback=feedback;hud.BoosterPressed=SelectBooster;hud.PauseChanged=SetPause;hud.RetryPressed=()=>Load(levelIndex,0,"retry");hud.ContinuePressed=()=>Load(Mathf.Min(49,levelIndex+1),0,"continue");hud.Build();
            var bg=new GameObject("Courtyard background");bg.transform.SetParent(transform,false);backdrop=bg.AddComponent<SpriteRenderer>();backdrop.sprite=uiAssets.Get("Gameplay_Backdrop");backdrop.sortingOrder=-100;backdrop.sharedMaterial=bodyMaterial;
            var listener=cameraObject.AddComponent<AudioListener>();if(FindObjectsOfType<AudioListener>().Length>1)listener.enabled=false;
            Load(initialLevel-1);InitializationComplete=true;}
        public void Load(int index,uint replaySeed=0,string reason="external"){
            LevelLeaving?.Invoke(reason);ResetHint();gestureGate.Interrupt();touchFrame=false;
            StopAllCoroutines();preparing=false;if(root!=null)root.gameObject.SetActive(false);if(board!=null){bank.Dispose();bank=new M46AtlasBank(assets);}
            feedback.ResetFeedback();hud.Close(false);resultShown=false;uiHint="";
            inventory=new BoosterInventory();boosterSelection=-1;levelIndex=Mathf.Clamp(index,0,assets.levels.Length-1);queue.Clear();queueIndex=0;current=null;clock=0;started=0;pause=false;inject=-1;selected=null;pressed=null;
            if(root!=null){root.gameObject.SetActive(false);Destroy(root.gameObject);}pool.Clear();root=new GameObject("Live board").transform;root.SetParent(transform,false);
            board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[levelIndex].text),replaySeed);StartingPowerError=null;HasStartedWithPowers=false;if(pendingStartingPowers!=null){string grantError;HasStartedWithPowers=board.TryPlaceStartingPowers(pendingStartingPowers,out grantError);if(!HasStartedWithPowers)StartingPowerError=grantError;pendingStartingPowers=null;}CurrentSeed=replaySeed==0?(uint)Math.Max(1,board.Level.tileSeed):replaySeed;idle=board.Snapshot();presentation=new BoardPresentation{columns=board.Level.columns,rows=board.Level.rows};foreach(var p in assets.debrisProfiles){var profile=JsonUtility.FromJson<DebrisProfile>(p.metadata.text);foreach(var piece in profile.pieces){if(piece.scaleMultiplier<=0)piece.scaleMultiplier=1;if(piece.spinMultiplier<=0)piece.spinMultiplier=1;}presentation.profiles.Add(p.family,profile);}
            var surface=Make("Approved R2 board",0);surface.sprite=bank.BoardSurface(levelIndex);surface.sharedMaterial=bodyMaterial;
            var maskObject=new GameObject("Active-cell mask");maskObject.transform.SetParent(root,false);var mask=maskObject.AddComponent<SpriteMask>();mask.sprite=bank.BoardMask(levelIndex);mask.isCustomRangeActive=true;mask.frontSortingOrder=15;mask.backSortingOrder=5;
            foreach(var exit in board.Level.deliveryExits??new Cell[0]){var sr=Make("Jar exit",4);sr.sprite=bank.Whole("exit",assets.exitMarker,.78f,true);sr.transform.localPosition=Position(exit.x,exit.y-.39f);}
            selection=Make("Selected cell",14);selectionSprite=uiAssets.Get("Focus_Cell");selection.sprite=selectionSprite;selection.color=Color.white;selection.transform.localScale=Vector3.one*(.94f/selectionSprite.bounds.size.x);selection.enabled=false;
            previousMoves=board.Moves;fittedWidth=-1;Fit();Render();UpdateHUD();if(showLevelIntro)hud.ShowIntro(board.Level.globalLevel,board.Snapshot().goals,board.Level.introductionTitle,board.Level.introductionInstruction);LevelLoaded?.Invoke(CurrentLevel);
        }
        Vector3 Position(float x,float y){return new Vector3(x-(board.Level.columns-1)*.5f,y-(board.Level.rows-1)*.5f,0);}
        SpriteRenderer Make(string label,int order){var go=new GameObject(label);go.transform.SetParent(root,false);var sr=go.AddComponent<SpriteRenderer>();sr.sharedMaterial=assets.effectsMaterial;sr.sortingOrder=order;return sr;}
        void Fit(){var safe=Screen.safeArea;if(safe==fittedSafe&&Screen.width==fittedWidth&&Screen.height==fittedHeight)return;fittedSafe=safe;fittedWidth=Screen.width;fittedHeight=Screen.height;var layout=ReviewLayout.Compute(safe.width,safe.height,board.Level.columns,board.Level.rows);float h=layout.height,cell=layout.cell;view.rect=new Rect(safe.x/Screen.width,safe.y/Screen.height,safe.width/Screen.width,safe.height/Screen.height);view.orthographicSize=h/(2*cell);view.transform.localPosition=new Vector3(0,20/cell,-10);float aspect=safe.width/safe.height;presentation.bottom=(board.Level.rows-1)*.5f+20/cell-view.orthographicSize;presentation.left=(board.Level.columns-1)*.5f-view.orthographicSize*aspect;presentation.right=(board.Level.columns-1)*.5f+view.orthographicSize*aspect;
            if(backdrop!=null){backdrop.transform.localPosition=new Vector3(0,20/cell,1);backdrop.transform.localScale=new Vector3(2*view.orthographicSize*aspect/backdrop.sprite.bounds.size.x,2*view.orthographicSize/backdrop.sprite.bounds.size.y,1);}}
        void Enqueue(IEnumerable<BoardStep> steps){queue.AddRange(steps);selected=null;pressed=null;StartCoroutine(PrepareQueue());}
        IEnumerator PrepareQueue(){preparing=true;uiHint="";yield return bank.Prewarm(bank.RequiredResources(queue));
            if(bank.LoadError!=null){uiHint="Unable to load effects. Restart this level.";hud.ShowPause();yield break;}
            preparing=false;if(current==null)Next();}
        void Next(){if(queueIndex>=queue.Count){current=null;idle=board.Snapshot();queue.Clear();queueIndex=0;TurnSettled?.Invoke(board.Status);message=board.Status=="Playing"?"Ready · "+board.Moves+" moves remaining":board.Status;return;}current=queue[queueIndex++];started=clock;presentation.Add(current,started);message=current.label;feedback.Begin(current);feedback.Sample(0);StepStarted?.Invoke(current);}
        void Accept(TurnResult result){if(!result.accepted){uiHint=result.reason;feedback.Play("ui_invalid",.65f);return;}uiHint="";Enqueue(result.steps);}
        void AcceptPlayer(TurnResult result,string kind,int x,int y,int toX=-1,int toY=-1,int booster=-1){
            PlayerActionCompleted?.Invoke(new PlayerActionRecord{kind=kind,x=x,y=y,toX=toX,toY=toY,booster=booster,accepted=result.accepted,reason=result.reason});
            Accept(result);
        }
        public void SelectBooster(int kind){if(!CanAct||kind<0||kind>3||inventory.Count((BoosterKind)kind)<=0)return;
            feedback.Play("ui_select",.65f,"select");if(kind==3){boosterSelection=-1;AcceptPlayer(board.UseBooster(BoosterKind.Atlas,0,0,inventory),"booster",0,0,booster:3);return;}
            boosterSelection=boosterSelection==kind?-1:kind;selected=null;uiHint=boosterSelection<0?"":new[]{"Hammer: choose a tile","Axe: choose a column","Ram: choose a row"}[kind];}
        public void UseBooster(BoosterKind kind,int x,int y){if(!CanAct)return;AcceptPlayer(board.UseBooster(kind,x,y,inventory),"booster",x,y,booster:(int)kind);}
        public void SetPause(bool value){pause=value;if(value)CancelPointer();else pressed=null;if(feedback!=null)feedback.Pause(value);}
        public void ResumeReview(){if(hud!=null)hud.Close(true);}
        void OnApplicationPause(bool suspended){if(suspended&&Ready){pressed=null;if(!hud.IsBlocking)hud.ShowPause();else SetPause(true);}}
        void UpdateHUD(){var visible=presentation.DisplayGoals(current,idle,clock-started);int shownMoves=current!=null?current.after.moves:idle.moves;hud.UpdateState(board.Level.globalLevel,shownMoves,visible,inventory,boosterSelection,Busy,uiHint);
            if(shownMoves==5&&previousMoves>5)feedback.Play("moves_low",.7f);previousMoves=shownMoves;
            if(!Busy&&!resultShown&&board.Status!="Playing"){resultShown=true;hud.ShowResult(board.Status=="Won",board.Level.globalLevel);}}
        void Update(){if(board==null)return;Fit();if(!pause&&!preparing){float advance=Time.deltaTime*playbackSpeed;
            while(current!=null&&advance>0){float remaining=current.duration-(clock-started);if(advance<remaining){clock+=advance;feedback.Sample(clock-started);advance=0;}else{clock+=remaining;feedback.Sample(current.duration);advance-=remaining;Next();}}
            if(current==null)clock+=advance;}
            ReadPointer();Render();UpdateHUD();UpdateHint();}
        void Render(){hud.BeginCollections();foreach(var goal in board.Goals.Keys){Vector2 point;if(hud.TryGoalScreenPoint(goal,out point)){var w=view.ScreenToWorldPoint(new Vector3(point.x,point.y,10));w=root.InverseTransformPoint(w);presentation.goalTargets[goal]=new Vector2(w.x+(board.Level.columns-1)*.5f,w.y+(board.Level.rows-1)*.5f);}}bank.BeginFrame();presentation.PruneHistory(clock);var kick=BoosterTimeline.BoardKick(presentation.history,clock,boardRecoil?1:0);root.localPosition=new Vector3(kick.x,kick.y,0);var draws=presentation.Sample(current,idle,clock,started);int count=0;foreach(var d in draws){var sprite=bank.Get(d);if(sprite==null||d.alpha<=0)continue;if(d.uiOverlay){var point=view.WorldToScreenPoint(root.TransformPoint(Position(d.x,d.y)));float pixels=view.pixelHeight/(2*view.orthographicSize);hud.DrawCollection(sprite,new Vector2(point.x,point.y),new Vector2(sprite.bounds.size.x*d.sx*pixels,sprite.bounds.size.y*d.sy*pixels),d.angle,new Color(d.red,d.green,d.blue,d.alpha));continue;}if(count>=pool.Count)pool.Add(Make("Sampled sprite",d.order));var sr=pool[count++];sr.enabled=true;sr.sprite=sprite;sr.sortingOrder=d.order;sr.sharedMaterial=d.glow>0?assets.tileGlowMaterial:d.masked?bodyMaterial:assets.effectsMaterial;sr.maskInteraction=d.masked?SpriteMaskInteraction.VisibleInsideMask:SpriteMaskInteraction.None;sr.transform.localPosition=Position(d.x,d.y);sr.transform.localScale=new Vector3(d.sx,d.sy,1);sr.transform.localRotation=Quaternion.Euler(0,0,d.angle);sr.color=new Color(d.red,d.green,d.blue,d.alpha);lightBlock.Clear();lightBlock.SetFloat("_Glow",d.glow);sr.SetPropertyBlock(lightBlock);}for(int i=count;i<pool.Count;i++){pool[i].enabled=false;pool[i].sprite=null;}hud.EndCollections();ActiveSpriteCount=count+draws.Count(d=>d.uiOverlay);bank.EndFrame(!Busy);
            selection.enabled=selected!=null&&!Busy;if(selection.enabled)selection.transform.localPosition=Position(selected.x,selected.y);
        }
        Cell ScreenCell(Vector2 screen){var w=view.ScreenToWorldPoint(new Vector3(screen.x,screen.y,10));w=root.InverseTransformPoint(w);int x=Mathf.RoundToInt(w.x+(board.Level.columns-1)*.5f),y=Mathf.RoundToInt(w.y+(board.Level.rows-1)*.5f);return board.Inside(x,y)?new Cell(x,y):null;}
        bool OverControls(Vector2 p){var safe=Screen.safeArea;float s=safe.width/720;return p.y>safe.yMax-240*s||p.y<safe.y+200*s||!safe.Contains(p)||hud.IsBlocking;}
        void ReadPointer(){
            if(!CanAct){CancelPointer();return;}
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
            if(down&&!OverControls(position)){pressed=ScreenCell(position);if(boosterSelection>=0)selected=pressed;}
            if(up&&pressed!=null){var from=pressed;pressed=null;if(OverControls(position))return;var to=ScreenCell(position);if(to==null)return;
                if(boosterSelection>=0){var kind=(BoosterKind)boosterSelection;boosterSelection=-1;UseBooster(kind,to.x,to.y);return;}
                if(inject>=0){if(ManualPlaytestProtected){inject=-1;return;}if(board.InjectReviewPower(to.x,to.y,inject)){idle=board.Snapshot();message="Review placement: "+ReviewScenario.Name(inject);inject=-1;}else message="Place a review power-up on an ordinary gem.";return;}
                if(Math.Abs(from.x-to.x)+Math.Abs(from.y-to.y)==1){AcceptPlayer(board.Swap(from.x,from.y,to.x,to.y),"swap",from.x,from.y,to.x,to.y);return;}
                if(selected!=null&&Math.Abs(selected.x-to.x)+Math.Abs(selected.y-to.y)==1){AcceptPlayer(board.Swap(selected.x,selected.y,to.x,to.y),"swap",selected.x,selected.y,to.x,to.y);selected=null;return;}
                if(selected!=null&&selected.x==to.x&&selected.y==to.y&&board.At(to.x,to.y)?.family=="power"){AcceptPlayer(board.Tap(to.x,to.y),"tap",to.x,to.y);return;}var piece=board.At(to.x,to.y);selected=piece!=null&&piece.Swappable?to:null;
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
        void OnDestroy(){if(bank!=null)bank.Dispose();if(bodyMaterial!=null)Destroy(bodyMaterial);if(selectionTexture!=null)Destroy(selectionTexture);}
    }
}
