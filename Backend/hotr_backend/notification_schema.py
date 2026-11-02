"""Additive schema4 notification tables; importing this module has no side effects."""

NOTIFICATIONS_V4_DDL = '''
CREATE TABLE commerce_notification_inbox (
 digest TEXT PRIMARY KEY, app_id INTEGER NOT NULL,
 sandbox INTEGER NOT NULL CHECK(sandbox IN (0,1)),
 kind TEXT NOT NULL CHECK(kind IN ('Invoice','Test')),
 order_id TEXT, invoice_id TEXT, product_id TEXT, purchase_id TEXT,
 received_at INTEGER NOT NULL,
 disposition TEXT NOT NULL CHECK(disposition IN ('Queued','Unmatched','Test')));
CREATE TABLE commerce_reconcile_jobs (
 id TEXT PRIMARY KEY, app_id INTEGER NOT NULL,
 sandbox INTEGER NOT NULL CHECK(sandbox IN (0,1)),
 order_id TEXT NOT NULL REFERENCES commerce_orders(id), invoice_id TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('Pending','Running','Done','Dead')),
 requested_revision INTEGER NOT NULL CHECK(requested_revision>0),
 claimed_revision INTEGER NOT NULL DEFAULT 0,
 lease_token TEXT, lease_until INTEGER NOT NULL DEFAULT 0,
 attempts INTEGER NOT NULL DEFAULT 0, next_at INTEGER NOT NULL,
 last_error TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
 UNIQUE(app_id,sandbox,order_id,invoice_id));
CREATE INDEX commerce_reconcile_due ON commerce_reconcile_jobs(state,next_at,lease_until);
'''
