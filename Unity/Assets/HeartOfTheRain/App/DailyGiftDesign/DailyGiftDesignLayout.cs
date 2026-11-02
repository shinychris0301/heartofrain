using System;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Profile {
    // Logical coordinates. Only viewport clips; the title, close decoration and footer stay fixed.
    public static class DailyGiftDesignLayout {
        const string Navy="#15365E",Muted="#687C8A",Cream="#FFF4D7";
        static void Add(HomeFrame f,string id,string parent,string kind,string value,float x,float y,float w,float h,int font=14,string color=Navy,bool sliced=false){
            var e=new HomeElement{id=id,parent=parent,kind=kind,x=x,y=y,width=w,height=h,fontSize=font,color=color,sliced=sliced,preserveAspect=!sliced};
            if(kind=="text")e.text=value;else if(kind=="sprite"){e.asset=value;e.color="#FFFFFF";}else e.action=value;f.elements.Add(e);
        }
        static string Icon(RewardGrant g)=>g.starting[0]>0?"DG_Rocket":g.starting[1]>0?"DG_Bomb":g.starting[2]>0?"DG_Orb":g.tools[0]>0?"DG_Hammer":"DG_Coin";
        static string Name(RewardGrant g)=>g.starting[0]>0?"rocket":g.starting[1]>0?"bomb":g.starting[2]>0?"orb":g.tools[0]>0?"hammer":"coins";
        static string Quantity(RewardGrant g){int n=0;foreach(var v in g.starting)n+=v;foreach(var v in g.tools)n+=v;return n>0?"×"+n:g.coins.ToString();}
        static void Reward(HomeFrame f,string id,string parent,RewardGrant g,float x,float y,float w,float iconHeight,int font=17,string color=Navy){
            string icon=Icon(g);float iw=icon=="DG_Rocket"?iconHeight*51/43:iconHeight;
            Add(f,id+"-icon",parent,"sprite",icon,x+(w-iw)/2,y,iw,iconHeight);
            Add(f,id+"-quantity",parent,"text",Quantity(g),x,y+iconHeight+2,w,25,font,color);
        }
        public static HomeFrame Build(float width,float height,DailyGiftView state){
            float w=Math.Max(320,width),h=Math.Max(300,height),pw=Math.Min(440,w-24),padding=pw<=321?17:20,bw=pw-padding*2;
            bool shortView=h<=650;float heroH=shortView?120:146,cardH=94,gap=pw<=321?7:9;
            float bodyH=state.error?150:42+heroH+16+42+2*cardH+gap+14+84+10;
            float footerH=state.development?126:110,ph=Math.Min(67+bodyH+footerH+18,h-58),py=Math.Max(44,(h-ph)/2);
            var f=new HomeFrame{width=w,height=h};
            Add(f,"panel","","group","",(w-pw)/2,py,pw,ph);
            Add(f,"shell","panel","sprite","DG_Chrome",0,0,pw,ph,sliced:true);
            Add(f,"header","panel","group","",0,0,pw,67);
            Add(f,"title","header","text",state.error?DailyGiftText.T("Please try again"):DailyGiftDesignText.T("title"),39,2,pw-78,56,pw<=321?27:30,Cream);
            if(!state.error||state.errorDismissible){Add(f,"close","header","group","close",pw-52,-32,46,46);Add(f,"close-art","close","sprite","DG_Close",-2.3f,-2.3f,50.6f,50.6f);}
            float vh=ph-67-footerH-18;
            Add(f,"viewport","panel","group","",padding,67,bw,vh);
            Add(f,"body","viewport","group","",0,0,bw,bodyH);
            Add(f,"intro","body","text",state.error?DailyGiftText.T(state.errorConnection?"The game could not reach the server. Check your connection and try again.":"Your saved game could not be loaded. Please try again."):DailyGiftDesignText.T("intro"),2,0,bw-4,state.error?135:38,state.error?17:14,Muted);
            int current=Math.Max(0,Math.Min(6,state.offer==null?state.claims%7:state.offer.step));bool claimed=state.offer!=null&&state.offer.claimed;
            if(!state.error){
                var schedule=state.schedule??GiftSchedule.Preview();var reward=state.offer?.grant??schedule.days[current];
                Add(f,"hero","body","group","",0,42,bw,heroH);
                Add(f,"hero-well","hero","sprite","DG_Hero",0,0,bw,heroH,sliced:true);
                float left=bw*.46f,rw=bw-left-8;
                Add(f,"chest","hero","sprite","DG_Chest",3,3,left-3,heroH-6);
                Add(f,"hero-label","hero","text",DailyGiftDesignText.T(claimed?"giftCollected":"todayGift"),left,6,rw,32,13,"#88662D");
                Add(f,"reward","hero","group","",left,37,rw,heroH-72);
                if(reward.coins>0&&reward.starting[2]>0){
                    float half=(rw-12)/2;Reward(f,"hero-orb","reward",new RewardGrant{starting=reward.starting},0,0,half,shortView?26:39,20);
                    Add(f,"hero-plus","reward","text","+",half,10,12,25,18,"#AF8B39");
                    Reward(f,"hero-coins","reward",new RewardGrant{coins=reward.coins},half+12,0,half,shortView?26:39,20);
                }else{
                    float sz=shortView?36:46,iw=Icon(reward)=="DG_Rocket"?sz*51/46:sz;
                    Add(f,"hero-icon","reward","sprite",Icon(reward),0,0,iw,sz);
                    Add(f,"hero-quantity","reward","text",Quantity(reward),iw+3,0,rw-iw-3,sz,shortView?29:34);
                }
                if(!shortView)Add(f,"hero-name","hero","text",DailyGiftDesignText.T(reward.coins>0&&reward.starting[2]>0?"bonusRewards":Name(reward)),left,heroH-51,rw,24,12,Muted);
                Add(f,"hero-day","hero","text",DailyGiftDesignText.Day(current+1),left,heroH-29,rw,24,12,"#3A7234");
                float y=42+heroH+16,cw=(bw-gap*2)/3;
                Add(f,"calendar-heading","body","text",DailyGiftDesignText.T("sevenGifts"),0,y,bw*.66f,36,15);
                Add(f,"calendar-progress","body","text",DailyGiftDesignText.T("progress").Replace("{n}",(current+1).ToString()),bw*.68f,y,bw*.32f,36,11,Muted);y+=42;
                for(int i=0;i<6;i++){
                    string id="day-"+i;float cx=i%3*(cw+gap),cy=y+i/3*(cardH+gap);bool done=i<current||i==current&&claimed;
                    Add(f,id,"body","group","",cx,cy,cw,cardH);
                    Add(f,id+"-card",id,"sprite",done?"DG_Collected":i==current?"DG_Today":"DG_Upcoming",0,0,cw,cardH,sliced:true);
                    Add(f,"day-label-"+i,id,"text",DailyGiftDesignText.Day(i+1),4,7,cw-8,20,12,done?"#597963":i==current?"#876124":"#65798E");
                    Reward(f,"day-reward-"+i,id,schedule.days[i],0,28,cw,39);
                    if(done)Add(f,"day-check-"+i,id,"sprite","DG_Check",cw-22,-7,18,18);
                    else if(i==current)Add(f,"today-dot",id,"dot","",cw-14,7,7,7,color:"#63AA50");
                }
                y+=2*cardH+gap+14;
                Add(f,"day-6","body","group","",0,y,bw,84);Add(f,"day-6-card","day-6","sprite","DG_Bonus",0,0,bw,84,sliced:true);
                float noteW=bw*.34f;
                Add(f,"day-label-6","day-6","text",DailyGiftDesignText.Day(7),10,10,noteW-10,26,17,"#FFF0BC");
                Add(f,"bonus-note","day-6","text",DailyGiftDesignText.T(current==6?(claimed?"collected":"today"):"finalGift"),9,36,noteW-8,34,11,"#BED4EC");
                // Compact bonus uses two vertical icon/quantity pairs so localized copy and 150 remain readable.
                float pairW=(bw-noteW-24)/2;
                Reward(f,"bonus-orb","day-6",new RewardGrant{starting=schedule.days[6].starting},noteW,7,pairW,39,17,"#FFF8E7");
                Add(f,"bonus-plus","day-6","text","+",noteW+pairW,22,18,25,16,"#E7C570");
                Reward(f,"bonus-coins","day-6",new RewardGrant{coins=schedule.days[6].coins},noteW+pairW+18,7,pairW,39,17,"#FFF8E7");
                if(current==6&&claimed)Add(f,"day-check-6","day-6","sprite","DG_Check",bw-23,4,18,18);
            }
            Add(f,"footer","panel","group","",padding,ph-footerH-18,bw,footerH);
            bool available=!state.loading&&(state.error||state.pending||state.networkError||state.offer!=null&&!claimed);
            string action=!state.error&&claimed&&!state.loading&&!state.pending&&!state.networkError?"close":available?"claim":"disabled";
            // A plain offer refresh is not a claim: the disabled button keeps its claim label while the status line explains.
            string label=state.loading?(state.claiming?"claiming":"claim"):state.error||state.pending||state.networkError?"retry":claimed?"done":state.offer==null?"Unavailable":"claim";
            Add(f,"claim","footer","group",action,3,8,bw-6,61);
            Add(f,"claim-art","claim","sprite","DG_Primary",0,0,bw-6,61,sliced:true);
            Add(f,"claim-label","claim","text",DailyGiftDesignText.T(label),8,0,bw-22,61,pw<=321?23:25,"#FFFFFF");
            string status=state.loading?DailyGiftText.T(state.claiming?"Claiming your gift...":"Checking your gift..."):state.networkError?DailyGiftText.T("Your gift could not be confirmed. Please try again."):state.error||state.pending?DailyGiftText.T("Please try again"):state.offer==null?DailyGiftText.T("Daily Gift is unavailable. Please try again later."):DailyGiftDesignText.T(claimed?"nextGift":"missed");
            Add(f,"status","footer","text",status,2,73,bw-4,36,11,Muted);
            if(state.development&&!state.error)Add(f,"preview","footer","text",DailyGiftText.T("Preview rewards"),2,108,bw-4,16,10,Muted);
            return f;
        }
    }
}
