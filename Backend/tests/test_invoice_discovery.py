"""Durable listing hints plus fresh v2 verification; no live payment/Console claim."""
import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import httpx

from hotr_backend.__main__ import main
from hotr_backend.api import create_app
from hotr_backend.commerce_schemas import CreateCommerceOrder
from hotr_backend.invoice_discovery import DiscoveryScanner, InvoiceHint, InvoicePage, RuStoreInvoiceLister, MAX_RESPONSE
from hotr_backend.rustore_provider import InvalidProviderResponse, ProviderUnavailable, RuStoreInvoiceProvider
from hotr_backend.service import Actor, ServiceError

CONFIG = Path(__file__).resolve().parents[1] / 'config'


class SyntheticSandboxLister:
    """Provider-independent test seam, not a documented RuStore sandbox listing."""
    configured = supports_sandbox = True

    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def page(self, app_id, day, page_number, page_size, **kwargs):
        self.calls.append((app_id, day, page_number, page_size, kwargs))
        value = self.pages[page_number]
        if isinstance(value, Exception):
            raise value
        return value


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-discovery-')
        self.root = Path(self.temp.name)
        self.path, self.config = self.root / 'authority.sqlite3', self.root / 'commerce.json'
        self.now, self.day = 300 * 86400, '2026-10-25'
        self.config.write_text(json.dumps({'version': 'synthetic-discovery-test', 'enabled': True,
            'appId': 123, 'sandbox': True, 'products': [{'id': 'fixture', 'storeProductId': 'synthetic_1000',
                'enabled': True, 'coins': 1000, 'amountMinor': 9900, 'currency': 'RUB'}]}), encoding='utf-8')
        self.http_calls, self.responses = [], {}
        self.provider = RuStoreInvoiceProvider(lambda: 'ephemeral-test-JWE', httpx.MockTransport(self.lookup))
        self.open()
        self.identity = self.app.state.authority.provision(lifetime=2_592_000)
        self.actor = Actor(self.identity['playerId'], self.now)
        self.order = self.app.state.commerce.create(self.actor, CreateCommerceOrder(commandId=uuid.uuid4().hex, productId='fixture'))
        self.hint = InvoiceHint('1001', str(uuid.uuid4()), 123, self.order['orderId'],
            self.order['sdk']['productId'], self.actor.player, self.order['sdk']['developerPayload'], 9900, 'RUB', 'CONFIRMED')
        self.responses['1001'] = self.entry(self.hint)

    def open(self):
        self.app = create_app(self.path, CONFIG, lambda: self.now, commerce_provider=self.provider,
                              commerce_config_path=self.config, notifications_enabled=False, identity_enabled=False)
        self.authority, self.commerce = self.app.state.authority, self.app.state.commerce
        self.database, self.worker = self.authority.database, self.app.state.reconciliation_worker

    def tearDown(self):
        self.temp.cleanup()

    def lookup(self, request):
        self.http_calls.append(str(request.url))
        self.assertEqual(request.url.scheme, 'https')
        self.assertEqual(request.url.host, 'public-api-m.rustore.ru')
        self.assertEqual(request.headers['Public-Token'], 'ephemeral-test-JWE')
        return httpx.Response(200, json={'code': 'OK', 'body': self.responses[request.url.path.rsplit('/', 1)[-1]]})

    @staticmethod
    def entry(hint):
        return {'invoiceId': int(hint.invoice_id), 'purchaseId': hint.purchase_id, 'appId': hint.app_id,
            'appUserId': hint.app_user_id, 'developerPayload': hint.developer_payload, 'invoiceStatus': hint.status,
            'acknowledgementState': 'PENDING', 'invoiceDate': '2026-10-25T12:00:00Z',
            'order': {'orderId': hint.order_id, 'itemCode': hint.product_id, 'amountCurrent': hint.amount_minor,
                      'currency': hint.currency}, 'paymentInfo': {'cardToken': 'sensitive-fixture-must-not-persist'},
            'purchase_token': 'sensitive-purchase-token-must-not-persist'}

    @staticmethod
    def page(hints, number=0, pages=1, total=None):
        return InvoicePage(number, pages, len(hints) if total is None else total, tuple(hints))

    def scanner(self, pages=None, *, enabled=True):
        lister = SyntheticSandboxLister(pages if pages is not None else [self.page([self.hint])])
        return DiscoveryScanner(self.authority, self.commerce, lister, enabled=enabled)

    def scan(self, scanner, **kwargs):
        return scanner.scan_once(123, self.day, True, 'fixture-worker', **kwargs)

    def counts(self):
        with self.database.connect() as db:
            return tuple(db.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0] for name in
                ('commerce_discovery_cursors', 'commerce_discovery_seen', 'commerce_reconcile_jobs',
                 'commerce_invoice_requests', 'commerce_credits', 'commerce_notification_inbox'))

    def cursor(self):
        with self.database.connect() as db:
            return dict(db.execute('SELECT * FROM commerce_discovery_cursors ORDER BY invoice_date DESC').fetchone())

    def test_synthetic_sandbox_lost_client_and_all_callbacks_recovers_by_real_v2_adapter_once(self):
        before = self.app.state.wallet.view(self.actor)['coins']
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0, 0))
        self.assertEqual(self.worker.seed_due(), 0)  # Original seed cannot enumerate an unknown invoice.
        result = self.scan(self.scanner())
        self.assertEqual((result['queued'], result['grantsFromListing']), (1, False))
        self.assertEqual(self.counts(), (1, 1, 1, 0, 0, 0))
        self.assertEqual(self.http_calls, [])
        self.assertEqual(self.worker.run_once('fixture-worker')['orderState'], 'Confirmed')
        self.assertEqual(self.http_calls, ['https://public-api-m.rustore.ru/public/sandbox/v2/invoices/1001'])
        self.assertEqual(self.app.state.wallet.view(self.actor)['coins'], before + 1000)
        self.scan(self.scanner(), rescan=True)
        self.worker.run_once('fixture-worker')
        self.assertEqual(self.counts()[4:], (1, 0))
        self.assertEqual(self.app.state.wallet.view(self.actor)['coins'], before + 1000)

    def test_official_production_http_listing_queues_but_does_not_waive_live_worker_gate(self):
        config = json.loads(self.config.read_text())
        config['sandbox'] = False
        self.config.write_text(json.dumps(config))
        with self.database.transaction() as db:
            db.execute('UPDATE commerce_orders SET sandbox=0 WHERE id=?', (self.order['orderId'],))
        self.open()  # Existing immutable live order fixture; create-live endpoint remains blocked.
        requested = []
        def listing(request):
            requested.append(request)
            return httpx.Response(200, json=self.list_response([self.entry(self.hint)]))
        scanner = DiscoveryScanner(self.authority, self.commerce,
            RuStoreInvoiceLister(lambda: 'synthetic-JWE', httpx.MockTransport(listing)), enabled=True)
        result = scanner.scan_once(123, self.day, False, 'fixture', page_size=20)
        self.assertEqual((result['queued'], len(requested)), (1, 1))
        req = requested[0]
        self.assertEqual(str(req.url.copy_with(query=None)), 'https://public-api-m.rustore.ru/public/applications/123/invoices')
        self.assertEqual(dict(req.url.params), {'invoiceStatuses': 'confirmed', 'invoiceDate': self.day, 'pageNumber': '0', 'pageSize': '20'})
        self.assertEqual(req.headers['Public-Token'], 'synthetic-JWE')
        self.assertEqual(self.worker.run_once('fixture')['error'], 'live_commerce_requires_wallet_integration')
        self.assertEqual((self.http_calls, self.counts()[4]), ([], 0))

    @staticmethod
    def list_response(entries, **changes):
        body = {'pageNumber': 0, 'pageSize': len(entries), 'totalPages': 1 if entries else 0,
                'totalElements': len(entries), 'content': entries}
        body.update(changes)
        return {'code': 'OK', 'body': body}

    def test_optional_listing_identity_never_substitutes_for_required_provider_identity(self):
        self.scan(self.scanner([self.page([replace(self.hint, app_user_id=None, developer_payload=None)])]))
        self.responses['1001']['appUserId'] = 'wrong-provider-account'
        outcome = self.worker.run_once('fixture')
        self.assertEqual((outcome['state'], outcome['error'], self.counts()[4]), ('Dead', 'purchase_binding_mismatch', 0))

    def test_mismatched_and_unrelated_listing_entries_are_ignored(self):
        for changes in ({'order_id': uuid.uuid4().hex}, {'product_id': 'wrong'}, {'app_user_id': uuid.uuid4().hex},
                        {'developer_payload': 'wrong'}, {'amount_minor': 9901}, {'currency': 'USD'}):
            with self.subTest(changes=changes):
                result = self.scan(self.scanner([self.page([replace(self.hint, **changes)])]), rescan=True)
                self.assertEqual((result['queued'], result['ignored'], self.counts()[2]), (0, 1, 0))

    def test_known_invoice_and_purchase_cannot_be_rebound_by_listing(self):
        with self.database.transaction() as db:
            db.execute('UPDATE commerce_orders SET invoice_id=?,purchase_id=? WHERE id=?',
                       ('2000', str(uuid.uuid4()), self.order['orderId']))
        result = self.scan(self.scanner())
        self.assertEqual((result['queued'], result['ignored']), (0, 1))

    def test_deleted_account_does_not_queue_and_deleted_after_queue_never_credits(self):
        self.scan(self.scanner())
        with self.database.transaction() as db:
            db.execute("INSERT INTO account_states(player_id,state,requested_at) VALUES(?,'DeletionRequested',?)", (self.actor.player, self.now))
        self.assertEqual(self.worker.run_once('fixture')['state'], 'Dead')
        result = self.scan(self.scanner(), rescan=True)
        self.assertEqual((result['queued'], result['ignored'], self.counts()[4]), (0, 1, 0))

    def test_pagination_bounded_batch_resumes_after_database_reopen(self):
        pages = [self.page([self.hint], pages=2, total=2), self.page([], number=1, pages=2, total=2)]
        first = self.scanner(pages)
        self.assertEqual(self.scan(first, max_pages=1)['state'], 'Pending')
        self.assertEqual((self.cursor()['next_page'], len(first.lister.calls)), (1, 1))
        self.open()
        second = self.scanner(pages)
        self.assertEqual(self.scan(second)['state'], 'Complete')
        self.assertEqual(second.lister.calls[0][2], 1)
        self.assertEqual(self.scan(second)['pages'], 0)
        self.assertEqual(self.counts()[2], 1)

    def test_separate_process_restarts_cursor_and_durable_queue_without_parent_state(self):
        scanner = self.scanner([self.page([self.hint], pages=2, total=2)])
        self.scan(scanner, max_pages=1)
        # No live objects or ephemeral provider result crosses this process boundary.
        script = '''
import json,sys
from pathlib import Path
from hotr_backend.api import create_app
from hotr_backend.invoice_discovery import DiscoveryScanner,InvoicePage
class EmptyFinalPage:
 configured=supports_sandbox=True
 def page(self,app,day,page,size,**kwargs):
  assert page==1
  return InvoicePage(1,2,2,())
app=create_app(Path(sys.argv[1]),Path(sys.argv[2]),lambda:int(sys.argv[4]),commerce_config_path=Path(sys.argv[3]),notifications_enabled=False,identity_enabled=False)
scanner=DiscoveryScanner(app.state.authority,app.state.commerce,EmptyFinalPage(),enabled=True)
result=scanner.scan_once(123,'2026-10-25',True,'new-process')
print(json.dumps({'state':result['state'],'pages':result['pages']}))
'''
        process = subprocess.run([sys.executable, '-c', script, str(self.path), str(CONFIG), str(self.config), str(self.now)],
                                 cwd=CONFIG.parent, capture_output=True, text=True, timeout=20, check=True)
        self.assertEqual(json.loads(process.stdout), {'state': 'Complete', 'pages': 1})
        self.assertEqual(self.counts()[2], 1)
        self.assertEqual(self.worker.run_once('fixture')['orderState'], 'Confirmed')

    def test_post_commit_lost_response_leaves_queued_work_and_completed_cursor(self):
        scanner = self.scanner()
        commit = scanner._commit
        def lost_reply(*args):
            commit(*args)
            raise OSError('synthetic post-commit lost reply')
        with patch.object(scanner, '_commit', side_effect=lost_reply), self.assertRaises(ServiceError):
            self.scan(scanner)
        self.assertEqual((self.cursor()['state'], self.cursor()['next_page'], self.counts()[2]), ('Complete', 1, 1))
        self.assertEqual(self.scan(self.scanner())['pages'], 0)
        self.assertEqual(self.worker.run_once('fixture')['orderState'], 'Confirmed')
        self.assertEqual(self.counts()[4], 1)

    def test_duplicate_on_multiple_pages_enqueues_only_once_per_revision(self):
        pages = [self.page([self.hint], pages=2, total=2), self.page([self.hint], number=1, pages=2, total=2)]
        result = self.scan(self.scanner(pages))
        self.assertEqual((result['queued'], result['duplicates']), (1, 1))
        with self.database.connect() as db:
            self.assertEqual(db.execute('SELECT requested_revision FROM commerce_reconcile_jobs').fetchone()[0], 1)

    def test_lease_busy_then_expiry_restart_and_stale_completion_cas(self):
        scanner = self.scanner()
        key = (123, 1, self.day, 'CONFIRMED')
        old, _ = scanner._claim(key, self.now, 100, False)
        self.assertEqual(self.scan(scanner)['state'], 'Busy')
        self.now += 61
        replacement, _ = scanner._claim(key, self.now, 100, False)
        self.assertIsNone(scanner._commit(old, self.page([self.hint]), self.now))
        self.assertEqual(self.counts()[2], 0)
        self.assertEqual(scanner._commit(replacement, self.page([self.hint]), self.now)['queued'], 1)

    def test_crash_before_checkpoint_and_failed_queue_commit_do_not_advance_cursor(self):
        scanner = self.scanner()
        with self.database.transaction() as db:
            db.execute("CREATE TRIGGER fail_discovery BEFORE INSERT ON commerce_reconcile_jobs BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
        with self.assertRaises(ServiceError) as error:
            self.scan(scanner)
        self.assertEqual(error.exception.code, 'invoice_discovery_storage_unavailable')
        self.assertEqual((self.cursor()['next_page'], self.cursor()['state'], self.counts()[1:3]), (0, 'Pending', (0, 0)))
        with self.database.transaction() as db:
            db.execute('DROP TRIGGER fail_discovery')
        self.assertEqual(self.scan(scanner)['queued'], 1)

    def test_overlap_and_rescan_find_late_additions_without_duplicate_credit(self):
        empty = self.scanner([self.page([], pages=0)])
        self.assertEqual(len(empty.scan_overlap(123, self.day, True, 'fixture', days=3)), 3)
        self.assertEqual(self.counts()[0], 3)
        late = self.scanner()
        self.assertEqual(self.scan(late)['pages'], 0)
        self.assertEqual(self.scan(late, rescan=True)['queued'], 1)
        self.worker.run_once('fixture')
        self.assertEqual(self.counts()[4], 1)

    def test_disabled_missing_provider_and_unsupported_sandbox_do_not_create_cursor(self):
        with self.assertRaises(ServiceError):
            self.scan(self.scanner(enabled=False))
        used = []
        actual = DiscoveryScanner(self.authority, self.commerce, RuStoreInvoiceLister(lambda: used.append(True)), enabled=True)
        with self.assertRaises(ServiceError) as error:
            self.scan(actual)
        self.assertEqual(error.exception.code, 'invoice_listing_sandbox_unavailable')
        self.assertEqual((used, self.counts()[0]), ([], 0))

    def test_strict_scope_and_all_limits_are_validated_before_cursor_write(self):
        for changes in ({'app_id': 124}, {'sandbox': False}, {'day': '2026-02-30'}, {'worker_id': 'bad\n'},
                        {'max_pages': True}, {'max_pages': 21}, {'page_size': 501}, {'status': 'REFUNDING'}, {'rescan': 1}):
            args = dict(app_id=123, day=self.day, sandbox=True, worker_id='fixture')
            args.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.scanner().scan_once(**args)
        self.assertEqual(self.counts()[0], 0)

    def test_mid_scan_page_size_change_requires_deliberate_rescan(self):
        scanner = self.scanner([self.page([], pages=2, total=2), self.page([], number=1, pages=2, total=2)])
        self.scan(scanner, max_pages=1, page_size=20)
        with self.assertRaises(ServiceError) as error:
            self.scan(scanner, page_size=50)
        self.assertEqual(error.exception.code, 'discovery_page_size_changed')
        self.assertEqual(self.scan(scanner, page_size=50, rescan=True)['state'], 'Complete')

    def test_invalid_provider_page_and_transport_failure_preserve_restart_position(self):
        for page in (InvoicePage(1, 1, 1, (self.hint,)), InvoicePage(0, 0, 1, (self.hint,)),
                     InvoicePage(0, 1, -1, ()), ProviderUnavailable()):
            with self.subTest(page_type=type(page).__name__), self.assertRaises(ServiceError):
                self.scan(self.scanner([page]))
            self.assertEqual((self.cursor()['next_page'], self.counts()[1:3]), (0, (0, 0)))

    def test_listing_http_parser_is_strict_and_source_is_fixed(self):
        entry = self.entry(self.hint)
        valid = self.list_response([entry])
        for response in (httpx.Response(302, headers={'location': 'https://untrusted.example'}),
            httpx.Response(200, text='{"code":"OK","code":"OK"}', headers={'content-type': 'application/json'}),
            httpx.Response(200, content=b' ' * (MAX_RESPONSE + 1), headers={'content-type': 'application/json'}),
            httpx.Response(200, json=self.list_response([entry], pageNumber=1)),
            httpx.Response(200, json=self.list_response([dict(entry, appId=124)])),
            httpx.Response(200, json=self.list_response([dict(entry, invoiceId=True)])),
            httpx.Response(200, json=self.list_response([dict(entry, order=dict(entry['order'], amountCurrent=0.5))])),
            httpx.Response(200, text='not json', headers={'content-type': 'text/plain'})):
            requested = []
            def respond(request):
                requested.append(request)
                return response
            with self.subTest(status=response.status_code), self.assertRaises((ProviderUnavailable, InvalidProviderResponse)):
                RuStoreInvoiceLister(lambda: 'synthetic', httpx.MockTransport(respond)).page(123, self.day, 0, 20)
            self.assertEqual(len(requested), 1)
            self.assertEqual(requested[0].url.host, 'public-api-m.rustore.ru')
        parsed = RuStoreInvoiceLister(lambda: 'synthetic', httpx.MockTransport(lambda request: httpx.Response(200, json=valid))).page(123, self.day, 0, 20)
        self.assertEqual(parsed.hints, (self.hint,))

    def test_auth_rejection_invalidates_only_ephemeral_token_and_retains_no_body(self):
        class Tokens:
            def __init__(self): self.invalidated = 0
            def __call__(self): return 'synthetic'
            def invalidate(self): self.invalidated += 1
        token = Tokens()
        with self.assertRaises(ProviderUnavailable):
            RuStoreInvoiceLister(token, httpx.MockTransport(lambda request: httpx.Response(401, text='secret-provider-body'))).page(123, self.day, 0, 20)
        self.assertEqual(token.invalidated, 1)

    def test_no_sensitive_listing_or_payment_data_is_persisted(self):
        requested = []
        def response(request):
            requested.append(request)
            return httpx.Response(200, json=self.list_response([self.entry(self.hint)]))
        # Explicit synthetic sandbox seam delegates only the production parser;
        # it does not claim or invent an official sandbox URL.
        parsed = RuStoreInvoiceLister(lambda: 'ephemeral-test-JWE', httpx.MockTransport(response)).page(123, self.day, 0, 100)
        self.scan(self.scanner([parsed]))
        with self.database.connect() as db:
            stored = '\n'.join(db.iterdump())
        for value in ('sensitive-fixture-must-not-persist', 'sensitive-purchase-token-must-not-persist',
                      'ephemeral-test-JWE', 'paymentInfo', 'purchase_token', json.dumps(self.entry(self.hint))):
            self.assertNotIn(value, stored)

    def test_cli_is_explicit_bounded_redacted_and_restores_mode(self):
        # Real listing parser with mocked HTTP, existing live fixture and closed worker gate.
        config = json.loads(self.config.read_text()); config['sandbox'] = False
        self.config.write_text(json.dumps(config))
        with self.database.transaction() as db:
            db.execute('UPDATE commerce_orders SET sandbox=0')
        self.provider.transport = httpx.MockTransport(lambda request: httpx.Response(200, json=self.list_response([self.entry(self.hint)])))
        self.open()
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch('hotr_backend.__main__.create_app', return_value=self.app), contextlib.redirect_stdout(output):
            main(['discover-invoices', '--mode', 'staging', '--environment', 'production', '--app-id', '123',
                  '--date', self.day, '--days', '1', '--max-pages', '1'])
            self.assertNotIn('HOTR_BACKEND_MODE', os.environ)
        result = json.loads(output.getvalue())
        self.assertEqual((result['dates'][0]['queued'], result['productionEnabled']), (1, False))
        for secret in ('ephemeral-test-JWE', self.order['orderId'], self.actor.player, self.hint.developer_payload):
            self.assertNotIn(secret, output.getvalue())
        with patch.dict(os.environ, {'HOTR_BACKEND_MODE': 'production'}, clear=True), self.assertRaises(SystemExit):
            main(['discover-invoices', '--mode', 'staging', '--environment', 'production', '--app-id', '123', '--date', self.day])


if __name__ == '__main__':
    unittest.main()
