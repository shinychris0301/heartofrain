using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif
namespace HeartOfTheRain.M46 {
    [DisallowMultipleComponent]
    public sealed class BoosterReview:MonoBehaviour {
        public M46Assets assets;[Range(0,3)]public int initialLevel=2;[Range(0,3)]public int initialBooster;public bool autoPlay=true;public float playbackSpeed=1;public bool boardRecoil=true;
        BoosterInventory inventory=new BoosterInventory();int boosterSelection=-1,sampleKind;BoardModel board;BoardPresentation presentation;M46AtlasBank bank;Camera view;Transform root;Material bodyMaterial;
        readonly List<SpriteRenderer> pool=new List<SpriteRenderer>();readonly List<BoardStep> queue=new List<BoardStep>();
        readonly MaterialPropertyBlock lightBlock=new MaterialPropertyBlock();
        SpriteRenderer selection;Texture2D selectionTexture;Sprite selectionSprite;BoardStep current;BoardSnapshot idle;float clock,started;int levelIndex,queueIndex,inject=-1;Cell selected,pressed;bool pause;string message="Swap adjacent gems. Tap a selected power-up to activate it.";
        public BoardModel Model=>board;public bool Busy=>current!=null;
        void Start(){if(assets==null){Debug.LogError("Assign the supplied M46Assets.asset.");enabled=false;return;}bank=new M46AtlasBank(assets);var cameraObject=new GameObject("M46 Review Camera");cameraObject.transform.SetParent(transform,false);view=cameraObject.AddComponent<Camera>();view.orthographic=true;view.clearFlags=CameraClearFlags.SolidColor;view.backgroundColor=new Color(.055f,.09f,.14f);view.transform.localPosition=new Vector3(0,0,-10);bodyMaterial=new Material(Shader.Find("Sprites/Default"));Load(initialLevel);if(autoPlay)PlayBoosterSample(initialBooster);}
        public void Load(int index){
            inventory=new BoosterInventory();boosterSelection=-1;levelIndex=Mathf.Clamp(index,0,assets.levels.Length-1);queue.Clear();queueIndex=0;current=null;clock=0;started=0;pause=false;inject=-1;selected=null;pressed=null;
            if(root!=null){root.gameObject.SetActive(false);Destroy(root.gameObject);}pool.Clear();root=new GameObject("Live board").transform;root.SetParent(transform,false);
            board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[levelIndex].text));idle=board.Snapshot();presentation=new BoardPresentation{columns=board.Level.columns,rows=board.Level.rows};foreach(var p in assets.debrisProfiles){var profile=JsonUtility.FromJson<DebrisProfile>(p.metadata.text);foreach(var piece in profile.pieces){if(piece.scaleMultiplier<=0)piece.scaleMultiplier=1;if(piece.spinMultiplier<=0)piece.spinMultiplier=1;}presentation.profiles.Add(p.family,profile);}
            var surface=Make("Approved R2 board",0);surface.sprite=bank.Whole("surface/"+levelIndex,assets.surfaces[levelIndex],assets.surfaces[levelIndex].width/64f);surface.sharedMaterial=bodyMaterial;
            var maskObject=new GameObject("Active-cell mask");maskObject.transform.SetParent(root,false);var mask=maskObject.AddComponent<SpriteMask>();mask.sprite=bank.Whole("mask/"+levelIndex,assets.masks[levelIndex],assets.masks[levelIndex].width/64f);mask.isCustomRangeActive=true;mask.frontSortingOrder=15;mask.backSortingOrder=5;
            foreach(var exit in board.Level.deliveryExits??new Cell[0]){var sr=Make("Jar exit",4);sr.sprite=bank.Whole("exit",assets.exitMarker,.78f);sr.transform.localPosition=Position(exit.x,exit.y-.39f);}
            selection=Make("Selected cell",14);if(selectionSprite==null){selectionTexture=new Texture2D(1,1);selectionTexture.SetPixel(0,0,Color.white);selectionTexture.Apply();selectionSprite=Sprite.Create(selectionTexture,new Rect(0,0,1,1),new Vector2(.5f,.5f),1);}selection.sprite=selectionSprite;selection.color=new Color(1,.86f,.4f,.18f);selection.transform.localScale=Vector3.one*.9f;selection.enabled=false;
            message="Level "+board.Level.globalLevel+" · swap adjacent gems; tap a selected power-up.";Fit();Render();
        }
        Vector3 Position(float x,float y){return new Vector3(x-(board.Level.columns-1)*.5f,y-(board.Level.rows-1)*.5f,0);}
        SpriteRenderer Make(string label,int order){var go=new GameObject(label);go.transform.SetParent(root,false);var sr=go.AddComponent<SpriteRenderer>();sr.sharedMaterial=assets.effectsMaterial;sr.sortingOrder=order;return sr;}
        void Fit(){var safe=Screen.safeArea;view.rect=new Rect(safe.x/Screen.width,safe.y/Screen.height,safe.width/Screen.width,safe.height/Screen.height);float aspect=safe.width/Mathf.Max(1,safe.height);view.orthographicSize=BoardPresentation.CameraHalfHeight(board.Level.columns,board.Level.rows,aspect);float center=(board.Level.rows-1)*.5f;presentation.bottom=center-view.orthographicSize;float halfWidth=view.orthographicSize*aspect;presentation.left=(board.Level.columns-1)*.5f-halfWidth;presentation.right=(board.Level.columns-1)*.5f+halfWidth;}
        void Enqueue(IEnumerable<BoardStep> steps){queue.AddRange(steps);selected=null;pressed=null;if(current==null)Next();}
        void Next(){if(queueIndex>=queue.Count){current=null;idle=board.Snapshot();queue.Clear();queueIndex=0;message=board.Status=="Playing"?"Ready · "+board.Moves+" moves remaining":board.Status;return;}current=queue[queueIndex++];started=clock;presentation.Add(current,started);message=current.label;}
        void Accept(TurnResult result){if(!result.accepted){message=result.reason;return;}Enqueue(result.steps);}
        public void PlayBoosterSample(int kind){sampleKind=Mathf.Clamp(kind,0,3);Load(new[]{2,1,2,3}[sampleKind]);int[] xs={5,4,4,5},ys={2,5,7,5};var initial=board.Snapshot();var result=board.UseBooster((BoosterKind)sampleKind,xs[sampleKind],ys[sampleKind],inventory);if(result.accepted){var steps=new List<BoardStep>{new BoardStep{kind="ready",duration=.75f,label=BoosterPlan.Name((BoosterKind)sampleKind),before=initial,after=initial}};steps.AddRange(result.steps);Enqueue(steps);}else message=result.reason;}
        public void UseBooster(BoosterKind kind,int x,int y){if(Busy)return;Accept(board.UseBooster(kind,x,y,inventory));}
        void Update(){if(board==null)return;Fit();if(!pause){clock+=Time.deltaTime*playbackSpeed;if(current!=null&&clock-started>=current.duration){clock=started+current.duration;Next();}}ReadPointer();Render();}
        void Render(){var kick=BoosterTimeline.BoardKick(presentation.history,clock,boardRecoil?1:0);root.localPosition=new Vector3(kick.x,kick.y,0);var draws=presentation.Sample(current,idle,clock,started);int count=0;foreach(var d in draws){var sprite=bank.Get(d);if(sprite==null||d.alpha<=0)continue;if(count>=pool.Count)pool.Add(Make("Sampled sprite",d.order));var sr=pool[count++];sr.enabled=true;sr.sprite=sprite;sr.sortingOrder=d.order;sr.sharedMaterial=d.glow>0?assets.tileGlowMaterial:d.masked?bodyMaterial:assets.effectsMaterial;sr.maskInteraction=d.masked?SpriteMaskInteraction.VisibleInsideMask:SpriteMaskInteraction.None;sr.transform.localPosition=Position(d.x,d.y);sr.transform.localScale=new Vector3(d.sx,d.sy,1);sr.transform.localRotation=Quaternion.Euler(0,0,d.angle);sr.color=new Color(d.red,d.green,d.blue,d.alpha);lightBlock.Clear();lightBlock.SetFloat("_Glow",d.glow);sr.SetPropertyBlock(lightBlock);}for(int i=count;i<pool.Count;i++)pool[i].enabled=false;
            selection.enabled=selected!=null&&!Busy;if(selection.enabled)selection.transform.localPosition=Position(selected.x,selected.y);
        }
        Cell ScreenCell(Vector2 screen){var w=view.ScreenToWorldPoint(new Vector3(screen.x,screen.y,10));w=transform.InverseTransformPoint(w);int x=Mathf.RoundToInt(w.x+(board.Level.columns-1)*.5f),y=Mathf.RoundToInt(w.y+(board.Level.rows-1)*.5f);return board.Inside(x,y)?new Cell(x,y):null;}
        bool OverControls(Vector2 p){var safe=Screen.safeArea;float s=Mathf.Min(safe.width/720,safe.height/1000);return p.y>safe.yMax-175*s||p.y<safe.y+175*s||!safe.Contains(p);}
        void ReadPointer(){if(Busy||pause||board.Status!="Playing")return;bool down=false,up=false;Vector2 position=default(Vector2);
#if ENABLE_INPUT_SYSTEM
            if(Touchscreen.current!=null&&Touchscreen.current.primaryTouch.press.isPressed){position=Touchscreen.current.primaryTouch.position.ReadValue();down=Touchscreen.current.primaryTouch.press.wasPressedThisFrame;}
            if(Touchscreen.current!=null&&Touchscreen.current.primaryTouch.press.wasReleasedThisFrame){position=Touchscreen.current.primaryTouch.position.ReadValue();up=true;}
            if(Mouse.current!=null&&(Mouse.current.leftButton.wasPressedThisFrame||Mouse.current.leftButton.wasReleasedThisFrame)){position=Mouse.current.position.ReadValue();down=Mouse.current.leftButton.wasPressedThisFrame;up=Mouse.current.leftButton.wasReleasedThisFrame;}
#else
            if(Input.touchCount>0){var touch=Input.GetTouch(0);position=touch.position;down=touch.phase==TouchPhase.Began;up=touch.phase==TouchPhase.Ended;}else {position=Input.mousePosition;down=Input.GetMouseButtonDown(0);up=Input.GetMouseButtonUp(0);}
#endif
            if(down&&!OverControls(position))pressed=ScreenCell(position);
            if(up&&pressed!=null){var from=pressed;pressed=null;if(OverControls(position))return;var to=ScreenCell(position);if(to==null)return;
                if(boosterSelection>=0){var kind=(BoosterKind)boosterSelection;boosterSelection=-1;UseBooster(kind,to.x,to.y);return;}
                if(inject>=0){if(board.InjectReviewPower(to.x,to.y,inject)){idle=board.Snapshot();message="Review placement: "+ReviewScenario.Name(inject);inject=-1;}else message="Place a review power-up on an ordinary gem.";return;}
                if(Math.Abs(from.x-to.x)+Math.Abs(from.y-to.y)==1){Accept(board.Swap(from.x,from.y,to.x,to.y));return;}
                if(selected!=null&&Math.Abs(selected.x-to.x)+Math.Abs(selected.y-to.y)==1){Accept(board.Swap(selected.x,selected.y,to.x,to.y));selected=null;return;}
                if(selected!=null&&selected.x==to.x&&selected.y==to.y&&board.At(to.x,to.y)?.family=="power"){Accept(board.Tap(to.x,to.y));return;}var piece=board.At(to.x,to.y);selected=piece!=null&&piece.Swappable?to:null;
            }
        }
        void OnGUI(){if(board==null)return;var safe=Screen.safeArea;float scale=Mathf.Min(safe.width/720,safe.height/1100);var oldMatrix=GUI.matrix;GUI.matrix=Matrix4x4.TRS(new Vector3(safe.x+(safe.width-720*scale)*.5f,Screen.height-safe.yMax,0),Quaternion.identity,Vector3.one*scale);float h=safe.height/scale;
            var title=new GUIStyle(GUI.skin.label){fontSize=27,fontStyle=FontStyle.Bold};var text=new GUIStyle(GUI.skin.label){fontSize=18,wordWrap=true};var button=new GUIStyle(GUI.skin.button){fontSize=17};
            GUI.Label(new Rect(22,14,680,38),"HEART OF THE RAIN · BOOSTERS",title);
            GUI.Label(new Rect(22,55,680,30),"Level "+board.Level.globalLevel+" | "+board.Level.columns+" × "+board.Level.rows+" | Moves "+board.Moves,text);
            GUI.Label(new Rect(22,88,680,48),string.Join(" · ",presentation.DisplayGoals(current,idle,clock-started).Select(g=>DisplayFamily(g.family)+" "+g.count)),text);
            GUI.Label(new Rect(22,138,680,40),message,text);
            float y=h-180;string[] names={"Hammer","Axe","Ram","Atlas"};GUI.enabled=!Busy;
            for(int i=0;i<4;i++)if(GUI.Button(new Rect(22+i*172,y,166,40),(boosterSelection==i?"✓ ":"")+names[i]+" ("+inventory.Count((BoosterKind)i)+")",button)){if(i==3){boosterSelection=-1;UseBooster(BoosterKind.Atlas,0,0);}else {boosterSelection=boosterSelection==i?-1:i;message=boosterSelection<0?"Selection cancelled":"Choose an active cell for "+names[i];}}
            GUI.enabled=true;
            for(int i=0;i<4;i++)if(GUI.Button(new Rect(22+i*172,y+48,166,36),"Preview "+names[i],button))PlayBoosterSample(i);
            if(GUI.Button(new Rect(22,y+92,108,36),pause?"Resume":"Pause",button))pause=!pause;
            if(GUI.Button(new Rect(138,y+92,108,36),"Replay",button))PlayBoosterSample(sampleKind);
            if(GUI.Button(new Rect(254,y+92,108,36),playbackSpeed<1?"Speed 0.5×":"Speed 1×",button))playbackSpeed=playbackSpeed<1?1:.5f;
            for(int i=0;i<4;i++)if(GUI.Button(new Rect(370+i*82,y+92,76,36),new[]{"L10","L18","L40","L41"}[i],button))Load(i);
            GUI.Label(new Rect(22,y+136,680,42),"Manual boosters use no moves. Atlas keeps obstacles and jars fixed.",text);GUI.matrix=oldMatrix;
        }
        public static string DisplayFamily(string f){switch(f){case "crate":return "Crates";case "moss":return "Overgrowth";case "stone":return "Stones";case "pail":return "Jars";case "gate":return "Sluices";case "case":return "Cases";default:return f;}}
        void OnDestroy(){if(bank!=null)bank.Dispose();if(bodyMaterial!=null)Destroy(bodyMaterial);if(selectionSprite!=null)Destroy(selectionSprite);if(selectionTexture!=null)Destroy(selectionTexture);}
    }
}
