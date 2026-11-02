"""Owned production discovery with real SQLite and scripted official HTTP adapters."""
import contextlib
from dataclasses import replace
import io
import json
import threading
import unittest
from unittest.mock import patch
import uuid

import httpx

from hotr_backend import production_discovery122 as discovery
from hotr_backend import production_ops122 as operations, production_runtime122 as runtime
from hotr_backend.commerce_schemas import CreateCommerceOrder
from hotr_backend.invoice_discovery import InvoiceHint
from hotr_backend.rustore_provider import RuStoreInvoiceProvider
from hotr_backend.service import Actor
from tests.production_fixture122 import ProductionFixture122


class ProductionDiscovery122Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProductionFixture122()
        self.addCleanup(self.fixture.close)
        self.day, self.calls = '2026-10-30', []
        self.page_hints, self.lookup_entries = {}, {}
        self.provider = RuStoreInvoiceProvider(lambda: 'explicit-scripted-discovery-JWE',
                                               httpx.MockTransport(self.http))
        self.fixture.provider = self.provider
        with self.fixture.context() as app:
            self.identity, self.headers = self.fixture.provision(app)
            actor = Actor(self.identity['playerId'], self.fixture.now)
            self.order = app.state.commerce.create(actor,
                CreateCommerceOrder(commandId=uuid.uuid4().hex, productId='wellkeeper'))
        self.path = runtime.owned_database(self.fixture.manifest)
        self.hint = InvoiceHint('1001', str(uuid.uuid4()), 123, self.order['orderId'],
            self.order['sdk']['productId'], self.identity['playerId'], self.order['sdk']['developerPayload'],
            9900, 'RUB', 'CONFIRMED')
        self.page_hints[(self.day, 0)] = [self.hint]
        self.total_pages = 1
        self.lookup_entries['1001'] = self.entry(self.hint)

    @staticmethod
    def entry(hint):
        return {'invoiceId': int(hint.invoice_id), 'purchaseId': hint.purchase_id, 'appId': hint.app_id,
                'appUserId': hint.app_user_id, 'developerPayload': hint.developer_payload,
                'invoiceStatus': hint.status, 'acknowledgementState': 'PENDING',
                'order': {'orderId': hint.order_id, 'itemCode': hint.product_id,
                          'amountCurrent': hint.amount_minor, 'currency': hint.currency},
                'paymentInfo': {'cardToken': 'explicit-sensitive-listing-data-not-for-storage'},
                'purchase_token': 'explicit-sensitive-purchase-data-not-for-storage'}

    def http(self, request):
        self.assertEqual(request.url.host, RuStoreInvoiceProvider.origin.split('://', 1)[1])
        self.assertEqual(request.headers['Public-Token'], 'explicit-scripted-discovery-JWE')
        self.assertEqual(request.headers['Accept-Encoding'], 'identity')
        self.calls.append((request.url.path, dict(request.url.params)))
        if request.url.path == '/public/applications/123/invoices':
            day, number = request.url.params['invoiceDate'], int(request.url.params['pageNumber'])
            hints = self.page_hints.get((day, number), [])
            return httpx.Response(200, json={'code': 'OK', 'body': {
                'pageNumber': number, 'pageSize': len(hints), 'totalPages': self.total_pages,
                'totalElements': max(len(hints), self.total_pages),
                'content': [self.entry(hint) for hint in hints]}})
        self.assertTrue(request.url.path.startswith('/public/v2/invoices/'))
        return httpx.Response(200, json={'code': 'OK', 'body':
            self.lookup_entries[request.url.path.rsplit('/', 1)[1]]})

    def scalar(self, sql, args=()):
        import sqlite3
        with contextlib.closing(sqlite3.connect(self.path)) as db:
            return db.execute(sql, args).fetchone()[0]

    def counts(self):
        return tuple(self.scalar('SELECT COUNT(*) FROM ' + table) for table in (
            'commerce_discovery_cursors', 'commerce_discovery_seen', 'commerce_reconcile_jobs',
            'commerce_invoice_requests', 'commerce_notification_inbox', 'commerce_credits'))

    def scan(self, app, **changes):
        scope = dict(date=self.day, days=1, page_size=20)
        scope.update(changes)
        return discovery.discover_bounded(app, self.fixture.manifest, **scope)

    def test_dual_loss_discovery_queues_then_independent_fresh_lookup_credits_full_grant_once(self):
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0, 0))
        with self.fixture.context(purpose='operations') as app:
            self.assertEqual(app.state.reconciliation_worker.seed_due(), 0)
            found = self.scan(app)
            self.assertEqual((found['pages'], found['queued'], found['grantsFromListing']), (1, 1, False))
            self.assertFalse(found['reconciliationPerformed'])
            self.assertEqual(self.counts(), (1, 1, 1, 0, 0, 0))
            self.assertEqual([path for path, _ in self.calls], ['/public/applications/123/invoices'])
            result = operations.reconcile_bounded(app, self.fixture.manifest, max_jobs=1)
            self.assertEqual(result['states'], {'Done': 1})
            self.assertEqual(self.counts()[5], 1)
            actor = Actor(self.identity['playerId'], self.fixture.now)
            wallet = app.state.wallet.view(actor)
            self.assertEqual(wallet['coins'], 3250)
            self.assertEqual(wallet['starting'], [6, 6, 4, 3])
            self.assertEqual(wallet['tools'], [4, 4, 4, 4])
            self.scan(app, rescan=True)
            operations.reconcile_bounded(app, self.fixture.manifest, max_jobs=1)
            self.assertEqual(app.state.wallet.view(actor)['coins'], 3250)
            self.assertEqual(self.counts()[5], 1)
        self.assertEqual([p for p, _ in self.calls].count('/public/v2/invoices/1001'), 2)

    def test_optional_listing_identity_never_authorizes_mismatched_fresh_lookup(self):
        self.page_hints[(self.day, 0)] = [replace(self.hint, app_user_id=None, developer_payload=None)]
        self.lookup_entries['1001']['appUserId'] = uuid.uuid4().hex
        with self.fixture.context(purpose='operations') as app:
            self.assertEqual(self.scan(app)['queued'], 1)
            outcome = operations.reconcile_bounded(app, self.fixture.manifest, max_jobs=1)
            self.assertEqual(outcome['queue']['states']['Dead'], 1)
            self.assertEqual(self.counts()[5], 0)

    def test_conflicting_and_unowned_listing_hints_do_not_queue(self):
        invalid = [replace(self.hint, order_id=uuid.uuid4().hex),
                   replace(self.hint, product_id='different-product'),
                   replace(self.hint, amount_minor=1),
                   replace(self.hint, app_user_id=uuid.uuid4().hex)]
        self.page_hints[(self.day, 0)] = invalid
        with self.fixture.context(purpose='operations') as app:
            found = self.scan(app)
            self.assertEqual((found['ignored'], found['queued']), (4, 0))
            self.assertEqual(self.counts()[2:], (0, 0, 0, 0))

    def test_cursor_pagination_resumes_after_operations_restart_without_rescan(self):
        self.total_pages = 2
        self.page_hints[(self.day, 1)] = []
        with self.fixture.context(purpose='operations') as app:
            first = self.scan(app, max_pages=1)
            self.assertEqual(first['status'], 'more_work_pending')
            self.assertTrue(first['resumeRequired'])
        with self.fixture.context(purpose='operations') as app:
            second = self.scan(app, max_pages=1)
            self.assertEqual(second['status'], 'completed')
            self.assertFalse(second['resumeRequired'])
        pages = [query['pageNumber'] for path, query in self.calls if path.endswith('/invoices')]
        self.assertEqual(pages, ['0', '1'])
        self.assertEqual(self.counts()[2], 1)

    def test_explicit_overlap_and_status_reach_only_the_fixed_production_listing(self):
        with self.fixture.context(purpose='operations') as app:
            found = self.scan(app, days=3, status='PAID')
            self.assertEqual(found['datesRequested'], 3)
        self.assertEqual([q['invoiceDate'] for _, q in self.calls], ['2026-10-30', '2026-10-29', '2026-10-28'])
        self.assertTrue(all(path == '/public/applications/123/invoices' for path, _ in self.calls))
        self.assertTrue(all(q['invoiceStatuses'] == 'paid' for _, q in self.calls))
        self.assertEqual(self.counts()[5], 0)

    def test_listing_cannot_override_held_or_cancelled_fresh_invoice(self):
        self.lookup_entries['1001']['invoiceStatus'] = 'PAID'
        with self.fixture.context(purpose='operations') as app:
            self.scan(app)
            operations.reconcile_bounded(app, self.fixture.manifest, max_jobs=1)
            self.assertEqual(self.scalar('SELECT state FROM commerce_orders'), 'Held')
            self.assertEqual(self.counts()[5], 0)
            self.lookup_entries['1001']['invoiceStatus'] = 'CANCELLED'
            self.scan(app, rescan=True)
            operations.reconcile_bounded(app, self.fixture.manifest, max_jobs=1)
            self.assertEqual(self.scalar('SELECT state FROM commerce_orders'), 'Cancelled')
            self.assertEqual(self.counts()[5], 0)

    def test_bad_date_scope_and_underflow_fail_before_clock_cursor_or_network_mutation(self):
        changes = [{'date': '2026-02-30'}, {'date': '2026-1-1'}, {'date': '0001-01-01', 'days': 2},
                   {'days': True}, {'days': 0}, {'days': 8}, {'max_pages': 0}, {'max_pages': 21},
                   {'page_size': 0}, {'page_size': 501}, {'status': 'REFUNDING'}, {'rescan': 1},
                   {'worker_id': '../other'}]
        with self.fixture.context(purpose='operations') as app:
            clock = self.scalar('SELECT high_water FROM clock_state')
            for change in changes:
                with self.subTest(field=next(iter(change))), self.assertRaises(discovery.ProductionDiscoveryError):
                    self.scan(app, **change)
            self.assertEqual(self.scalar('SELECT high_water FROM clock_state'), clock)
            self.assertEqual(self.counts(), (0, 0, 0, 0, 0, 0))
            self.assertEqual(self.calls, [])

    def test_api_purpose_or_foreign_manifest_cannot_operate_discovery(self):
        with self.fixture.context() as app:
            with self.assertRaises(runtime.ProductionError):
                self.scan(app)
        with ProductionFixture122() as other:
            with self.fixture.context(purpose='operations') as app:
                with self.assertRaises(runtime.ProductionError):
                    discovery.discover_bounded(app, other.manifest, date=self.day)
        self.assertEqual(self.calls, [])

    def test_real_operations_lease_rejects_concurrent_cli_ownership(self):
        with self.fixture.context(purpose='operations'):
            with self.assertRaises(runtime.ProductionError):
                with self.fixture.context(purpose='operations'):
                    self.fail('concurrent operations lease admitted')
        self.assertEqual(self.calls, [])

    def test_provider_failure_retains_page_zero_and_releases_durable_cursor_lease(self):
        with self.fixture.context(purpose='operations') as app:
            self.provider.transport = httpx.MockTransport(lambda _: httpx.Response(503))
            with self.assertRaises(discovery.ProductionDiscoveryError):
                self.scan(app)
            self.assertEqual(self.scalar('SELECT next_page FROM commerce_discovery_cursors'), 0)
            self.assertEqual(self.scalar('SELECT state FROM commerce_discovery_cursors'), 'Pending')
            self.assertIsNone(self.scalar('SELECT lease_token FROM commerce_discovery_cursors'))
            self.provider.transport = httpx.MockTransport(self.http)
            self.assertEqual(self.scan(app)['queued'], 1)
            self.assertEqual(self.counts()[5], 0)

    def test_sensitive_listing_fields_and_identifiers_never_enter_summary_or_database(self):
        with self.fixture.context(purpose='operations') as app:
            report = self.scan(app)
            raw = json.dumps(report)
            for value in (self.hint.invoice_id, self.hint.purchase_id, self.hint.order_id,
                          self.hint.app_user_id, self.hint.developer_payload,
                          'explicit-scripted-discovery-JWE', 'explicit-sensitive-listing-data-not-for-storage'):
                self.assertNotIn(value, raw)
            with app.state.authority.database.connect() as db:
                dump = '\n'.join(db.iterdump())
                self.assertNotIn('explicit-sensitive-listing-data-not-for-storage', dump)
                self.assertNotIn('explicit-sensitive-purchase-data-not-for-storage', dump)

    def test_closed_operations_application_cannot_resume_discovery(self):
        with self.fixture.context(purpose='operations') as app:
            pass
        with self.assertRaises(runtime.ProductionError):
            self.scan(app)
        self.assertEqual(self.calls, [])

    def test_cli_does_not_echo_bad_arguments_private_paths_or_provider_errors(self):
        marker = 'explicit-sensitive-argument-must-not-be-printed'
        for args in (['--unknown', marker], ['--manifest', marker, '--date', 'bad-date'],
                     ['--manifest', marker, '--date', self.day, '--status', marker]):
            output, error = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                self.assertEqual(discovery.main(args), 1)
            self.assertNotIn(marker, output.getvalue() + error.getvalue())
            self.assertFalse(json.loads(output.getvalue())['grantsFromListing'])


if __name__ == '__main__':
    unittest.main()
