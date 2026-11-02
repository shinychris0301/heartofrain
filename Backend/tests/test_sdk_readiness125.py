"""SDK125 readiness stays a bounded writer probe with exact selected version."""
from contextlib import closing
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from hotr_backend.readiness import database_write_ready
from hotr_backend.storage import Database
from sdk_fixture125 import SdkProductionFixture125

class SdkReadiness125Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = SdkProductionFixture125()
        self.addCleanup(self.fixture.close)
        self.context = self.fixture.context()
        self.app = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)
        self.client = self.fixture.client(self.app)
        self.addCleanup(self.client.close)

    def test_01_actual_sdk_readyz_is200_and_rolls_back_clock_probe(self):
        db = self.app.state.authority.database
        with db.connect() as connection:
            before = connection.execute('SELECT high_water FROM clock_state').fetchone()[0]
        self.assertEqual(self.client.get('/readyz').status_code, 200)
        with db.connect() as connection:
            self.assertEqual(connection.execute('SELECT high_water FROM clock_state').fetchone()[0], before)

    def test_02_writer_lock_returns503_bounded_and_recovers_after_rollback(self):
        with closing(sqlite3.connect(self.app.state.authority.database.path, isolation_level=None)) as writer:
            writer.execute('BEGIN IMMEDIATE')
            before = time.monotonic()
            self.assertEqual(self.client.get('/readyz').status_code, 503)
            self.assertLess(time.monotonic() - before, 2)
            writer.rollback()
        self.assertEqual(self.client.get('/readyz').status_code, 200)

    def test_03_sdk_rejects15_without_migration_and_accepts_only_selected125(self):
        database = self.app.state.authority.database
        with database.transaction() as db:
            db.execute('UPDATE schema_info SET version=15')
        self.assertEqual(self.client.get('/readyz').status_code, 503)
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 15)
        with database.transaction() as db:
            db.execute('UPDATE schema_info SET version=125')
        database.sdk_commerce125 = False
        self.assertFalse(database_write_ready(database))
        database.sdk_commerce125 = True
        self.assertTrue(database_write_ready(database))

    def test_04_missing_clock_is_unavailable_without_recreating_state(self):
        database = self.app.state.authority.database
        with database.transaction() as db:
            db.execute('DELETE FROM clock_state')
        self.assertEqual(self.client.get('/readyz').status_code, 503)
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM clock_state').fetchone()[0], 0)

    def test_05_corrupt_storage_is_unavailable(self):
        with tempfile.TemporaryDirectory(prefix='hotr-sdk125-readiness-corrupt-') as directory:
            path = Path(directory) / 'broken.sqlite3'
            database = Database(path, _sdk_commerce125=True)
            path.write_bytes(b'explicitly-corrupted-test-sqlite-header')
            self.assertFalse(database_write_ready(database))

    def test_06_probe_update_is_really_rolled_back_even_with_side_effect_trigger(self):
        database = self.app.state.authority.database
        with database.transaction() as db:
            db.execute('CREATE TABLE readiness_probe_test125(value INTEGER)')
            db.execute('CREATE TRIGGER readiness_probe_effect125 AFTER UPDATE ON clock_state '
                       'BEGIN INSERT INTO readiness_probe_test125 VALUES(1); END')
        self.assertEqual(self.client.get('/readyz').status_code, 200)
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM readiness_probe_test125').fetchone()[0], 0)

if __name__ == '__main__':
    unittest.main()

