#if DEVELOPMENT_BUILD || UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.Verification
{
    // Explicit harness invocation only. There is deliberately no automatic
    // startup/component and no normal credential/profile alias is accepted.
    public static class Identity82DeviceProbe
    {
        [Serializable] public sealed class Report {
            public string status, utc, stage, scopeHash, publicKeyHash, recordHash, unity;
            public int checks;
            public bool androidKeystore, privateKeyNonexportable, encryptionKeyNonexportable, hardwareBacked, recordExists;
            public string scope = "Actual explicit isolated QA Android JNI P256 signing and AES-GCM CAS journal stage; reopen is meaningful only when the harness records a distinct process. No hardware-attestation, OS power-loss, backend, normal-account or production integration claim.";
            public List<string> passed = new List<string>(), errors = new List<string>();
        }
        static void Check(Report report, bool condition, string label) { report.checks++; if(!condition) throw new InvalidOperationException(label); report.passed.Add(label); }
        public static IEnumerator RunStage(string isolatedScope, string stage, string outputDirectory, Action<Report> completed = null) {
            var report = new Report { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion, stage = stage };
            string output = null;
            try {
                if(isolatedScope == null || !Regex.IsMatch(isolatedScope, @"\Aqa82-[0-9a-f]{32}\z") || !new[] { "setup", "reopen", "clear" }.Contains(stage)) throw new InvalidOperationException("ExplicitQa82ScopeAndStageRequired");
                string allowed = Path.GetFullPath(Path.Combine(Application.persistentDataPath, "Identity82")) + Path.DirectorySeparatorChar;
                output = Path.GetFullPath(outputDirectory) + Path.DirectorySeparatorChar;
                if(!output.StartsWith(allowed, StringComparison.Ordinal)) throw new InvalidOperationException("IsolatedQa82OutputRequired");
                report.scopeHash = IdentityProtocol82.Sha(isolatedScope);
                using(var owner = new AndroidDeviceIdentity82(isolatedScope)) {
                    byte[] publicKey = owner.PublicSpkiDer(); report.publicKeyHash = IdentityProtocol82.Sha(publicKey); report.androidKeystore = owner.IsAndroidKeystore;
                    Check(report, report.androidKeystore && IdentityProtocol82.PublicKey(Convert.ToBase64String(publicKey)), "Android keystore P256 public SPKI");
                    byte[] message = Encoding.ASCII.GetBytes("public-noncredential-qa82-signature-check"); byte[] signature = owner.SignSha256Der(message);
                    Check(report, owner.VerifySha256Der(message, signature), "Actual Android DER signature verifies"); message[0] ^= 1; Check(report, !owner.VerifySha256Der(message, signature), "Changed message signature fails");
                    byte[] expected = Encoding.ASCII.GetBytes("public-noncredential-qa82-record-v1:" + isolatedScope), stored = owner.Read();
                    if(stage == "setup") { Check(report, stored == null, "Fresh isolated record absent"); owner.CompareExchange("", expected); stored = owner.Read(); Check(report, stored.SequenceEqual(expected), "Durable encrypted CAS readback"); }
                    else Check(report, stored != null && stored.SequenceEqual(expected), "Distinct-owner persisted record readback");
                    report.recordHash = IdentityProtocol82.Sha(stored);
                    bool conflict = false; try { owner.CompareExchange(new string('0', 64), expected); } catch(Exception) { conflict = true; }
                    Check(report, conflict && owner.Read().SequenceEqual(expected), "Stale CAS rejected without overwrite");
                    bool[] diagnostics = owner.Diagnostics(); Check(report, diagnostics != null && diagnostics.Length == 4, "Bounded keystore diagnostics");
                    report.privateKeyNonexportable = diagnostics[0]; report.encryptionKeyNonexportable = diagnostics[1]; report.hardwareBacked = diagnostics[3];
                    Check(report, diagnostics[0] && diagnostics[1] && diagnostics[2], "Private and encryption keys nonexportable with record present");
                    if(stage == "clear") { owner.CompareExchange(report.recordHash, null); Check(report, owner.Read() == null, "Explicit isolated encrypted record cleared"); Check(report, IdentityProtocol82.Sha(owner.PublicSpkiDer()) == report.publicKeyHash, "Signing key identity retained after credential clear"); }
                    report.recordExists = owner.Read() != null;
                }
            } catch(Exception error) { report.errors.Add(error is NotSupportedException ? "Android API26 keystore unavailable" : "Isolated device stage failed: " + error.GetType().Name); }
            report.status = report.errors.Count == 0 ? "PASS_NATIVE_ANDROID_IDENTITY82_" + stage.ToUpperInvariant() : "FAIL_NATIVE_ANDROID_IDENTITY82_STAGE";
            if(output != null) { Directory.CreateDirectory(output); File.WriteAllText(Path.Combine(output, "Identity82_" + stage + ".json"), JsonUtility.ToJson(report, true), new UTF8Encoding(false)); }
            completed?.Invoke(report); yield return null;
        }
    }
}
#endif
