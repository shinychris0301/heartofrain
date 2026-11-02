"""Pure additive schema5 for explicitly operated invoice discovery."""

DISCOVERY_V5_DDL = '''
CREATE TABLE commerce_discovery_cursors (
 app_id INTEGER NOT NULL, sandbox INTEGER NOT NULL CHECK(sandbox IN (0,1)),
 invoice_date TEXT NOT NULL, status_filter TEXT NOT NULL,
 scan_revision INTEGER NOT NULL CHECK(scan_revision>0), next_page INTEGER NOT NULL DEFAULT 0,
 page_size INTEGER NOT NULL CHECK(page_size BETWEEN 1 AND 500), total_pages INTEGER,
 state TEXT NOT NULL CHECK(state IN ('Pending','Running','Complete')),
 lease_token TEXT, lease_until INTEGER NOT NULL DEFAULT 0, last_error TEXT NOT NULL DEFAULT '',
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
 PRIMARY KEY(app_id,sandbox,invoice_date,status_filter));
CREATE TABLE commerce_discovery_seen (
 app_id INTEGER NOT NULL, sandbox INTEGER NOT NULL,
 invoice_date TEXT NOT NULL, status_filter TEXT NOT NULL, scan_revision INTEGER NOT NULL,
 invoice_id TEXT NOT NULL, order_id TEXT NOT NULL REFERENCES commerce_orders(id), created_at INTEGER NOT NULL,
 PRIMARY KEY(app_id,sandbox,invoice_date,status_filter,scan_revision,invoice_id),
 FOREIGN KEY(app_id,sandbox,invoice_date,status_filter)
 REFERENCES commerce_discovery_cursors(app_id,sandbox,invoice_date,status_filter));
'''
