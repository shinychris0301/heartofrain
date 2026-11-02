// Pure C# reference domain. No Unity, network, storage, or payment-provider dependencies.
// Production must implement IAtomicStore with a durable, per-player serialized transaction.
// Run this on the trusted economy authority, not as a client-authoritative coin store.
using System;
using System.Collections.Generic;

namespace HeartOfTheRain.ContinueReference
{
    public enum AttemptPhase { Playing, AwaitingContinue, Won, Ended }
    public enum PurchaseOutcome { Applied, InsufficientCoins, StaleQuote, Unavailable }
    public sealed class Attempt
    {
        public string Id, BoardState;
        public int Moves, ContinueCount, Revision;
        public AttemptPhase Phase;
        public Attempt Copy() { return (Attempt)MemberwiseClone(); }
    }
    public sealed class Offer
    {
        public int CoinCost, ExtraMoves;
        public string PolicyVersion;
        public TimeSpan ValidFor;
    }
    public sealed class Quote
    {
        public string Id, AttemptId, PolicyVersion;
        public int AttemptRevision, CoinCost, ExtraMoves;
        public DateTime ExpiresUtc;
        public Quote Copy() { return (Quote)MemberwiseClone(); }
    }
    public sealed class PurchaseCommand
    {
        // Amounts are NEVER accepted from the client. QuoteId resolves an authority-issued quote.
        public string OperationId, AttemptId, QuoteId;
        public PurchaseCommand Copy() { return (PurchaseCommand)MemberwiseClone(); }
    }
    public sealed class Receipt
    {
        public string OperationId, AttemptId, QuoteId;
        public PurchaseOutcome Outcome;
        public int CoinCost, ExtraMoves, WalletAfter, WalletRevision, MovesAfter, AttemptRevision;
        public Receipt Copy() { return (Receipt)MemberwiseClone(); }
    }
    public sealed class Ledger
    {
        public int Coins, Lives, WalletRevision;
        public DateTime? UnlimitedLivesUntilUtc;
        public Attempt Attempt;
        public Dictionary<string, Quote> Quotes = new Dictionary<string, Quote>();
        public Dictionary<string, Receipt> Receipts = new Dictionary<string, Receipt>();
        public Ledger Copy()
        {
            var v = new Ledger { Coins=Coins, Lives=Lives, WalletRevision=WalletRevision, UnlimitedLivesUntilUtc=UnlimitedLivesUntilUtc, Attempt=Attempt.Copy() };
            foreach(var p in Quotes) v.Quotes.Add(p.Key,p.Value.Copy());
            foreach(var p in Receipts) v.Receipts.Add(p.Key,p.Value.Copy());
            return v;
        }
    }
    public interface IAtomicStore
    {
        // Serializable transaction, isolated COPY, all-or-nothing durable commit before returning.
        // Exceptions must roll back. Include wallet, attempt snapshot, receipts, quotes in ONE commit.
        // Scope the store to the authenticated player. ALL wallet writers must use this authority.
        T Transact<T>(Func<Ledger,T> change);
    }
    public interface IContinueOfferPolicy
    {
        // Trusted policy. Return null when disabled, unavailable, or the configured limit is reached.
        Offer ForAttempt(Attempt attempt);
    }
    public sealed class ContinueService
    {
        readonly IAtomicStore store; readonly IContinueOfferPolicy policy; readonly Func<DateTime> utcNow;
        public ContinueService(IAtomicStore store, IContinueOfferPolicy policy, Func<DateTime> utcNow)
        { this.store=store; this.policy=policy; this.utcNow=utcNow; }
        public Ledger Read() { return store.Transact(s=>s.Copy()); }

        // Called ONLY by the trusted board resolver, AFTER all turn logic, goals and animation settle.
        // BoardState is the complete opaque snapshot (pieces, obstacles, powers, goals, score, RNG).
        // Never call with a client-provided claim that a level was won or with an unfinished cascade.
        public Attempt SettleTurn(string attemptId, int expectedRevision, int moves, bool goalsComplete,
                                  bool resolverSettled, string boardState)
        {
            return store.Transact(s=>{
                var a=s.Attempt;
                if(a.Id!=attemptId || a.Revision!=expectedRevision || a.Phase!=AttemptPhase.Playing || !resolverSettled)
                    return a.Copy();
                if(moves<0 || boardState==null) throw new ArgumentException("Invalid verified board state.");
                a.Moves=moves; a.BoardState=boardState; a.Revision++;
                a.Phase=goalsComplete ? AttemptPhase.Won : moves==0 ? AttemptPhase.AwaitingContinue : AttemptPhase.Playing;
                return a.Copy();
            });
        }
        public Quote GetQuote(string attemptId)
        {
            return store.Transact(s=>{
                var a=s.Attempt;
                if(a.Id!=attemptId || a.Phase!=AttemptPhase.AwaitingContinue || a.Moves!=0) return null;
                var offer=policy.ForAttempt(a.Copy());
                if(offer==null) return null;
                if(offer.CoinCost<=0 || offer.ExtraMoves<=0 || offer.ValidFor<=TimeSpan.Zero || string.IsNullOrEmpty(offer.PolicyVersion))
                    throw new InvalidOperationException("A valid trusted continue policy is required.");
                var now=utcNow();
                foreach(var q in s.Quotes.Values)
                    if(q.AttemptId==a.Id && q.AttemptRevision==a.Revision && q.ExpiresUtc>now &&
                       q.PolicyVersion==offer.PolicyVersion && q.CoinCost==offer.CoinCost && q.ExtraMoves==offer.ExtraMoves)
                        return q.Copy();
                var fresh=new Quote { Id=Guid.NewGuid().ToString("N"), AttemptId=a.Id, AttemptRevision=a.Revision,
                    CoinCost=offer.CoinCost, ExtraMoves=offer.ExtraMoves, PolicyVersion=offer.PolicyVersion,
                    ExpiresUtc=now.Add(offer.ValidFor) };
                s.Quotes.Add(fresh.Id,fresh); return fresh.Copy();
            });
        }
        public Receipt Purchase(PurchaseCommand command)
        {
            if(command==null || string.IsNullOrEmpty(command.OperationId) || string.IsNullOrEmpty(command.AttemptId) ||
               string.IsNullOrEmpty(command.QuoteId)) throw new ArgumentException("Missing purchase identity.");
            return store.Transact(s=>{
                Receipt prior;
                if(s.Receipts.TryGetValue(command.OperationId,out prior)) {
                    if(prior.AttemptId!=command.AttemptId || prior.QuoteId!=command.QuoteId)
                        throw new InvalidOperationException("Idempotency key reused for a different command.");
                    return prior.Copy();
                }
                var a=s.Attempt; Quote q;
                var receipt=new Receipt { OperationId=command.OperationId,AttemptId=command.AttemptId,
                    QuoteId=command.QuoteId,Outcome=PurchaseOutcome.Unavailable };
                if(a.Id==command.AttemptId && a.Phase==AttemptPhase.AwaitingContinue && a.Moves==0) {
                    if(!s.Quotes.TryGetValue(command.QuoteId,out q) || q.AttemptId!=a.Id ||
                       q.AttemptRevision!=a.Revision || q.ExpiresUtc<=utcNow()) receipt.Outcome=PurchaseOutcome.StaleQuote;
                    else {
                        // An issued quote is honored until expiry, even if the next offer's policy changes.
                        receipt.CoinCost=q.CoinCost; receipt.ExtraMoves=q.ExtraMoves;
                        if(s.Coins<q.CoinCost) receipt.Outcome=PurchaseOutcome.InsufficientCoins;
                        else {
                            s.Coins=checked(s.Coins-q.CoinCost); s.WalletRevision=checked(s.WalletRevision+1);
                            a.Moves=checked(a.Moves+q.ExtraMoves); a.ContinueCount=checked(a.ContinueCount+1);
                            a.Revision=checked(a.Revision+1); a.Phase=AttemptPhase.Playing;
                            receipt.Outcome=PurchaseOutcome.Applied;
                            // No change to BoardState or Lives. No new level/starting boosters/rewards.
                        }
                    }
                }
                receipt.WalletAfter=s.Coins; receipt.WalletRevision=s.WalletRevision;
                receipt.MovesAfter=a.Moves; receipt.AttemptRevision=a.Revision;
                s.Receipts.Add(receipt.OperationId,receipt);
                return receipt.Copy();
            });
        }
        public Receipt Lookup(PurchaseCommand command)
        {
            return store.Transact(s=>{
                Receipt r;
                if(!s.Receipts.TryGetValue(command.OperationId,out r)) return null;
                if(r.AttemptId!=command.AttemptId || r.QuoteId!=command.QuoteId)
                    throw new InvalidOperationException("Operation identity mismatch.");
                return r.Copy();
            });
        }
        // Only the confirmed no-moves abandonment path. Existing voluntary mid-level exit remains separate.
        public bool EndAttempt(string attemptId, int expectedRevision)
        {
            return store.Transact(s=>{
                var a=s.Attempt;
                if(a.Id!=attemptId || a.Phase!=AttemptPhase.AwaitingContinue || a.Moves!=0 || a.Revision!=expectedRevision) return false;
                a.Phase=AttemptPhase.Ended; a.Revision=checked(a.Revision+1);
                if(!s.UnlimitedLivesUntilUtc.HasValue || s.UnlimitedLivesUntilUtc.Value<=utcNow()) s.Lives=Math.Max(0,s.Lives-1);
                return true;
            });
        }
    }
    public interface IPendingPurchaseJournal
    {
        // Durable write before dispatch; throw if it cannot be persisted. Bind to authenticated player.
        void Save(PurchaseCommand command);
        void Clear();
    }
    public sealed class ContinueRequestGate
    {
        readonly IPendingPurchaseJournal journal;
        PurchaseCommand pending;
        public PurchaseCommand Pending { get { return pending==null?null:pending.Copy(); } }
        public ContinueRequestGate(IPendingPurchaseJournal journal, PurchaseCommand restored=null)
        { this.journal=journal; pending=restored==null?null:restored.Copy(); }
        public PurchaseCommand Begin(Quote quote)
        {
            if(Pending!=null || quote==null) return null;
            var c=new PurchaseCommand { AttemptId=quote.AttemptId,QuoteId=quote.Id,OperationId=Guid.NewGuid().ToString("N") };
            journal.Save(c.Copy()); pending=c; return c.Copy();
        }
        // Timeout is UNKNOWN, not failure. Keep Pending, lookup or resend EXACTLY this command.
        public PurchaseCommand ReconcileCommand() { return Pending==null?null:Pending.Copy(); }
        // Call after successful receipt + authoritative board/wallet reconciliation is durably applied locally.
        // For a known rejection, call after rendering the updated quote/balance. Ignore late callbacks.
        public bool Complete(Receipt receipt)
        {
            if(Pending==null || receipt==null || receipt.OperationId!=Pending.OperationId ||
               receipt.AttemptId!=Pending.AttemptId || receipt.QuoteId!=Pending.QuoteId) return false;
            journal.Clear(); pending=null; return true;
        }
    }
}
