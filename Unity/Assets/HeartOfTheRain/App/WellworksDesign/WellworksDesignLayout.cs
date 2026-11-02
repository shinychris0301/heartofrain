using System;
using System.Linq;
using System.Collections.Generic;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Profile {
    public static class WellworksDesignLayout {
        const string Navy="#163A61",Muted="#718494",Cream="#FFF4D7";
        static void Add(HomeFrame f,string id,string parent,string kind,string value,float x,float y,float w,float h,int font=14,string color=Navy,bool sliced=false){var e=new HomeElement{id=id,parent=parent,kind=kind,x=x,y=y,width=w,height=h,fontSize=font,color=color,sliced=sliced,preserveAspect=!sliced};if(kind=="text")e.text=value;else if(kind=="sprite"){e.asset=value;e.color="#FFFFFF";}else e.action=value;f.elements.Add(e);}
        public static List<KeyValuePair<string,int>> Rewards(RewardGrant g){var list=new List<KeyValuePair<string,int>>();if(g.coins>0)list.Add(new KeyValuePair<string,int>("DG_Coin",g.coins));string[] starts={"DG_Rocket","DG_Bomb","DG_Orb","WW_Golden"};for(int i=0;i<4;i++)if(g.starting[i]>0)list.Add(new KeyValuePair<string,int>(starts[i],g.starting[i]));string[] tools={"DG_Hammer","boosterAxe","boosterRam","boosterAtlas"};for(int i=0;i<4;i++)if(g.tools[i]>0)list.Add(new KeyValuePair<string,int>(tools[i],g.tools[i]));return list;}
        public static HomeFrame Build(float width,float height,WellworksView v){
            float w=Math.Max(320,width),h=Math.Max(300,height);bool wide=w>=650&&h<=550;float pw=Math.Min(wide?720:440,w-24),pad=pw<=321?17:20,bw=pw-pad*2;bool small=pw<=321,shortView=h<=650;
            var stages=v.schedule?.milestones??new WellworksMilestone[0];int progress=v.player?.completed??0,collected=v.player==null?0:stages.Count(m=>WellworksService.Claimed(v.player,m.level)),ready=v.player==null||!v.enabled?0:stages.Count(m=>progress>=m.level&&!WellworksService.Claimed(v.player,m.level));
            float heroH=shortView?124:128,rowGap=8,headingH=32,rowsH=stages.Length*73+Math.Max(0,stages.Length-1)*rowGap+5;
            float introH=36,heroW=wide?bw*.4f-8:bw,listW=wide?bw-heroW-16:bw,listX=wide?heroW+16:0,listY=wide?introH:introH+heroH+12,bodyH=v.error?155:wide?introH+Math.Max(heroH,headingH+rowsH)+4:listY+headingH+rowsH+4;
            float footerH=70,ph=Math.Min(67+bodyH+footerH+22,h-58),py=Math.Max(44,(h-ph)/2);var f=new HomeFrame{width=w,height=h};
            Add(f,"panel","","group","",(w-pw)/2,py,pw,ph);Add(f,"shell","panel","sprite","DG_Chrome",0,0,pw,ph,sliced:true);Add(f,"header","panel","group","",0,0,pw,67);
            Add(f,"title","header","text",v.error?WellworksText.T("Please try again"):WellworksDesignText.T("title"),40,2,pw-80,56,small?27:30,Cream);
            Add(f,"close","header","group","close",pw-52,-32,46,46);Add(f,"close-art","close","sprite","DG_Close",-2.3f,-2.3f,50.6f,50.6f);
            Add(f,"viewport","panel","group","",pad,67,bw,ph-67-footerH-22);Add(f,"body","viewport","group","",0,0,bw,bodyH);
            Add(f,"intro","body","text",v.error?WellworksText.T("Your saved game could not be loaded. Please try again."):WellworksDesignText.T("intro"),2,0,bw-4,v.error?145:introH,small?12:14,Muted);
            if(!v.error){
                Add(f,"hero","body","group","",0,introH,heroW,heroH);Add(f,"hero-well","hero","sprite","DG_Hero",0,0,heroW,heroH,sliced:true);
                float left=heroW*.44f,right=heroW-left-12;Add(f,"well","hero","sprite","WW_Well",3,3,left-3,heroH-6);
                Add(f,"progress-label","hero","text",WellworksDesignText.T("completedLevels"),left,2,right,32,13,"#88662D");
                Add(f,"progress-count","hero","text",progress+" / 50",left,30,right,38,small?27:32);
                Add(f,"progress-track","hero","group","",left,69,right,21);Add(f,"track","progress-track","sprite","WW_Track",0,0,right,21,sliced:true);
                Add(f,"progress-clip","progress-track","group","",4,4,(right-8)*Math.Max(0,Math.Min(1,progress/50f)),13);Add(f,"fill","progress-clip","sprite","WW_Fill",0,0,Math.Max(12,(right-8)*Math.Max(0,Math.Min(1,progress/50f))),13,sliced:true);
                var next=stages.FirstOrDefault(m=>progress<m.level);string key=collected==stages.Length&&stages.Length>0?"complete":ready==1?"oneReady":ready>1?"manyReady":"next";
                string heroStatus=!v.enabled?WellworksText.T("Rewards coming soon"):WellworksDesignText.N(key,ready>0?ready:next==null?0:next.level-progress);
                Add(f,"progress-status","hero","text",heroStatus,left,92,right,heroH-94,small?10:12,"#56834A");
                Add(f,"heading","body","text",WellworksDesignText.T("rewards"),listX,listY,listW*.64f,headingH,small?14:15);
                Add(f,"collected-count","body","text",WellworksDesignText.N("collectionCount",collected,stages.Length),listX+listW*.66f,listY,listW*.34f,headingH,10,Muted);
                float y=listY+headingH;
                for(int i=0;i<stages.Length;i++){
                    var m=stages[i];bool done=v.player!=null&&WellworksService.Claimed(v.player,m.level),eligible=v.enabled&&progress>=m.level&&!done,final=m.level==50;float rh=final?78:73;
                    string id="stage-"+i;Add(f,id,"body","group","",listX,y,listW,rh);Add(f,id+"-card",id,"sprite",final?"DG_Bonus":done?"DG_Collected":eligible?"DG_Today":"DG_Upcoming",0,0,listW,rh,sliced:true);
                    float inset=small?9:12,badge=small?38:43,action=small?72:77,gap=small?6:9,ax=listW-inset-action,rx=inset+badge+gap,rw=ax-gap-rx;string color=final?"#FFF8DE":Navy;
                    Add(f,id+"-badge",id,"sprite","WW_Badge",inset,8,badge,40);Add(f,"stage-title-"+i,id,"text",m.level.ToString(),inset,9,badge,31,21,"#FFFFFF");Add(f,id+"-levels",id,"text",WellworksDesignText.T("levels"),inset-1,49,badge+2,18,9,final?"#BED4EC":Muted);
                    Add(f,"rewards-"+i,id,"group","",rx,4,rw,rh-8);var receipt=v.player?.rewards.Find(r=>r.key==WellworksService.Key(m.level));var rewards=Rewards(receipt?.grant??m.grant);float cell=rw/Math.Max(1,rewards.Count),icon=small?35:40;
                    for(int j=0;j<rewards.Count;j++){var r=rewards[j];float iw=r.Key=="DG_Rocket"?icon*1.2f:icon;Add(f,"reward-"+i+"-"+j,"rewards-"+i,"sprite",r.Key,j*cell+(cell-iw)/2,0,iw,icon);Add(f,"quantity-"+i+"-"+j,"rewards-"+i,"text",(r.Key=="DG_Coin"?"":"×")+r.Value,j*cell,icon+1,cell,25,17,color);}
                    if(eligible){Add(f,"claim-"+i,id,"group","claim-"+m.level,ax,(rh-44)/2,action,44);Add(f,"claim-"+i+"-art","claim-"+i,"sprite","DG_Primary",0,0,action,44,sliced:true);Add(f,"claim-"+i+"-label","claim-"+i,"text",WellworksDesignText.T("claim"),small?6:7,0,action-(small?12:14),44,small?14:17,"#FFFFFF");}
                    else{Add(f,"state-icon-"+i,id,"sprite",done?"DG_Check":"WW_Lock",ax+(action-23)/2,12,23,23);Add(f,"state-label-"+i,id,"text",WellworksDesignText.T(done?"collected":"locked"),ax-1,38,action+2,29,10,final?"#BED4EC":done?"#56834A":Muted);}
                    y+=rh+rowGap;
                }
            }
            Add(f,"footer","panel","group","",pad,ph-footerH-22,bw,footerH);
            if(v.error){Add(f,"retry","footer","group","retry",(bw-170)/2,2,170,44);Add(f,"retry-art","retry","sprite","DG_Primary",0,0,170,44,sliced:true);Add(f,"retry-label","retry","text",WellworksText.T("Please try again"),7,0,156,44,17,"#FFFFFF");}
            else{
                string status=v.claimError?"error":v.received?"collectedNotice":"persistent";Add(f,"status","footer","text",WellworksDesignText.T(status),5,4,bw-10,42,small?10:11,Muted);
                Add(f,"preview","footer","text",DailyGiftText.T("Preview rewards"),5,48,bw-10,18,10,Muted);
            }
            return f;
        }
    }
}
