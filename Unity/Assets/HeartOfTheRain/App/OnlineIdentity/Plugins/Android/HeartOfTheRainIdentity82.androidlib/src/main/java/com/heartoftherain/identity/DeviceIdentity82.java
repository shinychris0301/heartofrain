package com.heartoftherain.identity;

import android.content.Context;
import android.os.Build;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyInfo;
import android.security.keystore.KeyProperties;
import android.util.AtomicFile;
import android.util.Base64;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.RandomAccessFile;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.spec.ECGenParameterSpec;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;

/** Explicit account owner only. No activity, service, provider or bootstrap.
 * Never logs keys, plaintext, tokens, signatures or server responses. */
public final class DeviceIdentity82 {
    private static final int LIMIT = 32768;
    private static final long MAGIC = 0x484f545249443832L; // HOTRID82
    private final File record, lockFile;
    private final AtomicFile atomic;
    private final String signingAlias, encryptionAlias;
    private final byte[] aad;
    private boolean closed;

    public DeviceIdentity82(Context context, String scope) {
        if (Build.VERSION.SDK_INT < 26) throw failure("IdentityApi26Required");
        if (context == null || scope == null || !scope.matches("[a-z][a-z0-9.-]{0,63}")) throw failure("InvalidIdentityScope");
        Context app = context.getApplicationContext();
        File directory = new File(app.getNoBackupFilesDir(), "hotr-identity82");
        if (!directory.isDirectory() && !directory.mkdirs()) throw failure("IdentityStorageUnavailable");
        record = new File(directory, scope + ".sealed");
        lockFile = new File(directory, scope + ".lock");
        atomic = new AtomicFile(record);
        String binding = app.getPackageName() + "|" + scope + "|hotr-managed-identity-v1";
        signingAlias = "hotr.identity82.sign." + scope;
        encryptionAlias = "hotr.identity82.seal." + scope;
        aad = binding.getBytes(StandardCharsets.UTF_8);
    }
    private static IllegalStateException failure(String code) { return new IllegalStateException(code); }
    private void alive() { if (closed) throw failure("IdentityOwnerClosed"); }
    private boolean hasRecord() { return record.exists() || new File(record.getPath() + ".bak").exists(); }
    private KeyStore keystore() throws Exception { KeyStore store = KeyStore.getInstance("AndroidKeyStore"); store.load(null); return store; }
    private KeyStore signingKey() throws Exception {
        KeyStore store = keystore();
        if (!store.containsAlias(signingAlias)) {
            if (hasRecord()) throw failure("IdentityDeviceKeyMissing");
            KeyPairGenerator generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore");
            generator.initialize(new KeyGenParameterSpec.Builder(signingAlias, KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                .setAlgorithmParameterSpec(new ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256).build());
            generator.generateKeyPair(); store = keystore();
        }
        return store;
    }
    private SecretKey encryptionKey(boolean create) throws Exception {
        KeyStore store = keystore();
        if (!store.containsAlias(encryptionAlias)) {
            if (!create || hasRecord()) throw failure("IdentityEncryptionKeyMissing");
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(encryptionAlias, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true).setKeySize(256).build());
            generator.generateKey(); store = keystore();
        }
        return (SecretKey) store.getKey(encryptionAlias, null);
    }
    private final class Lock implements AutoCloseable {
        private final RandomAccessFile file;
        private final FileLock held;
        Lock() throws Exception {
            file = new RandomAccessFile(lockFile, "rw");
            FileLock candidate;
            try { candidate = file.getChannel().tryLock(); }
            catch (Exception error) { file.close(); throw failure("IdentityStorageBusy"); }
            if (candidate == null) { file.close(); throw failure("IdentityStorageBusy"); }
            held = candidate;
        }
        public void close() throws Exception { try { held.release(); } finally { file.close(); } }
    }
    private static String encode(byte[] value) { return Base64.encodeToString(value, Base64.NO_WRAP); }
    private static byte[] decode(String value, int maximum) {
        if (value == null || value.length() > maximum * 2) throw failure("InvalidIdentityEncoding");
        byte[] decoded;
        try { decoded = Base64.decode(value, Base64.DEFAULT); }
        catch (Exception error) { throw failure("InvalidIdentityEncoding"); }
        if (decoded.length > maximum || !encode(decoded).equals(value)) throw failure("InvalidIdentityEncoding");
        return decoded;
    }
    private static String digest(byte[] data) throws Exception {
        if (data == null) return "";
        byte[] result = MessageDigest.getInstance("SHA-256").digest(data); StringBuilder text = new StringBuilder(64);
        for (byte b : result) text.append(String.format(java.util.Locale.ROOT, "%02x", b & 255)); return text.toString();
    }
    public synchronized String publicKeySpki() {
        alive();
        try (Lock ignored = new Lock()) { return encode(signingKey().getCertificate(signingAlias).getPublicKey().getEncoded()); }
        catch (Exception error) { throw failure("IdentityDeviceKeyUnavailable"); }
    }
    public synchronized String signSha256Der(String message) {
        alive(); byte[] bytes = decode(message, 4096);
        try (Lock ignored = new Lock()) {
            PrivateKey key = (PrivateKey) signingKey().getKey(signingAlias, null);
            if (key.getEncoded() != null) throw failure("ExportableDeviceKeyRejected");
            Signature signature = Signature.getInstance("SHA256withECDSA"); signature.initSign(key); signature.update(bytes); return encode(signature.sign());
        } catch (Exception error) { throw failure("IdentitySigningUnavailable"); }
    }
    public synchronized boolean verifySha256Der(String message, String encodedSignature) {
        alive();
        try (Lock ignored = new Lock()) {
            byte[] bytes = decode(message, 4096), signed = decode(encodedSignature, 80);
            Signature verifier = Signature.getInstance("SHA256withECDSA");
            verifier.initVerify(signingKey().getCertificate(signingAlias).getPublicKey()); verifier.update(bytes);
            return verifier.verify(signed);
        } catch (Exception error) { return false; }
    }
    private byte[] readLocked() throws Exception {
        if (!hasRecord()) return null;
        byte[] sealed;
        try (FileInputStream input = atomic.openRead(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096]; int count;
            while ((count = input.read(buffer)) != -1) { if (output.size() + count > LIMIT + 128) throw failure("IdentityRecordOversize"); output.write(buffer, 0, count); }
            sealed = output.toByteArray();
        }
        try (DataInputStream input = new DataInputStream(new ByteArrayInputStream(sealed))) {
            if (input.readLong() != MAGIC || input.readUnsignedByte() != 1 || input.readUnsignedByte() != 12) throw failure("IdentityRecordCorrupt");
            byte[] iv = new byte[12]; input.readFully(iv); int size = input.readInt();
            if (size < 16 || size > LIMIT + 16 || input.available() != size) throw failure("IdentityRecordCorrupt");
            byte[] cipherText = new byte[size]; input.readFully(cipherText);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.DECRYPT_MODE, encryptionKey(false), new GCMParameterSpec(128, iv)); cipher.updateAAD(aad);
            byte[] plain = cipher.doFinal(cipherText); if (plain.length < 1 || plain.length > LIMIT) throw failure("IdentityRecordCorrupt"); return plain;
        }
    }
    public synchronized String readProtected() {
        alive();
        try (Lock ignored = new Lock()) { byte[] value = readLocked(); return value == null ? null : encode(value); }
        catch (Exception error) { throw failure("IdentityProtectedReadUnavailable"); }
    }
    public synchronized void compareExchange(String expectedDigest, String replacement) {
        alive();
        if (expectedDigest == null || !(expectedDigest.length() == 0 || expectedDigest.matches("[0-9a-f]{64}"))) throw failure("InvalidIdentityRevision");
        byte[] plain = replacement == null ? null : decode(replacement, LIMIT);
        if (plain != null && plain.length == 0) throw failure("InvalidIdentityRecord");
        try (Lock ignored = new Lock()) {
            if (!MessageDigest.isEqual(expectedDigest.getBytes(StandardCharsets.US_ASCII), digest(readLocked()).getBytes(StandardCharsets.US_ASCII))) throw failure("IdentityRevisionConflict");
            if (plain == null) {
                atomic.delete(); KeyStore store = keystore(); if (store.containsAlias(encryptionAlias)) store.deleteEntry(encryptionAlias); return;
            }
            // Key creation happens only for a truly absent record; missing
            // existing keys never result in silent regeneration/new identity.
            signingKey(); Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.ENCRYPT_MODE, encryptionKey(true)); cipher.updateAAD(aad);
            byte[] cipherText = cipher.doFinal(plain), iv = cipher.getIV(); if (iv.length != 12) throw failure("InvalidIdentityIv");
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (DataOutputStream data = new DataOutputStream(bytes)) { data.writeLong(MAGIC); data.writeByte(1); data.writeByte(iv.length); data.write(iv); data.writeInt(cipherText.length); data.write(cipherText); }
            FileOutputStream stream = null;
            try { stream = atomic.startWrite(); stream.write(bytes.toByteArray()); stream.getFD().sync(); atomic.finishWrite(stream); stream = null; }
            finally { if (stream != null) atomic.failWrite(stream); }
        } catch (Exception error) { throw failure("IdentityProtectedWriteUnavailable"); }
    }
    public synchronized boolean[] diagnostics() {
        alive();
        try (Lock ignored = new Lock()) {
            KeyStore store = signingKey(); PrivateKey key = (PrivateKey) store.getKey(signingAlias, null);
            boolean aesNonexportable = !store.containsAlias(encryptionAlias) || store.getKey(encryptionAlias, null).getEncoded() == null;
            boolean hardware = false;
            try { java.security.KeyFactory factory = java.security.KeyFactory.getInstance(key.getAlgorithm(), "AndroidKeyStore"); hardware = factory.getKeySpec(key, KeyInfo.class).isInsideSecureHardware(); } catch (Exception ignoredHardware) { }
            return new boolean[] { key.getEncoded() == null, aesNonexportable, hasRecord(), hardware };
        } catch (Exception error) { throw failure("IdentityDiagnosticsUnavailable"); }
    }
    public synchronized void close() { closed = true; }
}
