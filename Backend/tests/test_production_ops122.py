"""Actual fresh production ownership/SQLite/leases with scripted provider/worker only."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from hotr_backend import production_ops122 as ops, production_runtime122 as runtime
from hotr_backend.commerce_schemas import CreateCommerceOrder, ReconcileCommerceOrder
from hotr_backend.operations import OperationError
from hotr_backend.rustore_provider import ProviderUnavailable
from hotr_backend.service import Actor, ServiceError
from hotr_backend.storage import SCHEMA_VERSION
from tests.production_fixture122 import ProductionFixture122


class ProductionOperations122Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProductionFixture122()
        self.addCleanup(self.fixture.close)
        self.manifest = self.fixture.manifest
        with self.fixture.context() as app:
            self.identity, self.headers = self.fixture.provision(app)
        self.path = runtime.owned_database(self.manifest)

    def snapshot(self, name='snapshot'):
        return self.manifest.data_directory / 'backups' / (name + '.sqlite3')

    def receipt(self, name='snapshot'):
        return self.manifest.data_directory / 'backups' / (name + '.receipt.json')

    def restored(self, tag='restore'):
        return self.manifest.data_directory / 'restores' / tag

    def scalar(self, sql, args=(), path=None):
        with contextlib.closing(sqlite3.connect(path or self.path)) as database:
            return database.execute(sql, args).fetchone()[0]

    def known_invoice(self, app):
        actor = Actor(self.identity['playerId'], self.fixture.now)
        order = app.state.commerce.create(actor, CreateCommerceOrder(commandId=uuid.uuid4().hex, productId='coins-1000'))
        invoice = self.fixture.invoice(order)
        with patch.object(self.fixture.provider, 'lookup', side_effect=ProviderUnavailable()):
            with self.assertRaises(ServiceError) as failed:
                app.state.commerce.reconcile(actor, order['orderId'], ReconcileCommerceOrder(invoiceId=invoice))
            self.assertEqual(failed.exception.status, 503)
        return order, invoice

    def test_online_wal_backup_and_quarantined_restore_preserve_authority_and_values(self):
        marker_before = (self.manifest.data_directory / runtime.MARKER).read_bytes()
        with contextlib.closing(sqlite3.connect(self.path, isolation_level=None)) as keeper:
            keeper.execute('PRAGMA journal_mode=WAL')
            keeper.execute('UPDATE clock_state SET high_water=99999999 WHERE id=1')
            self.assertGreater(Path(str(self.path) + '-wal').stat().st_size, 0)
            result = ops.backup_production(self.manifest, 'snapshot')
            self.assertFalse(result['databaseReplaced'])
            self.assertFalse(result['offHostCopyVerified'])
            self.assertEqual(result['schemaVersion'], SCHEMA_VERSION)
            self.assertEqual(self.scalar('SELECT high_water FROM clock_state', path=self.snapshot()), 99999999)
            restored = ops.restore_quarantine(self.manifest, 'snapshot', 'restore')
            self.assertFalse(restored['activationAllowed'])
            self.assertEqual(self.scalar('SELECT high_water FROM clock_state', path=self.restored() / runtime.DATABASE), 99999999)
            quarantine = json.loads((self.restored() / ops.QUARANTINE_MARKER).read_bytes())
            self.assertEqual(quarantine['state'], 'ValidatedQuarantine')
            self.assertFalse((self.restored() / runtime.MARKER).exists())
            self.assertEqual(keeper.execute('SELECT high_water FROM clock_state').fetchone()[0], 99999999)
        self.assertEqual((self.manifest.data_directory / runtime.MARKER).read_bytes(), marker_before)

    def test_snapshot_receipt_binds_nonce_manifest_and_schema_without_private_data(self):
        ops.backup_production(self.manifest, 'snapshot')
        proof = json.loads(self.receipt().read_bytes())
        marker = runtime.ownership_metadata(self.manifest)
        self.assertEqual(proof['state'], 'Ready')
        self.assertEqual(proof['schemaVersion'], SCHEMA_VERSION)
        for key in ('nonce', 'manifestSHA256', 'publicOrigin', 'deploymentId', 'identityScope'):
            self.assertEqual(proof[key], marker[key])
        raw = self.receipt().read_text('ascii')
        self.assertNotIn(str(self.fixture.root), raw)
        self.assertNotIn(self.identity['playerId'], raw)
        self.assertNotIn(self.identity['token'], raw)
        self.assertEqual(hashlib.sha256(self.snapshot().read_bytes()).hexdigest(), proof['sha256'])

    def test_invalid_names_timeouts_and_existing_destinations_preserve_files(self):
        for name in ('', '../other', 'a/b', 'a\\b', 'a.sqlite3', 'CON', 'LPT1', 'x' * 49):
            with self.subTest(name=name), self.assertRaises(ops.ProductionOpsError):
                ops.backup_production(self.manifest, name)
        for timeout in (0, 601, True, float('nan')):
            with self.assertRaises(ops.ProductionOpsError):
                ops.backup_production(self.manifest, 'snapshot', timeout_seconds=timeout)
        self.assertEqual(list((self.manifest.data_directory / 'backups').iterdir()), [])
        self.snapshot().write_bytes(b'owned-operator-file')
        with self.assertRaises(ops.ProductionOpsError):
            ops.backup_production(self.manifest, 'snapshot')
        self.assertEqual(self.snapshot().read_bytes(), b'owned-operator-file')
        self.assertFalse(self.receipt().exists())

    def test_failed_copy_preserves_pending_receipt_and_blocks_restore(self):
        with patch.object(ops, 'backup_database', side_effect=OperationError('synthetic_copy_interruption')):
            with self.assertRaises(OperationError):
                ops.backup_production(self.manifest, 'snapshot')
        self.assertEqual(json.loads(self.receipt().read_bytes())['state'], 'Pending')
        with self.assertRaises(ops.ProductionOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'restore')
        self.assertFalse(self.restored().exists())

    def test_tampered_foreign_pending_old_schema_and_sidecar_restore_reject_before_root(self):
        for variant in ('tampered', 'foreign', 'pending', 'old_schema', 'sidecar'):
            with self.subTest(variant=variant):
                name = 'snapshot_' + variant
                ops.backup_production(self.manifest, name)
                proof = json.loads(self.receipt(name).read_bytes())
                if variant == 'tampered':
                    with self.snapshot(name).open('ab') as file:
                        file.write(b'tampered')
                elif variant == 'sidecar':
                    Path(str(self.snapshot(name)) + '-wal').write_bytes(b'not-standalone')
                else:
                    key, value = {'foreign': ('nonce', 'f' * 32), 'pending': ('state', 'Pending'),
                                  'old_schema': ('schemaVersion', SCHEMA_VERSION - 1)}[variant]
                    proof[key] = value
                    self.receipt(name).write_bytes(ops._bytes(proof))
                with self.assertRaises(ops.ProductionOpsError):
                    ops.restore_quarantine(self.manifest, name, variant)
                self.assertFalse(self.restored(variant).exists())

    def test_failed_restore_remains_blocked_and_never_adopted(self):
        ops.backup_production(self.manifest, 'snapshot')
        with patch.object(ops, 'restore_database', side_effect=OperationError('synthetic_restore_interruption')):
            with self.assertRaises(OperationError):
                ops.restore_quarantine(self.manifest, 'snapshot', 'restore')
        quarantine = json.loads((self.restored() / ops.QUARANTINE_MARKER).read_bytes())
        self.assertEqual(quarantine['state'], 'RestoreQuarantinedPending')
        with self.assertRaises(ops.ProductionOpsError):
            ops.restore_quarantine(self.manifest, 'snapshot', 'restore')
        with self.assertRaises(runtime.ProductionError):
            runtime.initialize_owned_data(self.manifest)
        self.assertFalse((self.restored() / runtime.MARKER).exists())

    def test_owner_nonce_change_during_copy_never_finalizes_backup_or_quarantine(self):
        marker_path = self.manifest.data_directory / runtime.MARKER
        original_marker = marker_path.read_bytes()
        original_backup = ops.backup_database

        def change_owner():
            marker = json.loads(marker_path.read_bytes())
            marker['nonce'] = uuid.uuid4().hex
            marker_path.write_bytes(runtime._bytes(marker))

        def backup_then_change(*args, **kwargs):
            result = original_backup(*args, **kwargs)
            change_owner()
            return result

        with patch.object(ops, 'backup_database', side_effect=backup_then_change):
            with self.assertRaises(ops.ProductionOpsError) as failure:
                ops.backup_production(self.manifest, 'changed_owner')
        self.assertEqual(failure.exception.code, 'production_snapshot_owner_changed')
        self.assertEqual(json.loads(self.receipt('changed_owner').read_bytes())['state'], 'Pending')
        marker_path.write_bytes(original_marker)  # Restore only this disposable fault fixture.
        ops.backup_production(self.manifest, 'snapshot')
        original_restore = ops.restore_database

        def restore_then_change(*args, **kwargs):
            result = original_restore(*args, **kwargs)
            change_owner()
            return result

        with patch.object(ops, 'restore_database', side_effect=restore_then_change):
            with self.assertRaises(ops.ProductionOpsError) as failure:
                ops.restore_quarantine(self.manifest, 'snapshot', 'changed_owner')
        self.assertEqual(failure.exception.code, 'production_snapshot_owner_changed')
        self.assertEqual(json.loads((self.restored('changed_owner') / ops.QUARANTINE_MARKER).read_bytes())['state'], 'RestoreQuarantinedPending')

    def test_staging_and_initialized_roots_are_never_adopted(self):
        with ProductionFixture122() as fresh:
            with self.assertRaises(runtime.ProductionError):
                ops.backup_production(fresh.manifest, 'snapshot')
            self.assertFalse((fresh.manifest.data_directory / runtime.DATABASE).exists())
            fresh.document['mode'] = 'staging'
            fresh.manifest_path.write_text(json.dumps(fresh.document), encoding='utf-8')
            with self.assertRaises(runtime.ProductionError):
                ops.queue_summary(fresh.manifest_path)

    def test_known_live_invoice_recovers_once_after_restart_without_callback_or_sdk_ack(self):
        before = json.loads(self.scalar('SELECT balances FROM wallets WHERE player_id=?', (self.identity['playerId'],)))[0]
        with self.fixture.context(purpose='operations') as app:
            order, invoice = self.known_invoice(app)
            first = ops.reconcile_bounded(app, self.manifest, max_jobs=5)
            self.assertEqual(first['worked'], 1)
            self.assertEqual(first['queue']['states']['Done'], 1)
            self.assertFalse(first['sdkAcknowledgementWritten'])
        self.fixture.now += 301
        with self.fixture.context(purpose='operations') as app:
            second = ops.reconcile_bounded(app, self.manifest, max_jobs=5)
            self.assertEqual(second['worked'], 1)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_credits'), 1)
        self.assertEqual(json.loads(self.scalar('SELECT balances FROM wallets WHERE player_id=?', (self.identity['playerId'],)))[0], before + 1000)
        self.assertEqual(self.scalar('SELECT state FROM commerce_delivery_ack'), 'Pending')
        self.assertTrue(all(sandbox is False for _, sandbox in self.fixture.provider.calls))
        self.assertNotIn(invoice, json.dumps(first))
        self.assertNotIn(order['orderId'], json.dumps(first))

    def test_provider_outage_keeps_pending_work_and_retries_without_double_credit(self):
        with self.fixture.context(purpose='operations') as app:
            self.known_invoice(app)
            with patch.object(self.fixture.provider, 'lookup', side_effect=ProviderUnavailable()):
                unavailable = ops.reconcile_bounded(app, self.manifest)
            self.assertEqual(unavailable['queue']['states']['Pending'], 1)
            self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_credits'), 0)
            self.fixture.now += 16
            recovered = ops.reconcile_bounded(app, self.manifest)
            self.assertEqual(recovered['queue']['states']['Done'], 1)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_credits'), 1)

    def test_expired_job_lease_fences_stale_completion(self):
        with self.fixture.context(purpose='operations') as app:
            self.known_invoice(app)
            worker = app.state.reconciliation_worker
            worker.seed_due()
            old = worker._claim('old-process', self.fixture.now)
            self.fixture.now += worker.lease_seconds + 1
            new = worker._claim('new-process', self.fixture.now)
            self.assertNotEqual(old['lease_token'], new['lease_token'])
            self.assertEqual(worker._finish(old, self.fixture.now), 'StaleLease')
            self.assertEqual(worker._finish(new, self.fixture.now), 'Done')

    def test_limits_and_wrong_api_purpose_reject_before_seeding(self):
        with self.fixture.context(purpose='operations') as app:
            for limits in ({'max_jobs': 0}, {'max_jobs': True}, {'max_jobs': 101}, {'seed_limit': 101},
                           {'poll_seconds': 29}, {'worker_id': 'line\nsecret'}):
                with self.subTest(limits=limits), self.assertRaises(ops.ProductionOpsError):
                    ops.reconcile_bounded(app, self.manifest, **limits)
            self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_reconcile_jobs'), 0)
        with self.fixture.context() as app:
            with self.assertRaises(runtime.ProductionError):
                ops.reconcile_bounded(app, self.manifest)

    def test_queue_summary_is_read_only_and_exposes_no_identifiers(self):
        with self.fixture.context(purpose='operations') as app:
            self.known_invoice(app)
            app.state.reconciliation_worker.seed_due()
        before = self.path.read_bytes()
        summary = ops.queue_summary(self.manifest)
        self.assertEqual(summary['states']['Pending'], 1)
        self.assertFalse(summary['databaseChanged'])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn(self.identity['playerId'], json.dumps(summary))

    def test_dead_jobs_remain_visible_without_automatic_resurrection(self):
        with self.fixture.context(purpose='operations') as app:
            self.known_invoice(app)
            worker = app.state.reconciliation_worker
            worker.max_attempts = 1
            with patch.object(self.fixture.provider, 'lookup', side_effect=ProviderUnavailable()):
                report = ops.reconcile_bounded(app, self.manifest)
            self.assertEqual(report['status'], 'operator_attention_required')
            self.assertEqual(report['queue']['states']['Dead'], 1)
            self.fixture.now += 1000
            repeat = ops.reconcile_bounded(app, self.manifest)
            self.assertEqual(repeat['worked'], 0)
            self.assertEqual(repeat['queue']['states']['Dead'], 1)

    def test_queue_observes_wall_time_when_durable_clock_is_stale_without_writing_it(self):
        with self.fixture.context(purpose='operations') as app:
            self.known_invoice(app)
            worker = app.state.reconciliation_worker
            worker.seed_due()
            claim = worker._claim('interrupted-worker', self.fixture.now)
        before = self.path.read_bytes()
        high_water = self.scalar('SELECT high_water FROM clock_state WHERE id=1')
        observed = high_water + 1000
        with patch.object(ops.time, 'time', return_value=observed):
            report = ops.queue_summary(self.manifest)
        self.assertEqual(report['expiredLeases'], 1)
        self.assertEqual(report['observedUtc'], observed)
        self.assertEqual(self.scalar('SELECT high_water FROM clock_state WHERE id=1'), high_water)
        self.assertEqual(self.path.read_bytes(), before)

    def test_supervisor_uses_one_owned_context_and_stops_after_a_bounded_batch(self):
        stop = threading.Event()
        emitted = []

        def emit(report):
            emitted.append(report)
            stop.set()

        # Retain the real runtime and inject only scripted external adapters.
        original = runtime.application_context
        with patch.object(runtime, 'application_context', side_effect=lambda manifest, purpose: self._scripted_context(original, purpose)):
            result = ops.supervise_reconciliation(self.manifest, stop_event=stop, emit=emit, interval_seconds=5, max_jobs=1)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(result['status'], 'stopped')
        self.assertFalse(result['sdkAcknowledgementWritten'])

    @contextlib.contextmanager
    def _scripted_context(self, original, purpose):
        with patch('hotr_backend.production_runtime122._create_worker', return_value=self.fixture.worker), \
             patch('hotr_backend.rustore_provider.RuStoreInvoiceProvider', return_value=self.fixture.provider), \
             original(self.manifest, purpose=purpose, clock=lambda: self.fixture.now) as app:
            yield app

    def test_active_reconciliation_drains_before_operations_lease_is_released(self):
        context = self.fixture.context(purpose='operations')
        app = context.__enter__()
        entered, release, closed = threading.Event(), threading.Event(), threading.Event()
        outcomes = []
        order, invoice = self.known_invoice(app)
        lookup = self.fixture.provider.lookup

        def delayed(number, sandbox):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('synthetic_wait_timeout')
            return lookup(number, sandbox)

        def run():
            try:
                outcomes.append(ops.reconcile_bounded(app, self.manifest, max_jobs=1))
            except Exception as error:
                outcomes.append(type(error).__name__)

        def close():
            context.__exit__(None, None, None)
            closed.set()

        with patch.object(self.fixture.provider, 'lookup', side_effect=delayed):
            worker = threading.Thread(target=run)
            worker.start()
            try:
                self.assertTrue(entered.wait(3))
                closer = threading.Thread(target=close)
                closer.start()
                self.assertFalse(closed.wait(0.1))
                with self.assertRaises(runtime.ProductionError):
                    with runtime._lock(self.manifest, runtime.OPERATIONS_LOCK):
                        pass
            finally:
                release.set()
                worker.join(5)
                if 'closer' in locals():
                    closer.join(5)
                else:
                    context.__exit__(None, None, None)
        self.assertFalse(worker.is_alive())
        self.assertTrue(closed.is_set())
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM commerce_credits'), 1)

    def test_cli_errors_export_no_private_input_or_provider_exception(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = ops.main(['backup', '--manifest', str(self.fixture.root / 'private-secret-path'), '--name', 'snapshot'])
        self.assertEqual(result, 1)
        self.assertNotIn('private-secret-path', output.getvalue())
        self.assertNotIn(str(self.fixture.root), output.getvalue())


if __name__ == '__main__':
    unittest.main()
