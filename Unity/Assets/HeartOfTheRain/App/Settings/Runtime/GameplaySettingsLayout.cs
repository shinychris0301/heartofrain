using HeartOfTheRain.App.Localization;
using System;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Settings
{
    public static class GameplaySettingsLayout
    {
        static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="panel")
        {var e=new HomeElement{id=id,kind=kind,parent=parent,x=x,y=y,width=w,height=h};f.elements.Add(e);return e;}
        static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool sliced=false)
        {var e=Add(f,id,"sprite",x,y,w,h);e.asset=asset;e.sliced=sliced;e.preserveAspect=!sliced;}
        static void Text(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string color="#17354E",bool shadow=false)
        {var e=Add(f,id,"text",x,y,w,h);e.text=GameLocale.Element(id,text);e.fontSize=size;e.color=color;e.shadow=shadow;}
        static void Hit(HomeFrame f,string id,string action,string label,float x,float y,float w,float h)
        {var e=Add(f,id,"group",x,y,w,h);e.action=action;e.label=GameLocale.T(label);}
        public static HomeFrame Build(float width,float height,GameSettingsState state)
        {
            float w=Math.Max(320,width),h=Math.Max(300,height);bool wide=w>=640&&w/h>=1.35f;
            float pw=wide?480:Math.Min(344,w-24),ph=wide?316:382;
            var f=new HomeFrame{width=w,height=Math.Max(h,ph+24),landscape=wide,compact=!wide&&h<570};
            Add(f,"panel","group",(w-pw)/2,(f.height-ph)/2,pw,ph,"");
            Art(f,"panel-art","ModalShell_R2",0,0,pw,ph,true);
            Text(f,"title","Settings",50,15,pw-100,40,30,"#FFFFFF",true);
            string[] keys={"music","sound","hints"},labels={"Music","Sound","Hints"};bool[] values={state.Music,state.Sound,state.Hints};
            float span=wide?328:pw-48,cell=span/3,start=(pw-span)/2;
            for(int i=0;i<3;i++)
            {
                string id=keys[i];float x=start+i*cell;bool on=values[i];
                Text(f,id+"-label",labels[i],x,82,cell,24,17);
                Art(f,id+"-disc",on?"ToggleOn":"ToggleOff",x+(cell-74)/2,111,74,74);
                Art(f,id+"-icon",i==0?"MusicGlyph":i==1?"SoundGlyph":"HintGlyph",x+(cell-42)/2,125,42,42);
                if(!on)Art(f,id+"-slash","OffSlash",x+(cell-48)/2,122,48,48);
                Text(f,id+"-state",on?"On":"Off",x,192,cell,22,14,on?"#286B40":"#526777");
                Hit(f,id,"toggle:"+id,labels[i]+(on?", on":", off"),x+(cell-Math.Min(84,cell-6))/2,110,Math.Min(84,cell-6),107);
            }
            if(!wide)
            {
                Art(f,"divider","SectionDivider_R2",(pw-250)/2,229,250,2);
                Art(f,"exit-art","ExitButton",(pw-182)/2,244,182,43,true);
                Text(f,"exit-text","Exit Level",(pw-160)/2,244,160,38,18,"#FFFFFF",true);
                Hit(f,"exit","exit","Exit level; confirmation required",(pw-182)/2,241,182,47);
            }
            else
            {
                Art(f,"exit-art","ExitButton",37,252,163,44,true);
                Text(f,"exit-text","Exit Level",42,252,153,39,18,"#FFFFFF",true);
                Hit(f,"exit","exit","Exit level; confirmation required",37,250,163,48);
            }
            float rx=wide?217:(pw-228)/2,ry=ph-72,rw=wide?228:228;
            Art(f,"resume-art","R4_Start",rx,ry,rw,66);
            Text(f,"resume-text","Continue",rx+12,ry+10,rw-24,43,27,"#FFFFFF",true);
            Hit(f,"resume","resume","Continue level",rx,ry,rw,66);
            Art(f,"close-art","Close",pw-44,24,32,32);Hit(f,"close","resume","Close settings and continue",pw-50,18,44,44);
            return f;
        }
    }
}
