#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.RuStore.Editor;
using HeartOfTheRain.App.Shop;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification
{
    // Run only in the pinned Editor. Synthetic IDs/URLs exercise syntax, not
    // registration, deployment, signing ownership or a real payment provider.
    public static class RuStore81Verification
    {
        [Serializable] sealed class InputCase { public string name; public string[] blockers; }
        [Serializable] sealed class Report
        {
            public string status, utc, unity, error = "", projectSettingsBefore, projectSettingsAfter;
            public int checks, inputMutations, coinMappings, continuedPurchases, coordinatorCases, diskJournalCases, clientCases;
            public bool settingsUnchanged, preferencesUnchanged, environmentRestored;
            public bool actualReleaseBlocked, ordinaryBuildChannelUnaffected, proposalNotRegistered;
            public string scope = "Native Unity Editor execution of the actual release guard/configuration parser, imported Shop/NoMoves assets, isolated in-memory profile/model services, coordinator doubles and actual temporary-file payment journal I/O. The journal checksum detects corruption and is not authority. No OS power-loss proof, Console registration, hosted service, real signing certificate, SDK checkout, bank return, ad, payment fulfillment, Android or production-readiness claim.";
            public List<string> cases = new List<string>(), errors = new List<string>();
            public List<InputCase> inputs = new List<InputCase>();
        }
        [Serializable] sealed class CandidateIdentifiers { public string packageName, paymentReturnScheme, note; }
        [Serializable] sealed class CandidateProduct { public string shopOfferId, proposedStoreProductId; public int coins; public bool enabled; }
        [Serializable] sealed class Notifications { public string sandbox, production, status; }
        [Serializable] sealed class ReleaseTemplate
        {
            public string status, packageName, consoleApplicationId, paymentReturnScheme, backendOrigin;
            public string privacyPolicyUrl, supportUrl, termsUrl, signingCertificateSha256, environment;
            public int schemaVersion, minimumApiLevel, targetApiLevel, versionCode;
            public CandidateIdentifiers candidateIdentifiers;
            public CandidateProduct[] candidateProducts;
            public Notifications notificationPaths;
        }
        static Report report;
        static string temporary;
        // These doubles drive the real coordinator in native Unity. They do
        // not prove provider checkout, server authentication or disk durability.
        sealed class TestJournal : IPayJournal
        {
            public PayPending saved; public bool fail; public readonly List<string> events = new List<string>();
            public PayPending Load() => saved;
            public bool TrySave(PayPending value, out string error) { events.Add("save:" + value.phase); error = fail ? "synthetic-save-fault" : ""; if(fail) return false; saved = value; return true; }
        }
        sealed class TestStore : IPayStore
        {
            public bool configured = true, compiled = true, hold, unknown, throwLookup, failAck;
            public int purchases, lookups, lists, acknowledgements; public PayPurchase observed;
            public Action<PayReply<PayLocator>> delayed;
            public bool SdkCompiled => compiled; public bool Configured => configured;
            public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done) => done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));
            public void GetProducts(string[] ids, Action<PayReply<PayProduct[]>> done) => done(PayReply<PayProduct[]>.Ok(new[] { new PayProduct(ids[0], "provider-localized-label", "RUB", 9900) }));
            public void Purchase(PayRequest request, Action<PayReply<PayLocator>> done) { purchases++; if(hold) { delayed = done; return; } done(unknown ? PayReply<PayLocator>.Fail("synthetic-unknown", true) : PayReply<PayLocator>.Ok(observed.locator)); }
            public void GetPurchase(string id, Action<PayReply<PayPurchase>> done) { lookups++; if(throwLookup) throw new InvalidOperationException("synthetic-delayed-lookup"); done(PayReply<PayPurchase>.Ok(observed)); }
            public void GetPurchases(Action<PayReply<PayPurchase[]>> done) { lists++; done(PayReply<PayPurchase[]>.Ok(new[] { observed })); }
            public void ConfirmTwoStep(PayRequest request, PayPurchase purchase, PayCaptureAuthorization authorization, Action<PayReply<PayAvailability>> done) => done(PayReply<PayAvailability>.Fail("not-exercised"));
            public void Acknowledge(PayRequest request, PayPurchase purchase, PayDeliveryReceipt receipt, Action<PayReply<PayAvailability>> done) { acknowledgements++; if(failAck) { failAck = false; done(PayReply<PayAvailability>.Fail("synthetic-ack-lost", true)); } else done(PayReply<PayAvailability>.Ok(new PayAvailability(true))); }
        }
        sealed class TestAuthority : IPayAuthority
        {
            public bool ready = true, spendable = true; public int reconciliations;
            public bool WalletReady => ready;
            public void Reconcile(PayRequest request, PayPurchase observed, Action<PayReply<PayDeliveryReceipt>> done) {
                reconciliations++; done(PayReply<PayDeliveryReceipt>.Ok(new PayDeliveryReceipt(request.orderId, request.productId, request.appUserId, observed.locator.purchaseId, observed.locator.invoiceId, "synthetic-durable-receipt", request.sandbox, true, spendable)));
            }
        }
        sealed class PayFixture
        {
            public readonly PayRequest request = new PayRequest(new string('a', 32), "hotr_coins_1000", new string('b', 32), "hotr-order-v1:" + new string('a', 32) + ":" + new string('c', 32), 1, true);
            public readonly TestJournal journal = new TestJournal(); public readonly TestStore store = new TestStore(); public readonly TestAuthority authority = new TestAuthority();
            public PayFixture() { store.observed = new PayPurchase(new PayLocator("12345678-1234-1234-1234-123456789abc", "12345", request.orderId, request.productId, 1, true), request.developerPayload, "CONFIRMED", "ONE_STEP", "PENDING"); }
            public PayDeliveryCoordinator Coordinator() => new PayDeliveryCoordinator(store, authority, journal);
        }
        static void CoordinatorCases()
        {
            void Scenario(string name, Action action) { Case("Coordinator: " + name, () => { action(); report.coordinatorCases++; }); }
            Scenario("default actual adapter is unavailable without bootstrap", () => {
                var adapter = new RuStorePayAdapter(); Check(!adapter.Configured, "Actual adapter defaults unconfigured"); int callbacks = 0;
                adapter.GetPurchaseAvailability(x => { Check(!x.Succeeded, "Default adapter cannot show availability"); callbacks++; });
                adapter.GetProducts(new[] { "hotr_coins_1000" }, x => { Check(!x.Succeeded, "Default adapter cannot advertise registered products"); callbacks++; });
                adapter.Purchase(new PayFixture().request, x => { Check(!x.Succeeded, "Default authority cannot checkout"); callbacks++; });
                Check(callbacks == 3, "Unconfigured adapter completes every request without SDK access");
            });
            Scenario("strict request and locator boundaries", () => {
                var f = new PayFixture(); Check(f.request.Valid && f.store.observed.Matches(f.request), "Valid correlated synthetic control");
                foreach(string suffix in new[] { "\n", " " }) {
                    Check(!new PayRequest(f.request.orderId + suffix, f.request.productId, f.request.appUserId, f.request.developerPayload, 1, true).Valid, "Order ID rejects trailing input");
                    Check(!new PayLocator("purchase", "12345" + suffix, f.request.orderId, f.request.productId, 1, true).Matches(f.request), "Invoice ID rejects trailing input");
                }
                foreach(string invoice in new[] { "0", "01", new string('1', 31) }) Check(!new PayLocator("purchase", invoice, f.request.orderId, f.request.productId, 1, true).Matches(f.request), "Canonical bounded invoice ID required");
                Check(!new PayRequest(f.request.orderId, "bad\nproduct", f.request.appUserId, f.request.developerPayload, 1, true).Valid, "Product control character rejected");
            });
            Scenario("unready authority never dispatches", () => {
                var f = new PayFixture(); f.authority.ready = false; PayReply<PayPending> reply = null; f.Coordinator().Begin(f.request, x => reply = x);
                Check(reply != null && !reply.Succeeded && f.store.purchases == 0 && f.journal.saved == null, "No purchase without authoritative wallet readiness");
            });
            Scenario("journal failure precedes checkout", () => {
                var f = new PayFixture(); f.journal.fail = true; PayReply<PayPending> reply = null; f.Coordinator().Begin(f.request, x => reply = x);
                Check(reply != null && !reply.Succeeded && f.store.purchases == 0 && f.store.acknowledgements == 0, "Failed persistence cannot dispatch purchase");
            });
            Scenario("confirmed delivery exactly once", () => {
                var f = new PayFixture(); var c = f.Coordinator(); int completions = 0; PayReply<PayPending> reply = null; c.Begin(f.request, x => { reply = x; completions++; });
                Check(reply != null && reply.Succeeded && reply.value.phase == "Acknowledged" && !c.Busy, "Confirmed delivery finishes");
                Check(f.store.purchases == 1 && f.authority.reconciliations == 1 && f.store.acknowledgements == 1, "One checkout, reconcile and acknowledgement");
                Check(f.journal.events.First() == "save:AwaitingPayment" && f.journal.events.Contains("save:AcknowledgementPending") && f.journal.events.Last() == "save:Acknowledged", "Journal surrounds irreversible stages");
                PayReply<PayPending> replay = null; c.Begin(f.request, x => { replay = x; completions++; });
                Check(replay != null && replay.Succeeded, "Completed exact order freshly reconciled");
                Check(completions == 2 && f.store.purchases == 1 && f.store.acknowledgements == 2 && f.authority.reconciliations == 2 && f.store.lookups == 2, "Completed replay checks authority again without repurchasing");
                var changed = new PayRequest(f.request.orderId, "other_product", f.request.appUserId, f.request.developerPayload, 1, true); PayReply<PayPending> denied = null; c.Begin(changed, x => denied = x); Check(denied != null && !denied.Succeeded, "Completed order cannot change product");
                changed = new PayRequest(f.request.orderId, f.request.productId, new string('d', 32), f.request.developerPayload, 1, true); denied = null; c.Begin(changed, x => denied = x); Check(denied != null && !denied.Succeeded, "Completed order cannot change account");
                changed = new PayRequest(f.request.orderId, f.request.productId, f.request.appUserId, f.request.developerPayload, 1, false); denied = null; c.Begin(changed, x => denied = x); Check(denied != null && !denied.Succeeded, "Completed order cannot change environment");
            });
            Scenario("fabricated acknowledged journal cannot authorize success", () => {
                var f = new PayFixture(); f.journal.saved = new PayPending(f.request, "Acknowledged", f.store.observed.locator); PayReply<PayPending> reply = null; f.Coordinator().Begin(f.request, x => reply = x);
                Check(reply != null && !reply.Succeeded && f.store.acknowledgements == 0 && f.store.purchases == 0, "Phase alone without an authoritative receipt is insufficient");
            });
            Scenario("completed receipt cannot bypass current server denial", () => {
                var f = new PayFixture(); PayReply<PayPending> initial = null; f.Coordinator().Begin(f.request, x => initial = x); Check(initial != null && initial.Succeeded, "Initial confirmed delivery"); f.authority.spendable = false;
                PayReply<PayPending> reply = null; f.Coordinator().Recover(x => reply = x);
                Check(reply != null && !reply.Succeeded && f.store.purchases == 1 && f.authority.reconciliations == 2 && f.store.acknowledgements == 1, "Fresh denied authority overrides cached acknowledged receipt");
            });
            Scenario("unknown outcome recovers without repurchase", () => {
                var f = new PayFixture(); f.store.unknown = true; PayReply<PayPending> first = null; f.Coordinator().Begin(f.request, x => first = x);
                Check(first != null && !first.Succeeded && first.error.outcomeUnknown && f.journal.saved != null, "Unknown outcome remains journaled");
                PayReply<PayPending> recovered = null; f.Coordinator().Recover(x => recovered = x);
                Check(recovered != null && recovered.Succeeded && f.store.purchases == 1 && f.store.lists == 1 && f.store.acknowledgements == 1, "Recovery queries existing purchase, never buys again");
            });
            Scenario("nonspendable server credit cannot acknowledge", () => {
                var f = new PayFixture(); f.authority.spendable = false; PayReply<PayPending> reply = null; f.Coordinator().Begin(f.request, x => reply = x);
                Check(reply != null && !reply.Succeeded && f.store.acknowledgements == 0 && f.journal.saved.phase == "AwaitingAuthority", "Server-only credit remains pending without acknowledgement");
            });
            Scenario("hold is not confirmed delivery", () => {
                var f = new PayFixture(); var p = f.store.observed; f.store.observed = new PayPurchase(p.locator, p.developerPayload, "PAID", "TWO_STEP", "PENDING"); PayReply<PayPending> reply = null; f.Coordinator().Begin(f.request, x => reply = x);
                Check(reply != null && !reply.Succeeded && f.store.acknowledgements == 0, "Held payment does not deliver even with an incorrect positive test authority");
            });
            Scenario("cancellation and duplicate callbacks fenced", () => {
                var f = new PayFixture(); f.store.hold = true; var c = f.Coordinator(); int completions = 0; c.Begin(f.request, _ => completions++); Check(c.Busy, "Deferred checkout busy"); c.Cancel(); f.store.delayed(PayReply<PayLocator>.Ok(f.store.observed.locator));
                Check(!c.Busy && completions == 0 && f.authority.reconciliations == 0 && f.journal.saved != null, "Canceled callback cannot act; journal remains recoverable");
                var g = new PayFixture(); g.store.hold = true; int callbacks = 0; g.Coordinator().Begin(g.request, _ => callbacks++); var result = PayReply<PayLocator>.Ok(g.store.observed.locator); g.store.delayed(result); g.store.delayed(result);
                Check(callbacks == 1 && g.store.acknowledgements == 1 && g.authority.reconciliations == 1, "Duplicate provider callback finishes once");
            });
            Scenario("acknowledgement retry retains paid receipt", () => {
                var f = new PayFixture(); f.store.failAck = true; PayReply<PayPending> first = null; f.Coordinator().Begin(f.request, x => first = x);
                Check(first != null && !first.Succeeded && f.journal.saved.phase == "AcknowledgementPending" && f.journal.saved.receipt != null, "Lost acknowledgement retains committed receipt");
                PayReply<PayPending> recovered = null; f.Coordinator().Recover(x => recovered = x);
                Check(recovered != null && recovered.Succeeded && f.store.purchases == 1 && f.store.acknowledgements == 2, "Acknowledgement recovery does not repurchase");
            });
            Scenario("delayed stage exception releases busy state", () => {
                var f = new PayFixture(); f.store.hold = true; f.store.throwLookup = true; var c = f.Coordinator(); int callbacks = 0; PayReply<PayPending> reply = null; c.Begin(f.request, x => { reply = x; callbacks++; });
                f.store.delayed(PayReply<PayLocator>.Ok(f.store.observed.locator)); Check(callbacks == 1 && reply != null && !reply.Succeeded && reply.error.outcomeUnknown && !c.Busy && f.journal.saved != null, "Delayed exception fails closed without stranding busy state");
            });
        }
        static PayDeliveryReceipt Receipt(PayFixture fixture)
        {
            var locator = fixture.store.observed.locator;
            return new PayDeliveryReceipt(fixture.request.orderId, fixture.request.productId, fixture.request.appUserId,
                locator.purchaseId, locator.invoiceId, "synthetic-durable-receipt", fixture.request.sandbox, true, true);
        }
        static void DiskJournalCases()
        {
            void Scenario(string name, Action<string> action) { Case("Disk journal: " + name, () => { action(Path.Combine(temporary, Guid.NewGuid().ToString("N") + ".journal")); report.diskJournalCases++; }); }
            void Save(FilePayJournal journal, PayPending value) { string error; Check(journal.TrySave(value, out error) && string.IsNullOrEmpty(error), "Actual disk save succeeds: " + value.phase); }
            Scenario("fresh instance and every durable phase", path => {
                var f = new PayFixture(); var journal = new FilePayJournal(path, f.request.appUserId);
                Check(journal.Load() == null, "Missing primary has no fabricated journal");
                foreach(string phase in new[] { "AwaitingPayment", "OutcomeUnknown", "AwaitingRecovery", "AwaitingAuthority", "AcknowledgementPending", "Acknowledged" }) {
                    bool early = phase == "AwaitingPayment" || phase == "OutcomeUnknown", delivered = phase == "AcknowledgementPending" || phase == "Acknowledged";
                    Save(journal, new PayPending(f.request, phase, early ? null : f.store.observed.locator, delivered ? Receipt(f) : null));
                    var loaded = new FilePayJournal(path, f.request.appUserId).Load();
                    Check(loaded != null && loaded.Valid && loaded.phase == phase && loaded.request.SameOrder(f.request), "Fresh instance retains exact phase/order");
                    Check(early ? loaded.locator == null : loaded.locator.purchaseId == f.store.observed.locator.purchaseId && loaded.locator.invoiceId == f.store.observed.locator.invoiceId, "Fresh instance retains exact purchase correlation");
                    Check(delivered ? loaded.receipt.Matches(f.request, f.store.observed) : loaded.receipt == null, "Delivery metadata exists only after committed receipt");
                }
                Check(File.Exists(path + ".bak") && Directory.GetFiles(temporary, Path.GetFileName(path) + ".*.tmp").Length == 0, "Replacement leaves backup and no temporary-write residue");
            });
            Scenario("two independent owners cannot dispatch twice", path => {
                var first = new PayFixture(); first.store.hold = true;
                var coordinator = new PayDeliveryCoordinator(first.store, first.authority, new FilePayJournal(path, first.request.appUserId));
                coordinator.Begin(first.request, _ => { });
                Check(coordinator.Busy && first.store.purchases == 1, "First owner persisted before deferred checkout");
                var second = new PayFixture(); PayReply<PayPending> reply = null;
                new PayDeliveryCoordinator(second.store, second.authority, new FilePayJournal(path, second.request.appUserId)).Begin(second.request, x => reply = x);
                Check(reply != null && !reply.Succeeded && second.store.purchases == 0 && second.store.acknowledgements == 0, "Fresh owner sees pending order and cannot repurchase");
                string error; Check(!new FilePayJournal(path, first.request.appUserId).TrySave(new PayPending(first.request, "AwaitingPayment"), out error), "Journal itself rejects a second checkout claim");
                coordinator.Cancel(); first.store.delayed(PayReply<PayLocator>.Ok(first.store.observed.locator));
                Check(new FilePayJournal(path, first.request.appUserId).Load().phase == "AwaitingPayment" && first.authority.reconciliations == 0, "Canceled callback cannot advance persisted ownership");
            });
            Scenario("exclusive lock failure precedes checkout", path => {
                var f = new PayFixture(); var journal = new FilePayJournal(path, f.request.appUserId);
                using(var exclusive = new FileStream(path + ".lock", FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None)) {
                    Throws<InvalidOperationException>(() => journal.Load(), "Competing lock refuses an inconsistent read");
                    string error; Check(!journal.TrySave(new PayPending(f.request, "AwaitingPayment"), out error) && !string.IsNullOrEmpty(error), "Competing lock reports persistence failure");
                    PayReply<PayPending> reply = null; var coordinator = new PayDeliveryCoordinator(f.store, f.authority, journal); coordinator.Begin(f.request, x => reply = x);
                    Check(reply != null && !reply.Succeeded && !coordinator.Busy && f.store.purchases == 0 && !File.Exists(path), "Unavailable journal cannot dispatch checkout or create a primary");
                }
                Save(journal, new PayPending(f.request, "AwaitingPayment"));
                Check(new FilePayJournal(path, f.request.appUserId).Load().Valid, "Released lock permits a later independent owner");
            });
            Scenario("identity and purchase metadata cannot be replaced", path => {
                var f = new PayFixture(); var journal = new FilePayJournal(path, f.request.appUserId); var locator = f.store.observed.locator;
                Save(journal, new PayPending(f.request, "AwaitingRecovery", locator)); byte[] original = File.ReadAllBytes(path); string error;
                Check(!journal.TrySave(new PayPending(f.request, "OutcomeUnknown"), out error), "Known purchase identity cannot be erased");
                var other = new PayLocator("87654321-4321-4321-4321-cba987654321", "12346", f.request.orderId, f.request.productId, 1, true);
                Check(!journal.TrySave(new PayPending(f.request, "AwaitingRecovery", other), out error), "Known purchase/invoice cannot be changed");
                var changed = new PayRequest(f.request.orderId, "hotr_coins_5000", f.request.appUserId, f.request.developerPayload, 1, true);
                Check(!journal.TrySave(new PayPending(changed, "OutcomeUnknown"), out error), "An order cannot change SKU");
                Throws<InvalidOperationException>(() => new FilePayJournal(path, new string('d', 32)).Load(), "Other account cannot load this journal");
                Check(original.SequenceEqual(File.ReadAllBytes(path)), "Every rejected identity mutation leaves primary unchanged");
            });
            Scenario("corrupt primary never falls back to backup", path => {
                var f = new PayFixture(); var journal = new FilePayJournal(path, f.request.appUserId);
                Save(journal, new PayPending(f.request, "AwaitingPayment")); Save(journal, new PayPending(f.request, "OutcomeUnknown"));
                byte[] backup = File.ReadAllBytes(path + ".bak"); string original = File.ReadAllText(path);
                foreach(byte[] corrupt in new[] { System.Text.Encoding.UTF8.GetBytes(original.Replace("hotr_coins_1000", "hotr_coins_5000")), new byte[] { 0xff, 0xfe }, new byte[0], new byte[32769] }) {
                    File.WriteAllBytes(path, corrupt); Throws<InvalidOperationException>(() => new FilePayJournal(path, f.request.appUserId).Load(), "Corruption/invalid UTF8/size fails closed");
                    string error; Check(!journal.TrySave(new PayPending(f.request, "OutcomeUnknown"), out error), "Corrupt primary cannot be overwritten by normal recovery");
                    Check(corrupt.SequenceEqual(File.ReadAllBytes(path)) && backup.SequenceEqual(File.ReadAllBytes(path + ".bak")), "Corrupt main and previous backup remain intact for diagnosis");
                }
            });
            Scenario("fresh recovery rechecks authority without purchasing", path => {
                var f = new PayFixture(); var journal = new FilePayJournal(path, f.request.appUserId); Save(journal, new PayPending(f.request, "OutcomeUnknown"));
                PayReply<PayPending> recovered = null; new PayDeliveryCoordinator(f.store, f.authority, new FilePayJournal(path, f.request.appUserId)).Recover(x => recovered = x);
                Check(recovered != null && recovered.Succeeded && f.store.purchases == 0 && f.store.lists == 1 && f.authority.reconciliations == 1 && f.store.acknowledgements == 1, "Actual disk recovery queries existing checkout and fresh authority");
                Check(new FilePayJournal(path, f.request.appUserId).Load().phase == "Acknowledged", "Fresh instance reads completed delivery metadata");
                f.authority.spendable = false; PayReply<PayPending> denied = null;
                new PayDeliveryCoordinator(f.store, f.authority, new FilePayJournal(path, f.request.appUserId)).Recover(x => denied = x);
                Check(denied != null && !denied.Succeeded && f.authority.reconciliations == 2 && f.store.acknowledgements == 1 && f.store.purchases == 0, "Saved acknowledgement cannot bypass newer server denial");
            });
        }
        static string LiteralWallet(RuStoreServerWallet value)
        {
            string Bool(bool v) => v ? "true" : "false";
            return "{\"playerId\":\"" + value.playerId + "\",\"balanceScope\":\"" + value.balanceScope + "\",\"initialized\":" + Bool(value.initialized) +
                ",\"refundReviewRequired\":" + Bool(value.refundReviewRequired) + ",\"productionEnabled\":" + Bool(value.productionEnabled) +
                ",\"normalUnityProfileIntegrated\":" + Bool(value.normalUnityProfileIntegrated) + ",\"localProfileMutated\":" + Bool(value.localProfileMutated) +
                ",\"revision\":" + value.revision + ",\"coins\":" + value.coins + ",\"stars\":" + value.stars + ",\"lives\":" + value.lives + ",\"maxLives\":" + value.maxLives +
                ",\"completed\":" + value.completed + ",\"currentLevel\":" + value.currentLevel + ",\"serverUtc\":" + value.serverUtc + ",\"nextLifeAt\":" + value.nextLifeAt +
                ",\"starting\":[" + string.Join(",", value.starting) + "],\"tools\":[" + string.Join(",", value.tools) + "],\"activeAttempt\":null}";
        }
        static string LiteralCreatedOrder(RuStoreServerOrder value)
        {
            return "{\"orderId\":\"" + value.orderId + "\",\"playerId\":\"" + value.playerId + "\",\"state\":\"" + value.state +
                "\",\"catalogVersion\":\"" + value.catalogVersion + "\",\"productId\":\"" + value.productId + "\",\"coins\":" + value.coins + ",\"amountMinor\":" + value.amountMinor +
                ",\"currency\":\"RUB\",\"balanceScope\":\"server_wallet\",\"productionEnabled\":false,\"normalUnityProfileIntegrated\":false,\"localProfileMutated\":false," +
                "\"availableToSpend\":false,\"availableInServerWallet\":false,\"invoiceId\":null,\"purchaseId\":null,\"deliveryAcknowledgement\":null,\"pendingVerification\":[],\"sdk\":" + JsonUtility.ToJson(value.sdk) + ",\"credit\":null}";
        }
        static void ClientCases()
        {
            void Scenario(string name, Action action) { Case("Staging client: " + name, () => { action(); report.clientCases++; }); }
            Scenario("explicit transport configuration", () => {
                using(var client = new RuStoreBackendClient()) {
                    PayReply<RuStoreServerWallet> reply = null; client.GetWallet(x => reply = x);
                    Check(!client.Configured && !client.WalletReady && !client.Busy && reply != null && !reply.Succeeded, "Default client is closed without automatic dispatch");
                }
                Check(RuStoreBackendClient.IsAllowedOrigin("https://billing.hotr-nativecase.ru/"), "Explicit deployed-origin syntax control");
                Check(RuStoreBackendClient.IsAllowedOrigin("http://127.0.0.1:8787/", true), "Native Editor permits only opted-in loopback HTTP");
                foreach(string origin in new[] { null, "", "http://127.0.0.1:8787/", "http://pay.hotr-nativecase.ru/", "https://user:synthetic@pay.hotr-nativecase.ru/", "https://pay.hotr-nativecase.ru/path", "https://pay.hotr-nativecase.ru/?x=1", "https://pay.hotr-nativecase.ru/#fragment", "https://pay.hotr-nativecase.ru/\n", "https://pay.example/", "https://pay.invalid/" })
                    Check(!RuStoreBackendClient.IsAllowedOrigin(origin), "Unapproved origin rejected");
                Check(!RuStoreBackendClient.IsAllowedOrigin("http://127.0.0.2:8787/", true) && !RuStoreBackendClient.IsAllowedOrigin("http://10.0.2.2:8787/", true), "Development exception is exact loopback, not arbitrary private cleartext");
                foreach(string credential in new[] { null, "", new string('x', 42), new string('x', 44), new string('x', 42) + "\n" })
                    Throws<ArgumentException>(() => new RuStoreBackendClient("https://billing.hotr-nativecase.ru", credential, new string('b', 32), true, false, _ => { }), "Malformed in-memory bearer rejected");
                Throws<ArgumentException>(() => new RuStoreBackendClient("https://billing.hotr-nativecase.ru", new string('x', 43), new string('b', 32) + "\n", true, false, _ => { }), "Bound player identity rejects trailing input");
            });
            Scenario("bound wallet and immutable order parsing", () => {
                var fixture = new PayFixture(); var client = new RuStoreBackendClient("https://billing.hotr-nativecase.ru", new string('x', 43), fixture.request.appUserId, true, false, _ => { });
                const System.Reflection.BindingFlags flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
                var walletParser = typeof(RuStoreBackendClient).GetMethod("Wallet", flags); var orderParser = typeof(RuStoreBackendClient).GetMethod("Order", flags);
                var wallet = new RuStoreServerWallet { playerId = fixture.request.appUserId, balanceScope = "server_wallet", initialized = true, revision = 1, coins = 1250, lives = 5, maxLives = 5, currentLevel = 1, serverUtc = 1000, starting = new[] { 5, 5, 3, 2 }, tools = new[] { 3, 3, 3, 3 } };
                string json = LiteralWallet(wallet); walletParser.Invoke(client, new object[] { json }); Check(client.WalletReady, "Synthetic parser control accepts the fully bound wallet with literal null active attempt");
                Throws<System.Reflection.TargetInvocationException>(() => walletParser.Invoke(client, new object[] { JsonUtility.ToJson(wallet) }), "Serializer-created default inline attempt is invalid, not treated as absent");
                foreach(string invalid in new[] { json.Replace(",\"activeAttempt\":null", ""), json.Replace("\"activeAttempt\":null", "\"activeAttempt\":{}"), json.Replace("\"activeAttempt\":null", "\"activeAttempt\":[]"), json.Replace("\"coins\":1250", "\"coins\":null"), json.Replace("\"coins\":1250", "\"coins\":1250,\"coins\":1250") })
                    Throws<System.Reflection.TargetInvocationException>(() => walletParser.Invoke(client, new object[] { invalid }), "Missing/malformed/duplicate values are rejected rather than null-normalized");
                foreach(string field in new[] { "productionEnabled", "normalUnityProfileIntegrated", "localProfileMutated" }) {
                    string missing = json.Replace("\"" + field + "\":false,", ""); Check(missing != json, "Missing-flag fixture actually removes a field");
                    Throws<System.Reflection.TargetInvocationException>(() => walletParser.Invoke(client, new object[] { missing }), "Missing security flag cannot default to approved");
                }
                wallet.refundReviewRequired = true; walletParser.Invoke(client, new object[] { LiteralWallet(wallet) }); Check(!client.WalletReady, "Quarantined server wallet cannot enable payment"); wallet.refundReviewRequired = false;
                wallet.initialized = false; walletParser.Invoke(client, new object[] { LiteralWallet(wallet) }); Check(!client.WalletReady, "Historical uninitialized wallet cannot enable payment"); wallet.initialized = true;
                wallet.playerId = new string('d', 32); Throws<System.Reflection.TargetInvocationException>(() => walletParser.Invoke(client, new object[] { LiteralWallet(wallet) }), "Cross-account wallet rejected"); wallet.playerId = fixture.request.appUserId;
                walletParser.Invoke(client, new object[] { LiteralWallet(wallet) });
                var mutationParser = typeof(RuStoreBackendClient).GetMethod("Mutation", flags);
                var mutation = (RuStoreWalletMutation)mutationParser.Invoke(client, new object[] { "{\"receiptId\":\"wallet/synthetic\",\"operation\":\"life.refill\",\"wallet\":" + LiteralWallet(wallet) + ",\"attempt\":null}", "life.refill", null });
                Check(mutation.attempt == null && mutation.wallet.activeAttempt == null, "Nested wallet and mutation literal nulls survive Unity DTO conversion");
                typeof(RuStoreBackendClient).GetField("walletVerifiedTicks", flags).SetValue(client, System.Diagnostics.Stopwatch.GetTimestamp() - 31L * System.Diagnostics.Stopwatch.Frequency); Check(!client.WalletReady, "Readiness expires instead of trusting an indefinitely cached wallet");
                var order = new RuStoreServerOrder { orderId = fixture.request.orderId, playerId = fixture.request.appUserId, state = "Created", catalogVersion = "synthetic-parser-only", productId = "coins-1000", coins = 1000, amountMinor = 9900, currency = "RUB", balanceScope = "server_wallet", sdk = new RuStoreServerSdkOrder { orderId = fixture.request.orderId, productId = fixture.request.productId, appUserId = fixture.request.appUserId, developerPayload = fixture.request.developerPayload, quantity = 1, sandbox = true } };
                var created = (RuStoreServerOrder)orderParser.Invoke(client, new object[] { LiteralCreatedOrder(order), fixture.request.orderId, "coins-1000", fixture.request }); Check(created.credit == null && created.deliveryAcknowledgement == null, "Unpaid order literal null does not manufacture credit or delivery metadata");
                order.amountMinor++; Throws<System.Reflection.TargetInvocationException>(() => orderParser.Invoke(client, new object[] { LiteralCreatedOrder(order), fixture.request.orderId, "coins-1000", fixture.request }), "Known server order cannot change frozen price"); order.amountMinor--;
                order.sdk.productId = "hotr_coins_5000"; Throws<System.Reflection.TargetInvocationException>(() => orderParser.Invoke(client, new object[] { LiteralCreatedOrder(order), fixture.request.orderId, "coins-1000", fixture.request }), "Known server order cannot change SDK product"); client.Dispose();
            });
            Scenario("revoke fences a queued coroutine", () => {
                var pending = new List<IEnumerator>(); var client = new RuStoreBackendClient("https://billing.hotr-nativecase.ru", new string('x', 43), new string('b', 32), true, false, pending.Add);
                int callbacks = 0; PayReply<RuStoreServerWallet> result = null; client.GetWallet(x => { result = x; callbacks++; });
                Check(client.Busy && pending.Count == 1 && callbacks == 0, "Async operation is explicitly owned before dispatch"); client.Revoke();
                Check(callbacks == 1 && result != null && !result.Succeeded && !client.Configured && !client.WalletReady && !client.Busy, "Revocation completes once without success or retained readiness");
                Check(!pending[0].MoveNext() && callbacks == 1, "A previously queued coroutine cannot create a request after revocation"); (pending[0] as IDisposable)?.Dispose(); client.Dispose();
                pending.Clear(); callbacks = 0; result = null;
                var revoked = new RuStoreBackendClient("https://billing.hotr-nativecase.ru", new string('x', 43), new string('b', 32), true, false, pending.Add); revoked.GetWallet(x => { result = x; callbacks++; });
                var worker = new System.Threading.Thread(revoked.Revoke); worker.Start(); Check(worker.Join(2000), "Cross-thread revoke finishes without waiting on Unity");
                Check(!revoked.Configured && !revoked.WalletReady && callbacks == 0, "Cross-thread revoke clears credentials/readiness without calling owner callback on worker");
                Check(!pending[0].MoveNext() && callbacks == 1 && result != null && !result.Succeeded && !revoked.Busy, "Owner coroutine returns only failure after cross-thread revocation"); (pending[0] as IDisposable)?.Dispose();
            });
            Scenario("streaming response bound", () => {
                var type = typeof(RuStoreBackendClient).GetNestedType("BoundedDownload", System.Reflection.BindingFlags.NonPublic);
                const System.Reflection.BindingFlags flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
                using(var buffer = (IDisposable)Activator.CreateInstance(type, true)) {
                    var receive = type.GetMethod("ReceiveData", flags); var bytes = Enumerable.Repeat((byte)'x', 8192).ToArray();
                    for(int i = 0; i < 8; i++) Check((bool)receive.Invoke(buffer, new object[] { bytes, bytes.Length }), "Streaming buffer accepts bytes up to64KiB");
                    Check(!(bool)receive.Invoke(buffer, new object[] { new byte[] { 1 }, 1 }) && (bool)type.GetField("exceeded").GetValue(buffer), "Byte65537 is rejected during reception, not after an unbounded download");
                }
            });
        }
        [Serializable] sealed class HttpConfig { public string origin, playerId, token, expectedPurchaseId, invoiceId, runId; }
        [Serializable] sealed class HttpReport {
            public string status, utc, unity, runId, orderId, attemptId;
            public int checks, requests, duplicateCommands, finalCoins, finalLives;
            public long finalRevision;
            public int[] finalStarting, finalTools;
            public bool ordinaryProfileIntegrationDisabled;
            public string scope = "Actual Unity Editor IEnumerator/UnityWebRequest HTTP to a separate isolated FastAPI/SQLite staging fixture, with a synthetic CONFIRMED store provider and explicitly supplied SDK observation. No RuStore SDK payment, acknowledgement, real bank return, production identity, ordinary Unity-profile migration or device claim. Command IDs are explicit and reused only for exact retry.";
            public List<string> passed = new List<string>(), errors = new List<string>();
        }
        static HttpReport http;
        static HttpConfig httpConfig;
        static RuStoreBackendClient httpClient;
        static Stack<IEnumerator> httpStack;
        static AsyncOperation httpWaiting;
        static double httpStarted;
        static void HttpCheck(bool passed, string name) { http.checks++; if(!passed) throw new InvalidOperationException(name); http.passed.Add(name); }
        static string Command(string name) => Hash(System.Text.Encoding.UTF8.GetBytes(httpConfig.runId + "|" + name)).Substring(0, 32);
        static IEnumerator HttpAwait<T>(Action<Action<PayReply<T>>> call, Action<T> inspect) where T : class {
            PayReply<T> result = null; int count = 0; http.requests++;
            call(value => { result = value; count++; });
            while(result == null) yield return null;
            HttpCheck(count == 1 && result.Succeeded, "Typed HTTP response completes once: " + typeof(T).Name);
            inspect(result.value);
        }
        public static void RunHttp()
        {
            http = new HttpReport { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion };
            try {
                string input = Environment.GetEnvironmentVariable("HOTR_RUSTORE81_HTTP_CONFIG");
                string allowed = Path.GetFullPath("../.verification-cache/RuStore81/");
                if(string.IsNullOrEmpty(input) || !Path.GetFullPath(input).StartsWith(allowed, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException();
                httpConfig = JsonUtility.FromJson<HttpConfig>(File.ReadAllText(input)); Guid run, purchase;
                if(httpConfig == null || !Guid.TryParseExact(httpConfig.runId, "N", out run) || !Guid.TryParseExact(httpConfig.expectedPurchaseId, "D", out purchase) ||
                   httpConfig.invoiceId != "8100001" || !RuStoreBackendClient.IsAllowedOrigin(httpConfig.origin, true) || !new Uri(httpConfig.origin).IsLoopback) throw new InvalidOperationException();
                http.runId = httpConfig.runId; httpStack = new Stack<IEnumerator>(); httpStarted = EditorApplication.timeSinceStartup;
                httpClient = new RuStoreBackendClient(httpConfig.origin, httpConfig.token, httpConfig.playerId, true, true, routine => httpStack.Push(routine));
                httpStack.Push(HttpChecks()); EditorApplication.update += HttpTick;
            } catch(Exception) { http.errors.Add("Explicit isolated HTTP fixture configuration unavailable"); HttpFinish(); }
        }
        static void HttpTick()
        {
            try {
                if(EditorApplication.timeSinceStartup - httpStarted > 180) throw new TimeoutException("Isolated native HTTP fixture timed out");
                if(httpWaiting != null && !httpWaiting.isDone) return; httpWaiting = null;
                if(httpStack.Count == 0) { HttpFinish(); return; }
                var routine = httpStack.Peek(); if(!routine.MoveNext()) { httpStack.Pop(); return; }
                if(routine.Current is IEnumerator nested) httpStack.Push(nested); else if(routine.Current is AsyncOperation waiting) httpWaiting = waiting;
            } catch(Exception error) { http.errors.Add(error.GetType().Name + ": " + error.Message); HttpFinish(); }
        }
        static IEnumerator HttpChecks()
        {
            RuStoreServerWallet wallet = null; RuStoreServerOrder order = null;
            HttpCheck(!httpClient.WalletReady, "Explicit configuration alone does not mark wallet ready");
            yield return HttpAwait<RuStoreServerWallet>(done => httpClient.GetWallet(done), value => wallet = value);
            HttpCheck(httpClient.WalletReady && wallet.initialized && !wallet.refundReviewRequired && wallet.coins == 1250 && wallet.lives == 5 && wallet.revision == 1, "Fresh authenticated genesis wallet establishes staging readiness");
            string create = Command("create-order");
            yield return HttpAwait<RuStoreServerOrder>(done => httpClient.CreateOrder(create, "coins-1000", done), value => order = value);
            http.orderId = order.orderId; string creation = JsonUtility.ToJson(order);
            HttpCheck(order.state == "Created" && order.coins == 1000 && order.amountMinor == 9900 && order.currency == "RUB" && order.Request().Valid && !order.availableToSpend, "Server creates only the explicitly mapped staging order");
            yield return HttpAwait<RuStoreServerOrder>(done => httpClient.CreateOrder(create, "coins-1000", done), value => HttpCheck(JsonUtility.ToJson(value) == creation, "Exact create command returns the original receipt snapshot")); http.duplicateCommands++;
            yield return HttpAwait<RuStoreServerOrder>(done => httpClient.GetOrder(http.orderId, done), value => order = value);
            var request = order.Request(); var observation = new PayPurchase(new PayLocator(httpConfig.expectedPurchaseId, httpConfig.invoiceId, request.orderId, request.productId, 1, true), request.developerPayload, "CONFIRMED", "ONE_STEP", "PENDING");
            PayDeliveryReceipt first = null;
            yield return HttpAwait<PayDeliveryReceipt>(done => httpClient.Reconcile(request, observation, done), value => first = value);
            HttpCheck(first.Matches(request, observation) && first.durable && first.availableToSpend, "Canonical confirmed server-wallet receipt correlates all SDK identities");
            yield return HttpAwait<PayDeliveryReceipt>(done => httpClient.Reconcile(request, observation, done), value => HttpCheck(value.receiptId == first.receiptId, "Repeated provider reconciliation retains one durable receipt"));
            yield return HttpAwait<RuStoreServerWallet>(done => httpClient.GetWallet(done), value => wallet = value);
            HttpCheck(wallet.coins == 2250 && wallet.lives == 5 && !wallet.normalUnityProfileIntegrated && !wallet.localProfileMutated, "Server purchase projects exactly1000coins and leaves ordinary Unity profile disconnected");
            string reserve = Command("reserve"), start = Command("start"), tool = Command("tool"), quit = Command("quit");
            RuStoreWalletMutation response = null; long expected = wallet.revision;
            yield return HttpAwait<RuStoreWalletMutation>(done => httpClient.Reserve(reserve, expected, 1, new[] { 1, 0, 0, 0 }, done), value => response = value);
            http.attemptId = response.attempt.attemptId; string original = JsonUtility.ToJson(response);
            HttpCheck(response.attempt.state == "Reserved" && response.wallet.starting.SequenceEqual(new[] { 5, 5, 3, 2 }) && response.wallet.lives == 5, "Reserve creates server identity without spending selected stock");
            yield return HttpAwait<RuStoreWalletMutation>(done => httpClient.Reserve(reserve, expected, 1, new[] { 1, 0, 0, 0 }, done), value => HttpCheck(JsonUtility.ToJson(value) == original, "Reserve retry returns exact receipt")); http.duplicateCommands++;
            yield return HttpAwait<RuStoreServerWallet>(done => httpClient.GetWallet(done), value => wallet = value); expected = wallet.revision;
            yield return HttpAwait<RuStoreWalletMutation>(done => httpClient.Start(start, expected, http.attemptId, done), value => response = value); original = JsonUtility.ToJson(response);
            HttpCheck(response.attempt.state == "Started" && response.wallet.starting.SequenceEqual(new[] { 4, 5, 3, 2 }), "Start spends one selected Rocket and preserves other inventory");
            yield return HttpAwait<RuStoreWalletMutation>(done => httpClient.Start(start, expected, http.attemptId, done), value => HttpCheck(JsonUtility.ToJson(value) == original, "Start retry does not spend selected stock again")); http.duplicateCommands++;
            yield return HttpAwait<RuStoreServerAttempt>(done => httpClient.GetAttempt(http.attemptId, done), value => HttpCheck(value.state == "Started" && value.reward.coins == 50 && value.reward.stars == 1, "Typed attempt read preserves server-authorized metadata"));
            yield return HttpAwait<RuStoreServerWallet>(done => httpClient.GetWallet(done), value => wallet = value); expected = wallet.revision;
            yield return HttpAwait<RuStoreWalletMutation>(done => httpClient.SpendTool(tool, expected, http.attemptId, 0, done), value => response = value); original = JsonUtility.ToJson(response);
            HttpCheck(response.wallet.tools.SequenceEqual(new[] { 2, 3, 3, 3 }) && response.wallet.coins == 2250, "Typed tool command spends exactly one server tool");
            yield return HttpAwait<RuStoreWalletMutation>(done => httpClient.SpendTool(tool, expected, http.attemptId, 0, done), value => HttpCheck(JsonUtility.ToJson(value) == original, "Tool retry returns exact receipt")); http.duplicateCommands++;
            yield return HttpAwait<RuStoreServerWallet>(done => httpClient.GetWallet(done), value => wallet = value); expected = wallet.revision;
            yield return HttpAwait<RuStoreWalletMutation>(done => httpClient.Quit(quit, expected, http.attemptId, done), value => response = value); original = JsonUtility.ToJson(response);
            HttpCheck(response.attempt.state == "Lost" && response.wallet.lives == 4 && response.wallet.activeAttempt == null, "Started quit settles one loss and releases active slot");
            yield return HttpAwait<RuStoreWalletMutation>(done => httpClient.Quit(quit, expected, http.attemptId, done), value => HttpCheck(JsonUtility.ToJson(value) == original, "Quit retry cannot charge a second life")); http.duplicateCommands++;
            yield return HttpAwait<RuStoreServerWallet>(done => httpClient.GetWallet(done), value => wallet = value);
            HttpCheck(wallet.coins == 2250 && wallet.lives == 4 && wallet.starting.SequenceEqual(new[] { 4, 5, 3, 2 }) && wallet.tools.SequenceEqual(new[] { 2, 3, 3, 3 }) && wallet.activeAttempt == null, "Fresh read retains exact durable wallet/inventory/attempt result");
            http.finalCoins = wallet.coins; http.finalLives = wallet.lives; http.finalRevision = wallet.revision; http.finalStarting = wallet.starting; http.finalTools = wallet.tools;
            http.ordinaryProfileIntegrationDisabled = !wallet.normalUnityProfileIntegrated && !wallet.localProfileMutated && !wallet.productionEnabled;
            httpClient.Dispose(); HttpCheck(!httpClient.Configured && !httpClient.WalletReady && !httpClient.Busy, "Explicit owner disposal revokes credentials/readiness");
        }
        static void HttpFinish()
        {
            EditorApplication.update -= HttpTick; httpWaiting = null; httpClient?.Dispose();
            if(httpStack != null) while(httpStack.Count > 0) (httpStack.Pop() as IDisposable)?.Dispose();
            httpConfig = null; httpClient = null;
            http.status = http.errors.Count == 0 ? "PASS_NATIVE_RUSTORE81_HTTP_STAGING_CLIENT" : "FAIL_NATIVE_RUSTORE81_HTTP_STAGING_CLIENT";
            string native = Path.Combine(Output, "Native"); Directory.CreateDirectory(native); File.WriteAllText(Path.Combine(native, "HTTP.json"), JsonUtility.ToJson(http, true));
            if(Application.isBatchMode) EditorApplication.Exit(http.errors.Count == 0 ? 0 : 1);
        }
        static readonly string[] ExternalBlockers = {
            "production_identity_and_secure_credential_recovery_not_connected",
            "unified_server_gameplay_wallet_not_connected",
            "provider_notification_authentication_not_configured",
            "native_sandbox_and_external_bank_return_not_verified",
            "production_signing_and_legal_hosting_review_not_complete"
        };
        static string Output => Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_RUSTORE81_OUTPUT") ?? "../Verification/Evidence/RuStore81");
        static string Hash(byte[] data) { using(var algorithm = SHA256.Create()) return string.Concat(algorithm.ComputeHash(data).Select(x => x.ToString("x2"))); }
        static void Check(bool value, string message) { report.checks++; if(!value) throw new InvalidOperationException(message); }
        static void Throws<T>(Action action, string label) where T : Exception
        {
            bool expected = false; try { action(); } catch(T) { expected = true; }
            Check(expected, label);
        }
        static void Case(string name, Action action)
        {
            try { action(); report.cases.Add(name); } catch(Exception error) { report.errors.Add(name + ": " + error); }
        }
        static RuStoreReleaseConfiguration Good() => new RuStoreReleaseConfiguration {
            schemaVersion = 1, packageName = "org.hotr.nativecase", consoleApplicationId = "123456789",
            paymentReturnScheme = "hotr-nativecase-pay", backendOrigin = "https://billing.hotr-nativecase.ru",
            privacyPolicyUrl = "https://legal.hotr-nativecase.ru/privacy", supportUrl = "https://legal.hotr-nativecase.ru/support",
            termsUrl = "https://legal.hotr-nativecase.ru/terms", minimumApiLevel = 26, targetApiLevel = 35, versionCode = 1,
            signingCertificateSha256 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", environment = "sandbox"
        };
        static void Invalid(string name, Action<RuStoreReleaseConfiguration> mutate, string expected)
        {
            var config = Good(); mutate(config); var errors = RuStoreReleasePreflight.Validate(config);
            report.inputMutations++; report.inputs.Add(new InputCase { name = name, blockers = errors.ToArray() });
            Check(errors.SequenceEqual(new[] { expected }), "Single invalid input is isolated: " + name);
        }
        static void WithEnvironment(string path, string channel, Action action)
        {
            string priorPath = Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable);
            string priorChannel = Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ChannelVariable);
            try {
                Environment.SetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable, path);
                Environment.SetEnvironmentVariable(RuStoreReleasePreflight.ChannelVariable, channel); action();
            } finally {
                Environment.SetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable, priorPath);
                Environment.SetEnvironmentVariable(RuStoreReleasePreflight.ChannelVariable, priorChannel);
            }
        }
        static string WriteConfig(string name, string json)
        {
            string path = Path.Combine(temporary, name + ".json"); File.WriteAllText(path, json); return path;
        }
        static List<string> Evaluate(string path)
        {
            List<string> result = null;
            WithEnvironment(path, "rustore", () => { bool supplied; result = RuStoreReleasePreflight.Evaluate(out supplied); Check(supplied == !string.IsNullOrWhiteSpace(path), "Actual configuration presence readback"); });
            return result;
        }
        static void ExternalStillBlocked(List<string> errors)
        {
            Check(ExternalBlockers.All(errors.Contains), "Unconnected production capabilities block independently of syntax");
        }
        static LevelData Level()
        {
            var assets = AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
            Check(assets && assets.boards && assets.boards.levels.Length >= 1, "Actual level bindings exist");
            var level = JsonUtility.FromJson<LevelData>(assets.boards.levels[0].text); level.movesProposal = 1; return level;
        }
        static void Exhaust(BoardModel board)
        {
            int guard = 0;
            while(board.Status == "Playing" && guard++ < 64) {
                var move = NoMovesDeviceProbe.SafeSwap(board); board.Swap(move[0].x, move[0].y, move[1].x, move[1].y);
            }
            Check(board.Status == "Out of moves" && board.Moves == 0, "Actual nonwinning commands exhaust the review board");
        }
        static ProfileService Started(out string attempt, int coins = 2700)
        {
            var initial = PlayerProfile.New(new[] { 5, 5, 3, 2 }); initial.coins = coins;
            var profiles = new ProfileService(new MemoryProfileRepository(initial)); attempt = Guid.NewGuid().ToString("N");
            profiles.Reserve(attempt, 1, "rustore81-native-isolated", new int[4], 50, 1); profiles.CommitStart(attempt); return profiles;
        }

        public static void Run()
        {
            report = new Report { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion };
            string settingsPath = Path.GetFullPath("ProjectSettings/ProjectSettings.asset");
            string manifestPath = Path.GetFullPath("Packages/manifest.json"), lockPath = Path.GetFullPath("Packages/packages-lock.json");
            byte[] settings = File.ReadAllBytes(settingsPath), manifest = File.ReadAllBytes(manifestPath);
            byte[] packageLock = File.Exists(lockPath) ? File.ReadAllBytes(lockPath) : null;
            string configVariable = Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable), channelVariable = Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ChannelVariable);
            bool hadLanguage = PlayerPrefs.HasKey(GameLocale.PreferenceKey); int language = PlayerPrefs.GetInt(GameLocale.PreferenceKey, -1);
            report.projectSettingsBefore = Hash(settings);
            temporary = Path.GetFullPath("../.verification-cache/RuStore81/NativeGuard-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(temporary);
            try {
                Case("Pinned Editor and unconfigured input", () => {
                    Check(Application.unityVersion == "2022.3.62f3", "Pinned Unity version");
                    Check(RuStoreReleasePreflight.Validate(null).SequenceEqual(new[] { "release_configuration_missing" }), "Missing DTO fails closed");
                    Check(RuStoreReleasePreflight.Validate(new RuStoreReleaseConfiguration()).Count >= 10, "Empty DTO cannot activate release");
                });
                Case("Missing, unreadable and malformed files", () => {
                    var absent = Evaluate(null); Check(absent.Contains("release_configuration_missing"), "Missing external file blocks"); ExternalStillBlocked(absent);
                    var missing = Evaluate(Path.Combine(temporary, "not-created.json")); Check(missing.Contains("release_configuration_unreadable"), "Unreadable external file blocks"); ExternalStillBlocked(missing);
                    var malformed = Evaluate(WriteConfig("malformed", "{\"schemaVersion\": [ }")); Check(malformed.Contains("release_configuration_unreadable"), "Malformed external JSON blocks"); ExternalStillBlocked(malformed);
                });
                Case("Synthetic syntax control still cannot release", () => {
                    var fixture = Good(); Check(RuStoreReleasePreflight.Validate(fixture).Count == 0, "Synthetic syntax-positive control");
                    string path = WriteConfig("syntax-only-not-registered", JsonUtility.ToJson(fixture)); ExternalStillBlocked(Evaluate(path));
                    WithEnvironment(path, "rustore", () => Throws<BuildFailedException>(RuStoreReleasePreflight.RequireReady, "Even syntax-complete config cannot bypass missing production authority"));
                    fixture.environment = "production"; Check(RuStoreReleasePreflight.Validate(fixture).Count == 0, "Production environment syntax alone is accepted");
                    ExternalStillBlocked(Evaluate(WriteConfig("production-syntax-only", JsonUtility.ToJson(fixture)))); report.actualReleaseBlocked = true;
                });
                Case("Schema versions", () => { foreach(int value in new[] { -1, 0, 2 }) Invalid("schema-" + value, c => c.schemaVersion = value, "release_schema_unsupported"); });
                Case("Package identifiers", () => {
                    string[] values = { null, "", "game", "com.game", "com.DefaultCompany.game", "com.defaultcompany.game", "com.heartoftherain.verification", "com.example.game", "1com.hotr.game", "com.hotr.game ", "com.hotr.game\n" };
                    for(int i = 0; i < values.Length; i++) { string value = values[i]; Invalid("package-" + i, c => c.packageName = value, "registered_package_name_required"); }
                });
                Case("Console identifiers", () => {
                    string[] values = { null, "", "0", "-1", "01", "12a", "1 ", "1\n", "9223372036854775808", new string('1', 20), new string('1', 21) };
                    for(int i = 0; i < values.Length; i++) { string value = values[i]; Invalid("console-" + i, c => c.consoleApplicationId = value, "console_application_id_required"); }
                });
                Case("Payment return schemes", () => {
                    string[] values = { null, "", "ab", "1hotr", "hotr pay", "Hotr-pay", "http", "https", "file", "intent", "content", "javascript", new string('a', 64) };
                    for(int i = 0; i < values.Length; i++) { string value = values[i]; Invalid("scheme-" + i, c => c.paymentReturnScheme = value, "unique_payment_return_scheme_required"); }
                });
                Case("Backend origins and reserved placeholders", () => {
                    string[] values = { null, "", "http://pay.hotr-nativecase.ru", "https://localhost", "https://127.0.0.1", "https://[::1]", "https://host", "https://example.com", "https://pay.example.org", "https://pay.example.net", "https://pay.example", "https://pay.invalid", "https://pay.test", "https://pay.local", "https://pay.localhost", "https://user:synthetic@pay.hotr-nativecase.ru", "https://pay.hotr-nativecase.ru/path", "https://pay.hotr-nativecase.ru/?value=1", "https://pay.hotr-nativecase.ru/#fragment", "https://pay.hotr-nativecase.ru/\n" };
                    for(int i = 0; i < values.Length; i++) { string value = values[i]; Invalid("backend-" + i, c => c.backendOrigin = value, "deployed_https_backend_required"); }
                });
                Case("Legal URLs", () => {
                    foreach(string value in new[] { null, "http://legal.hotr-nativecase.ru/path", "https://legal.example/privacy", "https://legal.invalid/privacy", "https://user:synthetic@legal.hotr-nativecase.ru/privacy", "https://legal.hotr-nativecase.ru/privacy?q=1", "https://legal.hotr-nativecase.ru/privacy#top" }) {
                        Invalid("privacy-url", c => c.privacyPolicyUrl = value, "russian_privacy_policy_url_required");
                        Invalid("support-url", c => c.supportUrl = value, "support_url_required");
                        Invalid("terms-url", c => c.termsUrl = value, "terms_url_required");
                    }
                });
                Case("Android API and version bounds", () => {
                    foreach(int value in new[] { -1, 0, 25 }) Invalid("minimum-api-" + value, c => c.minimumApiLevel = value, "minimum_api_26_required");
                    foreach(int value in new[] { -1, 0, 25, 1001 }) Invalid("target-api-" + value, c => c.targetApiLevel = value, "explicit_target_api_required");
                    foreach(int value in new[] { -1, 0 }) Invalid("version-code-" + value, c => c.versionCode = value, "version_code_required");
                });
                Case("Signing fingerprint syntax and placeholders", () => {
                    string[] values = { null, "", new string('0', 63), new string('a', 65), new string('g', 64), new string('0', 64), new string('F', 64) };
                    for(int i = 0; i < values.Length; i++) { string value = values[i]; Invalid("certificate-" + i, c => c.signingCertificateSha256 = value, "release_signing_identity_required"); }
                });
                Case("Explicit environments", () => {
                    string[] values = { null, "", "live", "test", "Production", "sandbox ", "production\n" };
                    for(int i = 0; i < values.Length; i++) { string value = values[i]; Invalid("environment-" + i, c => c.environment = value, "explicit_payment_environment_required"); }
                });
                Case("Actual build guard and ordinary channel", () => {
                    var guard = new RuStoreReleaseGuard();
                    WithEnvironment(null, "rustore", () => Throws<BuildFailedException>(() => guard.OnPreprocessBuild(null), "Actual RuStore preprocess guard blocks without a build"));
                    foreach(string channel in new[] { null, "verification", "development" }) WithEnvironment(null, channel, () => guard.OnPreprocessBuild(null));
                    Check(guard.callbackOrder < 0, "Release guard precedes ordinary build work"); report.ordinaryBuildChannelUnaffected = true;
                });
                Case("Example is a proposal outside runtime assets", () => {
                    string path = Path.GetFullPath("../Release/RuStore/release.example.json"); Check(File.Exists(path), "External proposal file exists");
                    var template = JsonUtility.FromJson<ReleaseTemplate>(File.ReadAllText(path));
                    Check(template.status == "UNCONFIGURED_NOT_A_REGISTERED_APPLICATION", "Unregistered status explicit");
                    Check(string.IsNullOrEmpty(template.packageName) && string.IsNullOrEmpty(template.consoleApplicationId) && string.IsNullOrEmpty(template.paymentReturnScheme), "Candidate identifiers are not assigned real identifiers");
                    Check(string.IsNullOrEmpty(template.backendOrigin) && string.IsNullOrEmpty(template.signingCertificateSha256) && template.versionCode == 0, "No invented deployment or signing identity");
                    Check(template.candidateIdentifiers != null && !string.IsNullOrEmpty(template.candidateIdentifiers.packageName) && !string.IsNullOrEmpty(template.candidateIdentifiers.paymentReturnScheme), "Candidate identifier suggestions supplied separately");
                    Check(Directory.GetFiles(Application.dataPath, "release.example.json", SearchOption.AllDirectories).Length == 0, "Draft is not imported into Assets/Resources");
                    Check(template.notificationPaths.status == "IMPLEMENTED_DISABLED_UNHOSTED_UNREGISTERED" && template.notificationPaths.sandbox == "/v1/commerce/notifications/rustore/sandbox" && template.notificationPaths.production == "/v1/commerce/notifications/rustore/production", "Implemented notification paths remain disabled, unhosted and unregistered");
                    ExternalStillBlocked(Evaluate(path)); report.proposalNotRegistered = true;
                });
                Case("Proposed six coin mappings match current Shop", () => {
                    var template = JsonUtility.FromJson<ReleaseTemplate>(File.ReadAllText(Path.GetFullPath("../Release/RuStore/release.example.json")));
                    var asset = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/HeartOfTheRain/App/Shop/Data/ShopCatalog.json"); Check(asset, "Actual imported Shop catalog");
                    var shop = new ShopSession(JsonUtility.FromJson<ShopCatalog>(asset.text)); Check(shop.IsPreview, "Normal Shop stays preview");
                    Check(template.candidateProducts != null && template.candidateProducts.Length == 6 && shop.Coins.Length == 6, "Six existing coin offers retained");
                    Check(template.candidateProducts.Select(p => p.shopOfferId).Distinct().Count() == 6 && template.candidateProducts.Select(p => p.proposedStoreProductId).Distinct().Count() == 6, "Proposed mapping is unique");
                    foreach(var product in template.candidateProducts) {
                        var offer = shop.Coins.Single(o => o.id == product.shopOfferId); Check(!product.enabled && product.coins == offer.coins, "Disabled proposal matches actual coin grant");
                        Check(offer.boostersEach == 0 && Enumerable.Range(0, 4).All(i => offer.StartingCount(i) == 0), "Coin pack does not merge power/tool inventories"); report.coinMappings++;
                    }
                });
                Case("Existing continue rules and disabled default", () => {
                    var defaults = new ContinueRules(); defaults.Validate(); Check(!defaults.enabled && defaults.coinCost == 900 && defaults.extraMoves == 5 && defaults.maximumContinues == 0, "Unconfigured continue service remains disabled with approved values");
                    var design = Resources.Load<NoMovesAssets>("HOTR_NoMoves/Design"); Check(design && design.rules.enabled && design.rules.coinCost == 900 && design.rules.extraMoves == 5 && design.rules.maximumContinues == 0, "Approved local development presentation policy unchanged");
                    var level = Level(); var board = new BoardModel(level); Exhaust(board); string id; var profile = Started(out id);
                    var service = new DevelopmentContinueService(profile, new ContinueRules { enabled = true }, () => 1000, _ => level, false); service.Capture(id, board.Checkpoint());
                    Check(service.Quote(id) == null, "Disabled authority supplies no paid-move offer");
                    Throws<InvalidOperationException>(() => service.Prepare(id, "synthetic-not-an-offer"), "Disabled authority refuses preparing a spend");
                    Check(profile.Read().coins == 2700 && profile.Read().lives == 5 && string.IsNullOrEmpty(profile.Read().attempts.Single().continuation.pending), "Disabled authority does not debit or prepare");
                });
                Case("Repeated approved move purchases preserve board and wallet", () => {
                    var level = Level(); var board = new BoardModel(level); Exhaust(board); string id; var profile = Started(out id);
                    var service = new DevelopmentContinueService(profile, new ContinueRules { enabled = true }, () => 1000, _ => level, true);
                    for(int ordinal = 1; ordinal <= 2; ordinal++) {
                        service.Capture(id, board.Checkpoint()); var before = board.Checkpoint(); var quote = service.Quote(id);
                        Check(quote.cost == 900 && quote.moves == 5, "Repeat quote keeps approved price/moves"); string operation = service.Prepare(id, quote.id); var receipt = service.Purchase(id, operation);
                        Check(receipt.outcome == "Applied" && receipt.cost == 900 && receipt.movesAfter == 5, "Approved move receipt committed");
                        service.Purchase(id, operation); Check(profile.Read().coins == 2700 - ordinal * 900 && profile.Read().lives == 5, "Duplicate receipt does not double spend or lose life");
                        board.ApplyContinue(operation, receipt.movesAfter); var after = board.Checkpoint();
                        Check(before.random == after.random && before.nextId == after.nextId && before.quietMoves == after.quietMoves && before.growthUsed == after.growthUsed && before.board.turn == after.board.turn, "Continue preserves RNG/private counters/turn");
                        Check(JsonUtility.ToJson(new BoardSnapshot { pieces = before.board.pieces, goals = before.board.goals }) == JsonUtility.ToJson(new BoardSnapshot { pieces = after.board.pieces, goals = after.board.goals }), "Continue preserves pieces/goals");
                        Check(JsonUtility.ToJson(after) == receipt.afterCheckpoint, "Live and durable checkpoint agree"); service.Acknowledge(id, operation); report.continuedPurchases++;
                        if(ordinal == 1) { profile.LeaveContinueCheckpoint(id); Exhaust(board); }
                    }
                });
                Case("Approved full-life refill remains exactly once", () => {
                    Check(LifeRules.RefillCoins == 900, "Owner-approved full-life cost"); var initial = PlayerProfile.New(new[] { 5, 5, 3, 2 }); initial.coins = 900; initial.lives = 0; initial.livesRefillDueUnix = 2800;
                    var profile = new ProfileService(new MemoryProfileRepository(initial)); string operation = Guid.NewGuid().ToString("N"); var receipt = profile.RefillLives(operation, 1000); profile.RefillLives(operation, 1000);
                    Check(receipt.coins == 900 && profile.Read().coins == 0 && profile.Read().lives == profile.Read().maxLives && profile.Read().lifeRefills.Count == 1 && profile.Read().livesRefillDueUnix == 0, "Exactly900 restores full lives once and clears deadline");
                    Check(profile.Read().starting.SequenceEqual(new[] { 5, 5, 3, 2 }) && profile.Read().stars == 0, "Refill does not alter progression or power inventory");
                });
                Case("Insufficient life refill cannot debit", () => {
                    var initial = PlayerProfile.New(new[] { 5, 5, 3, 2 }); initial.coins = 899; initial.lives = 0; initial.livesRefillDueUnix = 2800;
                    var profile = new ProfileService(new MemoryProfileRepository(initial)); string before = JsonUtility.ToJson(profile.Read());
                    Throws<InvalidOperationException>(() => profile.RefillLives(Guid.NewGuid().ToString("N"), 1000), "899 cannot purchase a900 refill"); Check(JsonUtility.ToJson(profile.Read()) == before, "Rejected refill is atomic");
                });
                CoordinatorCases();
                DiskJournalCases();
                ClientCases();
            } catch(Exception error) { report.error = error.ToString(); report.errors.Add("Unexpected suite failure: " + error); }
            finally {
                Environment.SetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable, configVariable); Environment.SetEnvironmentVariable(RuStoreReleasePreflight.ChannelVariable, channelVariable);
                report.environmentRestored = Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable) == configVariable && Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ChannelVariable) == channelVariable;
                report.preferencesUnchanged = PlayerPrefs.HasKey(GameLocale.PreferenceKey) == hadLanguage && PlayerPrefs.GetInt(GameLocale.PreferenceKey, -1) == language;
                report.settingsUnchanged = settings.SequenceEqual(File.ReadAllBytes(settingsPath)) && manifest.SequenceEqual(File.ReadAllBytes(manifestPath)) && (packageLock == null ? !File.Exists(lockPath) : packageLock.SequenceEqual(File.ReadAllBytes(lockPath)));
                report.projectSettingsAfter = Hash(File.ReadAllBytes(settingsPath));
                if(!report.environmentRestored || !report.preferencesUnchanged || !report.settingsUnchanged) report.errors.Add("Ordinary settings, language preference or process environment changed");
            }
            report.status = report.errors.Count == 0 ? "PASS_NATIVE_RUSTORE81_RELEASE_GUARD" : "FAIL_NATIVE_RUSTORE81_RELEASE_GUARD";
            string native = Path.Combine(Output, "Native"); Directory.CreateDirectory(native); File.WriteAllText(Path.Combine(native, "RuStore81.json"), JsonUtility.ToJson(report, true));
            if(Application.isBatchMode) EditorApplication.Exit(report.errors.Count == 0 ? 0 : 1);
        }
    }
}
#endif
