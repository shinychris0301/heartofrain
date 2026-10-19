using System;
namespace HeartOfTheRain.App.Settings
{
    public interface ISettingsStore { int Read(string key,int fallback); void Write(string key,int value); void Flush(); }
    public sealed class GameSettingsState
    {
        readonly ISettingsStore store;
        public bool Music {get;private set;} public bool Sound {get;private set;} public bool Hints {get;private set;}
        const string Prefix="HeartOfTheRain.Settings.v1.";
        public GameSettingsState(ISettingsStore storage)
        {store=storage;Music=store.Read(Prefix+"music",1)!=0;Sound=store.Read(Prefix+"sound",1)!=0;Hints=store.Read(Prefix+"hints",1)!=0;}
        public bool Toggle(string key)
        {
            bool value;
            switch(key){case "music":Music=!Music;value=Music;break;case "sound":Sound=!Sound;value=Sound;break;case "hints":Hints=!Hints;value=Hints;break;default:return false;}
            store.Write(Prefix+key,value?1:0);store.Flush();return true;
        }
    }
    // Wait only while the player can act. A suggestion is latched until interaction or a board transition.
    public sealed class IdleHintGate
    {
        float elapsed; bool offered;
        public void Reset(){elapsed=0;offered=false;}
        public bool Tick(float dt,bool eligible)
        {if(!eligible){Reset();return false;}if(offered)return false;elapsed+=Math.Max(0,dt);if(elapsed<6)return false;offered=true;return true;}
    }
}
