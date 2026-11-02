#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;

namespace HeartOfTheRain.App.OnlineIdentity
{
    // Verification ONLY: real ephemeral Windows CNG P256 and an isolated
    // AES-CBC/HMAC file vault. This is not Android Keystore, persistent identity,
    // hardware attestation or a production credential-store implementation.
    public sealed class EditorEphemeralIdentity82 : IDisposable
    {
        [DllImport("bcrypt.dll", CharSet = CharSet.Unicode)] static extern int BCryptOpenAlgorithmProvider(out IntPtr algorithm, string name, string provider, uint flags);
        [DllImport("bcrypt.dll")] static extern int BCryptGenerateKeyPair(IntPtr algorithm, out IntPtr key, uint bits, uint flags);
        [DllImport("bcrypt.dll")] static extern int BCryptFinalizeKeyPair(IntPtr key, uint flags);
        [DllImport("bcrypt.dll", CharSet = CharSet.Unicode)] static extern int BCryptExportKey(IntPtr key, IntPtr exportKey, string type, byte[] output, uint capacity, out uint length, uint flags);
        [DllImport("bcrypt.dll")] static extern int BCryptSignHash(IntPtr key, IntPtr padding, byte[] hash, uint hashLength, byte[] output, uint capacity, out uint length, uint flags);
        [DllImport("bcrypt.dll")] static extern int BCryptVerifySignature(IntPtr key, IntPtr padding, byte[] hash, uint hashLength, byte[] signature, uint signatureLength, uint flags);
        [DllImport("bcrypt.dll")] static extern int BCryptDestroyKey(IntPtr key);
        [DllImport("bcrypt.dll")] static extern int BCryptCloseAlgorithmProvider(IntPtr algorithm, uint flags);
        IntPtr algorithm, key;
        byte[] sealKey = new byte[32], macKey = new byte[32];
        bool disposed;
        public Action<string> VerificationCheckpoint;
        public EditorEphemeralIdentity82() {
            if(Environment.OSVersion.Platform != PlatformID.Win32NT) throw new NotSupportedException("NativeEditorP256RequiresWindows");
            try {
                Need(BCryptOpenAlgorithmProvider(out algorithm, "ECDSA_P256", null, 0)); Need(BCryptGenerateKeyPair(algorithm, out key, 256, 0)); Need(BCryptFinalizeKeyPair(key, 0));
                using(var random = RandomNumberGenerator.Create()) { random.GetBytes(sealKey); random.GetBytes(macKey); }
            } catch { Dispose(); throw; }
        }
        static void Need(int code) { if(code != 0) throw new CryptographicException("EphemeralP256Unavailable"); }
        void Alive() { if(disposed) throw new ObjectDisposedException(nameof(EditorEphemeralIdentity82)); }
        byte[] Public() {
            Alive(); uint length; Need(BCryptExportKey(key, IntPtr.Zero, "ECCPUBLICBLOB", null, 0, out length, 0)); var blob = new byte[length]; Need(BCryptExportKey(key, IntPtr.Zero, "ECCPUBLICBLOB", blob, length, out length, 0));
            if(length != 72 || BitConverter.ToUInt32(blob, 0) != 0x31534345 || BitConverter.ToUInt32(blob, 4) != 32) throw new CryptographicException("InvalidEphemeralP256Blob");
            byte[] prefix = { 0x30, 0x59, 0x30, 0x13, 0x06, 0x07, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01, 0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07, 0x03, 0x42, 0x00, 0x04 };
            return prefix.Concat(blob.Skip(8)).ToArray();
        }
        static byte[] Integer(byte[] raw, int offset) {
            int first = offset; while(first < offset + 31 && raw[first] == 0) first++; int size = offset + 32 - first; bool pad = raw[first] >= 128;
            var result = new byte[size + (pad ? 3 : 2)]; result[0] = 2; result[1] = (byte)(size + (pad ? 1 : 0)); Buffer.BlockCopy(raw, first, result, pad ? 3 : 2, size); return result;
        }
        byte[] Sign(byte[] message) {
            Alive(); if(message == null || message.Length < 1 || message.Length > 4096) throw new ArgumentException("InvalidIdentityMessage");
            byte[] hash; using(var sha = SHA256.Create()) hash = sha.ComputeHash(message); uint length;
            Need(BCryptSignHash(key, IntPtr.Zero, hash, 32, null, 0, out length, 0)); var raw = new byte[length]; Need(BCryptSignHash(key, IntPtr.Zero, hash, 32, raw, length, out length, 0));
            if(length != 64) throw new CryptographicException("InvalidEphemeralSignature"); var body = Integer(raw, 0).Concat(Integer(raw, 32)).ToArray(); return new byte[] { 0x30, (byte)body.Length }.Concat(body).ToArray();
        }
        public bool Verify(byte[] message, byte[] signature) {
            Alive();
            try {
                if(signature == null || signature.Length < 8 || signature[0] != 0x30 || signature[1] != signature.Length - 2) return false;
                var raw = new byte[64]; int at = 2;
                for(int n = 0; n < 2; n++) {
                    if(at + 2 > signature.Length || signature[at++] != 2) return false; int size = signature[at++];
                    if(size < 1 || size > 33 || at + size > signature.Length || signature[at] >= 128) return false;
                    if(size > 1 && signature[at] == 0) { if(signature[at + 1] < 128) return false; at++; size--; }
                    if(size > 32) return false; Buffer.BlockCopy(signature, at, raw, n * 32 + 32 - size, size); at += size;
                }
                if(at != signature.Length) return false; byte[] hash; using(var sha = SHA256.Create()) hash = sha.ComputeHash(message);
                return BCryptVerifySignature(key, IntPtr.Zero, hash, 32, raw, 64, 0) == 0;
            } catch(Exception) { return false; }
        }
        sealed class Key : IDeviceIdentityKey82 {
            readonly EditorEphemeralIdentity82 owner; bool closed;
            public Key(EditorEphemeralIdentity82 owner) { this.owner = owner; }
            public bool IsAndroidKeystore => false;
            void Alive() { if(closed) throw new ObjectDisposedException(nameof(Key)); owner.Alive(); }
            public byte[] PublicSpkiDer() { Alive(); return owner.Public(); }
            public byte[] SignSha256Der(byte[] message) { Alive(); return owner.Sign(message); }
            public void Dispose() { closed = true; }
        }
        public IDeviceIdentityKey82 CreateKey() { Alive(); return new Key(this); }
        public IProtectedSessionStore82 CreateStore(string path) { Alive(); return new Store(this, path); }
        sealed class Store : IProtectedSessionStore82 {
            readonly EditorEphemeralIdentity82 owner; readonly string path; bool closed;
            readonly byte[] binding;
            public Store(EditorEphemeralIdentity82 owner, string path) {
                this.owner = owner; this.path = Path.GetFullPath(path);
                string allowed = Path.GetFullPath("../.verification-cache/Launch82/");
                if(!this.path.StartsWith(allowed, StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("EphemeralIdentityFixtureMustBeInIgnoredCache");
                Directory.CreateDirectory(Path.GetDirectoryName(this.path)); binding = Encoding.UTF8.GetBytes(this.path.ToLowerInvariant());
            }
            void Alive() { if(closed) throw new ObjectDisposedException(nameof(Store)); owner.Alive(); }
            FileStream Lock() => new FileStream(path + ".lock", FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            byte[] Mac(byte[] bytes) { using(var mac = new HMACSHA256(owner.macKey)) return mac.ComputeHash(binding.Concat(bytes).ToArray()); }
            byte[] ReadCore() {
                if(!File.Exists(path)) return null;
                long size = new FileInfo(path).Length; if(size < 72 || size > 33024) throw new InvalidOperationException("EphemeralIdentityCorrupt");
                var bytes = File.ReadAllBytes(path);
                if(bytes.Length < 8 + 16 + 16 + 32 || bytes.Length > 33024 || Encoding.ASCII.GetString(bytes, 0, 8) != "HOTR82T1") throw new InvalidOperationException("EphemeralIdentityCorrupt");
                var envelope = bytes.Take(bytes.Length - 32).ToArray(); var expected = Mac(envelope); int changed = 0;
                for(int n = 0; n < 32; n++) changed |= expected[n] ^ bytes[envelope.Length + n]; if(changed != 0) throw new InvalidOperationException("EphemeralIdentityCorrupt");
                using(var aes = Aes.Create()) { aes.Key = owner.sealKey; aes.Mode = CipherMode.CBC; aes.Padding = PaddingMode.PKCS7; aes.IV = bytes.Skip(8).Take(16).ToArray(); using(var decrypt = aes.CreateDecryptor()) { var plain = decrypt.TransformFinalBlock(bytes, 24, bytes.Length - 24 - 32); if(plain.Length < 1 || plain.Length > 32768) throw new InvalidOperationException("EphemeralIdentityCorrupt"); return plain; } }
            }
            public byte[] Read() { Alive(); using(Lock()) return ReadCore(); }
            public void CompareExchange(string expectedDigest, byte[] replacement) {
                Alive(); string temporary = null;
                try {
                    using(Lock()) {
                        var previous = ReadCore(); if((previous == null ? "" : IdentityProtocol82.Sha(previous)) != expectedDigest) throw new InvalidOperationException("IdentityRevisionConflict");
                        if(replacement == null) { if(File.Exists(path)) File.Delete(path); if(File.Exists(path + ".bak")) File.Delete(path + ".bak"); return; }
                        if(replacement.Length < 1 || replacement.Length > 32768) throw new ArgumentException("IdentityRecordSize"); byte[] envelope;
                        using(var aes = Aes.Create()) { aes.Key = owner.sealKey; aes.Mode = CipherMode.CBC; aes.Padding = PaddingMode.PKCS7; aes.GenerateIV(); using(var encrypt = aes.CreateEncryptor()) envelope = Encoding.ASCII.GetBytes("HOTR82T1").Concat(aes.IV).Concat(encrypt.TransformFinalBlock(replacement, 0, replacement.Length)).ToArray(); }
                        byte[] sealedRecord = envelope.Concat(Mac(envelope)).ToArray(); temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
                        using(var file = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None)) { file.Write(sealedRecord, 0, sealedRecord.Length); file.Flush(true); }
                        owner.VerificationCheckpoint?.Invoke("BeforeCommit"); if(File.Exists(path)) File.Replace(temporary, path, path + ".bak"); else File.Move(temporary, path); temporary = null; owner.VerificationCheckpoint?.Invoke("AfterCommit");
                    }
                } finally { if(temporary != null && File.Exists(temporary)) File.Delete(temporary); }
            }
            public void Dispose() { closed = true; }
        }
        public void Dispose() {
            if(disposed) return; disposed = true;
            if(key != IntPtr.Zero) BCryptDestroyKey(key); if(algorithm != IntPtr.Zero) BCryptCloseAlgorithmProvider(algorithm, 0); key = algorithm = IntPtr.Zero;
            Array.Clear(sealKey, 0, sealKey.Length); Array.Clear(macKey, 0, macKey.Length);
        }
    }
}
#endif
