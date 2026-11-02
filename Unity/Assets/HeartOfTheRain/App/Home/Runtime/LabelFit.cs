using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.App.Home
{
    public static class LabelFit
    {
        // The supplied fonts' line height exceeds their point size. Width-only
        // fitting can leave a nonempty label with zero generated vertices.
        public static void Apply(Text text, float width, float height, int minimum = 10)
        {
            minimum = Mathf.Min(minimum, text.fontSize);
            while (text.fontSize > minimum && text.preferredWidth > width) text.fontSize--;
            while (text.fontSize > 1 && text.preferredHeight > height + .01f) text.fontSize--;
        }
    }
}
