"""Host parser/command safety tests only; no ADB, phone, SDK or backend calls."""
import json
import unittest
from types import SimpleNamespace
import read_device_telemetry02_127 as tool

def sample():
    row = {key: 0 for key in tool.COUNTERS | tool.BALANCES}
    row.update({key: False for key in tool.FLAGS})
    row.update(version=1, package=tool.PACKAGE, unit='demo-rewarded-yandex',
        engine='6000.3.27f1', phase='PendingRecovery', error='', actorDigest='a' * 64,
        utc='2026-10-31T13:31:07.1234567Z', walletRevision=1, claimedToday=0,
        remainingToday=3, cooldownSeconds=0, journalPhase='AfterCommit',
        receiptDigests=[], scope=tool.SCOPE)
    return row

class ParserSafety(unittest.TestCase):
    def encode(self, row):
        return json.dumps(row).encode()
    def test_known_snapshot_preserves_observations(self):
        row = sample(); row['coins'] = 1250; row['loadRequests'] = 1
        actual, redacted = tool.sanitize(self.encode(row))
        self.assertEqual(actual, row); self.assertFalse(redacted)
    def test_unknown_payload_field_is_rejected(self):
        row = sample(); row['accessToken'] = 'synthetic-private-field'
        with self.assertRaisesRegex(tool.Invalid, '^ExactTelemetryWhitelistRequired$'):
            tool.sanitize(self.encode(row))
    def test_duplicate_key_is_rejected(self):
        raw = self.encode(sample()).replace(b'"version": 1', b'"version": 1,"version": 1')
        with self.assertRaisesRegex(tool.Invalid, '^DuplicateTelemetryKey$'):
            tool.sanitize(raw)
    def test_unknown_error_is_redacted_not_exported(self):
        row = sample(); row['error'] = 'synthetic arbitrary payload / do not export'
        actual, redacted = tool.sanitize(self.encode(row))
        self.assertTrue(redacted); self.assertEqual(actual['error'], 'UnrecognizedCodeRedacted')
        self.assertNotIn('arbitrary payload', json.dumps(actual))
    def test_boolean_integer_coercion_is_rejected(self):
        row = sample(); row['coins'] = True
        with self.assertRaisesRegex(tool.Invalid, '^InvalidTelemetryInteger$'):
            tool.sanitize(self.encode(row))
    def test_raw_actor_or_receipt_is_rejected(self):
        for key, value in [('actorDigest', 'not-a-sha'), ('receiptDigests', ['raw-id'])]:
            row = sample(); row[key] = value
            with self.assertRaises(tool.Invalid): tool.sanitize(self.encode(row))
    def test_profile_phase_quota_and_bounds(self):
        for key, value in [('package', 'com.heartoftherain.game'), ('phase', 'access-token'),
                           ('remainingToday', 4), ('cooldownSeconds', 601),
                           ('walletRevision', 2**63), ('connected', 1)]:
            row = sample(); row[key] = value
            with self.assertRaises(tool.Invalid): tool.sanitize(self.encode(row))
    def test_oversize_and_invalid_date_are_rejected(self):
        with self.assertRaises(tool.Invalid): tool.sanitize(b' ' * (tool.MAX_BYTES + 1))
        row = sample(); row['utc'] = '2026-99-31T13:31:07.1234567Z'
        with self.assertRaises(tool.Invalid): tool.sanitize(self.encode(row))
    def test_comparison_reports_changes_without_inference(self):
        old = sample(); new = sample(); new.update(coins=400, rewardedSignals=1)
        result = tool.comparison(old, new)
        self.assertTrue(result['sameActorDigest']); self.assertEqual(result['coinsDelta'], 400)
        self.assertEqual(result['loadRequestsDelta'], 0); self.assertEqual(result['rewardedSignalsDelta'], 1)

class ReadCommandSafety(unittest.TestCase):
    def fake(self, before=None, after=None):
        expected = tool.PACKAGE + '/com.unity3d.player.UnityPlayerActivity'
        views = iter([before or expected, after or expected]); calls = []
        def adb(*args, **kwargs):
            calls.append((args, kwargs)); return SimpleNamespace(returncode=0, stdout=json.dumps(sample()).encode())
        return SimpleNamespace(phone=lambda: 'SYNTHETIC_NOT_DEVICE', foreground=lambda serial: next(views), adb=adb), calls
    def test_only_fixed_public_file_bounded_read_command(self):
        device, calls = self.fake(); tool.collect(device)
        self.assertEqual(calls, [(('-s', 'SYNTHETIC_NOT_DEVICE', 'exec-out', 'head', '-c', str(tool.MAX_BYTES + 1), tool.DEVICE_PATH), {'timeout': 15})])
    def test_wrong_foreground_reads_no_file(self):
        device, calls = self.fake(before='other.package/.Activity')
        with self.assertRaisesRegex(tool.Invalid, '^ExactDemoForegroundRequired$'): tool.collect(device)
        self.assertEqual(calls, [])
    def test_foreground_race_rejects_snapshot(self):
        device, _ = self.fake(after='other.package/.Activity')
        with self.assertRaisesRegex(tool.Invalid, '^DemoForegroundChangedDuringRead$'): tool.collect(device)
    def test_exit_zero_head_error_stdout_is_not_json_or_exported(self):
        device, _ = self.fake()
        device.adb = lambda *a, **k: SimpleNamespace(returncode=0, stdout=b'head: synthetic command failure\n')
        with self.assertRaisesRegex(tool.Invalid, '^PublicTelemetryReadCommandReportedError$'):
            tool.collect(device)
    def test_exit_zero_non_json_is_rejected(self):
        device, _ = self.fake()
        device.adb = lambda *a, **k: SimpleNamespace(returncode=0, stdout=b'synthetic non-JSON response')
        with self.assertRaisesRegex(tool.Invalid, '^PublicTelemetryJsonObjectRequired$'):
            tool.collect(device)
    def test_nonzero_read_and_oversize_are_rejected(self):
        device, _ = self.fake()
        device.adb = lambda *a, **k: SimpleNamespace(returncode=1, stdout=b'')
        with self.assertRaisesRegex(tool.Invalid, '^OwnPublicTelemetryReadFailed$'):
            tool.collect(device)
        device, _ = self.fake()
        device.adb = lambda *a, **k: SimpleNamespace(returncode=0, stdout=b'{' + b' ' * tool.MAX_BYTES)
        with self.assertRaisesRegex(tool.Invalid, '^BoundedTelemetryRequired$'):
            tool.collect(device)

if __name__ == '__main__':
    unittest.main()
