using HeartOfTheRain.App.Localization;
using System;
using System.Collections.Generic;
using System.Globalization;

namespace HeartOfTheRain.App.Home
{
    [Serializable] public sealed class HomeState
    {
        public int currentLevel = 18, coins = 1250, stars = 0, lives = 5, maxLives = 5;
        public int chapterNumber = 1, completedLevelsInChapter = 17, levelsPerChapter = 50;
        public string chapterTitle = "The Village Well";
        public bool dailyVisible = true, cupVisible = true, wellworksVisible = true, teamVisible = true, reduceMotion;
        public string dailyStatus = "Ready", cupStatus = "2d 06h", wellworksStatus = "12/20", teamStatus = "1d 04h";
        public void Normalize()
        {
            currentLevel = Math.Max(1, currentLevel); coins = Math.Max(0, coins); stars = Math.Max(0, stars);
            maxLives = Math.Max(1, maxLives); lives = Math.Max(0, Math.Min(lives, maxLives));
            chapterNumber = Math.Max(1, chapterNumber); levelsPerChapter = Math.Max(1, levelsPerChapter);
            completedLevelsInChapter = Math.Max(0, Math.Min(completedLevelsInChapter, levelsPerChapter));
            chapterTitle = chapterTitle ?? "";
        }
    }
    [Serializable] public sealed class HomeElement
    {
        public string id, parent = "", kind, asset = "", text = "", action = "", label = "", color = "#FFFFFF";
        public float x, y, width, height;
        public int fontSize;
        public bool sliced, preserveAspect, shadow;
    }
    [Serializable] public sealed class HomeFrame
    {
        public float width, height;
        public bool landscape, compact, drawer;
        public List<HomeElement> elements = new List<HomeElement>();
    }
    // Pure C#: the Unity presenter and offline QA use exactly the same layout output.
    // Coordinates are safe-area-local logical units, with top-left origins.
    public static class HomeLayoutEngine
    {
        public const float MinimumWidth = 320, MinimumHeight = 420;
        static float Clamp(float x, float lo, float hi) { return Math.Max(lo, Math.Min(hi, x)); }
        static HomeElement Add(HomeFrame f, string id, string parent, string kind, float x, float y, float w, float h)
        {
            var e = new HomeElement { id=id, parent=parent, kind=kind, x=x, y=y, width=w, height=h };
            f.elements.Add(e); return e;
        }
        static HomeElement Group(HomeFrame f, string id, float x, float y, float w, float h, string action="", string label="")
        { var e=Add(f,id,"","group",x,y,w,h);e.action=action;e.label=GameLocale.T(label);return e; }
        static void Sprite(HomeFrame f,string id,string parent,string asset,float x,float y,float w,float h,bool sliced=false,bool aspect=false)
        {var e=Add(f,id,parent,"sprite",x,y,w,h);e.asset=asset;e.sliced=sliced;e.preserveAspect=aspect;}
        static void Text(HomeFrame f,string id,string parent,string text,float x,float y,float w,float h,int size,string color="#FFFFFF",bool shadow=true)
        {var e=Add(f,id,parent,"text",x,y,w,h);e.text=GameLocale.Element(id,text);e.fontSize=size;e.color=color;e.shadow=shadow;}
        static void Color(HomeFrame f,string id,string parent,float x,float y,float w,float h,string color)
        {var e=Add(f,id,parent,"color",x,y,w,h);e.color=color;}
        static void Event(HomeFrame f,string id,string asset,string name,string status,float x,float y,float w,float h)
        {
            Group(f,id,x,y,w,h,id,name+", "+status);
            float ah=Math.Min(h,w*1.13f),aw=ah/1.13f,ox=(w-aw)/2;
            Sprite(f,id+"-art",id,asset,ox,0,aw,ah);
            Text(f,id+"-title",id,name,ox+aw*.04f,ah*.635f,aw*.92f,ah*.145f,(int)Math.Round(aw*.145f),"#09182A",false);
            Text(f,id+"-status",id,status,ox+aw*.12f,ah*.81f,aw*.76f,ah*.135f,(int)Math.Round(aw*.155f));
        }
        static void Header(HomeFrame f,HomeState state,float x,float y,float w)
        {
            float h=w*360/2121;
            Group(f,"header",x,y,w,h);Sprite(f,"header-art","header","R4_Header",0,0,w,h);
            Text(f,"coin-count","header",CompactNumber(state.coins),w*.285f,h*.35f,w*.17f,h*.40f,(int)Math.Round(w*.047f),"#101A29",false);
            Text(f,"life-count","header",state.lives+"/"+state.maxLives,w*.68f,h*.35f,w*.15f,h*.40f,(int)Math.Round(w*.047f),"#101A29",false);
            float th=Math.Max(44,h),ty=y+(h-th)/2;
            Group(f,"avatar",x,ty,w*.18f,th,"profile","Your profile");
            Group(f,"coins",x+w*.19f,ty,w*.35f,th,"coins","Coins: "+state.coins+". Get coins");
            Group(f,"lives",x+w*.56f,ty,w*.29f,th,"lives","Lives: "+state.lives+" of "+state.maxLives);
            Group(f,"settings",x+w-Math.Max(44,w*.14f),ty,Math.Max(44,w*.14f),th,"settings","Settings");
        }
        static void Dock(HomeFrame f,float x,float y,float w)
        { MainNavigationLayout.Add(f,x,y,w,MainNavigationLayout.Height(f.width,f.height),2); }
        static void Controls(HomeFrame f,HomeState s,float x,float startY,float startW)
        {
            float sh=startW*437/1420, pw=startW*521/489,ph=pw*310/1644;
            Group(f,"start",x,startY,startW,Math.Max(44,sh),"prelevel","Start level "+s.currentLevel);
            Sprite(f,"start-art","start","R4_Start",0,0,startW,sh);
            Text(f,"start-label","start","Start Level",startW*.13f,sh*.12f,startW*.74f,sh*(GameLocale.Current==0?.31f:.38f),(int)Math.Round(startW*.12f));
            Text(f,"start-number","start",s.currentLevel.ToString(CultureInfo.InvariantCulture),startW*.15f,sh*.49f,startW*.7f,sh*.37f,(int)Math.Round(startW*.155f));
            Group(f,"progress",x+(startW-pw)/2,startY-ph-startW*.05f,pw,ph);
            Sprite(f,"progress-art","progress","R4_Progress",0,0,pw,ph);
            Text(f,"progress-count","progress",s.completedLevelsInChapter+" / "+s.levelsPerChapter,pw*.21f,ph*.13f,pw*.54f,ph*.36f,(int)Math.Round(pw*.047f));
            // The empty track is baked into the approved art; this transparent node defines its live fill bounds.
            Color(f,"progress-track","progress",pw*.193f,ph*.548f,pw*.563f,ph*.20f,"#FFFFFF00");
            Sprite(f,"progress-fill","progress","R4_ProgressFill",pw*.193f,ph*.548f,pw*.563f*s.completedLevelsInChapter/s.levelsPerChapter,ph*.20f,true);
        }
        public static HomeFrame Build(float width,float height,HomeState state,bool drawer=false)
        {
            state.Normalize();width=Math.Max(MinimumWidth,width);height=Math.Max(width>=480&&width/Math.Max(1,height)>=1.18f?320:MinimumHeight,height);
            var f=new HomeFrame {width=width,height=height,landscape=width/height>=1.18f,drawer=drawer};
            float w=width,h=height,ey,ey2,ew,left,right,progressY;
            if(!f.landscape)
            {
                bool tablet=w/h>=.68f&&w>=480;
                float s=tablet?Math.Min(w/1086,h/1200):Math.Min(w/941,h/1200);
                float hw=tablet?Math.Max(300,675*s):Math.Max(300,866*s),hy=tablet?60*s:22*s;
                Header(f,state,(w-hw)/2,hy,hw);
                float cw=(tablet?285:352)*s,ch=cw*501/2100,cy=(tablet?174:160)*s;
                Group(f,"chapter",(w-cw)/2,cy,cw,ch);Sprite(f,"chapter-art","chapter","R4_Chapter",0,0,cw,ch);
                Text(f,"chapter-index","chapter","Chapter "+state.chapterNumber,cw*.15f,ch*.05f,cw*.7f,ch*.31f,(int)Math.Round(cw*.064f));
                Text(f,"chapter-title","chapter",state.chapterTitle,cw*.08f,ch*.36f,cw*.84f,ch*.47f,(int)Math.Round(cw*.100f));
                float dw=Math.Min(620,tablet?924*s:w),dh=MainNavigationLayout.Height(w,h),dy=h-(tablet?40:36)*s-dh;
                Dock(f,(w-dw)/2,dy,dw);
                float sw=(tablet?394:489)*s,sy=dy-26*s-sw*437/1420;
                Controls(f,state,(w-sw)/2,sy,sw);
                progressY=sy-sw*521/489*310/1644-sw*.05f;
                ew=(tablet?145:190)*s;ey=(tablet?320:337)*s;ey2=(tablet?510:587)*s;
                left=tablet?60*s:20*s;right=w-left-ew;
                f.compact=ey2+ew*1.13f+12>progressY;
                if(f.compact)
                {
                    float dy2=Math.Min(progressY-56,cy+ch+16);
                    Group(f,"events",w-86,dy2,76,44,"events","Open events");
                    Sprite(f,"events-art","events","R3_Header",0,0,76,44,true);
                    Text(f,"events-label","events","Events",4,8,68,28,14);
                }
            }
            else
            {
                float dw=Math.Min(w,620),dh=MainNavigationLayout.Height(w,h),dy=h-8-dh;
                Dock(f,(w-dw)/2,dy,dw);
                float hw=Math.Min(w-32,Math.Max(300,h*.85f));Header(f,state,(w-hw)/2,8,hw);
                float by=12+hw*360/2121,sw=Math.Min(w*.28f,Math.Max(180,h*.40f)),sx=w-sw-16;
                float sy=dy-12-sw*437/1420;Controls(f,state,sx,sy,sw);progressY=sy-sw*521/489*310/1644-sw*.05f;
                float cw=Math.Min(200,w*.27f),ch=cw*501/2100;
                Group(f,"chapter",(w-cw)/2,by,cw,ch);Sprite(f,"chapter-art","chapter","R4_Chapter",0,0,cw,ch);
                Text(f,"chapter-index","chapter","Chapter "+state.chapterNumber,cw*.15f,ch*.05f,cw*.7f,ch*.31f,(int)Math.Round(cw*.064f));
                Text(f,"chapter-title","chapter",state.chapterTitle,cw*.08f,ch*.36f,cw*.84f,ch*.47f,(int)Math.Round(cw*.100f));
                ew=Math.Min((sw-12)/2,(progressY-by-20)/2.4f);ey=by+6;ey2=ey+ew*1.18f;left=sx;right=sx+sw-ew;
                f.compact=ew<64;
                if(f.compact)
                {
                    Group(f,"events",sx,by+4,sw,44,"events","Open events");Sprite(f,"events-art","events","R3_Header",0,0,sw,44,true);Text(f,"events-label","events","Events",4,8,sw-8,28,14);
                }
            }
            if(!f.compact)
            {
                if(state.dailyVisible)Event(f,"daily","R4_Daily","Daily Gift",state.dailyStatus,left,ey,ew,ew*1.13f);
                if(state.cupVisible)Event(f,"cup","R4_Cup","Rain Cup",state.cupStatus,right,ey,ew,ew*1.13f);
                if(state.wellworksVisible)Event(f,"wellworks","R4_Wellworks","Wellworks",state.wellworksStatus,left,ey2,ew,ew*1.13f);
                if(state.teamVisible)Event(f,"team","R4_Team","Team Quest",state.teamStatus,right,ey2,ew,ew*1.13f);
            }
            if(drawer)Drawer(f,state);return f;
        }
        static void Drawer(HomeFrame f,HomeState s)
        {
            Group(f,"drawer-scrim",0,0,f.width,f.height,"close-events","Close events");Color(f,"drawer-shade","drawer-scrim",0,0,f.width,f.height,"#061527F5");
            float w=Math.Min(350,f.width-24),h=Math.Min(386,f.height-24),x=(f.width-w)/2,y=(f.height-h)/2;
            Group(f,"drawer-panel",x,y,w,h);Text(f,"drawer-title","drawer-panel","Events",16,8,w-80,32,24);
            Group(f,"drawer-close",x+w-52,y,44,44,"close-events","Close events");Text(f,"drawer-close-label","drawer-close","×",0,0,44,44,29);
            float eh=(h-64)/2,ew=Math.Min((w-40)/2,eh/1.13f);
            if(s.dailyVisible)Event(f,"drawer-daily","R4_Daily","Daily Gift",s.dailyStatus,x+12,y+54,ew,eh);
            if(s.cupVisible)Event(f,"drawer-cup","R4_Cup","Rain Cup",s.cupStatus,x+w-ew-12,y+54,ew,eh);
            if(s.wellworksVisible)Event(f,"drawer-wellworks","R4_Wellworks","Wellworks",s.wellworksStatus,x+12,y+54+eh,ew,eh);
            if(s.teamVisible)Event(f,"drawer-team","R4_Team","Team Quest",s.teamStatus,x+w-ew-12,y+54+eh,ew,eh);
        }
        public static string CompactNumber(int n)
        {
            if(n<10000)return n.ToString("N0",CultureInfo.InvariantCulture);
            if(n<1000000)return (n/1000f).ToString("0.#",CultureInfo.InvariantCulture)+"K";
            return (n/1000000f).ToString("0.#",CultureInfo.InvariantCulture)+"M";
        }
    }

    public static class MainNavigationLayout
    {
        public static float Height(float width,float height)
        {return width/Math.Max(1,height)>1.4f?76:Math.Min(103,Math.Max(86,width*.255f));}
        public static void Add(HomeFrame f,float x,float y,float w,float h,int active)
        {
            f.elements.Add(new HomeElement{id="dock-bg",kind="sprite",asset="R3_Dock",x=x,y=y+h*.22f,width=w,height=h*.78f});
            string[] names={"Journey","Leaderboard","Home","Teams","Shop"};
            for(int i=0;i<5;i++)
            {
                float cw=w/5,xx=x+i*cw,pw=Math.Min(cw,h*.90f);bool selected=i==active;string id="nav-"+names[i].ToLowerInvariant();
                f.elements.Add(new HomeElement{id=id+"-plate",kind="sprite",asset="Nav_Active",x=xx+(cw-pw)/2,y=y,width=pw,height=h,color=selected?"#FFFFFF":"#FFFFFF00"});
                float size=Math.Min(cw-22,Math.Min(h*.50f,h-44));
                f.elements.Add(new HomeElement{id=id+"-icon",kind="sprite",asset="R3_"+names[i],x=xx+(cw-size)/2,y=y+(selected?18:30),width=size,height=size,preserveAspect=true,color="#FFFFFF"});
                string label=i==1?(cw<70?"Ranks":"Rankings"):names[i];
                f.elements.Add(new HomeElement{id=id+"-label",kind="text",text=GameLocale.T(label),x=xx+(cw-pw*.78f)/2,y=y+h-26,width=pw*.78f,height=18,fontSize=pw<90?12:14,color=selected?"#FFFFFF":"#FFFFFF00",shadow=selected});
                f.elements.Add(new HomeElement{id=id,kind="group",x=xx,y=y,width=cw,height=h,action=names[i].ToLowerInvariant(),label=GameLocale.T(names[i])});
            }
        }
    }
}

namespace HeartOfTheRain.App.Home
{
    // UI presentation only: preserve original textures and gameplay/VFX geometry.
    public static class RewardIconLayout
    {
        public static void ToolBounds(int index,float x,float y,float size,out float rx,out float ry,out float rs)
        {
            // Visible alpha bounds (>24/255) of approved 1254 px booster artwork.
            float[] left={109,85,56,47},top={70,79,319,135},right={1182,1219,1205,1217},bottom={1165,1184,959,1100};
            int i=Math.Max(0,Math.Min(3,index));float extent=Math.Max(right[i]-left[i],bottom[i]-top[i]);
            rs=size*.90f*1254/extent;rx=x+size/2-rs*(left[i]+right[i])/2508;ry=y+size/2-rs*(top[i]+bottom[i])/2508;
        }
        static void Icon(HomeFrame f,string id,string key,float x,float y,float w,float h,string p,string color)
        {f.elements.Add(new HomeElement{id=id,parent=p,kind="sprite",asset=key,x=x,y=y,width=w,height=h,preserveAspect=true,color=color});}
        public static void Tool(HomeFrame f,string id,int index,float x,float y,float size,string parent="",string color="#FFFFFF")
        {float rx,ry,rs;ToolBounds(index,x,y,size,out rx,out ry,out rs);Icon(f,id,new[]{"ShopHammer","ShopAxe","ShopRam","ShopAtlas"}[index],rx,ry,rs,rs,parent,color);}
        public static void StartingBooster(HomeFrame f,string id,int index,float x,float y,float size,string parent="",string color="#FFFFFF")
        {
            if(index<0||index>3)throw new ArgumentOutOfRangeException(nameof(index));
            Icon(f,id+"-icon",new[]{"Rocket","Bomb","RainbowOrb_R2","GoldenSeeker_R2"}[index],x+size*.05f,y+size*.05f,size*.9f,size*.9f,parent,color);
        }
    }
}
