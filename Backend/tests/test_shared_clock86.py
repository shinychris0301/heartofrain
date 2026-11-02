"""Actual ASGI/SQLite authentication deadlines on a snapshot read.

Synthetic clocks/credentials never leave the fixture; not wall-time performance,
hosted auth, or a change to actor-based gameplay/reward day semantics.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from fastapi.testclient import TestClient

from hotr_backend.api import create_app


class SharedClock86Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-auth-clock86-')
        self.now = 100 * 86400 + 59
        self.app = create_app(Path(self.temp.name) / 'authority.sqlite3', clock=lambda: self.now)
        self.authority = self.app.state.authority
        self.database = self.authority.database
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def credential(self, lifetime=600):
        value = self.authority.provision(lifetime=lifetime)
        return {'Authorization': 'Bearer ' + value['token']}

    def state(self, *, include_clock=True):
        tables = ('players', 'credentials', 'rate_windows', 'wallets', 'wallet_ledger', 'commands')
        if include_clock:
            tables += ('clock_state',)
        with self.database.connect() as db:
            value = {name: sorted(json.dumps(dict(row), sort_keys=True) for row in db.execute('SELECT * FROM ' + name))
                     for name in tables}
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    def test_01_authentication_does_not_wait_for_a_held_writer(self):
        # Review 136: the credential check is a snapshot read, so a busy writer delays nobody.
        headers = self.credential(lifetime=5)
        with self.database.connect() as writer:
            writer.execute('BEGIN IMMEDIATE')
            began = time.monotonic()
            response = self.client.get('/v1/time', headers=headers)
            self.assertLess(time.monotonic() - began, 2)
            writer.rollback()
        self.assertEqual(response.status_code, 200)

    def test_02_expiry_uses_the_time_of_the_request(self):
        headers = self.credential(lifetime=1)
        before = self.state()
        self.now += 1
        response = self.client.get('/v1/time', headers=headers)
        self.assertEqual((response.status_code, response.json()), (401, {'error': 'unauthorized'}))
        self.assertEqual(self.state(), before)  # A refused request writes nothing.

    def test_03_rate_budget_holds_per_minute_without_a_durable_write(self):
        headers = self.credential(lifetime=600)
        for _ in range(self.authority.requests_per_minute):
            self.assertEqual(self.client.get('/v1/time', headers=headers).status_code, 200)
        limited = self.client.get('/v1/time', headers=headers)
        self.assertEqual((limited.status_code, limited.json()), (429, {'error': 'rate_limited'}))
        self.assertEqual(limited.headers['Retry-After'], '30')
        other = self.credential(lifetime=600)
        self.assertEqual(self.client.get('/v1/time', headers=other).status_code, 200)
        self.now += 60
        self.assertEqual(self.client.get('/v1/time', headers=headers).status_code, 200)

    def test_04_invalid_or_unavailable_initial_clock_is_503_and_full_rollback(self):
        headers = self.credential()
        original_clock = self.authority.clock
        def unavailable():
            raise OSError('controlled_clock_unavailable')
        for clock in (lambda: -1, lambda: 253_402_300_800, lambda: float('nan'), lambda: float('inf'), unavailable):
            with self.subTest(clockFailure=True):
                before = self.state()
                self.authority.clock = clock
                try:
                    response = self.client.get('/v1/time', headers=headers)
                finally:
                    self.authority.clock = original_clock
                self.assertEqual((response.status_code, response.json()), (503, {'error': 'clock_unavailable'}))
                self.assertEqual(self.state(), before)

    def test_05_high_water_from_a_write_cannot_be_undone_by_a_backward_wall_clock(self):
        headers = self.credential(lifetime=1)
        with self.database.transaction() as db:
            db.execute('UPDATE clock_state SET high_water=? WHERE id=1', (self.now + 1,))
        response = self.client.get('/v1/time', headers=headers)
        self.assertEqual((response.status_code, response.json()), (401, {'error': 'unauthorized'}))


if __name__ == '__main__':
    unittest.main()
