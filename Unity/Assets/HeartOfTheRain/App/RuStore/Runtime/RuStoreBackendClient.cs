using System;
using System.Collections;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.App.RuStore
{
    [Serializable] public sealed class RuStoreCatalogProduct86 {
        public string id,storeProductId,currency;public int coins,amountMinor,quantity;
        public RewardGrant grant;public CommercePolicy100 policy;
    }
    [Serializable] public sealed class RuStoreServerCatalog86 {
        [NonSerialized] public string verificationMode;public CommerceVerificationMode125 Verification=>CommerceVerification125.Value(verificationMode);
        public string version,balanceScope,reason;public long appId;
        public bool enabled,sandbox,productionEnabled,serverWalletProjection,normalUnityProfileIntegrated;
        public RuStoreCatalogProduct86[] products;
    }
    [Serializable] public sealed class RuStoreServerAttempt {
        public string attemptId, state, configHash;
        public int level, moves, continues;
        public long seed, createdAt, updatedAt;
        public int[] starting;
        public RuStoreServerReward reward;
    }
    [Serializable] public sealed class RuStoreServerReward { public int coins, stars; }
    [Serializable] public sealed class RuStoreServerWallet {
        public string playerId, balanceScope;
        public bool initialized, refundReviewRequired, productionEnabled, normalUnityProfileIntegrated, localProfileMutated;
        public long revision, nextLifeAt, serverUtc;
        public int coins, stars, lives, maxLives, completed, currentLevel;
        public int[] starting, tools;
        public RuStoreServerAttempt activeAttempt;
    }
    [Serializable] public sealed class RuStoreWalletMutation {
        public string receiptId, operation;
        public RuStoreServerWallet wallet;
        public RuStoreServerAttempt attempt;
    }
    [Serializable] public sealed class RuStoreServerSdkOrder {
        public string orderId, productId, appUserId, developerPayload;
        public int quantity;
        public bool sandbox;
        public PayRequest Request() => new PayRequest(orderId, productId, appUserId, developerPayload, quantity, sandbox);
    }
    [Serializable] public sealed class RuStoreServerCredit {
        [NonSerialized] public string verificationMode;public CommerceVerificationMode125 Verification=>CommerceVerification125.Value(verificationMode);
        public string receiptId, balanceScope;
        public int coins;
        public long createdAt;public RewardGrant grant;
    }
    [Serializable] public sealed class RuStoreServerOrder {
        [NonSerialized] public string verificationMode;public CommerceVerificationMode125 Verification=>CommerceVerification125.Value(verificationMode);
        public string orderId, playerId, state, catalogVersion, productId, currency, invoiceId, purchaseId, deliveryAcknowledgement, balanceScope;
        public int coins, amountMinor;
        public bool productionEnabled, availableToSpend, availableInServerWallet, normalUnityProfileIntegrated, localProfileMutated;
        public RuStoreServerSdkOrder sdk;
        public RuStoreServerCredit credit;
        public RewardGrant grant;public CommercePolicy100 policy;public bool reservationReleased;public string creationCommandId;
        public PayRequest Request() => sdk == null ? null : sdk.Request();
    }

    // Explicit managed transport only: no automatic instance, credential
    // persistence, local-profile mutation, SDK bootstrap or payment grant.
    // The owner must dispose/revoke this client when its account/lifetime ends.
    public static class NetworkFailureLog {
        public static void Report(string client,UnityEngine.Networking.UnityWebRequest request){
            if(request==null)return;UnityEngine.Debug.Log("HOTR network "+client+" http="+request.responseCode+" result="+request.result+" error="+request.error);
        }
    }
    public sealed class RuStoreBackendClient : IPayAuthority, IPayTerminalAuthority, IDisposable
    {
        const int Limit = 65536;
        const double WalletFreshSeconds = 30;
        static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
        readonly string origin, player;
        readonly bool expectedProduction;readonly long expectedAppId;readonly string expectedVerificationMode;
        readonly Action<IEnumerator> dispatch;
        readonly int ownerThread;
        string token;
        bool configured, walletVerified;
        volatile bool disposed;
        long generation, walletVerifiedTicks;
        Operation active;
        readonly System.Collections.Generic.Dictionary<string, Binding> orders = new System.Collections.Generic.Dictionary<string, Binding>();
        sealed class Binding { public PayRequest request; public string productId, version, currency,verificationMode; public int coins, amount; public RewardGrant grant;public string creationCommandId; }
        sealed class Raw { public string text, error; public bool unknown; }
        sealed class Operation {
            public long generation;
            public UnityWebRequest request;
            public Action<Raw> done;
            public bool finished, released;
            public void Release() { if(released) return; released = true; request?.Dispose(); }
        }
        sealed class BoundedDownload : DownloadHandlerScript {
            readonly byte[] buffer = new byte[Limit];
            int count;
            public bool exceeded;
            public BoundedDownload() : base(new byte[8192]) { }
            protected override void ReceiveContentLengthHeader(ulong contentLength) { if(contentLength > Limit) exceeded = true; }
            protected override bool ReceiveData(byte[] bytes, int length) {
                if(exceeded || bytes == null || length < 0 || length > buffer.Length - count) { exceeded = true; return false; }
                Buffer.BlockCopy(bytes, 0, buffer, count, length); count += length; return true;
            }
            public string Text() { if(exceeded || count < 1) throw new InvalidOperationException(); return Utf8.GetString(buffer, 0, count); }
        }
        [Serializable] sealed class WalletCommand { public string commandId; public long expectedRevision; }
        [Serializable] sealed class ReserveCommand { public string commandId; public long expectedRevision; public int level; public int[] starting; }
        [Serializable] sealed class ToolCommand { public string commandId; public long expectedRevision; public int tool; }
        [Serializable] sealed class CreateCommand { public string commandId, productId; }
        [Serializable] sealed class ReconcileCommand { public string invoiceId; }
        // JsonUtility does not preserve null for inline serializable classes.
        // Keep the transport's explicit nulls and required scalar types before
        // using it for DTO conversion. No unknown type/object becomes "absent".
        sealed class JsonFields {
            readonly string text; int at;
            JsonFields(string text) { this.text = text ?? throw new InvalidOperationException(); if(text.Length > Limit) throw new InvalidOperationException(); }
            void Space() { while(at < text.Length && (text[at] == ' ' || text[at] == '\t' || text[at] == '\r' || text[at] == '\n')) at++; }
            bool Take(char c) { Space(); if(at >= text.Length || text[at] != c) return false; at++; return true; }
            void Need(char c) { if(!Take(c)) throw new InvalidOperationException(); }
            string String() {
                Space(); int start = at; Need('"');
                while(at < text.Length) {
                    char c = text[at++]; if(c == '"') return text.Substring(start, at - start);
                    if(c < 32) throw new InvalidOperationException();
                    if(c != '\\') continue;
                    if(at >= text.Length) throw new InvalidOperationException(); char escaped = text[at++];
                    if(escaped == 'u') { for(int n = 0; n < 4; n++) if(at >= text.Length || !Uri.IsHexDigit(text[at++])) throw new InvalidOperationException(); }
                    else if("\"\\/bfnrt".IndexOf(escaped) < 0) throw new InvalidOperationException();
                }
                throw new InvalidOperationException();
            }
            void Value(int depth) {
                if(depth > 16) throw new InvalidOperationException(); Space(); if(at >= text.Length) throw new InvalidOperationException();
                if(text[at] == '"') { String(); return; }
                if(Take('{')) { if(Take('}')) return; do { String(); Need(':'); Value(depth + 1); } while(Take(',')); Need('}'); return; }
                if(Take('[')) { if(Take(']')) return; do { Value(depth + 1); } while(Take(',')); Need(']'); return; }
                int start = at;
                while(at < text.Length && text[at] != ',' && text[at] != '}' && text[at] != ']' && !char.IsWhiteSpace(text[at])) at++;
                string value = text.Substring(start, at - start);
                if(value != "true" && value != "false" && value != "null" && !Regex.IsMatch(value, @"\A-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?\z")) throw new InvalidOperationException();
            }
            public static System.Collections.Generic.Dictionary<string, string> Read(string json) {
                var reader = new JsonFields(json); var result = new System.Collections.Generic.Dictionary<string, string>(); reader.Need('{');
                if(!reader.Take('}')) {
                    do {
                        string quoted = reader.String();
                        // Server contract keys are plain ASCII identifiers;
                        // reject ambiguous escaped/duplicate property names.
                        if(quoted.IndexOf('\\') >= 0) throw new InvalidOperationException();
                        string name = quoted.Substring(1, quoted.Length - 2); reader.Need(':'); reader.Space(); int start = reader.at; reader.Value(0);
                        result.Add(name, reader.text.Substring(start, reader.at - start));
                    } while(reader.Take(',')); reader.Need('}');
                }
                reader.Space(); if(reader.at != reader.text.Length) throw new InvalidOperationException(); return result;
            }
        }
        static string Required(System.Collections.Generic.Dictionary<string, string> fields, string name) { string value; if(!fields.TryGetValue(name, out value)) throw new InvalidOperationException(); return value; }
        static bool Boolean(System.Collections.Generic.Dictionary<string, string> fields, string name) { string value = Required(fields, name); if(value != "true" && value != "false") throw new InvalidOperationException(); return value == "true"; }
        static void Integer(System.Collections.Generic.Dictionary<string, string> fields, string name) { long value; if(!long.TryParse(Required(fields, name), System.Globalization.NumberStyles.AllowLeadingSign, System.Globalization.CultureInfo.InvariantCulture, out value)) throw new InvalidOperationException(); }

        // Supplying a dispatcher is explicit ownership, not an automatic game
        // service. Editor verification may drive the same IEnumerator directly.
        public RuStoreBackendClient(string backendOrigin = null, string bearerToken = null, string expectedPlayer = null,
            bool stagingOptIn = false, bool allowDevelopmentLoopback = false, Action<IEnumerator> dispatcher = null, bool expectedProduction = false, long expectedAppId = 0, string expectedVerificationMode = CommerceVerification125.ProviderApi)
        {
            ownerThread = Thread.CurrentThread.ManagedThreadId;
            if(expectedAppId<0||expectedProduction&&(allowDevelopmentLoopback||expectedAppId<=0))throw new ArgumentException("InvalidProductionBinding");
            this.expectedProduction=expectedProduction;this.expectedAppId=expectedAppId;this.expectedVerificationMode=CommerceVerification125.Legacy(expectedVerificationMode);
            if(this.expectedVerificationMode==CommerceVerification125.SdkClientReported&&expectedAppId<=0)throw new ArgumentException("InvalidSdkAppBinding");
            if(!stagingOptIn) return;
            if(!IsAllowedOrigin(backendOrigin, allowDevelopmentLoopback) || !PayRequest.Hex(expectedPlayer) ||
               bearerToken == null || !Regex.IsMatch(bearerToken, @"\A[A-Za-z0-9_-]{43}\z")) throw new ArgumentException("Invalid explicit staging configuration");
            var uri = new Uri(backendOrigin);
            origin = uri.GetLeftPart(UriPartial.Authority); player = expectedPlayer; token = bearerToken; dispatch = dispatcher;
            configured = dispatch != null;
        }
        public RuStoreBackendClient(MonoBehaviour runner, string backendOrigin, string bearerToken, string expectedPlayer,
            bool stagingOptIn = false, bool allowDevelopmentLoopback = false)
            : this(backendOrigin, bearerToken, expectedPlayer, stagingOptIn, allowDevelopmentLoopback,
                runner ? (Action<IEnumerator>)(routine => { if(!runner || !runner.isActiveAndEnabled) throw new InvalidOperationException(); runner.StartCoroutine(routine); }) : null) { }

        public static bool IsAllowedOrigin(string value, bool allowDevelopmentLoopback = false)
        {
            Uri uri;
            if(string.IsNullOrWhiteSpace(value) || value.Any(c => char.IsControl(c) || char.IsWhiteSpace(c)) ||
               !Uri.TryCreate(value, UriKind.Absolute, out uri) || uri.UserInfo != "" || uri.Query != "" || uri.Fragment != "" || uri.AbsolutePath != "/") return false;
            if(uri.IsLoopback) {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                return allowDevelopmentLoopback && (uri.Scheme == "http" || uri.Scheme == "https") &&
                    new[] { "localhost", "127.0.0.1", "[::1]" }.Contains(uri.Host);
#else
                return false;
#endif
            }
            if(uri.Scheme != "https" || uri.HostNameType != UriHostNameType.Dns || !uri.Host.Contains(".")) return false;
            string host = uri.DnsSafeHost.ToLowerInvariant();
            return !new[] { "example.com", "example.org", "example.net", "example", "invalid", "test", "local", "localhost" }
                .Any(h => host == h || host.EndsWith("." + h, StringComparison.Ordinal));
        }
        public bool Configured => configured && !disposed;
        public bool ExpectedProduction=>expectedProduction;
        public CommerceVerificationMode125 Verification=>CommerceVerification125.Value(expectedVerificationMode);
        public bool Busy => active != null;
        public bool WalletReady => Configured && walletVerified && (Stopwatch.GetTimestamp() - walletVerifiedTicks) / (double)Stopwatch.Frequency <= WalletFreshSeconds;
        public void Revoke() => Dispose();
        public void Dispose() {
            if(disposed) return;
            disposed = true; configured = walletVerified = false; token = null; Interlocked.Increment(ref generation);
            // Cross-thread revocation immediately clears authority and fences
            // results. Unity abort/dispose and the callback remain on the owner
            // thread when its coroutine next resumes. Normal owners dispose on
            // that thread so an in-flight request is aborted immediately.
            if(Thread.CurrentThread.ManagedThreadId != ownerThread) return;
            var pending = active;
            if(pending != null) { try { pending.request?.Abort(); } catch(Exception) { } Complete(pending, new Raw { error = "StagingClientRevoked", unknown = true }); pending.Release(); }
            orders.Clear();
        }
        static void Deliver<T>(Action<PayReply<T>> done, PayReply<T> reply) where T : class { try { done(reply); } catch(Exception) { /* UI cannot replay a transaction. */ } }
        void Complete(Operation operation, Raw raw) {
            if(operation.finished) return; operation.finished = true;
            if(active == operation) active = null;
            if(disposed || operation.generation != generation) raw = new Raw { error = "StagingClientRevoked", unknown = true };
            operation.done(raw);
        }
        void Send<T>(string method, string path, object body, Func<string, T> parse, Action<PayReply<T>> done) where T : class
        {
            if(done == null) throw new ArgumentNullException(nameof(done));
            if(Thread.CurrentThread.ManagedThreadId != ownerThread) { Deliver(done, PayReply<T>.Fail("StagingClientOwnerThreadRequired")); return; }
            if(!Configured) { Deliver(done, PayReply<T>.Fail("StagingClientNotConfigured")); return; }
            if(active != null) { Deliver(done, PayReply<T>.Fail("StagingClientBusy")); return; }
            string json = body == null ? null : JsonUtility.ToJson(body);
            if(json != null && Utf8.GetByteCount(json) > Limit) { Deliver(done, PayReply<T>.Fail("StagingRequestTooLarge")); return; }
            var operation = new Operation { generation = generation };
            operation.done = raw => {
                if(raw.error != null) { walletVerified = false; Deliver(done, PayReply<T>.Fail(raw.error, raw.unknown)); return; }
                T parsed;
                try { parsed = parse(raw.text); if(parsed == null) throw new InvalidOperationException(); }
                catch(Exception) { walletVerified = false; Deliver(done, PayReply<T>.Fail("StagingInvalidBoundResponse", method != "GET")); return; }
                if(disposed || operation.generation != generation) { Deliver(done, PayReply<T>.Fail("StagingClientRevoked", true)); return; }
                Deliver(done, PayReply<T>.Ok(parsed));
            };
            active = operation;
            try { dispatch(Exchange(operation, method, path, json)); }
            catch(Exception) { Complete(operation, new Raw { error = "StagingDispatchUnavailable", unknown = method != "GET" }); operation.Release(); }
        }
        IEnumerator Exchange(Operation operation, string method, string path, string json)
        {
            try {
                UnityWebRequestAsyncOperation sent = null; BoundedDownload download = null;
                try {
                    if(disposed || operation.generation != generation) throw new InvalidOperationException();
                    var request = operation.request = new UnityWebRequest(origin + path, method);
                    download = new BoundedDownload(); request.downloadHandler = download; request.timeout = 10; request.redirectLimit = 0;
                    request.SetRequestHeader("Authorization", "Bearer " + token); request.SetRequestHeader("Accept", "application/json");
                    if(json != null) { request.uploadHandler = new UploadHandlerRaw(Utf8.GetBytes(json)); request.SetRequestHeader("Content-Type", "application/json"); }
                    sent = request.SendWebRequest();
                } catch(Exception) { Complete(operation, new Raw { error = "StagingRequestUnavailable", unknown = method != "GET" }); }
                if(sent == null) yield break;
                yield return sent;
                if(operation.finished) yield break;
                Raw result;
                try {
                    var request = operation.request;
                    string contentType = request.GetResponseHeader("Content-Type");
                    if(download.exceeded) result = new Raw { error = "StagingResponseTooLarge", unknown = method != "GET" };
                    else if(request.result != UnityWebRequest.Result.Success || request.responseCode != 200) {
                        NetworkFailureLog.Report("wallet", request);
                        result = new Raw { error = request.responseCode == 0 ? "StagingNetworkUnavailable" : "StagingHttp" + request.responseCode, unknown = method != "GET" };
                    }
                    else if(contentType == null || !contentType.Split(';')[0].Trim().Equals("application/json", StringComparison.OrdinalIgnoreCase))
                        result = new Raw { error = "StagingInvalidContentType", unknown = method != "GET" };
                    else result = new Raw { text = download.Text() };
                } catch(Exception) { result = new Raw { error = "StagingResponseUnavailable", unknown = method != "GET" }; }
                Complete(operation, result);
            } finally {
                operation.Release();
                if(!operation.finished) Complete(operation, new Raw { error = "StagingRequestStopped", unknown = method != "GET" });
            }
        }
        static bool Code(string value) => value != null && Regex.IsMatch(value, @"\A[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\z");
        static bool Four(int[] values) => values != null && values.Length == 4 && values.All(v => v >= 0);
        static bool Attempt(RuStoreServerAttempt attempt) => attempt != null && PayRequest.Hex(attempt.attemptId) && attempt.level >= 1 && attempt.level <= 50 &&
            attempt.configHash != null && Regex.IsMatch(attempt.configHash, @"\A[0-9a-f]{64}\z") && attempt.seed > 0 && attempt.seed <= uint.MaxValue &&
            attempt.moves > 0 && attempt.continues >= 0 && Four(attempt.starting) && attempt.starting.All(v => v <= 1) &&
            attempt.reward != null && attempt.reward.coins == 50 && attempt.reward.stars == 1 &&
            new[] { "Reserved", "Started", "AwaitingContinuation", "Won", "Lost", "Released", "Cancelled" }.Contains(attempt.state);
        RuStoreServerWallet ReadWallet(string json) {
            var fields = JsonFields.Read(json);
            var value = JsonUtility.FromJson<RuStoreServerWallet>(json);
            value.initialized = Boolean(fields, "initialized"); value.refundReviewRequired = Boolean(fields, "refundReviewRequired"); value.productionEnabled = Boolean(fields, "productionEnabled");
            value.normalUnityProfileIntegrated = Boolean(fields, "normalUnityProfileIntegrated"); value.localProfileMutated = Boolean(fields, "localProfileMutated");
            foreach(string field in new[] { "revision", "coins", "stars", "lives", "maxLives", "completed", "currentLevel", "serverUtc", "nextLifeAt" }) Integer(fields, field);
            string attempt = Required(fields, "activeAttempt");
            value.activeAttempt = attempt == "null" ? null : ReadAttempt(attempt);
            ValidateWallet(value); return value;
        }
        RuStoreServerWallet Wallet(string json) {
            var value = ReadWallet(json);
            walletVerified = value.initialized && !value.refundReviewRequired; walletVerifiedTicks = Stopwatch.GetTimestamp(); return value;
        }
        static RuStoreServerAttempt ReadAttempt(string json) {
            var fields = JsonFields.Read(json);
            foreach(string name in new[] { "level", "moves", "continues", "seed", "createdAt", "updatedAt" }) Integer(fields, name);
            var value = JsonUtility.FromJson<RuStoreServerAttempt>(json); if(!Attempt(value)) throw new InvalidOperationException(); return value;
        }
        void ValidateWallet(RuStoreServerWallet value) {
            if(value == null || value.playerId != player || value.balanceScope != "server_wallet" || value.productionEnabled != expectedProduction ||
               value.normalUnityProfileIntegrated || value.localProfileMutated || value.revision < 0 || value.coins < 0 || value.stars < 0 ||
               value.maxLives != 5 || value.lives < 0 || value.lives > 5 || value.completed < 0 || value.completed > 50 ||
               value.currentLevel != Math.Min(50, value.completed + 1) || value.serverUtc <= 0 || value.nextLifeAt < 0 || !Four(value.starting) || !Four(value.tools) ||
               value.activeAttempt != null && (!Attempt(value.activeAttempt) || !new[] { "Reserved", "Started", "AwaitingContinuation" }.Contains(value.activeAttempt.state))) throw new InvalidOperationException();
        }
        RuStoreServerOrder Order(string json, string expectedOrder = null, string expectedProduct = null, PayRequest expectedRequest = null) {
            var fields = JsonFields.Read(json); var value = JsonUtility.FromJson<RuStoreServerOrder>(json);
            var terms=SocialJson82.Read(json);value.verificationMode=CommerceVerification125.Read(terms);if(value.verificationMode!=expectedVerificationMode)throw new InvalidOperationException();value.grant=CommerceTerms100.Grant(terms,value.coins,value.productId);value.policy=CommerceTerms100.Policy(terms,value.productId);
            if(terms.ContainsKey("reservationReleased"))value.reservationReleased=SocialJson82.Flag(terms,"reservationReleased");
            value.creationCommandId=null; // A legacy omitted field and explicit JSON null have the same unknown creator.
            if(terms.TryGetValue("creationCommandId",out var creator)){if(creator!=null&&(!(creator is string)||!PayRequest.Hex((string)creator)))throw new InvalidOperationException();value.creationCommandId=creator as string;}
            value.productionEnabled = Boolean(fields, "productionEnabled"); value.normalUnityProfileIntegrated = Boolean(fields, "normalUnityProfileIntegrated"); value.localProfileMutated = Boolean(fields, "localProfileMutated");
            value.availableToSpend = Boolean(fields, "availableToSpend"); value.availableInServerWallet = Boolean(fields, "availableInServerWallet");
            var sdk = JsonFields.Read(Required(fields, "sdk")); Boolean(sdk, "sandbox"); Integer(sdk, "quantity"); Integer(fields, "coins"); Integer(fields, "amountMinor");
            string credit = Required(fields, "credit"); value.credit = credit == "null" ? null : JsonUtility.FromJson<RuStoreServerCredit>(credit);
            if(value.credit!=null){var creditFields=SocialJson82.Read(credit);value.credit.verificationMode=CommerceVerification125.Read(creditFields);if(value.credit.verificationMode!=value.verificationMode)throw new InvalidOperationException();value.credit.coins=(int)SocialJson82.Number(creditFields,"coins",1,int.MaxValue);value.credit.grant=CommerceTerms100.Grant(creditFields,value.credit.coins,value.productId);
                if(value.credit.coins!=value.coins||!CommerceTerms100.Same(value.credit.grant,value.grant)||value.credit.balanceScope!="commerce_receipt_audit"||string.IsNullOrEmpty(value.credit.receiptId)||value.credit.createdAt<=0)throw new InvalidOperationException();}

            // JsonUtility can turn an explicit null string into an empty string.
            // Only an explicit JSON null is absence of delivery acknowledgement.
            string acknowledgement = Required(fields, "deliveryAcknowledgement");
            if(acknowledgement != "null" && (acknowledgement.Length < 2 || acknowledgement[0] != '"' || acknowledgement[acknowledgement.Length - 1] != '"')) throw new InvalidOperationException();
            value.deliveryAcknowledgement = acknowledgement == "null" ? null : value.deliveryAcknowledgement;
            var request = value.Request();
            if(!PayRequest.Hex(value.orderId) || value.playerId != player || value.balanceScope != "server_wallet" || value.productionEnabled != expectedProduction || value.normalUnityProfileIntegrated || value.localProfileMutated ||
               request == null || !request.Valid || request.sandbox == expectedProduction || request.orderId != value.orderId || request.appUserId != player || !Code(request.productId) || !Code(value.productId) ||
               value.coins < 1 || value.amountMinor < 1 || value.currency != "RUB" || string.IsNullOrEmpty(value.catalogVersion) ||
               !new[] { "Created", "Executed", "Confirmed", "Cancelled", "Rejected", "Expired", "Held", "RefundReview" }.Contains(value.state) ||
               expectedOrder != null && value.orderId != expectedOrder || expectedProduct != null && value.productId != expectedProduct || expectedRequest != null && !request.SameOrder(expectedRequest)) throw new InvalidOperationException();
            Binding binding;
            if(orders.TryGetValue(value.orderId, out binding)) {
                if(binding.verificationMode!=value.verificationMode||!binding.request.SameOrder(request) || binding.productId != value.productId || binding.version != value.catalogVersion || binding.currency != value.currency || binding.coins != value.coins || binding.amount != value.amountMinor || !CommerceTerms100.Same(binding.grant,value.grant) || binding.creationCommandId!=value.creationCommandId) throw new InvalidOperationException();
            } else orders.Add(value.orderId, new Binding { verificationMode=value.verificationMode,request = request, productId = value.productId, version = value.catalogVersion, currency = value.currency, coins = value.coins, amount = value.amountMinor, grant=value.grant.Copy(),creationCommandId=value.creationCommandId });
            if(value.state == "RefundReview") walletVerified = false;
            return value;
        }
        bool ValidCommand(string command, long revision) => PayRequest.Hex(command) && revision >= 0;
        bool Require<T>(bool condition, Action<PayReply<T>> done) where T : class { if(done == null) throw new ArgumentNullException(nameof(done)); if(condition) return true; Deliver(done, PayReply<T>.Fail("InvalidExplicitStagingCommand")); return false; }
        public void GetWallet(Action<PayReply<RuStoreServerWallet>> done) { walletVerified = false; Send("GET", "/v1/wallet", null, Wallet, done); }
        public void GetCatalog(Action<PayReply<RuStoreServerCatalog86>> done)=>Send("GET","/v1/commerce/catalog",null,ParseCatalog,done);
        RuStoreServerCatalog86 ParseCatalog(string json){
            var root=SocialJson82.Read(json);
            var value=new RuStoreServerCatalog86{verificationMode=CommerceVerification125.Read(root),version=SocialJson82.Text(root,"version",256),balanceScope=SocialJson82.Text(root,"balanceScope",64),reason=SocialJson82.Text(root,"reason",128),
                enabled=SocialJson82.Flag(root,"enabled"),sandbox=SocialJson82.Flag(root,"sandbox"),productionEnabled=SocialJson82.Flag(root,"productionEnabled"),
                serverWalletProjection=SocialJson82.Flag(root,"serverWalletProjection"),normalUnityProfileIntegrated=SocialJson82.Flag(root,"normalUnityProfileIntegrated")};
            object app=SocialJson82.Field(root,"appId");value.appId=app==null?0:SocialJson82.Number(root,"appId",1);
            if(value.verificationMode!=expectedVerificationMode||value.productionEnabled!=expectedProduction||value.normalUnityProfileIntegrated||!value.serverWalletProjection||value.balanceScope!="server_wallet"||value.version.Any(char.IsControl)||SocialJson82.Flag(root,"fullGameplayWallet")!=expectedProduction||value.sandbox==expectedProduction||expectedAppId>0&&value.appId!=expectedAppId)throw new InvalidOperationException();
            value.products=SocialJson82.Array(root,"products",100).Select(item=>{
                var p=SocialJson82.Object(item);var product=new RuStoreCatalogProduct86{id=SocialJson82.Text(p,"id",128),storeProductId=SocialJson82.Text(p,"storeProductId",128),currency=SocialJson82.Text(p,"currency",3),coins=(int)SocialJson82.Number(p,"coins",1,int.MaxValue),amountMinor=(int)SocialJson82.Number(p,"amountMinor",1,int.MaxValue),quantity=(int)SocialJson82.Number(p,"quantity",1,1)};
                product.grant=CommerceTerms100.Grant(p,product.coins,product.id);product.policy=CommerceTerms100.Policy(p,product.id);
                if(!Code(product.id)||!Code(product.storeProductId)||product.currency!="RUB")throw new InvalidOperationException();return product;
            }).ToArray();
            if(value.products.Select(p=>p.id).Distinct(StringComparer.Ordinal).Count()!=value.products.Length||value.products.Select(p=>p.storeProductId).Distinct(StringComparer.Ordinal).Count()!=value.products.Length||
                value.enabled&&(value.appId<1||value.sandbox==expectedProduction||value.products.Length==0)||!value.enabled&&value.products.Length!=0)throw new InvalidOperationException();
            return value;
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public RuStoreServerCatalog86 VerificationParseCatalog(string json)=>ParseCatalog(json);
#endif
        RuStorePendingOrders100 ParsePendingOrders122(string json,long after){
                var row=SocialJson82.Read(json);var result=new RuStorePendingOrders100{playerId=SocialJson82.Text(row,"playerId",32),nextCursor=SocialJson82.Number(row,"nextCursor",after),hasMore=SocialJson82.Flag(row,"hasMore"),productionEnabled=SocialJson82.Flag(row,"productionEnabled")};
                if(result.playerId!=player||result.productionEnabled!=expectedProduction)throw new InvalidOperationException();
                result.orders=SocialJson82.Array(row,"orders",100).Select(value=>Order(SocialJson82.Write(value))).ToArray();
                if(result.orders.Select(value=>value.orderId).Distinct(StringComparer.Ordinal).Count()!=result.orders.Length||result.orders.Length>0&&result.nextCursor<=after||result.hasMore&&result.orders.Length==0)throw new InvalidOperationException();return result;
        }
        public void GetPendingOrders100(long after,Action<PayReply<RuStorePendingOrders100>> done){
            if(!Require(Configured&&after>=0,done))return;
            Send("GET","/v1/commerce/orders/pending?after="+after.ToString(System.Globalization.CultureInfo.InvariantCulture)+"&limit=100",null,json=>ParsePendingOrders122(json,after),done);
        }
        public void GetAttempt(string attemptId, Action<PayReply<RuStoreServerAttempt>> done) {
            if(!Require(PayRequest.Hex(attemptId), done)) return;
            Send("GET", "/v1/attempts/" + attemptId, null, json => { var value = ReadAttempt(json); if(value.attemptId != attemptId) throw new InvalidOperationException(); return value; }, done);
        }
        RuStoreWalletMutation Mutation(string json, string operation, string attemptId) {
            var fields = JsonFields.Read(json); var value = JsonUtility.FromJson<RuStoreWalletMutation>(json);
            value.wallet = ReadWallet(Required(fields, "wallet")); string attempt = Required(fields, "attempt"); value.attempt = attempt == "null" ? null : ReadAttempt(attempt);
            if(value == null || string.IsNullOrEmpty(value.receiptId) || value.operation != operation || attemptId != null && (value.attempt == null || value.attempt.attemptId != attemptId)) throw new InvalidOperationException();
            ValidateWallet(value.wallet);
            if(value.attempt != null && !Attempt(value.attempt)) throw new InvalidOperationException();
            // Idempotent mutation replays may intentionally return an older
            // receipt snapshot. They never refresh authority readiness/age.
            if(!value.wallet.initialized || value.wallet.refundReviewRequired) walletVerified = false;
            return value;
        }
        public void Reserve(string commandId, long revision, int level, int[] starting, Action<PayReply<RuStoreWalletMutation>> done) {
            if(!Require(WalletReady && ValidCommand(commandId, revision) && level >= 1 && level <= 50 && Four(starting) && starting.All(v => v <= 1), done)) return;
            Send("POST", "/v1/attempts/reserve", new ReserveCommand { commandId = commandId, expectedRevision = revision, level = level, starting = (int[])starting.Clone() }, json => Mutation(json, "attempt.reserve", null), done);
        }
        void AttemptCommand(string operation, string commandId, long revision, string attemptId, Action<PayReply<RuStoreWalletMutation>> done) {
            if(!Require((operation == "quit" || WalletReady) && ValidCommand(commandId, revision) && PayRequest.Hex(attemptId), done)) return;
            Send("POST", "/v1/attempts/" + attemptId + "/" + operation, new WalletCommand { commandId = commandId, expectedRevision = revision }, json => Mutation(json, "attempt." + operation, attemptId), done);
        }
        public void Start(string commandId, long revision, string attemptId, Action<PayReply<RuStoreWalletMutation>> done) => AttemptCommand("start", commandId, revision, attemptId, done);
        public void Quit(string commandId, long revision, string attemptId, Action<PayReply<RuStoreWalletMutation>> done) => AttemptCommand("quit", commandId, revision, attemptId, done);
        public void Continue(string commandId, long revision, string attemptId, Action<PayReply<RuStoreWalletMutation>> done) => AttemptCommand("continue", commandId, revision, attemptId, done);
        public void SpendTool(string commandId, long revision, string attemptId, int tool, Action<PayReply<RuStoreWalletMutation>> done) {
            if(!Require(WalletReady && ValidCommand(commandId, revision) && PayRequest.Hex(attemptId) && tool >= 0 && tool <= 3, done)) return;
            Send("POST", "/v1/attempts/" + attemptId + "/tools", new ToolCommand { commandId = commandId, expectedRevision = revision, tool = tool }, json => Mutation(json, "attempt.tool", attemptId), done);
        }
        public void Refill(string commandId, long revision, Action<PayReply<RuStoreWalletMutation>> done) {
            if(!Require(WalletReady && ValidCommand(commandId, revision), done)) return;
            Send("POST", "/v1/wallet/refill", new WalletCommand { commandId = commandId, expectedRevision = revision }, json => Mutation(json, "life.refill", null), done);
        }
        public void CreateOrder(string commandId, string productId, Action<PayReply<RuStoreServerOrder>> done) {
            if(!Require(WalletReady && PayRequest.Hex(commandId) && Code(productId), done)) return;
            Send("POST", "/v1/commerce/orders", new CreateCommand { commandId = commandId, productId = productId }, json => Order(json, expectedProduct: productId), done);
        }
        public void GetOrder(string orderId, Action<PayReply<RuStoreServerOrder>> done) {
            if(!Require(PayRequest.Hex(orderId), done)) return;
            Send("GET", "/v1/commerce/orders/" + orderId, null, json => Order(json, orderId), done);
        }
        string ReconcileSuffix125=>expectedVerificationMode==CommerceVerification125.SdkClientReported?"/sdk-report":"/reconcile";
        bool Report(PayRequest request,PayPurchase observed,out object body){
            body=null;try{body=expectedVerificationMode==CommerceVerification125.SdkClientReported?(object)RuStoreSdkReport125.From(request,observed):new ReconcileCommand{invoiceId=observed.locator.invoiceId};return true;}catch{return false;}
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public RuStoreServerOrder VerificationParseOrder125(string json)=>Order(json);
        public string VerificationReportJson125(PayRequest request,PayPurchase observed){object body;if(!Report(request,observed,out body))throw new ArgumentException("SdkPurchaseObservationInvalid");return JsonUtility.ToJson(body);}
        public string VerificationReportSuffix125=>ReconcileSuffix125;
#endif
        public void Reconcile(PayRequest request, PayPurchase observed, Action<PayReply<PayDeliveryReceipt>> done) {
            if(!Require(Configured && request != null && request.Valid && request.appUserId == player && request.sandbox != expectedProduction && observed != null && observed.Matches(request), done)) return;
            object report;if(!Report(request,observed,out report)){Deliver(done,PayReply<PayDeliveryReceipt>.Fail("SdkPurchaseObservationInvalid"));return;}
            Send("POST", "/v1/commerce/orders/" + request.orderId + ReconcileSuffix125, report, json => {
                var value = Order(json, request.orderId, expectedRequest: request);
                if(observed.status != "CONFIRMED" || value.state != "Confirmed" || value.invoiceId != observed.locator.invoiceId || value.purchaseId != observed.locator.purchaseId ||
                   value.credit == null || string.IsNullOrEmpty(value.credit.receiptId) || value.credit.coins != value.coins || !value.availableToSpend || !value.availableInServerWallet || !WalletReady) throw new InvalidOperationException();
                var receipt = new PayDeliveryReceipt(request.orderId, request.productId, player, value.purchaseId, value.invoiceId, value.credit.receiptId, request.sandbox, true, true);
                if(!receipt.Matches(request, observed)) throw new InvalidOperationException(); return receipt;
            }, done);
        }
        public void ResolveTerminal(PayRequest request,PayPurchase observed,Action<PayReply<PayTerminalReceipt>> done){
            string expected=PayTerminalReceipt.StateFor(observed?.status);
            if(!Require(Configured&&request!=null&&request.Valid&&request.appUserId==player&&request.sandbox!=expectedProduction&&observed!=null&&observed.Matches(request)&&expected!=null,done))return;
            object report;if(!Report(request,observed,out report)){Deliver(done,PayReply<PayTerminalReceipt>.Fail("SdkPurchaseObservationInvalid"));return;}
            Send("POST","/v1/commerce/orders/"+request.orderId+ReconcileSuffix125,report,json=>ParseTerminalOrder(json,request,observed),done);
        }
        PayTerminalReceipt ParseTerminalOrder(string json,PayRequest request,PayPurchase observed){
            string expected=PayTerminalReceipt.StateFor(observed?.status);
            if(request==null||!request.Valid||request.appUserId!=player||request.sandbox==expectedProduction||observed==null||!observed.Matches(request)||expected==null)throw new InvalidOperationException();
            var value=Order(json,request.orderId,expectedRequest:request);
            if(value.state!=expected||value.invoiceId!=observed.locator.invoiceId||value.purchaseId!=observed.locator.purchaseId||value.credit!=null||value.availableToSpend||value.availableInServerWallet||value.deliveryAcknowledgement!=null)throw new InvalidOperationException();
            var receipt=new PayTerminalReceipt(request.orderId,request.productId,player,value.purchaseId,value.invoiceId,value.state,request.sandbox,true,true);
            if(!receipt.Matches(request,observed.locator))throw new InvalidOperationException();return receipt;
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public PayTerminalReceipt VerificationParseTerminalOrder(string json,PayRequest request,PayPurchase observed)=>ParseTerminalOrder(json,request,observed);
#endif
    }
}
