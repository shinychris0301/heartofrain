using System;
namespace HeartOfTheRain.M48 {
    public static class InteractionGate {
        public static bool CanAct(bool ready,bool busy,bool paused,bool blocked,string status)=>ready&&!busy&&!paused&&!blocked&&status=="Playing";
    }
    public struct ReviewLayout {
        public float height,cell;
        public static ReviewLayout Compute(float width,float height,int columns,int rows) {
            if(width<=0||height<=0||columns<1||rows<1)throw new ArgumentOutOfRangeException("Invalid safe area or board dimensions");
            float logicalHeight=height*720/width;
            return new ReviewLayout{height=logicalHeight,cell=Math.Max(1,Math.Min(676f/columns,(logicalHeight-460)/rows))};
        }
    }
}
