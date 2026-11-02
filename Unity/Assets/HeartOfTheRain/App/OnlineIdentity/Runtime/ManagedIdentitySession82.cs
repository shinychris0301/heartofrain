using System;
using System.Diagnostics;

namespace HeartOfTheRain.App.OnlineIdentity
{
    // Explicit managed staging session. No MonoBehaviour/factory, wallet,
    // ordinary profile, provider login or account-merge side effect.
    public sealed partial class ManagedIdentitySession82 : IDisposable
    {
        readonly IDeviceIdentityKey82 key;
        readonly IProtectedSessionStore82 store;
        readonly IIdentityTransport82 transport;
        readonly ProtectedSessionJournal82 journal;
        readonly string publicKey;
        readonly bool expectedProduction;
        long generation, accessAt;
        double accessSeconds;
        string access,accessPlayerId;
        bool busy, disposed, renewing;
        const double RenewalMarginSeconds = 60;
        public bool Busy => busy;
        double AccessAge => (Stopwatch.GetTimestamp() - accessAt) / (double)Stopwatch.Frequency;
        // The server honours a rotated token for a short grace period, so a
        // same-account renewal does not interrupt requests or cached pages.
        public bool HasAccess => !disposed && (!busy || renewing) && access != null && AccessAge < accessSeconds;
        public bool RenewalDue => !disposed && !busy && access != null && AccessAge >= accessSeconds - RenewalMarginSeconds;
        public string AccessToken => HasAccess ? access : null;
        // The player ID was already bound to the signed response and committed
        // to the protected journal. Rendering may read it without decrypting
        // that journal for every label, pane and frame. View remains a durable read.
        public string ActivePlayerId => HasAccess ? accessPlayerId : null;
        // A durable read decrypts through the keystore. Callers polling every frame while
        // offline use this instead; only this class's operations can change the journal.
        string knownPlayerId; bool playerKnown;
        public string KnownPlayerId { get { if(!playerKnown) { knownPlayerId = View.playerId; playerKnown = true; } return knownPlayerId; } }
        // The monotonic clock can stop in deep sleep while the server's token keeps ageing.
        public void AdjustForSleep(double seconds) { if(seconds > 0) accessAt -= (long)(seconds * Stopwatch.Frequency); }
        // The server refused this token, so its local age was wrong. The session itself stays.
        public void ExpireAccess() { if(!renewing) access = accessPlayerId = null; }
        public ManagedIdentitySession82(IDeviceIdentityKey82 key, IProtectedSessionStore82 store, IIdentityTransport82 transport, bool expectedProduction=false)
        {
            this.expectedProduction=expectedProduction;
            if(transport is IdentityHttpTransport82 http&&http.ExpectedProduction!=expectedProduction)throw new ArgumentException("IdentityEnvironmentMismatch");
            this.key = key ?? throw new ArgumentNullException(nameof(key)); this.store = store ?? throw new ArgumentNullException(nameof(store)); this.transport = transport ?? throw new ArgumentNullException(nameof(transport));
            publicKey = Convert.ToBase64String(key.PublicSpkiDer()); journal = new ProtectedSessionJournal82(store, publicKey);
            string digest; journal.Read(out digest); // A corrupt/mismatched store never becomes a fresh guest.
        }
        public IdentityView82 View {
            get {
                if(disposed) throw new ObjectDisposedException(nameof(ManagedIdentitySession82)); string digest; var value = journal.Read(out digest);
                return new IdentityView82(value.hasCurrent ? value.current.playerId : null, value.hasCurrent ? value.current.familyId : null,
                    IdentityProtocol82.Fingerprint(publicKey), value.hasPending ? value.pending.purpose : null, value.hasCurrent ? value.current.refreshExpiresAt : 0, key.IsAndroidKeystore);
            }
        }
        // Call only for an explicit account-backup action. Never write the
        // result to analytics, ordinary profiles, PlayerPrefs or source files.
        public string RecoverySecretForExplicitBackup() {
            if(disposed || busy) throw new InvalidOperationException("IdentitySessionUnavailable"); string digest; var value = journal.Read(out digest);
            if(!value.hasCurrent || value.hasPending) throw new InvalidOperationException("IdentitySessionUnavailable"); return value.current.recoverySecret;
        }
        static void Deliver(Action<IdentityReply82<IdentityView82>> done, IdentityReply82<IdentityView82> reply) { try { done(reply); } catch(Exception) { } }
        bool Ready(Action<IdentityReply82<IdentityView82>> done) {
            if(done == null) throw new ArgumentNullException(nameof(done));
            if(disposed || busy) { Deliver(done, IdentityReply82<IdentityView82>.Fail(disposed ? "IdentityOwnerClosed" : "IdentityBusy")); return false; } return true;
        }
        void Begin(IdentityIntent82 intent, Action<IdentityReply82<IdentityView82>> done) {
            if(!Ready(done)) return;
            try { if(intent == null || !intent.Valid) throw new InvalidOperationException(); journal.Prepare(intent); }
            catch(Exception) { renewing = false; Deliver(done, IdentityReply82<IdentityView82>.Fail("IdentityIntentSaveUnconfirmed", true)); return; }
            Dispatch(intent, done);
        }
        public void CreateGuest(string requestId, Action<IdentityReply82<IdentityView82>> done) {
            if(!Ready(done)) return; string digest; IdentityDocument82 value;
            try { value = journal.Read(out digest); } catch(Exception) { Deliver(done, IdentityReply82<IdentityView82>.Fail("IdentityProtectedReadUnavailable")); return; }
            if(value.hasCurrent || value.hasPending) { Deliver(done, IdentityReply82<IdentityView82>.Fail("ExistingIdentityRequiresRecovery")); return; }
            Begin(new IdentityIntent82 { purpose = "guest", requestId = requestId, publicKey = publicKey, refreshToken = IdentityProtocol82.NewSecret(), recoverySecret = IdentityProtocol82.NewSecret() }, done);
        }
        public void Refresh(string requestId, Action<IdentityReply82<IdentityView82>> done) => SessionOperation("session", requestId, done);
        public void Logout(string requestId, Action<IdentityReply82<IdentityView82>> done) => SessionOperation("logout", requestId, done);
        public void RequestDeletion(string requestId, Action<IdentityReply82<IdentityView82>> done) => SessionOperation("delete", requestId, done);
        void SessionOperation(string purpose, string requestId, Action<IdentityReply82<IdentityView82>> done) {
            if(!Ready(done)) return; string digest; IdentityDocument82 value;
            try { value = journal.Read(out digest); } catch(Exception) { Deliver(done, IdentityReply82<IdentityView82>.Fail("IdentityProtectedReadUnavailable")); return; }
            if(!value.hasCurrent || value.hasPending) { Deliver(done, IdentityReply82<IdentityView82>.Fail("IdentitySessionRequiresRecovery")); return; }
            renewing = purpose == "session" && access != null; if(!renewing) access = accessPlayerId = null;
            Begin(new IdentityIntent82 { purpose = purpose, requestId = requestId, publicKey = publicKey, refreshToken = value.current.refreshToken,
                replacementToken = purpose == "session" ? IdentityProtocol82.NewSecret() : null, playerId = purpose == "delete" ? value.current.playerId : null }, done);
        }
        public void Recover(string requestId, string playerId, string recoverySecret, Action<IdentityReply82<IdentityView82>> done) {
            if(!Ready(done)) return; string digest; IdentityDocument82 value;
            try { value = journal.Read(out digest); } catch(Exception) { Deliver(done, IdentityReply82<IdentityView82>.Fail("IdentityProtectedReadUnavailable")); return; }
            if(value.hasCurrent || value.hasPending) { Deliver(done, IdentityReply82<IdentityView82>.Fail("RecoveryRequiresExplicitEmptyIdentityScope")); return; }
            Begin(new IdentityIntent82 { purpose = "recover", requestId = requestId, publicKey = publicKey, playerId = playerId, recoverySecret = recoverySecret,
                replacementRecoverySecret = IdentityProtocol82.NewSecret(), refreshToken = IdentityProtocol82.NewSecret() }, done);
        }
        public void Resume(Action<IdentityReply82<IdentityView82>> done) {
            if(!Ready(done)) return;
            try { string digest; var value = journal.Read(out digest); if(!value.hasPending) { Deliver(done, IdentityReply82<IdentityView82>.Fail("NoPendingIdentityOperation")); return; } renewing = value.pending.purpose == "session" && access != null; Dispatch(value.pending.Copy(), done); }
            catch(Exception) { Deliver(done, IdentityReply82<IdentityView82>.Fail("IdentityProtectedReadUnavailable")); }
        }
        void Finish(long token, Action<IdentityReply82<IdentityView82>> done, string error, bool unknown = false) {
            if(disposed || generation != token) return; bool renewal = renewing; busy = renewing = false; playerKnown = false;
            // A failed renewal leaves the old token usable until it really expires.
            if(error != null && !renewal) access = accessPlayerId = null;
            Deliver(done, error == null ? IdentityReply82<IdentityView82>.Ok(View) : IdentityReply82<IdentityView82>.Fail(error, unknown));
        }
        void Dispatch(IdentityIntent82 intent, Action<IdentityReply82<IdentityView82>> done) {
            busy = true; long token = ++generation; long began = Stopwatch.GetTimestamp(); int challengeCalled = 0, submitCalled = 0;
            IdentityDocument82 expected;
            try { string digest; expected = journal.Read(out digest); }
            catch(Exception) { Finish(token, done, "IdentityProtectedReadUnavailable"); return; }
            try {
                transport.Challenge(new IdentityChallengeRequest82 { purpose = intent.purpose, requestId = intent.requestId, publicKey = intent.publicKey, payloadDigest = IdentityProtocol82.PayloadDigest(intent) }, challengeReply => {
                    if(disposed || token != generation || System.Threading.Interlocked.Exchange(ref challengeCalled, 1) != 0) return;
                    try {
                        if(challengeReply == null || !challengeReply.Succeeded) { Finish(token, done, challengeReply?.error ?? "IdentityChallengeUnavailable", true); return; }
                        var challenge = challengeReply.value; byte[] bytes = IdentityProtocol82.ChallengeBytes(challenge, intent);
                        if((Stopwatch.GetTimestamp() - began) / (double)Stopwatch.Frequency >= 55) { Finish(token, done, "IdentityChallengeExpired", true); return; }
                        string signature = Convert.ToBase64String(key.SignSha256Der(bytes));
                        transport.Submit(intent.Copy(), challenge.challengeId, signature, reply => {
                            if(disposed || token != generation || System.Threading.Interlocked.Exchange(ref submitCalled, 1) != 0) return;
                            try {
                                if(reply == null || !reply.Succeeded) { Finish(token, done, reply?.error ?? "IdentityConfirmationUnavailable", true); return; }
                                var response = reply.value;
                                ValidateResponse(intent, expected, challenge, response);
                                try { journal.Promote(intent, response); }
                                catch(Exception) { if(!journal.IsPromoted(intent, response)) { Finish(token, done, "IdentitySuccessorSaveUnconfirmed", true); return; } }
                                if(intent.purpose == "logout" || intent.purpose == "delete") access = accessPlayerId = null;
                                else {
                                    access = response.accessToken; accessPlayerId = response.playerId; accessAt = began;
                                    // Uses server challenge time plus monotonic elapsed time,
                                    // never device UTC. Conservative if minting was later.
                                    accessSeconds = Math.Min(900, response.expiresAt - challenge.serverUtc);
                                }
                                Finish(token, done, null);
                            } catch(Exception) { Finish(token, done, "IdentityBoundConfirmationInvalid", true); }
                        });
                    } catch(Exception) { Finish(token, done, "IdentityChallengeOrSigningInvalid", true); }
                });
            } catch(Exception) { Finish(token, done, "IdentityDispatchUnavailable", true); }
        }
        void ValidateResponse(IdentityIntent82 intent, IdentityDocument82 prior, IdentityChallenge82 challenge, IdentitySessionResponse82 response) {
            if(response == null || response.requestId != intent.requestId || !IdentityProtocol82.Id(response.playerId)) throw new InvalidOperationException();
            if(intent.purpose == "logout") {
                if(!prior.hasCurrent || response.playerId != prior.current.playerId || response.familyId != prior.current.familyId || response.state != "LoggedOut") throw new InvalidOperationException(); return;
            }
            if(intent.purpose == "delete") {
                if(response.playerId != intent.playerId || response.state != "DeletionRequested" || !response.sessionsRevoked || response.requestedAt <= 0 || response.requestedAt > challenge.serverUtc + 60 ||
                   response.normalUnityProfileIntegrated || response.localProfileMutated || response.physicalPurgeComplete || response.retentionPolicyConfigured) throw new InvalidOperationException(); return;
            }
            if(!IdentityProtocol82.Id(response.familyId) || response.keyFingerprint != IdentityProtocol82.Fingerprint(intent.publicKey) || !IdentityProtocol82.Secret(response.accessToken) ||
               response.accountState != "Active" || response.productionEnabled != expectedProduction || response.normalUnityProfileIntegrated || response.expiresAt <= challenge.serverUtc || response.expiresAt > challenge.serverUtc + 960 ||
               response.refreshExpiresAt < response.expiresAt || response.refreshExpiresAt > challenge.serverUtc + 90L * 86400 + 60) throw new InvalidOperationException();
            if(intent.purpose == "session" && (!prior.hasCurrent || response.playerId != prior.current.playerId || response.familyId != prior.current.familyId)) throw new InvalidOperationException();
            if(intent.purpose == "recover" && response.playerId != intent.playerId) throw new InvalidOperationException();
        }
        public void Cancel() { generation++; busy = renewing = false; playerKnown = false; access = accessPlayerId = null; try { transport.Cancel(); } catch(Exception) { } }
        public void Dispose() { if(disposed) return; Cancel(); disposed = true; try { key.Dispose(); } finally { store.Dispose(); } }
    }
}
