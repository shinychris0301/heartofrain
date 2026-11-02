"""Custody/recovery failure checks against the actual local release identity.

Run only after creation, with HOTR_SIGNING_TEST_ROOT/BACKUP/JDK/COMPAT_JDK.
No passwords, private keys or decrypted recovery data are printed or persisted.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import uuid

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("release_signing", REPO / "Release/Signing/manage_release_signing.py")
signing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signing)


class ReleaseCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary = Path(os.environ["HOTR_SIGNING_TEST_ROOT"]).resolve()
        cls.backup = Path(os.environ["HOTR_SIGNING_TEST_BACKUP"]).resolve()
        cls.jdk = Path(os.environ["HOTR_SIGNING_TEST_JDK"])
        cls.compat = Path(os.environ["HOTR_SIGNING_TEST_COMPAT_JDK"])
        cls.primary_hash = signing.sha(cls.primary / signing.KEYSTORE)
        cls.backup_hash = signing.sha(cls.backup / signing.KEYSTORE)

    def setUp(self):
        temp = Path(tempfile.gettempdir()).resolve()
        self.work = signing.private_directory(temp / ("HOTRSigningCheck_" + uuid.uuid4().hex))
        self.assertEqual(self.work.parent, temp)

    def tearDown(self):
        # Only the exact private fixture created by this case is removed.
        # No recursive shell command and no traversal outside its resolved root.
        root = self.work.resolve()
        self.assertEqual(root.parent, Path(tempfile.gettempdir()).resolve())
        self.assertTrue(root.name.startswith("HOTRSigningCheck_"))
        for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            self.assertTrue(path.resolve().is_relative_to(root))
            path.rmdir() if path.is_dir() else path.unlink()
        root.rmdir()
        self.assertEqual(signing.sha(self.primary / signing.KEYSTORE), self.primary_hash)
        self.assertEqual(signing.sha(self.backup / signing.KEYSTORE), self.backup_hash)

    def copy_backup(self):
        target = signing.private_directory(self.work / "backup")
        for name in (signing.KEYSTORE, signing.PUBLIC, "certificate.der", "certificate.pem"):
            signing.write_new(target / name, (self.backup / name).read_bytes())
        return target

    def test_repository_cannot_receive_private_material(self):
        with self.assertRaises(signing.SigningError):
            signing.outside_repo(REPO / ".verification-cache/unsafe-signing-root")

    def test_existing_file_cannot_be_overwritten(self):
        target = self.work / "sentinel"
        signing.write_new(target, b"preserve")
        with self.assertRaises(FileExistsError):
            signing.write_new(target, b"replacement")
        self.assertEqual(target.read_bytes(), b"preserve")

    def test_create_refuses_existing_primary_before_secret_generation(self):
        args = argparse.Namespace(root=self.primary, backup=self.work / "new-backup",
                                  jdk=self.jdk, compat_jdk=self.compat)
        with mock.patch.object(signing, "PUBLISHED_CERTIFICATE", self.work / "not-yet-published.json"), mock.patch.object(signing.secrets, "token_urlsafe", side_effect=AssertionError("MustNotGenerateReplacementPassword")):
            with self.assertRaises(signing.SigningError):
                signing.create(args)
        self.assertFalse((self.work / "new-backup").exists())

    def test_published_identity_blocks_accidental_replacement_key(self):
        args = argparse.Namespace(root=self.work / "new-custody", backup=self.work / "new-backup",
                                  jdk=self.jdk, compat_jdk=self.compat)
        with self.assertRaisesRegex(signing.SigningError, "ReleaseSigningIdentityAlreadyEstablished"):
            signing.create(args)
        self.assertFalse((self.work / "new-custody").exists())

    def test_dpapi_tamper_is_rejected(self):
        secret = secrets.token_bytes(32)
        sealed = signing.dpapi(secret)
        self.assertNotEqual(sealed, secret)
        self.assertTrue(signing.dpapi(sealed, decrypt=True) == secret, "Protected fixture did not round-trip")
        damaged = sealed[:-1] + bytes([sealed[-1] ^ 1])
        with self.assertRaises(signing.SigningError):
            signing.dpapi(damaged, decrypt=True)

    def test_wrong_backup_password_cannot_use_private_key(self):
        with self.assertRaises(signing.SigningError):
            signing.probe(self.jdk, self.backup / signing.KEYSTORE, secrets.token_urlsafe(32))

    def test_corrupt_backup_rejected_before_private_key_use(self):
        target = self.copy_backup()
        path = target / signing.KEYSTORE
        data = path.read_bytes()
        path.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        with mock.patch.object(signing, "probe", side_effect=AssertionError("CorruptBytesMustNotReachSigner")):
            with self.assertRaises(signing.SigningError):
                signing.verify(target, self.jdk, "unused")

    def test_wrong_public_certificate_is_rejected(self):
        target = self.copy_backup()
        der = target / "certificate.der"
        der.write_bytes(b"wrong public certificate")
        with mock.patch.object(signing, "probe", side_effect=AssertionError("WrongCertificateMustNotReachSigner")):
            with self.assertRaises(signing.SigningError):
                signing.verify(target, self.jdk, "unused")

    def test_substituted_release_identity_is_rejected(self):
        target = self.copy_backup()
        descriptor = target / signing.PUBLIC
        value = json.loads(descriptor.read_text("utf-8"))
        value["sha256"] = "f" * 64
        descriptor.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(signing.SigningError, "NotThePublishedReleaseSigningIdentity"):
            signing.verify(target, self.jdk, "unused")

    def test_portable_restore_uses_only_backup_and_password(self):
        password = signing.local_password(self.primary)
        target = self.work / "restored"
        original_read_bytes = Path.read_bytes
        original_read_text = Path.read_text

        def bytes_without_primary(path):
            if path.resolve().is_relative_to(self.primary):
                raise AssertionError("RestoreMustNotReadOriginalCustody")
            return original_read_bytes(path)

        def text_without_primary(path, *args, **kwargs):
            if path.resolve().is_relative_to(self.primary):
                raise AssertionError("RestoreMustNotReadOriginalCustody")
            return original_read_text(path, *args, **kwargs)

        with mock.patch.object(Path, "read_bytes", bytes_without_primary), mock.patch.object(Path, "read_text", text_without_primary):
            result = signing.restore_from_backup(self.backup, target, password, self.jdk, self.compat)
        self.assertEqual(result["status"], "RESTORED_TO_NEW_PRIVATE_DIRECTORY")
        self.assertEqual(signing.sha(target / signing.KEYSTORE), self.backup_hash)
        self.assertTrue(signing.local_password(target) == password, "Restored password does not match")
        self.assertEqual(result["sha256"], signing.public_record(self.backup)["sha256"])

    def test_existing_restore_destination_is_preserved(self):
        password = signing.local_password(self.primary)
        target = signing.private_directory(self.work / "already-owned")
        signing.write_new(target / "sentinel", b"preserve")
        with self.assertRaises(signing.SigningError):
            signing.restore_from_backup(self.backup, target, password, self.jdk)
        self.assertEqual((target / "sentinel").read_bytes(), b"preserve")
        self.assertFalse((target / signing.SECRET).exists())

    def test_both_jdks_and_cli_return_public_data_only(self):
        password = signing.local_password(self.primary)
        certificate = signing.verify(self.primary, self.jdk, password, self.compat)
        command = [sys.executable, "-B", str(REPO / "Release/Signing/manage_release_signing.py"),
                   "verify", "--root", str(self.primary), "--jdk", str(self.jdk), "--compat-jdk", str(self.compat)]
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(password.encode("ascii") in result.stdout + result.stderr,
                         "Secret appeared in captured output; captured data withheld")
        self.assertEqual(json.loads(result.stdout)["certificate"], certificate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
