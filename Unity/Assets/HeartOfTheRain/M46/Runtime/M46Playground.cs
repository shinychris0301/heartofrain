using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif
namespace HeartOfTheRain.M46 {
    [DisallowMultipleComponent]
    public sealed class M46Playground:MonoBehaviour {
        public M46Assets assets;[Range(0,3)]public int initialLevel;
        BoardModel board;BoardPresentation presentation;M46AtlasBank bank;Camera view;Transform root;Material bodyMaterial;
        readonly List<SpriteRenderer> pool=new List<SpriteRenderer>();readonly List<BoardStep> queue=new List<BoardStep>();
        readonly MaterialPropertyBlock lightBlock=new MaterialPropertyBlock();
        SpriteRenderer selection;Texture2D selectionTexture;Sprite selectionSprite;BoardStep current;BoardSnapshot idle;float clock,started;int levelIndex,queueIndex,inject=-1;Cell selected,pressed;bool pause;string message="Swap adjacent gems. Tap a selected power-up to activate it.";
        public BoardModel Model=>board;public bool Busy=>current!=null;
        void Start(){if(assets==null){Debug.LogError("Assign the supplied M46Assets.asset.");enabled=false;return;}bank=new M46AtlasBank(assets);var cameraObject=new GameObject("M46 Review Camera");cameraObject.transform.SetParent(transform,false);view=cameraObject.AddComponent<Camera>();view.orthographic=true;view.clearFlags=CameraClearFlags.SolidColor;view.backgroundColor=new Color(.055f,.09f,.14f);view.transform.localPosition=new Vector3(0,0,-10);bodyMaterial=new Material(Shader.Find("Sprites/Default"));Load(initialLevel);}
        public void Load(int index){
            levelIndex=Mathf.Clamp(index,0,assets.levels.Length-1);queue.Clear();queueIndex=0;current=null;clock=0;started=0;pause=false;inject=-1;selected=null;pressed=null;
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
        public void PlaySample(){Load(levelIndex);Enqueue(ReviewScenario.Build(board));}
        void Update(){if(board==null)return;Fit();if(!pause){clock+=Time.deltaTime;if(current!=null&&clock-started>=current.duration){clock=started+current.duration;Next();}}ReadPointer();Render();}
        void Render(){var draws=presentation.Sample(current,idle,clock,started);int count=0;foreach(var d in draws){var sprite=bank.Get(d);if(sprite==null||d.alpha<=0)continue;if(count>=pool.Count)pool.Add(Make("Sampled sprite",d.order));var sr=pool[count++];sr.enabled=true;sr.sprite=sprite;sr.sortingOrder=d.order;sr.sharedMaterial=d.glow>0?assets.tileGlowMaterial:d.masked?bodyMaterial:assets.effectsMaterial;sr.maskInteraction=d.masked?SpriteMaskInteraction.VisibleInsideMask:SpriteMaskInteraction.None;sr.transform.localPosition=Position(d.x,d.y);sr.transform.localScale=new Vector3(d.sx,d.sy,1);sr.transform.localRotation=Quaternion.Euler(0,0,d.angle);sr.color=new Color(d.red,d.green,d.blue,d.alpha);lightBlock.Clear();lightBlock.SetFloat("_Glow",d.glow);sr.SetPropertyBlock(lightBlock);}for(int i=count;i<pool.Count;i++)pool[i].enabled=false;
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
                if(inject>=0){if(board.InjectReviewPower(to.x,to.y,inject)){idle=board.Snapshot();message="Review placement: "+ReviewScenario.Name(inject);inject=-1;}else message="Place a review power-up on an ordinary gem.";return;}
                if(Math.Abs(from.x-to.x)+Math.Abs(from.y-to.y)==1){Accept(board.Swap(from.x,from.y,to.x,to.y));return;}
                if(selected!=null&&Math.Abs(selected.x-to.x)+Math.Abs(selected.y-to.y)==1){Accept(board.Swap(selected.x,selected.y,to.x,to.y));selected=null;return;}
                if(selected!=null&&selected.x==to.x&&selected.y==to.y&&board.At(to.x,to.y)?.family=="power"){Accept(board.Tap(to.x,to.y));return;}var piece=board.At(to.x,to.y);selected=piece!=null&&piece.Swappable?to:null;
            }
        }
        void OnGUI(){if(board==null)return;var safe=Screen.safeArea;float scale=Mathf.Min(safe.width/720,safe.height/1000);var oldMatrix=GUI.matrix;GUI.matrix=Matrix4x4.TRS(new Vector3(safe.x+(safe.width-720*scale)*.5f,Screen.height-safe.yMax,0),Quaternion.identity,Vector3.one*scale);float h=safe.height/scale;var title=new GUIStyle(GUI.skin.label){fontSize=28,fontStyle=FontStyle.Bold};var text=new GUIStyle(GUI.skin.label){fontSize=19,wordWrap=true};var small=new GUIStyle(GUI.skin.label){fontSize=16};var button=new GUIStyle(GUI.skin.button){fontSize=18};
            GUI.Label(new Rect(22,14,680,38),"HEART OF THE RAIN · CHAPTER 1",title);
            var snap=current==null?idle:current.after;GUI.Label(new Rect(22,54,680,30),"Level "+board.Level.globalLevel+"  |  "+board.Level.columns+" × "+board.Level.rows+"  |  Moves "+snap.moves,text);
            var goals=presentation.DisplayGoals(current,idle,clock-started);GUI.Label(new Rect(22,89,680,50),string.Join("   ·   ",goals.Select(g=>DisplayFamily(g.family)+" "+g.count)),text);
            GUI.Label(new Rect(22,139,680,32),message,small);
            float y=h-164;for(int i=0;i<assets.levels.Length;i++){int idx=i;if(GUI.Button(new Rect(22+i*84,y,78,38),new[]{"L10","L18","L40","L41"}[i],button)){Load(idx);}}
            if(GUI.Button(new Rect(366,y,96,38),"Restart",button))Load(levelIndex);
            if(GUI.Button(new Rect(470,y,96,38),pause?"Resume":"Pause",button))pause=!pause;
            if(GUI.Button(new Rect(574,y,124,38),"Play sample",button))PlaySample();
            GUI.enabled=!Busy;int[] kinds={4,5,21,11,7,16};string[] labels={"Rocket H","Rocket V","Bomb","Rain","Orb","Golden"};for(int i=0;i<kinds.Length;i++)if(GUI.Button(new Rect(22+i*114,y+48,108,38),(inject==kinds[i]?"✓ ":"")+labels[i],button)){inject=inject==kinds[i]?-1:kinds[i];message=inject<0?"Placement cancelled":"Review tool: choose a gem cell for "+ReviewScenario.Name(inject);}
            if(GUI.Button(new Rect(22,y+96,108,36),"Hint",button)){var hints=board.LegalSwaps();if(hints.Count>0){selected=hints[0][0];message="Swap highlighted cell with ("+(hints[0][1].x+1)+", "+(hints[0][1].y+1)+")";}}
            GUI.enabled=true;GUI.Label(new Rect(144,y+98,550,50),"Review placement tools · do not consume moves.\nGolden creates two seekers; no Golden + Golden rule.",small);GUI.matrix=oldMatrix;
        }
        public static string DisplayFamily(string f){switch(f){case "crate":return "Crates";case "moss":return "Overgrowth";case "stone":return "Stones";case "pail":return "Jars";case "gate":return "Sluices";case "case":return "Cases";default:return f;}}
        void OnDestroy(){if(bank!=null)bank.Dispose();if(bodyMaterial!=null)Destroy(bodyMaterial);if(selectionSprite!=null)Destroy(selectionSprite);if(selectionTexture!=null)Destroy(selectionTexture);}
    }
}
