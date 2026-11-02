import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.Key;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.SecureRandom;
import java.security.Security;
import java.security.Signature;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.util.Arrays;
import java.util.Enumeration;

/**
 * Public certificate metadata and proof that the selected private key signs.
 * Dependency-free Java11 source. Password input is child-process environment only.
 * Never generates keys, writes the keystore, or prints private values/paths.
 */
public final class SigningProbe {
    private static final String PASSWORD_ENV = "HOTR_RELEASE_SIGNING_PASSWORD";
    private static final String SHA256_RSA_OID = "1.2.840.113549.1.1.11";
    private static final String HEX = "0123456789abcdef";

    private SigningProbe() {}

    private static final class ProbeFailure extends Exception {
        private final String reason;
        ProbeFailure(String reason) {
            super(reason);
            this.reason = reason;
        }
    }

    private static void require(boolean condition, String reason) throws ProbeFailure {
        if (!condition) {
            throw new ProbeFailure(reason);
        }
    }

    private static String hex(byte[] value) {
        StringBuilder result = new StringBuilder(value.length * 2);
        for (byte item : value) {
            int unsigned = item & 0xff;
            result.append(HEX.charAt(unsigned >>> 4));
            result.append(HEX.charAt(unsigned & 15));
        }
        return result.toString();
    }

    private static String quoted(String value) {
        StringBuilder result = new StringBuilder(value.length() + 2);
        result.append('"');
        for (int index = 0; index < value.length(); index++) {
            char item = value.charAt(index);
            switch (item) {
                case '"': result.append("\\\""); break;
                case '\\': result.append("\\\\"); break;
                case '\b': result.append("\\b"); break;
                case '\f': result.append("\\f"); break;
                case '\n': result.append("\\n"); break;
                case '\r': result.append("\\r"); break;
                case '\t': result.append("\\t"); break;
                default:
                    if (item < 0x20 || Character.isSurrogate(item)) {
                        result.append("\\u");
                        result.append(HEX.charAt((item >>> 12) & 15));
                        result.append(HEX.charAt((item >>> 8) & 15));
                        result.append(HEX.charAt((item >>> 4) & 15));
                        result.append(HEX.charAt(item & 15));
                    } else {
                        result.append(item);
                    }
            }
        }
        return result.append('"').toString();
    }

    private static String inspect(String storePath, String expectedAlias, char[] password)
            throws Exception {
        // The JDK compatibility loader otherwise accepts JKS under the PKCS12
        // name. Disable that fallback in this one short-lived probe process.
        Security.setProperty("keystore.type.compat", "false");
        KeyStore store = KeyStore.getInstance("PKCS12");
        try (InputStream input = Files.newInputStream(Path.of(storePath))) {
            store.load(input, password);
        } catch (Exception ignored) {
            throw new ProbeFailure("signing_probe_keystore_load_failed");
        }

        Enumeration<String> aliases = store.aliases();
        require(aliases.hasMoreElements(), "signing_probe_exactly_one_alias_required");
        String actualAlias = aliases.nextElement();
        require(!aliases.hasMoreElements(), "signing_probe_exactly_one_alias_required");
        require(actualAlias.equals(expectedAlias), "signing_probe_alias_mismatch");
        require(store.isKeyEntry(actualAlias), "signing_probe_private_key_required");

        Key key;
        try {
            key = store.getKey(actualAlias, password);
        } catch (Exception ignored) {
            throw new ProbeFailure("signing_probe_private_key_unavailable");
        }
        require(key instanceof PrivateKey && key instanceof RSAPrivateKey
                        && "RSA".equalsIgnoreCase(key.getAlgorithm()),
                "signing_probe_rsa_private_key_required");
        RSAPrivateKey privateKey = (RSAPrivateKey) key;
        int keySize = privateKey.getModulus().bitLength();
        require(keySize >= 3072, "signing_probe_rsa_3072_required");

        Certificate rawCertificate = store.getCertificate(actualAlias);
        require(rawCertificate instanceof X509Certificate, "signing_probe_x509_certificate_required");
        X509Certificate certificate = (X509Certificate) rawCertificate;
        require(SHA256_RSA_OID.equals(certificate.getSigAlgOID()),
                "signing_probe_sha256withrsa_certificate_required");
        require(certificate.getPublicKey() instanceof RSAPublicKey
                        && "RSA".equalsIgnoreCase(certificate.getPublicKey().getAlgorithm()),
                "signing_probe_rsa_certificate_required");
        RSAPublicKey publicKey = (RSAPublicKey) certificate.getPublicKey();
        require(privateKey.getModulus().equals(publicKey.getModulus()),
                "signing_probe_key_certificate_mismatch");
        try {
            certificate.checkValidity();
        } catch (Exception ignored) {
            throw new ProbeFailure("signing_probe_certificate_not_currently_valid");
        }
        require(certificate.getIssuerX500Principal().equals(certificate.getSubjectX500Principal()),
                "signing_probe_self_signed_certificate_required");
        try {
            certificate.verify(publicKey);
        } catch (Exception ignored) {
            throw new ProbeFailure("signing_probe_certificate_self_signature_failed");
        }

        SecureRandom random = new SecureRandom();
        byte[] challenge = new byte[32];
        byte[] signed = null;
        try {
            random.nextBytes(challenge);
            Signature signer = Signature.getInstance("SHA256withRSA");
            signer.initSign(privateKey, random);
            signer.update(challenge);
            signed = signer.sign();
            Signature verifier = Signature.getInstance("SHA256withRSA");
            verifier.initVerify(publicKey);
            verifier.update(challenge);
            require(verifier.verify(signed), "signing_probe_challenge_failed");
        } catch (ProbeFailure failure) {
            throw failure;
        } catch (Exception ignored) {
            throw new ProbeFailure("signing_probe_challenge_failed");
        } finally {
            Arrays.fill(challenge, (byte) 0);
            if (signed != null) {
                Arrays.fill(signed, (byte) 0);
            }
        }

        byte[] encoded = certificate.getEncoded();
        String sha1 = hex(MessageDigest.getInstance("SHA-1").digest(encoded));
        String sha256 = hex(MessageDigest.getInstance("SHA-256").digest(encoded));
        return "{\"alias\":" + quoted(actualAlias)
                + ",\"storeType\":\"PKCS12\""
                + ",\"keyAlgorithm\":\"RSA\""
                + ",\"keySize\":" + keySize
                + ",\"signatureAlgorithm\":\"SHA256withRSA\""
                + ",\"subject\":" + quoted(certificate.getSubjectX500Principal().getName())
                + ",\"serialHex\":" + quoted(certificate.getSerialNumber().toString(16))
                + ",\"notBeforeUtc\":" + quoted(certificate.getNotBefore().toInstant().toString())
                + ",\"notAfterUtc\":" + quoted(certificate.getNotAfter().toInstant().toString())
                + ",\"sha1\":" + quoted(sha1)
                + ",\"sha256\":" + quoted(sha256)
                + ",\"challengeVerified\":true}";
    }

    public static void main(String[] args) {
        char[] password = null;
        int exitCode = 0;
        try {
            require(args.length == 2, "signing_probe_two_arguments_required");
            require(!args[0].isBlank() && !args[1].isBlank(), "signing_probe_nonblank_arguments_required");
            String secret = System.getenv(PASSWORD_ENV);
            require(secret != null && !secret.isBlank(), "signing_probe_password_required");
            password = secret.toCharArray();
            String result = inspect(args[0], args[1], password);
            byte[] output = (result + "\n").getBytes(StandardCharsets.UTF_8);
            System.out.write(output, 0, output.length);
            System.out.flush();
            require(!System.out.checkError(), "signing_probe_public_output_failed");
        } catch (ProbeFailure failure) {
            System.err.println(failure.reason);
            exitCode = 1;
        } catch (Throwable ignored) {
            // Provider exceptions and malformed store inputs may contain secret
            // values or private paths. Never expose their messages or traces.
            System.err.println("signing_probe_failed");
            exitCode = 1;
        } finally {
            if (password != null) {
                Arrays.fill(password, '\0');
            }
        }
        if (exitCode != 0) {
            System.exit(exitCode);
        }
    }
}

