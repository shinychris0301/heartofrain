"""A bounded, rolled-back database writer probe, not release certification."""
import sqlite3

from .storage import SCHEMA_VERSION


def database_write_ready(database):
    expected_version = SCHEMA_VERSION
    if getattr(database, 'sdk_commerce125', False) is True:
        from .sdk_schema125 import SDK_SCHEMA_VERSION
        expected_version = SDK_SCHEMA_VERSION
    try:
        with database.connect(timeout=1.0) as db:
            try:
                # Authenticated reads advance the durable clock; a service that
                # can only SELECT cannot serve ordinary game requests either.
                db.execute('BEGIN IMMEDIATE')
                rows = db.execute('SELECT version FROM schema_info').fetchall()
                if len(rows) != 1 or rows[0][0] != expected_version:
                    return False
                db.execute('UPDATE clock_state SET high_water=high_water WHERE id=1')
                return db.execute('SELECT changes()').fetchone()[0] == 1
            finally:
                if db.in_transaction:
                    db.rollback()
    except sqlite3.OperationalError as error:
        # This process's own writers holding the database and still moving is load, not an outage.
        gate = getattr(database, 'writer_gate', None)
        return 'locked' in str(error) and gate is not None and gate.progressing()
    except (sqlite3.Error, OSError):
        return False
