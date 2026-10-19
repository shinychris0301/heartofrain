using HeartOfTheRain.App.Localization;
using System;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.EndLevel
{
    public static class EndLevelLayout
    {
        static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="panel")
        {var e=new HomeElement{id=id,kind=kind,parent=parent,x=x,y=y,width=w,height=h};f.elements.Add(e);return e;}
        static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool sliced=false)
        {var e=Add(f,id,"sprite",x,y,w,h);e.asset=asset;e.sliced=sliced;e.preserveAspect=!sliced;}
        static void Text(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string color="#17354E",bool shadow=false)
        {var e=Add(f,id,"text",x,y,w,h);e.text=GameLocale.Element(id,text);e.fontSize=size;e.color=color;e.shadow=shadow;}
        static void Hit(HomeFrame f,string id,string action,string label,float x,float y,float w,float h)
        {var e=Add(f,id,"group",x,y,w,h);e.action=action;e.label=GameLocale.T(label);}
        public static HomeFrame Build(float width,float height,EndLevelViewData state)
        {
            float w=Math.Max(320,width),h=Math.Max(300,height);bool wide=w>=640&&w/h>=1.35f;
            float pw=wide?500:Math.Min(344,w-24),ph=wide?316:424;
            var f=new HomeFrame{width=w,height=Math.Max(h,ph+24),landscape=wide,compact=!wide&&h<570};
            Add(f,"panel","group",(w-pw)/2,(f.height-ph)/2,pw,ph,"");
            Art(f,"panel-art","ModalShell_R2",0,0,pw,ph,true);
            Text(f,"title","End Level?",45,15,pw-90,40,28,"#FFFFFF",true);
            if(wide)
            {
                Art(f,"ivan","Avatar_Ivan_Home",31,90,108,118);
                Art(f,"life-heart","LifeLostHeart",139,78,132,132);
                if(state.lives>0){Art(f,"loss-badge","QuantityBadge_R2",230,180,34,25);Text(f,"loss-number","−1",232,181,30,21,15,"#FFFFFF",true);}
                Text(f,"warning-a",state.lives>0?"You’ll lose":"No lives",278,105,194,27,20);
                Text(f,"warning-b",state.lives==1?"your last life.":state.lives>1?"1 life.":"remaining.",278,134,194,30,24,"#9E3D43");
                Text(f,"consequence","Level progress will be lost.",272,174,206,25,12,"#526777");
                Art(f,"exit-art","ExitButton",37,252,163,44,true);
                Text(f,"exit-text","Exit Level",42,252,153,39,18,"#FFFFFF",true);
                Hit(f,"exit","confirm","End level and lose one life",37,250,163,48);
            }
            else
            {
                float offset=(pw-344)/2;
                Art(f,"ivan","Avatar_Ivan_Home",31+offset,91,126,137);
                Art(f,"life-heart","LifeLostHeart",166+offset,81,148,148);
                if(state.lives>0){Art(f,"loss-badge","QuantityBadge_R2",271+offset,193,34,25);Text(f,"loss-number","−1",273+offset,194,30,21,15,"#FFFFFF",true);}
                string warning=state.lives==1?"You’ll lose your last life.":state.lives>1?"You’ll lose 1 life.":"No lives remaining.";
                Text(f,"warning",warning,20,237,pw-40,28,state.lives==1?18:21);
                Text(f,"consequence","Level progress will be lost.",20,268,pw-40,22,13,"#526777");
                Art(f,"exit-art","ExitButton",(pw-182)/2,299,182,43,true);
                Text(f,"exit-text","Exit Level",(pw-160)/2,299,160,38,18,"#FFFFFF",true);
                Hit(f,"exit","confirm","End level and lose one life",(pw-182)/2,297,182,47);
            }
            float kx=wide?237:(pw-228)/2,ky=ph-72;
            Art(f,"keep-art","R4_Start",kx,ky,228,66);
            Text(f,"keep-text","Keep Playing",kx+12,ky+10,204,43,22,"#FFFFFF",true);
            Hit(f,"keep","cancel","Keep playing without losing a life",kx,ky,228,66);
            Art(f,"close-art","Close",pw-44,24,32,32);Hit(f,"close","cancel","Cancel exit and keep playing",pw-50,18,44,44);
            return f;
        }
    }
}
