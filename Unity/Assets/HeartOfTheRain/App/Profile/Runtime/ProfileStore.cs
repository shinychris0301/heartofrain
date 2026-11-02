using System;
using UnityEngine;
namespace HeartOfTheRain.App.Profile
{
    public interface IAppearancePreferences
    {
        string Read();
        void Write(string json);
        void Flush();
    }
    // Appearance is a local preference, separate from the durable campaign/economy ledger.
    sealed class PlayerAppearancePreferences : IAppearancePreferences
    {
        readonly string key;
        public PlayerAppearancePreferences(string key=ProfileStore.Key){if(string.IsNullOrEmpty(key))throw new ArgumentException("Appearance key is required",nameof(key));this.key=key;}
        public string Read()=>PlayerPrefs.GetString(key,"{}");
        public void Write(string json)=>PlayerPrefs.SetString(key,json);
        public void Flush()=>PlayerPrefs.Save();
    }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
    public sealed class MemoryAppearancePreferences : IAppearancePreferences
    {
        string json="{}";
        public string Read()=>json;
        public void Write(string value){json=value;}
        public void Flush(){}
    }
#endif
    // Local appearance preferences only. This is not cloud identity or an economy save.
    public sealed class ProfileStore
    {
        public const string Key="HeartOfTheRain.Profile.v1";
        ProfileData value;
        readonly IAppearancePreferences preferences;
        public ProfileData Snapshot=>value.Copy();
        public event Action<ProfileData> Changed;
        public ProfileStore(IAppearancePreferences preferences=null)
        {
            this.preferences=preferences??new PlayerAppearancePreferences();
            try {value=ProfileRules.Sanitize(JsonUtility.FromJson<ProfileData>(this.preferences.Read()));}
            catch(Exception){value=new ProfileData();Debug.LogWarning("Profile preferences could not be read; default appearance is in use.");}
        }
        public bool Rename(string name,out string error)
        {
            string clean;if(!ProfileRules.TryName(name,out clean,out error))return false;
            var next=value.Copy();next.displayName=clean;return Commit(next,out error);
        }
        public bool Select(int tab,string id,out string error)
        {
            error="selection-invalid";var next=value.Copy();
            if(tab==0&&ProfileRules.Contains(ProfileRules.Avatars,id))next.avatarId=id;
            else if(tab==1&&ProfileRules.Contains(ProfileRules.Banners,id))next.bannerId=id;
            else if(tab==2&&ProfileRules.Contains(ProfileRules.Frames,id))next.frameId=id;
            else return false;
            return Commit(next,out error);
        }
        bool Commit(ProfileData next,out string error)
        {
            error="";string previous=JsonUtility.ToJson(value);
            try {preferences.Write(JsonUtility.ToJson(next));preferences.Flush();}
            catch(Exception){try{preferences.Write(previous);}catch(Exception){}error="save-failed";return false;}
            value=next;Changed?.Invoke(Snapshot);return true;
        }
    }
}
