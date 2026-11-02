using System;
namespace HeartOfTheRain.App.Celebrations
{
    [Serializable] public struct RigPoint {public float x,y;public RigPoint(float x,float y){this.x=x;this.y=y;}}
    [Serializable] public struct RigPose {public float bodyX,bodyY,bodyAngle,headAngle,headY,leftShoulder,rightShoulder,leftElbow,rightElbow;}
    [Serializable] public struct RigRect {public float x,y,width,height;public RigRect(float x,float y,float w,float h){this.x=x;this.y=y;this.width=w;this.height=h;}}
    public static class DariaRigMotion
    {
        // All values are analytic in active seconds. There are no pose holds or frame indices.
        public static RigPose Sample(float seconds,int variant,bool reduced)
        {
            if(reduced)return new RigPose{leftShoulder=10,rightShoulder=-10,leftElbow=5,rightElbow=-5};
            float t=Math.Max(0,seconds),wave=.5f-.5f*(float)Math.Cos(t*3.8f),lag=.5f-.5f*(float)Math.Cos(Math.Max(0,t-.075f)*3.8f);
            return new RigPose{bodyX=.004f*(float)Math.Sin(t*2.7f),bodyY=-.007f*(float)Math.Sin(t*3.8f),bodyAngle=.65f*(float)Math.Sin(t*2.6f),
                headAngle=1.8f*(float)Math.Sin(t*3.1f),headY=.003f*(float)Math.Sin(t*7.6f),
                leftShoulder=4+10*wave,rightShoulder=-4-10*lag,leftElbow=3+6*wave,rightElbow=-3-6*lag};
        }
        // Character space is top-left based and independent of texture resolution.
        public static RigRect Bounds(int part)
        {
            switch(part){case 0:return new RigRect(.22f,.405f,.56f,.4745f);
                case 1:return new RigRect(.335f,.105f,.33f,.3950f);
                case 2:return new RigRect(-.024f,.4334f,.45f,.296f);
                default:return new RigRect(.574f,.4334f,.45f,.296f);}
        }
        public static float ForearmWeight(int part,float u)
        {float f=part==2?( .80f-u)/.26f:(u-.20f)/.26f;f=Math.Max(0,Math.Min(1,f));return f*f*(3-2*f);}
        // Sleeve roots stay attached to the torso beneath the cape. The lower sleeve
        // gradually follows the shoulder; the cuff and bare forearm move together.
        public static float ShoulderWeight(int part,float u,float v)
        {
            var r=Bounds(part);bool left=part==2;float x=r.x+u*r.width,y=r.y+v*r.height;
            float dx=left?-.09f:.09f,dy=.181f;
            float along=((x-(left?.374f:.626f))*dx+(y-.48f)*dy)/(dx*dx+dy*dy);
            float f=Math.Max(0,Math.Min(1,(along-.14f)/.71f));return Math.Max(f*f*(3-2*f),ForearmWeight(part,u));
        }
        static RigPoint Rotate(RigPoint point,RigPoint pivot,float degrees)
        {float a=degrees*(float)Math.PI/180,c=(float)Math.Cos(a),s=(float)Math.Sin(a),x=point.x-pivot.x,y=point.y-pivot.y;return new RigPoint(pivot.x+x*c-y*s,pivot.y+x*s+y*c);}
        public static RigPoint Vertex(int part,float u,float v,RigPose pose)
        {
            var r=Bounds(part);var p=new RigPoint(r.x+u*r.width,r.y+v*r.height);
            if(part==1){p=Rotate(p,new RigPoint(.5f,.469f),pose.headAngle);p.y+=pose.headY;}
            else if(part>=2)
            {
                bool left=part==2;var shoulder=new RigPoint(left?.374f:.626f,.48f);
                var elbow=new RigPoint(left?.284f:.716f,.661f);
                var lower=Rotate(p,elbow,left?pose.leftElbow:pose.rightElbow);float weight=ForearmWeight(part,u);
                var bent=new RigPoint(p.x+(lower.x-p.x)*weight,p.y+(lower.y-p.y)*weight);
                bent=Rotate(bent,shoulder,left?pose.leftShoulder:pose.rightShoulder);
                float shoulderWeight=ShoulderWeight(part,u,v);
                p=new RigPoint(p.x+(bent.x-p.x)*shoulderWeight,p.y+(bent.y-p.y)*shoulderWeight);
            }
            p=Rotate(p,new RigPoint(.5f,.70f),pose.bodyAngle);p.x+=pose.bodyX;p.y+=pose.bodyY;return p;
        }
    }
}
