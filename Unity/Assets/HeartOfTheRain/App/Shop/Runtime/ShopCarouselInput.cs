using System;using UnityEngine;using UnityEngine.UI;using UnityEngine.EventSystems;
namespace HeartOfTheRain.App.Shop
{
 // Axis-locked nested dragging: vertical gestures continue to the page ScrollRect.
 public sealed class ShopCarouselInput:MonoBehaviour,IInitializePotentialDragHandler,IBeginDragHandler,IDragHandler,IEndDragHandler,IScrollHandler,IPointerEnterHandler,IPointerExitHandler,IPointerDownHandler,IPointerUpHandler
 {
  readonly ShopCarouselMotion motion=new ShopCarouselMotion();RectTransform track,rect;ScrollRect page;
  Func<bool> blocked,reduced;Action<int> selected;Action keyboardFocus;float stride,scale;Vector2 origin;int pointer=int.MinValue;
  readonly Vector3[] corners=new Vector3[4],pageCorners=new Vector3[4];
  bool vertical,hover,pressed,activeFocus=true;public bool Busy=>motion.Dragging||motion.Sliding;
  public void Configure(RectTransform content,ScrollRect outer,float step,float uiScale,int count,int index,Func<bool> isBlocked,Func<bool> reduce,Action<int> onSelect,Action onKeyboardFocus)
  {track=content;rect=(RectTransform)transform;page=outer;stride=step;scale=uiScale;blocked=isBlocked;reduced=reduce;selected=onSelect;keyboardFocus=onKeyboardFocus;motion.Reset(count,index);Apply();}
  bool FocusInside(){var go=EventSystem.current?EventSystem.current.currentSelectedGameObject:null;return go&&go.transform.IsChildOf(transform);}
  bool Onscreen()
  {
   if(!page||!rect)return false;var a=corners;var b=pageCorners;rect.GetWorldCorners(a);page.viewport.GetWorldCorners(b);
   return Math.Min(a[2].y,b[2].y)-Math.Max(a[0].y,b[0].y)>(a[2].y-a[0].y)*.6f;
  }
  void Update()
  {
   if(track==null)return;int before=motion.Index;bool focus=FocusInside();
   motion.Tick(Time.unscaledDeltaTime,!activeFocus||blocked()||!Onscreen()||pressed,reduced(),hover||focus||vertical||page.velocity.sqrMagnitude>1);
   Apply();if(before!=motion.Index){selected(motion.Index);if(focus)keyboardFocus?.Invoke();}
  }
  void Apply(){if(track)track.anchoredPosition=new Vector2(-motion.Position*stride,0);}
  public void Step(int direction)
  {if(blocked()||!activeFocus)return;int before=motion.Index;if(motion.Step(direction,reduced())){Apply();if(before!=motion.Index){selected(motion.Index);if(FocusInside())keyboardFocus?.Invoke();}}}
  public void OnInitializePotentialDrag(PointerEventData e){if(page)page.OnInitializePotentialDrag(e);}
  public void OnBeginDrag(PointerEventData e)
  {
   if(blocked()||pointer!=int.MinValue)return;pointer=e.pointerId;origin=e.pressPosition;
   Vector2 d=e.position-origin;vertical=Mathf.Abs(d.y)>=Mathf.Abs(d.x)||motion.Count<2;pressed=false;
   if(vertical)page.OnBeginDrag(e);else{page.StopMovement();motion.BeginDrag();e.eligibleForClick=false;}
  }
  public void OnDrag(PointerEventData e)
  {if(pointer!=e.pointerId||blocked())return;if(vertical)page.OnDrag(e);else{motion.Drag(-(e.position.x-origin.x)/(Math.Max(.01f,scale)*stride));Apply();e.eligibleForClick=false;}}
  public void OnEndDrag(PointerEventData e)
  {
   if(pointer!=e.pointerId)return;if(vertical)page.OnEndDrag(e);else{int before=motion.Index;motion.EndDrag(reduced());Apply();if(before!=motion.Index)selected(motion.Index);}
   pointer=int.MinValue;vertical=pressed=false;motion.Touch();
  }
  public void OnScroll(PointerEventData e)
  {if(blocked())return;motion.Touch();if(Mathf.Abs(e.scrollDelta.x)>Mathf.Abs(e.scrollDelta.y))Step(e.scrollDelta.x>0?1:-1);else page.OnScroll(e);e.Use();}
  public void OnPointerEnter(PointerEventData e){hover=true;}
  public void OnPointerExit(PointerEventData e){hover=false;}
  public void OnPointerDown(PointerEventData e){pressed=true;motion.Touch();}
  public void OnPointerUp(PointerEventData e){pressed=false;if(e.pointerId>=0)hover=false;motion.Touch();}
  void Cancel(){motion.Cancel();Apply();pointer=int.MinValue;vertical=pressed=hover=false;if(page)page.StopMovement();}
  void OnApplicationFocus(bool value){activeFocus=value;if(!value)Cancel();}
  void OnApplicationPause(bool value){activeFocus=!value;if(value)Cancel();}
  void OnDisable(){Cancel();}
 }
}
