"""Real SQLite + ownership/receipt failure boundaries; no listener or provider."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from hotr_backend.operations import OperationError
from hotr_backend.staging105 import (StagingError, complete_restore, initialize_owned_data,
                                    manifest_for_data_directory, owned_database,
                                    ownership_metadata, read_manifest)
from hotr_backend.staging_ops105 import StagingOpsError, backup_staging, main, restore_staging
from hotr_backend.storage import Database, SCHEMA_VERSION


class StagingOps105Tests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {k: v for k, v in os.environ.items() if not k.startswith('HOTR_')}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.temporary = tempfile.TemporaryDirectory(prefix='hotr-staging-ops105-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest_path = self.root / 'manifest.json'
        self.manifest_path.write_text(json.dumps({
            'version': 1, 'mode': 'staging', 'publicOrigin': 'https://staging.ops105-fixture.net',
            'identityScope': 'review-ops105-fixture', 'deploymentId': 'ops-fixture105',
            'dataDirectory': str(self.root / 'authority'), 'port': 0,
            'vk': {'enabled': False, 'clientId': '', 'redirectUri': ''},
            'replay': {'enabled': False, 'bundle': '', 'approvalFile': '', 'approvalSHA256': ''}}), encoding='utf-8')
        self.manifest = read_manifest(self.manifest_path)
        self.make_ready(self.manifest)

    @staticmethod
    def make_ready(manifest):
        # Explicit disposable restore fixture, using the real initializer and
        # current model schema; no manual ownership-marker forgery.
        initialize_owned_data(manifest, restore_pending=True)
        database = Database(manifest.data_directory / 'authority.sqlite3')
        with database.transaction() as connection:
            connection.execute('UPDATE clock_state SET high_water=105105 WHERE id=1')
        complete_restore(manifest)

    def snapshot(self, name='snapshot'):
        return self.manifest.data_directory / 'backups' / (name + '.sqlite3')

    def receipt(self, name='snapshot'):
        return self.manifest.data_directory / 'backups' / (name + '.receipt.json')

    def target(self, tag='restored'):
        return self.manifest.data_directory / 'restores' / tag

    def test_online_wal_backup_and_owned_new_restore_keep_model(self):
        source = owned_database(self.manifest)
        with contextlib.closing(sqlite3.connect(source, isolation_level=None)) as keeper:
            keeper.execute('PRAGMA journal_mode=WAL')
            keeper.execute('UPDATE clock_state SET high_water=105999 WHERE id=1')
            self.assertGreater(Path(str(source) + '-wal').stat().st_size, 0)
            result = backup_staging(self.manifest_path, 'snapshot')
            proof = json.loads(self.receipt().read_bytes())
            self.assertEqual((result['operation'], result['schemaVersion'], proof['state']), ('staging_backup', SCHEMA_VERSION, 'Ready'))
            self.assertEqual(proof['nonce'], ownership_metadata(self.manifest)['nonce'])
            restored = restore_staging(self.manifest, 'snapshot', 'restored')
            self.assertFalse(restored['activationPerformed'] or restored['descriptorWritten'])
            new_manifest = manifest_for_data_directory(self.manifest, self.target())
            self.assertEqual(ownership_metadata(new_manifest)['state'], 'Ready')
            with contextlib.closing(sqlite3.connect(owned_database(new_manifest))) as db:
                self.assertEqual(db.execute('SELECT high_water FROM clock_state WHERE id=1').fetchone()[0], 105999)
            self.assertNotEqual(ownership_metadata(new_manifest)['nonce'], proof['nonce'])
            self.assertEqual(ownership_metadata(self.manifest)['state'], 'Ready')
            self.assertEqual(keeper.execute('SELECT high_water FROM clock_state WHERE id=1').fetchone()[0], 105999)

    def test_invalid_names_and_timeouts_reject_before_snapshot_artifacts(self):
        folder = self.manifest.data_directory / 'backups'
        for name in ('', '../outside', 'a/b', 'a\\b', '/absolute', 'a.sqlite3', 'a\n', 'CON', 'LPT1', 'x' * 49):
            with self.assertRaises(StagingOpsError):
                backup_staging(self.manifest, name)
            with self.assertRaises(StagingOpsError):
                restore_staging(self.manifest, 'snapshot', name)
        for timeout in (0, 601, True, '60', float('nan')):
            with self.assertRaises(StagingOpsError):
                backup_staging(self.manifest, 'snapshot', timeout_seconds=timeout)
        self.assertEqual(list(folder.iterdir()), [])
        self.assertEqual(list((self.manifest.data_directory / 'restores').iterdir()), [])

    def test_existing_snapshot_or_receipt_never_overwritten(self):
        self.snapshot().write_bytes(b'operator-owned-file')
        with self.assertRaises(StagingOpsError):
            backup_staging(self.manifest, 'snapshot')
        self.assertEqual(self.snapshot().read_bytes(), b'operator-owned-file')
        self.assertFalse(self.receipt().exists())
        self.receipt('other').write_bytes(b'operator-owned-receipt')
        with self.assertRaises(StagingOpsError):
            backup_staging(self.manifest, 'other')
        self.assertFalse(self.snapshot('other').exists())
        self.assertEqual(self.receipt('other').read_bytes(), b'operator-owned-receipt')

    def test_receipt_public_binding_has_no_account_or_secret_payload(self):
        backup_staging(self.manifest, 'snapshot')
        proof = json.loads(self.receipt().read_bytes())
        self.assertEqual(set(proof), {'version', 'kind', 'state', 'deploymentId', 'publicOrigin', 'identityScope', 'nonce',
                                    'operationId', 'snapshotName', 'sha256', 'bytes', 'schemaVersion'})
        self.assertEqual(proof['deploymentId'], self.manifest.deployment_id)
        self.assertEqual(proof['publicOrigin'], self.manifest.public_origin)
        self.assertNotIn(str(self.root), self.receipt().read_text(encoding='utf-8'))

    def test_foreign_same_identity_scope_backup_nonce_rejected_before_target(self):
        backup_staging(self.manifest, 'snapshot')
        other = manifest_for_data_directory(self.manifest, self.root / 'other-authority')
        self.make_ready(other)
        for suffix in ('.sqlite3', '.receipt.json'):
            shutil.copyfile(self.manifest.data_directory / 'backups' / ('snapshot' + suffix), other.data_directory / 'backups' / ('snapshot' + suffix))
        with self.assertRaises(StagingOpsError) as raised:
            restore_staging(other, 'snapshot', 'must-not-exist')
        self.assertEqual(raised.exception.code, 'staging_snapshot_owner_mismatch')
        self.assertFalse((other.data_directory / 'restores' / 'must-not-exist').exists())

    def test_tampered_snapshot_sidecar_and_receipt_fail_before_target_creation(self):
        backup_staging(self.manifest, 'snapshot')
        original = self.snapshot().read_bytes()
        self.snapshot().write_bytes(original + b'tamper')
        with self.assertRaises(StagingOpsError) as raised:
            restore_staging(self.manifest, 'snapshot', 'hash')
        self.assertEqual(raised.exception.code, 'staging_snapshot_hash_mismatch')
        self.assertFalse(self.target('hash').exists())
        self.snapshot().write_bytes(original)
        sidecar = Path(str(self.snapshot()) + '-wal')
        sidecar.write_bytes(b'not-owned-by-standalone-snapshot')
        with self.assertRaises(StagingOpsError):
            restore_staging(self.manifest, 'snapshot', 'sidecar')
        self.assertFalse(self.target('sidecar').exists())
        sidecar.unlink()
        raw = self.receipt().read_bytes()
        self.receipt().write_bytes(raw.replace(b'"state":"Ready"', b'"state":"Ready","state":"Ready"'))
        with self.assertRaises(StagingOpsError):
            restore_staging(self.manifest, 'snapshot', 'duplicate')
        self.assertFalse(self.target('duplicate').exists())

    def test_hardlinked_snapshot_and_source_are_rejected(self):
        backup_staging(self.manifest, 'snapshot')
        alias = self.root / 'snapshot-alias.sqlite3'
        os.link(self.snapshot(), alias)
        with self.assertRaises(StagingOpsError):
            restore_staging(self.manifest, 'snapshot', 'linked')
        self.assertFalse(self.target('linked').exists())
        source_alias = self.root / 'source-alias.sqlite3'
        os.link(owned_database(self.manifest), source_alias)
        with self.assertRaises(StagingError):
            backup_staging(self.manifest, 'linked-source')
        self.assertFalse(self.receipt('linked-source').exists())

    def test_receipt_failure_preserves_pending_snapshot_and_blocks_restore_retry(self):
        with patch('hotr_backend.staging_ops105._ready_receipt', side_effect=OSError('controlled-receipt-write-failure')):
            with self.assertRaises(OSError):
                backup_staging(self.manifest, 'snapshot')
        self.assertTrue(self.snapshot().is_file())
        self.assertEqual(json.loads(self.receipt().read_bytes())['state'], 'Pending')
        with self.assertRaises(StagingOpsError):
            restore_staging(self.manifest, 'snapshot', 'not-created')
        self.assertFalse(self.target('not-created').exists())
        saved = self.snapshot().read_bytes()
        with self.assertRaises(StagingOpsError):
            backup_staging(self.manifest, 'snapshot')
        self.assertEqual(self.snapshot().read_bytes(), saved)

    def test_copy_failure_preserves_partial_artifact_and_pending_receipt(self):
        def fail_copy(source, target, **options):
            target.write_bytes(b'controlled-partial-snapshot')
            raise OperationError('database_copy_failed_artifact_preserved')
        with patch('hotr_backend.staging_ops105.backup_database', side_effect=fail_copy):
            with self.assertRaises(OperationError):
                backup_staging(self.manifest, 'snapshot')
        self.assertEqual(self.snapshot().read_bytes(), b'controlled-partial-snapshot')
        self.assertEqual(json.loads(self.receipt().read_bytes())['state'], 'Pending')
        self.assertEqual(ownership_metadata(self.manifest)['state'], 'Ready')
        with self.assertRaises(StagingOpsError):
            restore_staging(self.manifest, 'snapshot', 'not-created')
        self.assertFalse(self.target('not-created').exists())

    def test_failed_restore_retains_nonlaunchable_pending_destination(self):
        backup_staging(self.manifest, 'snapshot')
        with patch('hotr_backend.staging_ops105.restore_database', side_effect=OperationError('database_copy_timeout')):
            with self.assertRaises(OperationError):
                restore_staging(self.manifest, 'snapshot', 'partial')
        pending = manifest_for_data_directory(self.manifest, self.target('partial'))
        self.assertEqual(ownership_metadata(pending, allowed_states=('RestorePending',))['state'], 'RestorePending')
        with self.assertRaises(StagingError):
            owned_database(pending)
        with self.assertRaises(StagingOpsError):
            restore_staging(self.manifest, 'snapshot', 'partial')
        self.assertEqual(ownership_metadata(self.manifest)['state'], 'Ready')

    def test_independent_validation_failure_cannot_promote_restored_database(self):
        backup_staging(self.manifest, 'snapshot')
        with patch('hotr_backend.staging_ops105.complete_restore', side_effect=StagingError('staging_database_validation_failed')):
            with self.assertRaises(StagingError):
                restore_staging(self.manifest, 'snapshot', 'invalid')
        pending = manifest_for_data_directory(self.manifest, self.target('invalid'))
        self.assertTrue((pending.data_directory / 'authority.sqlite3').is_file())
        self.assertEqual(ownership_metadata(pending, allowed_states=('RestorePending',))['state'], 'RestorePending')
        with self.assertRaises(StagingError):
            owned_database(pending)

    def test_cli_logs_only_safe_summary_or_fixed_error_codes(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(['backup', '--manifest', str(self.manifest_path), '--name', 'cli'])
        result = json.loads(output.getvalue())
        self.assertEqual((status, result['operation']), (0, 'staging_backup'))
        self.assertNotIn(str(self.root), output.getvalue())
        self.assertNotIn(self.manifest.public_origin, output.getvalue())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(['backup', '--manifest', 'do-not-echo-this-path', '--name', 'bad', '--timeout-seconds', 'do-not-echo-this-value'])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())['code'], 'staging_operator_arguments_invalid')
        self.assertNotIn('do-not-echo', output.getvalue())
        output = io.StringIO()
        with patch('hotr_backend.staging_ops105.backup_database', side_effect=OperationError('untrusted-provider-detail')):
            with contextlib.redirect_stdout(output):
                status = main(['backup', '--manifest', str(self.manifest_path), '--name', 'secret-error'])
        self.assertEqual((status, json.loads(output.getvalue())['code']), (1, 'staging_operation_failed'))
        self.assertNotIn('untrusted-provider-detail', output.getvalue())


if __name__ == '__main__':
    unittest.main()
