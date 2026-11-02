using System;
using System.Globalization;
using System.Text;
namespace HeartOfTheRain.App.Profile
{
    [Serializable] public sealed class ProfileData
    {
        public int version=1;
        public string displayName="Rainkeeper", avatarId="Ivan", bannerId="Village", frameId="Gold";
        public ProfileData Copy()=>new ProfileData {version=version,displayName=displayName,avatarId=avatarId,bannerId=bannerId,frameId=frameId};
    }
    public static class ProfileRules
    {
        public static readonly string[] Avatars={"Ivan","Dariya","Raindrop","Lantern","Heart","Compass"};
        public static readonly string[] Banners={"Village","Twilight","Lantern"};
        public static readonly string[] Frames={"Gold","Sapphire","Ivory","RainkeeperGold","LanternSapphire","GardenIvory"};
        public static bool Contains(string[] values,string id)=>Array.IndexOf(values,id)>=0;
        public static bool TryName(string input,out string value,out string error)
        {
            value="";error="name-empty";
            if(string.IsNullOrWhiteSpace(input))return false;
            try {value=input.Trim().Normalize(NormalizationForm.FormC);} catch(ArgumentException){error="name-invalid";return false;}
            var e=StringInfo.GetTextElementEnumerator(value);int count=0;
            while(e.MoveNext())count++;
            if(count>20){error="name-long";return false;}
            for(int i=0;i<value.Length;i++)
            {
                if(char.IsSurrogate(value[i])&&(!char.IsHighSurrogate(value[i])||i+1>=value.Length||!char.IsLowSurrogate(value[i+1])))
                {error="name-invalid";return false;}
                UnicodeCategory c=CharUnicodeInfo.GetUnicodeCategory(value,i);
                if(c==UnicodeCategory.Control||c==UnicodeCategory.Format||c==UnicodeCategory.LineSeparator||c==UnicodeCategory.ParagraphSeparator)
                {error="name-invalid";return false;}
                if(char.IsHighSurrogate(value[i]))i++;
            }
            error="";return true;
        }
        public static ProfileData Sanitize(ProfileData input)
        {
            var d=input==null?new ProfileData():input.Copy();string name,error;
            if(!TryName(d.displayName,out name,out error))name="Rainkeeper";
            d.displayName=name;d.version=1;
            if(!Contains(Avatars,d.avatarId))d.avatarId="Ivan";
            if(!Contains(Banners,d.bannerId))d.bannerId="Village";
            if(!Contains(Frames,d.frameId))d.frameId="Gold";
            return d;
        }
    }
}
