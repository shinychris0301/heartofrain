"""Actual owned SQLite SDK snapshots; synthetic SDK reports, no provider/device proof."""
from contextlib import closing, redirect_stdout
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient

from hotr_backend import monitoring122, operations, staging105 as staging
from hotr_backend import staging_ops105 as legacy_ops
from hotr_backend import staging_sdk126 as runtime
from hotr_backend import staging_sdk_ops126 as ops
from hotr_backend.sdk_schema125 import validate_sdk_database
from hotr_backend.storage import Database

ROOT = Path(__file__).resolve().parents[2]


class StagingSdkOperations126Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-staging-sdk-ops126-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest_path = self.root / 'staging.json'
        self.manifest_path.write_text(json.dumps(dict(
            version=1, mode='staging', publicOrigin='https://sdk.ops126-fixture.net',
            identityScope='review-sdk-ops126', deploymentId='sdk-ops126-fixture',
            dataDirectory=str(self.root / 'authority'), port=0,
            vk=dict(enabled=False, clientId='', redirectUri=''),
            replay=dict(enabled=False, bundle='', approvalFile='', approvalSHA256=''))), encoding='utf-8')
        self.manifest = staging.read_manifest(self.manifest_path)
        staging.initialize_owned_data(self.manifest, restore_pending=True)
        self.path = self.manifest.data_directory / staging.DATABASE
        Database(self.path)
        staging.complete_restore(self.manifest)
        # Provision on the original schema15 authority. Its actor, access token
        # and wallet must survive the real stopped same-wallet transition.
        app = staging._construct(self.manifest, None)
        self.identity = app.state.authority.provision(lifetime=2_592_000)
        self.headers = {'Authorization': 'Bearer ' + self.identity['token']}
        with TestClient(app) as client:
            wallet = client.get('/v1/wallet', headers=self.headers)
            self.assertEqual(wallet.status_code, 200)
            self.wallet_before = wallet.json()
        self.owner_before = (self.manifest.data_directory / staging.MARKER).read_bytes()
        catalog = json.loads((ROOT / 'Release/RuStore/commerce.example.json').read_text('utf-8-sig'))
        catalog.update(enabled=True, sandbox=True, appId=123, verificationMode='sdk_client_reported')
        for item in catalog['products']:
            item['enabled'] = True
        self.catalog_path = self.root / 'sdk-catalog.json'
        self.catalog_path.write_text(json.dumps(catalog), encoding='utf-8')
        runtime.prepare_sdk_authority(self.manifest_path, self.catalog_path, 'com.heartoftherain.game',
                                      'sdk_ops126', confirm_sdk_client_reported=True)
        runtime.require_sdk_ready(self.manifest)

    def scalar(self, query, args=(), path=None):
        with closing(sqlite3.connect(path or self.path)) as db:
            return db.execute(query, args).fetchone()[0]

    def snapshot(self, name='snapshot'):
        return self.manifest.data_directory / 'backups' / (name + '.sqlite3')

    def receipt(self, name='snapshot'):
        return self.manifest.data_directory / 'backups' / (name + '.receipt.json')

    def target_root(self, tag='drill'):
        return self.manifest.data_directory / 'restores' / tag

    def report_purchase(self):
        with runtime.application_context(self.manifest) as app:
            with TestClient(app) as client:
                response = client.post('/v1/commerce/orders', headers=self.headers,
                    json={'commandId': uuid.uuid4().hex, 'productId': 'coins-1000'})
                self.assertEqual(response.status_code, 200)
                order = response.json()
                observed = dict(invoiceId='10001', purchaseId=str(uuid.uuid4()),
                    orderId=order['orderId'], productId=order['sdk']['productId'],
                    developerPayload=order['sdk']['developerPayload'], quantity=1,
                    sandbox=True, status='CONFIRMED', purchaseType='ONE_STEP',
                    acknowledgementState='PENDING', productType='CONSUMABLE_PRODUCT',
                    amountMinor=order['amountMinor'], currency=order['currency'])
                result = client.post('/v1/commerce/orders/' + order['orderId'] + '/sdk-report',
                                     headers=self.headers, json=observed)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(client.get('/v1/wallet', headers=self.headers).json()['playerId'],
                                 self.wallet_before['playerId'])
        return order

    def test_stopped_same_wallet_grant_backup_and_permanent_restore_keep_owner_and_all_rows(self):
        self.report_purchase()
        self.assertEqual((self.manifest.data_directory / staging.MARKER).read_bytes(), self.owner_before)
        with closing(sqlite3.connect(self.path, isolation_level=None)) as wal:
            wal.execute('PRAGMA journal_mode=WAL')
            wal.execute('UPDATE clock_state SET high_water=high_water+10 WHERE id=1')
            self.assertGreater(Path(str(self.path) + '-wal').stat().st_size, 0)
            backup = ops.backup_staging_sdk(self.manifest_path, 'snapshot')
            result = ops.restore_quarantine(self.manifest_path, 'snapshot', 'drill')
            copied = self.target_root() / staging.DATABASE
            with closing(sqlite3.connect(copied)) as db:
                self.assertEqual(validate_sdk_database(db), 125)
                source_tables = [row[0] for row in wal.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                for name in source_tables:
                    self.assertEqual(sorted(wal.execute('SELECT * FROM "' + name + '"').fetchall(), key=repr),
                                     sorted(db.execute('SELECT * FROM "' + name + '"').fetchall(), key=repr), name)
            self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_credits', path=copied), 1)
        self.assertEqual((backup['schemaVersion'], result['schemaVersion']), (125, 125))
        self.assertFalse(result['activationPerformed'] or result['activationAllowed'] or result['databaseReplaced'])
        self.assertEqual((self.manifest.data_directory / staging.MARKER).read_bytes(), self.owner_before)
        quarantine = json.loads((self.target_root() / ops.QUARANTINE_MARKER).read_bytes())
        self.assertEqual(quarantine['state'], 'ValidatedQuarantine')
        self.assertFalse(quarantine['activationAllowed'])
        self.assertFalse((self.target_root() / staging.MARKER).exists())
        self.assertFalse((self.target_root() / runtime.POLICY).exists())
        alternate = replace(self.manifest, data_directory=self.target_root())
        with self.assertRaises(Exception):
            runtime.require_sdk_ready(alternate)
        with self.assertRaises(Exception):
            staging.owned_database(alternate)

    def test_installed_monitor_accepts_exact_schema125_staging_receipt_without_integrity_claim(self):
        ops.backup_staging_sdk(self.manifest, 'snapshot')
        proof = json.loads(self.receipt().read_bytes())
        self.assertEqual(set(proof), {'version', 'kind', 'state', 'deploymentId', 'publicOrigin',
            'identityScope', 'nonce', 'operationId', 'snapshotName', 'sha256', 'bytes', 'schemaVersion'})
        self.assertEqual((proof['kind'], proof['schemaVersion']), ('HeartOfTheRainStagingBackup105', 125))
        checks = monitoring122._backup_check(self.manifest_path, self.manifest.public_origin, 24, 1)
        self.assertTrue(all(row['ok'] for row in checks), checks)
        self.assertEqual(checks[0]['invalidReceiptCount'], 0)
        self.assertFalse(checks[0]['snapshotIntegrityVerified'] or checks[0]['offHostCopyVerified'])

    def test_legacy_entrypoints_remain_exact_and_refuse125_without_migration(self):
        for name, function in (('legacy_backup', operations.backup_database),
                               ('legacy_restore', operations.restore_database)):
            target = self.root / (name + '.sqlite3')
            with self.assertRaises(operations.OperationError):
                function(self.path, target)
            self.assertFalse(target.exists())
        ops.backup_staging_sdk(self.manifest, 'snapshot')
        with self.assertRaises(legacy_ops.StagingOpsError):
            legacy_ops.restore_staging(self.manifest, 'snapshot', 'legacy_must_not_start')
        self.assertFalse(self.target_root('legacy_must_not_start').exists())
        self.assertEqual(self.scalar('SELECT version FROM schema_info'), 125)

    def test_wrong_schema_shape_rejects_before_backup_artifacts(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('CREATE TABLE foreign_shape126 (value TEXT)')
            db.commit()
        with self.assertRaises(Exception):
            ops.backup_staging_sdk(self.manifest, 'bad')
        self.assertFalse(self.snapshot('bad').exists())
        self.assertFalse(self.receipt('bad').exists())

    def test_invalid_snapshot_hash_sidecar_duplicate_or_owner_reject_before_quarantine(self):
        ops.backup_staging_sdk(self.manifest, 'snapshot')
        original, raw = self.snapshot().read_bytes(), self.receipt().read_bytes()
        self.snapshot().write_bytes(original + b'tamper')
        with self.assertRaises(ops.StagingSdkOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'hash')
        self.assertFalse(self.target_root('hash').exists())
        self.snapshot().write_bytes(original)
        sidecar = Path(str(self.snapshot()) + '-wal')
        sidecar.write_bytes(b'foreign-sidecar')
        with self.assertRaises(ops.StagingSdkOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'sidecar')
        self.assertFalse(self.target_root('sidecar').exists())
        sidecar.unlink()
        self.receipt().write_bytes(raw.replace(b'"state":"Ready"', b'"state":"Ready","state":"Ready"'))
        with self.assertRaises(ops.StagingSdkOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'duplicate')
        self.assertFalse(self.target_root('duplicate').exists())
        proof = json.loads(raw)
        proof['nonce'] = uuid.uuid4().hex
        self.receipt().write_bytes(legacy_ops._bytes(proof))
        with self.assertRaises(ops.StagingSdkOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'foreign_owner')
        self.assertFalse(self.target_root('foreign_owner').exists())

    def test_hash_consistent_schema15_snapshot_still_rejects_before_quarantine(self):
        ops.backup_staging_sdk(self.manifest, 'snapshot')
        legacy = self.root / 'ordinary15.sqlite3'
        Database(legacy)
        self.snapshot().write_bytes(legacy.read_bytes())
        proof = json.loads(self.receipt().read_bytes())
        proof.update(sha256=hashlib.sha256(self.snapshot().read_bytes()).hexdigest(), bytes=self.snapshot().stat().st_size)
        self.receipt().write_bytes(legacy_ops._bytes(proof))
        with self.assertRaises(operations.OperationError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'wrong_schema')
        self.assertFalse(self.target_root('wrong_schema').exists())

    def test_copy_failure_retains_partial_pending_and_cannot_restore_or_overwrite(self):
        def fail(source, target, **options):
            target.write_bytes(b'controlled-partial-copy')
            raise operations.OperationError('database_copy_failed_artifact_preserved')
        with patch.object(ops, 'backup_database', side_effect=fail):
            with self.assertRaises(operations.OperationError):
                ops.backup_staging_sdk(self.manifest, 'snapshot')
        self.assertEqual(json.loads(self.receipt().read_bytes())['state'], 'Pending')
        with self.assertRaises(ops.StagingSdkOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'not_created')
        with self.assertRaises(legacy_ops.StagingOpsError):
            ops.backup_staging_sdk(self.manifest, 'snapshot')
        self.assertEqual(self.snapshot().read_bytes(), b'controlled-partial-copy')
        self.assertFalse(self.target_root('not_created').exists())

    def test_owner_change_during_backup_never_marks_stale_receipt_ready(self):
        original_copy = ops.backup_database
        def changed(source, target, **options):
            result = original_copy(source, target, **options)
            owner = json.loads(self.owner_before)
            owner['nonce'] = uuid.uuid4().hex
            (self.manifest.data_directory / staging.MARKER).write_bytes(staging._bytes(owner))
            return result
        with patch.object(ops, 'backup_database', side_effect=changed):
            with self.assertRaises(Exception):
                ops.backup_staging_sdk(self.manifest, 'snapshot')
        self.assertTrue(self.snapshot().is_file())
        self.assertEqual(json.loads(self.receipt().read_bytes())['state'], 'Pending')

    def test_policy_change_during_backup_never_marks_stale_receipt_ready(self):
        original_copy = ops.backup_database
        def changed(source, target, **options):
            result = original_copy(source, target, **options)
            (self.manifest.data_directory / runtime.CATALOG).write_bytes(b'{}')
            return result
        with patch.object(ops, 'backup_database', side_effect=changed):
            with self.assertRaises(Exception):
                ops.backup_staging_sdk(self.manifest, 'snapshot')
        self.assertEqual(json.loads(self.receipt().read_bytes())['state'], 'Pending')

    def test_restore_interruption_and_owner_change_keep_nonlaunchable_quarantine(self):
        ops.backup_staging_sdk(self.manifest, 'snapshot')
        with patch.object(ops, 'restore_database', side_effect=operations.OperationError('database_copy_timeout')):
            with self.assertRaises(operations.OperationError):
                ops.restore_quarantine(self.manifest, 'snapshot', 'partial')
        pending = self.target_root('partial') / ops.QUARANTINE_MARKER
        self.assertEqual(json.loads(pending.read_bytes())['state'], 'RestoreQuarantinedPending')
        with self.assertRaises(legacy_ops.StagingOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'partial')
        original_copy = ops.restore_database
        def changed(source, target, **options):
            result = original_copy(source, target, **options)
            owner = json.loads(self.owner_before)
            owner['nonce'] = uuid.uuid4().hex
            (self.manifest.data_directory / staging.MARKER).write_bytes(staging._bytes(owner))
            return result
        with patch.object(ops, 'restore_database', side_effect=changed):
            with self.assertRaises(Exception):
                ops.restore_quarantine(self.manifest, 'snapshot', 'changed_owner')
        self.assertEqual(json.loads((self.target_root('changed_owner') / ops.QUARANTINE_MARKER).read_bytes())['state'],
                         'RestoreQuarantinedPending')
        self.assertFalse((self.target_root('changed_owner') / staging.MARKER).exists())

    def test_invalid_names_timeouts_links_and_existing_destinations_are_preserved(self):
        for name in ('', '../escape', 'a/b', 'CON', 'NUL', 'x' * 49):
            with self.assertRaises(legacy_ops.StagingOpsError):
                ops.backup_staging_sdk(self.manifest, name)
        for timeout in (True, 0, 601, float('nan')):
            with self.assertRaises(legacy_ops.StagingOpsError):
                ops.backup_staging_sdk(self.manifest, 'badtimeout', timeout_seconds=timeout)
        self.snapshot().write_bytes(b'operator-file')
        with self.assertRaises(legacy_ops.StagingOpsError):
            ops.backup_staging_sdk(self.manifest, 'snapshot')
        self.assertEqual(self.snapshot().read_bytes(), b'operator-file')
        self.assertFalse(self.receipt().exists())
        self.snapshot().unlink()
        ops.backup_staging_sdk(self.manifest, 'snapshot')
        os.link(self.snapshot(), self.root / 'snapshot-alias')
        with self.assertRaises(legacy_ops.StagingOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'hardlink')
        self.assertFalse(self.target_root('hardlink').exists())

    def test_cli_summary_and_failures_never_echo_paths_tokens_or_foreign_errors(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = ops.main(['backup', '--manifest', str(self.manifest_path), '--name', 'cli'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['operation'], 'staging_sdk_backup')
        for private in (str(self.root), self.identity['token'], self.identity['playerId'], self.manifest.public_origin):
            self.assertNotIn(private, output.getvalue())
        output = io.StringIO()
        with redirect_stdout(output):
            code = ops.main(['backup', '--manifest', 'private-path-never-echo', '--name', 'bad',
                             '--timeout-seconds', 'private-value-never-echo'])
        self.assertEqual((code, json.loads(output.getvalue())['code']),
                         (1, 'staging_sdk_operator_arguments_invalid'))
        self.assertNotIn('never-echo', output.getvalue())
        output = io.StringIO()
        with patch.object(ops, 'backup_database', side_effect=operations.OperationError('private-provider-detail')):
            with redirect_stdout(output):
                code = ops.main(['backup', '--manifest', str(self.manifest_path), '--name', 'foreign'])
        self.assertEqual((code, json.loads(output.getvalue())['code']), (1, 'staging_sdk_operation_failed'))
        self.assertNotIn('private-provider-detail', output.getvalue())


if __name__ == '__main__':
    unittest.main()
