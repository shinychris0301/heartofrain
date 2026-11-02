using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.App.Home
{
    public static class SpriteFit
    {
        public static void Center(Image image)
        {
            if (!image.preserveAspect || !image.sprite) return;
            // uGUI aligns contained artwork by its pivot. Keep the layout's
            // outer rectangle fixed while centering art inside that rectangle.
            var rect = image.rectTransform;
            var center = new Vector2(.5f, .5f);
            rect.anchoredPosition += Vector2.Scale(center - rect.pivot, rect.rect.size);
            rect.pivot = center;
        }
    }
}
