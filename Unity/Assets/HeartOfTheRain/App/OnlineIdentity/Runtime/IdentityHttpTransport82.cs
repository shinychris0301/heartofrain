using System;
using System.Collections;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.OnlineIdentity
{
    // Explicit unauthenticated challenge/device-proof transport. Success is
    // interpreted only by ManagedIdentitySession82; no automatic login or grant.
    public sealed partial class IdentityHttpTransport82 : IIdentityTransport82, IDisposable
    {
        const int Limit = 65536;
        static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
        readonly string origin;
        readonly bool expectedProduction;
        public bool ExpectedProduction=>expectedProduction;
        readonly Action<IEnumerator> dispatch;
        readonly int thread = System.Threading.Thread.CurrentThread.ManagedThreadId;
        bool disposed;
        long generation;
        Pending active;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        readonly System.Collections.Generic.List<int> verificationStatuses = new System.Collections.Generic.List<int>();
        public int VerificationRequestCount { get; private set; }
        public int[] VerificationStatuses => verificationStatuses.ToArray();
#endif
        sealed class Pending {
            public UnityWebRequest request;
            public long generation;
            public Action<string, string> complete;
            public bool done, released;
            public void Release() { if(released) return; released = true; request?.Dispose(); }
        }
        sealed class Download : DownloadHandlerScript {
            readonly byte[] bytes = new byte[Limit]; int count; public bool exceeded;
            public Download() : base(new byte[8192]) { }
            protected override void ReceiveContentLengthHeader(ulong length) { if(length > Limit) exceeded = true; }
            protected override bool ReceiveData(byte[] data, int length) { if(exceeded || data == null || length < 0 || length > Limit - count) { exceeded = true; return false; } Buffer.BlockCopy(data, 0, bytes, count, length); count += length; return true; }
            public string Text() { if(exceeded || count < 1) throw new InvalidOperationException(); return Utf8.GetString(bytes, 0, count); }
        }
        [Serializable] class Signed { public string requestId, challengeId, publicKey, signature; }
        [Serializable] sealed class Guest : Signed { public string refreshToken, recoverySecret; }
        [Serializable] sealed class Session : Signed { public string refreshToken, replacementToken; }
        [Serializable] sealed class Recover : Signed { public string playerId, recoverySecret, replacementRecoverySecret, refreshToken; }
        [Serializable] sealed class Logout : Signed { public string refreshToken; }
        [Serializable] sealed class Delete : Signed { public string playerId, refreshToken; }
        public IdentityHttpTransport82(string backendOrigin = null, Action<IEnumerator> dispatcher = null, bool allowDevelopmentLoopback = false, bool expectedProduction = false) {
            if(expectedProduction&&allowDevelopmentLoopback)throw new ArgumentException("ProductionLoopbackRejected");
            this.expectedProduction=expectedProduction;
            if(backendOrigin == null && dispatcher == null) return;
            if(!RuStoreBackendClient.IsAllowedOrigin(backendOrigin, allowDevelopmentLoopback) || dispatcher == null) throw new ArgumentException("InvalidExplicitIdentityTransport");
            origin = new Uri(backendOrigin).GetLeftPart(UriPartial.Authority); dispatch = dispatcher;
        }
        public bool Configured => !disposed && origin != null && dispatch != null;
        public bool Busy => active != null;
        static void Deliver<T>(Action<IdentityReply82<T>> done, IdentityReply82<T> result) where T : class { try { done(result); } catch(Exception) { } }
        // Identity responses are flat protocol fields, not free-form user data.
        // Require exactly one literal boolean, not a missing/string/null value.
        static void Flag(string json, string name, bool expected) {
            string key = "(?<!\\\\)\"" + Regex.Escape(name) + "\"\\s*:";
            if(Regex.Matches(json, key).Count != 1 || !Regex.IsMatch(json, key + @"\s*" + (expected ? "true" : "false") + @"(?=\s*[,}])")) throw new InvalidOperationException("InvalidIdentityResponseFlag");
        }
        void Complete(Pending pending, string json, string error) {
            if(pending.done) return; pending.done = true; if(active == pending) active = null;
            if(disposed || pending.generation != generation) { json = null; error = "IdentityTransportCancelled"; }
            pending.complete(json, error);
        }
        void Send<T>(string path, object body, Func<string, T> parse, Action<IdentityReply82<T>> done) where T : class {
            if(done == null) throw new ArgumentNullException(nameof(done));
            if(!Configured || thread != System.Threading.Thread.CurrentThread.ManagedThreadId) { Deliver(done, IdentityReply82<T>.Fail("IdentityTransportNotConfigured")); return; }
            if(active != null) { Deliver(done, IdentityReply82<T>.Fail("IdentityTransportBusy")); return; }
            string json;
            try { json = JsonUtility.ToJson(body); if(Utf8.GetByteCount(json) > Limit) throw new InvalidOperationException(); }
            catch(Exception) { Deliver(done, IdentityReply82<T>.Fail("IdentityRequestEncodingInvalid")); return; }
            var pending = new Pending { generation = generation };
            pending.complete = (text, error) => {
                if(error != null) { Deliver(done, IdentityReply82<T>.Fail(error, true)); return; }
                T value;
                try { value = parse(text); if(value == null) throw new InvalidOperationException(); }
                catch(Exception) { Deliver(done, IdentityReply82<T>.Fail("IdentityBoundResponseInvalid", true)); return; }
                if(disposed || pending.generation != generation) { Deliver(done, IdentityReply82<T>.Fail("IdentityTransportCancelled", true)); return; }
                Deliver(done, IdentityReply82<T>.Ok(value));
            };
            active = pending;
            try { dispatch(Exchange(pending, path, json)); }
            catch(Exception) { Complete(pending, null, "IdentityDispatchUnavailable"); pending.Release(); }
        }
        public const string SessionRefused = "IdentitySessionRefused";
        // These two 401s end this device's session: its key or token was revoked, usually by a
        // recovery on another device. A failed proof or lost reply stays an ordinary retry.
        public static string FailureCode(long status, string wire) {
            if(status == 0) return "IdentityNetworkUnavailable";
            if(status == 401 && wire != null && (wire.Contains("\"invalid_identity_session\"") || wire.Contains("\"refresh_reuse_detected\""))) return SessionRefused;
            return "IdentityHttp" + status;
        }
        IEnumerator Exchange(Pending pending, string path, string json) {
            try {
                Download download = null; UnityWebRequestAsyncOperation sent = null;
                try {
                    if(disposed || pending.generation != generation) throw new InvalidOperationException();
                    var request = pending.request = new UnityWebRequest(origin + path, "POST");
                    request.redirectLimit = 0; request.timeout = 15; download = new Download(); request.downloadHandler = download;
                    request.uploadHandler = new UploadHandlerRaw(Utf8.GetBytes(json)); request.SetRequestHeader("Content-Type", "application/json"); request.SetRequestHeader("Accept", "application/json");
                    sent = request.SendWebRequest();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    VerificationRequestCount++;
#endif
                } catch(Exception) { Complete(pending, null, "IdentityRequestUnavailable"); }
                if(sent == null) yield break; yield return sent; if(pending.done) yield break;
                string text = null, error = null;
                try {
                    var request = pending.request; string type = request.GetResponseHeader("Content-Type");
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    if(verificationStatuses.Count < 64) verificationStatuses.Add((int)request.responseCode);
#endif
                    if(download.exceeded) error = "IdentityResponseTooLarge";
                    else if(request.result != UnityWebRequest.Result.Success || request.responseCode != 200) { NetworkFailureLog.Report("identity", request); string wire = null; try { wire = download.Text(); } catch(Exception) { } error = FailureCode(request.responseCode, wire); }
                    else if(type == null || !type.Split(';')[0].Trim().Equals("application/json", StringComparison.OrdinalIgnoreCase)) error = "IdentityResponseTypeInvalid";
                    else text = download.Text();
                } catch(Exception) { error = "IdentityResponseUnavailable"; }
                Complete(pending, text, error);
            } finally { pending.Release(); if(!pending.done) Complete(pending, null, "IdentityRequestStopped"); }
        }
        public void Challenge(IdentityChallengeRequest82 request, Action<IdentityReply82<IdentityChallenge82>> done) {
            if(done == null) throw new ArgumentNullException(nameof(done));
            if(request == null || !IdentityProtocol82.Id(request.requestId) || !IdentityProtocol82.PublicKey(request.publicKey) || !IdentityProtocol82.Digest(request.payloadDigest)) { Deliver(done, IdentityReply82<IdentityChallenge82>.Fail("InvalidIdentityChallengeIntent")); return; }
            Send("/v1/identity/challenges", request, JsonUtility.FromJson<IdentityChallenge82>, done);
        }
        IdentitySessionResponse82 ParseSessionResponse122(string json){
            Flag(json,"productionEnabled",expectedProduction);Flag(json,"normalUnityProfileIntegrated",false);
            return JsonUtility.FromJson<IdentitySessionResponse82>(json);
        }
        public void Submit(IdentityIntent82 intent, string challengeId, string signature, Action<IdentityReply82<IdentitySessionResponse82>> done) {
            if(done == null) throw new ArgumentNullException(nameof(done));
            if(intent == null || !intent.Valid || !IdentityProtocol82.Id(challengeId) || string.IsNullOrEmpty(signature) || signature.Length < 80 || signature.Length > 112) { Deliver(done, IdentityReply82<IdentitySessionResponse82>.Fail("InvalidSignedIdentityIntent")); return; }
            Signed body; string path;
            switch(intent.purpose) {
                case "guest": body = new Guest { refreshToken = intent.refreshToken, recoverySecret = intent.recoverySecret }; path = "/v1/identity/guest"; break;
                case "session": body = new Session { refreshToken = intent.refreshToken, replacementToken = intent.replacementToken }; path = "/v1/identity/session"; break;
                case "recover": body = new Recover { playerId = intent.playerId, recoverySecret = intent.recoverySecret, replacementRecoverySecret = intent.replacementRecoverySecret, refreshToken = intent.refreshToken }; path = "/v1/identity/recover"; break;
                case "logout": body = new Logout { refreshToken = intent.refreshToken }; path = "/v1/identity/logout"; break;
                case "delete": body = new Delete { playerId = intent.playerId, refreshToken = intent.refreshToken }; path = "/v1/account/deletion"; break;
                default: Deliver(done, IdentityReply82<IdentitySessionResponse82>.Fail("UnsupportedIdentityPurpose")); return;
            }
            body.requestId = intent.requestId; body.challengeId = challengeId; body.publicKey = intent.publicKey; body.signature = signature;
            Send(path, body, json => {
                if(intent.purpose == "guest" || intent.purpose == "session" || intent.purpose == "recover") return ParseSessionResponse122(json);
                if(intent.purpose == "delete") { Flag(json, "sessionsRevoked", true); Flag(json, "normalUnityProfileIntegrated", false); Flag(json, "localProfileMutated", false); Flag(json, "physicalPurgeComplete", false); Flag(json, "retentionPolicyConfigured", false); }
                return JsonUtility.FromJson<IdentitySessionResponse82>(json);
            }, done);
        }
        public void Cancel() {
            generation++; var pending = active; if(pending == null) return;
            if(thread != System.Threading.Thread.CurrentThread.ManagedThreadId) return;
            try { pending.request?.Abort(); } catch(Exception) { } Complete(pending, null, "IdentityTransportCancelled"); pending.Release();
        }
        public void Dispose() { if(disposed) return; Cancel(); disposed = true; }
    }
}
