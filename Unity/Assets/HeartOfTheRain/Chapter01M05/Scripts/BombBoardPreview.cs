using UnityEngine;
using RocketPlayer = HeartOfTheRain.M04.RocketSpritePlayer;
using BoardLayout = HeartOfTheRain.M04.RocketBoardPreview;

namespace HeartOfTheRain.M05
{
    /// <summary>2D asset demonstration only. No match detection, score, refill, or game-state ownership.</summary>
    public sealed class BombBoardPreview : MonoBehaviour
    {
        [Range(3,15)] public int columns=9,rows=9;
        [Min(.1f)] public float cellPitch=1;
        [Min(1)] public float cellsPerSecond=20;
        public BlastKind effect=BlastKind.Bomb;
        public Vector2Int origin=new Vector2Int(-1,-1);
        [Range(1,4)] public int bombRadius=2,doubleBombRadius=3;
        [Range(0,2)] public int rocketBandHalfWidth=1;
        public Texture2D bombAtlas,fxAtlas,verticalAtlas,horizontalAtlas,comboBombAtlas,comboRocketAtlas,detailAtlas,blockerAtlas;
        public TextAsset bombManifest,fxManifest,verticalManifest,horizontalManifest,comboBombManifest,comboRocketManifest,detailManifest,blockerManifest;
        public bool showBlockers=false;
        public Material spriteMaterial,glowMaterial;
        public Sprite[] referenceTiles;
        public bool createPreviewCamera=true;
        public bool enableBoardRecoil=true;

        Transform content; Camera previewCamera; Texture2D whiteTexture; Sprite white;
        SpriteRenderer[,] tiles,flashes;
        RenderedSpritePlayer[,] tileBreakup,tileSpark;
        int[,] tileIndices;
        bool[,] blockers; bool oldShowBlockers;
        RenderedSpritePlayer bomb,secondBomb,combo;
        SpriteRenderer chargeGlow;
        const float MergeStart=1f, HoldStart=1.6f, Detonation=52f/30f;
        RenderedSpritePlayer[] layers;
        RocketPlayer mergeRocket;
        RocketPlayer[] rockets;
        SpriteRenderer[] beams,cores;
        int ox,oy,partnerX,phase=-1,oldColumns,oldRows,oldBand;
        float time,oldPitch; BlastKind oldEffect; Vector2Int oldOrigin;

        Vector3 Cell(int x,int y)=>BoardLayout.CellPosition(x,y,columns,rows,cellPitch);
        bool IsBlocker(int x,int y)
        {
            int dx=x-ox,dy=y-oy;
            return showBlockers && ((dy==-1 && dx>=-2 && dx<=0)||(dx==-2 && dy>=0 && dy<=1)||(dx==-1 && dy==0));
        }
        SpriteRenderer Sprite(string name,Sprite image,Vector3 p,Vector3 scale,Color color,int order,Material mat)
        {
            var go=new GameObject(name);go.transform.SetParent(content,false);go.transform.localPosition=p;go.transform.localScale=scale;
            var sr=go.AddComponent<SpriteRenderer>();sr.sprite=image;sr.color=color;sr.sortingOrder=order;sr.sharedMaterial=mat;return sr;
        }
        RenderedSpritePlayer Player(string name,Texture2D atlas,TextAsset manifest,int order)
        {
            var go=new GameObject(name);go.SetActive(false);go.transform.SetParent(content,false);
            var p=go.AddComponent<RenderedSpritePlayer>();p.atlas=atlas;p.manifest=manifest;p.unlitMaterial=spriteMaterial;
            p.playOnEnable=false;p.returnToIdle=false;p.sortingOrder=order;p.Initialize();go.SetActive(true);return p;
        }
        RocketPlayer Rocket(string name,bool vertical)
        {
            var go=new GameObject(name);go.SetActive(false);go.transform.SetParent(content,false);
            var p=go.AddComponent<RocketPlayer>();p.atlas=vertical?verticalAtlas:horizontalAtlas;
            p.manifest=vertical?verticalManifest:horizontalManifest;p.unlitMaterial=spriteMaterial;
            p.playOnEnable=false;p.returnToIdle=false;p.sortingOrder=25;p.Initialize();go.SetActive(true);
            go.transform.localScale=Vector3.one*cellPitch;return p;
        }
        void Start()
        {
            if (referenceTiles==null || referenceTiles.Length<6 || bombAtlas==null || fxAtlas==null ||
                detailAtlas==null || detailManifest==null || blockerAtlas==null || blockerManifest==null || comboBombAtlas==null || comboRocketAtlas==null || comboBombManifest==null || comboRocketManifest==null || bombManifest==null || fxManifest==null || verticalAtlas==null || horizontalAtlas==null ||
                verticalManifest==null || horizontalManifest==null || spriteMaterial==null || glowMaterial==null)
            { Debug.LogError("M05 preview requires the supplied bomb, FX, rocket, material, and tile references.",this);enabled=false;return; }
            whiteTexture=new Texture2D(1,1,TextureFormat.RGBA32,false);whiteTexture.SetPixel(0,0,Color.white);whiteTexture.Apply();
            white=UnityEngine.Sprite.Create(whiteTexture,new Rect(0,0,1,1),new Vector2(.5f,.5f),1);
            if (createPreviewCamera)
            {
                var go=new GameObject("M05 Preview Camera");go.transform.SetParent(transform,false);go.transform.localPosition=new Vector3(0,0,-10);
                previewCamera=go.AddComponent<Camera>();previewCamera.orthographic=true;previewCamera.clearFlags=CameraClearFlags.SolidColor;
                previewCamera.backgroundColor=new Color(.055f,.12f,.15f);
            }
            Rebuild();
        }
        void Rebuild()
        {
            if (content!=null){content.gameObject.SetActive(false);Destroy(content.gameObject);}
            columns=Mathf.Clamp(columns,3,15);rows=Mathf.Clamp(rows,3,15);cellPitch=Mathf.Max(.1f,cellPitch);
            content=new GameObject("2D Bomb Asset Board").transform;content.SetParent(transform,false);
            ox=origin.x<0?columns/2:Mathf.Clamp(origin.x,0,columns-1);oy=origin.y<0?rows/2:Mathf.Clamp(origin.y,0,rows-1);
            partnerX=ox+1<columns?ox+1:ox-1;
            Sprite("Rim",white,Vector3.zero,new Vector3(columns+.28f,rows+.28f,1)*cellPitch,new Color(.68f,.55f,.33f),-2,spriteMaterial);
            var layout=BoardLayout.MakeLayout(columns,rows);tileIndices=layout;
            tiles=new SpriteRenderer[columns,rows];flashes=new SpriteRenderer[columns,rows];
            tileBreakup=new RenderedSpritePlayer[columns,rows];tileSpark=new RenderedSpritePlayer[columns,rows];
            blockers=new bool[columns,rows];
            for(int y=0;y<rows;y++)for(int x=0;x<columns;x++)
            {
                Sprite("Cell",white,Cell(x,y),new Vector3(.985f,.985f,1)*cellPitch,(x+y)%2==0?new Color(.47f,.61f,.68f):new Color(.44f,.58f,.65f),-1,spriteMaterial);
                tiles[x,y]=Sprite("Tile",referenceTiles[layout[x,y]],Cell(x,y),Vector3.one*cellPitch,Color.white,0,spriteMaterial);
                flashes[x,y]=Sprite("Impact",white,Cell(x,y),Vector3.one*cellPitch,Color.clear,12,glowMaterial);
                blockers[x,y]=IsBlocker(x,y);
                tileBreakup[x,y]=Player("Cell Debris",blockers[x,y]?blockerAtlas:detailAtlas,blockers[x,y]?blockerManifest:detailManifest,blockers[x,y]?40:34);
                tileSpark[x,y]=Player("Tile Impact Spark",fxAtlas,fxManifest,36);
                tileSpark[x,y].transform.localPosition=Cell(x,y);
                float variation=(x*43+y*71)%360;
                tileBreakup[x,y].transform.localRotation=Quaternion.Euler(0,0,variation);
                tileSpark[x,y].transform.localRotation=Quaternion.Euler(0,0,variation);
            }
            bomb=Player("Bomb",bombAtlas,bombManifest,20);secondBomb=Player("Second Bomb",bombAtlas,bombManifest,20);
            bomb.transform.localScale=secondBomb.transform.localScale=Vector3.one*cellPitch;
            mergeRocket=Rocket("Merge Rocket",false);
            combo=Player("Combined Form",effect==BlastKind.BombBomb?comboBombAtlas:comboRocketAtlas,
                effect==BlastKind.BombBomb?comboBombManifest:comboRocketManifest,22);
            combo.transform.localScale=Vector3.one*cellPitch;
            chargeGlow=Sprite("Charge Glow",white,Vector3.zero,Vector3.one,Color.clear,15,glowMaterial);
            layers=new[]{Player("Broad White Blast",fxAtlas,fxManifest,30),Player("Pressure Front",fxAtlas,fxManifest,31),Player("Second Pressure Front",fxAtlas,fxManifest,32)};
            int bands=2*rocketBandHalfWidth+1;rockets=new RocketPlayer[bands*4];beams=new SpriteRenderer[bands*2];cores=new SpriteRenderer[bands*2];
            for(int i=0;i<bands*2;i++)
            {
                bool v=i>=bands;rockets[i*2]=Rocket("Rocket +",v);rockets[i*2+1]=Rocket("Rocket -",v);
                rockets[i*2+1].Renderer.flipY=v;rockets[i*2+1].Renderer.flipX=!v;
                beams[i]=Sprite("Lane Glow",white,Vector3.zero,Vector3.one,Color.clear,8,glowMaterial);
                cores[i]=Sprite("Lane Core",white,Vector3.zero,Vector3.one,Color.clear,9,glowMaterial);
            }
            oldColumns=columns;oldRows=rows;oldPitch=cellPitch;oldEffect=effect;oldOrigin=origin;oldBand=rocketBandHalfWidth;oldShowBlockers=showBlockers;
            phase=-1;time=0;
        }
        void Update()
        {
            if(content==null)return;
            if(oldColumns!=columns || oldRows!=rows || oldPitch!=cellPitch || oldEffect!=effect || oldOrigin!=origin || oldBand!=rocketBandHalfWidth || oldShowBlockers!=showBlockers)Rebuild();
            if(previewCamera!=null)previewCamera.orthographicSize=.5f*cellPitch*Mathf.Max(rows+1.3f,(columns+1.3f)/previewCamera.aspect);
            float speed=Mathf.Max(1,cellsPerSecond);float duration=3.0f+Mathf.Max(columns,rows)/speed;
            time+=Time.deltaTime;if(time>=duration){time%=duration;phase=-1;}
            int next=time<MergeStart?0:time<HoldStart?1:time<Detonation?2:3;
            if(next!=phase){phase=next;if(phase==0)mergeRocket.Play("Idle");if(phase==3)foreach(var rocket in rockets)rocket.Play("Flight");}
            bool combination=effect!=BlastKind.Bomb;
            Vector3 center=Cell(ox,oy);float e=time-Detonation;
            string normal=time<.6f?"Create":time<Detonation-.2f?"Idle":time<Detonation?"Charge":"Detonate";
            float normalTime=time<.6f?time:time<Detonation-.2f?0:time<Detonation?time-(Detonation-.2f):e;
            float anticipation=!combination && time<Detonation?Mathf.SmoothStep(0,1,(time-(Detonation-.2f))/.2f):0;
            bomb.transform.localScale=Vector3.one*cellPitch*(1+.12f*anticipation);
            bomb.Sample(normal,normalTime);secondBomb.Sample(normal,normalTime);
            bomb.transform.localPosition=center;secondBomb.transform.localPosition=mergeRocket.transform.localPosition=Cell(partnerX,oy);
            bomb.Renderer.enabled=!(combination && time>=MergeStart) && time<Detonation+1f/30f;
            secondBomb.Renderer.enabled=effect==BlastKind.BombBomb && time<MergeStart;
            mergeRocket.Renderer.enabled=effect==BlastKind.RocketBomb && time<MergeStart;
            if(combination && time>=MergeStart)
                combo.Sample(time<HoldStart?(partnerX>ox?"Merge_Right":"Merge_Left"):time<Detonation?"Armed":"Release",
                    time<HoldStart?time-MergeStart:time<Detonation?0:e);
            else combo.Renderer.enabled=false;
            if(time>=Detonation+1f/30f)combo.Renderer.enabled=false;
            combo.transform.localPosition=center;
            float charge=combination && time>=MergeStart && time<Detonation?Mathf.SmoothStep(0,1,(time-MergeStart)/.6f):anticipation;
            chargeGlow.transform.localPosition=center;chargeGlow.transform.localScale=Vector3.one*cellPitch*(1.4f+1.9f*charge);
            chargeGlow.color=new Color(1,.68f,.18f,.65f*charge*charge);
            float radius=effect==BlastKind.BombBomb?doubleBombRadius:bombRadius;
            float fxScale=effect==BlastKind.BombBomb?1.4f*doubleBombRadius/3f:effect==BlastKind.RocketBomb?1.1f:bombRadius/2f;
            float amplitude=effect==BlastKind.BombBomb ? .085f:effect==BlastKind.RocketBomb ? .065f:.045f;
            float recoil=enableBoardRecoil && e>=0 && e<.2f?amplitude*Mathf.Exp(-16*e)*Mathf.Cos(55*e):0;
            content.localPosition=new Vector3(recoil,recoil*.65f,0)*cellPitch;
            for(int i=0;i<layers.Length;i++)
            {
                float delay=i==2 ? .14f:i==1 ? .06f:0;
                float age=e-delay;float rate=effect==BlastKind.BombBomb ? .85f : 1f;
                layers[i].Sample(i==0?"Burst":"Wave",Mathf.Max(0,age)*rate);
                layers[i].Renderer.enabled=age>=0 && age*rate<(i==0?22f/60f:16f/30f) && (i!=2 || effect==BlastKind.BombBomb);
                layers[i].transform.localPosition=center;
                float size=i==2?1.13f:1;
                layers[i].transform.localScale=Vector3.one*cellPitch*fxScale*size;
            }
            for(int y=0;y<rows;y++)for(int x=0;x<columns;x++)
            {
                bool hit=BlastPattern.Affected(x,y,ox,oy,columns,rows,effect,bombRadius,doubleBombRadius,rocketBandHalfWidth);
                float age=e-BlastPattern.Arrival(x,y,ox,oy,effect,speed,rocketBandHalfWidth);
                float pop=hit && age>=0?Mathf.Clamp01(age/(2f/30f)):0;
                bool reserved=(x==ox && y==oy)||(combination && x==partnerX && y==oy);
                tiles[x,y].enabled=!blockers[x,y] && !reserved && pop<1;tiles[x,y].color=new Color(1,1,1,1-pop);
                tiles[x,y].transform.localScale=Vector3.one*cellPitch*(1+.22f*Mathf.Sin(pop*Mathf.PI));
                float flash=hit && age>=0 && age<.1f?1-age/.1f:0;
                flashes[x,y].color=new Color(1,.96f,.72f,.7f*flash);
                flashes[x,y].transform.localScale=Vector3.one*cellPitch*1.2f;
                float sparkRate=1.6f+.12f*((x*7+y*3)%5);
                var spark=tileSpark[x,y];spark.Sample("Spark",Mathf.Max(0,age)*sparkRate);
                spark.Renderer.enabled=hit && age>=0 && age<6f/(30f*sparkRate);
                spark.transform.localScale=Vector3.one*cellPitch*(.32f+.035f*((x*3+y*7)%5));
                float chipAge=age-1f/60f;var chips=tileBreakup[x,y];bool wood=blockers[x,y];
                chips.Sample(wood?"CrateBreakup":"Tile"+tileIndices[x,y],Mathf.Max(0,chipAge));
                chips.Renderer.enabled=hit && !reserved && chipAge>=0 && chipAge<(wood?24f/30f:16f/30f);
                Vector3 away=(Cell(x,y)-center).normalized;
                chips.transform.localPosition=Cell(x,y)+away*cellPitch*Mathf.Clamp01(chipAge/.35f)*.6f;
                chips.transform.localScale=Vector3.one*cellPitch;
                chips.transform.localRotation=Quaternion.Euler(0,0,(x*43+y*71)%360);
                if(wood && (!hit || chipAge<0))
                {
                    chips.Sample("CrateIdle",0);chips.Renderer.enabled=!reserved;
                    chips.transform.localPosition=Cell(x,y);chips.transform.localRotation=Quaternion.identity;
                }
            }
            int bands=2*rocketBandHalfWidth+1;float distance=Mathf.Max(0,e)*speed;
            for(int i=0;i<beams.Length;i++)
            {
                bool v=i>=bands;int lane=i%bands-rocketBandHalfWidth;
                bool valid=effect==BlastKind.RocketBomb && phase==3 && (v?ox+lane>=0 && ox+lane<columns:oy+lane>=0 && oy+lane<rows);
                Vector3 start=Cell(v?ox+lane:ox,v?oy:oy+lane),axis=v?Vector3.up:Vector3.right;
                float positive=(v?rows-1-oy:columns-1-ox)+.7f,negative=(v?oy:ox)+.7f;
                rockets[i*2].Renderer.enabled=valid && distance<positive;rockets[i*2+1].Renderer.enabled=valid && distance<negative;
                rockets[i*2].transform.localPosition=start+axis*distance*cellPitch;rockets[i*2+1].transform.localPosition=start-axis*distance*cellPitch;
                float p=Mathf.Min(distance,positive),n=Mathf.Min(distance,negative),span=(p+n)*cellPitch;
                float fade=valid?Mathf.Clamp01(1-Mathf.Max(0,e-Mathf.Max(positive,negative)/speed)/.2f):0;
                beams[i].transform.localPosition=cores[i].transform.localPosition=start+axis*(p-n)*.5f*cellPitch;
                beams[i].transform.localScale=v?new Vector3(.95f*cellPitch,span,1):new Vector3(span,.95f*cellPitch,1);
                cores[i].transform.localScale=v?new Vector3(.27f*cellPitch,span,1):new Vector3(span,.27f*cellPitch,1);
                beams[i].color=new Color(1,.55f,.10f,.9f*fade);cores[i].color=new Color(1,.96f,.75f,fade);
            }
        }
        void OnDestroy(){if(white!=null)Destroy(white);if(whiteTexture!=null)Destroy(whiteTexture);}
    }
}
