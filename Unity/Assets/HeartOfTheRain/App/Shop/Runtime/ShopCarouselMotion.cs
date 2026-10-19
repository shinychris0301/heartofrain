using System;
namespace HeartOfTheRain.App.Shop
{
 // Pure motion state shared with offline playback tests. Position is measured in cards.
 // Leading/trailing duplicate cards permit a seamless forward/backward wrap.
 public sealed class ShopCarouselMotion
 {
  public const float Interval=4.5f,Duration=.48f,InteractionDelay=8;
  public int Count{get;private set;} public int Index{get;private set;}
  public float Position{get;private set;} public bool Dragging{get;private set;}
  public bool Sliding{get;private set;} public float Idle{get;private set;}
  float from,to,elapsed,dragOrigin,cooldown;
  public void Reset(int count,int index)
  {Count=Math.Max(0,count);Index=Count==0?0:Math.Max(0,Math.Min(Count-1,index));Position=Count>1?Index+1:0;Idle=0;cooldown=0;Dragging=Sliding=false;}
  public void Touch(){Idle=0;cooldown=InteractionDelay;}
  public bool Step(int direction,bool reducedMotion=false,bool manual=true)
  {
   if(Count<2||Dragging||Sliding||direction==0)return false;
   if(manual)Touch();from=Position;to=Index+1+(direction>0?1:-1);elapsed=0;Sliding=true;
   if(reducedMotion)Finish();return true;
  }
  public bool BeginDrag()
  {if(Count<2)return false;Touch();Sliding=false;Dragging=true;dragOrigin=Position;return true;}
  public void Drag(float cells)
  {if(Dragging)Position=Math.Max(0,Math.Min(Count+1,dragOrigin+Math.Max(-1,Math.Min(1,cells))));}
  public void EndDrag(bool reducedMotion=false)
  {
   if(!Dragging)return;Dragging=false;float delta=Position-(Index+1);
   from=Position;to=Index+1+(Math.Abs(delta)>=.16f?(delta>0?1:-1):0);elapsed=0;Sliding=true;Touch();if(reducedMotion)Finish();
  }
  public void Cancel(){Dragging=Sliding=false;Position=Count>1?Index+1:0;Touch();}
  public void Tick(float delta,bool paused,bool reducedMotion,bool holdAuto=false)
  {
   if(delta<=0||float.IsNaN(delta)||float.IsInfinity(delta)||Count<2)return;
   // Backgrounding, modal opening, hover/focus, and offscreen content freeze motion.
   if(paused)return;
   if(Sliding){if(reducedMotion){Finish();return;}elapsed+=delta;float t=Math.Min(1,elapsed/Duration);float ease=t*t*t*(t*(t*6-15)+10);Position=from+(to-from)*ease;if(t>=1)Finish();return;}
   if(Dragging||reducedMotion||holdAuto)return;
   if(cooldown>0){cooldown=Math.Max(0,cooldown-delta);return;}
   Idle+=delta;if(Idle>=Interval){Idle=0;Step(1,false,false);}
  }
  void Finish(){int slot=(int)Math.Round(to);Index=(slot-1+Count)%Count;Position=Index+1;Sliding=false;Idle=0;}
 }
}
