"""Isolated SDK-reported commerce schema; ordinary15/versioned-staging16 stay exact."""
from contextlib import closing
from functools import lru_cache
import sqlite3

SDK_SCHEMA_VERSION = 125
SDK_COMMERCE_DDL = """
ALTER TABLE commerce_orders ADD COLUMN verification_mode TEXT NOT NULL DEFAULT 'provider_api'
 CHECK(verification_mode IN ('provider_api','sdk_client_reported'));
ALTER TABLE commerce_orders ADD COLUMN sdk_purchase_type TEXT;
ALTER TABLE commerce_orders ADD COLUMN sdk_product_type TEXT;
ALTER TABLE commerce_orders ADD COLUMN sdk_last_status TEXT;
ALTER TABLE commerce_orders ADD COLUMN sdk_reported_at INTEGER;
CREATE TRIGGER commerce_mode_immutable125 BEFORE UPDATE OF verification_mode ON commerce_orders
 WHEN OLD.verification_mode<>NEW.verification_mode
 BEGIN SELECT RAISE(ABORT,'commerce verification mode is immutable'); END;
"""

@lru_cache(maxsize=1)
def expected_sdk_objects():
    from .operations import _expected, _objects
    with closing(sqlite3.connect(':memory:')) as db:
        for kind in ('table', 'index', 'trigger', 'view'):
            for typ, _, _, sql in _expected(15):
                if typ == kind:
                    db.execute(sql)
        db.executescript(SDK_COMMERCE_DDL)
        return _objects(db)

def validate_sdk_database(db, *, full=True):
    """full runs the whole-file checks, for deploy, backup, restore and preflight. An ordinary
    service restart checks only the schema, because their cost grows with the database."""
    from .operations import OperationError, _objects
    if (full and (db.execute('PRAGMA quick_check').fetchall() != [('ok',)]
                  or db.execute('PRAGMA foreign_key_check').fetchone() is not None)
            or db.execute('SELECT version FROM schema_info').fetchall() != [(SDK_SCHEMA_VERSION,)]
            or _objects(db) != expected_sdk_objects()):
        raise OperationError('sdk125_database_schema_mismatch')
    return SDK_SCHEMA_VERSION

def apply_sdk_upgrade(db):
    """Caller must already own a stopped/backup-backed15 or fresh authority."""
    from .operations import _validate
    old_factory = db.row_factory
    try:
        db.row_factory = None
        if _validate(db) != 15:
            raise RuntimeError('SDK125 requires exact ordinary schema15')
        # executescript would commit the caller's transaction. Execute ALTERs
        # and the whole trigger separately for complete transactional rollback.
        statements = SDK_COMMERCE_DDL.split('CREATE TRIGGER', 1)
        for statement in statements[0].split(';'):
            if statement.strip():
                db.execute(statement)
        db.execute('CREATE TRIGGER ' + statements[1].strip())
        db.execute('UPDATE schema_info SET version=?', (SDK_SCHEMA_VERSION,))
        validate_sdk_database(db)
    finally:
        db.row_factory = old_factory

