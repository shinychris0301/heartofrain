using HeartOfTheRain.App.Localization;
using System;
using System.Collections.Generic;
using System.Globalization;

namespace HeartOfTheRain.App.Home
{
    [Serializable] public sealed class HomeState
    {
        public int currentLevel = 1, coins = 0, stars = 0, lives = 0, maxLives = 5;
        public int chapterNumber = 1, completedLevelsInChapter = 0, levelsPerChapter = 50;
        public string chapterTitle = "The Village Well";
        [NonSerialized] public string lifeRefillStatus="\u2026";[NonSerialized] public bool lifeRefillClock=true, walletUnavailable;
        public bool dailyVisible = true, cupVisible = true, wellworksVisible = true, teamVisible = true, reduceMotion;
        public string dailyStatus = "", cupStatus = "", wellworksStatus = "", teamStatus = "";
        [NonSerialized] public bool rewardedVisible, rewardedEligible;
        [NonSerialized] public string rewardedStatus = "";
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
        static void RewardedEvent(HomeFrame f,string id,HomeState state,float x,float y,float w,float h)
        {
            Group(f,id,x,y,w,h,"video",GameLocale.T("Video"));
            float ah=Math.Min(h,w*1.13f),aw=ah/1.13f,ox=(w-aw)/2;
            Sprite(f,id+"-icon",id,"Rewarded_Video_Icon",ox+aw*.035f,0,aw*.93f,ah*.75f,false,true);
            if(!state.rewardedEligible)f.elements[f.elements.Count-1].color="#FFFFFFA6";
            Sprite(f,id+"-ribbon",id,"R3_Ribbon",ox,ah*.625f,aw,ah*.19f);
            Text(f,id+"-title",id,"Video",ox+aw*.08f,ah*.655f,aw*.84f,ah*.12f,(int)Math.Round(aw*.145f),"#09182A",false);
            Sprite(f,id+"-plate",id,"R3_Header",ox+aw*.14f,ah*.82f,aw*.72f,ah*.15f);
            Text(f,id+"-status",id,state.rewardedStatus??"",ox+aw*.18f,ah*.825f,aw*.64f,ah*.13f,(int)Math.Round(aw*.16f),state.rewardedEligible?"#8BF278":"#E8EFF8",false);
        }
        static void Header(HomeFrame f,HomeState state,float x,float y,float w)
        {
            float h=w*360/2121;
            float avatarW=w*HomeHeaderGeometry.AvatarFraction;
            float avatarEdge=w*HomeHeaderGeometry.FrameFraction;
            Group(f,"header",x,y,w,h);
            Sprite(f,"header-connector","header","HomeHeaderConnector",avatarEdge,0,avatarW-avatarEdge,h);
            Sprite(f,"header-panel","header","HomeHeaderPanel",avatarW,0,w-avatarW,h);
            Text(f,"coin-count","header",state.walletUnavailable?"\u2014":CompactNumber(state.coins),w*.285f,h*.35f,w*.17f,h*.40f,(int)Math.Round(w*.047f),"#101A29",false);
            Text(f,"life-count","header",state.walletUnavailable?"\u2014/"+state.maxLives:state.lives+"/"+state.maxLives,w*.68f,h*.32f,w*.15f,h*.28f,(int)Math.Round(w*.043f),state.walletUnavailable?"#425F79":state.lives==0?"#B12640":state.lives==1?"#945522":"#101A29",false);
            Text(f,"life-refill-status","header",state.lifeRefillStatus??"\u2026",w*.678f,h*.59f,w*.154f,h*.17f,(int)Math.Round(Clamp(w*.028f,10,18)),"#425F79",false);
            float th=Math.Max(44,h),ty=y+(h-th)/2;
            Group(f,"avatar",x,ty,avatarW,th,"profile","Your profile");
            Add(f,"avatar-slot","avatar","group",0,(th-avatarEdge)/2,avatarW,avatarEdge);
            Sprite(f,"avatar-default","avatar-slot","HomeHeaderDefaultAvatar",0,0,avatarEdge,avatarEdge);
            Group(f,"coins",x+w*.19f,ty,w*.35f,th,"coins",state.walletUnavailable?GameLocale.T("Unavailable"):"Coins: "+state.coins+". Get coins");
            Group(f,"lives",x+w*.56f,ty,w*.29f,th,"lives",state.walletUnavailable?GameLocale.T("Unavailable"):HomeLivesText.Count("counter",state.lives,state.maxLives)+". "+HomeLivesText.T("action"));
            Group(f,"settings",x+w-Math.Max(44,w*.14f),ty,Math.Max(44,w*.14f),th,"settings","Settings");
        }
        static void Dock(HomeFrame f,float x,float y,float w)
        { MainNavigationLayout.Add(f,x,y,w,MainNavigationLayout.Height(f.width,f.height),2); }
        static void Controls(HomeFrame f,HomeState s,float x,float startY,float startW)
        {
            float sh=startW*437/1420, pw=startW*521/489,ph=pw*310/1644;
            string levelLabel=s.walletUnavailable?GameLocale.Format("Level {0}","\u2014"):GameLocale.Format("Level {0}",s.currentLevel);
            Group(f,"start",x,startY,startW,Math.Max(44,sh),"prelevel",levelLabel);
            Sprite(f,"start-art","start","R4_Start",0,0,startW,sh);
            Text(f,"start-label","start",levelLabel,startW*.11f,sh*.12f,startW*.78f,sh*.76f,(int)Math.Round(startW*.16f));
            Group(f,"progress",x+(startW-pw)/2,startY-ph-startW*.05f,pw,ph);
            Sprite(f,"progress-art","progress","R4_Progress",0,0,pw,ph);
            Text(f,"progress-count","progress",(s.walletUnavailable?"\u2014":s.completedLevelsInChapter.ToString())+" / "+s.levelsPerChapter,pw*.21f,ph*.13f,pw*.54f,ph*.36f,(int)Math.Round(pw*.047f));
            // The empty track is baked into the approved art; this transparent node defines its live fill bounds.
            Color(f,"progress-track","progress",pw*.193f,ph*.548f,pw*.563f,ph*.20f,"#FFFFFF00");
            Sprite(f,"progress-fill","progress","R4_ProgressFill",pw*.193f,ph*.548f,pw*.563f*(s.walletUnavailable?0:s.completedLevelsInChapter)/s.levelsPerChapter,ph*.20f,true);
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
                float dw=MainNavigationLayout.Width(w,h),dh=MainNavigationLayout.Height(w,h),dy=h-MainNavigationLayout.BottomInset(w,h)-dh;
                Dock(f,(w-dw)/2,dy,dw);
                float sw=(tablet?394:489)*s,sy=dy-26*s-sw*437/1420;
                Controls(f,state,(w-sw)/2,sy,sw);
                progressY=sy-sw*521/489*310/1644-sw*.05f;
                ew=(tablet?145:190)*s;ey=(tablet?320:337)*s;ey2=(tablet?510:587)*s;
                left=tablet?60*s:20*s;right=w-left-ew;
                f.compact=ey2+ew*1.13f+12>progressY||state.rewardedVisible&&ey2+(ey2-ey)+ew*1.13f+12>progressY;
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
                float dw=MainNavigationLayout.Width(w,h),dh=MainNavigationLayout.Height(w,h),dy=h-MainNavigationLayout.BottomInset(w,h)-dh;
                Dock(f,(w-dw)/2,dy,dw);
                float hw=Math.Min(w-32,Math.Max(300,h*.85f));Header(f,state,(w-hw)/2,8,hw);
                float by=12+hw*360/2121,sw=Math.Min(w*.28f,Math.Max(180,h*.40f)),sx=w-sw-16;
                float sy=dy-12-sw*437/1420;Controls(f,state,sx,sy,sw);progressY=sy-sw*521/489*310/1644-sw*.05f;
                float cw=Math.Min(200,w*.27f),ch=cw*501/2100;
                Group(f,"chapter",(w-cw)/2,by,cw,ch);Sprite(f,"chapter-art","chapter","R4_Chapter",0,0,cw,ch);
                Text(f,"chapter-index","chapter","Chapter "+state.chapterNumber,cw*.15f,ch*.05f,cw*.7f,ch*.31f,(int)Math.Round(cw*.064f));
                Text(f,"chapter-title","chapter",state.chapterTitle,cw*.08f,ch*.36f,cw*.84f,ch*.47f,(int)Math.Round(cw*.100f));
                ew=Math.Min((sw-12)/2,(progressY-by-20)/2.4f);ey=by+6;ey2=ey+ew*1.18f;left=sx;right=sx+sw-ew;
                f.compact=ew<64||state.rewardedVisible&&ey2+(ey2-ey)+ew*1.13f+12>progressY;
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
                if(state.rewardedVisible)RewardedEvent(f,"video",state,right,ey2+(ey2-ey),ew,ew*1.13f);
            }
            if(drawer)Drawer(f,state);return f;
        }
        static void Drawer(HomeFrame f,HomeState s)
        {
            Group(f,"drawer-scrim",0,0,f.width,f.height,"close-events","Close events");Color(f,"drawer-shade","drawer-scrim",0,0,f.width,f.height,"#061527F5");
            float w=Math.Min(350,f.width-24),h=Math.Min(s.rewardedVisible?450:386,f.height-24),x=(f.width-w)/2,y=(f.height-h)/2;
            Group(f,"drawer-panel",x,y,w,h);Text(f,"drawer-title","drawer-panel","Events",16,8,w-80,32,24);
            Group(f,"drawer-close",x+w-52,y,44,44,"close-events","Close events");Text(f,"drawer-close-label","drawer-close","×",0,0,44,44,29);
            float eh=(h-64)/(s.rewardedVisible?3:2),ew=Math.Min((w-40)/2,eh/1.13f);
            if(s.dailyVisible)Event(f,"drawer-daily","R4_Daily","Daily Gift",s.dailyStatus,x+12,y+54,ew,eh);
            if(s.cupVisible)Event(f,"drawer-cup","R4_Cup","Rain Cup",s.cupStatus,x+w-ew-12,y+54,ew,eh);
            if(s.wellworksVisible)Event(f,"drawer-wellworks","R4_Wellworks","Wellworks",s.wellworksStatus,x+12,y+54+eh,ew,eh);
            if(s.teamVisible)Event(f,"drawer-team","R4_Team","Team Quest",s.teamStatus,x+w-ew-12,y+54+eh,ew,eh);
            if(s.rewardedVisible)RewardedEvent(f,"drawer-video",s,x+w-ew-12,y+54+eh*2,ew,eh);
        }
        public static string CompactNumber(int n)
        {
            if(n<10000)return n.ToString("N0",CultureInfo.InvariantCulture);
            if(n<1000000)return (n/1000f).ToString("0.#",CultureInfo.InvariantCulture)+"K";
            return (n/1000000f).ToString("0.#",CultureInfo.InvariantCulture)+"M";
        }
    }

    // The approved 2121 x 360 texture is an atlas, never a full header overlay.
    public static class HomeHeaderGeometry
    {
        public const float AvatarFraction=400f/2121f;
        // Match the original M71 avatar's square display size, not the atlas slice.
        public const float FrameFraction=.17f;
        public const float DefaultPortraitFraction=386f/2121f;
        public const float ConnectorFraction=16f/2121f;
    }

    public static class MainNavigationLayout
    {
        public static float BottomInset(float width,float height){if(width/Math.Max(1,height)>=1.18f)return 8;bool tablet=width/height>=.68f&&width>=480;return (tablet?40:36)*Math.Min(width/(tablet?1086:941),height/1200);}
        public static float Width(float width,float height){bool tablet=width/Math.Max(1,height)<1.18f&&width/height>=.68f&&width>=480;return Math.Min(620,tablet?924*Math.Min(width/1086,height/1200):width);}
        public static float ReservedHeight(float width,float height)=>Height(width,height)+BottomInset(width,height);
        public static void AddDock(HomeFrame frame,float width,float height,int active){frame.width=width;frame.height=height;float w=Width(width,height),h=Height(width,height);Add(frame,(width-w)/2,height-BottomInset(width,height)-h,w,h,active);}
        public static float Height(float width,float height)
        {return width/Math.Max(1,height)>1.4f?76:Math.Min(103,Math.Max(86,width*.255f));}
        public static void Add(HomeFrame f,float x,float y,float w,float h,int active)
        {
            // Preserve the original dock dimensions, consuming only available
            // safe-bottom inset for the small shared downward adjustment.
            y+=Math.Min(4,Math.Max(0,f.height-(y+h)));
            if(w<320){AddCompact(f,x,y,w,h,active);return;}
            f.elements.Add(new HomeElement{id="dock-bg",kind="sprite",asset="R3_Dock",x=x,y=y+h*.22f,width=w,height=h*.78f});
            float cw=w/5,pw=Math.Min(cw,h*.90f),size=Math.Min(cw-22,Math.Min(h*.50f,h-44));
            // Five original-size icon footprints, with each intervening gap
            // reduced by exactly 5%. The visual group stays centered; fixed
            // full-size touch columns keep their original bounds and routes.
            float pitch=size+.95f*(cw-size);
            string[] names={"Journey","Leaderboard","Home","Teams","Shop"};
            for(int i=0;i<5;i++)
            {
                float center=x+w/2+(i-2)*pitch;bool selected=i==active;string id="nav-"+names[i].ToLowerInvariant();
                f.elements.Add(new HomeElement{id=id+"-plate",kind="sprite",asset="Nav_Active",x=center-pw/2,y=y,width=pw,height=h,color=selected?"#FFFFFF":"#FFFFFF00"});
                f.elements.Add(new HomeElement{id=id+"-icon",kind="sprite",asset="R3_"+names[i],x=center-size/2,y=y+(selected?18:30),width=size,height=size,preserveAspect=true,color="#FFFFFF"});
                string label=i==1?(cw<70?"Ranks":"Rankings"):names[i];
                f.elements.Add(new HomeElement{id=id+"-label",kind="text",text=GameLocale.T(label),x=center-pw*.78f/2,y=y+h-26,width=pw*.78f,height=18,fontSize=pw<90?12:14,color=selected?"#FFFFFF":"#FFFFFF00",shadow=selected});
                f.elements.Add(new HomeElement{id=id,kind="group",x=x+i*cw,y=y,width=cw,height=h,action=names[i].ToLowerInvariant(),label=GameLocale.T(names[i])});
            }
        }
        // Retain the bounded 106 presentation only when an extreme UI scale
        // yields less than 320 logical units. The original cw-22 icon formula
        // cannot represent those clipped viewports safely.
        static void AddCompact(HomeFrame f,float x,float y,float w,float h,int active)
        {
            float barY=y+h*.22f,barH=h*.78f;
            f.elements.Add(new HomeElement{id="dock-bg",kind="sprite",asset="R3_Dock",x=x,y=barY,width=w,height=barH});
            // The rounded gold ends are not navigation columns. All content
            // shares the painted bar, rather than the taller reserved region.
            float side=w*.08f,cw=(w-2*side)/5;
            string[] names={"Journey","Leaderboard","Home","Teams","Shop"};
            float[] aspect={326f/238f,300f/212f,344f/296f,311f/275f,337f/285f};
            for(int i=0;i<5;i++)
            {
                float xx=x+side+i*cw,ph=Math.Min(barH*.82f,Math.Max(1,cw)/(1342f/1172f)),pw=ph*(1342f/1172f),py=barY+(barH-ph)/2;bool selected=i==active;string id="nav-"+names[i].ToLowerInvariant();
                f.elements.Add(new HomeElement{id=id+"-plate",kind="sprite",asset="Nav_Active",x=xx+(cw-pw)/2,y=py,width=pw,height=ph,preserveAspect=true,color=selected?"#FFFFFF":"#FFFFFF00"});
                // Match visible icon height without squashing the original PNGs.
                float ih=ph*.40f,iw=ih*aspect[i];
                f.elements.Add(new HomeElement{id=id+"-icon",kind="sprite",asset="R3_"+names[i],x=xx+(cw-iw)/2,y=py+ph*.43f-ih/2,width=iw,height=ih,preserveAspect=true,color="#FFFFFF"});
                string label=i==1?(cw<70?"Ranks":"Rankings"):names[i];float labelH=ph*.20f;
                f.elements.Add(new HomeElement{id=id+"-label",kind="text",text=GameLocale.T(label),x=xx+(cw-pw*.60f)/2,y=py+ph*.66f,width=pw*.60f,height=labelH,fontSize=pw<90?12:14,color=selected?"#FFFFFF":"#FFFFFF00",shadow=selected});
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
