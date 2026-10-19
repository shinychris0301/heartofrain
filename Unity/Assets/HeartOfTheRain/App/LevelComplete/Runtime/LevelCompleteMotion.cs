using System;
namespace HeartOfTheRain.App.LevelComplete {
 [Serializable]public sealed class CompletionParticle {public float x,y,scale,alpha,angle;}
 [Serializable]public sealed class CompletionPose {public float alpha,starScale,haloAngle,haloAlpha,reward,progress;public CompletionParticle[] particles=new CompletionParticle[18];}
 public static class LevelCompleteMotion {
  static float Clamp(float t)=>Math.Max(0,Math.Min(1,t));static float Ease(float t){t=Clamp(t);return 1-(1-t)*(1-t)*(1-t);}
  public static CompletionPose Sample(float time,bool reduced=false){
   float t=Math.Max(0,time);var p=new CompletionPose{alpha=reduced?1:Clamp(t/.2f),starScale=1,haloAngle=0,haloAlpha=.78f,reward=reduced?1:Ease((t-.40f)/.55f),progress=reduced?1:Ease((t-.55f)/.8f)};
   if(!reduced){float a=Clamp(t/.6f);p.starScale=a<.65f?.65f+.44f*Ease(a/.65f):1+.09f*(1-Ease((a-.65f)/.35f));p.haloAngle=t*9;p.haloAlpha=.68f+.12f*(float)Math.Sin(t*1.5f);}
   for(int i=0;i<18;i++){float a=(float)(i*Math.PI*2/18),delay=.16f+(i%3)*.025f,age=t-delay,life=1.1f+(i%4)*.13f,q=Clamp(age/life),radius=26+(47+(i%5)*8)*Ease(q);p.particles[i]=new CompletionParticle{x=(float)Math.Cos(a)*radius,y=(float)Math.Sin(a)*radius+q*q*25,scale=.52f+(i%3)*.23f,angle=i*23+q*120,alpha=reduced||age<0||age>=life?0:(float)Math.Sin(q*Math.PI)*.9f};}
   return p;
  }
 }
}
