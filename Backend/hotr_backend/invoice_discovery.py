"""Explicit bounded invoice listing discovery, never listing-authorized credit.

Official production-only listing contract reviewed2026-10-25:
https://www.rustore.ru/help/work-with-rustore-api/api-subscription-payment/applications-appid-invoices
No sandbox listing URL or provider date/timezone boundary is documented here.
Use explicit ISO dates with overlap/rescan; real Console acceptance remains open.
"""
import datetime as dt
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import httpx

from .guards import require_active_player
from .notifications import enqueue
from .rustore_provider import InvalidProviderResponse, ProviderUnavailable, _invalid_constant, _unique_object
from .service import ServiceError

STATUSES = ('CREATED', 'EXECUTED', 'CONFIRMED', 'CANCELLED', 'REJECTED', 'EXPIRED', 'PAID', 'REVERSED', 'REFUNDED')
MAX_RESPONSE = 1_048_576


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError('Explicit ISO invoice date required')
    return dt.date.fromisoformat(value).isoformat()


def _text(value, maximum=512):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or any(ord(c) < 32 for c in value):
        raise InvalidProviderResponse()
    return value


@dataclass(frozen=True)
class InvoiceHint:
    invoice_id: str
    purchase_id: str
    app_id: int
    order_id: str
    product_id: str
    app_user_id: str | None
    developer_payload: str | None
    amount_minor: int
    currency: str
    status: str

    def __post_init__(self):
        if (not isinstance(self.invoice_id, str) or not re.fullmatch(r'[1-9][0-9]{0,29}', self.invoice_id)
                or type(self.app_id) is not int or not 0 < self.app_id <= 9_223_372_036_854_775_807
                or type(self.amount_minor) is not int or not 0 <= self.amount_minor <= 2_147_483_647
                or self.status not in STATUSES or not isinstance(self.currency, str)
                or not re.fullmatch(r'[A-Z]{3}', self.currency)):
            raise InvalidProviderResponse()
        try:
            if str(uuid.UUID(self.purchase_id)) != self.purchase_id:
                raise ValueError()
        except (TypeError, ValueError, AttributeError):
            raise InvalidProviderResponse() from None
        _text(self.order_id, 150)
        _text(self.product_id)
        if self.app_user_id is not None:
            _text(self.app_user_id)
        if self.developer_payload is not None:
            _text(self.developer_payload)


@dataclass(frozen=True)
class InvoicePage:
    page_number: int
    total_pages: int
    total_elements: int
    hints: tuple[InvoiceHint, ...]


class RuStoreInvoiceLister:
    configured = True
    supports_sandbox = False
    origin = 'https://public-api-m.rustore.ru'

    def __init__(self, token_supplier, transport=None):
        if not callable(token_supplier):
            raise ValueError('Explicit server-only JWE supplier required')
        self.token_supplier, self.transport = token_supplier, transport

    def page(self, app_id, day, page_number, page_size, *, sandbox=False, status='CONFIRMED'):
        if type(sandbox) is not bool or sandbox:
            raise ServiceError(503, 'invoice_listing_sandbox_unavailable')
        day = _day(day)
        if (type(app_id) is not int or not 0 < app_id <= 9_223_372_036_854_775_807
                or type(page_number) is not int or not 0 <= page_number < 100_000
                or type(page_size) is not int or not 1 <= page_size <= 500 or status not in STATUSES):
            raise ValueError('Invalid bounded invoice listing request')
        try:
            token = self.token_supplier()
            if not isinstance(token, str) or not token or len(token) > 16_384 or any(c.isspace() for c in token):
                raise ProviderUnavailable()
            # One explicit array member avoids assuming undocumented comma vs
            # repeated-parameter serialization. Separate statuses have cursors.
            parameters = {'invoiceStatuses': status.lower(), 'invoiceDate': day,
                          'pageNumber': page_number, 'pageSize': page_size}
            with httpx.Client(transport=self.transport, timeout=10, follow_redirects=False, trust_env=False) as client:
                with client.stream('GET', self.origin + f'/public/applications/{app_id}/invoices', params=parameters,
                        headers={'Public-Token': token, 'Accept': 'application/json', 'Accept-Encoding': 'identity'}) as response:
                    if response.status_code != 200:
                        if response.status_code in (401, 403):
                            invalidate = getattr(self.token_supplier, 'invalidate', None)
                            if callable(invalidate):
                                invalidate()
                        raise ProviderUnavailable()
                    if (response.headers.get('content-encoding', '').lower() not in ('', 'identity')
                            or response.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json'):
                        raise InvalidProviderResponse()
                    chunks = bytearray()
                    for chunk in response.iter_bytes(chunk_size=16_384):
                        chunks.extend(chunk)
                        if len(chunks) > MAX_RESPONSE:
                            raise InvalidProviderResponse()
            value = json.loads(chunks, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
            if not isinstance(value, dict) or value.get('code') != 'OK' or not isinstance(value.get('body'), dict):
                raise InvalidProviderResponse()
            body = value['body']
            number, size, pages, total, content = (body[name] for name in ('pageNumber', 'pageSize', 'totalPages', 'totalElements', 'content'))
            if (any(type(item) is not int for item in (number, size, pages, total)) or number != page_number
                    or not 0 <= size <= page_size or not 0 <= pages <= 100_000 or not 0 <= total <= 9_223_372_036_854_775_807
                    or not isinstance(content, list) or len(content) > page_size or total < len(content)
                    or content and (pages == 0 or size < len(content))):
                raise InvalidProviderResponse()
            hints = []
            for entry in content:
                if not isinstance(entry, dict) or not isinstance(entry.get('order'), dict):
                    raise InvalidProviderResponse()
                order = entry['order']
                amount = Decimal(str(order['amountCurrent']))
                if type(order['amountCurrent']) not in (int, float) or not amount.is_finite() or amount != amount.to_integral_value():
                    raise InvalidProviderResponse()
                if type(entry['invoiceId']) is not int or type(entry['appId']) is not int or entry['appId'] != app_id:
                    raise InvalidProviderResponse()
                if _text(entry['acknowledgementState']).upper() not in ('PENDING', 'ACKNOWLEDGED', 'UNKNOWN'):
                    raise InvalidProviderResponse()
                hints.append(InvoiceHint(str(entry['invoiceId']), str(uuid.UUID(_text(entry['purchaseId']))),
                    entry['appId'], _text(order['orderId'], 150), _text(order['itemCode']), entry.get('appUserId'),
                    entry.get('developerPayload'), int(amount), _text(order['currency'], 3), _text(entry['invoiceStatus']).upper()))
            return InvoicePage(number, pages, total, tuple(hints))
        except (ServiceError, ProviderUnavailable, InvalidProviderResponse):
            raise
        except httpx.HTTPError:
            raise ProviderUnavailable() from None
        except (ValueError, TypeError, KeyError, UnicodeError, InvalidOperation, OverflowError, RecursionError):
            raise InvalidProviderResponse() from None


class DiscoveryScanner:
    def __init__(self, authority, commerce, lister, *, enabled=False, lease_seconds=60):
        if type(enabled) is not bool or type(lease_seconds) is not int or not 15 <= lease_seconds <= 600:
            raise ValueError('Explicit bounded discovery activation required')
        self.authority, self.commerce, self.database = authority, commerce, authority.database
        self.lister, self.enabled, self.lease_seconds = lister, enabled, lease_seconds

    def _claim(self, key, now, page_size, rescan):
        with self.database.transaction() as db:
            db.execute('''INSERT OR IGNORE INTO commerce_discovery_cursors
                (app_id,sandbox,invoice_date,status_filter,scan_revision,page_size,state,created_at,updated_at)
                VALUES(?,?,?,?,1,?,'Pending',?,?)''', (*key, page_size, now, now))
            row = db.execute('SELECT * FROM commerce_discovery_cursors WHERE app_id=? AND sandbox=? AND invoice_date=? AND status_filter=?', key).fetchone()
            if row['state'] == 'Running' and row['lease_until'] > now:
                return None, 'Busy'
            if rescan:
                db.execute('''UPDATE commerce_discovery_cursors SET scan_revision=scan_revision+1,next_page=0,
                    page_size=?,total_pages=NULL,state='Pending',lease_token=NULL,lease_until=0,last_error='',updated_at=?
                    WHERE app_id=? AND sandbox=? AND invoice_date=? AND status_filter=?''', (page_size, now, *key))
            elif row['state'] == 'Complete':
                return None, 'Complete'
            elif row['page_size'] != page_size:
                raise ServiceError(409, 'discovery_page_size_changed')
            token = uuid.uuid4().hex
            db.execute('''UPDATE commerce_discovery_cursors SET state='Running',lease_token=?,lease_until=?,updated_at=?
                WHERE app_id=? AND sandbox=? AND invoice_date=? AND status_filter=?''', (token, now + self.lease_seconds, now, *key))
            return dict(db.execute('SELECT * FROM commerce_discovery_cursors WHERE app_id=? AND sandbox=? AND invoice_date=? AND status_filter=?', key).fetchone()), 'Running'

    @staticmethod
    def _key(claim):
        return tuple(claim[field] for field in ('app_id', 'sandbox', 'invoice_date', 'status_filter'))

    def _release(self, claim, code):
        try:
            with self.database.transaction() as db:
                db.execute('''UPDATE commerce_discovery_cursors SET state='Pending',lease_token=NULL,lease_until=0,last_error=?
                    WHERE app_id=? AND sandbox=? AND invoice_date=? AND status_filter=? AND lease_token=?''',
                           (code, *self._key(claim), claim['lease_token']))
        except sqlite3.Error:
            pass  # Original lease expires; no cursor advancement was acknowledged.

    def _commit(self, claim, page, now):
        if (not isinstance(page, InvoicePage) or not isinstance(page.hints, tuple)
                or type(page.page_number) is not int or page.page_number != claim['next_page']
                or type(page.total_pages) is not int or not 0 <= page.total_pages <= 100_000
                or type(page.total_elements) is not int or not len(page.hints) <= page.total_elements <= 9_223_372_036_854_775_807
                or len(page.hints) > claim['page_size'] or page.hints and page.total_pages <= page.page_number
                or any(not isinstance(hint, InvoiceHint) or hint.app_id != claim['app_id'] for hint in page.hints)):
            raise InvalidProviderResponse()
        queued = ignored = duplicates = 0
        key = self._key(claim)
        with self.database.transaction() as db:
            current = db.execute('SELECT * FROM commerce_discovery_cursors WHERE app_id=? AND sandbox=? AND invoice_date=? AND status_filter=?', key).fetchone()
            if (not current or current['state'] != 'Running' or current['lease_token'] != claim['lease_token']
                    or current['scan_revision'] != claim['scan_revision'] or current['next_page'] != claim['next_page']):
                return None
            for hint in page.hints:
                row = db.execute('SELECT * FROM commerce_orders WHERE id=?', (hint.order_id,)).fetchone()
                if (not row or row['app_id'] != hint.app_id or bool(row['sandbox']) != bool(claim['sandbox'])
                        or row['store_product'] != hint.product_id or row['amount_minor'] != hint.amount_minor or row['currency'] != hint.currency
                        or hint.app_user_id is not None and row['player_id'] != hint.app_user_id
                        or hint.developer_payload is not None and row['binding'] != hint.developer_payload
                        or row['invoice_id'] is not None and row['invoice_id'] != hint.invoice_id
                        or row['purchase_id'] is not None and row['purchase_id'] != hint.purchase_id):
                    ignored += 1
                    continue
                try:
                    require_active_player(db, row['player_id'])
                except ServiceError:
                    ignored += 1
                    continue
                inserted = db.execute('''INSERT OR IGNORE INTO commerce_discovery_seen
                    (app_id,sandbox,invoice_date,status_filter,scan_revision,invoice_id,order_id,created_at)
                    VALUES(?,?,?,?,?,?,?,?)''', (*key, claim['scan_revision'], hint.invoice_id, row['id'], now)).rowcount
                if inserted:
                    enqueue(db, row, hint.invoice_id, now)
                    queued += 1
                else:
                    duplicates += 1
            complete = page.total_pages == 0 or page.page_number + 1 >= page.total_pages
            state = 'Complete' if complete else 'Pending'
            db.execute('''UPDATE commerce_discovery_cursors SET next_page=?,total_pages=?,state=?,lease_token=NULL,
                lease_until=0,last_error='',updated_at=? WHERE app_id=? AND sandbox=? AND invoice_date=? AND status_filter=?''',
                       (page.page_number + 1, page.total_pages, state, now, *key))
            return {'state': state, 'queued': queued, 'ignored': ignored, 'duplicates': duplicates}

    def scan_once(self, app_id, day, sandbox, worker_id, *, max_pages=5, page_size=100, status='CONFIRMED', rescan=False):
        day = _day(day)
        if (type(app_id) is not int or app_id != self.commerce.config.appId or type(sandbox) is not bool
                or sandbox != self.commerce.config.sandbox or not isinstance(worker_id, str)
                or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', worker_id) or type(max_pages) is not int or not 1 <= max_pages <= 20
                or type(page_size) is not int or not 1 <= page_size <= 500 or status not in STATUSES or type(rescan) is not bool):
            raise ValueError('Invalid explicit discovery scope')
        if not self.enabled or not getattr(self.lister, 'configured', False) or not self.commerce.config.enabled:
            raise ServiceError(503, 'invoice_discovery_not_configured')
        if sandbox and not getattr(self.lister, 'supports_sandbox', False):
            raise ServiceError(503, 'invoice_listing_sandbox_unavailable')
        result = {'state': 'Pending', 'pages': 0, 'queued': 0, 'ignored': 0, 'duplicates': 0,
                  'sandbox': sandbox, 'productionEnabled': False, 'grantsFromListing': False}
        key = (app_id, int(sandbox), day, status)
        for index in range(max_pages):
            claim, state = self._claim(key, self.authority._now(), page_size, rescan and index == 0)
            if claim is None:
                result['state'] = state
                break
            try:
                page = self.lister.page(app_id, day, claim['next_page'], page_size, sandbox=sandbox, status=status)
                committed = self._commit(claim, page, self.authority._now())
            except ProviderUnavailable:
                self._release(claim, 'listing_unavailable')
                raise ServiceError(503, 'invoice_listing_unavailable') from None
            except InvalidProviderResponse:
                self._release(claim, 'listing_invalid_response')
                raise ServiceError(503, 'invoice_listing_invalid_response') from None
            except sqlite3.Error:
                self._release(claim, 'listing_storage_unavailable')
                raise ServiceError(503, 'invoice_discovery_storage_unavailable') from None
            except ServiceError:
                self._release(claim, 'listing_unavailable')
                raise
            except Exception:
                self._release(claim, 'listing_unavailable')
                raise ServiceError(503, 'invoice_listing_unavailable') from None
            if committed is None:
                result['state'] = 'StaleLease'
                break
            result['pages'] += 1
            for field in ('queued', 'ignored', 'duplicates'):
                result[field] += committed[field]
            result['state'] = committed['state']
            if result['state'] == 'Complete':
                break
        return result

    def scan_overlap(self, app_id, day, sandbox, worker_id, *, days=3, **kwargs):
        if type(days) is not int or not 1 <= days <= 7:
            raise ValueError('Bounded overlap of 1-7 explicit dates required')
        anchor = dt.date.fromisoformat(_day(day))
        return [self.scan_once(app_id, (anchor - dt.timedelta(days=offset)).isoformat(), sandbox, worker_id, **kwargs)
                for offset in range(days)]
