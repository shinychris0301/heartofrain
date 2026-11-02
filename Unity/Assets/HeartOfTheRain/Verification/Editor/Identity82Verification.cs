#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.Verification
{
    public static class Identity82Verification
    {
        [Serializable] sealed class Report {
            public string status, utc, unity, accountIdHash;
            public int checks, cases, requests, rejectedOldAccess, walletCoins;
            public int signedTransportRequests, walletRequests;
            public List<int> signedTransportStatuses = new List<int>(), walletStatuses = new List<int>();
            public bool normalProfileIntegrated = false, androidKeystore = false;
            public string scope;
            public List<string> passed = new List<string>(), errors = new List<string>();
        }
        static Report report;
        static string Root => Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_IDENTITY82_OUTPUT") ?? "../Verification/Evidence/Launch82");
        static string Temporary => Path.GetFullPath("../.verification-cache/Launch82/Identity/" + Guid.NewGuid().ToString("N"));
        static string Id() => Guid.NewGuid().ToString("N");
        static void Check(bool valid, string label) { report.checks++; if(!valid) throw new InvalidOperationException(label); }
        static void Reject(Action action, string label) { bool threw = false; try { action(); } catch(Exception) { threw = true; } Check(threw, label); }
        static void Case(string label, Action action) { report.cases++; try { action(); report.passed.Add(label); } catch(Exception error) { report.errors.Add(label + ": " + error.GetType().Name + ": " + error.Message); } }
        static void Save(string filename, string pass) {
            report.status = report.errors.Count == 0 ? pass : "FAIL_" + pass.Substring(5);
            string folder = Path.Combine(Root, "Native"); Directory.CreateDirectory(folder);
            File.WriteAllText(Path.Combine(folder, filename), JsonUtility.ToJson(report, true), new UTF8Encoding(false));
        }
        static IdentityChallenge82 Challenge(IdentityChallengeRequest82 request, long clock) {
            var value = new IdentityChallenge82 { challengeId = Id(), purpose = request.purpose, requestId = request.requestId,
                keyFingerprint = IdentityProtocol82.Fingerprint(request.publicKey), payloadDigest = request.payloadDigest,
                nonce = IdentityProtocol82.NewSecret(), algorithm = "ES256-DER", serverUtc = clock, expiresAt = clock + 60 };
            // Independent literal field order, mirroring the published server
            // wire contract, rather than calling the client's reconstruction.
            string json = "{\"challengeId\":\"" + value.challengeId + "\",\"expiresAt\":" + value.expiresAt.ToString(CultureInfo.InvariantCulture) +
                ",\"keyFingerprint\":\"" + value.keyFingerprint + "\",\"nonce\":\"" + value.nonce + "\",\"payloadDigest\":\"" + value.payloadDigest +
                "\",\"purpose\":\"" + value.purpose + "\",\"requestId\":\"" + value.requestId + "\"}";
            value.signingBytes = Convert.ToBase64String(Encoding.ASCII.GetBytes(IdentityProtocol82.Protocol + "\n" + json)); return value;
        }
        sealed class Server {
            public string player = Id(), family = Id(), refresh, recovery;
            public long clock = 1000;
            public int applies;
            public readonly Dictionary<string, string> digests = new Dictionary<string, string>();
            public readonly Dictionary<string, IdentitySessionResponse82> results = new Dictionary<string, IdentitySessionResponse82>();
            public IdentitySessionResponse82 Apply(IdentityIntent82 intent) {
                string digest = IdentityProtocol82.PayloadDigest(intent);
                if(digests.ContainsKey(intent.requestId)) {
                    if(digests[intent.requestId] != digest) throw new InvalidOperationException();
                    var old = JsonUtility.FromJson<IdentitySessionResponse82>(JsonUtility.ToJson(results[intent.requestId])); old.replayed = true;
                    if(old.accountState == "Active") { old.accessToken = IdentityProtocol82.NewSecret(); old.expiresAt = clock + 900; } return old;
                }
                if(intent.purpose == "session" || intent.purpose == "logout" || intent.purpose == "delete") { if(intent.refreshToken != refresh) throw new InvalidOperationException(); }
                if(intent.purpose == "recover" && (intent.playerId != player || intent.recoverySecret != recovery)) throw new InvalidOperationException();
                if(intent.purpose == "guest") { if(refresh != null) throw new InvalidOperationException(); refresh = intent.refreshToken; recovery = intent.recoverySecret; }
                if(intent.purpose == "session") refresh = intent.replacementToken;
                if(intent.purpose == "recover") { family = Id(); refresh = intent.refreshToken; recovery = intent.replacementRecoverySecret; }
                var result = new IdentitySessionResponse82 { playerId = player, familyId = family, requestId = intent.requestId };
                if(intent.purpose == "logout") { result.state = "LoggedOut"; refresh = null; }
                else if(intent.purpose == "delete") { result.state = "DeletionRequested"; result.requestedAt = clock; result.sessionsRevoked = true; refresh = null; }
                else { result.accountState = "Active"; result.keyFingerprint = IdentityProtocol82.Fingerprint(intent.publicKey); result.accessToken = IdentityProtocol82.NewSecret(); result.expiresAt = clock + 900; result.refreshExpiresAt = clock + 30L * 86400; }
                applies++; digests.Add(intent.requestId, digest); results.Add(intent.requestId, result); return result;
            }
        }
        sealed class Transport : IIdentityTransport82 {
            readonly Server server; readonly EditorEphemeralIdentity82 vault;
            public int challenges, submits, signatures; public bool loseReply, hold, duplicate, badBinding;
            public IdentityIntent82 observed; public IdentityChallenge82 lastChallenge; public Action release;
            public Transport(Server server, EditorEphemeralIdentity82 vault) { this.server = server; this.vault = vault; }
            public void Challenge(IdentityChallengeRequest82 request, Action<IdentityReply82<IdentityChallenge82>> done) {
                challenges++; lastChallenge = Identity82Verification.Challenge(request, server.clock);
                var value = lastChallenge; if(badBinding) value.requestId = Id();
                Action invoke = () => { done(IdentityReply82<IdentityChallenge82>.Ok(value)); if(duplicate) done(IdentityReply82<IdentityChallenge82>.Ok(value)); };
                if(hold) release = invoke; else invoke();
            }
            public void Submit(IdentityIntent82 intent, string challengeId, string signature, Action<IdentityReply82<IdentitySessionResponse82>> done) {
                submits++; observed = intent.Copy();
                if(lastChallenge.challengeId != challengeId || !vault.Verify(Convert.FromBase64String(lastChallenge.signingBytes), Convert.FromBase64String(signature)) || lastChallenge.payloadDigest != IdentityProtocol82.PayloadDigest(intent)) { done(IdentityReply82<IdentitySessionResponse82>.Fail("SyntheticSignatureRejected")); return; }
                signatures++; IdentitySessionResponse82 result;
                try { result = server.Apply(intent); } catch(Exception) { done(IdentityReply82<IdentitySessionResponse82>.Fail("SyntheticAuthorityRejected")); return; }
                if(loseReply) { loseReply = false; done(IdentityReply82<IdentitySessionResponse82>.Fail("SyntheticLostReply", true)); return; }
                done(IdentityReply82<IdentitySessionResponse82>.Ok(result)); if(duplicate) done(IdentityReply82<IdentitySessionResponse82>.Ok(result));
            }
            public void Cancel() { }
        }
        sealed class Fixture : IDisposable {
            public readonly EditorEphemeralIdentity82 vault = new EditorEphemeralIdentity82();
            public readonly Server server; public readonly string path = Temporary + ".sealed";
            public Transport transport; public ManagedIdentitySession82 manager;
            public Fixture(Server server = null) { this.server = server ?? new Server(); Open(); }
            public void Open() { transport = new Transport(server, vault); manager = new ManagedIdentitySession82(vault.CreateKey(), vault.CreateStore(path), transport); }
            public void Reopen() { manager.Dispose(); Open(); }
            public void Guest() { IdentityReply82<IdentityView82> reply = null; manager.CreateGuest(Id(), r => reply = r); Check(reply != null && reply.Succeeded && manager.HasAccess && manager.View.hasSession && manager.ActivePlayerId==manager.View.playerId, "Bound guest promoted with the in-memory validated owner"); }
            public void Dispose() { manager?.Dispose(); vault.Dispose(); }
        }
        public static void Run() {
            report = new Report { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion,
                scope = "Actual pinned Unity Editor, ephemeral Windows CNG P256 signing, isolated authenticated encrypted file I/O and explicit transport doubles. No Android Keystore, real HTTP, normal profile integration, hardware attestation or production availability claim." };
            Case("Native P256 SPKI DER signatures and tamper rejection", () => {
                using(var vault = new EditorEphemeralIdentity82()) using(var key = vault.CreateKey()) {
                    Check(!key.IsAndroidKeystore && IdentityProtocol82.PublicKey(Convert.ToBase64String(key.PublicSpkiDer())), "Editor key scope accurate");
                    byte[] bytes = Encoding.ASCII.GetBytes("independent-identity82-native-proof"), signature = key.SignSha256Der(bytes);
                    Check(vault.Verify(bytes, signature), "Real native DER verifies"); bytes[0] ^= 1; Check(!vault.Verify(bytes, signature), "Changed message rejected"); bytes[0] ^= 1; signature[signature.Length - 1] ^= 1; Check(!vault.Verify(bytes, signature), "Changed signature rejected");
                }
            });
            Case("Canonical payload and signing bytes all purposes", () => {
                using(var vault = new EditorEphemeralIdentity82()) using(var key = vault.CreateKey()) {
                    string pub = Convert.ToBase64String(key.PublicSpkiDer());
                    foreach(string purpose in new[] { "guest", "session", "recover", "logout", "delete" }) {
                        var intent = new IdentityIntent82 { purpose = purpose, requestId = Id(), publicKey = pub, refreshToken = IdentityProtocol82.NewSecret() };
                        if(purpose == "guest" || purpose == "recover") intent.recoverySecret = IdentityProtocol82.NewSecret();
                        if(purpose == "session") intent.replacementToken = IdentityProtocol82.NewSecret();
                        if(purpose == "recover") intent.replacementRecoverySecret = IdentityProtocol82.NewSecret();
                        if(purpose == "recover" || purpose == "delete") intent.playerId = Id();
                        Check(intent.Valid, "Purpose-specific valid intent"); string digest = IdentityProtocol82.PayloadDigest(intent);
                        if(purpose == "guest") {
                            string canonical = "{\"protocol\":\"hotr-managed-identity-v1\",\"publicKey\":\"" + pub + "\",\"purpose\":\"guest\",\"recoveryDigest\":\"" + IdentityProtocol82.Sha(intent.recoverySecret) + "\",\"refreshDigest\":\"" + IdentityProtocol82.Sha(intent.refreshToken) + "\",\"requestId\":\"" + intent.requestId + "\"}";
                            Check(digest == IdentityProtocol82.Sha(Encoding.ASCII.GetBytes(canonical)), "Independently ordered guest payload digest");
                        }
                        var challenge = Challenge(new IdentityChallengeRequest82 { purpose = purpose, requestId = intent.requestId, publicKey = pub, payloadDigest = digest }, 1000);
                        Check(IdentityProtocol82.ChallengeBytes(challenge, intent).SequenceEqual(Convert.FromBase64String(challenge.signingBytes)), "Independent challenge bytes match");
                        challenge.purpose = "changed"; Reject(() => IdentityProtocol82.ChallengeBytes(challenge, intent), "Changed challenge binding rejected"); challenge.purpose = purpose;
                        challenge.signingBytes = Convert.ToBase64String(Encoding.ASCII.GetBytes("unbound")); Reject(() => IdentityProtocol82.ChallengeBytes(challenge, intent), "Blind arbitrary signing rejected");
                        intent.refreshToken += "\n"; Check(!intent.Valid, "Noncanonical secret rejected");
                    }
                }
            });
            Case("Encrypted CAS durable reopen corruption and cross-vault rejection", () => {
                string path = Temporary + ".sealed"; byte[] plain = Encoding.ASCII.GetBytes("public-test-record-not-a-credential");
                using(var vault = new EditorEphemeralIdentity82()) {
                    using(var first = vault.CreateStore(path)) { Check(first.Read() == null, "Initially absent"); first.CompareExchange("", plain); Reject(() => first.CompareExchange("", plain), "Stale CAS fails"); }
                    using(var reopened = vault.CreateStore(path)) { Check(reopened.Read().SequenceEqual(plain), "Fresh owner reads committed record"); Check(!Encoding.ASCII.GetString(File.ReadAllBytes(path)).Contains(Encoding.ASCII.GetString(plain)), "No plaintext on disk"); }
                    using(var held = new FileStream(path + ".lock", FileMode.Open, FileAccess.ReadWrite, FileShare.None)) using(var competing = vault.CreateStore(path)) Reject(() => competing.CompareExchange(IdentityProtocol82.Sha(plain), plain), "Competing file owner cannot overwrite");
                    using(var other = new EditorEphemeralIdentity82()) using(var wrong = other.CreateStore(path)) Reject(() => wrong.Read(), "Wrong vault cannot decrypt");
                    byte[] sealedBytes = File.ReadAllBytes(path); sealedBytes[30] ^= 1; File.WriteAllBytes(path, sealedBytes);
                    using(var corrupted = vault.CreateStore(path)) Reject(() => corrupted.Read(), "Authenticated corruption fails closed");
                }
            });
            Case("Explicit transport configuration is closed by default", () => {
                using(var closed = new IdentityHttpTransport82()) {
                    Check(!closed.Configured, "No automatic identity backend");
                    IdentityReply82<IdentityChallenge82> reply = null;
                    using(var vault = new EditorEphemeralIdentity82()) using(var key = vault.CreateKey()) closed.Challenge(new IdentityChallengeRequest82 { purpose = "guest", requestId = Id(), publicKey = Convert.ToBase64String(key.PublicSpkiDer()), payloadDigest = new string('a', 64) }, x => reply = x);
                    Check(reply != null && !reply.Succeeded, "Unconfigured identity cannot dispatch");
                }
                foreach(string origin in new[] { "http://identity.hotr-nativecase.ru", "https://identity.hotr-nativecase.ru/path", "https://user@identity.hotr-nativecase.ru", "http://127.0.0.1:8123" }) Reject(() => new IdentityHttpTransport82(origin, _ => { }, false), "Strict origin rejects unsafe or non-opted-in transport");
                using(var loopback = new IdentityHttpTransport82("http://127.0.0.1:8123", _ => { }, true)) Check(loopback.Configured, "Editor loopback needs explicit opt-in");
            });
            Case("Same protected scope cannot be adopted by a different key", () => {
                using(var first = new Fixture()) {
                    first.Guest(); using(var other = new EditorEphemeralIdentity82()) {
                        // Use original encryption owner but a different public
                        // signing key: the journal's account binding rejects it.
                        using(var otherKey = other.CreateKey()) using(var store = first.vault.CreateStore(first.path)) Reject(() => new ManagedIdentitySession82(otherKey, store, new Transport(first.server, other)), "Cross-device journal binding rejected");
                    }
                    Check(first.manager.View.hasSession, "Original account remains readable");
                }
            });
            Case("Save before dispatch and duplicate callbacks", () => {
                using(var f = new Fixture()) {
                    f.vault.VerificationCheckpoint = stage => { if(stage == "BeforeCommit") throw new IOException(); };
                    IdentityReply82<IdentityView82> reply = null; f.manager.CreateGuest(Id(), x => reply = x);
                    Check(reply != null && !reply.Succeeded && f.transport.challenges == 0 && !f.manager.View.hasPending, "Failed intent save dispatches nothing");
                    f.vault.VerificationCheckpoint = null; f.transport.duplicate = true; int callbacks = 0;
                    f.manager.CreateGuest(Id(), x => { reply = x; callbacks++; });
                    Check(reply.Succeeded && callbacks == 1 && f.server.applies == 1 && f.transport.submits == 1, "Double callbacks apply and complete once");
                }
            });
            Case("Lost remote reply reopened exact successor retry", () => {
                using(var f = new Fixture()) {
                    f.transport.loseReply = true; IdentityReply82<IdentityView82> reply = null; f.manager.CreateGuest(Id(), x => reply = x); var sent = f.transport.observed.Copy();
                    Check(!reply.Succeeded && f.manager.View.hasPending && !f.manager.HasAccess && f.server.applies == 1, "Lost remote result stays pending");
                    f.Reopen(); f.manager.Resume(x => reply = x);
                    Check(reply.Succeeded && !f.manager.View.hasPending && f.server.applies == 1 && IdentityProtocol82.PayloadDigest(sent) == IdentityProtocol82.PayloadDigest(f.transport.observed), "Fresh owner reuses exact durable secrets and id");
                }
            });
            Case("Local promotion fault before commit retains retry", () => {
                using(var f = new Fixture()) {
                    f.Guest(); int writes = 0; f.vault.VerificationCheckpoint = stage => { if(stage == "BeforeCommit" && ++writes == 2) throw new IOException(); };
                    IdentityReply82<IdentityView82> reply = null; f.manager.Refresh(Id(), x => reply = x); var sent = f.transport.observed.Copy();
                    Check(!reply.Succeeded && !f.manager.HasAccess && f.manager.View.hasPending && f.server.applies == 2, "Unconfirmed successor not exposed");
                    f.vault.VerificationCheckpoint = null; f.Reopen(); f.manager.Resume(x => reply = x);
                    Check(reply.Succeeded && f.server.applies == 2 && f.transport.observed.replacementToken == sent.replacementToken, "Refresh committed once after reopen");
                }
            });
            Case("After-commit intent and promotion faults recover canonical record", () => {
                using(var f = new Fixture()) {
                    f.vault.VerificationCheckpoint = stage => { if(stage == "AfterCommit") throw new IOException(); };
                    IdentityReply82<IdentityView82> reply = null; f.manager.CreateGuest(Id(), x => reply = x);
                    Check(!reply.Succeeded && f.transport.challenges == 0 && f.manager.View.hasPending, "Lost local save ack persists pending before network");
                    f.vault.VerificationCheckpoint = null; f.manager.Resume(x => reply = x); Check(reply.Succeeded && f.server.applies == 1, "Saved intent retry succeeds");
                    int writes = 0; f.vault.VerificationCheckpoint = stage => { if(stage == "AfterCommit" && ++writes == 2) throw new IOException(); };
                    f.manager.Refresh(Id(), x => reply = x); Check(reply.Succeeded && f.manager.HasAccess && !f.manager.View.hasPending && f.server.applies == 2, "Durable promotion readback confirms lost local ack");
                }
            });
            Case("Cancel fences stale callback and preserves journal", () => {
                using(var f = new Fixture()) {
                    f.transport.hold = true; int calls = 0; f.manager.CreateGuest(Id(), x => calls++); Check(f.manager.Busy && f.manager.View.hasPending, "Pending before held challenge");
                    f.manager.Cancel(); f.transport.release(); Check(!f.manager.Busy && !f.manager.HasAccess && calls == 0 && f.transport.submits == 0 && f.manager.View.hasPending, "Cancelled owner cannot sign or expose stale access");
                    f.Reopen(); IdentityReply82<IdentityView82> reply = null; f.manager.Resume(x => reply = x); Check(reply.Succeeded, "Fresh owner resumes cancelled operation");
                }
            });
            Case("Changed challenge cannot invoke signer or authority", () => {
                using(var f = new Fixture()) { f.transport.badBinding = true; IdentityReply82<IdentityView82> reply = null; f.manager.CreateGuest(Id(), x => reply = x); Check(!reply.Succeeded && f.transport.submits == 0 && f.server.applies == 0 && f.manager.View.hasPending, "Changed binding stays unspent and pending"); }
            });
            Case("Explicit new-key recovery rotates backup and logout clears session", () => {
                using(var old = new Fixture()) {
                    old.Guest(); string backup = old.manager.RecoverySecretForExplicitBackup();
                    using(var next = new Fixture(old.server)) {
                        IdentityReply82<IdentityView82> reply = null; next.manager.Recover(Id(), old.manager.View.playerId, backup, x => reply = x);
                        Check(reply.Succeeded && next.manager.View.keyFingerprint != old.manager.View.keyFingerprint && next.manager.RecoverySecretForExplicitBackup() != backup, "New key and successor recovery bound");
                        old.manager.Refresh(Id(), x => reply = x); Check(!reply.Succeeded && !old.manager.HasAccess, "Old refresh rejected after recovery");
                        next.manager.Logout(Id(), x => reply = x); Check(reply.Succeeded && !next.manager.View.hasSession && !next.manager.HasAccess && next.manager.ActivePlayerId==null, "Logout clears current credentials and cached owner");
                        next.Reopen(); Check(!next.manager.View.hasSession, "Logout durable across owner reopen");
                    }
                }
            });
            Case("Deletion lost reply accepts historical committed receipt", () => {
                using(var f = new Fixture()) { f.Guest(); f.transport.loseReply = true; IdentityReply82<IdentityView82> reply = null; f.manager.RequestDeletion(Id(), x => reply = x); Check(!reply.Succeeded && f.manager.View.hasPending, "Deletion uncertain remains retryable"); f.server.clock += 20; f.Reopen(); f.manager.Resume(x => reply = x); Check(reply.Succeeded && !f.manager.View.hasSession && f.server.applies == 2, "Old deletion requestedAt accepted only for bound exact request"); }
            });
            Save("Identity82.json", "PASS_NATIVE_IDENTITY82"); if(Application.isBatchMode) EditorApplication.Exit(report.errors.Count == 0 ? 0 : 1);
        }

        static readonly Stack<IEnumerator> routines = new Stack<IEnumerator>(); static readonly Queue<IEnumerator> dispatched = new Queue<IEnumerator>(); static AsyncOperation waiting;
        static readonly List<IDisposable> cleanup = new List<IDisposable>(); static double deadline;
        static void Dispatch(IEnumerator routine) { dispatched.Enqueue(routine); }
        static void Tick() {
            try {
                if(EditorApplication.timeSinceStartup > deadline) throw new TimeoutException();
                if(waiting != null) { if(!waiting.isDone) return; waiting = null; }
                if(routines.Count == 0) { FinishHttp(); return; }
                var routine = routines.Peek(); bool advanced = routine.MoveNext();
                if(!advanced) { routines.Pop(); (routine as IDisposable)?.Dispose(); }
                else if(routine.Current is IEnumerator child) routines.Push(child); else if(routine.Current is AsyncOperation operation) waiting = operation;
                // A challenge completion may synchronously enqueue Submit.
                // Drain after removing the actual completed iterator so a new
                // request cannot be popped in place of its predecessor.
                while(dispatched.Count != 0) routines.Push(dispatched.Dequeue());
            } catch(Exception error) { report.errors.Add("HTTP lifecycle: " + error.GetType().Name + ": " + error.Message); FinishHttp(); }
        }
        static void FinishHttp() {
            EditorApplication.update -= Tick; while(routines.Count != 0) (routines.Pop() as IDisposable)?.Dispose(); while(dispatched.Count != 0) (dispatched.Dequeue() as IDisposable)?.Dispose();
            foreach(var item in cleanup) if(item is IdentityHttpTransport82 transport) { report.signedTransportRequests += transport.VerificationRequestCount; report.signedTransportStatuses.AddRange(transport.VerificationStatuses); }
            for(int n = cleanup.Count - 1; n >= 0; n--) try { cleanup[n].Dispose(); } catch(Exception) { } cleanup.Clear(); waiting = null;
            Save("Identity82_HTTP.json", "PASS_NATIVE_IDENTITY82_HTTP"); if(Application.isBatchMode) EditorApplication.Exit(report.errors.Count == 0 ? 0 : 1);
        }
        static IEnumerator Operation(Action<Action<IdentityReply82<IdentityView82>>> call) {
            bool done = false; IdentityReply82<IdentityView82> reply = null; call(x => { reply = x; done = true; });
            while(!done) yield return null; report.requests += 2; Check(reply != null && reply.Succeeded, "Real signed HTTP operation succeeds");
        }
        static IEnumerator Wallet(string origin, ManagedIdentitySession82 manager, string player, bool expected) {
            var client = new RuStoreBackendClient(origin, manager.AccessToken, player, true, true, Dispatch); cleanup.Add(client);
            bool done = false; PayReply<RuStoreServerWallet> reply = null; client.GetWallet(x => { reply = x; done = true; }); while(!done) yield return null; report.requests++;
            Check(reply != null && reply.Succeeded == expected, "Bearer wallet access bound to managed session"); report.walletRequests++;
            Check(expected || reply.error?.code == "StagingHttp401", "Rejected old bearer is actual HTTP401"); report.walletStatuses.Add(expected ? 200 : 401);
            if(expected) { Check(reply.value.playerId == player && reply.value.initialized && reply.value.coins == 1250 && !reply.value.normalUnityProfileIntegrated && !reply.value.localProfileMutated, "Server genesis once and no local integration"); report.walletCoins = reply.value.coins; }
            else report.rejectedOldAccess++;
        }
        static ManagedIdentitySession82 HttpManager(string origin, EditorEphemeralIdentity82 vault, string path) {
            var transport = new IdentityHttpTransport82(origin, Dispatch, true); cleanup.Add(transport);
            var manager = new ManagedIdentitySession82(vault.CreateKey(), vault.CreateStore(path), transport); cleanup.Add(manager); return manager;
        }
        static IEnumerator HttpChecks(string origin) {
            var firstVault = new EditorEphemeralIdentity82(); cleanup.Add(firstVault); string firstPath = Temporary + ".sealed";
            var first = HttpManager(origin, firstVault, firstPath);
            yield return Operation(done => first.CreateGuest(Id(), done)); string player = first.View.playerId, backup = first.RecoverySecretForExplicitBackup(); report.accountIdHash = IdentityProtocol82.Sha(player);
            yield return Wallet(origin, first, player, true);
            yield return Operation(done => first.Refresh(Id(), done)); yield return Wallet(origin, first, player, true);
            var nextVault = new EditorEphemeralIdentity82(); cleanup.Add(nextVault); string nextPath = Temporary + ".sealed";
            var next = HttpManager(origin, nextVault, nextPath); yield return Operation(done => next.Recover(Id(), player, backup, done));
            Check(next.View.keyFingerprint != first.View.keyFingerprint, "Real recovery uses independent new device key"); yield return Wallet(origin, next, player, true); yield return Wallet(origin, first, player, false);
            backup = next.RecoverySecretForExplicitBackup(); yield return Operation(done => next.Logout(Id(), done)); Check(!next.HasAccess && !next.View.hasSession, "Real logout clears session");
            next.Dispose(); var reopened = HttpManager(origin, nextVault, nextPath); Check(!reopened.View.hasSession && !reopened.View.hasPending, "Protected logout journal survives owner reopen");
            var thirdVault = new EditorEphemeralIdentity82(); cleanup.Add(thirdVault); var third = HttpManager(origin, thirdVault, Temporary + ".sealed");
            yield return Operation(done => third.Recover(Id(), player, backup, done)); yield return Wallet(origin, third, player, true);
            // Durable client outbox stays pending after a lost response caused
            // by the protected-store pre-promotion failure, then retries the
            // exact same deletion request against the actual server receipt.
            int writes = 0; thirdVault.VerificationCheckpoint = stage => { if(stage == "BeforeCommit" && ++writes == 2) throw new IOException(); };
            bool doneDelete = false; IdentityReply82<IdentityView82> deleted = null; third.RequestDeletion(Id(), x => { deleted = x; doneDelete = true; }); while(!doneDelete) yield return null; report.requests += 2;
            Check(deleted != null && !deleted.Succeeded && third.View.hasPending && !third.HasAccess, "Actual deletion saved server-side while local successor commit interrupted");
            thirdVault.VerificationCheckpoint = null; yield return Operation(done => third.Resume(done));
            Check(!third.View.hasPending && !third.View.hasSession && !third.HasAccess, "Exact deletion retry durably clears session"); report.cases = 8;
        }
        public static void RunHttp() {
            report = new Report { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion,
                scope = "Actual UnityWebRequest HTTP against explicit isolated managed-identity backend fixture, native ephemeral Windows P256 and encrypted temporary journal. Guest, server wallet, refresh, new-key recovery/revocation, logout/reopen and idempotent deletion. No Android Keystore, hosted production service, normal profile integration or payment claim." };
            try {
                string origin = Environment.GetEnvironmentVariable("HOTR_IDENTITY82_HTTP_ORIGIN");
                if(Environment.GetEnvironmentVariable("HOTR_IDENTITY82_HTTP_ALLOWED") != "1" || !RuStoreBackendClient.IsAllowedOrigin(origin, true) || !new Uri(origin).IsLoopback) throw new InvalidOperationException();
                routines.Clear(); deadline = EditorApplication.timeSinceStartup + 240; routines.Push(HttpChecks(origin)); EditorApplication.update += Tick;
            } catch(Exception) { report.errors.Add("Explicit isolated HTTP fixture unavailable"); FinishHttp(); }
        }
    }
}
#endif
