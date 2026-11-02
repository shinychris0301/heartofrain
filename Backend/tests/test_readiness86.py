"""Real SQLite readiness, including read-only and concurrent-writer failure."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.storage import SCHEMA_VERSION


class Readiness86Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-ready86-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.app = create_app(self.path)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.database = self.app.state.authority.database

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_01_healthy_probe_does_not_create_or_change_game_state(self):
        def snapshot():
            with self.database.connect() as db:
                return {name: [tuple(row) for row in db.execute('SELECT * FROM ' + name)]
                        for name in ('clock_state', 'players', 'wallets', 'wallet_ledger', 'commands', 'offers')}
        before = snapshot()
        for _ in range(3):
            response = self.client.get('/readyz')
            self.assertEqual((response.status_code, response.json()), (200, {'status': 'ready'}))
        self.assertEqual(snapshot(), before)

    def test_02_actual_read_only_connection_is_not_write_ready(self):
        @contextmanager
        def readonly(timeout=10):
            db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, isolation_level=None)
            db.row_factory = sqlite3.Row
            try:
                yield db
            finally:
                db.close()
        with patch.object(self.database, 'connect', readonly):
            response = self.client.get('/readyz')
        self.assertEqual((response.status_code, response.json()), (503, {'status': 'unavailable'}))

    def test_03_held_real_writer_returns_bounded_unavailable_then_recovers(self):
        with self.database.connect() as writer:
            writer.execute('BEGIN IMMEDIATE')
            began = time.monotonic()
            response = self.client.get('/readyz')
            self.assertLess(time.monotonic() - began, 2)
            self.assertEqual((response.status_code, response.json()), (503, {'status': 'unavailable'}))
            writer.rollback()
        self.assertEqual(self.client.get('/readyz').status_code, 200)

    def test_04_schema_mismatch_is_not_ready_and_probe_does_not_migrate(self):
        with self.database.transaction() as db:
            db.execute('UPDATE schema_info SET version=?', (SCHEMA_VERSION + 1,))
        response = self.client.get('/readyz')
        self.assertEqual((response.status_code, response.json()), (503, {'status': 'unavailable'}))
        with self.database.connect() as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], SCHEMA_VERSION + 1)

    def test_05_missing_clock_row_is_unavailable_and_never_recreated(self):
        with self.database.transaction() as db:
            db.execute('DELETE FROM clock_state')
        response = self.client.get('/readyz')
        self.assertEqual((response.status_code, response.json()), (503, {'status': 'unavailable'}))
        with self.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM clock_state').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
