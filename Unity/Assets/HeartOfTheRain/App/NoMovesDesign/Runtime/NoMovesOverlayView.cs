// Presentation only. No wallet mutation, IAP, board restart, or life settlement.
using System;
using System.Globalization;

using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.ContinueReference;
namespace HeartOfTheRain.NoMovesUI
{
    [Serializable] public sealed class ContinueLabels
    {
        public string Title, AddMoves, PlayOn, EndLevel, Loading, Unavailable, Error, Retry;
        public string PackName, PackAmount, PackPrice;
    }
    [DisallowMultipleComponent]
    public sealed class NoMovesOverlayView : MonoBehaviour
    {
        public RectTransform SafeArea, Viewport, Content, Band, Hero, Offer, PriceGroup, Pack;
        public ScrollRect Scroll;
        public Image Scrim, BandImage, Dariya, Halo, Badge, Primary, WalletImage, PackImage, PackIcon, PackButtonImage;
        public Image CloseImage, WalletCoin, PriceCoin, WalletPlus;
        public Text Title, Amount, Copy, PlayLabel, Price, Balance, PackName, PackAmount, PackPrice;
        public Button PlayButton, CloseButton, WalletButton, PackButton;
        public event Action PlayRequested, ShopRequested, EndConfirmationRequested, RetryQuoteRequested, PackRequested;
        ContinueOfferViewModel model = ContinueOfferViewModel.Loading();
        ContinueLabels labels;
        bool busy, showPack;
        int wallet;
        CultureInfo culture = CultureInfo.InvariantCulture;
        Vector2 lastSize;
        Rect lastSafe;
        void Awake()
        {
            PlayButton.onClick.AddListener(OnPlay);
            CloseButton.onClick.AddListener(OnClose);
            WalletButton.onClick.AddListener(OnShop);
            PackButton.onClick.AddListener(OnPack);
        }
        void OnDestroy()
        {
            PlayButton.onClick.RemoveListener(OnPlay); CloseButton.onClick.RemoveListener(OnClose);
            WalletButton.onClick.RemoveListener(OnShop); PackButton.onClick.RemoveListener(OnPack);
        }
        void OnPlay()
        {
            if (busy || !gameObject.activeInHierarchy) return;
            if (model.Status == ContinueOfferStatus.Available) PlayRequested?.Invoke();
            else if (model.Status == ContinueOfferStatus.ConfirmedUnavailable) EndConfirmationRequested?.Invoke();
            else if (model.Status == ContinueOfferStatus.RecoverableError) RetryQuoteRequested?.Invoke();
        }
        void OnClose() { if (!busy && gameObject.activeInHierarchy) EndConfirmationRequested?.Invoke(); }
        void OnShop() { if (!busy && gameObject.activeInHierarchy) ShopRequested?.Invoke(); }
        void OnPack() { if (!busy && showPack && gameObject.activeInHierarchy) PackRequested?.Invoke(); }
        // Only pass a pack after the platform store has returned a real localized price.
        // null/empty PackPrice hides the optional card without affecting the move offer.
        public void Render(ContinueOfferViewModel value, int coins, ContinueLabels text, string locale, bool transactionPending = false)
        {
            if (value == null || text == null) throw new ArgumentNullException();
            model = value; wallet = coins; labels = text; busy = transactionPending;
            culture = CultureInfo.GetCultureInfo(locale);
            gameObject.SetActive(true);
            Title.text = text.Title; Balance.text = wallet.ToString("N0", culture);
            bool valid = model.Status == ContinueOfferStatus.Available;
            var q = model.Quote;
            Amount.text = valid ? "+" + q.ExtraMoves.ToString("N0", culture) : "—";
            Copy.text = valid ? text.AddMoves.Replace("{n}", q.ExtraMoves.ToString("N0", culture)) :
                model.Status == ContinueOfferStatus.Loading ? text.Loading :
                model.Status == ContinueOfferStatus.RecoverableError ? text.Error : text.Unavailable;
            PlayLabel.text = valid ? text.PlayOn : model.Status == ContinueOfferStatus.Loading ? text.Loading :
                model.Status == ContinueOfferStatus.RecoverableError ? text.Retry : text.EndLevel;
            Price.text = valid ? q.CoinCost.ToString("N0", culture) : "";
            PriceGroup.gameObject.SetActive(valid);
            showPack = valid && !busy && !string.IsNullOrEmpty(text.PackPrice);
            Pack.gameObject.SetActive(showPack);
            PackName.text = text.PackName; PackAmount.text = text.PackAmount; PackPrice.text = text.PackPrice;
            // DO NOT disable Play On for an insufficient balance. Its tap opens Shop.
            PlayButton.interactable = !busy && model.Status != ContinueOfferStatus.Loading;
            CloseButton.interactable = WalletButton.interactable = !busy;
            PackButton.interactable = showPack && !busy;
            Relayout();
        }
        public void SetTransactionPending(bool value)
        { if (labels != null) Render(model, wallet, labels, culture.Name, value); }
        void LateUpdate()
        {
            var size = ((RectTransform)transform).rect.size;
            if (size != lastSize || Screen.safeArea != lastSafe) Relayout();
        }
        public void Relayout()
        {
            if (SafeArea == null || Screen.width == 0 || Screen.height == 0) return;
            lastSize = ((RectTransform)transform).rect.size; lastSafe = Screen.safeArea;
            SafeArea.anchorMin = new Vector2(lastSafe.xMin / Screen.width, lastSafe.yMin / Screen.height);
            SafeArea.anchorMax = new Vector2(lastSafe.xMax / Screen.width, lastSafe.yMax / Screen.height);
            SafeArea.offsetMin = SafeArea.offsetMax = Vector2.zero;
            var sw = lastSize.x * lastSafe.width / Screen.width;
            var sh = lastSize.y * lastSafe.height / Screen.height;
            bool land = lastSize.x / Mathf.Max(1, lastSize.y) > 1.18f;
            bool compact = lastSize.y < 680 || lastSize.x < 345;
            bool shortLand = land && lastSize.y < 380;
            float hero = land ? (shortLand ? 110 : 126) : compact ? 153 : 196;
            float paddingTop = land ? 24 : 14, paddingBottom = land ? 12 : 14;
            float availableH = Mathf.Max(1, sh - paddingTop - paddingBottom);
            Set(Viewport, land ? 12 : 6, paddingTop, sw - (land ? 24 : 12), availableH);
            float width = Mathf.Min(land && showPack ? 740 : 430, Viewport.rect.width);
            float top = land || compact ? 0 : 40, walletH = land ? 44 : compact ? 48 : 51;
            float bandWidth = land && showPack ? (width - 12) * 1.8f / 2.8f : width;
            float bandH = 60 + hero + 79;
            float packH = compact ? 79 : 91, packGap = compact ? 11 : 18;
            float height = top + walletH + (land ? 12 : 0) + bandH + 8;
            if (showPack && !land) height += packGap + packH;
            Set(Content, (Viewport.rect.width - width) / 2, 0, width, Mathf.Max(height, availableH));
            float y = Mathf.Max(0, (availableH - height) / 2) + top;
            Set(WalletButton.transform as RectTransform, land ? 9 : 14, y, WalletWidth(), 44);
            LayoutWallet();
            y += walletH + (land ? 12 : 0);
            Set(Band, 0, y, bandWidth, bandH);
            Set(Title.rectTransform, 45, 0, bandWidth - 90, 60);
            FitText(Title, land ? 25 : compact ? 26 : 30, 21);
            Set(CloseButton.transform as RectTransform, bandWidth - 58, -19, 48, 48);
            Set(CloseImage.rectTransform, -2, -2, 52, 52);
            Set(Hero, 4, 60, bandWidth - 8, hero);
            float left = (bandWidth - 8) * .46f;
            float portraitH = Mathf.Min(hero, left * Dariya.sprite.rect.height / Dariya.sprite.rect.width);
            Set(Dariya.rectTransform, 0, hero - portraitH, left, portraitH);
            Set(Offer, left, 0, Hero.rect.width - left, hero);
            Set(Halo.rectTransform, 0, 0, Offer.rect.width, hero);
            float bw = land ? (shortLand ? 58 : 66) : compact ? 78 : 99;
            float bh = land ? (shortLand ? 66 : 74) : compact ? 88 : 112;
            float fs = land ? (shortLand ? 14 : 15) : compact ? 16 : 19;
            FitText(Copy, fs, fs - 1); Copy.horizontalOverflow = HorizontalWrapMode.Wrap;
            float copyWidth = Mathf.Min(180, Offer.rect.width - 12);
            float copyH = Mathf.Max(fs * 2.24f, Preferred(Copy,copyWidth).y);
            float groupH = bh + 4 + copyH;
            float oy = Mathf.Max(4, (hero - groupH) / 2);
            float center = (Offer.rect.width - 12) / 2;
            Set(Badge.rectTransform, center - bw / 2, oy, bw, bh);
            Set(Amount.rectTransform, 0, 0, bw, bh - 10);
            FitText(Amount, land ? (shortLand ? 28 : 31) : compact ? 36 : 44, 24);
            Set(Copy.rectTransform, center - copyWidth / 2, oy + bh + 4, copyWidth, copyH);
            LayoutPlay(bandWidth, 60 + hero + 9, compact ? 22 : 24);
            if (showPack) LayoutPack(land, compact, width, bandWidth, y, bandH, packGap, packH);
            // Pixel density is derived from each source's import PPU and the actual host Canvas.
            Slice(BandImage, 4); Slice(Primary, 300f / 35); Slice(WalletImage, 80f / 18);
            Slice(PackImage, 4);
            Slice(PackButtonImage, 300f / 26);
            Scroll.vertical = height > availableH;
        }
        float WalletWidth() { return Mathf.Max(122, Preferred(Balance).x + 78); }
        void LayoutWallet()
        {
            float w = (WalletButton.transform as RectTransform).rect.width;
            Set(WalletCoin.rectTransform, 6, 7, 30, 30);
            Set(Balance.rectTransform, 41, 2, w - 78, 40); FitText(Balance, 21, 16);
            Set(WalletPlus.rectTransform, w - 33, 8, 26, 28);
        }
        void LayoutPlay(float w, float y, float font)
        {
            FitText(PlayLabel, font, 18); FitText(Price, 23, 18);
            float labelW = Preferred(PlayLabel).x;
            float priceW = model.ShowsPrice ? 30 + Preferred(Price).x : 0;
            float contentW = labelW + (model.ShowsPrice ? 8 + priceW : 0);
            float buttonW = Mathf.Clamp(contentW + 42, 185, w - 46);
            Set(PlayButton.transform as RectTransform, (w - buttonW) / 2, y, buttonW, 57);
            float scale = Mathf.Min(1, (buttonW - 42) / Mathf.Max(1, contentW));
            labelW *= scale; priceW *= scale; contentW *= scale;
            float start = (buttonW - contentW) / 2;
            Set(PlayLabel.rectTransform, start, 8, labelW + 1, 38);
            Set(PriceGroup, start + labelW + 8 * scale, 8, priceW, 38);
            Set(PriceCoin.rectTransform, 0, 6, 26, 26);
            Set(Price.rectTransform, 30, 0, Mathf.Max(1, priceW - 30), 38);
        }
        void LayoutPack(bool land, bool compact, float width, float bw, float y, float bh, float gap, float ph)
        {
            float pw = land ? width - bw - 12 : width - (compact ? 24 : 32);
            Set(Pack, land ? bw + 12 : compact ? 12 : 16,
                land ? y + (bh - 218) / 2 : y + bh + gap, pw, land ? 218 : ph);
            float icon = land ? 67 : compact ? 49 : 65;
            Set(PackIcon.rectTransform, land ? (pw - icon) / 2 : 13, land ? 13 : 12, icon, icon);
            if (land)
            {
                Set(PackName.rectTransform, 14, 85, pw - 28, 25);
                Set(PackAmount.rectTransform, 14, 114, pw - 28, 23);
                Set(PackButton.transform as RectTransform, 14, 153, pw - 28, 49);
            }
            else
            {
                float priceW = Mathf.Max(74, Preferred(PackPrice).x + 28);
                priceW = Mathf.Min(priceW, pw * .36f);
                float tx = 13 + icon + 7, tw = pw - tx - priceW - 20;
                Set(PackName.rectTransform, tx, compact ? 11 : 19, tw, 27);
                Set(PackAmount.rectTransform, tx, compact ? 38 : 46, tw, 24);
                Set(PackButton.transform as RectTransform, pw - priceW - 13, (ph - 49) / 2, priceW, 49);
            }
            FitText(PackName, compact ? 15 : 17, 12); FitText(PackAmount, compact ? 12 : 14, 11);
            PackName.alignment = PackAmount.alignment = land ? TextAnchor.MiddleCenter : TextAnchor.MiddleLeft;
            var pr = PackButton.transform as RectTransform;
            Set(PackPrice.rectTransform, 12, 5, pr.rect.width - 24, 38); FitText(PackPrice, 19, 15);
        }
        static void Set(RectTransform r, float x, float y, float w, float h)
        { r.anchorMin = r.anchorMax = r.pivot = new Vector2(0, 1); r.localScale = Vector3.one; r.anchoredPosition = new Vector2(x, -y); r.sizeDelta = new Vector2(w, h); }
        static Vector2 Preferred(Text text,float width=0) {
            var settings=text.GetGenerationSettings(new Vector2(width,500));settings.resizeTextForBestFit=false;settings.fontSize=text.resizeTextForBestFit?text.resizeTextMaxSize:text.fontSize;settings.verticalOverflow=VerticalWrapMode.Overflow;
            var generator=new TextGenerator();return new Vector2(generator.GetPreferredWidth(text.text,settings),generator.GetPreferredHeight(text.text,settings))/text.pixelsPerUnit;
        }
        static void FitText(Text t, float max, float min)
        { t.fontSize = Mathf.RoundToInt(max); t.resizeTextForBestFit = true; t.resizeTextMaxSize = Mathf.RoundToInt(max); t.resizeTextMinSize = Mathf.RoundToInt(min); }
        static void Slice(Image image, float sourcePixelsPerLogicalPixel)
        {
            if (image == null || image.sprite == null) return;
            image.type = Image.Type.Sliced; image.color = Color.white;
            float reference = image.canvas == null ? 100 : image.canvas.referencePixelsPerUnit;
            image.pixelsPerUnitMultiplier = sourcePixelsPerLogicalPixel * reference / image.sprite.pixelsPerUnit;
            image.SetVerticesDirty();
        }
    }
}
