using HeartOfTheRain.App.Localization;
using System;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.AppSettings
{
    [Serializable] public sealed class AppSettingsFrame
    {public float width,height,viewportX,viewportY,viewportWidth,viewportHeight;public HomeFrame chrome,content;}
    public static class AppSettingsLayout
    {
        const string Ink="#17354E",Muted="#526F80";
        static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="")
        {var e=new HomeElement{id=id,kind=kind,parent=parent,x=x,y=y,width=w,height=h};f.elements.Add(e);return e;}
        static void Art(HomeFrame f,string id,string key,float x,float y,float w,float h,bool sliced=false,string color="#FFFFFF",string parent="")
        {var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=key;e.sliced=sliced;e.preserveAspect=!sliced;e.color=color;}
        static void Text(HomeFrame f,string id,string value,float x,float y,float w,float h,int size=16,string color=Ink,bool left=false)
        {var e=Add(f,id,left?"lefttext":"text",x,y,w,h);e.text=GameLocale.T(value);e.fontSize=size;e.color=color;}
        static void Hit(HomeFrame f,string id,string action,string label,float x,float y,float w,float h)
        {var e=Add(f,id,"group",x,y,w,h);e.action=action;e.label=GameLocale.T(label);}
        static void Card(HomeFrame f,string id,string title,string subtitle,string icon,string action,float x,float y,float w,float h=60)
        {
            Art(f,id+"-face","AS_Row",x,y,w,h,true);
            Art(f,id+"-icon",icon,x+10,y+7,46,h-14);
            Text(f,id+"-title",title,x+65,y+8,w-98,24,18,Ink,true);
            Text(f,id+"-subtitle",subtitle,x+65,y+31,w-98,19,11,Muted,true);
            Art(f,id+"-arrow","AS_Chevron",x+w-26,y+(h-18)/2,12,18);
            Hit(f,id,action,title,x,y,w,h);
        }
        static void Toggles(HomeFrame f,AppSettingsSession s,float x,float y,float w)
        {
            Art(f,"preferences-face","AS_Well",x,y,w,125,true);
            string[] keys={"music","sound","hints"},labels={"Music","Sound","Hints"},icons={"MusicGlyph","SoundGlyph","HintGlyph"};
            bool[] values={s.Preferences.Music,s.Preferences.Sound,s.Preferences.Hints};float cell=w/3;
            for(int i=0;i<3;i++)
            {
                float bx=x+i*cell;string id="preference-"+keys[i];
                Text(f,id+"-label",labels[i],bx,y+7,cell,24,14);
                Art(f,id+"-disc",values[i]?"ToggleOn":"ToggleOff",bx+(cell-60)/2,y+33,60,60);
                Art(f,id+"-glyph",icons[i],bx+(cell-32)/2,y+43,32,32);
                if(!values[i])Art(f,id+"-slash","OffSlash",bx+(cell-38)/2,y+40,38,38);
                Text(f,id+"-state",values[i]?"On":"Off",bx,y+96,cell,22,12,values[i]?"#286B40":Muted);
                Hit(f,id,"toggle:"+keys[i],labels[i]+(values[i]?", on":", off"),bx+3,y+31,cell-6,88);
            }
        }
        static void Inventory(HomeFrame f,AppSettingsSession s,float w)
        {
            string[][] labels={new[]{"Rocket","Bomb","Rainbow\nOrb","Golden\nSeeker"},new[]{"Hammer","Axe","Ram","Atlas"}};
            int first=f.elements.Count;float offset=(f.width-w)/2;float cell=(w-24)/4,stride=115+cell;
            for(int row=0;row<2;row++)
            {
                float y=row*stride;
                Text(f,"inventory-heading-"+row,row==0?"Starting boosters":"Level tools",0,y,w,26,21);
                Text(f,"inventory-note-"+row,row==0?"Choose before a level":"Provided at the start of each level",0,y+27,w,20,11,Muted);
                for(int i=0;i<4;i++)
                {
                    float x=i*(cell+8),size=Math.Min(cell-10,64);string id="inventory-"+row+"-"+i;
                    Art(f,id+"-well","AS_Well",x,y+51,cell,cell+6,true);
                    if(row==0)RewardIconLayout.StartingBooster(f,id,i,x+(cell-size)/2,y+56,size,"");
                    else RewardIconLayout.Tool(f,id,i,x+(cell-size)/2,y+56,size,"");
                    Text(f,id+"-count","×"+(row==0?s.StartingCount(i):s.ToolCount(i)),x,y+51+cell+9,cell,22,16);
                    Text(f,id+"-name",labels[row][i],x-0,y+51+cell+32,cell,28,11);
                }
            }
            float by=2*stride+8;Art(f,"inventory-shop-face","AS_Primary",(w-210)/2,by,210,48,true);Text(f,"inventory-shop-label","View Shop",(w-210)/2,by,210,46,19,"#FFFFFF");Hit(f,"inventory-shop","shop","View Shop",(w-210)/2,by,210,48);
            f.height=by+54;for(int i=first;i<f.elements.Count;i++)f.elements[i].x+=offset;
        }
        public static AppSettingsFrame Build(float width,float height,AppSettingsSession s)
        {
            float w=Math.Max(320,width),h=Math.Max(300,height);bool wide=w>=650&&w/h>1.3f;
            float pw=wide?Math.Min(720,w-24):Math.Min(368,w-24),ph=Math.Min(wide?394:604,h-24),px=(w-pw)/2,py=(h-ph)/2;
            var c=new HomeFrame{width=w,height=h};var body=new HomeFrame{width=pw-40};
            var r=new AppSettingsFrame{width=w,height=h,chrome=c,content=body,viewportX=px+20,viewportY=py+82,viewportWidth=pw-40,viewportHeight=ph-154};
            var scrim=Add(c,"backdrop","color",0,0,w,h);scrim.color="#071827BF";
            Art(c,"settings-shell","ModalShell_R2",px,py,pw,ph,true);
            string title=s.Page=="main"?"Settings":s.Page=="inventory"?"Inventory":s.Page=="language"?"Language":s.Page=="help"?"Help & Support":s.Page=="follow"?"Follow Us":s.NoticeTitle;
            Text(c,"page-title",title,px+52,py+18,pw-104,37,s.Page=="notice"?23:27,"#FFFFFF");
            Art(c,"close-art","Close",px+pw-44,py+25,30,30);Hit(c,"close","close","Close settings",px+pw-51,py+18,44,44);
            float bw=body.width;
            if(s.Page=="main")
            {
                float col=wide?(bw-20)/2:bw;Toggles(body,s,0,0,col);
                if(wide)
                {
                    Card(body,"inventory","Inventory","Boosters & tools","SP_Treasury","inventory",0,133,col,56);
                    Card(body,"language","Language",AppSettingsSession.LanguageNames[s.Language],"AS_Globe","language",col+20,0,col,56);
                    Card(body,"help","Help & Support","Tips and answers","AS_Support","help",col+20,64,col,56);
                    Card(body,"follow","Follow Us","News from the village","AS_Follow","follow",col+20,128,col,56);body.height=190;
                }
                else
                {
                    Card(body,"inventory","Inventory","Boosters & tools","SP_Treasury","inventory",0,139,bw,66);
                    Card(body,"language","Language",AppSettingsSession.LanguageNames[s.Language],"AS_Globe","language",0,215,bw);
                    Card(body,"help","Help & Support","Tips and answers","AS_Support","help",0,285,bw);
                    Card(body,"follow","Follow Us","News from the village","AS_Follow","follow",0,355,bw);body.height=421;
                }
                float fy=py+ph-56,half=(pw-48)/2;
                Text(c,"terms-label","Terms of Service",px+24,fy,half,44,12,"#FFF2D4");Hit(c,"terms","link:terms","Terms of Service",px+24,fy,half,44);
                Text(c,"privacy-label","Privacy Policy",px+24+half,fy,half,44,12,"#FFF2D4");Hit(c,"privacy","link:privacy","Privacy Policy",px+24+half,fy,half,44);
            }
            else
            {
                if(s.Page=="inventory")Inventory(body,s,Math.Min(bw,400));
                else if(s.Page=="language")
                {
                    Text(body,"language-intro","Choose your game language",0,0,bw,28,15);
                    for(int i=0;i<AppSettingsSession.LanguageNames.Length;i++)
                    {
                        float y=40+i*61;string id="language-"+i;Art(body,id+"-face","AS_Row",0,y,bw,53,true);
                        // Native names remain legible regardless of the current interface language.
                        string label=AppSettingsSession.LanguageNames[i];Text(body,id+"-label",label,16,y+4,bw-76,44,17,Ink,true);
                        if(i==s.Language)Art(body,id+"-check","SelectionTick_R2",bw-47,y+12,27,27);
                        
                        Hit(body,id,"language:"+i,label+(i==s.Language?", selected":""),0,y,bw,53);
                    }body.height=40+AppSettingsSession.LanguageNames.Length*61;
                }
                else if(s.Page=="help")
                {
                    string[] questions={"How do I play?","How do boosters work?","What happens when I exit?"};
                    string[] answers={"Swap neighboring tiles to match three.\nClear the targets before your moves\nrun out.","Choose starting boosters before a level.\nUse tools from the gameplay toolbar.\nCombine power-ups for bigger effects.","Leaving an unfinished level costs a life.\nCancel the exit to continue playing.\nTry Again starts the level afresh."};
                    float y=0;
                    for(int i=0;i<3;i++)
                    {
                        string id="help-"+i;bool expanded=s.ExpandedHelp==i;Art(body,id+"-face","AS_Row",0,y,bw,expanded?132:54,true);
                        Text(body,id+"-question",questions[i],14,y+5,bw-48,44,15,Ink,true);Text(body,id+"-mark",expanded?"−":"+",bw-36,y+4,24,44,23,Muted);Hit(body,id,"faq:"+i,questions[i]+(expanded?", expanded":", collapsed"),0,y,bw,54);
                        if(expanded)Text(body,id+"-answer",answers[i],14,y+57,bw-28,64,12,Muted,true);y+=expanded?142:64;
                    }
                    Card(body,"contact","Contact Support",s.LinkAvailable("support")?"Open the support center":"Available soon","AS_Support","link:support",0,y+8,bw);body.height=y+76;
                }
                else if(s.Page=="follow")
                {
                    Art(body,"follow-emblem","AS_Follow",(bw-80)/2,5,80,80);Text(body,"follow-intro","Stay close to the village",0,95,bw,30,19);
                    string[] keys={"instagram","youtube","facebook"},names={"Instagram","YouTube","Facebook"};
                    for(int i=0;i<3;i++)Card(body,"social-"+keys[i],names[i],s.LinkAvailable(keys[i])?"Open official channel":"Coming soon","AS_Follow","link:"+keys[i],0,146+i*72,bw);
                    body.height=356;
                }
                else
                {
                    Art(body,"notice-icon","AS_Document",(bw-76)/2,8,76,76);Text(body,"notice-message",s.NoticeText,4,105,bw-8,70,14,Muted);body.height=190;
                }
                float fy=py+ph-58;
                Art(c,"return-face","AS_Primary",px+(pw-218)/2,fy,218,46,true);Text(c,"return-label",s.Page=="notice"?"Back":"Back to Settings",px+(pw-218)/2,fy,218,44,17,"#FFFFFF");Hit(c,"return","back","Back",px+(pw-218)/2,fy,218,46);
            }
            body.height=Math.Max(body.height,r.viewportHeight);return r;
        }
    }
}
