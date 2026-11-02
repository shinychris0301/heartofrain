using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

namespace HeartOfTheRain.App.OnlineIdentity
{
    public interface IDeviceIdentityKey82 : IDisposable {
        bool IsAndroidKeystore { get; }
        byte[] PublicSpkiDer();
        byte[] SignSha256Der(byte[] message);
    }
    public interface IProtectedSessionStore82 : IDisposable {
        byte[] Read();
        // An absent record has an empty expected digest. Implementations must
        // compare AND durably replace under the same exclusive lock.
        void CompareExchange(string expectedDigest, byte[] replacement);
    }
    public interface IIdentityTransport82 {
        void Challenge(IdentityChallengeRequest82 request, Action<IdentityReply82<IdentityChallenge82>> completed);
        void Submit(IdentityIntent82 request, string challengeId, string signature, Action<IdentityReply82<IdentitySessionResponse82>> completed);
        void Cancel();
    }
    public sealed class IdentityReply82<T> where T : class {
        public readonly T value; public readonly string error; public readonly bool unknown;
        IdentityReply82(T value, string error, bool unknown) { this.value = value; this.error = error; this.unknown = unknown; }
        public bool Succeeded => value != null && error == null;
        public static IdentityReply82<T> Ok(T value) => new IdentityReply82<T>(value ?? throw new ArgumentNullException(nameof(value)), null, false);
        public static IdentityReply82<T> Fail(string error, bool unknown = false) => new IdentityReply82<T>(null, error ?? "IdentityUnavailable", unknown);
    }
    [Serializable] public sealed class IdentityChallengeRequest82 { public string purpose, requestId, publicKey, payloadDigest; }
    [Serializable] public sealed class IdentityChallenge82 {
        public string challengeId, purpose, requestId, keyFingerprint, payloadDigest, nonce, algorithm, signingBytes;
        public long expiresAt, serverUtc;
    }
    [Serializable] public sealed class IdentitySessionResponse82 {
        public string playerId, familyId, keyFingerprint, accessToken, requestId, accountState, state;
        public long expiresAt, refreshExpiresAt, requestedAt;
        public bool replayed, productionEnabled, normalUnityProfileIntegrated, localProfileMutated, sessionsRevoked, physicalPurgeComplete, retentionPolicyConfigured;
    }
    // Never log/serialize this DTO except into the protected journal or the
    // bounded TLS request. The server never returns successor secrets.
    [Serializable] public sealed class IdentityIntent82 {
        public string purpose, requestId, publicKey, playerId, refreshToken, replacementToken, recoverySecret, replacementRecoverySecret;
        public IdentityIntent82 Copy() => (IdentityIntent82)MemberwiseClone();
        public bool Valid {
            get {
                if(!IdentityProtocol82.Id(requestId) || !IdentityProtocol82.PublicKey(publicKey)) return false;
                switch(purpose) {
                    case "guest": return IdentityProtocol82.Secret(refreshToken) && IdentityProtocol82.Secret(recoverySecret) && refreshToken != recoverySecret && Empty(playerId, replacementToken, replacementRecoverySecret);
                    case "session": return IdentityProtocol82.Secret(refreshToken) && IdentityProtocol82.Secret(replacementToken) && refreshToken != replacementToken && Empty(playerId, recoverySecret, replacementRecoverySecret);
                    case "recover": return IdentityProtocol82.Id(playerId) && IdentityProtocol82.Secret(recoverySecret) && IdentityProtocol82.Secret(replacementRecoverySecret) && IdentityProtocol82.Secret(refreshToken) && new[] { recoverySecret, replacementRecoverySecret, refreshToken }.Distinct().Count() == 3 && Empty(replacementToken);
                    case "logout": return IdentityProtocol82.Secret(refreshToken) && Empty(playerId, replacementToken, recoverySecret, replacementRecoverySecret);
                    case "delete": return IdentityProtocol82.Id(playerId) && IdentityProtocol82.Secret(refreshToken) && Empty(replacementToken, recoverySecret, replacementRecoverySecret);
                    default: return false;
                }
            }
        }
        static bool Empty(params string[] fields) => fields.All(string.IsNullOrEmpty);
    }
    public sealed class IdentityView82 {
        public readonly string playerId, familyId, keyFingerprint, pendingPurpose;
        public readonly bool hasSession, hasPending, androidKeystore;
        public readonly long refreshExpiresAt;
        internal IdentityView82(string playerId, string familyId, string fingerprint, string pending, long expiry, bool android) {
            this.playerId = playerId; this.familyId = familyId; keyFingerprint = fingerprint; pendingPurpose = pending;
            hasSession = !string.IsNullOrEmpty(playerId); hasPending = !string.IsNullOrEmpty(pending); refreshExpiresAt = expiry; androidKeystore = android;
        }
    }
    public static class IdentityProtocol82 {
        public const string Protocol = "hotr-managed-identity-v1";
        static readonly byte[] SpkiPrefix = { 0x30, 0x59, 0x30, 0x13, 0x06, 0x07, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01, 0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07, 0x03, 0x42, 0x00, 0x04 };
        public static bool Id(string value) => value != null && Regex.IsMatch(value, @"\A[0-9a-f]{32}\z");
        public static bool Digest(string value) => value != null && Regex.IsMatch(value, @"\A[0-9a-f]{64}\z");
        public static bool Secret(string value) => value != null && Regex.IsMatch(value, @"\A[A-Za-z0-9_-]{43}\z") && CanonicalSecret(value);
        static bool CanonicalSecret(string value) { try { byte[] data = Convert.FromBase64String(value.Replace('-', '+').Replace('_', '/') + "="); return data.Length == 32 && Base64Url(data) == value; } catch(FormatException) { return false; } }
        public static string Base64Url(byte[] bytes) => Convert.ToBase64String(bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        public static string NewSecret() { var bytes = new byte[32]; using(var rng = RandomNumberGenerator.Create()) rng.GetBytes(bytes); return Base64Url(bytes); }
        public static string Sha(byte[] bytes) { using(var hash = SHA256.Create()) return string.Concat(hash.ComputeHash(bytes).Select(x => x.ToString("x2", CultureInfo.InvariantCulture))); }
        public static string Sha(string ascii) { if(ascii == null || ascii.Any(c => c > 127)) throw new InvalidOperationException("Non-ASCII identity binding"); return Sha(Encoding.ASCII.GetBytes(ascii)); }
        public static bool PublicKey(string value) {
            try { var bytes = Convert.FromBase64String(value ?? ""); return bytes.Length == 91 && bytes.Take(SpkiPrefix.Length).SequenceEqual(SpkiPrefix) && Convert.ToBase64String(bytes) == value; }
            catch(FormatException) { return false; }
        }
        public static string Fingerprint(string publicKey) { if(!PublicKey(publicKey)) throw new InvalidOperationException("Invalid device public key"); return Sha(Convert.FromBase64String(publicKey)); }
        static string Quote(string value) {
            // Every value is a validated ASCII protocol identifier, standard
            // base64, hex digest or enum, never user free text.
            if(value == null || value.Any(c => c < 32 || c > 126 || c == '"' || c == '\\')) throw new InvalidOperationException("Invalid identity binding value");
            return "\"" + value + "\"";
        }
        static string Canonical(SortedDictionary<string, string> fields) => "{" + string.Join(",", fields.Select(x => Quote(x.Key) + ":" + Quote(x.Value))) + "}";
        public static string PayloadDigest(IdentityIntent82 intent) {
            if(intent == null || !intent.Valid) throw new InvalidOperationException("Invalid durable identity intent");
            var fields = new SortedDictionary<string, string>(StringComparer.Ordinal) { { "protocol", Protocol }, { "purpose", intent.purpose }, { "requestId", intent.requestId }, { "publicKey", intent.publicKey } };
            if(intent.purpose == "recover" || intent.purpose == "delete") fields.Add("playerId", intent.playerId);
            fields.Add("refreshDigest", Sha(intent.refreshToken ?? ""));
            if(intent.purpose == "guest" || intent.purpose == "recover") fields.Add("recoveryDigest", Sha(intent.recoverySecret));
            if(intent.purpose == "session") fields.Add("replacementDigest", Sha(intent.replacementToken));
            if(intent.purpose == "recover") fields.Add("replacementRecoveryDigest", Sha(intent.replacementRecoverySecret));
            return Sha(Canonical(fields));
        }
        public static byte[] ChallengeBytes(IdentityChallenge82 challenge, IdentityIntent82 intent) {
            if(challenge == null || intent == null || !intent.Valid || challenge.algorithm != "ES256-DER" || !Id(challenge.challengeId) || challenge.requestId != intent.requestId || challenge.purpose != intent.purpose ||
               challenge.keyFingerprint != Fingerprint(intent.publicKey) || challenge.payloadDigest != PayloadDigest(intent) || !Secret(challenge.nonce) || challenge.serverUtc <= 0 || challenge.expiresAt - challenge.serverUtc != 60) throw new InvalidOperationException("Unbound identity challenge");
            var fields = new SortedDictionary<string, string>(StringComparer.Ordinal) { { "challengeId", challenge.challengeId }, { "keyFingerprint", challenge.keyFingerprint }, { "nonce", challenge.nonce }, { "payloadDigest", challenge.payloadDigest }, { "purpose", challenge.purpose }, { "requestId", challenge.requestId } };
            // expiresAt is the only numeric JSON field in the signed contract.
            string json = "{" + string.Join(",", fields.Select(x => Quote(x.Key) + ":" + Quote(x.Value)).Concat(new[] { "\"expiresAt\":" + challenge.expiresAt.ToString(CultureInfo.InvariantCulture) }).OrderBy(x => x, StringComparer.Ordinal)) + "}";
            byte[] expected = Encoding.ASCII.GetBytes(Protocol + "\n" + json), supplied;
            try { supplied = Convert.FromBase64String(challenge.signingBytes ?? ""); } catch(FormatException) { throw new InvalidOperationException("Invalid challenge encoding"); }
            if(Convert.ToBase64String(supplied) != challenge.signingBytes || !supplied.SequenceEqual(expected)) throw new InvalidOperationException("Identity signing bytes changed"); return expected;
        }
    }
}
