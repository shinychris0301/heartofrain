using System;
using UnityEngine;
using Player = HeartOfTheRain.M05.RenderedSpritePlayer;

namespace HeartOfTheRain.M07
{
    public enum ReviewKind { BombThenRocket, RocketThenBomb, RocketBomb, DoubleBomb, RocketHorizontal, RocketVertical, DoubleRocket, RainbowOrb, RainbowRocket, RainbowBomb, DoubleRainbow, RainSeeker, RainSeekerRocket, RainSeekerBomb, DoubleRainSeeker, OrbRainSeeker, GoldenSeeker, GoldenSeekerRocket, GoldenSeekerBomb, GoldenRainSeeker, OrbGoldenSeeker, Bomb }
    /// <summary>Scripted asset playback with refill. No match detection, scoring or level state.</summary>
    public sealed class BoardReactionReview : MonoBehaviour
    {
        [Range(3,15)] public int columns=9,rows=9;public Vector2Int origin=new Vector2Int(-1,-1);public ReviewKind kind;[Tooltip("Rainbow combinations: -1 selects the most common eligible color; 0–5 override it for review.")][Range(-1,5)] public int targetColor=-1;
        [Tooltip("Rain Seeker and its combinations: (-1,-1) selects automatically; otherwise an eligible target cell.")] public Vector2Int seekerTarget=new Vector2Int(-1,-1);
        [Tooltip("Seeker + Rocket: clear the target column when enabled; otherwise the target row.")] public bool rocketVertical;
        public float cellPitch=1;public bool showBlockers=true,play=true,enableRecoil=true,createPreviewCamera=true;
        [Range(0,40f)] public float scrubTime;
        [HideInInspector] public bool externallyDriven;
        public Texture2D[] atlases;public TextAsset[] manifests;public Material spriteMaterial,tileGlowMaterial;public Sprite[] referenceTiles;
        public TextAsset[] validationFixtures;
        readonly MaterialPropertyBlock tileLight = new MaterialPropertyBlock();
        ReviewPlan plan;Transform content;Camera previewCamera;Texture2D whiteTexture;Sprite white;SpriteRenderer[] tiles;Player[] crates,fx,powers;Player[][] beamSegments;Player[] beamHeads;
        int oldC,oldR,oldTargetColor;Vector2Int oldOrigin,oldRainSeekerTarget;ReviewKind oldKind;float oldPitch,time;bool oldBlockers,oldRocketVertical;
        Vector3 Position(float x,float y)=>new Vector3((x-(columns-1)*.5f)*cellPitch,(y-(rows-1)*.5f)*cellPitch,0);
        Player Make(string label,int atlas,int order)
        {
            var go=new GameObject(label);go.transform.SetParent(content,false);var p=go.AddComponent<Player>();p.playOnEnable=false;p.returnToIdle=false;
            p.atlas=atlases[atlas];p.manifest=manifests[atlas];p.unlitMaterial=spriteMaterial;p.sortingOrder=order;p.Initialize();return p;
        }
        SpriteRenderer MakeSprite(string name,Sprite sprite,int order)
        {
            var go=new GameObject(name);go.transform.SetParent(content,false);var sr=go.AddComponent<SpriteRenderer>();sr.sprite=sprite;sr.sharedMaterial=spriteMaterial;sr.sortingOrder=order;go.transform.localScale=Vector3.one*cellPitch;return sr;
        }
        public ReviewPlan CurrentPlan => plan;
        public Camera PreviewCamera => previewCamera;
        public void SetBoardVisible(bool visible){if(content!=null)content.gameObject.SetActive(visible);}
        public void FitPreviewCamera(){if(previewCamera!=null)previewCamera.orthographicSize=.5f*cellPitch*Mathf.Max(rows+3.8f,(columns+3.0f)/previewCamera.aspect);}
        /// <summary>Start one of the four Golden combinations on this configured board.</summary>
        public void PlayGoldenCombination(ReviewKind combination,Vector2Int cell,bool vertical=false,int color=-1)
        {
            if((int)combination<17||(int)combination>20)throw new ArgumentOutOfRangeException(nameof(combination));
            kind=combination;origin=cell;rocketVertical=vertical;targetColor=color;play=true;Rebuild();
        }
        [ContextMenu("Restart animation")]
        public void Restart(){Rebuild();}
        void Start(){if(plan==null)Rebuild();}
        public void Rebuild()
        {
            columns=Mathf.Clamp(columns,3,15);rows=Mathf.Clamp(rows,3,15);cellPitch=Mathf.Max(.1f,cellPitch);
            if(atlases==null||atlases.Length!=42||manifests==null||manifests.Length!=42||referenceTiles==null||referenceTiles.Length!=6)throw new InvalidOperationException("The power-up playback package requires the supplied 42 atlas bindings and six approved tiles.");
            if((kind==ReviewKind.RainbowOrb||kind==ReviewKind.RainbowRocket||kind==ReviewKind.RainbowBomb||kind==ReviewKind.DoubleRainbow||kind==ReviewKind.RainSeeker||kind==ReviewKind.RainSeekerRocket||kind==ReviewKind.RainSeekerBomb||kind==ReviewKind.DoubleRainSeeker||kind==ReviewKind.OrbRainSeeker||kind==ReviewKind.GoldenSeeker||(int)kind>=17)&&tileGlowMaterial==null)throw new InvalidOperationException("Assign the supplied OrbTileGlow material.");
            if(content!=null){content.gameObject.SetActive(false);Destroy(content.gameObject);}
            plan=ReviewPlan.Build(columns,rows,(int)kind,origin,showBlockers,targetColor,seekerTarget,rocketVertical);content=new GameObject("M07 2D review").transform;content.SetParent(transform,false);
            if(white==null){whiteTexture=new Texture2D(1,1);whiteTexture.SetPixel(0,0,Color.white);whiteTexture.Apply();white=Sprite.Create(whiteTexture,new Rect(0,0,1,1),new Vector2(.5f,.5f),1);}
            for(int y=0;y<rows;y++)for(int x=0;x<columns;x++){var cell=MakeSprite("Cell",white,0);cell.transform.localPosition=Position(x,y);cell.color=(x+y)%2==0?new Color(.55f,.67f,.72f):new Color(.51f,.63f,.68f);}
            var maskGo=new GameObject("Refill clip");maskGo.transform.SetParent(content,false);maskGo.transform.localScale=new Vector3(columns*cellPitch,rows*cellPitch,1);
            var mask=maskGo.AddComponent<SpriteMask>();mask.sprite=white;mask.isCustomRangeActive=true;mask.frontSortingOrder=15;mask.backSortingOrder=5;
            tiles=new SpriteRenderer[plan.tiles.Length];crates=new Player[plan.tiles.Length];
            for(int i=0;i<tiles.Length;i++)
            {
                var tile=plan.tiles[i];tiles[i]=MakeSprite("Tile",referenceTiles[tile.tile],10);tiles[i].maskInteraction=SpriteMaskInteraction.VisibleInsideMask;if((kind==ReviewKind.RainbowOrb||kind==ReviewKind.RainbowRocket||kind==ReviewKind.RainbowBomb||kind==ReviewKind.DoubleRainbow||kind==ReviewKind.RainSeeker||kind==ReviewKind.RainSeekerRocket||kind==ReviewKind.RainSeekerBomb||kind==ReviewKind.DoubleRainSeeker||kind==ReviewKind.OrbRainSeeker||kind==ReviewKind.GoldenSeeker||(int)kind>=17))tiles[i].sharedMaterial=tileGlowMaterial;
                if(tile.wood){crates[i]=Make("Crate",11,11);crates[i].Sample("CrateIdle",0);crates[i].Renderer.maskInteraction=SpriteMaskInteraction.VisibleInsideMask;crates[i].transform.localPosition=Position(tile.x,tile.y);crates[i].transform.localScale=Vector3.one*cellPitch;}
            }
            fx=new Player[plan.effects.Length];for(int i=0;i<fx.Length;i++)fx[i]=Make(plan.effects[i].clip,plan.effects[i].atlas,plan.effects[i].order);
            int beamCount=plan.beams==null?0:plan.beams.Length;beamSegments=new Player[beamCount][];beamHeads=new Player[beamCount];
            for(int i=0;i<beamCount;i++){beamSegments[i]=new Player[1];for(int j=0;j<1;j++)beamSegments[i][j]=Make("Orb link",20,16);beamHeads[i]=Make("Orb packet",20,18);}
            powers=new Player[plan.powers.Length];for(int i=0;i<powers.Length;i++)powers[i]=Make("Power-up",plan.powers[i].atlas,20);
            if(createPreviewCamera&&previewCamera==null){var go=new GameObject("M07 Preview Camera");go.transform.SetParent(transform,false);go.transform.localPosition=new Vector3(0,0,-10);previewCamera=go.AddComponent<Camera>();previewCamera.orthographic=true;previewCamera.clearFlags=CameraClearFlags.SolidColor;previewCamera.backgroundColor=new Color(.08f,.16f,.20f);}
            oldC=columns;oldR=rows;oldTargetColor=targetColor;oldOrigin=origin;oldRainSeekerTarget=seekerTarget;oldKind=kind;oldPitch=cellPitch;oldBlockers=showBlockers;oldRocketVertical=rocketVertical;time=0;Sample(0);
        }
        public void Sample(float t)
        {
            if(plan==null)return;
            for(int i=0;i<tiles.Length;i++)
            {
                var tile=plan.tiles[i];float disappear=tile.convertedAt>=0?tile.convertedAt:tile.hit,age=t-disappear,alpha=disappear>=0&&age>=0?1-Mathf.SmoothStep(0,1,age/.035f):1;
                tiles[i].enabled=!tile.wood&&!tile.reserved&&alpha>0&&(!tile.incoming||t>=tile.fallStart);
                float glow=plan.TargetGlow(tile,t);tiles[i].GetPropertyBlock(tileLight);tileLight.SetFloat("_Glow",glow);tiles[i].SetPropertyBlock(tileLight);
                tiles[i].color=new Color(1,1,1,alpha);tiles[i].transform.localPosition=Position(tile.x,ReviewPlan.FallY(tile,t));
                tiles[i].transform.localScale=Vector3.one*cellPitch*(1+.045f*glow)*(tile.hit>=0&&age>=0&&age<.05f?1+.12f*Mathf.Sin(age/.05f*Mathf.PI):1);
                if(crates[i]!=null){crates[i].transform.localPosition=Position(tile.x,ReviewPlan.FallY(tile,t));crates[i].Renderer.enabled=alpha>0;crates[i].Renderer.color=new Color(1,1,1,alpha);}
            }
            for(int i=0;i<fx.Length;i++)
            {
                var e=plan.effects[i];float age=t-e.start;bool visible=age>=0&&age<e.duration;fx[i].Renderer.enabled=visible;if(!visible)continue;
                fx[i].Sample(e.clip,age);var transformSample=plan.EffectTransform(e,age);
                fx[i].transform.localPosition=Position(transformSample.x,transformSample.y);
                fx[i].transform.localRotation=Quaternion.Euler(0,0,plan.EffectAngle(e,age));fx[i].transform.localScale=Vector3.one*cellPitch*transformSample.z;
                float opacity=e.ramp>0?Mathf.SmoothStep(0,1,age/e.ramp):1;if(e.clip=="OR_Target")opacity*=1-Mathf.SmoothStep(0,1,(age-(e.duration-.08f))/.08f);if(e.clip=="OR_Orbit"||e.clip=="OR_SpinStars"||e.clip=="DO_SpinLight"||e.clip=="DO_SpinStars")opacity*=1-Mathf.SmoothStep(0,1,(age-(e.duration-.075f))/.075f);if(e.fadeOut>0)opacity*=1-Mathf.SmoothStep(0,1,(age-(e.duration-e.fadeOut))/e.fadeOut);fx[i].Renderer.color=new Color(1,1,1,opacity);
            }
            for(int i=0;i<beamHeads.Length;i++)
            {
                var b=plan.beams[i];float age=t-b.start;bool visible=age>=0&&t<b.end;
                float progress=Mathf.Clamp01(age/b.travel),alpha=(1-Mathf.SmoothStep(0,1,(age-b.travel-.025f)/.16f))*(1-Mathf.SmoothStep(0,1,(t-(b.end-.04f))/.04f));
                for(int j=0;j<1;j++)
                {
                    var p=beamSegments[i][j];Vector2 a=ReviewPlan.BeamPoint(b,progress*j),q=ReviewPlan.BeamPoint(b,progress*(j+1));float length=Vector2.Distance(a,q);p.Renderer.enabled=visible&&length>=.001f;if(!p.Renderer.enabled)continue;
                    p.Sample("OR_Link",age);var mid=(a+q)*.5f;p.transform.localPosition=Position(mid.x,mid.y);p.transform.localRotation=Quaternion.Euler(0,0,Mathf.Atan2(q.y-a.y,q.x-a.x)*Mathf.Rad2Deg);p.transform.localScale=new Vector3(length,1,1)*cellPitch;p.Renderer.color=new Color(1,1,1,alpha);
                }
                var head=beamHeads[i];head.Renderer.enabled=visible&&age<b.travel;if(head.Renderer.enabled){head.Sample("OR_Packet",age);var point=ReviewPlan.BeamPoint(b,progress);head.transform.localPosition=Position(point.x,point.y);head.transform.localScale=Vector3.one*cellPitch;head.transform.localRotation=Quaternion.Euler(0,0,Mathf.Atan2(b.targetY-b.y,b.targetX-b.x)*Mathf.Rad2Deg);}
            }
            for(int i=0;i<powers.Length;i++)
            {
                var p=plan.powers[i];float charge=p.charge>0?Mathf.Clamp01((t-(p.end-p.charge))/p.charge):0;
                powers[i].Sample(charge>0?"Charge":"Idle",charge*.4f);float appear=p.begin>0?Mathf.SmoothStep(0,1,(t-p.begin)/.12f):1;powers[i].Renderer.enabled=t>=p.begin&&t<p.end;powers[i].Renderer.color=new Color(1,1,1,appear);powers[i].transform.localPosition=Position(p.x,p.y);powers[i].transform.localScale=Vector3.one*cellPitch*(1+.13f*charge)*(.15f+.85f*appear);
            }
            float recoil=0;
            if(enableRecoil)
            {
                foreach(var blast in plan.blasts){float a=t-blast.start;if(a>=0&&a<.16f)recoil+=.04f*blast.scale*Mathf.Exp(-20*a)*Mathf.Cos(65*a);}
                if(kind==ReviewKind.RocketThenBomb||kind==ReviewKind.RocketHorizontal||kind==ReviewKind.RocketVertical){float a=t-plan.primary;if(a>=0&&a<.16f)recoil+=.025f*Mathf.Exp(-20*a)*Mathf.Cos(65*a);}
            }
            content.localPosition=new Vector3(recoil,recoil*.5f,0)*cellPitch;
        }
        void Update()
        {
            if(oldC!=columns||oldR!=rows||oldTargetColor!=targetColor||oldOrigin!=origin||oldRainSeekerTarget!=seekerTarget||oldKind!=kind||oldPitch!=cellPitch||oldBlockers!=showBlockers||oldRocketVertical!=rocketVertical)Rebuild();
            if(!externallyDriven){if(play)time=(time+Time.deltaTime)%plan.duration;Sample(play?time:scrubTime);}
            FitPreviewCamera();
        }
        void OnDestroy(){if(white!=null)Destroy(white);if(whiteTexture!=null)Destroy(whiteTexture);}
    }
}
