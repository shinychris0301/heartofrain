using System;
using System.Text;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.OnlineSocial
{
    [Serializable] public sealed class SocialPendingCommand82 {
        public string operation, path, body, commandId;
        public SocialPendingCommand82 Copy() => (SocialPendingCommand82)MemberwiseClone();
    }
    // A SEPARATE protected store is mandatory for writes. Never give this class
    // the managed identity journal's path/alias; the two CAS documents differ.
    public sealed class ProtectedSocialCommandJournal82
    {
        [Serializable] sealed class Document { public int version = 1; public string playerId, origin; public bool hasPending; public SocialPendingCommand82 pending; }
        readonly IProtectedSessionStore82 store; readonly string player, origin;SocialPendingCommand82 cachedPending;
        static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
        public ProtectedSocialCommandJournal82(IProtectedSessionStore82 store, string player, string origin) {
            this.store = store ?? throw new ArgumentNullException(nameof(store)); this.player = player; this.origin = origin;
            string digest;var current=Read(out digest);cachedPending=current.hasPending?current.pending.Copy():null;
        }
        Document Read(out string digest) {
            byte[] bytes = store.Read(); digest = bytes == null || bytes.Length == 0 ? "" : IdentityProtocol82.Sha(bytes);
            if(bytes == null || bytes.Length == 0) return new Document { playerId = player, origin = origin };
            if(bytes.Length > 65536) throw new InvalidOperationException("SocialOutboxCorrupt");
            string json = Utf8.GetString(bytes); var fields = SocialJson82.Read(json);
            if(SocialJson82.Number(fields, "version", 1, 1) != 1 || SocialJson82.Text(fields, "playerId", 32) != player ||
               SocialJson82.Text(fields, "origin", 2048) != origin) throw new InvalidOperationException("SocialOutboxScopeMismatch");
            bool pending = SocialJson82.Flag(fields, "hasPending"); var value = JsonUtility.FromJson<Document>(json);
            if(pending) Validate(value.pending); else value.pending = null;
            return value;
        }
        static void Validate(SocialPendingCommand82 value) {
            if(value == null || !IdentityProtocol82.Id(value.commandId) || string.IsNullOrEmpty(value.operation) || value.operation.Length > 64 ||
               string.IsNullOrEmpty(value.path) || !value.path.StartsWith("/v1/", StringComparison.Ordinal) || value.path.Length > 512 ||
               value.path.IndexOfAny(new[] { '\r', '\n', '\\', '#', '?' }) >= 0 || string.IsNullOrEmpty(value.body) || Utf8.GetByteCount(value.body) > 16384 ||
               SocialJson82.Text(SocialJson82.Read(value.body), "commandId", 32) != value.commandId) throw new InvalidOperationException("SocialOutboxCorrupt");
        }
        static bool Same(SocialPendingCommand82 first, SocialPendingCommand82 second) => first != null && second != null && first.operation == second.operation && first.path == second.path && first.body == second.body && first.commandId == second.commandId;
        void Save(string digest, Document value) { byte[] bytes = Utf8.GetBytes(JsonUtility.ToJson(value)); if(bytes.Length > 65536) throw new InvalidOperationException(); store.CompareExchange(digest, bytes); }
        public SocialPendingCommand82 Pending { get { string digest; var value = Read(out digest); return value.hasPending ? value.pending.Copy() : null; } }
        // UI polling must not decrypt the protected store every frame. Durable
        // mutations and recovery continue to use Pending/Read and CAS.
        public SocialPendingCommand82 CachedPending => cachedPending?.Copy();
        public void Prepare(SocialPendingCommand82 command) {
            Validate(command); string digest; var value = Read(out digest);
            cachedPending=value.hasPending?value.pending.Copy():null;
            if(value.hasPending) { if(!Same(value.pending, command)) throw new InvalidOperationException("SocialPendingMutationConflict"); return; }
            value.pending = command.Copy(); value.hasPending = true; Save(digest, value);cachedPending=command.Copy();
        }
        public void Confirm(SocialPendingCommand82 command) {
            string digest; var value = Read(out digest);
            cachedPending=value.hasPending?value.pending.Copy():null;
            if(!value.hasPending || !Same(value.pending, command)) throw new InvalidOperationException("SocialOutboxChanged");
            value.hasPending = false; value.pending = null; Save(digest, value);cachedPending=null;
        }
        public void AcknowledgeAndDiscard(string expectedCommandId, bool acknowledgesMayAlreadyBeCommitted) {
            if(!acknowledgesMayAlreadyBeCommitted || !IdentityProtocol82.Id(expectedCommandId)) throw new InvalidOperationException("ExplicitSocialDiscardAcknowledgementRequired");
            var pending = Pending;
            if(pending == null || pending.commandId != expectedCommandId) throw new InvalidOperationException("SocialOutboxChanged");
            // This only discards local retry ownership. It cannot undo a server
            // message or declare that an in-flight/lost request never committed.
            Confirm(pending);
        }
    }
}
