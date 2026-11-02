"""Review 136: capacity, queueing, retention and player-loss fixes over real ASGI and SQLite.

Worker output is the scripted protocol fixture from test_replay_service, never a Unity verifier.
"""
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.operations import _objects, _validate
from hotr_backend.readiness import database_write_ready
from hotr_backend.replay_contract import ReplayError
from hotr_backend.replay_service import FAILURES_WHEN_OTHERS_SUCCEED
from hotr_backend.runtime136 import Metrics, RequestGuard, Retention, ServiceRuntime
from hotr_backend.storage import Database, WriterGate, remove_performance_objects
from test_replay_service import ReplayServiceTests, ScriptedWorker, ident

CONFIG = Path(__file__).resolve().parents[1] / 'config'


class DispatcherFixture(unittest.TestCase):
    players = 6

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-review136-')
        self.path, self.now = Path(self.temp.name) / 'authority.sqlite3', 100 * 86400
        self.worker = ScriptedWorker()
        self.app = create_app(self.path, CONFIG, lambda: self.now, replay_enabled=True, replay_worker=self.worker, service_runtime=True)
        self.authority, self.broker = self.app.state.authority, self.app.state.replay_broker
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.identities = [self.authority.provision(lifetime=2_592_000) for _ in range(self.players)]

    def tearDown(self):
        self.app.state.service_runtime136.stop()
        for _ in range(100):
            if not self.broker._draining:
                break
            time.sleep(.05)
        self.client.close()
        self.temp.cleanup()

    def headers(self, who):
        return {'Authorization': 'Bearer ' + self.identities[who]['token']}

    def request(self, method, path, body, who):
        value = self.client.request(method, path, json=body, headers=self.headers(who))
        self.assertIn(value.status_code, (200, 202), value.text)  # 202 is the broker's Pending.
        return value.json()

    def start(self, who, level=1):
        wallet = self.request('GET', '/v1/wallet', None, who)
        reserved = self.request('POST', '/v1/attempts/reserve', {'commandId': ident(), 'expectedRevision': wallet['revision'], 'level': level, 'starting': [0, 0, 0, 0]}, who)
        started = self.request('POST', '/v1/attempts/' + reserved['attempt']['attemptId'] + '/start', {'commandId': ident(), 'expectedRevision': reserved['wallet']['revision']}, who)
        return started['attempt']['attemptId']

    def verify(self, who, attempt):
        body = {'commandId': ident(), 'expectedPrefixRevision': 0, 'actions': [{'index': 0, 'kind': 'Swap', 'x': 1, 'y': 1, 'toX': 2, 'toY': 1}]}
        return body, self.request('POST', '/v1/gameplay/attempts/' + attempt + '/verify', body, who)

    def resume(self, who, attempt, command):
        return self.request('POST', '/v1/gameplay/attempts/' + attempt + '/operations/' + command + '/resume', {}, who)

    def wait_for(self, predicate, seconds=10):
        limit = time.monotonic() + seconds
        while time.monotonic() < limit:
            if predicate():
                return True
            time.sleep(.02)
        return False

    def state(self, command):
        with self.authority.database.connect() as db:
            return db.execute('SELECT state FROM replay_operations WHERE command_id=?', (command,)).fetchone()['state']


class ReplayDispatcherTests(DispatcherFixture):
    def test_01_operations_finish_in_arrival_order_without_any_more_polls(self):
        self.worker.outcome = 'Won'
        entered, release = threading.Event(), threading.Event()
        order = []
        def observer(job):
            order.append(job['attemptId'])
            if len(order) == 1:
                entered.set()
                release.wait(10)
        self.worker.observer = observer
        attempts = [self.start(who) for who in range(4)]
        commands, results = {}, {}
        def first():
            commands[0], results[0] = self.verify(0, attempts[0])
        holder = threading.Thread(target=first)
        holder.start()
        self.assertTrue(entered.wait(5))
        for who in (1, 2, 3):
            commands[who], results[who] = self.verify(who, attempts[who])
            self.assertEqual(results[who]['state'], 'Pending')
            self.assertEqual(results[who]['queuePosition'], who + 1)
        release.set()
        holder.join(10)
        self.assertEqual(results[0]['state'], 'Committed')
        for who in (1, 2, 3):
            self.assertTrue(self.wait_for(lambda: self.state(commands[who]['commandId']) == 'Committed'), who)
        self.assertEqual(order, attempts)
        for who in (1, 2, 3):
            done = self.resume(who, attempts[who], commands[who]['commandId'])
            self.assertEqual((done['state'], done['displayReceipt']['awardedCoins']), ('Committed', 50))
            self.assertNotIn('queuePosition', done)
        self.assertEqual(self.broker.queue_depth(), 0)

    def test_02_a_later_poll_cannot_jump_the_line(self):
        self.worker.outcome = 'Won'
        entered, release = threading.Event(), threading.Event()
        order = []
        def observer(job):
            order.append(job['attemptId'])
            if len(order) == 1:
                entered.set()
                release.wait(10)
        self.worker.observer = observer
        attempts = [self.start(who) for who in range(3)]
        holder = threading.Thread(target=self.verify, args=(0, attempts[0]))
        holder.start()
        self.assertTrue(entered.wait(5))
        one, _ = self.verify(1, attempts[1])
        two, _ = self.verify(2, attempts[2])
        for _ in range(3):
            self.assertEqual(self.resume(2, attempts[2], two['commandId'])['state'], 'Pending')
        release.set()
        holder.join(10)
        self.assertTrue(self.wait_for(lambda: self.state(two['commandId']) == 'Committed'))
        self.assertEqual(order[1:], attempts[1:])

    def test_03_a_failing_job_goes_to_the_back_and_stops_after_the_limit_without_charge(self):
        self.worker.outcome = 'Won'
        bad = self.start(0)
        good = [self.start(who) for who in (1, 2)]
        calls = {'bad': 0}
        def observer(job):
            if job['attemptId'] == bad:
                calls['bad'] += 1
                raise ReplayError('fixture_unavailable')
        self.worker.observer = observer
        before = self.request('GET', '/v1/wallet', None, 0)
        body, first = self.verify(0, bad)
        self.assertEqual(first['state'], 'Pending')
        self.assertEqual(self.broker._waiting[next(iter(self.broker._waiting))].failures, 1)
        for who, attempt in zip((1, 2), good):
            self.verify(who, attempt)
        # The job's own failures, while others succeed, are the job's fault. Time is skipped here.
        for _ in range(FAILURES_WHEN_OTHERS_SUCCEED - 1):
            with self.broker._queue_lock:
                for entry in self.broker._waiting.values():
                    entry.not_before = 0
            self.wait_for(lambda: self.state(body['commandId']) == 'Committed' or calls['bad'] >= FAILURES_WHEN_OTHERS_SUCCEED, 3)
            self.resume(0, bad, body['commandId'])
        self.assertTrue(self.wait_for(lambda: self.state(body['commandId']) == 'Committed'))
        final = self.resume(0, bad, body['commandId'])
        self.assertEqual(final['displayReceipt']['outcome'], 'Fault')
        self.assertEqual(final['attempt']['state'], 'Released')
        self.assertEqual(final['wallet']['lives'], before['lives'])
        with self.authority.database.connect() as db:
            audit = json.loads(db.execute('SELECT result_json FROM replay_operations WHERE command_id=?', (body['commandId'],)).fetchone()[0])
        self.assertEqual(audit['trustedFault'], 'worker_retry_limit')

    def test_04_worker_outage_keeps_the_result_pending_and_it_commits_on_return(self):
        self.worker.outcome = 'Won'
        self.worker.fail = True
        attempt = self.start(0)
        body, first = self.verify(0, attempt)
        self.assertEqual(first['state'], 'Pending')
        for _ in range(3):
            with self.broker._queue_lock:
                for entry in self.broker._waiting.values():
                    entry.not_before = 0
            self.assertEqual(self.resume(0, attempt, body['commandId'])['state'], 'Pending')
        self.worker.fail = False
        with self.broker._queue_lock:
            for entry in self.broker._waiting.values():
                entry.not_before = 0
        self.assertTrue(self.wait_for(lambda: self.state(body['commandId']) == 'Committed'))
        self.assertEqual(self.resume(0, attempt, body['commandId'])['displayReceipt']['outcome'], 'Won')

    def test_05_stop_ends_the_dispatcher(self):
        self.broker.stop_dispatcher()
        self.broker._kick()
        self.assertFalse(self.broker._draining)

    def test_06_candidate_job_is_cleared_when_an_operation_ends(self):
        self.worker.outcome = 'Won'
        attempt = self.start(0)
        body, done = self.verify(0, attempt)
        self.assertEqual(done['state'], 'Committed')
        with self.authority.database.connect() as db:
            row = db.execute('SELECT candidate_json,result_json,request_json FROM replay_operations WHERE command_id=?', (body['commandId'],)).fetchone()
        self.assertIsNone(row['candidate_json'])
        self.assertIsNotNone(row['result_json'])
        self.assertIsNotNone(row['request_json'])


class ReplayFlowsWithDispatcherOn(ReplayServiceTests):
    """The whole existing broker suite again, on the path the live launchers select."""
    def open(self):
        self.app = create_app(self.path, CONFIG, lambda: self.now, replay_enabled=True, replay_worker=self.worker, service_runtime=True)
        self.authority, self.broker = self.app.state.authority, self.app.state.replay_broker
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def restart(self):
        self.app.state.service_runtime136.stop()
        super().restart()

    def tearDown(self):
        self.app.state.service_runtime136.stop()
        for _ in range(100):
            if not self.broker._draining:
                break
            time.sleep(.05)
        super().tearDown()


class LifeDueDuringVerification(DispatcherFixture):
    players = 1

    def lose_life(self):
        with self.authority.database.transaction() as db:
            db.execute("UPDATE wallets SET next_life_at=?,balances=json_set(balances,'$[10]',4) WHERE player_id=?", (self.now + 10, self.identities[0]['playerId']))

    def test_01_due_life_during_the_worker_does_not_reject_a_valid_win(self):
        self.lose_life()
        self.worker.outcome = 'Won'
        attempt = self.start(0)
        def advance(job):
            self.now += 20  # Crosses the due time while the worker runs.
        self.worker.observer = advance
        _, done = self.verify(0, attempt)
        self.assertEqual((done['state'], done['displayReceipt']['outcome']), ('Committed', 'Won'))
        self.assertEqual(done['wallet']['lives'], 5)

    def test_02_wallet_read_regenerating_during_the_worker_does_not_reject_a_valid_win(self):
        self.lose_life()
        self.worker.outcome = 'Won'
        attempt = self.start(0)
        def read(job):
            self.now += 20
            # This read regenerates the life and moves the wallet revision.
            self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(0)).json()['lives'], 5)
        self.worker.observer = read
        _, done = self.verify(0, attempt)
        self.assertEqual((done['state'], done['displayReceipt']['outcome']), ('Committed', 'Won'))

    def test_03_another_real_wallet_change_still_conflicts(self):
        self.worker.outcome = 'Won'
        attempt = self.start(0)
        def spend(job):
            with self.authority.database.transaction() as db:
                from hotr_backend.wallet import project
                project(db, self.identities[0]['playerId'], 'fixture/spend', [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], self.now)
        self.worker.observer = spend
        _, done = self.verify(0, attempt)
        self.assertEqual((done['state'], done['code']), ('Rejected', 'gameplay_snapshot_conflict'))


class WriterAndReads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-review136-db-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400
        self.app = create_app(self.path, CONFIG, lambda: self.now, identity_enabled=True, social_enabled=True, notifications_enabled=False)
        self.authority = self.app.state.authority
        self.database = self.authority.database
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def bearer(self):
        return {'Authorization': 'Bearer ' + self.authority.provision(lifetime=86400)['token']}

    def test_01_writers_run_in_arrival_order(self):
        gate = WriterGate()
        gate.acquire(1)
        order, threads = [], []
        def writer(number):
            gate.acquire(5)
            order.append(number)
            gate.release()
        for number in range(8):
            thread = threading.Thread(target=writer, args=(number,))
            thread.start()
            threads.append(thread)
            while gate.waiters != number + 1:
                time.sleep(.002)
        gate.release()
        for thread in threads:
            thread.join(5)
        self.assertEqual(order, list(range(8)))

    def test_02_gate_timeout_is_a_locked_error_and_leaves_the_queue(self):
        gate = WriterGate()
        gate.acquire(1)
        with self.assertRaises(sqlite3.OperationalError):
            gate.acquire(.05)
        self.assertEqual((gate.waiters, gate.lock_timeouts), (0, 1))
        gate.release()
        self.assertEqual(gate.acquire(.05), 0.0)

    def test_03_read_transaction_cannot_write(self):
        with self.assertRaises(sqlite3.OperationalError):
            with self.database.read() as db:
                db.execute('UPDATE clock_state SET high_water=1')

    def test_04_common_reads_answer_while_a_writer_holds_the_database(self):
        headers = self.bearer()
        self.assertEqual(self.client.get('/v1/wallet', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/v1/daily-gift/offer', headers=headers).status_code, 200)  # The day's first ask writes.
        with self.database.connect() as writer:
            writer.execute('BEGIN IMMEDIATE')
            began = time.monotonic()
            for path in ('/v1/wallet', '/v1/time', '/v1/records', '/v1/teams', '/v1/wellworks', '/v1/daily-gift/offer', '/v1/rain-cup'):
                response = self.client.get(path, headers=headers)
                self.assertNotEqual(response.status_code, 503, path)
            self.assertLess(time.monotonic() - began, 5)
            writer.rollback()

    def test_05_ready_while_own_writers_are_busy_but_not_when_stuck(self):
        with self.database.connect() as writer:
            writer.execute('BEGIN IMMEDIATE')
            self.assertFalse(database_write_ready(self.database))  # Nothing of ours is moving.
            self.database.writer_gate.acquire(1)
            try:
                self.assertTrue(database_write_ready(self.database))  # Our own writers are working.
            finally:
                self.database.writer_gate.release()
            writer.rollback()
        self.assertTrue(database_write_ready(self.database))

    def test_06_performance_objects_are_invisible_to_validators_and_removable(self):
        with self.database.connect() as db:
            db.row_factory = None
            self.assertTrue(db.execute("SELECT 1 FROM sqlite_master WHERE name='perf136_team_kicks'").fetchone())
            self.assertFalse([row for row in _objects(db) if row[1].startswith('perf136_')])
            self.assertEqual(_validate(db), 15)
            db.execute('BEGIN IMMEDIATE')
            self.assertGreater(remove_performance_objects(db), 10)
            db.commit()
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE substr(name,1,8)='perf136_'").fetchone())
            self.assertEqual(_validate(db), 15)
        # Opening again recreates them and the backfill runs once more, harmlessly.
        self.assertTrue(Database(self.path))

    def test_07_team_view_finds_kicks_without_scanning_commands(self):
        with self.database.connect() as db:
            plan = ' '.join(row[3] for row in db.execute('''EXPLAIN QUERY PLAN SELECT rowid FROM commands
                WHERE substr(operation,1,17)='social.team.kick/' AND operation=?
                AND json_extract(response_json,'$.playerId')=? AND json_extract(response_json,'$.action')='kick' ''', ('social.team.kick/x', 'y')))
        self.assertIn('perf136_team_kicks', plan)
        self.assertNotIn('SCAN', plan)

    def test_08_wallet_backfill_runs_once_per_database(self):
        with self.database.connect() as db:
            self.assertEqual(db.execute("SELECT value FROM perf136_maintenance WHERE key='wallet_backfill'").fetchone()[0], 1)
        with self.database.transaction() as db:
            db.execute("INSERT INTO players(id,reward_totals,created_at) VALUES(?,?,0)", ('a' * 32, json.dumps([0] * 10)))
        from hotr_backend.wallet import Wallet
        Wallet(self.authority, CONFIG)
        with self.database.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM wallets WHERE player_id=?', ('a' * 32,)).fetchone())
            db.execute("DELETE FROM perf136_maintenance")
        Wallet(self.authority, CONFIG)
        with self.database.connect() as db:
            self.assertIsNotNone(db.execute('SELECT 1 FROM wallets WHERE player_id=?', ('a' * 32,)).fetchone())


class Overload(unittest.TestCase):
    def test_01_excess_requests_get_json_with_retry_after_and_health_still_answers(self):
        sent = []
        async def inner(scope, receive, send):
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'{}'})
        metrics = Metrics()
        guard = RequestGuard(inner, metrics, limit=2)
        metrics.in_flight = 2
        async def capture(message):
            sent.append(message)
        import asyncio
        asyncio.run(guard({'type': 'http', 'path': '/v1/wallet'}, None, capture))
        self.assertEqual(sent[0]['status'], 503)
        self.assertIn((b'retry-after', b'2'), sent[0]['headers'])
        self.assertEqual(json.loads(sent[1]['body']), {'error': 'server_busy'})
        self.assertEqual((metrics.counts['shed'], metrics.counts['status503']), (1, 1))
        sent.clear()
        asyncio.run(guard({'type': 'http', 'path': '/healthz'}, None, capture))
        self.assertEqual(sent[0]['status'], 200)

    def test_02_real_app_counts_refusals_and_storage_errors_carry_retry_after(self):
        with tempfile.TemporaryDirectory(prefix='hotr-review136-over-') as directory:
            app = create_app(Path(directory) / 'authority.sqlite3', CONFIG, lambda: 100 * 86400)
            with TestClient(app, raise_server_exceptions=False) as client:
                token = app.state.authority.provision(lifetime=600)['token']
                app.state.authority.requests_per_minute = 1
                headers = {'Authorization': 'Bearer ' + token}
                self.assertEqual(client.get('/v1/time', headers=headers).status_code, 200)
                limited = client.get('/v1/time', headers=headers)
                self.assertEqual(limited.status_code, 429)
                self.assertEqual(limited.headers['Retry-After'], '30')
                self.assertEqual(app.state.metrics136.counts['status429'], 1)
                with patch.object(app.state.authority.database, 'read', side_effect=sqlite3.OperationalError('database is locked')):
                    with self.assertLogs('hotr_backend.ops', level='WARNING') as logs:
                        busy = client.get('/v1/time', headers=headers)
                self.assertEqual(busy.status_code, 503)
                self.assertEqual(busy.headers['Retry-After'], '2')
                self.assertEqual(busy.json(), {'error': 'storage_unavailable'})
                self.assertEqual(logs.output, ['WARNING:hotr_backend.ops:hotr_storage_error OperationalError'])

    def test_03_counters_log_without_any_request_content(self):
        with tempfile.TemporaryDirectory(prefix='hotr-review136-log-') as directory:
            app = create_app(Path(directory) / 'authority.sqlite3', CONFIG, lambda: 100 * 86400, service_runtime=True)
            runtime = app.state.service_runtime136
            app.state.metrics136.count('status429', 3)
            with self.assertLogs('hotr_backend.ops', level='WARNING') as logs:
                runtime.log()
            self.assertIn('"status429":3', logs.output[0])
            self.assertNotIn(directory, logs.output[0])
            runtime.stop()


class Retention136(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-review136-keep-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 400 * 86400
        self.app = create_app(self.path, CONFIG, lambda: self.now, identity_enabled=True, social_enabled=True, notifications_enabled=False)
        self.authority = self.app.state.authority
        self.database = self.authority.database

    def tearDown(self):
        self.temp.cleanup()

    def test_01_removes_only_what_no_retry_can_reach(self):
        player = self.authority.provision(lifetime=600)['playerId']
        keep_token = self.authority.provision(player, lifetime=600)
        with self.database.transaction() as db:
            db.execute("INSERT INTO identity_devices VALUES('f',?,'k',0,0)", (player,))
            db.execute("INSERT INTO identity_sessions VALUES('fam',?,'f','current',0,?,?,0)", (player, self.now - 86400, self.now + 86400))
            db.execute("INSERT INTO credentials VALUES('old',?,'player',?,0)", (player, self.now - 2 * 86400))
            db.execute("INSERT INTO identity_access VALUES('old','fam',0)")
            db.execute("INSERT INTO credentials VALUES('fresh',?,'player',?,0)", (player, self.now - 3600))
            db.execute("INSERT INTO identity_access VALUES('fresh','fam',0)")
            db.execute("INSERT INTO credentials VALUES('mod',?,'player',?,0)", (player, self.now - 2 * 86400))
            db.execute("INSERT INTO social_moderators VALUES('mod',0)")
            db.execute("INSERT INTO credentials VALUES('verifier',?,'verifier',?,0)", (player, self.now - 2 * 86400))
            db.execute("INSERT INTO identity_refresh VALUES('older','fam',?,'r1','p','used')", (self.now - 30 * 86400,))
            db.execute("INSERT INTO identity_refresh VALUES('used','fam',?,'r2','p','current')", (self.now - 30 * 86400,))
            db.execute("INSERT INTO identity_refresh VALUES('current','fam',?,NULL,NULL,NULL)", (self.now - 30 * 86400,))
            db.execute("INSERT INTO identity_operations VALUES('f','session','r1','p',?,'fam','{}',?)", (player, self.now - 40 * 86400))
            db.execute("INSERT INTO identity_operations VALUES('f','session','recent','p',?,'fam','{}',?)", (player, self.now - 2 * 86400))
            db.execute("INSERT INTO identity_operations VALUES('f','guest','g1','p',?,'fam','{}',0)", (player,))
            db.execute("INSERT INTO rate_windows VALUES('old',1,1)")
        removed = Retention(self.authority, pause=0).run_once()
        self.assertEqual((removed['rateWindows'], removed['accessRows'], removed['credentials'], removed['usedRefreshTokens'], removed['sessionReceipts']), (1, 1, 1, 1, 1))
        with self.database.connect() as db:
            credentials = {row[0] for row in db.execute('SELECT digest FROM credentials')}
            self.assertNotIn('old', credentials)
            self.assertTrue({'fresh', 'mod', 'verifier', self.authority._digest(keep_token['token'])} <= credentials)
            self.assertEqual({row[0] for row in db.execute('SELECT digest FROM identity_refresh')}, {'used', 'current'})
            self.assertEqual({row[0] for row in db.execute('SELECT request_id FROM identity_operations')}, {'recent', 'g1'})
            self.assertEqual(db.execute('SELECT COUNT(*) FROM wallet_ledger WHERE player_id=?', (player,)).fetchone()[0], 1)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_02_batches_stop_when_asked(self):
        stop = threading.Event()
        stop.set()
        self.assertEqual(Retention(self.authority, pause=0).run_once(stop), {})

    def test_03_leftover_worker_folders_are_cleared_by_age_only(self):
        jobs = Path(self.temp.name) / 'replay-jobs'
        (jobs / 'replay-old').mkdir(parents=True)
        (jobs / 'replay-new').mkdir()
        (jobs / 'other').mkdir()
        import os
        os.utime(jobs / 'replay-old', (1, 1))
        Retention(self.authority, jobs_directory=jobs, pause=0).run_once()
        self.assertEqual(sorted(path.name for path in jobs.iterdir()), ['other', 'replay-new'])

    def test_04_runtime_starts_retention_only_when_due(self):
        runtime = ServiceRuntime(self.authority, Metrics())
        runtime.tick()
        self.assertFalse(runtime.running)
        runtime.next_retention = 0
        started = threading.Event()
        with patch.object(runtime.retention, 'run_once', side_effect=lambda stop: started.set() or {}):
            runtime.tick()
            self.assertTrue(started.wait(3))
        runtime.stop()


class PermitChecks(unittest.TestCase):
    def permit(self):
        from hotr_backend import staging_sdk126 as sdk
        permit = sdk._Permit(sdk._SECRET, None, {'state': 'Ready'}, {'kind': 'fixture'})
        return sdk, permit

    def wait_checked(self, permit):
        limit = time.monotonic() + 3
        while permit._checking and time.monotonic() < limit:
            time.sleep(.005)

    def test_01_a_request_does_no_file_work_and_a_transient_failure_refuses_nobody(self):
        sdk, permit = self.permit()
        calls = []
        def failing(path):
            calls.append(path)
            raise OSError('transient')
        with patch.object(permit, 'validate', failing), patch.object(sdk, 'PERMIT_CHECK_SECONDS', 0), patch.object(sdk, 'staging') as staging:
            staging.DATABASE = 'authority.sqlite3'
            permit._manifest = type('M', (), {'data_directory': Path('.')})()
            for _ in range(sdk.PERMIT_FAILURES_TO_CLOSE - 1):
                self.assertTrue(permit.enter())
                permit.leave()
                self.wait_checked(permit)
            self.assertEqual(len(calls), sdk.PERMIT_FAILURES_TO_CLOSE - 1)
            self.assertTrue(permit.enter())
            permit.leave()

    def test_02_repeated_failures_close_it_and_a_good_check_reopens_it(self):
        sdk, permit = self.permit()
        def failing(path):
            raise OSError('changed')
        with patch.object(sdk, 'PERMIT_CHECK_SECONDS', 0), patch.object(sdk, 'staging') as staging:
            staging.DATABASE = 'authority.sqlite3'
            permit._manifest = type('M', (), {'data_directory': Path('.')})()
            with patch.object(permit, 'validate', failing):
                for _ in range(sdk.PERMIT_FAILURES_TO_CLOSE):
                    if permit.enter():
                        permit.leave()
                    self.wait_checked(permit)
                self.assertFalse(permit.enter())
                self.wait_checked(permit)
            with patch.object(permit, 'validate', lambda path: None):
                self.assertFalse(permit.enter())
                self.wait_checked(permit)
                self.assertTrue(permit.enter())
                permit.leave()

    def test_03_close_is_immediate_and_final(self):
        _, permit = self.permit()
        self.assertTrue(permit.enter())
        permit.leave()
        permit.close()
        self.assertFalse(permit.enter())


class LauncherStartup(unittest.TestCase):
    def test_01_real_launcher_skips_whole_file_checks_selects_runtime_and_does_not_listen_yet(self):
        from test_staging_sdk126 import Fixture
        from hotr_backend import sdk_schema125, staging_sdk126 as sdk
        import socket
        fixture = Fixture()
        self.addCleanup(fixture.close)
        fixture.prepare()
        seen = []
        original = sdk_schema125.validate_sdk_database
        def spy(db, *, full=True):
            seen.append(full)
            return original(db, full=full)
        with patch.object(sdk, 'validate_sdk_database', spy):
            with sdk.application_context(fixture.m) as app:
                self.assertEqual(set(seen), {False})
                self.assertIsNotNone(app.state.service_runtime136)
                port = app.state.sdk_staging_socket126.getsockname()[1]
                probe = socket.socket()
                probe.settimeout(.5)
                try:
                    with self.assertRaises(OSError):  # Refused at once, not left waiting in a backlog.
                        probe.connect(('127.0.0.1', port))
                finally:
                    probe.close()

    def test_02_the_launchers_no_longer_cap_connections(self):
        root = Path(__file__).resolve().parents[1] / 'hotr_backend'
        for name in ('staging_sdk126.py', 'staging105.py', 'production_runtime122.py'):
            self.assertIn('limit_concurrency=None', (root / name).read_text('utf-8'))
            self.assertNotIn('limit_concurrency=32', (root / name).read_text('utf-8'))


class ChatAndTeams(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-review136-chat-')
        self.now = 100 * 86400
        self.app = create_app(Path(self.temp.name) / 'authority.sqlite3', CONFIG, lambda: self.now, social_enabled=True)
        self.authority = self.app.state.authority
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.owner, self.joiner = (self.authority.provision(lifetime=86400) for _ in range(2))

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def call(self, who, method, path, body=None, status=200):
        response = self.client.request(method, path, json=body, headers={'Authorization': 'Bearer ' + who['token']})
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def team(self):
        return self.call(self.owner, 'POST', '/v1/teams', {'commandId': ident(), 'name': 'Rainkeepers', 'description': ''})['teamId']

    def send(self, team, text, status=200):
        return self.call(self.owner, 'POST', '/v1/messages/Team/' + team, {'commandId': ident(), 'text': text}, status)

    def test_01_new_member_starts_with_nothing_unread_and_can_read_history(self):
        team = self.team()
        self.send(team, 'one')
        self.send(team, 'two')
        self.call(self.joiner, 'POST', '/v1/teams/' + team + '/join', {'commandId': ident()})
        page = self.call(self.joiner, 'GET', '/v1/messages/Team/' + team)
        self.assertEqual((page['unreadCount'], len(page['messages'])), (0, 2))
        self.send(team, 'three')
        self.assertEqual(self.call(self.joiner, 'GET', '/v1/messages/Team/' + team)['unreadCount'], 1)

    def test_02_zwj_emoji_and_crlf_are_accepted_but_bare_controls_are_not(self):
        team = self.team()
        self.send(team, 'shrug \U0001F937‍♂️')
        self.send(team, 'line one\r\nline two')
        texts = [row['text'] for row in self.call(self.owner, 'GET', '/v1/messages/Team/' + team)['messages']]
        self.assertEqual(texts[1], 'line one\nline two')
        self.send(team, '‍', status=422)
        self.send(team, 'bad\rreturn', status=422)
        self.send(team, 'bad\x00null', status=422)
        self.call(self.owner, 'POST', '/v1/teams', {'commandId': ident(), 'name': 'Zero‍Name', 'description': ''}, 422)


class Ranks(unittest.TestCase):
    def test_01_shared_ranks_match_the_old_per_row_count_and_use_one_grouped_query(self):
        with tempfile.TemporaryDirectory(prefix='hotr-review136-rank-') as directory:
            app = create_app(Path(directory) / 'authority.sqlite3', CONFIG, lambda: 100 * 86400, social_enabled=True)
            authority = app.state.authority
            identities = [authority.provision(lifetime=86400) for _ in range(6)]
            scores = [7, 5, 5, 3, 3, 0]
            with authority.database.transaction() as db:
                for identity, score in zip(identities, scores):
                    db.execute('UPDATE players SET completed=? WHERE id=?', (score, identity['playerId']))
                    db.execute('INSERT INTO social_profiles(player_id,display_name,leaderboard_opt_in,created_at,updated_at) VALUES(?,?,1,0,0)', (identity['playerId'], 'P' + identity['playerId'][:6]))
            with TestClient(app, raise_server_exceptions=False) as client:
                value = client.get('/v1/leaderboards/global?limit=2&offset=1', headers={'Authorization': 'Bearer ' + identities[5]['token']}).json()
            self.assertEqual([row['rank'] for row in value['entries']], [2, 2])
            self.assertEqual(value['nextOffset'], 3)


if __name__ == '__main__':
    unittest.main()
