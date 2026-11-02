"""Idempotent store receipts atomically projected into the staging server wallet."""
import os
import uuid
from pathlib import Path

from .commerce_schemas import CommerceConfig, valid_order_id
from .rustore_provider import InvalidProviderResponse, ProviderUnavailable, RuStoreInvoiceProvider, UnavailablePurchaseProvider, VerifiedInvoice
from .schemas import Grant, INT_MAX
from .service import ServiceError
from .storage import canonical
from .wallet import commerce_projection
from .guards import require_actor
from .production_runtime122 import production_enabled


class Commerce:
    statuses = {'CREATED', 'EXECUTED', 'CONFIRMED', 'CANCELLED', 'REJECTED', 'EXPIRED', 'PAID', 'REVERSED', 'REFUNDING', 'REFUNDED'}
    terminal_failures = {'CANCELLED', 'REJECTED', 'EXPIRED'}
    pending_sql = "(o.state IN ('Created','Executed','Held','RefundReview') OR (o.state='Confirmed' AND COALESCE(a.state,'Pending')!='Acknowledged'))"
    pending_byte_limit = 48 * 1024  # Below the app's 64KiB bounded HTTP buffer.

    def __init__(self, authority, config_path: Path, provider=None):
        self.authority = authority
        self.database = authority.database
        self.config = CommerceConfig.model_validate_json(Path(config_path).read_text('utf-8-sig'))
        self.provider = provider if provider is not None else UnavailablePurchaseProvider()
        if provider is None and self.config.enabled and self.config.verificationMode == 'provider_api':
            key_id = os.getenv('HOTR_RUSTORE_KEY_ID')
            key_file = os.getenv('HOTR_RUSTORE_PRIVATE_KEY_FILE')
            if bool(key_id) != bool(key_file):
                raise RuntimeError('Incomplete server-only RuStore authentication configuration')
            if key_id and key_file:
                from .rustore_auth import RuStoreTokenSupplier
                self.provider = RuStoreInvoiceProvider(RuStoreTokenSupplier.from_file(key_id, key_file))
        if self.config.verificationMode == 'sdk_client_reported':
            if not getattr(self.database, 'sdk_commerce125', False) or self.provider.configured:
                raise RuntimeError('Isolated SDK125 storage without a verification provider required')
        self.checkpoint = None  # In-process transaction fault tests; never an HTTP control.

    @staticmethod
    def _mode(row):
        return row['verification_mode'] if 'verification_mode' in row.keys() else 'provider_api'

    def _ready(self):
        return self.config.enabled and (
            self.config.verificationMode == 'sdk_client_reported'
            and getattr(self.database, 'sdk_commerce125', False)
            or self.config.verificationMode == 'provider_api' and self.provider.configured)

    def catalog(self, actor):
        with self.database.transaction() as db:
            require_actor(db, actor)
            ready = self._ready() and self.config.sandbox is not production_enabled(self.authority)
            products = [{'id': p.id, 'storeProductId': p.storeProductId, 'coins': p.coins,
                         'grant': p.grant.model_dump(), 'amountMinor': p.amountMinor,
                         'currency': p.currency, 'quantity': 1,
                         **self._eligibility(db, actor.player, p.id, p.purchaseLimitPerPlayer)}
                        for p in self.config.products if ready and p.enabled]
        return {'version': self.config.version, 'verificationMode': self.config.verificationMode,
                'appId': self.config.appId, 'sandbox': self.config.sandbox,
                'enabled': ready, 'productionEnabled': production_enabled(self.authority),
                'fullGameplayWallet': production_enabled(self.authority), 'balanceScope': 'server_wallet',
                'serverWalletProjection': True, 'normalUnityProfileIntegrated': False,
                'reason': (('production_server_wallet' if production_enabled(self.authority) else 'staging_server_wallet') if ready else
                           'live_commerce_requires_wallet_integration' if self.config.enabled and not self.config.sandbox else 'commerce_not_configured'),
                'walletScope': 'Authoritative staging server balances and typed spending; normal Unity profiles remain unmigrated.',
                'fullGrantDelivery': True, 'stablePlayerOfferEligibility': True,
                'products': products}

    @staticmethod
    def _grant(row):
        return Grant.model_validate_json(row['grant_json']) if row['grant_json'] else Grant(coins=row['coins'])

    @classmethod
    def _eligibility(cls, db, player, product, limit):
        entitlement = db.execute('SELECT state,order_id FROM commerce_entitlements WHERE player_id=? AND offer_id=?',
                                 (player, product)).fetchone()
        quarantined = db.execute("SELECT 1 FROM commerce_orders WHERE player_id=? AND state='RefundReview'", (player,)).fetchone()
        pending = None
        if entitlement:
            # Persisted one-time entitlement cannot be bypassed by a catalog
            # mistakenly changing this offer to repeatable after its purchase.
            limit = 1
            status = 'Purchased' if entitlement['state'] == 'Consumed' else 'Pending'
            if entitlement['state'] == 'Reserved':
                pending = entitlement['order_id']
        else:
            status = 'Available'
            existing = db.execute('''SELECT o.id FROM commerce_orders o LEFT JOIN commerce_delivery_ack a ON a.order_id=o.id
                WHERE o.player_id=? AND o.internal_product=? AND ''' + cls.pending_sql + ' ORDER BY o.rowid LIMIT 1',
                                  (player, product)).fetchone()
            if existing:
                pending = existing['id']
        if quarantined:
            status = 'RefundReview'
        return {'purchaseLimitPerPlayer': limit, 'repeatable': limit is None,
                'eligible': status == 'Available', 'pendingOrderId': pending, 'eligibility': status}

    @staticmethod
    def _order(db, actor, order_id):
        require_actor(db, actor)
        if not valid_order_id(order_id):
            raise ServiceError(404, 'order_not_found')
        row = db.execute('SELECT * FROM commerce_orders WHERE id=? AND player_id=?', (order_id, actor.player)).fetchone()
        if not row:
            raise ServiceError(404, 'order_not_found')
        return row

    def _view(self, db, row):
        credit = db.execute('SELECT * FROM commerce_credits WHERE order_id=?', (row['id'],)).fetchone()
        ack = db.execute('SELECT state FROM commerce_delivery_ack WHERE order_id=?', (row['id'],)).fetchone()
        wallet = db.execute('SELECT initialized FROM wallets WHERE player_id=?', (row['player_id'],)).fetchone()
        quarantine = db.execute("SELECT 1 FROM commerce_orders WHERE player_id=? AND state='RefundReview'", (row['player_id'],)).fetchone()
        spendable = credit is not None and wallet is not None and bool(wallet['initialized']) and not bool(quarantine)
        requests = db.execute('SELECT invoice_id,state,last_error,attempts FROM commerce_invoice_requests WHERE order_id=? ORDER BY updated_at,invoice_id LIMIT 100', (row['id'],)).fetchall()
        return {'orderId': row['id'], 'playerId': row['player_id'], 'state': row['state'],
                'verificationMode': self._mode(row),
                'creationCommandId': row['creation_command_id'],
                'catalogVersion': row['catalog_version'], 'productId': row['internal_product'],
                'coins': row['coins'], 'amountMinor': row['amount_minor'], 'currency': row['currency'],
                'grant': self._grant(row).model_dump(),
                **self._eligibility(db, row['player_id'], row['internal_product'], row['purchase_limit']),
                'reservationReleased': bool(row['reservation_released']),
                'invoiceId': row['invoice_id'], 'purchaseId': row['purchase_id'],
                'sdk': {'orderId': row['id'], 'productId': row['store_product'], 'quantity': 1,
                        'appUserId': row['player_id'], 'developerPayload': row['binding'], 'sandbox': bool(row['sandbox'])},
                'credit': None if credit is None else {'receiptId': credit['id'], 'coins': credit['coins'],
                                                       'verificationMode': self._mode(row),
                                                       'grant': self._grant(credit).model_dump(),
                                                       'createdAt': credit['created_at'], 'balanceScope': 'commerce_receipt_audit'},
                'deliveryAcknowledgement': None if ack is None else ack['state'],
                'pendingVerification': [dict(r) for r in requests],
                'productionEnabled': production_enabled(self.authority), 'availableToSpend': spendable,
                'availableInServerWallet': spendable, 'balanceScope': 'server_wallet',
                'normalUnityProfileIntegrated': False, 'localProfileMutated': False}

    def order(self, actor, order_id):
        with self.database.transaction() as db:
            return self._view(db, self._order(db, actor, order_id))

    def pending(self, actor, after=0, limit=100):
        """Recover server-owned orders without trusting a device's local journal."""
        with self.database.transaction() as db:
            require_actor(db, actor)
            rows = db.execute('''SELECT o.rowid AS cursor,o.* FROM commerce_orders o
                LEFT JOIN commerce_delivery_ack a ON a.order_id=o.id WHERE o.player_id=? AND o.rowid>? AND '''
                              + self.pending_sql + ' ORDER BY o.rowid LIMIT ?', (actor.player, after, limit + 1)).fetchall()
            value = {'playerId': actor.player, 'orders': [], 'nextCursor': after,
                     'hasMore': bool(rows), 'productionEnabled': production_enabled(self.authority)}
            for row in rows[:limit]:
                view = self._view(db, row)
                # "false" is one byte longer than "true" in JSON.
                candidate = value | {'orders': [*value['orders'], view], 'nextCursor': row['cursor'], 'hasMore': False}
                if len(canonical(candidate).encode('utf-8')) > self.pending_byte_limit:
                    if not value['orders']:
                        raise ServiceError(503, 'commerce_order_view_too_large')
                    break
                value = candidate
            value['hasMore'] = len(rows) > len(value['orders'])
            return value

    def create(self, actor, request):
        def run(db):
            def execute():
                if not self._ready():
                    raise ServiceError(503, 'commerce_not_configured')
                if not self.config.sandbox and not production_enabled(self.authority):
                    raise ServiceError(503, 'live_commerce_requires_wallet_integration')
                if production_enabled(self.authority) and self.config.sandbox:
                    raise ServiceError(503, 'purchase_environment_mismatch')
                product = next((p for p in self.config.products if p.id == request.productId and p.enabled), None)
                if product is None:
                    raise ServiceError(404, 'product_unavailable')
                wallet = db.execute('SELECT initialized FROM wallets WHERE player_id=?', (actor.player,)).fetchone()
                if not wallet or not wallet['initialized']:
                    raise ServiceError(409, 'wallet_migration_required')
                if db.execute("SELECT 1 FROM commerce_orders WHERE player_id=? AND state='RefundReview'", (actor.player,)).fetchone():
                    raise ServiceError(409, 'wallet_refund_review_required')
                entitlement = db.execute('SELECT state,order_id FROM commerce_entitlements WHERE player_id=? AND offer_id=?',
                                         (actor.player, product.id)).fetchone()
                if entitlement:
                    if entitlement['state'] == 'Consumed':
                        raise ServiceError(409, 'commerce_offer_already_purchased')
                    return self._view(db, self._order(db, actor, entitlement['order_id']))
                order_id = uuid.uuid4().hex
                binding = 'hotr-order-v1:' + order_id + ':' + uuid.uuid4().hex
                columns = 'id,player_id,catalog_version,internal_product,store_product,app_id,sandbox,amount_minor,currency,coins,binding,created_at,updated_at,grant_json,purchase_limit,creation_command_id'
                values = (order_id, actor.player, self.config.version, product.id, product.storeProductId,
                          self.config.appId, int(self.config.sandbox), product.amountMinor, product.currency,
                          product.coins, binding, actor.now, actor.now, canonical(product.grant.model_dump()),
                          product.purchaseLimitPerPlayer, request.commandId)
                if getattr(self.database, 'sdk_commerce125', False):
                    columns += ',verification_mode'
                    values += (self.config.verificationMode,)
                db.execute('INSERT INTO commerce_orders (' + columns + ') VALUES('
                           + ','.join('?' for _ in values) + ')', values)
                if product.purchaseLimitPerPlayer == 1:
                    db.execute("INSERT INTO commerce_entitlements VALUES(?,?,?,'Reserved',?)", (actor.player, product.id, order_id, actor.now))
                return self._view(db, self._order(db, actor, order_id))
            return self.authority._command(db, actor, 'commerce.create', request.commandId, request.model_dump(), execute)
        return self.authority._transaction(run)

    def _request_result(self, order_id, invoice_id, state, error, now):
        with self.database.transaction() as db:
            db.execute('UPDATE commerce_invoice_requests SET state=?,last_error=?,updated_at=? WHERE order_id=? AND invoice_id=?',
                       (state, error, now, order_id, invoice_id))

    def _match(self, row, invoice, requested):
        if not isinstance(invoice, VerifiedInvoice):
            raise InvalidProviderResponse()
        if (type(invoice.app_id) is not int or type(invoice.sandbox) is not bool
                or type(invoice.amount_minor) is not int or not 0 < invoice.amount_minor <= INT_MAX
                or not isinstance(invoice.status, str) or not isinstance(invoice.acknowledgement, str)
                or invoice.status not in self.statuses or invoice.acknowledgement not in {'PENDING', 'ACKNOWLEDGED', 'UNKNOWN'}):
            raise InvalidProviderResponse()
        expected = (requested, row['app_id'], bool(row['sandbox']), row['id'], row['store_product'],
                    row['player_id'], row['binding'], row['amount_minor'], row['currency'])
        actual = (invoice.invoice_id, invoice.app_id, invoice.sandbox, invoice.order_id, invoice.product_id,
                  invoice.app_user_id, invoice.developer_payload, invoice.amount_minor, invoice.currency)
        if actual != expected:
            raise ServiceError(409, 'purchase_binding_mismatch')
        try:
            return str(uuid.UUID(invoice.purchase_id))
        except (ValueError, TypeError, AttributeError):
            raise InvalidProviderResponse() from None

    def reconcile(self, actor, order_id, request):
        """An authenticated callback or future verified webhook worker queries here.

        An unverified invoice request never reserves its global invoice identity:
        otherwise an attacker could submit somebody else's invoice first and
        prevent its real owner from receiving it. No network call holds a DB lock.
        """
        invoice_id = request.invoiceId
        with self.database.transaction() as db:
            row = dict(self._order(db, actor, order_id))
            if self.config.verificationMode != 'provider_api' or self._mode(row) != 'provider_api':
                raise ServiceError(409, 'use_sdk_client_report')
            if not row['sandbox'] and not production_enabled(self.authority):
                raise ServiceError(503, 'live_commerce_requires_wallet_integration')
            if production_enabled(self.authority) and row['sandbox']:
                raise ServiceError(503, 'purchase_environment_mismatch')
            if row['invoice_id'] is not None and row['invoice_id'] != invoice_id:
                raise ServiceError(409, 'order_already_bound')
            db.execute('''INSERT INTO commerce_invoice_requests(order_id,invoice_id,attempts,updated_at) VALUES(?,?,1,?)
                ON CONFLICT(order_id,invoice_id) DO UPDATE SET attempts=attempts+1,updated_at=excluded.updated_at''',
                       (order_id, invoice_id, actor.now))
        try:
            invoice = self.provider.lookup(invoice_id, bool(row['sandbox']))
            purchase_id = self._match(row, invoice, invoice_id)
        except ProviderUnavailable:
            self._request_result(order_id, invoice_id, 'Unavailable', 'provider_unavailable', actor.now)
            raise ServiceError(503, 'provider_unavailable') from None
        except InvalidProviderResponse:
            self._request_result(order_id, invoice_id, 'Rejected', 'provider_invalid_response', actor.now)
            raise ServiceError(503, 'provider_invalid_response') from None
        except ServiceError as error:
            self._request_result(order_id, invoice_id, 'Rejected', error.code, actor.now)
            raise
        return self._commit_observation(actor, order_id, invoice_id, purchase_id,
                                        invoice.status, invoice.acknowledgement)

    def _match_sdk(self, row, order_id, report):
        # These are client claims from GetPurchase, not independent store proof.
        if (bool(row['sandbox']) != self.config.sandbox
                or bool(row['sandbox']) == production_enabled(self.authority)
                or row['app_id'] != self.config.appId):
            raise ServiceError(409, 'sdk_purchase_application_environment_mismatch')
        expected = (row['id'], row['store_product'], row['binding'], 1,
                    bool(row['sandbox']), row['amount_minor'], row['currency'])
        actual = (report.orderId, report.productId, report.developerPayload, report.quantity,
                  report.sandbox, report.amountMinor, report.currency)
        if actual != expected or report.orderId != order_id:
            raise ServiceError(409, 'sdk_purchase_binding_mismatch')
        if (row['sdk_purchase_type'] not in (None, 'UNDEFINED')
                and report.purchaseType != 'UNDEFINED' and row['sdk_purchase_type'] != report.purchaseType
                or row['sdk_product_type'] is not None and row['sdk_product_type'] != report.productType):
            raise ServiceError(409, 'sdk_purchase_identity_changed')

    def sdk_report(self, actor, order_id, report):
        if self.config.verificationMode != 'sdk_client_reported':
            raise ServiceError(409, 'sdk_client_reported_mode_required')
        if not self.config.sandbox and not production_enabled(self.authority):
            raise ServiceError(503, 'live_commerce_requires_wallet_integration')
        if production_enabled(self.authority) and self.config.sandbox:
            raise ServiceError(503, 'purchase_environment_mismatch')
        status = {'INVOICE_CREATED': 'CREATED', 'PROCESSING': 'EXECUTED',
                  'EXECUTING': 'EXECUTED'}.get(report.status, report.status)
        return self._commit_observation(actor, order_id, report.invoiceId, report.purchaseId,
            status, report.acknowledgementState, verification_mode='sdk_client_reported',
            sdk_report=report)

    def _commit_observation(self, actor, order_id, invoice_id, purchase_id, status,
                            acknowledgement, *, verification_mode='provider_api', sdk_report=None):
        with self.database.transaction() as db:
            current = self._order(db, actor, order_id)
            if self._mode(current) != verification_mode:
                raise ServiceError(409, 'purchase_verification_mode_mismatch')
            if sdk_report is not None:
                self._match_sdk(current, order_id, sdk_report)
                db.execute('''UPDATE commerce_orders SET sdk_purchase_type=?,sdk_product_type=?,
                    sdk_last_status=?,sdk_reported_at=? WHERE id=?''',
                    (current['sdk_purchase_type'] if sdk_report.purchaseType == 'UNDEFINED'
                        and current['sdk_purchase_type'] not in (None, 'UNDEFINED')
                        else sdk_report.purchaseType,
                     sdk_report.productType, sdk_report.status, actor.now, order_id))
            if current['invoice_id'] is not None and current['invoice_id'] != invoice_id:
                raise ServiceError(409, 'order_already_bound')
            existing = db.execute('''SELECT id FROM commerce_orders WHERE app_id=? AND sandbox=?
                AND (invoice_id=? OR purchase_id=?) AND id!=?''',
                                  (current['app_id'], current['sandbox'], invoice_id, purchase_id, order_id)).fetchone()
            if existing:
                raise ServiceError(409, 'purchase_already_bound')
            credit = db.execute('SELECT id FROM commerce_credits WHERE order_id=?', (order_id,)).fetchone()
            if current['purchase_id'] is not None and current['purchase_id'] != purchase_id:
                raise ServiceError(409, 'purchase_identity_changed')
            state = current['state']
            # Refund initiation/refund/reversal evidence is sticky across ALL
            # later observations. REFUNDING is not a successful new payment;
            # it enters review without granting or automatically debiting coins.
            # This includes delayed confirmation started before refund evidence
            # committed. There is no provider revision clock with which to prove
            # that such a confirmation supersedes a terminal refund.
            late_once = current['purchase_limit'] == 1 and current['reservation_released'] and status == 'CONFIRMED'
            # An SDK cancel report can precede a bank-return confirmation of the same
            # order. With no other order holding the offer it is a normal one-time
            # delivery, not a double payment, and must not freeze the wallet.
            if (late_once and verification_mode == 'sdk_client_reported' and state != 'RefundReview'
                    and not db.execute('SELECT 1 FROM commerce_entitlements WHERE player_id=? AND offer_id=?',
                                       (actor.player, current['internal_product'])).fetchone()):
                db.execute("INSERT INTO commerce_entitlements VALUES(?,?,?,'Reserved',?)",
                           (actor.player, current['internal_product'], order_id, actor.now))
                db.execute('UPDATE commerce_orders SET reservation_released=0 WHERE id=?', (order_id,))
                late_once = False
            quarantined = state == 'RefundReview' or status in ('REFUNDING', 'REFUNDED', 'REVERSED') or late_once
            if quarantined:
                state = 'RefundReview'
                if credit:
                    db.execute("UPDATE commerce_delivery_ack SET state='RefundReview',updated_at=? WHERE order_id=?", (actor.now, order_id))
            elif status == 'CONFIRMED':
                if not credit:
                    total = db.execute('SELECT COALESCE(SUM(coins),0) FROM commerce_credits WHERE player_id=?', (actor.player,)).fetchone()[0]
                    if total + current['coins'] > INT_MAX:
                        raise ServiceError(409, 'purchase_credit_overflow')
                    prefix = 'rustore-sdk' if verification_mode == 'sdk_client_reported' else 'rustore'
                    receipt = f"{prefix}/{current['app_id']}/{'sandbox' if current['sandbox'] else 'live'}/{invoice_id}"
                    grant = self._grant(current)
                    if current['purchase_limit'] == 1:
                        reserved = db.execute("SELECT 1 FROM commerce_entitlements WHERE player_id=? AND offer_id=? AND order_id=? AND state='Reserved'",
                                              (actor.player, current['internal_product'], order_id)).fetchone()
                        if not reserved:
                            raise ServiceError(409, 'commerce_entitlement_conflict')
                    db.execute('''INSERT INTO commerce_credits
                        (id,order_id,player_id,app_id,sandbox,invoice_id,purchase_id,coins,created_at,grant_json)
                        VALUES(?,?,?,?,?,?,?,?,?,?)''',
                               (receipt, order_id, actor.player, current['app_id'], current['sandbox'], invoice_id, purchase_id, current['coins'], actor.now, canonical(grant.model_dump())))
                    commerce_projection(db, actor.player, receipt, grant, actor.now)
                    if current['purchase_limit'] == 1:
                        db.execute("UPDATE commerce_entitlements SET state='Consumed',updated_at=? WHERE order_id=?", (actor.now, order_id))
                state = 'Confirmed'
                old_ack = db.execute('SELECT state FROM commerce_delivery_ack WHERE order_id=?', (order_id,)).fetchone()
                ack = ('RefundReview' if state == 'RefundReview' else
                       'Acknowledged' if acknowledgement == 'ACKNOWLEDGED' or old_ack and old_ack['state'] == 'Acknowledged' else 'Pending')
                db.execute('''INSERT INTO commerce_delivery_ack VALUES(?,?,?) ON CONFLICT(order_id)
                    DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at''', (order_id, ack, actor.now))
            elif not credit:
                if current['purchase_limit'] == 1 and status in self.terminal_failures:
                    db.execute("DELETE FROM commerce_entitlements WHERE order_id=? AND state='Reserved'", (order_id,))
                    db.execute('UPDATE commerce_orders SET reservation_released=1 WHERE id=?', (order_id,))
                # Once a one-time reservation has been released, stale held or
                # created observations cannot silently reacquire it.
                if not current['reservation_released']:
                    state = 'Held' if status == 'PAID' else status.title()
            db.execute('UPDATE commerce_orders SET invoice_id=?,purchase_id=?,state=?,updated_at=? WHERE id=?',
                       (invoice_id, purchase_id, state, actor.now, order_id))
            if verification_mode == 'provider_api':
                db.execute("UPDATE commerce_invoice_requests SET state='Verified',last_error='',updated_at=? WHERE order_id=? AND invoice_id=?", (actor.now, order_id, invoice_id))
            if self.checkpoint:
                self.checkpoint('BeforeCreditCommit')
            value = self._view(db, self._order(db, actor, order_id))
        if self.checkpoint:
            self.checkpoint('AfterCreditCommit')
        return value

    def credits(self, actor, after=0, limit=100):
        with self.database.transaction() as db:
            require_actor(db, actor)
            rows = db.execute('SELECT rowid AS cursor,id,order_id,coins,grant_json,created_at FROM commerce_credits WHERE player_id=? AND rowid>? ORDER BY rowid LIMIT ?',
                              (actor.player, after, limit + 1)).fetchall()
            page = rows[:limit]
            return {'playerId': actor.player, 'balanceScope': 'commerce_receipt_audit',
                    'availableToSpend': False, 'fullGameplayWallet': production_enabled(self.authority),
                    'serverWalletProjection': True, 'normalUnityProfileIntegrated': False,
                    'spendabilityEndpoint': '/v1/wallet',
                    'credits': [{key: r[key] for key in ('cursor', 'id', 'order_id', 'coins', 'created_at')}
                        | {'grant': self._grant(r).model_dump(), 'verificationMode': self._mode(
                            db.execute('SELECT * FROM commerce_orders WHERE id=?', (r['order_id'],)).fetchone())} for r in page],
                    'nextCursor': page[-1]['cursor'] if page else after,
                    'hasMore': len(rows) > limit}
