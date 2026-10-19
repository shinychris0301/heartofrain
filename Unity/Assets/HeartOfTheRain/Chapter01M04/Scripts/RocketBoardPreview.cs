using UnityEngine;

namespace HeartOfTheRain.M04
{
    /// <summary>Asset review harness, not a game controller. All visible elements use SpriteRenderer.</summary>
    public sealed class RocketBoardPreview : MonoBehaviour
    {
        [Range(3, 15)] public int columns = 9, rows = 11;
        [Min(.1f)] public float cellPitch = 1;
        [Min(1)] public float cellsPerSecond = 10;
        public bool vertical = true;
        public bool createPreviewCamera = true;
        public Texture2D verticalAtlas, horizontalAtlas;
        public TextAsset verticalManifest, horizontalManifest;
        public Material spriteMaterial, glowMaterial;
        public Sprite[] referenceTiles;

        Transform content;
        Sprite white;
        Texture2D whiteTexture;
        SpriteRenderer[,] tiles;
        SpriteRenderer[] flashes;
        SpriteRenderer glow, core;
        RocketSpritePlayer forward, backward;
        Camera previewCamera;
        int oldColumns, oldRows, phase = -1;
        float oldPitch, time;
        bool oldVertical;

        public static Vector3 CellPosition(int x, int y, int width, int height, float pitch)
            => new Vector3((x - (width - 1) * .5f) * pitch, (y - (height - 1) * .5f) * pitch, 0);

        public static int[,] MakeLayout(int width, int height)
        {
            var layout=new int[width,height]; var counts=new int[6]; uint seed=24011;
            for (int y=0;y<height;y++) for (int x=0;x<width;x++)
            {
                seed=unchecked(seed*1664525u+1013904223u); int start=(int)(seed%6), chosen=-1;
                for (int j=0;j<6;j++)
                {
                    int k=(start+j)%6;
                    if ((x>=2 && layout[x-1,y]==k && layout[x-2,y]==k) ||
                        (y>=2 && layout[x,y-1]==k && layout[x,y-2]==k)) continue;
                    if (chosen<0 || counts[k]<counts[chosen]) chosen=k;
                }
                layout[x,y]=chosen; counts[chosen]++;
            }
            return layout;
        }

        SpriteRenderer MakeSprite(string label, Sprite sprite, Vector3 position, Vector3 scale, Color color, int order, Material material)
        {
            var go = new GameObject(label); go.transform.SetParent(content, false);
            go.transform.localPosition = position; go.transform.localScale = scale;
            var sr = go.AddComponent<SpriteRenderer>(); sr.sprite = sprite;
            sr.color = color; sr.sortingOrder = order; sr.sharedMaterial = material;
            return sr;
        }

        RocketSpritePlayer MakeRocket(string label)
        {
            var go = new GameObject(label); go.SetActive(false); go.transform.SetParent(content, false);
            var player = go.AddComponent<RocketSpritePlayer>();
            player.atlas = vertical ? verticalAtlas : horizontalAtlas;
            player.manifest = vertical ? verticalManifest : horizontalManifest;
            player.unlitMaterial = spriteMaterial; player.playOnEnable = false;
            player.returnToIdle = false; go.transform.localScale = Vector3.one * cellPitch;
            player.Initialize(); go.SetActive(true); return player;
        }

        void Start()
        {
            if (referenceTiles == null || referenceTiles.Length < 6 || spriteMaterial == null || glowMaterial == null ||
                verticalAtlas == null || horizontalAtlas == null || verticalManifest == null || horizontalManifest == null)
            { Debug.LogError("M04 demo requires both rocket atlases, manifests, materials, and six tile sprites.", this); enabled = false; return; }
            whiteTexture = new Texture2D(1, 1, TextureFormat.RGBA32, false);
            whiteTexture.SetPixel(0, 0, Color.white); whiteTexture.Apply();
            white = Sprite.Create(whiteTexture, new Rect(0, 0, 1, 1), new Vector2(.5f,.5f), 1);
            if (createPreviewCamera)
            {
                var go = new GameObject("M04 Preview Camera"); go.transform.SetParent(transform, false);
                previewCamera = go.AddComponent<Camera>(); previewCamera.orthographic = true;
                previewCamera.clearFlags = CameraClearFlags.SolidColor;
                previewCamera.backgroundColor = new Color(.055f,.12f,.15f);
                go.transform.localPosition = new Vector3(0,0,-10);
            }
            Rebuild();
        }

        void Rebuild()
        {
            if (content != null) { content.gameObject.SetActive(false); Destroy(content.gameObject); }
            columns = Mathf.Clamp(columns, 3, 15); rows = Mathf.Clamp(rows, 3, 15); cellPitch = Mathf.Max(.1f, cellPitch);
            content = new GameObject("2D Board Assets").transform; content.SetParent(transform, false);
            tiles = new SpriteRenderer[columns,rows];
            var layout=MakeLayout(columns,rows);
            MakeSprite("Board Rim", white, Vector3.zero, new Vector3(columns+.28f,rows+.28f,1)*cellPitch,
                new Color(.68f,.55f,.33f), -2, spriteMaterial);
            for (int y = 0; y < rows; y++) for (int x = 0; x < columns; x++)
            {
                var position = CellPosition(x,y,columns,rows,cellPitch);
                MakeSprite("Cell",white,position,new Vector3(.985f,.985f,1)*cellPitch,
                    (x+y)%2==0 ? new Color(.47f,.61f,.68f) : new Color(.44f,.58f,.65f),-1,spriteMaterial);
                int index = layout[x,y];
                tiles[x,y] = MakeSprite("Tile",referenceTiles[index],position,Vector3.one*cellPitch,Color.white,0,spriteMaterial);
            }
            forward = MakeRocket("Rocket Forward"); backward = MakeRocket("Rocket Reverse");
            backward.Renderer.flipX = !vertical; backward.Renderer.flipY = vertical;
            glow = MakeSprite("Clear Glow",white,Vector3.zero,Vector3.one,Color.clear,10,glowMaterial);
            core = MakeSprite("Clear Core",white,Vector3.zero,Vector3.one,Color.clear,11,glowMaterial);
            flashes = new SpriteRenderer[vertical ? rows : columns];
            for (int i=0;i<flashes.Length;i++) flashes[i]=MakeSprite("Cell Impact",white,Vector3.zero,Vector3.one,Color.clear,12,glowMaterial);
            oldColumns=columns; oldRows=rows; oldPitch=cellPitch; oldVertical=vertical;
            time=0; phase=-1;
        }

        void Update()
        {
            if (content == null) return;
            if (oldColumns!=columns || oldRows!=rows || oldPitch!=cellPitch || oldVertical!=vertical) Rebuild();
            if (previewCamera != null)
                previewCamera.orthographicSize=.5f*cellPitch*Mathf.Max(rows+1.2f,(columns+1.2f)/previewCamera.aspect);
            time+=Time.deltaTime;
            int ox=columns/2, oy=rows/2;
            float endDistance=Mathf.Max(vertical ? oy : ox,vertical ? rows-1-oy : columns-1-ox)+1;
            float flightDuration=endDistance/Mathf.Max(1,cellsPerSecond);
            float cycle=1.8f+flightDuration+1.1f;
            if (time>=cycle) { time%=cycle; phase=-1; }
            int next=time<.6f?0:time<1.4f?1:time<1.8f?2:time<1.8f+flightDuration?3:4;
            if (next!=phase)
            {
                phase=next;
                if (phase<3) forward.Play(phase==0?"Create":phase==1?"DepthTurn":"Charge");
                if (phase==3) { forward.Play("Flight"); backward.Play("Flight"); }
            }
            var origin=CellPosition(ox,oy,columns,rows,cellPitch);
            var axis=vertical?Vector3.up:Vector3.right;
            float distance=Mathf.Max(0,time-1.8f)*Mathf.Max(1,cellsPerSecond);
            float plusEdge=(vertical?rows-1-oy:columns-1-ox)+.7f;
            float minusEdge=(vertical?oy:ox)+.7f;
            forward.Renderer.enabled=phase<3 || (phase==3 && distance<plusEdge);
            backward.Renderer.enabled=phase==3 && distance<minusEdge;
            forward.transform.localPosition=origin+axis*(phase>=3?distance*cellPitch:0);
            backward.transform.localPosition=origin-axis*distance*cellPitch;
            float positive=Mathf.Min(distance,plusEdge), negative=Mathf.Min(distance,minusEdge);
            float span=(positive+negative)*cellPitch;
            var center=origin+axis*((positive-negative)*.5f*cellPitch);
            float fade=phase<3?0:Mathf.Clamp01(1-Mathf.Max(0,time-1.8f-flightDuration)/.25f);
            glow.transform.localPosition=core.transform.localPosition=center;
            glow.transform.localScale=vertical?new Vector3(.95f*cellPitch,span,1):new Vector3(span,.95f*cellPitch,1);
            core.transform.localScale=vertical?new Vector3(.24f*cellPitch,span,1):new Vector3(span,.24f*cellPitch,1);
            glow.color=new Color(1,.55f,.08f,.9f*fade); core.color=new Color(1,.96f,.72f,fade);
            for (int y=0;y<rows;y++) for (int x=0;x<columns;x++)
            {
                bool centerCell=x==ox && y==oy;
                bool line=vertical?x==ox:y==oy;
                float age=time-1.8f-Mathf.Abs(vertical?y-oy:x-ox)/Mathf.Max(1,cellsPerSecond);
                float pop=line && age>=0 ? Mathf.Clamp01(age/.18f) : 0;
                tiles[x,y].enabled=!centerCell && pop<1;
                tiles[x,y].color=new Color(1,1,1,1-pop);
                tiles[x,y].transform.localScale=Vector3.one*cellPitch*(1+.15f*Mathf.Sin(pop*Mathf.PI));
            }
            for (int i=0;i<flashes.Length;i++)
            {
                float age=time-1.8f-Mathf.Abs(i-(vertical?oy:ox))/Mathf.Max(1,cellsPerSecond);
                float pulse=age>=0 && age<.24f ? 1-age/.24f : 0;
                flashes[i].transform.localPosition=CellPosition(vertical?ox:i,vertical?i:oy,columns,rows,cellPitch);
                flashes[i].transform.localScale=Vector3.one*cellPitch*(1.5f-.5f*pulse);
                flashes[i].color=new Color(1,.85f,.35f,pulse);
            }
        }

        void OnDestroy()
        {
            if (white!=null) Destroy(white);
            if (whiteTexture!=null) Destroy(whiteTexture);
        }
    }
}
