"""Actual authenticated ASGI/SQLite orchestration with a scripted worker seam.

These tests prove permissions, receipts, leases and atomic accounting, not board
rules. The separate pinned Unity/Windows corpus must prove the actual model.
"""
import concurrent.futures
import json
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.replay_contract import ApprovedWorker, ReplayError, TrustedModelFault, encode_job, sha256
from hotr_backend.replay_schemas import VerifyReplay
from hotr_backend.service import ServiceError
from hotr_backend.wallet_schemas import SettleAttempt
from hotr_backend.wallet import project

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident(): return uuid.uuid4().hex


class ScriptedWorker(ApprovedWorker):
    """Explicit test-only protocol output. Never called a Unity verifier."""
    def __init__(self):
        self.enabled, self.timeout, self.calls, self.fail, self.observer = True, 60, [], False, None
        self.outcome, self.forge, self.fault = None, False, False
        levels = json.loads((CONFIG / 'levels.json').read_text('utf-8-sig'))['levels']
        self.pins = {'levels': [{'level': row['level'], 'sha256': row['sourceSHA256'], 'moves': row['moves']} for row in levels]}
        self.digest = sha256(b'explicit-scripted-orchestration-fixture-not-a-worker-build')

    def _verify_bundle(self): return {}, self.pins, self.digest

    def run(self, job):
        self.calls.append(job)
        if self.observer: self.observer(job)
        if self.fail: raise ReplayError('fixture_unavailable')
        if self.fault: raise TrustedModelFault({'outputSHA256': sha256(b'explicit-scripted-fault-not-real-model-guard'),
            'jobSHA256': sha256(encode_job(job)), 'scope': 'scripted_financial_orchestration_only'})
        moves, turn, rows = job['initialMoves'], 0, []
        for action in job['actions']:
            if action['kind'] in ('Swap', 'Tap'): moves -= 1; turn += 1
            elif action['kind'] == 'Continue': moves = 5
            rows.append({'index': action['index'], 'kind': action['kind'], 'moves': moves, 'turn': turn,
                'status': 'Out of moves' if moves == 0 else 'Playing', 'checkpointSHA256': sha256(str(action['index']).encode())})
        outcome = self.outcome or ('Out of moves' if moves == 0 else 'Playing')
        final = rows[-1]['checkpointSHA256'] if rows else sha256(b'fixture-opening')
        if rows: rows[-1]['status'] = outcome
        result = {'version': 1, 'status': 'PASS_PINNED_MODEL_REPLAY', 'code': '', 'unity': '2022.3.62f3',
            'jobSHA256': 'f' * 64 if self.forge else sha256(encode_job(job)), 'pinsSHA256': job['pinsSHA256'],
            'levelSHA256': job['levelSHA256'], 'checkpointSHA256': final, 'outcome': outcome,
            'level': job['level'], 'actions': len(rows), 'moves': moves, 'turn': turn,
            'remainingGoals': 0 if outcome == 'Won' else 20, 'productionEnabled': False,
            'financialMutation': False, 'actionResults': rows}
        return {'result': result}


class ReplayServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-replay-service-')
        self.path, self.now = Path(self.temp.name) / 'authority.sqlite3', 100 * 86400
        self.worker = ScriptedWorker(); self.open()
        self.identities = [self.authority.provision(lifetime=2_592_000) for _ in range(2)]
        self.players = [row['playerId'] for row in self.identities]
        self.attempt = self.start()

    def open(self):
        self.app = create_app(self.path, CONFIG, lambda: self.now, replay_enabled=True, replay_worker=self.worker)
        self.authority, self.broker = self.app.state.authority, self.app.state.replay_broker
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def restart(self): self.client.close(); self.open()
    def tearDown(self): self.client.close(); self.temp.cleanup()
    def headers(self, who=0): return {'Authorization': 'Bearer ' + self.identities[who]['token']}
    def request(self, method, path, body=None, who=0, status=200):
        value = self.client.request(method, path, json=body, headers=self.headers(who))
        self.assertEqual(value.status_code, status, value.text)
        return value.json()
    def wallet(self, who=0): return self.request('GET', '/v1/wallet', who=who)
    def start(self, who=0, level=1):
        wallet = self.wallet(who)
        reserved = self.request('POST', '/v1/attempts/reserve', {'commandId': ident(), 'expectedRevision': wallet['revision'], 'level': level, 'starting': [0, 0, 0, 0]}, who)
        started = self.request('POST', '/v1/attempts/' + reserved['attempt']['attemptId'] + '/start', {'commandId': ident(), 'expectedRevision': reserved['wallet']['revision']}, who)
        return started['attempt']['attemptId']
    @staticmethod
    def moves(count=1, first=0): return [{'index': first + index, 'kind': 'Swap', 'x': 1, 'y': 1, 'toX': 1, 'toY': 2} for index in range(count)]
    def body(self, revision=0, actions=None, **extra): return {'commandId': ident(), 'expectedPrefixRevision': revision, 'actions': self.moves() if actions is None else actions, **extra}
    def submit(self, kind='verify', body=None, status=200, who=0, attempt=None):
        return self.request('POST', '/v1/gameplay/attempts/' + (attempt or self.attempt) + '/' + kind, self.body() if body is None else body, who, status)
    def count(self, table):
        with self.authority.database.connect() as db: return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
    def operation(self, command, suffix='', body=None, status=200, who=0):
        return self.request('POST' if suffix else 'GET', '/v1/gameplay/attempts/' + self.attempt + '/operations/' + command + suffix, body, who, status)

    def test_01_default_disabled_and_no_client_win_seed_checkpoint_receipt_or_budget_override(self):
        disabled = create_app(Path(self.temp.name) / 'disabled.sqlite3', CONFIG, lambda: self.now)
        token = disabled.state.authority.provision()
        with TestClient(disabled) as client:
            self.assertEqual(client.post('/v1/gameplay/attempts/' + ident() + '/verify', json=self.body(), headers={'Authorization': 'Bearer ' + token['token']}).status_code, 503)
        for key in ('Won', 'seed', 'checkpoint', 'receipts', 'initialMoves', 'pinsSHA256'):
            self.submit(body=self.body(**{key: 1}), status=422)
        self.assertEqual((len(self.worker.calls), self.count('replay_operations')), (0, 0))

    def test_02_server_owned_job_and_immutable_prefix_idempotence_and_rewind_denial(self):
        body = self.body(); first = self.submit(body=body)
        self.assertEqual((first['state'], first['prefixRevision'], first['acceptedActions']), ('Committed', 1, 1))
        job = self.worker.calls[0]
        with self.authority.database.connect() as db:
            attempt = db.execute('SELECT * FROM gameplay_attempts WHERE id=?', (self.attempt,)).fetchone()
        self.assertEqual((job['attemptId'], job['playerId'], job['seed'], job['levelSHA256']), (self.attempt, self.players[0], attempt['seed'], attempt['config_hash']))
        self.assertEqual(self.submit(body=body), first); self.assertEqual(len(self.worker.calls), 1)
        changed = dict(body, actions=self.moves(2)); self.submit(body=changed, status=409)
        self.submit(body=self.body(), status=409)
        second = self.submit(body=self.body(1, self.moves(first=1)))
        self.assertEqual(second['acceptedActions'], 2)
        self.assertEqual(self.worker.calls[-1]['actions'][0], job['actions'][0])

    def test_03_player_ownership_cached_guards_revocation_and_deleted_account(self):
        body = self.body(); self.submit(body=body)
        self.submit(body=body, who=1, status=404); self.operation(body['commandId'], who=1, status=404)
        stale = self.authority.authenticate(self.identities[0]['token']); self.authority.revoke(self.identities[0]['token'])
        self.submit(body=body, status=401)
        with self.assertRaises(ServiceError): self.broker.get(stale, self.attempt, body['commandId'])
        replacement = self.authority.provision(self.players[0]); self.identities[0] = replacement
        with self.authority.database.transaction() as db: db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.players[0], self.now))
        self.submit(body=body, status=410)

    def test_04_tool_verified_before_debit_and_atomic_actual_receipt_target_binding(self):
        before = self.wallet(); observed = []
        def outside(job):
            with self.authority.database.transaction(timeout=1) as db:
                stock = json.loads(db.execute('SELECT balances FROM wallets WHERE player_id=?', (self.players[0],)).fetchone()[0])
                observed.append(stock[6])  # A writer obtains lock while worker runs.
        self.worker.observer = outside
        body = self.body(expectedWalletRevision=before['revision'], tool=0, x=2, y=3)
        first = self.submit('tool', body)
        self.assertEqual(observed, [before['tools'][0]])
        self.assertEqual((first['wallet']['tools'][0], first['acceptedActions']), (before['tools'][0] - 1, 2))
        self.assertEqual(self.submit('tool', body), first)
        with self.authority.database.connect() as db:
            binding = db.execute('SELECT * FROM replay_paid_bindings').fetchone()
            ledger = db.execute('SELECT * FROM wallet_ledger WHERE id=?', (binding['receipt_id'],)).fetchone()
            self.assertEqual((binding['tool'], binding['x'], binding['y'], binding['action_index']), (0, 2, 3, 1))
            self.assertEqual(json.loads(ledger['delta_json'])[6], -1)
            self.assertEqual(self.worker.calls[0]['receipts'][0]['receiptId'], ledger['id'])
        self.assertEqual(self.count('replay_paid_bindings'), 1)

    def test_05_infrastructure_failure_or_forged_output_never_spends_and_can_resume(self):
        before = self.wallet(); self.worker.fail = True
        body = self.body(expectedWalletRevision=before['revision'], tool=1, x=1, y=1)
        pending = self.submit('tool', body, status=202)
        self.assertEqual((pending['state'], self.wallet()['tools'], self.count('replay_paid_bindings')), ('Pending', before['tools'], 0))
        self.worker.fail = False; self.worker.forge = True
        self.operation(body['commandId'], '/resume', {}, status=202)
        self.assertEqual(self.wallet()['tools'], before['tools'])
        self.worker.forge = False
        final = self.operation(body['commandId'], '/resume', {})
        self.assertEqual(final['wallet']['tools'][1], before['tools'][1] - 1)

    def test_06_worker_callback_race_wallet_revision_and_seed_mutation_reject_without_debit(self):
        before = self.wallet()
        def mutation(job):
            with self.authority.database.transaction() as db: db.execute('UPDATE gameplay_attempts SET seed=seed+1 WHERE id=?', (self.attempt,))
        self.worker.observer = mutation
        result = self.submit('tool', self.body(expectedWalletRevision=before['revision'], tool=0, x=1, y=1))
        self.assertEqual((result['state'], result['code']), ('Rejected', 'attempt_configuration_mismatch'))
        self.assertEqual(self.wallet()['tools'], before['tools'])

    def test_07_full_history_limit_and_invalid_index_reject_before_paid_debit(self):
        before = self.wallet()
        bad = self.body(actions=self.moves(first=1), expectedWalletRevision=before['revision'], tool=0, x=1, y=1)
        self.assertEqual(self.submit('tool', bad)['state'], 'Rejected')
        self.assertEqual((len(self.worker.calls), self.wallet()['tools']), (0, before['tools']))
        self.submit(body=self.body(actions=self.moves(129)), status=422)
        # A durable accepted-prefix capacity control independent of board rules.
        self.submit(body=self.body(actions=[]))
        with self.authority.database.transaction() as db:
            db.execute('UPDATE replay_attempts SET prefix_json=? WHERE attempt_id=?', (json.dumps([{'index': i} for i in range(1000)]), self.attempt))
        result = self.submit('tool', self.body(1, [], expectedWalletRevision=self.wallet()['revision'], tool=0, x=1, y=1))
        self.assertEqual((result['state'], result['code']), ('Rejected', 'gameplay_history_capacity'))
        self.assertEqual(self.wallet()['tools'], before['tools'])

    def test_08_model_verified_out_of_moves_then_actual900_plus5_and_repeated_continue(self):
        before = self.wallet(); budget = self.app.state.wallet.catalog.levels[0].moves
        no_moves = self.submit(body=self.body(actions=self.moves(budget)))
        self.assertEqual((no_moves['model']['outcome'], no_moves['attempt']['state'], no_moves['wallet']['lives']), ('Out of moves', 'AwaitingContinuation', before['lives']))
        self.assertEqual(no_moves['displayReceipt']['awardedCoins'], 0)
        body = self.body(1, [], expectedWalletRevision=no_moves['wallet']['revision'])
        continued = self.submit('continue', body)
        self.assertEqual((continued['addedMoves'], continued['model']['moves'], continued['attempt']['moves']), (5, 5, budget + 5))
        self.assertEqual(continued['wallet']['coins'], before['coins'] - 900)
        self.assertEqual(self.submit('continue', body), continued)
        again = self.submit(body=self.body(2, self.moves(5, budget + 1)))
        denied = self.submit('continue', self.body(3, [], expectedWalletRevision=again['wallet']['revision']))
        self.assertEqual((denied['state'], denied['code']), ('Rejected', 'insufficient_coins'))
        self.assertEqual(self.wallet()['coins'], before['coins'] - 900)

    def test_09_continue_without_verified_exhaustion_and_raw_financial_verifier_bypass_are_denied(self):
        before = self.wallet()
        rejected = self.submit('continue', self.body(actions=[], expectedWalletRevision=before['revision']))
        self.assertEqual(rejected['state'], 'Rejected')
        for path, extra in (('continue', {}), ('tools', {'tool': 0})):
            self.request('POST', '/v1/attempts/' + self.attempt + '/' + path, {'commandId': ident(), 'expectedRevision': before['revision'], **extra}, status=409)
        verifier = self.authority.provision(role='verifier')
        with self.assertRaises(ServiceError):
            self.app.state.wallet.settle(self.authority.authenticate(verifier['token'], 'verifier'), SettleAttempt(commandId=ident(), expectedRevision=before['revision'], playerId=self.players[0], attemptId=self.attempt, outcome='Won', proofDigest='a' * 64))
        self.assertEqual((self.wallet()['coins'], self.wallet()['tools']), (before['coins'], before['tools']))

    def test_10_actual_reward_receipt_first_clear_and_replay_award_zero(self):
        self.worker.outcome = 'Won'; before = self.wallet(); body = self.body()
        first = self.submit(body=body)
        display = first['displayReceipt']
        self.assertEqual((display['awardedCoins'], display['awardedStars'], display['firstClear'], display['completedBefore'], display['completedAfter']), (50, 1, True, 0, 1))
        self.assertEqual((first['wallet']['coins'], first['wallet']['lives']), (before['coins'] + 50, before['lives']))
        self.assertEqual(self.submit(body=body), first)
        self.attempt = self.start(level=1)
        replay = self.submit(body=self.body())
        self.assertEqual((replay['displayReceipt']['awardedCoins'], replay['displayReceipt']['awardedStars'], replay['displayReceipt']['firstClear']), (0, 0, False))
        self.assertEqual(self.wallet()['coins'], before['coins'] + 50)

    def test_11_no_legal_moves_waits_for_explicit_acknowledgement_before_one_life_loss(self):
        self.worker.outcome = 'No legal moves'; before = self.wallet()
        result = self.submit()
        self.assertTrue(result['acknowledgementRequired']); self.assertIsNone(result['displayReceipt'])
        self.assertEqual((result['attempt']['state'], self.wallet()['lives']), ('Started', before['lives']))
        body = {'commandId': ident(), 'expectedRevision': self.wallet()['revision']}
        lost = self.submit('abandon', body)
        self.assertEqual((lost['displayReceipt']['outcome'], lost['wallet']['lives']), ('Lost', before['lives'] - 1))
        self.assertEqual(self.submit('abandon', body), lost)

    def test_12_pending_abandon_fences_late_win_and_quits_once_without_releasing_global_slot_early(self):
        entered, release = threading.Event(), threading.Event()
        self.worker.outcome = 'Won'
        self.worker.observer = lambda job: (entered.set(), release.wait(10))
        body = self.body(); before = self.wallet()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.submit, 'verify', body)
            self.assertTrue(entered.wait(5))
            abandon = {'commandId': ident(), 'expectedRevision': before['revision']}
            lost = self.submit('abandon', abandon)
            with self.authority.database.connect() as db:
                self.assertIsNotNone(db.execute('SELECT operation_id FROM replay_worker_slot').fetchone()[0])
            release.set(); late = future.result(10)
        self.assertEqual(late['state'], 'Rejected')
        self.assertEqual((self.wallet()['lives'], self.wallet()['coins']), (before['lives'] - 1, before['coins']))
        self.assertEqual(self.count('verified_clears'), 0)
        self.assertEqual(self.submit('abandon', abandon), lost)

    def test_13_completed_win_cannot_be_abandoned_or_spend_a_life(self):
        self.worker.outcome = 'Won'; won = self.submit()
        self.submit('abandon', {'commandId': ident(), 'expectedRevision': won['wallet']['revision']}, status=409)
        self.assertEqual(self.wallet()['lives'], 5)

    def test_14_global_slot_and_same_operation_lease_prevent_duplicate_concurrent_work(self):
        entered, release = threading.Event(), threading.Event()
        self.worker.observer = lambda job: (entered.set(), release.wait(10))
        first_body = self.body(); second_attempt = self.start(who=1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(self.submit, 'verify', first_body)
            self.assertTrue(entered.wait(5))
            self.submit(body=first_body, status=202)
            other = self.submit(body=self.body(), who=1, attempt=second_attempt, status=202)
            self.assertEqual(other['state'], 'Pending'); self.assertEqual(len(self.worker.calls), 1)
            release.set(); self.assertEqual(first.result(10)['state'], 'Committed')
        self.assertEqual(self.count('replay_operations'), 2)

    def test_15_process_restart_resume_and_aftercommit_retry_never_double_debits(self):
        before = self.wallet(); self.worker.fail = True
        body = self.body(expectedWalletRevision=before['revision'], tool=0, x=1, y=1)
        self.submit('tool', body, status=202); self.restart(); self.worker.fail = False
        def fault(stage):
            if stage == 'AfterCommit': raise OSError('synthetic lost reply')
        self.broker.checkpoint = fault
        first = self.operation(body['commandId'], '/resume', {})
        self.broker.checkpoint = None; self.restart()
        self.assertEqual(self.operation(body['commandId']), first)
        self.assertEqual((self.wallet()['tools'][0], self.count('replay_paid_bindings')), (before['tools'][0] - 1, 1))

    def test_16_atomic_commit_failure_rolls_back_tool_ledger_binding_and_prefix(self):
        before = self.wallet()
        self.broker.checkpoint = lambda stage: (_ for _ in ()).throw(OSError('synthetic precommit')) if stage == 'BeforeCommit' else None
        body = self.body(expectedWalletRevision=before['revision'], tool=3, x=-1, y=-1)
        self.submit('tool', body, status=202)
        self.assertEqual((self.wallet()['tools'], self.count('replay_paid_bindings')), (before['tools'], 0))
        with self.authority.database.connect() as db:
            self.assertEqual(tuple(db.execute('SELECT revision,prefix_json FROM replay_attempts').fetchone()), (0, '[]'))
        self.broker.checkpoint = None
        self.operation(body['commandId'], '/resume', {})
        self.assertEqual(self.wallet()['tools'][3], before['tools'][3] - 1)

    def test_17_revocation_or_deletion_during_worker_never_commits_win_or_debit(self):
        before = self.wallet(); self.worker.outcome = 'Won'
        def delete(job):
            with self.authority.database.transaction() as db:
                db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.players[0], self.now))
                db.execute('UPDATE credentials SET revoked=1 WHERE player_id=?', (self.players[0],))
        self.worker.observer = delete
        self.submit('tool', self.body(expectedWalletRevision=before['revision'], tool=0, x=1, y=1), status=410)
        with self.authority.database.connect() as db:
            wallet = json.loads(db.execute('SELECT balances FROM wallets WHERE player_id=?', (self.players[0],)).fetchone()[0])
            self.assertEqual((wallet[0], wallet[6]), (before['coins'], before['tools'][0]))
        self.assertEqual((self.count('rewards'), self.count('replay_paid_bindings')), (0, 0))

    def test_18_concurrent_legitimate_wallet_projection_fences_stale_paid_and_win_result(self):
        before = self.wallet(); self.worker.outcome = 'Won'
        def projection(job):
            with self.authority.database.transaction() as db:
                project(db, self.players[0], 'explicit-test-concurrent-credit', [1] + [0] * 10, self.now)
        self.worker.observer = projection
        value = self.submit('tool', self.body(expectedWalletRevision=before['revision'], tool=0, x=1, y=1))
        self.assertEqual((value['state'], value['code']), ('Rejected', 'gameplay_snapshot_conflict'))
        after = self.wallet()
        self.assertEqual((after['coins'], after['tools'], after['completed']), (before['coins'] + 1, before['tools'], 0))
        self.assertEqual((self.count('rewards'), self.count('replay_paid_bindings')), (0, 0))

    def test_19_paid_ledger_corruption_is_not_accepted_as_reusable_receipt_authority(self):
        before = self.wallet()
        paid = self.submit('tool', self.body(expectedWalletRevision=before['revision'], tool=2, x=1, y=1))
        with self.authority.database.transaction() as db:
            db.execute('UPDATE wallet_ledger SET delta_json=? WHERE id=?', (json.dumps([0] * 11), paid['paidReceiptId']))
        self.submit(body=self.body(1, self.moves(first=2)), status=409)
        self.assertEqual((len(self.worker.calls), self.count('replay_paid_bindings')), (1, 1))

    def test_20_actual_start_receipt_required_not_an_opaque_client_string(self):
        with self.authority.database.transaction() as db:
            command = db.execute("SELECT command_id,response_json FROM commands WHERE player_id=? AND operation='wallet.start'", (self.players[0],)).fetchone()
            value = json.loads(command['response_json']); value['receiptId'] = 'wallet/' + 'd' * 64
            db.execute('UPDATE commands SET response_json=? WHERE player_id=? AND command_id=?', (json.dumps(value), self.players[0], command['command_id']))
        self.submit(status=409)
        self.assertEqual((len(self.worker.calls), self.count('replay_attempts')), (0, 0))

    def test_21_expired_lease_replacement_fences_late_result_and_spends_once(self):
        entered, release = threading.Event(), threading.Event()
        def hold_first(job):
            if len(self.worker.calls) == 1: entered.set(); release.wait(10)
        self.worker.observer = hold_first
        before = self.wallet(); body = self.body(expectedWalletRevision=before['revision'], tool=0, x=1, y=1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            original = pool.submit(self.submit, 'tool', body)
            self.assertTrue(entered.wait(5)); self.now += 121
            replacement = self.operation(body['commandId'], '/resume', {})
            self.assertEqual(replacement['state'], 'Committed')
            release.set(); self.assertEqual(original.result(10), replacement)
        self.assertEqual((self.wallet()['tools'][0], self.count('replay_paid_bindings')), (before['tools'][0] - 1, 1))

    def test_22_stale_abandon_revision_rolls_back_cancellation_before_retry_and_loss_once(self):
        self.worker.fail = True; command = self.body(); before = self.wallet()
        self.submit(body=command, status=202)
        self.submit('abandon', {'commandId': ident(), 'expectedRevision': before['revision'] - 1}, status=409)
        self.assertEqual(self.operation(command['commandId'], status=202)['state'], 'Pending')
        body = {'commandId': ident(), 'expectedRevision': before['revision']}
        result = self.submit('abandon', body)
        self.assertEqual((result['attempt']['state'], result['wallet']['lives']), ('Lost', before['lives'] - 1))
        self.assertEqual(self.submit('abandon', body), result)

    def test_23_configured_strict_mode_blocks_legacy_http_verifier_clear(self):
        verifier = self.authority.provision(role='verifier'); self.identities.append(verifier)
        self.request('POST', '/internal/v1/verified-first-clear', {'attemptId': ident(), 'level': 1, 'proofDigest': 'a' * 64}, who=2, status=409)
        self.assertEqual((self.count('verified_clears'), self.count('rewards')), (0, 0))

    def test_24_legacy_paid_attempt_without_action_binding_requires_a_fresh_verified_session(self):
        before = self.wallet(); self.app.state.wallet.replay_enabled = False
        self.request('POST', '/v1/attempts/' + self.attempt + '/tools', {'commandId': ident(), 'expectedRevision': before['revision'], 'tool': 0})
        self.app.state.wallet.replay_enabled = True
        self.submit(status=409)
        self.assertEqual((len(self.worker.calls), self.count('replay_attempts')), (0, 0))

    def test_25_only_typed_pinned_fault_releases_without_life_refunds_start_and_preserves_used_tools(self):
        # Start a separate owned attempt with selected stock so refund is nonzero.
        self.submit('abandon', {'commandId': ident(), 'expectedRevision': self.wallet()['revision']})
        wallet = self.wallet()
        reserved = self.request('POST', '/v1/attempts/reserve', {'commandId': ident(), 'expectedRevision': wallet['revision'], 'level': 1, 'starting': [1, 0, 1, 0]})
        self.attempt = reserved['attempt']['attemptId']
        started = self.request('POST', '/v1/attempts/' + self.attempt + '/start', {'commandId': ident(), 'expectedRevision': reserved['wallet']['revision']})
        paid = self.submit('tool', self.body(actions=[], expectedWalletRevision=started['wallet']['revision'], tool=0, x=1, y=1))
        before = self.wallet(); self.worker.fault = True
        request = self.body(1, self.moves(first=1), expectedWalletRevision=before['revision'], tool=1, x=1, y=1)
        released = self.submit('tool', request)
        self.assertEqual((released['state'], released['attempt']['state'], released['displayReceipt']['outcome']), ('Committed', 'Released', 'Fault'))
        self.assertIsNone(released['model']); self.assertEqual((released['paidReceiptId'], released['addedMoves']), ('', 0))
        self.assertEqual((released['acceptedActions'], released['prefixRevision']), (1, 1))
        self.assertEqual((released['wallet']['lives'], released['wallet']['coins']), (before['lives'], before['coins']))
        self.assertEqual(released['wallet']['tools'], before['tools'])
        self.assertEqual(released['wallet']['starting'], [a + b for a, b in zip(before['starting'], [1, 0, 1, 0])])
        self.assertEqual(self.count('replay_paid_bindings'), 1)
        self.assertEqual(self.submit('tool', request), released)
        self.assertEqual(self.wallet()['starting'], released['wallet']['starting'])

    def test_26_fault_release_precommit_failure_does_not_partially_refund_or_end_attempt(self):
        before = self.wallet(); self.worker.fault = True
        self.broker.checkpoint = lambda stage: (_ for _ in ()).throw(OSError('precommit fault-release fixture')) if stage == 'BeforeCommit' else None
        body = self.body(); self.submit(body=body, status=202)
        self.assertEqual((self.wallet()['revision'], self.wallet()['lives']), (before['revision'], before['lives']))
        self.assertEqual(self.wallet()['activeAttempt']['state'], 'Started')
        self.broker.checkpoint = None
        released = self.operation(body['commandId'], '/resume', {})
        self.assertEqual(released['attempt']['state'], 'Released')
        self.assertEqual(self.operation(body['commandId']), released)

    def test_27_access_expiry_after_worker_leaves_payment_pending_until_fresh_actor_resumes_once(self):
        # This is only orchestration/credential fencing. The scripted worker
        # deliberately returns Won; separate native corpus proves board rules.
        before = self.wallet()
        with self.authority.database.transaction() as db:
            db.execute('UPDATE credentials SET expires_at=? WHERE player_id=?', (self.now + 1, self.players[0]))
        self.worker.outcome = 'Won'
        def expire_after_work(job):
            self.now += 1  # No revocation/deletion or other clock request.
            self.worker.observer = None
        self.worker.observer = expire_after_work
        body = self.body(actions=[], expectedWalletRevision=before['revision'], tool=0, x=1, y=1)
        self.submit('tool', body, status=401)
        with self.authority.database.connect() as db:
            balances = json.loads(db.execute('SELECT balances FROM wallets WHERE player_id=?', (self.players[0],)).fetchone()[0])
            self.assertEqual((balances[0], balances[1], balances[6]), (before['coins'], before['stars'], before['tools'][0]))
            operation = db.execute('SELECT state,error_code FROM replay_operations').fetchone()
            self.assertEqual(tuple(operation), ('Pending', 'actor_reauthentication_required'))
            self.assertEqual(tuple(db.execute('SELECT revision,prefix_json FROM replay_attempts').fetchone()), (0, '[]'))
            self.assertIsNone(db.execute('SELECT operation_id FROM replay_worker_slot').fetchone()[0])
            self.assertEqual(db.execute('SELECT state FROM gameplay_attempts WHERE id=?', (self.attempt,)).fetchone()[0], 'Started')
        self.assertEqual((self.count('rewards'), self.count('verified_clears'), self.count('replay_paid_bindings')), (0, 0, 0))

        self.identities[0] = self.authority.provision(self.players[0], lifetime=600)
        won = self.operation(body['commandId'], '/resume', {})
        self.assertEqual((won['state'], won['displayReceipt']['outcome']), ('Committed', 'Won'))
        self.assertEqual((won['wallet']['coins'], won['wallet']['stars'], won['wallet']['lives']),
                         (before['coins'] + 50, before['stars'] + 1, before['lives']))
        self.assertEqual(won['wallet']['tools'][0], before['tools'][0] - 1)
        self.assertEqual((len(self.worker.calls), self.count('rewards'), self.count('verified_clears'), self.count('replay_paid_bindings')),
                         (2, 1, 1, 1))
        ledger_count = self.count('wallet_ledger')
        self.assertEqual(self.operation(body['commandId'], '/resume', {}), won)
        self.assertEqual(self.submit('tool', body), won)
        self.assertEqual((len(self.worker.calls), self.count('wallet_ledger')), (2, ledger_count))
        self.assertEqual(self.wallet()['coins'], before['coins'] + 50)

    def seed_capacity_prefix(self, count):
        # Explicit synthetic durable history for the technical capacity limit,
        # not a claim of1000 natural moves on a real Unity board. Keep normal
        # authored opening budget and consistent prior paid-ledger bindings.
        registered = self.submit(body=self.body(actions=[]))
        budget = self.app.state.wallet.catalog.levels[0].moves
        continues, tools = divmod(count - budget, 6)
        actions, receipts = [], []
        with self.authority.database.transaction() as db:
            project(db, self.players[0], 'explicit-synthetic-capacity-stock',
                    [continues * 900, 0, 0, 0, 0, 0, tools, 0, 0, 0, 0], self.now)
            def paid(kind):
                operation = ident()
                receipt = project(db, self.players[0], 'attempt.' + kind.lower() + '/' + operation,
                                  [-900] + [0] * 10 if kind == 'Continue' else [0] * 6 + [-1] + [0] * 4, self.now)
                index = len(actions)
                tool, x, y, added = (-1, -1, -1, 5) if kind == 'Continue' else (0, 1, 1, 0)
                actions.append({'index': index, 'kind': kind, 'ax': x, 'ay': y, 'bx': -1, 'by': -1,
                                'tool': tool, 'movesAfter': added, 'receiptId': receipt})
                receipts.append({'receiptId': receipt, 'attemptId': self.attempt, 'kind': kind, 'actionIndex': index,
                                 'tool': tool, 'coins': 900 if added else 0, 'quantity': 0 if added else 1, 'movesAfter': added})
                db.execute('''INSERT INTO replay_operations(id,attempt_id,player_id,command_id,kind,request_hash,
                    request_json,state,base_revision,response_json,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,'Committed',?,?,?,?)''',
                           (operation, self.attempt, self.players[0], ident(), kind, sha256(b'explicit-synthetic-capacity'),
                            '{}', registered['prefixRevision'], json.dumps({'syntheticCapacityHistory': True}), self.now, self.now))
                db.execute('INSERT INTO replay_paid_bindings VALUES(?,?,?,?,?,?,?,?,?)',
                           (receipt, self.attempt, operation, index, kind, tool, x, y, added))
            def moves(amount):
                for _ in range(amount):
                    actions.append({'index': len(actions), 'kind': 'Swap', 'ax': 1, 'ay': 1, 'bx': 1, 'by': 2,
                                    'tool': -1, 'movesAfter': 0, 'receiptId': ''})
            for _ in range(tools):
                paid('Tool')
            moves(budget)
            for _ in range(continues):
                paid('Continue')
                moves(5)
            self.assertEqual(len(actions), count)
            db.execute("UPDATE gameplay_attempts SET state='AwaitingContinuation',continues=?,moves=? WHERE id=?",
                       (continues, budget + continues * 5, self.attempt))
            db.execute("""UPDATE replay_attempts SET prefix_json=?,receipts_json=?,outcome='Out of moves',moves=0,
                turn=?,checkpoint_sha=? WHERE attempt_id=?""",
                       (json.dumps(actions), json.dumps(receipts), budget + continues * 5,
                        sha256(b'explicit-synthetic-capacity-checkpoint'), self.attempt))
        return registered['prefixRevision']

    def capacity_state(self):
        with self.authority.database.connect() as db:
            return {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table)]
                    for table in ('wallets', 'wallet_ledger', 'gameplay_attempts', 'replay_attempts',
                                  'replay_paid_bindings', 'replay_worker_slot', 'rewards', 'verified_clears')}

    def test_28_at994_continue_reserves_all5_moves_and_old_paid_receipt_recovers_at1000(self):
        revision = self.seed_capacity_prefix(994)
        before = self.wallet()
        binding_count, calls = self.count('replay_paid_bindings'), len(self.worker.calls)
        body = self.body(revision, [], expectedWalletRevision=before['revision'])
        continued = self.submit('continue', body)
        self.assertEqual((continued['state'], continued['acceptedActions'], continued['addedMoves'], continued['model']['moves']),
                         ('Committed', 995, 5, 5))
        self.assertEqual(continued['wallet']['coins'], before['coins'] - 900)
        self.assertEqual(self.count('replay_paid_bindings'), binding_count + 1)
        exhausted = self.submit(body=self.body(continued['prefixRevision'], self.moves(5, 995)))
        self.assertEqual((exhausted['acceptedActions'], exhausted['model']['moves'], exhausted['attempt']['state']),
                         (1000, 0, 'AwaitingContinuation'))
        self.assertEqual(exhausted['wallet']['coins'], before['coins'] - 900)
        self.assertEqual(len(self.worker.calls), calls + 2)
        committed_state = self.capacity_state()
        self.assertEqual(self.submit('continue', body), continued)  # Original committed response, no capacity recheck/debit.
        self.assertEqual(self.operation(body['commandId'], '/resume', {}), continued)
        self.assertEqual(self.capacity_state(), committed_state)
        denied = self.submit('continue', self.body(exhausted['prefixRevision'], [], expectedWalletRevision=exhausted['wallet']['revision']))
        self.assertEqual((denied['state'], denied['code']), ('Rejected', 'gameplay_history_capacity'))
        self.assertEqual(self.capacity_state(), committed_state)

    def assert_continue_capacity_denied(self, count):
        revision = self.seed_capacity_prefix(count)
        before_wallet, before_state = self.wallet(), self.capacity_state()
        calls, operation_count = len(self.worker.calls), self.count('replay_operations')
        body = self.body(revision, [], expectedWalletRevision=before_wallet['revision'])
        denied = self.submit('continue', body)
        self.assertEqual((denied['state'], denied['code'], denied['wallet']['coins']),
                         ('Rejected', 'gameplay_history_capacity', before_wallet['coins']))
        self.assertEqual((denied['acceptedActions'], denied['prefixRevision'], denied['addedMoves'], denied['paidReceiptId']),
                         (count, revision, 0, ''))
        self.assertEqual(self.capacity_state(), before_state)
        with self.authority.database.connect() as db:
            row = db.execute('''SELECT state,lease_token,lease_until,candidate_json,snapshot_json,result_json
                FROM replay_operations WHERE command_id=?''', (body['commandId'],)).fetchone()
            self.assertEqual(tuple(row), ('Rejected', None, 0, None, None, None))
        self.assertEqual(self.submit('continue', body), denied)
        self.assertEqual(self.operation(body['commandId'], '/resume', {}), denied)
        self.assertEqual((len(self.worker.calls), self.count('replay_operations')), (calls, operation_count + 1))
        self.assertEqual(self.capacity_state(), before_state)

    def test_29_at995_refuses_continue_before_charge_or_worker_and_exact_retry_is_stable(self):
        self.assert_continue_capacity_denied(995)

    def test_30_at999_refuses_continue_before_charge_or_worker_and_exact_retry_is_stable(self):
        self.assert_continue_capacity_denied(999)

    def test_31_at1000_refuses_continue_before_charge_or_worker_and_exact_retry_is_stable(self):
        self.assert_continue_capacity_denied(1000)

    def test_32_tool_at995_cannot_take_one_of_the5_just_purchased_move_slots(self):
        revision = self.seed_capacity_prefix(994)
        continued = self.submit('continue', self.body(revision, [], expectedWalletRevision=self.wallet()['revision']))
        self.assertEqual((continued['acceptedActions'], continued['model']['moves']), (995, 5))
        before = self.capacity_state()
        calls, bindings = len(self.worker.calls), self.count('replay_paid_bindings')
        body = self.body(continued['prefixRevision'], [], expectedWalletRevision=continued['wallet']['revision'], tool=0, x=1, y=1)
        denied = self.submit('tool', body)
        self.assertEqual((denied['state'], denied['code'], denied['wallet']['tools']),
                         ('Rejected', 'gameplay_history_capacity', continued['wallet']['tools']))
        self.assertEqual((denied['acceptedActions'], denied['model']['moves'], denied['paidReceiptId']), (995, 5, ''))
        self.assertEqual(self.capacity_state(), before)
        self.assertEqual(self.submit('tool', body), denied)
        self.assertEqual(self.operation(body['commandId'], '/resume', {}), denied)
        self.assertEqual((len(self.worker.calls), self.count('replay_paid_bindings')), (calls, bindings))
        self.assertEqual(self.capacity_state(), before)

    def test_33_tool_at994_with5_moves_leaves_all5_slots_and_cached_tool_recovers_at1000(self):
        revision = self.seed_capacity_prefix(993)
        continued = self.submit('continue', self.body(revision, [], expectedWalletRevision=self.wallet()['revision']))
        self.assertEqual((continued['acceptedActions'], continued['model']['moves']), (994, 5))
        body = self.body(continued['prefixRevision'], [], expectedWalletRevision=continued['wallet']['revision'], tool=0, x=1, y=1)
        paid = self.submit('tool', body)
        self.assertEqual((paid['state'], paid['acceptedActions'], paid['model']['moves']), ('Committed', 995, 5))
        self.assertEqual(paid['wallet']['tools'][0], continued['wallet']['tools'][0] - 1)
        self.assertEqual(paid['wallet']['coins'], continued['wallet']['coins'])
        exhausted = self.submit(body=self.body(paid['prefixRevision'], self.moves(5, 995)))
        self.assertEqual((exhausted['acceptedActions'], exhausted['model']['moves']), (1000, 0))
        before, calls = self.capacity_state(), len(self.worker.calls)
        self.assertEqual(self.submit('tool', body), paid)
        self.assertEqual(self.operation(body['commandId'], '/resume', {}), paid)
        self.assertEqual(self.capacity_state(), before)
        self.assertEqual(len(self.worker.calls), calls)


if __name__ == '__main__': unittest.main()
