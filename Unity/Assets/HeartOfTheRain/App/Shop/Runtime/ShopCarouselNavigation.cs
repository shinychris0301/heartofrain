using UnityEngine;using UnityEngine.EventSystems;
namespace HeartOfTheRain.App.Shop
{
 public sealed class ShopCarouselNavigation:MonoBehaviour,IMoveHandler
 {
  public ShopCarouselInput carousel;
  public void OnMove(AxisEventData e){if(!carousel)return;if(e.moveDir==MoveDirection.Left||e.moveDir==MoveDirection.Right){carousel.Step(e.moveDir==MoveDirection.Right?1:-1);e.Use();}}
 }
}
