"""Real SQLite snapshot and operator CLI controls; no provider network/payments."""
import contextlib
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hotr_backend.__main__ import main
from hotr_backend.api import create_app
from hotr_backend.commerce_schemas import CreateCommerceOrder, ReconcileCommerceOrder
from hotr_backend.operations import OperationError, backup_database, reconcile_bounded, restore_database
from hotr_backend.identity_schema import IDENTITY_V4_DDL
from hotr_backend.notification_schema import NOTIFICATIONS_V4_DDL
from hotr_backend.rustore_provider import VerifiedInvoice
from hotr_backend.service import Actor
from hotr_backend.storage import COMMERCE_V2, DDL, SCHEMA_VERSION, WALLET_V3

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config'


class Provider:
    configured = True

    def __init__(self):
        self.values, self.calls = {}, 0

    def lookup(self, invoice, sandbox):
        self.calls += 1
        return self.values[invoice]


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-operations-')
        self.root = Path(self.temp.name)
        self.path = self.root / 'authority.sqlite3'
        self.config = self.root / 'commerce.json'
        self.now = 300 * 86400
        self.config.write_text(json.dumps({'version': 'synthetic-operations-test', 'enabled': True,
            'appId': 123, 'sandbox': True, 'products': [{'id': 'fixture', 'storeProductId': 'synthetic_1000',
                'enabled': True, 'coins': 1000, 'amountMinor': 9900, 'currency': 'RUB'}]}), encoding='utf-8')
        self.provider = Provider()
        self.app = self.open(self.path)
        self.authority = self.app.state.authority
        self.identity = self.authority.provision(lifetime=2_592_000)
        self.actor = Actor(self.identity['playerId'], self.now)
        self.sequence = 1000
        self.order, self.invoice = self.purchase()

    def open(self, path):
        return create_app(path, CONFIG, lambda: self.now, commerce_provider=self.provider,
                          commerce_config_path=self.config, notifications_enabled=False, identity_enabled=False)

    def tearDown(self):
        self.temp.cleanup()

    def purchase(self):
        commerce = self.app.state.commerce
        order = commerce.create(self.actor, CreateCommerceOrder(commandId=uuid.uuid4().hex, productId='fixture'))
        self.sequence += 1
        invoice = str(self.sequence)
        self.provider.values[invoice] = VerifiedInvoice(invoice, str(uuid.uuid4()), 123, True, order['orderId'],
            order['sdk']['productId'], self.actor.player, order['sdk']['developerPayload'], 9900, 'RUB', 'CONFIRMED', 'PENDING')
        commerce.reconcile(self.actor, order['orderId'], ReconcileCommerceOrder(invoiceId=invoice))
        return order, invoice

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def test_real_receipt_wallet_snapshot_and_new_database_recovery(self):
        before = self.app.state.wallet.view(self.actor)
        snapshot, recovered = self.root / 'snapshot.sqlite3', self.root / 'recovered.sqlite3'
        backup = backup_database(self.path, snapshot)
        restored = restore_database(snapshot, recovered)
        self.assertEqual((backup['schemaVersion'], restored['schemaVersion']), (SCHEMA_VERSION, SCHEMA_VERSION))
        self.assertTrue(backup['fileFsynced'] and backup['destinationWasNew'])
        self.assertFalse(restored['inPlaceRestore'])
        self.assertEqual(restored['sha256'], self.digest(recovered))
        reopened = self.open(recovered)
        after = reopened.state.wallet.view(self.actor)
        self.assertEqual((after['coins'], after['revision'], after['starting'], after['tools']),
                         (before['coins'], before['revision'], before['starting'], before['tools']))
        reopened.state.commerce.reconcile(self.actor, self.order['orderId'], ReconcileCommerceOrder(invoiceId=self.invoice))
        self.assertEqual(reopened.state.wallet.view(self.actor)['coins'], before['coins'])
        with reopened.state.authority.database.connect() as database:
            self.assertEqual(database.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)

    def test_online_backup_includes_committed_uncheckpointed_wal(self):
        keeper = sqlite3.connect(self.path, isolation_level=None)
        try:
            keeper.execute('PRAGMA journal_mode=WAL')
            self.purchase()
            wal = Path(str(self.path) + '-wal')
            self.assertTrue(wal.is_file() and wal.stat().st_size > 0)
            destination = self.root / 'wal-snapshot.sqlite3'
            backup_database(self.path, destination)
            with contextlib.closing(sqlite3.connect(destination)) as database:
                self.assertEqual(database.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 2)
                self.assertEqual(database.execute('PRAGMA journal_mode').fetchone()[0], 'delete')
            self.assertFalse(Path(str(destination) + '-wal').exists())
        finally:
            keeper.close()

    def test_existing_destination_and_in_place_restore_never_overwrite(self):
        destination = self.root / 'existing.sqlite3'
        destination.write_bytes(b'operator-owned-existing-file')
        expected = destination.read_bytes()
        with self.assertRaises(OperationError) as error:
            backup_database(self.path, destination)
        self.assertEqual(str(error.exception), 'destination_exists')
        self.assertEqual(destination.read_bytes(), expected)
        source_hash = self.digest(self.path)
        with self.assertRaises(OperationError):
            restore_database(self.path, self.path)
        self.assertEqual(self.digest(self.path), source_hash)

    def test_corrupt_source_denied_before_creating_destination(self):
        corrupt = self.root / 'corrupt.sqlite3'
        corrupt.write_bytes(b'not-a-database')
        output = self.root / 'never-created.sqlite3'
        with self.assertRaises(OperationError):
            restore_database(corrupt, output)
        self.assertFalse(output.exists())
        self.assertEqual(corrupt.read_bytes(), b'not-a-database')

    def test_future_schema_denied_without_source_migration(self):
        snapshot = self.root / 'future.sqlite3'
        backup_database(self.path, snapshot)
        with contextlib.closing(sqlite3.connect(snapshot, isolation_level=None)) as database:
            database.execute('UPDATE schema_info SET version=999')
        before = self.digest(snapshot)
        target = self.root / 'future-restore.sqlite3'
        with self.assertRaises(OperationError) as error:
            restore_database(snapshot, target)
        self.assertEqual(str(error.exception), 'unknown_database_schema')
        self.assertFalse(target.exists())
        self.assertEqual(before, self.digest(snapshot))

    def test_false_schema_claim_and_missing_unique_index_denied(self):
        partial = self.root / 'partial.sqlite3'
        with contextlib.closing(sqlite3.connect(partial, isolation_level=None)) as database:
            database.executescript('CREATE TABLE schema_info(version INTEGER); INSERT INTO schema_info VALUES(' + str(SCHEMA_VERSION) + ');')
        with self.assertRaises(OperationError):
            restore_database(partial, self.root / 'partial-out.sqlite3')
        changed = self.root / 'changed.sqlite3'
        backup_database(self.path, changed)
        with contextlib.closing(sqlite3.connect(changed, isolation_level=None)) as database:
            database.execute('DROP INDEX commerce_one_invoice')
        with self.assertRaises(OperationError) as error:
            restore_database(changed, self.root / 'changed-out.sqlite3')
        self.assertEqual(str(error.exception), 'database_schema_mismatch')

    def test_foreign_key_corruption_denied_even_with_quick_check_ok(self):
        snapshot = self.root / 'foreign.sqlite3'
        backup_database(self.path, snapshot)
        with contextlib.closing(sqlite3.connect(snapshot, isolation_level=None)) as database:
            database.execute('PRAGMA foreign_keys=OFF')
            database.execute('INSERT INTO credentials VALUES(?,?,?,?,0)', ('f' * 64, uuid.uuid4().hex, 'player', self.now + 10))
            self.assertEqual(database.execute('PRAGMA quick_check').fetchall(), [('ok',)])
        with self.assertRaises(OperationError) as error:
            restore_database(snapshot, self.root / 'foreign-out.sqlite3')
        self.assertEqual(str(error.exception), 'database_foreign_keys_failed')

    def test_known_legacy_schema_remains_unmigrated_until_operator_opens_it(self):
        legacy, snapshot, restored = (self.root / name for name in ('legacy.sqlite3', 'legacy-copy.sqlite3', 'legacy-restored.sqlite3'))
        with contextlib.closing(sqlite3.connect(legacy, isolation_level=None)) as database:
            database.executescript(DDL + COMMERCE_V2 + 'UPDATE schema_info SET version=2;')
        backup = backup_database(legacy, snapshot)
        result = restore_database(snapshot, restored)
        self.assertEqual((backup['schemaVersion'], result['schemaVersion'], result['requiresMigration']), (2, 2, True))
        for path in (legacy, snapshot, restored):
            with contextlib.closing(sqlite3.connect(path)) as database:
                self.assertEqual(database.execute('SELECT version FROM schema_info').fetchone()[0], 2)

    def test_schema4_purchase_wallet_snapshot_stays_known_after_schema5_added(self):
        legacy, snapshot, restored = (self.root / name for name in ('schema4.sqlite3', 'schema4-copy.sqlite3', 'schema4-restored.sqlite3'))
        with contextlib.closing(sqlite3.connect(legacy, isolation_level=None)) as database:
            from tests.legacy_schema_fixture import copy_legacy
            with self.authority.database.connect() as source:
                copy_legacy(source, database, 4)
        backup_database(legacy, snapshot)
        result = restore_database(snapshot, restored)
        self.assertEqual((result['schemaVersion'], result['requiresMigration']), (4, SCHEMA_VERSION > 4))
        with contextlib.closing(sqlite3.connect(restored)) as database, self.authority.database.connect() as source:
            self.assertEqual(database.execute('SELECT version FROM schema_info').fetchone()[0], 4)
            self.assertEqual(database.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)
            self.assertEqual(database.execute('SELECT balances FROM wallets').fetchone()[0], source.execute('SELECT balances FROM wallets').fetchone()[0])

    def test_missing_source_and_invalid_timeout_do_not_create_files(self):
        missing, target = self.root / 'missing.sqlite3', self.root / 'out.sqlite3'
        with self.assertRaises(OperationError):
            backup_database(missing, target)
        with self.assertRaises(OperationError):
            backup_database(self.path, target, timeout_seconds=0)
        self.assertFalse(missing.exists() or target.exists())

    def test_fsync_failure_preserves_artifact_and_prevents_silent_reuse(self):
        target = self.root / 'failed-snapshot.sqlite3'
        with patch('hotr_backend.operations.os.fsync', side_effect=OSError('synthetic')):
            with self.assertRaises(OperationError) as error:
                backup_database(self.path, target)
        self.assertEqual(str(error.exception), 'database_copy_failed_artifact_preserved')
        self.assertTrue(target.exists())
        with self.assertRaises(OperationError):
            backup_database(self.path, target)

    def test_platform_permission_scope_is_explicit(self):
        target = self.root / 'permissions.sqlite3'
        result = backup_database(self.path, target)
        if os.name == 'posix':
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertTrue(result['directoryFsynced'])
        else:
            self.assertEqual(result['permissionScope'], 'creation_mode0600_windows_acl_inherited')
            self.assertFalse(result['directoryFsynced'])

    def test_worker_disabled_and_live_commerce_fail_before_any_work(self):
        for enabled, sandbox, configured in ((False, True, True), (True, False, True), (True, True, False)):
            fake = SimpleNamespace(state=SimpleNamespace(commerce=SimpleNamespace(
                config=SimpleNamespace(enabled=enabled, sandbox=sandbox), provider=SimpleNamespace(configured=configured))))
            with self.assertRaises(OperationError):
                reconcile_bounded(fake, 'staging')
        with self.assertRaises(OperationError):
            reconcile_bounded(self.app, 'production')

    def test_real_bounded_worker_poll_preserves_one_credit_and_redacts_output(self):
        value = reconcile_bounded(self.app, 'staging', worker_id='fixture', max_jobs=1)
        self.assertEqual((value['worked'], value['seeded'], value['productionEnabled'], value['sdkAcknowledgementWritten']), (1, 1, False, False))
        self.assertEqual(value['states'], {'Done': 1})
        serialized = json.dumps(value)
        self.assertTrue(self.identity['token'] not in serialized and self.order['sdk']['developerPayload'] not in serialized)
        with self.authority.database.connect() as database:
            self.assertEqual(database.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)

    def test_worker_invalid_limits_do_not_seed_jobs(self):
        for changes in ({'max_jobs': 1001}, {'seed_limit': 0}, {'poll_seconds': 29}, {'worker_id': 'bad\nworker'}):
            with self.assertRaises(OperationError):
                reconcile_bounded(self.app, 'staging', **changes)
        with self.authority.database.connect() as database:
            self.assertEqual(database.execute('SELECT COUNT(*) FROM commerce_reconcile_jobs').fetchone()[0], 0)

    def test_cli_backup_never_initializes_app_and_production_mode_is_blocked(self):
        target = self.root / 'cli.sqlite3'
        output = io.StringIO()
        with patch.dict(os.environ, {'HOTR_BACKEND_MODE': 'local'}), patch('hotr_backend.__main__.create_app') as factory:
            with contextlib.redirect_stdout(output):
                main(['backup', '--source', str(self.path), '--out', str(target)])
            factory.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['operation'], 'backup')
        with patch.dict(os.environ, {'HOTR_BACKEND_MODE': 'production'}):
            with self.assertRaises(SystemExit):
                main(['restore', '--source', str(target), '--out', str(self.root / 'blocked.sqlite3')])
        self.assertFalse((self.root / 'blocked.sqlite3').exists())

    def test_cli_worker_requires_explicit_mode_and_restores_environment(self):
        with patch('hotr_backend.__main__.create_app') as factory:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['reconcile-worker'])
            factory.assert_not_called()
        with patch.dict(os.environ, {}, clear=True), patch('hotr_backend.__main__.create_app', return_value=self.app):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                main(['reconcile-worker', '--mode', 'staging', '--max-jobs', '1'])
            self.assertNotIn('HOTR_BACKEND_MODE', os.environ)
            self.assertEqual(json.loads(output.getvalue())['mode'], 'staging')

    def test_actual_separate_cli_process_backup_and_restore(self):
        snapshot, restored = self.root / 'process-copy.sqlite3', self.root / 'process-restore.sqlite3'
        environment = dict(os.environ, HOTR_BACKEND_MODE='local')
        for operation, source, target in (('backup', self.path, snapshot), ('restore', snapshot, restored)):
            completed = subprocess.run([sys.executable, '-m', 'hotr_backend', operation, '--source', str(source), '--out', str(target)],
                cwd=ROOT, env=environment, capture_output=True, text=True, timeout=20)
            self.assertEqual(completed.returncode, 0)
            report = json.loads(completed.stdout)
            self.assertEqual(report['operation'], operation)
            self.assertEqual(report['sha256'], self.digest(target))
        with contextlib.closing(sqlite3.connect(restored)) as database:
            self.assertEqual(database.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)
