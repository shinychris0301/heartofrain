using System;
namespace HeartOfTheRain.ContinueReference
{
    // Affordability is intentionally absent. A zero-coin wallet can still have a valid offer.
    public enum ContinueOfferStatus { Loading, Available, ConfirmedUnavailable, RecoverableError }
    public sealed class ContinueOfferViewModel
    {
        public ContinueOfferStatus Status { get; private set; }
        readonly Quote quote;
        public Quote Quote { get { return quote == null ? null : quote.Copy(); } }
        public bool ShowsPrice { get { return Status == ContinueOfferStatus.Available; } }
        ContinueOfferViewModel(ContinueOfferStatus status, Quote value = null)
        { Status = status; quote = value == null ? null : value.Copy(); }
        public static ContinueOfferViewModel Loading()
        { return new ContinueOfferViewModel(ContinueOfferStatus.Loading); }
        public static ContinueOfferViewModel Ready(Quote quote)
        {
            if (quote == null || quote.CoinCost <= 0 || quote.ExtraMoves <= 0)
                throw new ArgumentException("Ready requires a valid authority-issued offer, independent of wallet balance.");
            return new ContinueOfferViewModel(ContinueOfferStatus.Available, quote);
        }
        // Call only after authority confirms a continue cap or policy restriction.
        public static ContinueOfferViewModel Unavailable()
        { return new ContinueOfferViewModel(ContinueOfferStatus.ConfirmedUnavailable); }
        // Offline, timeout and missing config are NOT confirmed unavailability.
        public static ContinueOfferViewModel Error()
        { return new ContinueOfferViewModel(ContinueOfferStatus.RecoverableError); }
    }
}
