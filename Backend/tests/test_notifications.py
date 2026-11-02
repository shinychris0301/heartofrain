"""Actual AES-GCM/SQLite/worker tests with ephemeral keys and fake provider only."""
import base64
import concurrent.futures
import json
import multiprocessing
import os
import secrets
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from dataclasses import replace
from pathlib import Path

from Crypto.Cipher import AES
from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.commerce import Commerce
from hotr_backend.commerce_schemas import CreateCommerceOrder, ReconcileCommerceOrder
from hotr_backend.notification_worker import ReconciliationWorker
from hotr_backend.notifications import NotificationInbox, file_key_source
from hotr_backend.rustore_provider import ProviderUnavailable, VerifiedInvoice
from hotr_backend.service import Actor, Authority, ServiceError
from hotr_backend.storage import Database

CONFIG = Path(__file__).resolve().parents[1] / 'config'


class Provider:
    configured = True

    def __init__(self):
        self.values, self.calls, self.fail, self.observer = {}, 0, False, None

    def lookup(self, invoice, sandbox):
        self.calls += 1
        if self.observer:
            self.observer()
        if self.fail:
            raise ProviderUnavailable()
        return self.values[invoice]


def worker_process(database_path, config_path, now, invoice, result):
    """A new spawned process reopens only durable work, not parent callback state."""
    provider = Provider()
    provider.values[invoice.invoice_id] = invoice
    authority = Authority(Database(database_path), CONFIG, lambda: now)
    commerce = Commerce(authority, Path(config_path), provider)
    worker = ReconciliationWorker(NotificationInbox(authority, commerce))
    outcome = worker.run_once('separate-process')
    result.put((os.getpid(), outcome))


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-notifications-')
        self.root = Path(self.temp.name)
        self.path = self.root / 'authority.sqlite3'
        self.now = 300 * 86400
        self.key = secrets.token_bytes(32)
        self.keyfile = self.root / 'external-key'
        self.keyfile.write_text(base64.b64encode(self.key).decode(), encoding='ascii')
        self.config = self.root / 'commerce.json'
        self.config.write_text(json.dumps({'version': 'synthetic-notification-test', 'enabled': True,
            'appId': 123, 'sandbox': True, 'products': [{'id': 'fixture', 'storeProductId': 'synthetic_1000',
                'enabled': True, 'coins': 1000, 'amountMinor': 9900, 'currency': 'RUB'}]}), encoding='utf-8')
        self.provider = Provider()
        self.open()
        self.identity = self.authority.provision(lifetime=2_592_000)
        self.actor = Actor(self.identity['playerId'], self.now)
        self.order = self.commerce.create(self.actor, CreateCommerceOrder(commandId=uuid.uuid4().hex, productId='fixture'))
        self.invoice = VerifiedInvoice('1001', str(uuid.uuid4()), 123, True, self.order['orderId'],
            self.order['sdk']['productId'], self.actor.player, self.order['sdk']['developerPayload'],
            9900, 'RUB', 'CONFIRMED', 'PENDING')
        self.provider.values['1001'] = self.invoice

    def open(self):
        self.database = Database(self.path)
        self.authority = Authority(self.database, CONFIG, lambda: self.now)
        self.commerce = Commerce(self.authority, self.config, self.provider)
        self.inbox = NotificationInbox(self.authority, self.commerce, file_key_source(self.keyfile),
                                       ('127.0.0.1/32',), enabled=True)
        self.worker = ReconciliationWorker(self.inbox)

    def tearDown(self):
        self.temp.cleanup()

    def wire(self, *, changes=None, payload_changes=None, outer_changes=None, key=None, data=None):
        body = {'product_code': self.invoice.product_id, 'change_status_time': '2026-10-25T12:00:00Z',
                'status_old': 'executed', 'status_new': 'confirmed', 'purchase_token': secrets.token_urlsafe(24),
                'invoice_id': self.invoice.invoice_id, 'order_id': self.invoice.order_id,
                'purchase_id': self.invoice.purchase_id, 'developer_payload': self.invoice.developer_payload}
        body.update(changes or {})
        payload = {'app_id': 123, 'notification_type': 'INVOICE_STATUS_SANDBOX',
                   'data': json.dumps(data if data is not None else body)}
        payload.update(payload_changes or {})
        cipher = AES.new(key if key is not None else self.key, AES.MODE_GCM, nonce=secrets.token_bytes(12), mac_len=16)
        ciphertext, tag = cipher.encrypt_and_digest(json.dumps(payload).encode())
        outer = {'id': uuid.uuid4().hex, 'timestamp': '2026-10-25T12:00:01.123+0000',
                 'payload': base64.b64encode(cipher.nonce + ciphertext + tag).decode()}
        outer.update(outer_changes or {})
        return json.dumps(outer).encode(), body

    def receive(self, body):
        return self.inbox.receive(body, '127.0.0.1')

    def counts(self):
        with self.database.connect() as db:
            return tuple(db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in
                         ('commerce_notification_inbox', 'commerce_reconcile_jobs', 'commerce_credits'))

    def job(self):
        with self.database.connect() as db:
            return dict(db.execute('SELECT * FROM commerce_reconcile_jobs').fetchone())

    def denied(self, body, status=400):
        with self.assertRaises(ServiceError) as error:
            self.receive(body)
        self.assertEqual(error.exception.status, status)

    def test_disabled_source_and_configuration_never_use_a_secret_or_provider(self):
        used = []
        disabled = NotificationInbox(self.authority, self.commerce, lambda: used.append(True))
        with self.assertRaises(ServiceError) as error:
            disabled.receive(b'{}', '127.0.0.1')
        self.assertEqual(error.exception.status, 503)
        with self.assertRaises(ServiceError) as error:
            self.inbox.receive(b'{}', '95.163.133.1')
        self.assertEqual(error.exception.status, 403)
        with self.assertRaises(ValueError):
            NotificationInbox(self.authority, self.commerce, lambda: '', (), enabled=True)
        self.assertEqual((used, self.provider.calls, self.counts()), ([], 0, (0, 0, 0)))

    def test_documented_wire_decrypts_then_only_durably_queues(self):
        raw, data = self.wire()
        result = self.receive(raw)
        self.assertEqual(result, {'accepted': True, 'duplicate': False, 'disposition': 'Queued'})
        self.assertEqual(self.counts(), (1, 1, 0))
        self.assertEqual(self.provider.calls, 0)
        with self.database.connect() as db:
            stored = '\n'.join(db.iterdump())
        self.assertTrue(data['purchase_token'] not in stored)
        self.assertTrue(raw.decode() not in stored)
        self.assertTrue(base64.b64encode(self.key).decode() not in stored)

    def test_tampered_cipher_tag_key_and_truncated_iv_fail_closed(self):
        raw, _ = self.wire()
        envelope = json.loads(raw)
        encrypted = bytearray(base64.b64decode(envelope['payload']))
        for offset in (0, 13, len(encrypted) - 1):
            changed = bytearray(encrypted)
            changed[offset] ^= 1
            self.denied(json.dumps(dict(envelope, payload=base64.b64encode(changed).decode())).encode())
        self.denied(self.wire(key=secrets.token_bytes(32))[0])
        self.denied(json.dumps(dict(envelope, payload=base64.b64encode(b'bad').decode())).encode())
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_exact_app_environment_binding_and_scalar_types(self):
        for changes in ({'app_id': 124}, {'app_id': True}, {'notification_type': 'INVOICE_STATUS'},
                        {'notification_type': 'SUBSCRIPTION_EVENT_SANDBOX'}, {'data': {}}):
            self.denied(self.wire(payload_changes=changes)[0])
        for changes in ({'invoice_id': '01'}, {'invoice_id': '1001\n'}, {'order_id': 'x' * 32},
                        {'product_code': 'wrong_product'}, {'developer_payload': 'wrong'},
                        {'purchase_id': 'invalid'}, {'status_new': 'UNREVIEWED'}):
            self.denied(self.wire(changes=changes)[0], 409 if 'product_code' in changes or 'developer_payload' in changes else 400)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_duplicate_json_and_oversized_body_rejected(self):
        self.denied(b'{"id":"a","id":"b","timestamp":"x","payload":"x"}')
        self.denied(b' ' * 65_537)
        self.denied(b'\xff')
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_replay_outer_id_timestamp_and_new_nonce_do_not_duplicate_jobs(self):
        raw, _ = self.wire()
        self.receive(raw)
        envelope = json.loads(raw)
        envelope.update(id='outer-id-is-not-authority', timestamp='2024-01-01T00:00:00Z')
        self.assertTrue(self.receive(json.dumps(envelope).encode())['duplicate'])
        self.assertTrue(self.receive(self.wire()[0])['duplicate'])
        self.assertEqual((self.counts(), self.job()['requested_revision']), ((1, 1, 0), 1))

    def test_concurrent_duplicate_delivery_commits_one_inbox_and_one_job(self):
        raw, _ = self.wire()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(self.receive, [raw] * 12))
        self.assertEqual(sum(not value['duplicate'] for value in results), 1)
        self.assertEqual(self.counts(), (1, 1, 0))

    def test_connection_test_and_unmatched_order_never_create_grants(self):
        raw, _ = self.wire(payload_changes={'notification_type': 'TEST_EVENT_SANDBOX'}, data={'test': 'TEST'})
        self.assertEqual(self.receive(raw)['disposition'], 'Test')
        raw, _ = self.wire(changes={'order_id': uuid.uuid4().hex})
        self.assertEqual(self.receive(raw)['disposition'], 'Unmatched')
        self.assertEqual(self.counts(), (2, 0, 0))

    def test_external_key_rotation_is_reread_without_old_key_fallback(self):
        old, _ = self.wire()
        self.key = secrets.token_bytes(32)
        self.keyfile.write_text(base64.b64encode(self.key).decode() + '\n', encoding='ascii')
        self.denied(old)
        self.assertTrue(self.receive(self.wire()[0])['accepted'])
        self.keyfile.write_text('invalid', encoding='ascii')
        with self.assertRaises(ServiceError) as error:
            self.receive(self.wire()[0])
        self.assertEqual(error.exception.status, 503)

    def test_intake_and_job_are_one_atomic_transaction(self):
        with self.database.transaction() as db:
            db.execute("CREATE TRIGGER reject_job BEFORE INSERT ON commerce_reconcile_jobs BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        raw, _ = self.wire()
        with self.assertRaises(sqlite3.IntegrityError):
            self.receive(raw)
        self.assertEqual(self.counts(), (0, 0, 0))
        with self.database.transaction() as db:
            db.execute('DROP TRIGGER reject_job')
        self.assertTrue(self.receive(raw)['accepted'])

    def test_claimed_confirmation_requeries_provider_and_delivers_exactly_once(self):
        self.receive(self.wire()[0])
        result = self.worker.run_once('worker-a')
        self.assertEqual((result['state'], result['orderState'], self.counts()), ('Done', 'Confirmed', (1, 1, 1)))
        self.assertFalse(self.worker.run_once('worker-b')['worked'])
        self.receive(self.wire(changes={'change_status_time': '2026-10-25T12:01:00Z'})[0])
        self.worker.run_once('worker-b')
        self.assertEqual(self.counts(), (2, 1, 1))
        self.assertEqual(self.provider.calls, 2)

    def test_callback_confirmation_does_not_deliver_a_provider_paid_hold(self):
        self.provider.values['1001'] = replace(self.invoice, status='PAID')
        self.receive(self.wire()[0])
        self.assertEqual(self.worker.run_once('worker')['orderState'], 'Held')
        self.assertEqual(self.counts()[2], 0)
        self.provider.values['1001'] = self.invoice
        self.now += 15
        self.assertEqual(self.worker.run_once('worker')['orderState'], 'Confirmed')
        self.assertEqual(self.counts()[2], 1)

    def test_binding_mismatch_from_provider_is_permanent_without_credit(self):
        self.provider.values['1001'] = replace(self.invoice, app_user_id=uuid.uuid4().hex)
        self.receive(self.wire()[0])
        result = self.worker.run_once('worker')
        self.assertEqual((result['state'], result['error'], self.counts()[2]), ('Dead', 'purchase_binding_mismatch', 0))

    def test_refunding_notification_retry_records_sticky_review_without_credit(self):
        # The authenticated hint itself still has no grant/quarantine authority.
        # First the provider is unavailable; durable work survives and then the
        # fresh invoice lookup proves REFUNDING, which must not be rejected503.
        self.provider.values['1001'] = replace(self.invoice, status='REFUNDING')
        self.provider.fail = True
        self.receive(self.wire(changes={'status_new': 'refunding'})[0])
        first = self.worker.run_once('worker')
        self.assertEqual((first['state'], first['error'], self.counts()[2]), ('Pending', 'provider_unavailable', 0))
        self.provider.fail = False
        self.now += 15
        self.open()
        second = self.worker.run_once('worker-reopened')
        self.assertEqual((second['state'], second['orderState'], self.counts()[2]), ('Done', 'RefundReview', 0))
        self.provider.values['1001'] = self.invoice
        self.receive(self.wire(changes={'change_status_time': '2026-10-25T12:04:00Z'})[0])
        stale = self.worker.run_once('worker-stale-confirmation')
        self.assertEqual((stale['state'], stale['orderState'], self.counts()[2]), ('Done', 'RefundReview', 0))
        self.assertEqual(self.commerce.order(self.actor, self.order['orderId'])['state'], 'RefundReview')

    def test_transient_failure_backoff_limit_and_new_authenticated_redrive(self):
        self.receive(self.wire()[0])
        self.provider.fail = True
        worker = ReconciliationWorker(self.inbox, max_attempts=2)
        self.assertEqual(worker.run_once('worker')['state'], 'Pending')
        self.assertFalse(worker.run_once('worker')['worked'])
        self.now += 15
        self.assertEqual(worker.run_once('worker')['state'], 'Dead')
        self.assertFalse(worker.run_once('worker')['worked'])
        self.provider.fail = False
        self.receive(self.wire(changes={'change_status_time': '2026-10-25T12:02:00Z'})[0])
        self.assertEqual(worker.run_once('worker')['state'], 'Done')
        self.assertEqual(self.counts()[2], 1)

    def test_new_hint_during_lookup_is_not_lost_and_refund_remains_sticky(self):
        self.receive(self.wire()[0])
        def newer():
            self.provider.observer = None
            self.receive(self.wire(changes={'status_new': 'refunded', 'status_old': 'confirmed'})[0])
        self.provider.observer = newer
        self.assertEqual(self.worker.run_once('worker')['state'], 'Pending')
        self.provider.values['1001'] = replace(self.invoice, status='REFUNDED')
        self.assertEqual(self.worker.run_once('worker')['orderState'], 'RefundReview')
        self.provider.values['1001'] = self.invoice
        self.receive(self.wire(changes={'change_status_time': '2026-10-25T12:03:00Z'})[0])
        self.assertEqual(self.worker.run_once('worker')['orderState'], 'RefundReview')
        self.assertEqual(self.counts()[2], 1)

    def test_expired_lease_fences_stale_completion(self):
        self.receive(self.wire()[0])
        old = self.worker._claim('old-worker', self.now)
        self.now += 61
        new = self.worker._claim('new-worker', self.now)
        self.assertNotEqual(old['lease_token'], new['lease_token'])
        self.assertEqual(self.worker._finish(old, self.now), 'StaleLease')
        self.assertEqual(self.job()['lease_token'], new['lease_token'])
        self.assertEqual(self.worker._finish(new, self.now), 'Done')

    def test_lost_postcommit_result_retries_without_duplicate_credit(self):
        self.receive(self.wire()[0])
        def fail(phase):
            if phase == 'AfterCreditCommit':
                raise RuntimeError('synthetic lost reply')
        self.commerce.checkpoint = fail
        self.assertEqual(self.worker.run_once('worker')['state'], 'Pending')
        self.assertEqual(self.counts()[2], 1)
        self.commerce.checkpoint = None
        self.now += 15
        self.assertEqual(self.worker.run_once('worker')['state'], 'Done')
        self.assertEqual(self.counts()[2], 1)

    def test_database_reopen_and_distinct_process_resume_durable_job(self):
        self.receive(self.wire()[0])
        context = multiprocessing.get_context('spawn')
        queue = context.Queue()
        process = context.Process(target=worker_process, args=(str(self.path), str(self.config), self.now, self.invoice, queue))
        process.start()
        try:
            process.join(15)
            self.assertFalse(process.is_alive())
            self.assertEqual(process.exitcode, 0)
            child_pid, outcome = queue.get(timeout=3)
            self.assertNotEqual(child_pid, os.getpid())
            self.assertEqual(outcome['state'], 'Done')
        finally:
            if process.is_alive():
                process.terminate()
                process.join(5)
            queue.close()
        self.open()
        self.assertEqual(self.counts()[2], 1)
        self.assertFalse(self.worker.run_once('reopened')['worked'])

    def test_seed_known_pending_invoice_and_later_confirmed_poll(self):
        self.provider.fail = True
        with self.assertRaises(ServiceError):
            self.commerce.reconcile(self.actor, self.order['orderId'], ReconcileCommerceOrder(invoiceId='1001'))
        self.assertEqual(self.worker.seed_due(), 1)
        self.assertEqual(self.worker.seed_due(), 0)
        self.provider.fail = False
        self.assertEqual(self.worker.run_once('worker')['state'], 'Done')
        self.assertEqual(self.worker.seed_due(), 0)
        self.now += 300
        self.assertEqual(self.worker.seed_due(), 1)
        self.worker.run_once('worker')
        self.assertEqual(self.counts()[2], 1)

    def test_bounded_runner_and_worker_identifiers(self):
        with self.assertRaises(ValueError):
            self.worker.run_once('unbounded\nworker')
        with self.assertRaises(ValueError):
            self.worker.run_bounded('worker', 1001)
        with self.assertRaises(ValueError):
            self.worker.seed_due(limit=101)
        self.assertEqual(self.worker.run_bounded('worker', 1), [{'worked': False, 'state': 'Idle'}])

    def test_mounted_route_requires_actual_peer_content_type_and_environment(self):
        app = create_app(self.path, CONFIG, lambda: self.now, commerce_provider=self.provider,
            commerce_config_path=self.config, notifications_enabled=True,
            notification_key_source=file_key_source(self.keyfile), notification_allowed_networks=('127.0.0.1/32',))
        raw, _ = self.wire()
        path = '/v1/commerce/notifications/rustore/sandbox'
        with TestClient(app, client=('127.0.0.1', 9000)) as client:
            response = client.post(path, content=raw, headers={'Content-Type': 'application/json'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['disposition'], 'Queued')
            self.assertEqual(client.post(path, content=raw, headers={'Content-Type': 'text/plain'}).status_code, 415)
            self.assertEqual(client.post('/v1/commerce/notifications/rustore/production', content=raw,
                headers={'Content-Type': 'application/json'}).status_code, 503)
        with TestClient(app, client=('192.0.2.10', 9000)) as client:
            response = client.post(path, content=raw, headers={'Content-Type': 'application/json',
                                                             'X-Forwarded-For': '127.0.0.1'})
            self.assertEqual(response.status_code, 403)
        self.assertEqual((self.provider.calls, self.counts()), (0, (1, 1, 0)))

    def test_worker_final_credit_guard_closes_concurrent_account_deletion(self):
        self.receive(self.wire()[0])
        def deletion_between_query_and_credit():
            self.provider.observer = None
            with self.database.transaction() as db:
                db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.actor.player, self.now))
        self.provider.observer = deletion_between_query_and_credit
        result = self.worker.run_once('worker')
        self.assertEqual((result['state'], result['error'], self.counts()[2]),
                         ('Dead', 'account_deletion_requested', 0))

    def test_deleted_account_job_never_calls_provider(self):
        self.receive(self.wire()[0])
        with self.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.actor.player, self.now))
        result = self.worker.run_once('worker')
        self.assertEqual((result['state'], self.provider.calls, self.counts()[2]), ('Dead', 0, 0))

    def contention(self, start_delay=0):
        entered = threading.Event()
        release = threading.Event()
        raw = self.wire()[0]
        held = []
        def writer():
            with self.database.transaction():
                started = time.perf_counter()
                entered.set()
                # Keep the actual lock through the receive attempt, even if
                # the caller is descheduled after observing entered. A six-
                # second failsafe still bounds a broken/unbounded receiver.
                release.wait(6)
                remainder = 2 - (time.perf_counter() - started)
                if remainder > 0:
                    time.sleep(remainder)
                held.append(time.perf_counter() - started)
        thread = threading.Thread(target=writer)
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            if start_delay:
                time.sleep(start_delay)
            started = time.perf_counter()
            with self.assertRaises(sqlite3.OperationalError):
                self.receive(raw)
            self.assertLess(time.perf_counter() - started, 3)
        finally:
            release.set()
            thread.join(4)
        self.assertFalse(thread.is_alive())
        self.assertGreaterEqual(held[0], 1.9)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_contention_control_survives_delayed_request_start(self):
        self.contention(start_delay=2.1)

    def test_actual_writer_contention_bounds_receipt_clock_wait(self):
        self.contention()

    def test_actual_writer_contention_bounds_receipt_commit_wait(self):
        # This independent control reaches the second transaction while an
        # actual writer is held. It does not claim to exercise clock authority.
        self.authority._now = lambda **kwargs: self.now
        self.contention()
