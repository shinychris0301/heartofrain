using HeartOfTheRain.App.Localization;
using System;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.PreLevel
{
    // One geometry definition for the Unity view and the offline design review.
    public static class PreLevelLayout
    {
        const string Ink="#17354E", Secondary="#526777";
        static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="panel")
        {var e=new HomeElement{id=id,kind=kind,parent=parent,x=x,y=y,width=w,height=h};f.elements.Add(e);return e;}
        static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool sliced=false,string color="#FFFFFF")
        {var e=Add(f,id,"sprite",x,y,w,h);e.asset=asset;e.sliced=sliced;e.color=color;e.preserveAspect=!sliced;}
        static void Label(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string color=Ink,bool shadow=false)
        {var e=Add(f,id,"text",x,y,w,h);e.text=GameLocale.Element(id,text);e.fontSize=size;e.color=color;e.shadow=shadow;}
        static void Hit(HomeFrame f,string id,string action,string label,float x,float y,float w,float h)
        {var e=Add(f,id,"group",x,y,w,h);e.action=action;e.label=GameLocale.T(label);}
        static string Clock(int seconds){seconds=Math.Max(0,seconds);return (seconds/60).ToString("00")+":"+(seconds%60).ToString("00");}
        static string Target(string family)
        {switch(family){case "crystal":return "crystalIcon";case "pod":return "waterSpirit";case "rainlight":return "rainlight";case "crate":return "crate_1";case "moss":return "moss_1";case "stone":return "stone_1";case "pail":return "pail_Full";case "case":return "case_1";default:return "gate_1";}}
        static void Goals(HomeFrame f,PreLevelViewData s,float x,float y,float w)
        {
            Label(f,"targets-label","Targets",x,y,w,21,16);
            int n=Math.Min(4,s.goals.Length);float span=Math.Min(w,n*67),cell=span/Math.Max(1,n);
            for(int i=0;i<n;i++)
            {
                float gx=x+(w-span)/2+i*cell;string family=s.goals[i].family;
                float size=family=="gate"||family=="rainlight"||family=="pod"?44:40;
                Art(f,"target-"+i,Target(family),gx+(cell-size)/2,y+27+(44-size)/2,size,size);
                Label(f,"target-count-"+i,s.goals[i].count.ToString(),gx,y+72,cell,24,20);
            }
        }
        static void Rewards(HomeFrame f,PreLevelViewData s,float x,float y,float w)
        {
            if(!string.IsNullOrEmpty(s.message)){Label(f,"feedback",s.message,x,y,w,28,11,"#8B3430");return;}
            float start=x+(w-226)/2;
            Label(f,"reward-label","Rewards",start,y,85,25,12,Secondary);
            Art(f,"reward-coin","RewardCoin",start+92,y+1,23,23);
            Label(f,"reward-coins",s.rewardCoins.ToString(),start+118,y,34,25,17);
            Art(f,"reward-star","RewardStar_R2",start+160,y+1,23,23);
            Label(f,"reward-stars",s.rewardStars.ToString(),start+186,y,32,25,17);
        }
        static void Boosters(HomeFrame f,PreLevelViewData s,float x,float y,float w)
        {
            Label(f,"booster-label","Choose boosters",x,y,w,24,17);
            const float gap=8;float bw=(w-3*gap)/4,by=y+34;
            string[] names={"Rocket","Bomb","Rainbow Orb","Golden Seeker"};
            for(int i=0;i<4;i++)
            {
                float bx=x+i*(bw+gap);string prefix="booster-"+i;bool selected=s.selected[i];string tint=s.stock[i]>0&&(!s.retry||s.lives>0)?"#FFFFFF":"#FFFFFF66";
                Art(f,prefix+"-socket",selected?"BoosterWellSelected_R2":"BoosterWell_R2",bx,by,bw,bw,true);
                RewardIconLayout.StartingBooster(f,prefix,i,bx+bw*.14f,by+bw*.10f,bw*.72f,"panel",tint);
                Art(f,prefix+"-quantity","QuantityBadge_R2",bx+(bw-32)/2,by+bw-11,32,23);
                Label(f,prefix+"-count",s.stock[i].ToString(),bx+(bw-30)/2,by+bw-10,30,21,14,"#FFFFFF",true);
                if(selected)Art(f,prefix+"-check","SelectionTick_R2",bx+bw-18,by-5,23,23);
                Hit(f,prefix,"toggle:"+i,names[i]+", "+s.stock[i]+" available"+(selected?", selected":""),bx,by,bw,bw+15);
            }
        }
        public static HomeFrame Build(float width,float height,PreLevelViewData s)
        {
            if(s.livesOnly)return Lives(width,height,s);
            float w=Math.Max(320,width),h=Math.Max(320,height);bool wide=w>=640&&w/h>=1.35f;
            float pw=wide?556:Math.Min(344,w-24),ph=wide?316:452;
            var f=new HomeFrame{width=w,height=Math.Max(h,ph+24),landscape=wide,compact=!wide&&h<570};
            Add(f,"panel","group",(w-pw)/2,(f.height-ph)/2,pw,ph,"");
            Art(f,"panel-art","ModalShell_R2",0,0,pw,ph,true);
            Label(f,"level","Level "+s.level,50,15,pw-100,40,30,"#FFFFFF",true);
            if(s.retry)
            {
                // Center the status in the flat side band, below the raised title crest.
                Art(f,"retry-life-icon","RetryLife",22,35,20,20);
                Label(f,"retry-lives",s.lives.ToString(),44,32,20,26,17,"#FFFFFF",true);
            }
            if(wide)
            {
                Goals(f,s,25,80,222);Rewards(f,s,23,185,226);
                Boosters(f,s,275,81,256);
            }
            else
            {
                Goals(f,s,24,80,pw-48);Rewards(f,s,24,181,pw-48);
                Art(f,"section-divider","SectionDivider_R2",(pw-250)/2,210,250,2);
                Boosters(f,s,24,217,pw-48);
            }
            float playY=ph-72;bool noLives=s.lives<=0;
            Art(f,"play-art","R4_Start",(pw-228)/2,playY,228,66,false,s.lives>0||s.canRefill?"#FFFFFF":"#89969F");
            // A refill is still an offer when the wallet cannot afford it. Keep
            // its price visible instead of replacing the whole action with "No lives".
            string playText=noLives?"Refill "+s.refillCoins:s.retry?"Try Again":"Play";
            Label(f,"play-text",playText,(pw-190)/2,playY+10,190,43,29,"#FFFFFF",true);
            if(noLives)
            {
                // Removing booster names frees this band without expanding the
                // approved shell or squeezing a countdown into the button itself.
                if(s.nextLifeSeconds>=0)Label(f,"life-timer","Next life in "+Clock(s.nextLifeSeconds),24,playY-39,pw-48,18,11,Secondary);
                if(!s.canRefill&&!s.busy)Label(f,"refill-unaffordable","Not enough coins",24,playY-21,pw-48,16,11,"#8B3430");
            }
            string playAction=noLives?"refill":"play";
            Hit(f,"play",playAction,playAction=="refill"?"Refill lives for "+s.refillCoins+" coins":(s.retry?"Retry level ":"Play level ")+s.level,(pw-228)/2,playY,228,66);
            float closeX=pw-50,closeY=s.retry?23:18;
            Art(f,"close-art","Close",closeX+6,closeY+6,32,32);Hit(f,"close","close",s.retry?"Return Home without restarting":"Close level preview",closeX,closeY,44,44);
            return f;
        }
        static HomeFrame Lives(float width,float height,PreLevelViewData s)
        {
            bool empty=s.lives<=0;float w=Math.Max(320,width),h=Math.Max(320,height),pw=Math.Min(344,w-24),ph=empty?338:280;
            var f=new HomeFrame{width=w,height=Math.Max(h,ph+24),compact=true};
            Add(f,"panel","group",(w-pw)/2,(f.height-ph)/2,pw,ph,"");
            Art(f,"panel-art","ModalShell_R2",0,0,pw,ph,true);
            Label(f,"lives-title",HomeLivesText.T("lives"),50,15,pw-100,40,30,"#FFFFFF",true);
            // The compact shell's fixed bottom slice begins at210. Keep dark
            // information text above200, clear of the curved gold/cream seam.
            Art(f,"lives-heart","LivesHeart",(pw-80)/2,empty?78:60,80,80);
            Label(f,"lives-count",s.lives+" / "+s.maxLives,24,empty?163:142,pw-48,empty?31:29,24,empty?"#B12640":Ink);
            bool full=s.lives>=s.maxLives;
            string status=full?HomeLivesText.T("full"):s.nextLifeSeconds<0?HomeLivesText.T("sync"):HomeLivesText.T("nextLife").Replace("{time}",Clock(s.nextLifeSeconds));
            if(!full)Art(f,"lives-clock","LivesClock",24,empty?207:177,17,17);
            Label(f,"lives-status",status,full?24:47,empty?202:174,full?pw-48:pw-71,empty?27:24,16,full?"#377347":Secondary);
            if(!string.IsNullOrEmpty(s.message))Label(f,"lives-feedback",s.message,24,empty?231:228,pw-48,empty?18:24,11,empty?"#8B3430":"#FFFFFF");
            else if(s.lives<=0&&!s.canRefill&&!s.busy)Label(f,"refill-unaffordable","Not enough coins",24,231,pw-48,18,11,"#8B3430");
            if(s.lives<=0)
            {
                float y=ph-80;Art(f,"play-art","R4_Start",(pw-228)/2,y,228,66,false,s.canRefill?"#FFFFFF":"#89969F");
                Label(f,"play-text","Refill "+s.refillCoins,(pw-190)/2,y+10,190,43,29,"#FFFFFF",true);
                Hit(f,"play","refill","Refill lives for "+s.refillCoins+" coins",(pw-228)/2,y,228,66);
            }
            Art(f,"close-art","Close",pw-44,24,32,32);Hit(f,"close","close",GameLocale.T("Close"),pw-50,18,44,44);
            return f;
        }
    }
}
