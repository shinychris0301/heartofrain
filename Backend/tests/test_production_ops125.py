"""Owned SDK125 snapshots with synthetic SDK reports; no store/provider acceptance."""
from contextlib import closing, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
import uuid

from hotr_backend import operations, production_ops122 as ops, production_runtime122 as runtime
from hotr_backend.sdk_schema125 import validate_sdk_database
from tests.production_fixture122 import ProductionFixture122
from tests.sdk_fixture125 import SdkProductionFixture125


class ProductionOperations125Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = SdkProductionFixture125()
        self.addCleanup(self.fixture.close)
        self.manifest = self.fixture.manifest
        with self.fixture.context() as app:
            self.identity, headers = self.fixture.provision(app)
            with self.fixture.client(app) as client:
                order_response = client.post('/v1/commerce/orders', headers=headers,
                    json={'commandId': uuid.uuid4().hex, 'productId': 'coins-1000'})
                self.assertEqual(order_response.status_code, 200)
                self.order = order_response.json()
                report = client.post('/v1/commerce/orders/' + self.order['orderId'] + '/sdk-report',
                                     headers=headers, json=self.fixture.observation(self.order))
                self.assertEqual(report.status_code, 200)
        self.path = runtime.owned_database(self.manifest)

    def scalar(self, sql, args=(), path=None):
        with closing(sqlite3.connect(path or self.path)) as db:
            return db.execute(sql, args).fetchone()[0]

    def test_sdk125_backup_and_quarantine_preserve_grant_and_never_activate(self):
        marker = self.manifest.data_directory / runtime.MARKER
        owner_before = marker.read_bytes()
        balances_before = self.scalar('SELECT balances FROM wallets WHERE player_id=?', (self.identity['playerId'],))
        with closing(sqlite3.connect(self.path, isolation_level=None)) as wal:
            wal.execute('PRAGMA journal_mode=WAL')
            wal.execute('UPDATE clock_state SET high_water=high_water+1 WHERE id=1')
            self.assertGreater(Path(str(self.path) + '-wal').stat().st_size, 0)
            clock_before = self.scalar('SELECT high_water FROM clock_state')
            backup = ops.backup_production(self.manifest, 'sdk_snapshot')
            restore = ops.restore_quarantine(self.manifest, 'sdk_snapshot', 'sdk_quarantine')
            self.assertEqual(self.scalar('SELECT high_water FROM clock_state'), clock_before)
        target_root = self.manifest.data_directory / 'restores/sdk_quarantine'
        target = target_root / 'authority.sqlite3'
        self.assertEqual((backup['schemaVersion'], restore['schemaVersion']), (125, 125))
        self.assertFalse(restore['activationAllowed'])
        self.assertFalse(restore['databaseReplaced'])
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_credits', path=target), 1)
        self.assertEqual(self.scalar('SELECT verification_mode FROM commerce_orders', path=target), 'sdk_client_reported')
        self.assertEqual(self.scalar('SELECT sdk_last_status FROM commerce_orders', path=target), 'CONFIRMED')
        self.assertEqual(self.scalar('SELECT balances FROM wallets WHERE player_id=?', (self.identity['playerId'],), target), balances_before)
        with closing(sqlite3.connect(target)) as copied:
            self.assertEqual(validate_sdk_database(copied), 125)
        self.assertEqual(marker.read_bytes(), owner_before)
        self.assertFalse((target_root / runtime.MARKER).exists())
        quarantine = json.loads((target_root / ops.QUARANTINE_MARKER).read_text())
        self.assertEqual(quarantine['state'], 'ValidatedQuarantine')
        self.assertFalse(quarantine['activationAllowed'])
        self.assertEqual(quarantine['schemaVersion'], 125)
        with self.assertRaises(ops.ProductionOpsError):
            ops.restore_quarantine(self.manifest, 'sdk_snapshot', 'sdk_quarantine')

    def test_ordinary_snapshot_entrypoints_still_reject_sdk125_before_destination_creation(self):
        for name, function in (('ordinary_backup', operations.backup_database),
                               ('ordinary_restore', operations.restore_database)):
            target = self.fixture.root / (name + '.sqlite3')
            with self.assertRaises(operations.OperationError):
                function(self.path, target)
            self.assertFalse(target.exists())

    def test_sdk_snapshot_validator_never_accepts_ordinary15(self):
        with ProductionFixture122() as legacy:
            with legacy.context():
                pass
            source = runtime.owned_database(legacy.manifest)
            target = legacy.root / 'not_an_sdk_snapshot.sqlite3'
            with self.assertRaises(operations.OperationError):
                operations.backup_database(source, target, _validator=validate_sdk_database)
            self.assertFalse(target.exists())
            self.assertEqual(self.scalar('SELECT version FROM schema_info', path=source), 15)

    def test_altered_sdk_shape_never_creates_a_snapshot_or_ready_receipt(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('CREATE TABLE unexpected_sdk_shape125 (value TEXT)')
            db.commit()
        with self.assertRaises(runtime.ProductionError):
            ops.backup_production(self.manifest, 'altered')
        self.assertFalse((self.manifest.data_directory / 'backups/altered.sqlite3').exists())
        self.assertFalse((self.manifest.data_directory / 'backups/altered.receipt.json').exists())

    def test_sdk_reconciliation_cannot_seed_or_claim_provider_work(self):
        with self.fixture.context(purpose='operations') as app:
            with patch.object(app.state.reconciliation_worker, 'seed_due') as seed, \
                 patch.object(app.state.reconciliation_worker, 'run_bounded') as work, \
                 patch.object(app.state.commerce.provider, 'lookup') as provider:
                with self.assertRaises(ops.ProductionOpsError) as rejected:
                    ops.reconcile_bounded(app, self.manifest)
                self.assertEqual(rejected.exception.code, ops.SDK_RECONCILIATION_UNAVAILABLE)
                seed.assert_not_called()
                work.assert_not_called()
                provider.assert_not_called()
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_reconcile_jobs'), 0)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_credits'), 1)

    def test_sdk_reconcile_and_supervisor_cli_report_not_applicable_without_opening_runtime(self):
        with patch.object(runtime, 'application_context') as opening:
            for action in ('reconcile', 'supervise-reconciliation'):
                output = io.StringIO()
                with redirect_stdout(output):
                    result = ops.main([action, '--manifest', str(self.fixture.manifest_path)])
                self.assertEqual(result, 1)
                report = json.loads(output.getvalue())
                self.assertEqual(report['status'], 'not_applicable_sdk_client_reported_mode')
                self.assertFalse(report['providerNetworkContacted'])
                self.assertFalse(report['providerAcceptanceVerified'])
                self.assertFalse(report['sdkAcknowledgementWritten'])
                self.assertNotIn(str(self.fixture.root), output.getvalue())
            opening.assert_not_called()

    def test_sdk_queue_summary_remains_readonly_without_provider_claims(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        clock_before = self.scalar('SELECT high_water FROM clock_state')
        result = ops.queue_summary(self.manifest)
        self.assertEqual(result['states'], dict.fromkeys(('Pending', 'Running', 'Done', 'Dead'), 0))
        self.assertFalse(result['databaseChanged'])
        self.assertFalse(result['providerNetworkContacted'])
        self.assertEqual(self.scalar('SELECT high_water FROM clock_state'), clock_before)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)


if __name__ == '__main__':
    unittest.main()
