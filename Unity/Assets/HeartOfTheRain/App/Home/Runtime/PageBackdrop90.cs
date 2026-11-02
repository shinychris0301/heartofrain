using System;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.App.Home
{
    // Backgrounds and decorative scrims paint the display; their existing
    // parents retain draw order, CanvasGroup fades and safe-area controls.
    // Only the supplied non-interactive graphic opts out of UI masking.
    public static class PageBackdrop90
    {
        static readonly Vector3[] Corners = new Vector3[4];

        public static void Fill(MaskableGraphic graphic, Canvas canvas)
        {
            if (!graphic || !canvas) throw new ArgumentNullException(!graphic ? "graphic" : "canvas");
            var parent = graphic.rectTransform.parent;
            var display = (RectTransform)canvas.transform;
            display.GetWorldCorners(Corners);
            var bottomLeft = parent.InverseTransformPoint(Corners[0]);
            var topRight = parent.InverseTransformPoint(Corners[2]);
            SetBounds(graphic, bottomLeft.x, bottomLeft.y, topRight.x, topRight.y);
        }

        // The Journey header's lower edge stays aligned with the unchanged
        // safe-area title/content. Its decoration continues through insets.
        public static void ExtendTop(MaskableGraphic graphic, Canvas canvas)
        {
            if (!graphic || !canvas) throw new ArgumentNullException(!graphic ? "graphic" : "canvas");
            var parent = graphic.rectTransform.parent;
            graphic.rectTransform.GetWorldCorners(Corners);
            float bottom = parent.InverseTransformPoint(Corners[0]).y;
            ((RectTransform)canvas.transform).GetWorldCorners(Corners);
            var bottomLeft = parent.InverseTransformPoint(Corners[0]);
            var topRight = parent.InverseTransformPoint(Corners[2]);
            SetBounds(graphic, bottomLeft.x, bottom, topRight.x, topRight.y);
        }

        public static void Cover(RawImage image)
        {
            if (!image || !image.texture) return;
            var size = image.rectTransform.rect.size;
            if (size.x <= 0 || size.y <= 0) return;
            float source = image.texture.width / (float)image.texture.height;
            float target = size.x / size.y;
            image.uvRect = source > target
                ? new Rect((1 - target / source) / 2, 0, target / source, 1)
                : new Rect(0, (1 - source / target) / 2, 1, source / target);
        }

        static void SetBounds(MaskableGraphic graphic, float left, float bottom, float right, float top)
        {
            graphic.maskable = false;
            graphic.RecalculateClipping();
            graphic.raycastTarget = false;
            var rect = graphic.rectTransform;
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.sizeDelta = new Vector2(right - left, top - bottom);
            rect.localPosition = new Vector3(left, top, rect.localPosition.z);
        }
    }
}
