"""Bounded loopback TCP/SQLite operational rehearsal with disposable accounts.

The child hosts the actual ASGI factory in a separate Uvicorn process. Only this
loopback fixture adds an operator-file-controlled lost-response fault. No hosted
deployment, Unity execution, provider payment, ad impression or capacity claim.
Private keys, tokens, databases and response bodies remain in ignored storage or
memory; the exported report contains only checks, timings and source digests.
"""
import argparse
import base64
import concurrent.futures
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'Backend'
sys.path.insert(0, str(BACKEND))

import httpx
from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS

from hotr_backend.api import create_app
from hotr_backend.operations import backup_database, restore_database
from hotr_backend.storage import Database, SCHEMA_VERSION
from run_tests import source_hashes


def digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as file:
        json.dump(value, file, indent=2)
        file.write('\n')
        file.flush()
        os.fsync(file.fileno())


class FixtureJob:
    """Kill-on-close covers the Windows venv redirector AND actual Python."""
    def __init__(self):
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [('processTime', ctypes.c_int64), ('jobTime', ctypes.c_int64), ('flags', w.DWORD),
                        ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t), ('active', w.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('readOps', 'writeOps', 'otherOps', 'readBytes', 'writeBytes', 'otherBytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('processMemory', ctypes.c_size_t), ('jobMemory', ctypes.c_size_t),
                        ('peakProcessMemory', ctypes.c_size_t), ('peakJobMemory', ctypes.c_size_t)]
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        for name, args, result in (
            ('CreateJobObjectW', [ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            ('SetInformationJobObject', [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            ('OpenProcess', [w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            ('IsProcessInJob', [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)], w.BOOL),
            ('AssignProcessToJobObject', [w.HANDLE, w.HANDLE], w.BOOL),
            ('WaitForSingleObject', [w.HANDLE, w.DWORD], w.DWORD),
            ('CloseHandle', [w.HANDLE], w.BOOL)):
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = args, result
        self.handle = self.kernel.CreateJobObjectW(None, None)
        info = Extended()
        info.basic.flags = 0x2000
        if not self.handle or not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise DrillFailure('owned_fixture_job_unavailable')

    def assign(self, pid):
        from ctypes import wintypes as w
        handle = self.kernel.OpenProcess(0x1101, False, pid)
        if not handle:
            raise DrillFailure('owned_fixture_process_unavailable')
        try:
            member = w.BOOL()
            if (not self.kernel.IsProcessInJob(handle, self.handle, ctypes.byref(member))
                    or not member and not self.kernel.AssignProcessToJobObject(self.handle, handle)):
                raise DrillFailure('owned_fixture_job_assignment_failed')
        finally:
            self.kernel.CloseHandle(handle)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def child(private):
    import uvicorn
    from fastapi.responses import JSONResponse
    private = private.resolve()
    allowed = (ROOT / '.verification-cache/Review93/BackendOperations').resolve()
    if not private.is_relative_to(allowed):
        raise SystemExit('private_fixture_path_required')
    settings = json.loads(private.read_text('utf-8'))
    directory = private.parent
    database = (directory / settings['database']).resolve()
    if not database.is_relative_to(directory) or settings.get('mode') != 'isolated_loopback93':
        raise SystemExit('private_fixture_configuration_invalid')
    # Explicit fixture-only activation; shipping configuration remains disabled.
    app = create_app(database, identity_enabled=True, social_enabled=True)

    @app.middleware('http')
    async def lost_committed_claim_response(request, call_next):
        response = await call_next(request)
        flag = directory / 'drop-confirmed-gift-response.once'
        if (request.url.path == '/v1/daily-gift/claim' and response.status_code == 200 and flag.exists()):
            try:
                flag.unlink()
            except FileNotFoundError:
                pass
            else:
                return JSONResponse({'error': 'fixture_confirmation_lost'}, status_code=503)
        return response

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    connection = {'origin': 'http://127.0.0.1:' + str(listener.getsockname()[1]),
                  'pid': os.getpid(), 'parentPid': os.getppid(), 'runId': settings['runId']}
    pending = directory / 'connection.pending'
    write_new(pending, connection)
    os.replace(pending, directory / 'connection.json')
    server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning',
                                          proxy_headers=False, limit_concurrency=32))
    server.run(sockets=[listener])


class DrillFailure(Exception):
    pass


class Drill:
    def __init__(self, output):
        self.output = output.resolve()
        allowed = (ROOT / 'Verification/Evidence/Review93/Backend').resolve()
        if not self.output.is_relative_to(allowed) or self.output.exists():
            raise DrillFailure('new_review93_backend_output_required')
        self.output.mkdir(parents=True)
        self.identifier = uuid.uuid4().hex
        self.private = ROOT / '.verification-cache/Review93/BackendOperations' / self.identifier
        self.private.mkdir(parents=True)
        self.settings = self.private / 'server.json'
        write_new(self.settings, {'mode': 'isolated_loopback93', 'runId': self.identifier, 'database': 'authority.sqlite3'})
        self.database = self.private / 'authority.sqlite3'
        self.checks, self.samples, self.processes = [], [], []
        self.secrets = []
        self.lock = threading.Lock()
        self.process, self.http, self.job = None, None, None
        self.started = time.monotonic()
        self.utc = dt.datetime.now(dt.timezone.utc).isoformat()
        self.sources = source_hashes()

    def check(self, name, condition):
        if not condition:
            raise DrillFailure(name)
        self.checks.append(name)

    def stop(self):
        if self.http is not None:
            self.http.close()
            self.http = None
        if self.process is not None:
            owned = self.process
            if self.job is not None:
                self.job.close()
                self.job = None
            if owned.poll() is None:
                owned.terminate()
                try:
                    owned.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    owned.kill()
                    owned.wait(timeout=5)
            self.processes[-1]['exitCode'] = owned.returncode
            self.processes[-1]['ownedProcessTerminated'] = True
            self.process = None

    def start(self, database='authority.sqlite3'):
        settings = {'mode': 'isolated_loopback93', 'runId': self.identifier, 'database': database}
        # This file contains no credentials, only the private fixture path.
        self.settings.write_text(json.dumps(settings), 'utf-8')
        prior = self.private / 'connection.json'
        if prior.exists():
            prior.unlink()
        if os.name != 'nt':
            raise DrillFailure('windows_owned_process_rehearsal_required')
        self.job = FixtureJob()
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--serve-private', str(self.settings)]
        self.process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.job.assign(self.process.pid)
        self.processes.append({'ordinal': len(self.processes) + 1, 'pid': self.process.pid,
                               'database': 'restored_snapshot' if database != 'authority.sqlite3' else 'original_disposable',
                               'boundToLoopback': True, 'separateProcess': True,
                               'ownedKillOnCloseJobAssigned': True,
                               'terminationScope': 'owned process termination, not physical power loss'})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise DrillFailure('fixture_process_stopped_before_readiness')
            if prior.exists():
                connection = json.loads(prior.read_text('utf-8'))
                if (connection['runId'] == self.identifier and
                        (connection['pid'] == self.process.pid or connection['parentPid'] == self.process.pid)):
                    self.job.assign(connection['pid'])
                    self.processes[-1]['actualServerPid'] = connection['pid']
                    if self.http is None:
                        self.http = httpx.Client(base_url=connection['origin'], timeout=10, trust_env=False,
                                                 limits=httpx.Limits(max_connections=16, max_keepalive_connections=16))
                    try:
                        if self.http.get('/readyz').status_code == 200:
                            self.check('separate_process_' + str(len(self.processes)) + '_writer_ready', True)
                            return
                    except httpx.HTTPError:
                        pass
            time.sleep(0.05)
        raise DrillFailure('fixture_readiness_timeout')

    def request(self, method, path, owner=None, body=None, status=200):
        headers = {'Authorization': 'Bearer ' + owner['accessToken']} if owner is not None else {}
        started = time.monotonic()
        response = self.http.request(method, path, headers=headers, json=body)
        with self.lock:
            self.samples.append({'method': method, 'status': response.status_code,
                                 'milliseconds': round((time.monotonic() - started) * 1000, 3)})
        if response.status_code != status:
            # Never stringify a response, request or assertion value here.
            raise DrillFailure('unexpected_http_status_' + str(response.status_code) + '_expected_' + str(status))
        self.check('http_' + str(len(self.samples)) + '_expected_status', True)
        return response.json()

    def post(self, path, owner, status=200, **body):
        body.setdefault('commandId', uuid.uuid4().hex)
        return self.request('POST', path, owner, body, status)

    def signed(self, owner, purpose, **values):
        key = owner['key']
        public = base64.b64encode(key.public_key().export_key(format='DER')).decode('ascii')
        body = {'requestId': uuid.uuid4().hex, 'publicKey': public, **values}
        binding = {'protocol': 'hotr-managed-identity-v1', 'purpose': purpose,
                   'requestId': body['requestId'], 'publicKey': public}
        fields = {'guest': (('refreshToken', 'refreshDigest'), ('recoverySecret', 'recoveryDigest')),
                  'session': (('refreshToken', 'refreshDigest'), ('replacementToken', 'replacementDigest')),
                  'recover': (('refreshToken', 'refreshDigest'), ('recoverySecret', 'recoveryDigest'),
                              ('replacementRecoverySecret', 'replacementRecoveryDigest')),
                  'delete': (('refreshToken', 'refreshDigest'),)}
        for source, target in fields[purpose]:
            binding[target] = digest(body[source])
            self.secrets.append(body[source])
        if purpose in ('recover', 'delete'):
            binding['playerId'] = body['playerId']
        challenge = self.request('POST', '/v1/identity/challenges', body={
            'purpose': purpose, 'requestId': body['requestId'], 'publicKey': public,
            'payloadDigest': digest(canonical(binding))})
        expected = 'hotr-managed-identity-v1\n' + canonical({field: challenge[field] for field in
            ('challengeId', 'expiresAt', 'keyFingerprint', 'nonce', 'payloadDigest', 'purpose', 'requestId')})
        decoded = base64.b64decode(challenge['signingBytes'], validate=True)
        self.check('challenge_' + purpose + '_independently_bound',
                   decoded == expected.encode('ascii') and challenge['payloadDigest'] == digest(canonical(binding)))
        signature = DSS.new(key, 'fips-186-3', encoding='der').sign(SHA256.new(decoded))
        return {**body, 'challengeId': challenge['challengeId'], 'signature': base64.b64encode(signature).decode('ascii')}

    def guest(self):
        owner = {'key': ECC.generate(curve='P-256'), 'refresh': secrets.token_urlsafe(32),
                 'recovery': secrets.token_urlsafe(32)}
        body = self.signed(owner, 'guest', refreshToken=owner['refresh'], recoverySecret=owner['recovery'])
        result = self.request('POST', '/v1/identity/guest', body=body)
        self.secrets.append(result['accessToken'])
        owner.update(result)
        return owner

    def friendship(self, first, second):
        sent = self.post('/v1/friends/request', first, playerId=second['playerId'])
        self.post('/v1/friends/respond', second, requestId=sent['requestId'], action='accept')

    def run(self):
        self.start()
        self.request('GET', '/v1/wallet', status=401)
        owners = [self.guest() for _ in range(4)]
        a, b, c, staff = owners
        for index, owner in enumerate(owners):
            self.post('/v1/profile', owner, displayName='Review ' + str(index + 1), leaderboardOptIn=index < 3)
            self.post('/v1/region', owner, regionCode='US' if index == 2 else 'RU')
            wallet = self.request('GET', '/v1/wallet', owner)
            self.check('guest_' + str(index + 1) + '_single_genesis', wallet['coins'] == 1250 and wallet['lives'] == 5)
        global_rows = self.request('GET', '/v1/leaderboards/global', a)['entries']
        regional_rows = self.request('GET', '/v1/leaderboards/regional', a)['entries']
        self.check('global_regional_country_and_shared_zero_rank',
                   len(global_rows) == 3 and len(regional_rows) == 2 and all(row['rank'] == 1 for row in global_rows)
                   and c['playerId'] not in {row['playerId'] for row in regional_rows})
        self.request('POST', '/v1/profile', a, {'commandId': uuid.uuid4().hex,
                     'displayName': 'Invalid score', 'leaderboardOptIn': True, 'completedLevels': 50}, status=422)
        self.friendship(a, b)
        direct_path = '/v1/messages/Direct/' + b['playerId']
        direct = self.post(direct_path, a, text='Controlled direct message')
        received = self.request('GET', '/v1/messages/Direct/' + a['playerId'] + '?tail=true', b)
        self.check('direct_delivery_and_owned_latest_window',
                   len(received['messages']) == 1 and received['messages'][0]['messageId'] == direct['messageId'])
        self.request('GET', '/v1/messages/Direct/' + a['playerId'], c, status=404)
        team = self.post('/v1/teams', a, name='Review Team', description='Disposable operational rehearsal')['teamId']
        self.post('/v1/teams/' + team + '/join', b)
        team_message = self.post('/v1/messages/Team/' + team, a, text='Controlled team message')
        self.check('team_chat_member_can_read', len(self.request('GET', '/v1/messages/Team/' + team, b)['messages']) == 1)
        self.request('GET', '/v1/messages/Team/' + team, c, status=403)
        teams = self.request('GET', '/v1/team-leaderboards/regional', b)
        self.check('regional_team_uses_current_leader_country', len(teams['entries']) == 1
                   and teams['entries'][0]['teamId'] == team and teams['entries'][0]['memberCount'] == 2)
        self.post('/v1/blocks/add', b, playerId=a['playerId'])
        self.request('POST', direct_path, a, {'commandId': uuid.uuid4().hex, 'text': 'Blocked'}, status=404)
        self.check('blocked_team_author_filtered', not self.request('GET', '/v1/messages/Team/' + team, b)['messages'])
        self.post('/v1/reports', b, messageId=direct['messageId'], reason='Other', details='Disposable report')
        self.request('GET', '/internal/v1/moderation/reports', a, status=403)
        # An explicit trusted operator fixture grant is not a public role route.
        database = Database(self.database)
        with database.transaction() as db:
            db.execute('INSERT INTO social_moderators VALUES(?,?)', (digest(staff['accessToken']), int(time.time())))
        queue = self.request('GET', '/internal/v1/moderation/reports', staff)
        self.check('operator_granted_moderation_queue', len(queue['reports']) == 1)
        self.post('/internal/v1/moderation/messages', staff, messageId=direct['messageId'],
                  action='Hide', reason='Disposable operator review')
        self.post('/internal/v1/moderation/messages', staff, messageId=team_message['messageId'],
                  action='Hide', reason='Disposable operator review')
        self.post('/v1/blocks/remove', b, playerId=a['playerId'])
        # Unblocking does not silently restore the cancelled friendship or
        # bypass the existing 24-hour safety cooldown for another request.
        self.post('/v1/friends/request', a, status=409, playerId=b['playerId'])
        self.request('GET', '/v1/messages/Direct/' + a['playerId'], b, status=404)
        self.check('moderated_team_message_hidden_after_unblock',
                   not self.request('GET', '/v1/messages/Team/' + team, b)['messages'])
        self.post('/v1/ugc/reports', b, kind='Team', targetId=team, reason='Other', details='Disposable review')
        self.post('/internal/v1/moderation/ugc/actions', staff, kind='Team', targetId=team,
                  action='ResetTeamText', reason='Disposable operator review')
        self.check('manual_team_text_reset_keeps_membership',
                   self.request('GET', '/v1/teams/' + team, b)['memberCount'] == 2)
        # Drop the first successful grant response after its actual DB commit.
        offer = self.request('GET', '/v1/daily-gift/offer', a)
        claim = {'requestId': uuid.uuid4().hex, 'offerId': offer['id'], 'day': offer['day'],
                 'step': offer['step'], 'schedule': offer['schedule'], 'expectedGrant': offer['grant']}
        (self.private / 'drop-confirmed-gift-response.once').write_text('explicit isolated fixture', 'ascii')
        self.request('POST', '/v1/daily-gift/claim', a, claim, status=503)
        def concurrent_claim(index):
            body = claim if index < 6 else {**claim, 'requestId': uuid.uuid4().hex}
            return self.request('POST', '/v1/daily-gift/claim', a, body)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            claims = list(pool.map(concurrent_claim, range(12)))
        self.check('lost_reply_and_12_parallel_claims_one_durable_receipt',
                   len({row['receiptId'] for row in claims}) == 1
                   and self.request('GET', '/v1/wallet', a)['coins'] == 1300
                   and len(self.request('GET', '/v1/rewards', a)['receipts']) == 1)
        self.check('private_records_are_owner_derived', self.request('GET', '/v1/records', a)['completedLevels'] == 0)
        self.check('wellworks_remains_locked_without_trusted_clears',
                   not any(row['eligible'] for row in self.request('GET', '/v1/wellworks', a)['milestones']))
        self.request('GET', '/v1/rain-cup', a)
        ads = self.request('GET', '/v1/ads/rewarded/status?timeZoneId=Europe/Moscow', a)
        self.check('ads_disabled_and_local_calendar_retained', ads['reason'] == 'ads_disabled'
                   and ads['rewardCoins'] == 400 and ads['dailyLimit'] == 3 and ads['timeZoneId'] == 'Europe/Moscow')
        catalog = self.request('GET', '/v1/commerce/catalog', a)
        self.check('unconfigured_checkout_fails_closed', not catalog['enabled'] and not catalog['products'])
        self.request('POST', '/v1/commerce/orders', a, {'commandId': uuid.uuid4().hex, 'productId': 'coins_1000'}, status=503)
        # Bounded concurrent TCP reads across independent managed owners.
        routes = ('/v1/wallet', '/v1/records', '/v1/leaderboards/global', '/v1/friends')
        def concurrent_read(index):
            return self.request('GET', routes[index % 4], owners[index % 3])
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(concurrent_read, range(72)))
        self.check('72_concurrent_tcp_reads_completed', len(responses) == 72)
        # Real online backup includes committed WAL and restores only to a NEW
        # file. Actual separate-process startup from that restore is below.
        backup = backup_database(self.database, self.private / 'snapshot.sqlite3')
        restore = restore_database(self.private / 'snapshot.sqlite3', self.private / 'restored.sqlite3')
        self.check('validated_online_backup_restore_new_files', backup['status'] == restore['status'] == 'completed'
                   and backup['schemaVersion'] == restore['schemaVersion'] == SCHEMA_VERSION)
        self.stop()
        self.start()
        self.check('original_restart_preserves_claim_wallet_and_social',
                   self.request('GET', '/v1/wallet', a)['coins'] == 1300
                   and self.request('POST', '/v1/daily-gift/claim', a, claim)['receiptId'] == claims[0]['receiptId']
                   and self.request('GET', '/v1/teams/' + team, b)['memberCount'] == 2)
        self.stop()
        self.start('restored.sqlite3')
        self.check('restored_database_http_preserves_finance_and_social',
                   self.request('GET', '/v1/wallet', a)['coins'] == 1300
                   and len(self.request('GET', '/v1/rewards', a)['receipts']) == 1
                   and self.request('GET', '/v1/teams/' + team, b)['memberCount'] == 2
                   and not self.request('GET', '/v1/messages/Team/' + team, b)['messages'])
        # Rotate then recover and delete a disposable ordinary managed account.
        old_access, old_refresh = c['accessToken'], c['refresh']
        replacement = secrets.token_urlsafe(32)
        session = self.request('POST', '/v1/identity/session', body=self.signed(c, 'session',
            refreshToken=old_refresh, replacementToken=replacement))
        self.secrets.append(session['accessToken'])
        c.update(session)
        c['refresh'] = replacement
        self.request('GET', '/v1/wallet', {**c, 'accessToken': old_access}, status=401)
        old_access = c['accessToken']
        recovered = {'key': ECC.generate(curve='P-256'), 'refresh': secrets.token_urlsafe(32),
                     'recovery': secrets.token_urlsafe(32)}
        recovery = self.request('POST', '/v1/identity/recover', body=self.signed(recovered, 'recover',
            playerId=c['playerId'], recoverySecret=c['recovery'], replacementRecoverySecret=recovered['recovery'],
            refreshToken=recovered['refresh']))
        self.secrets.append(recovery['accessToken'])
        recovered.update(recovery)
        self.check('cross_key_recovery_preserves_player_and_single_genesis', recovered['playerId'] == c['playerId']
                   and self.request('GET', '/v1/wallet', recovered)['coins'] == 1250)
        self.request('GET', '/v1/wallet', {**c, 'accessToken': old_access}, status=401)
        deletion = self.request('POST', '/v1/account/deletion', body=self.signed(recovered, 'delete',
            playerId=recovered['playerId'], refreshToken=recovered['refresh']))
        self.check('signed_deletion_revokes_and_exposes_retention_limits', deletion['state'] == 'DeletionRequested'
                   and deletion['sessionsRevoked'] and not deletion['physicalPurgeComplete'])
        self.request('GET', '/v1/wallet', recovered, status=401)
        ranks = self.request('GET', '/v1/leaderboards/global', a)['entries']
        self.check('deleted_player_removed_from_standings', c['playerId'] not in {row['playerId'] for row in ranks})
        # Use a separate owner's remaining authenticated budget, never change
        # runtime limits. Stop immediately at the observed cap.
        seen_rate_limit = False
        rate_successes = 0
        for _ in range(121):
            response = self.http.get('/v1/time', headers={'Authorization': 'Bearer ' + staff['accessToken']})
            if response.status_code == 429:
                seen_rate_limit = response.json() == {'error': 'rate_limited'}
                break
            if response.status_code != 200:
                raise DrillFailure('rate_control_unexpected_status')
            rate_successes += 1
        self.check('persistent_auth_rate_limit_observed_without_private_echo', seen_rate_limit and 0 < rate_successes <= 120)
        with Database(self.private / 'restored.sqlite3').connect() as db:
            self.check('restored_database_integrity_and_foreign_keys', db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
                       and not db.execute('PRAGMA foreign_key_check').fetchall())
            self.check('one_reward_ledger_origin_after_recovery', db.execute("SELECT COUNT(*) FROM wallet_ledger WHERE origin LIKE 'reward/%'").fetchone()[0] == 1)
        return {'backup': backup, 'restore': restore, 'parallelReads': 72, 'parallelClaimRetries': 12,
                'rateControlSuccessfulReadsBeforeLimit': rate_successes,
                'ordinaryOwnerAccounts': 4, 'moderatorGrant': 'explicit operator fixture row only',
                'trustedProgressionForged': False, 'realPayments': False, 'realAds': False}

    def finish(self, status, details=None, failure=None):
        self.stop()
        after = source_hashes()
        changed = sorted(path for path in self.sources.keys() | after.keys() if self.sources.get(path) != after.get(path))
        report = {'schemaVersion': 1, 'startedUtc': self.utc, 'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                  'status': status if not changed else 'FAIL_OPERATIONAL_REHEARSAL93_SOURCE_CHANGED',
                  'scope': __doc__.strip(), 'checks': len(self.checks), 'passed': self.checks,
                  'failureCode': failure, 'seconds': round(time.monotonic() - self.started, 3),
                  'requests': self.samples, 'processes': self.processes, 'details': details,
                  'sourceSHA256': self.sources, 'sourceSHA256After': after, 'sourceInputsChangedDuringRun': changed,
                  'limits': ['Local TCP loopback, not hosted HTTPS or production capacity',
                             'Controlled owned process termination, not physical power-loss certification',
                             'No Unity worker/gameplay, live provider payment, notification or ad impression',
                             'Financial provider, expiry, concurrency and boundary controls are separate service tests',
                             'Four disposable managed owners; no ordinary device/user state read or changed']}
        encoded = json.dumps(report, indent=2)
        if any(secret and secret in encoded for secret in self.secrets):
            raise DrillFailure('credential_export_prevented')
        write_new(self.output / 'Operational_Rehearsal.json', report)
        print(json.dumps({'status': report['status'], 'checks': len(self.checks), 'requests': len(self.samples)}))
        return 0 if report['status'] == 'PASS_OPERATIONAL_REHEARSAL93' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--serve-private', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve_private is not None:
        child(args.serve_private)
        return 0
    if args.out is None:
        raise SystemExit('new_output_directory_required')
    drill = Drill(args.out)
    try:
        details = drill.run()
    except DrillFailure as error:
        return drill.finish('FAIL_OPERATIONAL_REHEARSAL93', failure=str(error))
    except Exception:
        # Raw exceptions may embed private transport/identity input. Keep only
        # a fixed failure code, plus the already completed public checks.
        return drill.finish('FAIL_OPERATIONAL_REHEARSAL93', failure='unexpected_fixture_failure')
    return drill.finish('PASS_OPERATIONAL_REHEARSAL93', details=details)


if __name__ == '__main__':
    raise SystemExit(main())
