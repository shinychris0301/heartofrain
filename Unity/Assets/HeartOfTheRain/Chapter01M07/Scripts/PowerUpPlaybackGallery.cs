using System;
using UnityEngine;
using HeartOfTheRain.M05;

namespace HeartOfTheRain.M07
{
    [Serializable] public class PowerUpGalleryEntry
    {
        public string id,title,group,description;public int kind,targetColor=5;
    }
    [Serializable] public class PowerUpGalleryAtlas
    {
        public int atlas;public string title;public string[] clipLabels;
    }
    [Serializable] public class PowerUpGalleryCatalog
    {
        public string revision;public PowerUpGalleryEntry[] entries;public PowerUpGalleryAtlas[] library;
    }

    /// <summary>One review surface for the frozen power-up set. Uses IMGUI and needs no UI/Input package.</summary>
    [DisallowMultipleComponent]
    public sealed class PowerUpPlaybackGallery : MonoBehaviour
    {
        public BoardReactionReview board;
        public TextAsset catalog;
        public bool playing=true,loop=true,autoAdvance;
        [Range(.25f,2)] public float speed=1;
        public int selectedEntry,selectedLibrary,selectedClip;
        PowerUpGalleryCatalog data;
        SpriteManifest clipManifest;
        RenderedSpritePlayer clipPlayer;
        float cursor;
        int mode;
        bool showLibrary;
        Vector2 scroll;
        GUIStyle titleStyle,headingStyle,bodyStyle,smallStyle,buttonStyle,selectedStyle;
        public float PlaybackTime => cursor;
        public int EntryCount => data==null?0:data.entries.Length;
        public float Duration => mode==0?(board.CurrentPlan==null?0:board.CurrentPlan.duration):
            (clipManifest==null?0:clipManifest.clips[selectedClip].Duration);
        float Scale => Mathf.Clamp(Mathf.Min(Screen.width/1280f,Screen.height/900f),.5f,2f);

        void Start()
        {
            if(board==null)board=GetComponent<BoardReactionReview>();
            if(board==null||catalog==null)throw new InvalidOperationException("Use the supplied PowerUpPlaybackGallery prefab.");
            data=JsonUtility.FromJson<PowerUpGalleryCatalog>(catalog.text);
            if(data==null||data.entries==null||data.entries.Length!=22||data.library==null||data.library.Length!=40)
                throw new InvalidOperationException("The approved gallery requires its supplied catalog.");
            board.externallyDriven=true;board.play=false;board.createPreviewCamera=true;
            SelectEntry(Mathf.Clamp(selectedEntry,0,data.entries.Length-1));
        }
        public void SelectEntry(int index)
        {
            if(data==null)return;selectedEntry=(index%data.entries.Length+data.entries.Length)%data.entries.Length;
            var e=data.entries[selectedEntry];mode=0;cursor=0;board.kind=(ReviewKind)e.kind;board.targetColor=e.targetColor;
            board.origin=new Vector2Int(-1,-1);board.seekerTarget=new Vector2Int(-1,-1);board.Rebuild();board.SetBoardVisible(true);
            if(clipPlayer!=null)clipPlayer.gameObject.SetActive(false);
        }
        public void Replay(){cursor=0;playing=true;Sample();}
        public void Seek(float seconds){cursor=Mathf.Clamp(seconds,0,Duration);playing=false;Sample();}
        public void StepFrame(int direction)
        {float fps=mode==0?60:clipManifest.clips[selectedClip].fps;Seek(cursor+direction/fps);}
        public void SetBoardSize(int columns,int rows)
        {board.columns=columns;board.rows=rows;board.Rebuild();cursor=0;board.SetBoardVisible(mode==0);}
        void SetMode(int next)
        {
            if(next==mode)return;mode=next;cursor=0;scroll=Vector2.zero;
            if(mode==0){SelectEntry(selectedEntry);return;}
            board.SetBoardVisible(false);SelectLibrary(selectedLibrary);
        }
        void SelectLibrary(int index)
        {
            selectedLibrary=Mathf.Clamp(index,0,data.library.Length-1);selectedClip=0;cursor=0;showLibrary=false;
            if(clipPlayer!=null){clipPlayer.gameObject.SetActive(false);Destroy(clipPlayer.gameObject);}
            int atlas=data.library[selectedLibrary].atlas;clipManifest=JsonUtility.FromJson<SpriteManifest>(board.manifests[atlas].text);
            var go=new GameObject("Animation preview");go.SetActive(false);go.transform.SetParent(transform,false);
            clipPlayer=go.AddComponent<RenderedSpritePlayer>();clipPlayer.playOnEnable=false;clipPlayer.returnToIdle=false;
            clipPlayer.atlas=board.atlases[atlas];clipPlayer.manifest=board.manifests[atlas];clipPlayer.unlitMaterial=board.spriteMaterial;clipPlayer.sortingOrder=60;
            clipPlayer.Initialize();go.SetActive(true);Sample();
        }
        void Next(int delta)
        {
            if(mode==0)SelectEntry(selectedEntry+delta);
            else{selectedClip=(selectedClip+delta+clipManifest.clips.Length)%clipManifest.clips.Length;cursor=0;}
        }
        void LateUpdate()
        {
            if(data==null)return;
            board.SetBoardVisible(mode==0);
            if(playing)
            {
                cursor+=Time.unscaledDeltaTime*speed;
                if(cursor>Duration+(mode==0?.40f:.25f))
                {if(autoAdvance)Next(1);else if(loop)cursor=0;else{cursor=Duration;playing=false;}}
            }
            var cam=board.PreviewCamera;
            if(cam!=null)
            {
                float w=Screen.width/Scale,h=Screen.height/Scale;
                cam.rect=new Rect(340/w,118/h,(w-356)/w,(h-306)/h);
                if(mode==0)board.FitPreviewCamera();
                else
                {
                    float canvas=clipManifest.frames[0].width/clipManifest.pixelsPerUnit;
                    cam.orthographicSize=.62f*canvas*Mathf.Max(1,1/cam.aspect);
                }
            }
            Sample();
        }
        void Sample()
        {
            if(data==null)return;
            if(mode==0)board.Sample(Mathf.Min(cursor,Duration));
            else if(clipPlayer!=null)clipPlayer.Sample(clipManifest.clips[selectedClip].name,Mathf.Min(cursor,Duration));
        }
        void Styles()
        {
            if(titleStyle!=null)return;
            titleStyle=new GUIStyle(GUI.skin.label){fontSize=28,fontStyle=FontStyle.Bold};titleStyle.normal.textColor=new Color(.96f,.96f,.91f);
            headingStyle=new GUIStyle(GUI.skin.label){fontSize=16,fontStyle=FontStyle.Bold};headingStyle.normal.textColor=new Color(.87f,.74f,.45f);
            bodyStyle=new GUIStyle(GUI.skin.label){fontSize=15,wordWrap=true};bodyStyle.normal.textColor=new Color(.91f,.94f,.93f);
            smallStyle=new GUIStyle(bodyStyle){fontSize=12};smallStyle.normal.textColor=new Color(.65f,.76f,.77f);
            buttonStyle=new GUIStyle(GUI.skin.button){fontSize=14,alignment=TextAnchor.MiddleLeft,padding=new RectOffset(12,8,6,6),wordWrap=true};
            selectedStyle=new GUIStyle(buttonStyle){fontStyle=FontStyle.Bold};selectedStyle.normal.textColor=new Color(1,.84f,.45f);
        }
        static void Fill(Rect rect,Color color){var old=GUI.color;GUI.color=color;GUI.DrawTexture(rect,Texture2D.whiteTexture);GUI.color=old;}
        void OnGUI()
        {
            if(data==null)return;Styles();var old=GUI.matrix;float scale=Scale,w=Screen.width/scale,h=Screen.height/scale;
            GUI.matrix=Matrix4x4.TRS(Vector3.zero,Quaternion.identity,Vector3.one*scale);
            // Leave the board camera viewport unobstructed.
            var bg=new Color(.055f,.105f,.13f);Fill(new Rect(0,0,w,112),bg);Fill(new Rect(0,112,332,h-112),bg);Fill(new Rect(332,h-112,w-332,112),bg);
            Fill(new Rect(332,112,w-332,76),bg);Fill(new Rect(w-16,112,16,h-112),bg);
            GUI.Label(new Rect(24,18,w-48,38),"Power-up playback",titleStyle);
            GUI.Label(new Rect(25,65,w-50,28),"HEART OF THE RAIN  /  APPROVED DESIGNS  /  2D GAMEPLAY",headingStyle);
            GUILayout.BeginArea(new Rect(16,118,300,h-138));
            int nextMode=GUILayout.Toolbar(mode,new[]{"Board playback","Animation library"});if(nextMode!=mode)SetMode(nextMode);
            GUILayout.Space(12);scroll=GUILayout.BeginScrollView(scroll);
            if(mode==0)
            {
                string group="";
                for(int i=0;i<data.entries.Length;i++)
                {
                    var e=data.entries[i];if(e.group!=group){GUILayout.Space(9);GUILayout.Label(e.group.ToUpperInvariant(),headingStyle);group=e.group;}
                    if(GUILayout.Button(e.title,i==selectedEntry?selectedStyle:buttonStyle,GUILayout.MinHeight(28)))SelectEntry(i);
                }
            }
            else
            {
                if(GUILayout.Button(data.library[selectedLibrary].title+"  ▾",selectedStyle,GUILayout.MinHeight(38)))showLibrary=!showLibrary;
                if(showLibrary)for(int i=0;i<data.library.Length;i++)if(GUILayout.Button(data.library[i].title,buttonStyle))SelectLibrary(i);
                GUILayout.Space(12);GUILayout.Label("ANIMATIONS",headingStyle);
                for(int i=0;i<clipManifest.clips.Length;i++)
                    if(GUILayout.Button(data.library[selectedLibrary].clipLabels[i],i==selectedClip?selectedStyle:buttonStyle,GUILayout.MinHeight(28)))
                    {selectedClip=i;cursor=0;Sample();}
            }
            GUILayout.EndScrollView();GUILayout.EndArea();
            string title=mode==0?data.entries[selectedEntry].title:data.library[selectedLibrary].title;
            string sub=mode==0?data.entries[selectedEntry].description:data.library[selectedLibrary].clipLabels[selectedClip]+"  /  isolated animation";
            GUI.Label(new Rect(352,117,w-380,30),title,titleStyle);GUI.Label(new Rect(352,153,w-380,32),sub,bodyStyle);
            GUILayout.BeginArea(new Rect(352,h-104,w-384,100));
            GUILayout.BeginHorizontal();
            if(GUILayout.Button(playing?"Pause":"Play",GUILayout.Width(72)))playing=!playing;
            if(GUILayout.Button("Replay",GUILayout.Width(70)))Replay();
            if(GUILayout.Button("Previous",GUILayout.Width(80)))Next(-1);
            if(GUILayout.Button("Next",GUILayout.Width(65)))Next(1);
            if(GUILayout.Button("− frame",GUILayout.Width(70)))StepFrame(-1);
            if(GUILayout.Button("+ frame",GUILayout.Width(70)))StepFrame(1);
            GUILayout.FlexibleSpace();GUILayout.Label(speed.ToString("0.##")+"×",bodyStyle,GUILayout.Width(36));
            foreach(float s in new[]{.25f,.5f,1f,2f})if(GUILayout.Button(s.ToString("0.##")+"×",GUILayout.Width(42)))speed=s;
            GUILayout.EndHorizontal();
            float seek=GUILayout.HorizontalSlider(Mathf.Min(cursor,Duration),0,Mathf.Max(.001f,Duration));if(Mathf.Abs(seek-Mathf.Min(cursor,Duration))>.0001f)Seek(seek);
            GUILayout.BeginHorizontal();GUILayout.Label(Mathf.Min(cursor,Duration).ToString("0.00")+" / "+Duration.ToString("0.00")+" s",smallStyle,GUILayout.Width(116));
            loop=GUILayout.Toggle(loop,"Loop",GUILayout.Width(64));autoAdvance=GUILayout.Toggle(autoAdvance,"Play all",GUILayout.Width(80));
            if(mode==0)
            {
                foreach(var size in new[]{new Vector2Int(9,9),new Vector2Int(9,11),new Vector2Int(11,11)})
                    if(GUILayout.Button(size.x+"×"+size.y,GUILayout.Width(58)))SetBoardSize(size.x,size.y);
                bool blockers=GUILayout.Toggle(board.showBlockers,"Obstacles",GUILayout.Width(88));if(blockers!=board.showBlockers){board.showBlockers=blockers;board.Rebuild();cursor=0;}
                if(board.kind==ReviewKind.RainSeekerRocket||board.kind==ReviewKind.GoldenSeekerRocket)
                {bool vertical=GUILayout.Toggle(board.rocketVertical,"Vertical",GUILayout.Width(80));if(vertical!=board.rocketVertical){board.rocketVertical=vertical;board.Rebuild();cursor=0;}}
            }
            GUILayout.EndHorizontal();GUILayout.EndArea();GUI.matrix=old;
        }
        void OnDisable()
        {if(board!=null){board.externallyDriven=false;board.SetBoardVisible(true);if(board.PreviewCamera!=null)board.PreviewCamera.rect=new Rect(0,0,1,1);}if(clipPlayer!=null)clipPlayer.gameObject.SetActive(false);}
        void OnEnable(){if(data!=null){board.externallyDriven=true;board.SetBoardVisible(mode==0);if(clipPlayer!=null)clipPlayer.gameObject.SetActive(mode==1);}}
    }
}
