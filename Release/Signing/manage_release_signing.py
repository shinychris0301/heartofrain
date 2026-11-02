"""Developer-owned Windows release signing; never writes a password to stdout.

Private material belongs outside the checkout. Public certificates may be
committed. The portable backup is a password-encrypted PKCS#12 keystore; its
password must also be retained independently of this Windows account.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ALIAS = "heartoftherain-release"
KEYSTORE = "heartoftherain-release.keystore"
SECRET = "password.dpapi"
PUBLIC = "certificate.json"
PASSWORD_ENV = "HOTR_RELEASE_SIGNING_PASSWORD"
REPO = Path(__file__).resolve().parents[2]
PROBE = Path(__file__).with_name("SigningProbe.java")
PUBLISHED_CERTIFICATE = Path(__file__).with_name("release-certificate.json")


class SigningError(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise SigningError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, value):
    write_new(path, (json.dumps(value, indent=2) + "\n").encode("utf-8"))


def outside_repo(path):
    original = Path(path).expanduser().absolute()
    for part in (original, *original.parents):
        if part.exists() or part.is_symlink():
            require(not part.is_symlink()
                    and not getattr(part.lstat(), "st_file_attributes", 0) & 0x400,
                    "ReparsePathsAreNotSigningCustody")
    value = original.resolve()
    require(value != REPO and REPO not in value.parents,
            "PrivateMaterialMustBeOutsideRepository")
    return value


def run(command, password=None):
    env = os.environ.copy()
    env.pop(PASSWORD_ENV, None)
    if password is not None:
        env[PASSWORD_ENV] = password
    result = subprocess.run([str(part) for part in command], env=env,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=90,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    # Tool diagnostics are deliberately not forwarded: never expose a secret
    # if a Java/tool version unexpectedly includes one in its diagnostics.
    require(result.returncode == 0, "SigningToolFailed_" + str(result.returncode))
    return result.stdout


def owner_sid():
    rows = list(csv.reader(run(["whoami.exe", "/user", "/fo", "csv", "/nh"])
                           .decode("utf-8", errors="replace").strip().splitlines()))
    require(len(rows) == 1 and len(rows[0]) == 2 and rows[0][1].startswith("S-1-"),
            "CurrentWindowsOwnerNotResolved")
    return rows[0][1]


def private_directory(path):
    path = outside_repo(path)
    require(not path.exists(), "RefusingExistingPrivateDirectory")
    path.mkdir(parents=True, exist_ok=False)
    run(["icacls.exe", path, "/inheritance:r", "/grant:r",
         "*" + owner_sid() + ":(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"])
    return path


class Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def dpapi(data, decrypt=False):
    crypt = ctypes.WinDLL("crypt32.dll", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32.dll", use_last_error=True)
    kernel.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel.LocalFree.restype = wintypes.HLOCAL
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    if decrypt:
        method = crypt.CryptUnprotectData
        method.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                           ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                           ctypes.POINTER(Blob)]
        args = [ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)]
    else:
        method = crypt.CryptProtectData
        method.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p,
                           ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                           ctypes.POINTER(Blob)]
        args = [ctypes.byref(source), "Heart of the Rain release signing", None,
                None, None, 1, ctypes.byref(output)]
    method.restype = wintypes.BOOL
    require(bool(method(*args)), "WindowsCurrentUserSecretProtectionFailed")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel.LocalFree(ctypes.cast(output.pbData, wintypes.HLOCAL))


def tools(jdk):
    directory = Path(jdk).resolve()
    java, keytool = directory / "bin/java.exe", directory / "bin/keytool.exe"
    require(java.is_file() and keytool.is_file(), "ExplicitExistingJdkRequired")
    return java, keytool


def probe(jdk, keystore, password):
    java, _ = tools(jdk)
    value = json.loads(run([java, "--source", "11", PROBE, keystore, ALIAS], password))
    require(value.get("alias") == ALIAS and value.get("storeType") == "PKCS12"
            and value.get("challengeVerified") is True
            and value.get("keyAlgorithm") == "RSA" and value.get("keySize", 0) >= 3072
            and value.get("signatureAlgorithm") == "SHA256withRSA",
            "ReleasePrivateKeyChallengeFailed")
    return value


def public_record(root):
    record = json.loads((root / PUBLIC).read_text("utf-8"))
    require(record["alias"] == ALIAS and record["packageName"] == "com.heartoftherain.game"
            and record["keystoreFile"] == KEYSTORE, "UnexpectedSigningDescriptor")
    if PUBLISHED_CERTIFICATE.exists():
        published = json.loads(PUBLISHED_CERTIFICATE.read_text("utf-8"))
        require(record["sha256"] == published["sha256"]
                and record["sha1"] == published["sha1"], "NotThePublishedReleaseSigningIdentity")
    return record


def verify(root, jdk, password, compat_jdk=None):
    root = outside_repo(root)
    record = public_record(root)
    require(sha(root / KEYSTORE) == record["keystoreSHA256"], "KeystoreBytesDoNotMatchDescriptor")
    der = (root / "certificate.der").read_bytes()
    require(hashlib.sha256(der).hexdigest() == record["sha256"]
            and hashlib.sha1(der).hexdigest() == record["sha1"], "PublicDerDoesNotMatchDescriptor")
    pem = (root / "certificate.pem").read_text("ascii")
    import ssl
    require(ssl.PEM_cert_to_DER_cert(pem) == der, "PublicPemDoesNotMatchDer")
    observed = probe(jdk, root / KEYSTORE, password)
    require(observed["sha256"] == record["sha256"] and observed["sha1"] == record["sha1"],
            "CertificateDoesNotMatchDescriptor")
    if compat_jdk:
        compatible = probe(compat_jdk, root / KEYSTORE, password)
        require(compatible == observed, "OtherJdkCannotUseSamePrivateSigningKey")
    return record


def local_password(root):
    return dpapi((outside_repo(root) / SECRET).read_bytes(), decrypt=True).decode("ascii")


def backup(root, destination, jdk, password, compat_jdk=None):
    record = verify(root, jdk, password, compat_jdk)
    target = private_directory(destination)
    for filename in (KEYSTORE, PUBLIC, "certificate.der", "certificate.pem"):
        write_new(target / filename, (root / filename).read_bytes())
    # No DPAPI file in a portable backup. It is usable on a different account
    # only when the owner independently retains the PKCS#12 password.
    restored = verify(target, jdk, password, compat_jdk)
    require(restored == record, "PortableBackupVerificationFailed")
    receipt = {"schemaVersion": 1, "utc": datetime.now(timezone.utc).isoformat(),
               "status": "LOCAL_PORTABLE_BACKUP_PRIVATE_KEY_VERIFIED",
               "sha256": record["sha256"], "keystoreSHA256": record["keystoreSHA256"],
               "offDeviceCopyVerified": False, "independentPasswordEscrowVerified": False}
    write_json(target / "backup-receipt.json", receipt)
    return target


def create(args):
    require(not PUBLISHED_CERTIFICATE.exists(), "ReleaseSigningIdentityAlreadyEstablished")
    _, keytool = tools(args.jdk)
    if args.compat_jdk:
        tools(args.compat_jdk)
    source, target = outside_repo(args.root), outside_repo(args.backup)
    require(not source.exists() and not target.exists(), "RefusingExistingSigningMaterial")
    require(source != target and source not in target.parents and target not in source.parents,
            "SeparateLocalBackupDirectoryRequired")
    root = private_directory(args.root)
    password = secrets.token_urlsafe(32)
    # Persist protected recovery before keytool; a failure never destroys the
    # only password for a partially generated durable keystore.
    write_new(root / SECRET, dpapi(password.encode("ascii")))
    run([keytool,
         "-J-Dkeystore.pkcs12.keyProtectionAlgorithm=PBEWithHmacSHA256AndAES_256",
         "-J-Dkeystore.pkcs12.certProtectionAlgorithm=PBEWithHmacSHA256AndAES_256",
         "-J-Dkeystore.pkcs12.macAlgorithm=HmacPBESHA256",
         "-J-Dkeystore.pkcs12.keyPbeIterationCount=100000",
         "-J-Dkeystore.pkcs12.certPbeIterationCount=100000",
         "-J-Dkeystore.pkcs12.macIterationCount=100000",
         "-genkeypair", "-noprompt", "-storetype", "PKCS12", "-keystore", root / KEYSTORE,
         "-alias", ALIAS, "-keyalg", "RSA", "-keysize", "3072", "-sigalg", "SHA256withRSA",
         "-validity", "10000", "-startdate", "-1d", "-dname", "CN=Heart of the Rain Release",
         "-storepass:env", PASSWORD_ENV, "-keypass:env", PASSWORD_ENV], password)
    observed = probe(args.jdk, root / KEYSTORE, password)
    for filename, rfc in (("certificate.der", False), ("certificate.pem", True)):
        command = [keytool, "-exportcert", "-keystore", root / KEYSTORE,
                   "-storetype", "PKCS12", "-alias", ALIAS, "-storepass:env", PASSWORD_ENV,
                   "-file", root / filename]
        if rfc:
            command.append("-rfc")
        run(command, password)
    der = (root / "certificate.der").read_bytes()
    require(hashlib.sha256(der).hexdigest() == observed["sha256"]
            and hashlib.sha1(der).hexdigest() == observed["sha1"], "ExportedPublicCertificateMismatch")
    record = dict(observed, schemaVersion=1, packageName="com.heartoftherain.game",
                  consoleApplicationId="2063777840", keystoreFile=KEYSTORE,
                  keystoreSHA256=sha(root / KEYSTORE),
                  createdUtc=datetime.now(timezone.utc).isoformat(),
                  purpose="Developer-owned future release signing identity",
                  androidApkSigned=False)
    write_json(root / PUBLIC, record)
    verified = verify(root, args.jdk, local_password(root), args.compat_jdk)
    target = backup(root, outside_repo(args.backup), args.jdk, password, args.compat_jdk)
    return {"status": "RELEASE_SIGNING_IDENTITY_CREATED_AND_LOCAL_BACKUP_VERIFIED",
            "root": str(root), "backup": str(target), "certificate": verified,
            "offDeviceCopyVerified": False, "independentPasswordEscrowVerified": False}


def restore_from_backup(source, target, password, jdk, compat_jdk=None):
    # This function uses ONLY the portable backup and an owner-supplied password.
    # No access to an original primary directory or DPAPI source is needed.
    source = outside_repo(source)
    record = verify(source, jdk, password, compat_jdk)
    target = private_directory(target)
    for filename in (KEYSTORE, PUBLIC, "certificate.der", "certificate.pem"):
        write_new(target / filename, (source / filename).read_bytes())
    write_new(target / SECRET, dpapi(password.encode("ascii")))
    verify(target, jdk, local_password(target), compat_jdk)
    return {"status": "RESTORED_TO_NEW_PRIVATE_DIRECTORY", "root": str(target), "sha256": record["sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify", "backup", "verify-backup", "restore", "show-password"))
    parser.add_argument("--root", required=True, help="Private custody directory outside this repository")
    parser.add_argument("--jdk", help="Existing JDK with keytool and source-launching java")
    parser.add_argument("--compat-jdk", help="Second existing JDK for private-key compatibility verification")
    parser.add_argument("--backup", help="New portable backup directory, or existing backup to verify/restore")
    args = parser.parse_args()
    require(os.name == "nt", "WindowsCurrentUserCustodyRequired")
    root = outside_repo(args.root)
    if args.command == "show-password":
        # Invoked explicitly by the owner only. Never call this from automation
        # or a captured shell; nothing sensitive is written to stdout/clipboard.
        message = ("Save this password in your own password manager and independent recovery storage.\n"
                   "It opens the release keystore and its portable backup.\n\n" + local_password(root))
        ctypes.windll.user32.MessageBoxW(None, message, "Heart of the Rain - private release password", 0x40)
        return {"status": "OWNER_PASSWORD_DIALOG_CLOSED_NO_SECRET_OUTPUT"}
    require(args.jdk is not None, "ExplicitExistingJdkRequired")
    if args.command == "create":
        require(args.backup is not None, "SeparateLocalBackupDirectoryRequired")
        return create(args)
    if args.command in ("verify", "backup", "verify-backup"):
        password = local_password(root)
        if args.command == "verify":
            certificate = verify(root, args.jdk, password, args.compat_jdk)
            return {"status": "PRIVATE_KEY_VERIFIED", "certificate": certificate}
        require(args.backup is not None, "BackupDirectoryRequired")
        if args.command == "backup":
            target = backup(root, outside_repo(args.backup), args.jdk, password, args.compat_jdk)
            return {"status": "LOCAL_PORTABLE_BACKUP_VERIFIED", "backup": str(target)}
        value = verify(outside_repo(args.backup), args.jdk, password, args.compat_jdk)
        require(value["sha256"] == public_record(root)["sha256"], "BackupNotForCurrentReleaseIdentity")
        return {"status": "PORTABLE_BACKUP_PRIVATE_KEY_VERIFIED", "sha256": value["sha256"]}
    # Restore works independently of DPAPI: ask for the escrowed password at a
    # real interactive terminal, then bind it to the new Windows current user.
    require(args.backup is not None and sys.stdin.isatty(), "InteractiveOwnerRestoreRequired")
    source = outside_repo(args.backup)
    password = getpass.getpass("Release keystore password (hidden): ")
    return restore_from_backup(source, root, password, args.jdk, args.compat_jdk)


if __name__ == "__main__":
    try:
        print(json.dumps(main(), indent=2))
    except SigningError as error:
        print("Release signing operation stopped: " + str(error), file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        # No tracebacks or raw tool errors: they may contain caller input or
        # diagnostic data. Preserve all existing material for owner recovery.
        print("Release signing operation failed; existing material was preserved.", file=sys.stderr)
        sys.exit(1)
