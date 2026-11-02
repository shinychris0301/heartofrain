"""Bounded durable reconciliation worker; no provider/SDK acknowledgement writes."""
import re
import uuid

from .commerce_schemas import ReconcileCommerceOrder
from .notifications import enqueue
from .service import Actor, ServiceError


class ReconciliationWorker:
    def __init__(self, inbox, commerce=None, *, lease_seconds=60, max_attempts=16):
        self.inbox, self.commerce = inbox, commerce or inbox.commerce
        self.authority, self.database = inbox.authority, inbox.database
        if not 15 <= lease_seconds <= 600 or not 1 <= max_attempts <= 64:
            raise ValueError('Invalid bounded worker limits')
        self.lease_seconds, self.max_attempts = lease_seconds, max_attempts

    def seed_due(self, limit=50, poll_seconds=300):
        """Discover only already-known invoice IDs. Never invent/list store invoices.

        Done confirmed orders are polled too, to observe acknowledgement/refund
        changes when a notification was missed. Dead jobs require a genuinely new
        authenticated notification or explicit future operator repair.
        """
        if type(limit) is not int or not 1 <= limit <= 100 or type(poll_seconds) is not int or not 30 <= poll_seconds <= 86_400:
            raise ValueError('Invalid bounded seeding limits')
        now = self.authority._now()
        count = 0
        with self.database.transaction() as db:
            rows = db.execute('''SELECT o.*,r.invoice_id AS candidate FROM commerce_orders o
                JOIN commerce_invoice_requests r ON r.order_id=o.id
                LEFT JOIN commerce_reconcile_jobs j ON j.app_id=o.app_id AND j.sandbox=o.sandbox
                    AND j.order_id=o.id AND j.invoice_id=r.invoice_id
                WHERE o.state IN ('Created','Executed','Held','Confirmed')
                    AND (o.invoice_id=r.invoice_id OR (o.invoice_id IS NULL AND r.state IN ('Pending','Unavailable')))
                    AND (j.id IS NULL OR (j.state='Done' AND j.updated_at<=?))
                ORDER BY COALESCE(j.updated_at,0),o.created_at,o.id,r.invoice_id LIMIT ?''', (now - poll_seconds, limit)).fetchall()
            for row in rows:
                enqueue(db, row, row['candidate'], now)
                count += 1
        return count

    def _claim(self, worker_id, now):
        if not isinstance(worker_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', worker_id):
            raise ValueError('Invalid worker identifier')
        with self.database.transaction() as db:
            row = db.execute('''SELECT * FROM commerce_reconcile_jobs WHERE
                (state='Pending' AND next_at<=?) OR (state='Running' AND lease_until<=?)
                ORDER BY next_at,created_at,id LIMIT 1''', (now, now)).fetchone()
            if row is None:
                return None
            lease = uuid.uuid4().hex
            db.execute('''UPDATE commerce_reconcile_jobs SET state='Running',claimed_revision=requested_revision,
                lease_token=?,lease_until=?,attempts=attempts+1,updated_at=? WHERE id=?''',
                       (lease, now + self.lease_seconds, now, row['id']))
            claimed = dict(db.execute('SELECT * FROM commerce_reconcile_jobs WHERE id=?', (row['id'],)).fetchone())
            order = db.execute('SELECT player_id FROM commerce_orders WHERE id=?', (row['order_id'],)).fetchone()
            claimed['player_id'] = order['player_id'] if order else None
            return claimed

    def _finish(self, claim, now, *, retry=False, error='', terminal=False):
        with self.database.transaction() as db:
            current = db.execute('SELECT * FROM commerce_reconcile_jobs WHERE id=?', (claim['id'],)).fetchone()
            if current is None or current['state'] != 'Running' or current['lease_token'] != claim['lease_token']:
                return 'StaleLease'
            if current['requested_revision'] != claim['claimed_revision']:
                state, next_at, attempts = 'Pending', now, 0
            elif terminal or retry and current['attempts'] >= self.max_attempts:
                state, next_at, attempts = 'Dead', now, current['attempts']
            elif retry:
                state, next_at, attempts = 'Pending', now + min(3600, 15 * 2 ** min(current['attempts'] - 1, 8)), current['attempts']
            else:
                state, next_at, attempts = 'Done', now, 0
            db.execute('''UPDATE commerce_reconcile_jobs SET state=?,lease_token=NULL,lease_until=0,
                attempts=?,next_at=?,last_error=?,updated_at=? WHERE id=? AND lease_token=?''',
                       (state, attempts, next_at, error, now, claim['id'], claim['lease_token']))
            return state

    def run_once(self, worker_id):
        now = self.authority._now()
        claim = self._claim(worker_id, now)
        if claim is None:
            return {'worked': False, 'state': 'Idle'}
        try:
            if claim['player_id'] is None:
                raise ServiceError(404, 'order_not_found')
            # Commerce owns active-account checks before AND after the provider
            # request. A worker actor never bypasses deletion's final commit guard.
            result = self.commerce.reconcile(Actor(claim['player_id'], now), claim['order_id'],
                                             ReconcileCommerceOrder(invoiceId=claim['invoice_id']))
            pending = result['state'] in ('Created', 'Executed', 'Held')
            state = self._finish(claim, self.authority._now(), retry=pending,
                                 error='payment_not_final' if pending else '')
            return {'worked': True, 'state': state, 'orderState': result['state']}
        except ServiceError as error:
            code = error.code if isinstance(error.code, str) and re.fullmatch(r'[a-z0-9_]{1,64}', error.code) else 'reconciliation_failed'
            state = self._finish(claim, self.authority._now(), retry=error.status >= 500,
                                 terminal=error.status < 500, error=code)
            return {'worked': True, 'state': state, 'error': code}
        except Exception:
            # No response body, key, token, provider exception or purchase data
            # becomes a log/diagnostic. Durable work survives process failures.
            state = self._finish(claim, self.authority._now(), retry=True, error='worker_unavailable')
            return {'worked': True, 'state': state, 'error': 'worker_unavailable'}

    def run_bounded(self, worker_id, max_jobs=50):
        if type(max_jobs) is not int or not 1 <= max_jobs <= 1000:
            raise ValueError('Invalid bounded job count')
        results = []
        for _ in range(max_jobs):
            result = self.run_once(worker_id)
            results.append(result)
            if not result['worked']:
                break
        return results
