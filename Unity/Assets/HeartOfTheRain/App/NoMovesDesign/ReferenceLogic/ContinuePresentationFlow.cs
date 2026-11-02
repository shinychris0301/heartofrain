// Presentation routing only. Bind to ContinueService and the existing authenticated shop.
// No coin or life mutation occurs in this class. A failed balance precheck dispatches no purchase.
using System;
namespace HeartOfTheRain.ContinueReference
{
    public enum ContinueScreen { Resolving, Notice, WaitingForQuote, Offer, Shop, StorePending, PurchasingMoves, Unknown, ConfirmEnd, Playing, Ended, Won }
    public enum ContinueAction { None, RequestMovePurchase, OpenShop, RequestStorePurchase, ReconcileMovePurchase, RequestEndAttempt }
    public sealed class ContinuePresentationFlow
    {
        public ContinueScreen Screen { get; private set; } = ContinueScreen.Resolving;
        public Quote CurrentQuote { get { return quote==null?null:quote.Copy(); } }
        Quote quote; bool quoteResolved;
        public void BoardSettled(bool won, int remainingMoves)
        {
            if(Screen!=ContinueScreen.Resolving)return;
            Screen=won?ContinueScreen.Won:remainingMoves>0?ContinueScreen.Playing:ContinueScreen.Notice;
        }
        // Fetch in parallel with the short notification. null = confirmed unavailable, not still loading.
        public void SetQuote(Quote value)
        {
            quote=value==null?null:value.Copy(); quoteResolved=true;
            if(Screen==ContinueScreen.WaitingForQuote) Screen=ContinueScreen.Offer;
        }
        public void FinishNotice()
        {
            if(Screen==ContinueScreen.Notice)Screen=quoteResolved?ContinueScreen.Offer:ContinueScreen.WaitingForQuote;
        }
        public ContinueAction PlayOn(int currentBalance)
        {
            if(Screen==ContinueScreen.Unknown)return ContinueAction.ReconcileMovePurchase;
            if(Screen!=ContinueScreen.Offer)return ContinueAction.None;
            if(quote==null){Screen=ContinueScreen.ConfirmEnd;return ContinueAction.None;}
            if(currentBalance<quote.CoinCost){Screen=ContinueScreen.Shop;return ContinueAction.OpenShop;}
            Screen=ContinueScreen.PurchasingMoves;return ContinueAction.RequestMovePurchase;
        }
        public ContinueAction OpenCoinShop()
        {
            if(Screen!=ContinueScreen.Offer)return ContinueAction.None;
            Screen=ContinueScreen.Shop;return ContinueAction.OpenShop;
        }
        public ContinueAction BeginStorePurchase()
        {
            if(Screen!=ContinueScreen.Shop)return ContinueAction.None;
            Screen=ContinueScreen.StorePending;return ContinueAction.RequestStorePurchase;
        }
        // Call successful only AFTER the store receipt and authoritative coin credit are settled.
        public void StoreResolved(bool credited, Quote refreshedQuote)
        {
            if(Screen!=ContinueScreen.StorePending)return;
            if(credited){SetQuote(refreshedQuote);Screen=ContinueScreen.Offer;}
            else Screen=ContinueScreen.Shop;
            // No move purchase is dispatched automatically in either case.
        }
        public void StoreUnknown() { /* Keep StorePending; reconcile the existing store transaction. */ }
        public void MovePurchaseUnknown()
        { if(Screen==ContinueScreen.PurchasingMoves)Screen=ContinueScreen.Unknown; }
        // Applied means board + wallet are already reconciled, not merely that an HTTP response arrived.
        public ContinueAction MovePurchaseResolved(PurchaseOutcome outcome, Quote refreshedQuote)
        {
            if(Screen!=ContinueScreen.PurchasingMoves&&Screen!=ContinueScreen.Unknown)return ContinueAction.None;
            if(outcome==PurchaseOutcome.Applied){Screen=ContinueScreen.Playing;return ContinueAction.None;}
            SetQuote(refreshedQuote);
            if(outcome==PurchaseOutcome.InsufficientCoins){Screen=ContinueScreen.Shop;return ContinueAction.OpenShop;}
            Screen=ContinueScreen.Offer;return ContinueAction.None;
        }
        public void Back()
        {
            if(Screen==ContinueScreen.Shop||Screen==ContinueScreen.ConfirmEnd) Screen=ContinueScreen.Offer;
            else if(Screen==ContinueScreen.Offer)Screen=ContinueScreen.ConfirmEnd;
            // Never dismiss pending/unknown purchases or resume a zero-move board.
        }
        public ContinueAction ConfirmEnd()
        { return Screen==ContinueScreen.ConfirmEnd?ContinueAction.RequestEndAttempt:ContinueAction.None; }
        public void EndResolved(bool committed)
        { if(Screen==ContinueScreen.ConfirmEnd&&committed)Screen=ContinueScreen.Ended; }
    }
}
