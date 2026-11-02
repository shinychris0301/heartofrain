"""Authenticated RuStore payment hints, never callback-authorized currency.

Official wire contract (reviewed2026-10-25): Base64(IV12 || ciphertext || tag16),
AES256/GCM/NoPadding; Base64 Console key, no associated data in the official Java
example. Outer notification id/timestamp are NOT authenticated by this format.
https://www.rustore.ru/help/developers/monetization/payment-callback/server-set-up
https://www.rustore.ru/help/developers/monetization/payment-callback/notification
Only normalized identifiers/digests survive. Purchase tokens, plaintext payloads,
ciphertext bodies, decryption keys and outer id/timestamp are never persisted.
"""
import base64
import binascii
import datetime as dt
import hashlib
import ipaddress
import json
import re
import uuid
from pathlib import Path

from Crypto.Cipher import AES

from .notification_schema import NOTIFICATIONS_V4_DDL
from .service import ServiceError
from .storage import canonical


MAX_BODY = 65_536
MAX_PLAINTEXT = 32_768
STATUSES = frozenset(('CREATED', 'EXECUTED', 'CONFIRMED', 'CANCELLED', 'REJECTED',
                      'EXPIRED', 'PAID', 'REVERSED', 'REFUNDED', 'REFUNDING'))


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def _constant(_):
    raise ValueError()


def _json(raw):
    value = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
    if not isinstance(value, dict):
        raise ValueError()
    return value


def _text(value, limit):
    if not isinstance(value, str) or not 1 <= len(value) <= limit or any(ord(c) < 32 for c in value):
        raise ValueError()
    return value


def _time(value):
    value = _text(value, 64)
    instant = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if instant.tzinfo is None:
        raise ValueError()
    return instant.astimezone(dt.timezone.utc).isoformat()


def file_key_source(path):
    """External secret reference, reread on every message for operator rotation.

    No current/previous-key fallback is invented. An operator must coordinate
    Console rotation; old-key messages fail authentication after replacement.
    """
    source = Path(path)

    def read():
        try:
            with source.open('rb') as stream:
                value = stream.read(257)
            if len(value) > 256:
                raise ValueError()
            return value.strip().decode('ascii')
        except (OSError, UnicodeError, ValueError):
            raise ServiceError(503, 'notification_key_unavailable') from None
    return read


def job_id(app_id, sandbox, order_id, invoice_id):
    return hashlib.sha256(canonical([app_id, bool(sandbox), order_id, invoice_id]).encode()).hexdigest()


def enqueue(db, order, invoice_id, now, *, new_revision=True):
    """Must run inside the caller's durable transaction."""
    identity = job_id(order['app_id'], order['sandbox'], order['id'], invoice_id)
    inserted = db.execute('''INSERT OR IGNORE INTO commerce_reconcile_jobs
        (id,app_id,sandbox,order_id,invoice_id,state,requested_revision,next_at,created_at,updated_at)
        VALUES(?,?,?,?,?,'Pending',1,?,?,?)''',
                          (identity, order['app_id'], order['sandbox'], order['id'], invoice_id, now, now, now)).rowcount
    if not inserted and new_revision:
        db.execute('''UPDATE commerce_reconcile_jobs SET requested_revision=requested_revision+1,
            state=CASE WHEN state='Running' AND lease_until>? THEN 'Running' ELSE 'Pending' END,
            attempts=CASE WHEN state='Running' AND lease_until>? THEN attempts ELSE 0 END,
            next_at=?,last_error='',updated_at=? WHERE id=?''', (now, now, now, now, identity))
    return identity


class NotificationInbox:
    def __init__(self, authority, commerce, keysource=None, allowednetworks=(), enabled=False):
        if type(enabled) is not bool:
            raise ValueError('Explicit notification activation required')
        self.authority, self.commerce, self.database = authority, commerce, authority.database
        self.enabled, self.keysource = enabled, keysource
        self.networks = tuple(ipaddress.ip_network(value, strict=True) for value in allowednetworks)
        if enabled and (not callable(keysource) or not self.networks or type(commerce.config.appId) is not int):
            raise ValueError('Incomplete notification configuration')

    def _source(self, client_ip):
        try:
            address = ipaddress.ip_address(client_ip)
        except (ValueError, TypeError):
            raise ServiceError(403, 'notification_source_denied') from None
        if not any(address in network for network in self.networks):
            raise ServiceError(403, 'notification_source_denied')

    def _decode(self, raw):
        try:
            if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_BODY:
                raise ValueError()
            outer = _json(raw.decode('utf-8'))
            if set(outer) != {'id', 'timestamp', 'payload'}:
                raise ValueError()
            _text(outer['id'], 256)
            _time(outer['timestamp'])  # Shape only. Never a freshness/authentication decision.
            encrypted = base64.b64decode(_text(outer['payload'], MAX_BODY), validate=True)
            if not 29 <= len(encrypted) <= MAX_PLAINTEXT + 28:
                raise ValueError()
        except (ValueError, TypeError, UnicodeError, binascii.Error, RecursionError):
            raise ServiceError(400, 'invalid_notification') from None
        try:
            encoded_key = self.keysource()
            if not isinstance(encoded_key, str) or len(encoded_key) > 256:
                raise ValueError()
            key = base64.b64decode(encoded_key, validate=True)
            if len(key) != 32:
                raise ValueError()
        except ServiceError:
            raise
        except Exception:
            raise ServiceError(503, 'notification_key_unavailable') from None
        try:
            cipher = AES.new(key, AES.MODE_GCM, nonce=encrypted[:12], mac_len=16)
            plaintext = cipher.decrypt_and_verify(encrypted[12:-16], encrypted[-16:])
            payload = _json(plaintext.decode('utf-8'))
            if set(payload) != {'app_id', 'notification_type', 'data'}:
                raise ValueError()
            if type(payload['app_id']) is not int or payload['app_id'] != self.commerce.config.appId:
                raise ValueError()
            kind = payload['notification_type']
            if kind not in ('INVOICE_STATUS', 'INVOICE_STATUS_SANDBOX', 'TEST_EVENT', 'TEST_EVENT_SANDBOX'):
                raise ValueError()
            sandbox = kind.endswith('_SANDBOX')
            if sandbox != self.commerce.config.sandbox:
                raise ValueError()
            data = _json(_text(payload['data'], MAX_PLAINTEXT))
            if kind.startswith('TEST_EVENT'):
                if data != {'test': 'TEST'}:
                    raise ValueError()
                return {'kind': 'Test', 'app_id': payload['app_id'], 'sandbox': sandbox}
            required = {'product_code', 'change_status_time', 'status_new', 'status_old',
                        'purchase_token', 'invoice_id', 'order_id', 'purchase_id'}
            if not required <= set(data) or set(data) - required - {'developer_payload'}:
                raise ValueError()
            product = _text(data['product_code'], 128)
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', product):
                raise ValueError()
            invoice = _text(data['invoice_id'], 30)
            order = _text(data['order_id'], 32)
            if not re.fullmatch(r'[1-9][0-9]{0,29}', invoice) or not re.fullmatch(r'[0-9a-f]{32}', order):
                raise ValueError()
            purchase = str(uuid.UUID(_text(data['purchase_id'], 64)))
            previous, current = _text(data['status_old'], 32).upper(), _text(data['status_new'], 32).upper()
            if previous not in STATUSES or current not in STATUSES:
                raise ValueError()
            _text(data['purchase_token'], 1024)  # Deliberately discarded.
            binding = data.get('developer_payload')
            if binding is not None:
                _text(binding, 512)
            return {'kind': 'Invoice', 'app_id': payload['app_id'], 'sandbox': sandbox,
                    'order_id': order, 'invoice_id': invoice, 'product_id': product, 'purchase_id': purchase,
                    'change_time': _time(data['change_status_time']), 'status_old': previous,
                    'status_new': current, 'binding': binding}
        except (ValueError, TypeError, UnicodeError, KeyError, OverflowError, RecursionError):
            raise ServiceError(400, 'invalid_notification') from None

    def receive(self, raw_body, client_ip):
        if not self.enabled:
            raise ServiceError(503, 'notifications_not_configured')
        self._source(client_ip)  # Actual transport peer only. Never reads forwarding headers.
        hint = self._decode(raw_body)
        digest = hashlib.sha256(canonical(hint).encode()).hexdigest()
        # Receipt has a short upstream response budget. Each possible writer
        # wait is bounded; failure is retried by RuStore, never acknowledged.
        now = self.authority._now(timeout=1)
        with self.database.transaction(timeout=1) as db:
            prior = db.execute('SELECT disposition FROM commerce_notification_inbox WHERE digest=?', (digest,)).fetchone()
            if prior:
                return {'accepted': True, 'duplicate': True, 'disposition': prior['disposition']}
            disposition, order = 'Test', None
            if hint['kind'] == 'Invoice':
                order = db.execute('SELECT * FROM commerce_orders WHERE id=?', (hint['order_id'],)).fetchone()
                if order and (order['app_id'] != hint['app_id'] or bool(order['sandbox']) != hint['sandbox']
                              or order['store_product'] != hint['product_id']
                              or hint['binding'] is not None and hint['binding'] != order['binding']
                              or order['invoice_id'] is not None and order['invoice_id'] != hint['invoice_id']
                              or order['purchase_id'] is not None and order['purchase_id'] != hint['purchase_id']):
                    raise ServiceError(409, 'notification_binding_mismatch')
                disposition = 'Queued' if order else 'Unmatched'
            db.execute('''INSERT INTO commerce_notification_inbox
                (digest,app_id,sandbox,kind,order_id,invoice_id,product_id,purchase_id,received_at,disposition)
                VALUES(?,?,?,?,?,?,?,?,?,?)''',
                       (digest, hint['app_id'], int(hint['sandbox']), hint['kind'], hint.get('order_id'),
                        hint.get('invoice_id'), hint.get('product_id'), hint.get('purchase_id'), now, disposition))
            if order:
                enqueue(db, order, hint['invoice_id'], now)
            return {'accepted': True, 'duplicate': False, 'disposition': disposition}
