using System;
using System.Linq;
using System.Text;
using UnityEngine;

namespace HeartOfTheRain.App.OnlineIdentity
{
    [Serializable] sealed class IdentityCredentials82 {
        public string playerId, familyId, keyFingerprint, refreshToken, recoverySecret;
        public long refreshExpiresAt;
    }
    [Serializable] sealed class IdentityDocument82 {
        public int version = 1;
        public long revision;
        public string publicKey, lastCompletedRequest, lastCompletedPurpose;
        public bool hasCurrent, hasPending;
        public IdentityCredentials82 current = new IdentityCredentials82();
        public IdentityIntent82 pending = new IdentityIntent82();
    }
    // Exactly one encrypted document owns the current credential AND pending
    // successor. Promotion and clearing the outbox occur in a single CAS write.
    // This is never a ProfileService repository or a wallet import mechanism.
    sealed partial class ProtectedSessionJournal82
    {
        static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
        readonly IProtectedSessionStore82 store;
        readonly string publicKey;
        public ProtectedSessionJournal82(IProtectedSessionStore82 store, string publicKey) {
            this.store = store ?? throw new ArgumentNullException(nameof(store));
            if(!IdentityProtocol82.PublicKey(publicKey)) throw new ArgumentException("InvalidDevicePublicKey"); this.publicKey = publicKey;
        }
        static IdentityCredentials82 Copy(IdentityCredentials82 c) => new IdentityCredentials82 { playerId = c.playerId, familyId = c.familyId, keyFingerprint = c.keyFingerprint, refreshToken = c.refreshToken, recoverySecret = c.recoverySecret, refreshExpiresAt = c.refreshExpiresAt };
        static IdentityDocument82 Canonical(IdentityDocument82 value) => new IdentityDocument82 {
            version = value.version, revision = value.revision, publicKey = value.publicKey, hasCurrent = value.hasCurrent, hasPending = value.hasPending,
            lastCompletedRequest = value.lastCompletedRequest, lastCompletedPurpose = value.lastCompletedPurpose,
            current = value.hasCurrent ? Copy(value.current) : new IdentityCredentials82(), pending = value.hasPending ? value.pending.Copy() : new IdentityIntent82()
        };
        void Validate(IdentityDocument82 value) {
            if(value == null || value.version != 1 || value.revision < 0 || value.publicKey != publicKey) throw new InvalidOperationException("InvalidProtectedIdentityRecord");
            if(!string.IsNullOrEmpty(value.lastCompletedRequest) && (!IdentityProtocol82.Id(value.lastCompletedRequest) || !new[] { "guest", "session", "recover", "logout", "delete", "vk" }.Contains(value.lastCompletedPurpose))) throw new InvalidOperationException("InvalidCompletedIdentityOperation");
            if(value.hasCurrent) {
                var c = value.current;
                // An exact empty backup denotes a VK-recovered scope which
                // does not know or rotate the owner's existing recovery code.
                if(c == null || !IdentityProtocol82.Id(c.playerId) || !IdentityProtocol82.Id(c.familyId) || c.keyFingerprint != IdentityProtocol82.Fingerprint(publicKey) || !IdentityProtocol82.Secret(c.refreshToken) || !(c.recoverySecret==""||IdentityProtocol82.Secret(c.recoverySecret)) || c.refreshToken == c.recoverySecret || c.refreshExpiresAt <= 0) throw new InvalidOperationException("InvalidProtectedIdentitySession");
            }
            if(value.hasPending) {
                var p = value.pending;
                if(p == null || !p.Valid || p.publicKey != publicKey) throw new InvalidOperationException("InvalidProtectedIdentityIntent");
                if(p.purpose == "guest" || p.purpose == "recover") { if(value.hasCurrent) throw new InvalidOperationException("IdentityAccountReplacementRequiresExplicitNewScope"); }
                else if(!value.hasCurrent || p.refreshToken != value.current.refreshToken || p.purpose == "delete" && p.playerId != value.current.playerId) throw new InvalidOperationException("IdentityIntentSessionMismatch");
            }
        }
        public IdentityDocument82 Read(out string digest) {
            byte[] bytes = store.Read();
            if(bytes == null) { digest = ""; return new IdentityDocument82 { publicKey = publicKey }; }
            if(bytes.Length < 1 || bytes.Length > 32768) throw new InvalidOperationException("ProtectedIdentityRecordSize");
            string json = Utf8.GetString(bytes); var value = JsonUtility.FromJson<IdentityDocument82>(json); Validate(value);
            if(JsonUtility.ToJson(Canonical(value)) != json) throw new InvalidOperationException("NoncanonicalProtectedIdentityRecord");
            digest = IdentityProtocol82.Sha(bytes); return Canonical(value);
        }
        public IdentityDocument82 Write(string expectedDigest, IdentityDocument82 next) {
            Validate(next); var canonical = Canonical(next); byte[] bytes = Utf8.GetBytes(JsonUtility.ToJson(canonical));
            if(bytes.Length > 32768) throw new InvalidOperationException("ProtectedIdentityRecordSize");
            store.CompareExchange(expectedDigest, bytes);
            // A store that reports success must make the exact record readable.
            string actualDigest; var confirmed = Read(out actualDigest);
            if(actualDigest != IdentityProtocol82.Sha(bytes)) throw new InvalidOperationException("ProtectedIdentityWriteUnconfirmed"); return confirmed;
        }
        public IdentityDocument82 Prepare(IdentityIntent82 intent) {
            string digest; var value = Read(out digest);
            if(value.hasPending) {
                if(value.pending.requestId != intent.requestId || IdentityProtocol82.PayloadDigest(value.pending) != IdentityProtocol82.PayloadDigest(intent)) throw new InvalidOperationException("AnotherIdentityOperationRequiresRecovery"); return value;
            }
            if(value.revision == long.MaxValue || value.lastCompletedRequest == intent.requestId) throw new InvalidOperationException("IdentityCommandMustBeNew");
            value.revision++; value.hasPending = true; value.pending = intent.Copy(); return Write(digest, value);
        }
        public IdentityDocument82 Promote(IdentityIntent82 intent, IdentitySessionResponse82 response) {
            string digest; var value = Read(out digest);
            if(!value.hasPending || value.pending.requestId != intent.requestId || IdentityProtocol82.PayloadDigest(value.pending) != IdentityProtocol82.PayloadDigest(intent)) throw new InvalidOperationException("IdentityIntentChangedDuringConfirmation");
            if(value.revision == long.MaxValue) throw new InvalidOperationException("IdentityRevisionOverflow");
            if(intent.purpose == "logout" || intent.purpose == "delete") { value.hasCurrent = false; value.current = new IdentityCredentials82(); }
            else {
                string refresh = intent.purpose == "session" ? intent.replacementToken : intent.refreshToken;
                string recovery = intent.purpose == "guest" ? intent.recoverySecret : intent.purpose == "recover" ? intent.replacementRecoverySecret : value.current.recoverySecret;
                value.hasCurrent = true; value.current = new IdentityCredentials82 { playerId = response.playerId, familyId = response.familyId, keyFingerprint = response.keyFingerprint, refreshToken = refresh, recoverySecret = recovery, refreshExpiresAt = response.refreshExpiresAt };
            }
            value.hasPending = false; value.pending = new IdentityIntent82(); value.lastCompletedRequest = intent.requestId; value.lastCompletedPurpose = intent.purpose; value.revision++;
            return Write(digest, value);
        }
        public bool IsPromoted(IdentityIntent82 intent, IdentitySessionResponse82 response) {
            string digest; var value = Read(out digest);
            if(value.hasPending || value.lastCompletedRequest != intent.requestId || value.lastCompletedPurpose != intent.purpose) return false;
            if(intent.purpose == "logout" || intent.purpose == "delete") return !value.hasCurrent;
            return value.hasCurrent && value.current.playerId == response.playerId && value.current.familyId == response.familyId && value.current.keyFingerprint == response.keyFingerprint && value.current.refreshExpiresAt == response.refreshExpiresAt &&
                value.current.refreshToken == (intent.purpose == "session" ? intent.replacementToken : intent.refreshToken) &&
                (intent.purpose != "recover" || value.current.recoverySecret == intent.replacementRecoverySecret) && (intent.purpose != "guest" || value.current.recoverySecret == intent.recoverySecret);
        }
    }
}
