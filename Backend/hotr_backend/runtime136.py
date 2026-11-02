"""Service-runtime helpers from review 136: overload shedding, counters and batched retention.

Nothing here logs a token, credential, player ID, path or request content: only counts and
exception class names.
"""
import json
import logging
import shutil
import threading
import time
from pathlib import Path

LOG = logging.getLogger('hotr_backend.ops')
MAX_IN_FLIGHT = 256
SHED_RETRY_SECONDS = 2
LOG_INTERVAL_SECONDS = 60
RETENTION_INTERVAL_SECONDS = 900
BATCH_ROWS = 500
BATCH_PAUSE_SECONDS = .05
MAX_BATCHES_PER_STEP = 40
CREDENTIAL_KEEP_SECONDS = 86400
USED_REFRESH_KEEP_SECONDS = 7 * 86400
SESSION_RECEIPT_KEEP_SECONDS = 30 * 86400
CANDIDATE_KEEP_SECONDS = 3600
JOB_FOLDER_KEEP_SECONDS = 86400


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.counts = {}
        self.in_flight = 0
        self.peak_in_flight = 0

    def count(self, name, amount=1):
        with self.lock:
            self.counts[name] = self.counts.get(name, 0) + amount

    def snapshot(self, gate=None, broker=None):
        with self.lock:
            value = dict(self.counts)
        value['inFlight'], value['peakInFlight'] = self.in_flight, self.peak_in_flight
        if gate is not None:
            value.update(lockWaits=gate.lock_waits, lockWaitSeconds=round(gate.lock_wait_seconds, 3),
                         lockTimeouts=gate.lock_timeouts, writersQueued=gate.waiters)
        if broker is not None and hasattr(broker, 'queue_depth'):
            value['verificationQueue'] = broker.queue_depth()
        return value


class RequestGuard:
    """Refuses excess work as JSON. Only requests in progress count, never idle connections."""
    EXEMPT = ('/healthz', '/readyz')

    def __init__(self, app, metrics, runtime=None, limit=MAX_IN_FLIGHT):
        self.app, self.metrics, self.runtime, self.limit = app, metrics, runtime, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        metrics = self.metrics
        if self.runtime is not None:
            self.runtime.tick()
        if metrics.in_flight >= self.limit and scope.get('path') not in self.EXEMPT:
            metrics.count('shed')
            metrics.count('status503')
            await send({'type': 'http.response.start', 'status': 503, 'headers': [
                (b'content-type', b'application/json'), (b'retry-after', str(SHED_RETRY_SECONDS).encode()),
                (b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]})
            await send({'type': 'http.response.body', 'body': b'{"error":"server_busy"}'})
            return
        metrics.in_flight += 1
        metrics.peak_in_flight = max(metrics.peak_in_flight, metrics.in_flight)
        async def observed(message):
            if message['type'] == 'http.response.start' and message['status'] in (429, 503):
                metrics.count('status' + str(message['status']))
            await send(message)
        try:
            await self.app(scope, receive, observed)
        finally:
            metrics.in_flight -= 1


class Retention:
    """Removes data no retry or rule can reach any more, in small writer turns.

    Pruned: player access credentials a day after expiry, with their access rows; the retired
    rate_windows table; used refresh tokens a week after expiry once a later token has also been
    used; session-renewal receipts 30 days old once a later renewal has happened; stored replay
    candidate jobs an hour after the operation ended; worker job folders older than a day.

    Kept on purpose: wallets, ledger, rewards, purchases, attempts, verified clears, replay
    results and requests, audit events, messages and moderation, moderator credentials, players,
    devices, recovery records, current refresh tokens, guest/recover/logout/deletion receipts and
    the whole commands table, whose idempotency receipts have no age and can be retried by a
    client's durable outbox at any time.
    """
    STEPS = (
        ('rateWindows', 'DELETE FROM rate_windows WHERE rowid IN (SELECT rowid FROM rate_windows LIMIT ?)', ()),
        ('accessRows', '''DELETE FROM identity_access WHERE digest IN (SELECT c.digest FROM credentials c
            WHERE c.role='player' AND c.expires_at<? AND c.digest IN (SELECT digest FROM identity_access)
            AND NOT EXISTS(SELECT 1 FROM social_moderators m WHERE m.credential_digest=c.digest) LIMIT ?)''', ('credential',)),
        ('credentials', '''DELETE FROM credentials WHERE digest IN (SELECT c.digest FROM credentials c
            WHERE c.role='player' AND c.expires_at<?
            AND NOT EXISTS(SELECT 1 FROM identity_access a WHERE a.digest=c.digest)
            AND NOT EXISTS(SELECT 1 FROM rate_windows r WHERE r.credential=c.digest)
            AND NOT EXISTS(SELECT 1 FROM social_moderators m WHERE m.credential_digest=c.digest) LIMIT ?)''', ('credential',)),
        ('usedRefreshTokens', '''DELETE FROM identity_refresh WHERE digest IN (SELECT t.digest FROM identity_refresh t
            WHERE t.used_request_id IS NOT NULL AND t.expires_at<?
            AND NOT EXISTS(SELECT 1 FROM identity_refresh n WHERE n.digest=t.replacement_digest AND n.used_request_id IS NULL)
            ORDER BY t.expires_at LIMIT ?)''', ('refresh',)),
        ('sessionReceipts', '''DELETE FROM identity_operations WHERE rowid IN (SELECT o.rowid FROM identity_operations o
            JOIN identity_sessions s ON s.id=o.family_id
            WHERE o.purpose='session' AND o.created_at<? AND o.created_at<s.last_used_at LIMIT ?)''', ('receipt',)),
        ('candidateJobs', '''UPDATE replay_operations SET candidate_json=NULL WHERE id IN (SELECT id FROM replay_operations
            WHERE candidate_json IS NOT NULL AND state IN ('Committed','Rejected') AND updated_at<? LIMIT ?)''', ('candidate',)),
    )

    def __init__(self, authority, metrics=None, jobs_directory=None, *, pause=BATCH_PAUSE_SECONDS):
        self.authority, self.database, self.metrics = authority, authority.database, metrics
        self.jobs_directory, self.pause = jobs_directory, pause

    def run_once(self, stop=None):
        now = self.authority._now()
        cutoff = {'credential': now - CREDENTIAL_KEEP_SECONDS, 'refresh': now - USED_REFRESH_KEEP_SECONDS,
                  'receipt': now - SESSION_RECEIPT_KEEP_SECONDS, 'candidate': now - CANDIDATE_KEEP_SECONDS}
        removed = {}
        for name, statement, bounds in self.STEPS:
            total = 0
            for _ in range(MAX_BATCHES_PER_STEP):
                if stop is not None and stop.is_set():
                    return removed
                with self.database.transaction() as db:
                    changed = db.execute(statement, (*[cutoff[key] for key in bounds], BATCH_ROWS)).rowcount
                total += changed
                if changed < BATCH_ROWS:
                    break
                time.sleep(self.pause)
            removed[name] = total
        removed['jobFolders'] = self._job_folders(time.time() - JOB_FOLDER_KEEP_SECONDS)
        if self.metrics is not None:
            for name, value in removed.items():
                if value:
                    self.metrics.count('pruned' + name[0].upper() + name[1:], value)
        return removed

    def _job_folders(self, older_than):
        # run() removes its folder. This clears what a killed process left behind.
        if self.jobs_directory is None:
            return 0
        removed = 0
        try:
            for path in Path(self.jobs_directory).glob('replay-*'):
                if path.is_dir() and not path.is_symlink() and path.stat().st_mtime < older_than:
                    shutil.rmtree(path, ignore_errors=True)
                    removed += 1
        except OSError:
            pass
        return removed


class ServiceRuntime:
    """Work a long-running service owes itself. Started only by the owned launchers."""
    def __init__(self, authority, metrics, broker=None, jobs_directory=None):
        self.metrics, self.gate, self.broker = metrics, authority.database.writer_gate, broker
        self.retention = Retention(authority, metrics, jobs_directory)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.running = False
        began = time.monotonic()
        self.next_retention, self.next_log = began + RETENTION_INTERVAL_SECONDS, began + LOG_INTERVAL_SECONDS
        self.logged = None

    def tick(self):
        now = time.monotonic()
        if now >= self.next_log:
            self.next_log = now + LOG_INTERVAL_SECONDS
            self.log()
        if now >= self.next_retention:
            with self.lock:
                if self.running:
                    return
                self.running = True
                self.next_retention = now + RETENTION_INTERVAL_SECONDS
            threading.Thread(target=self._retain, daemon=True, name='hotr-retention').start()

    def log(self):
        value = self.metrics.snapshot(self.gate, self.broker)
        steady = {key: item for key, item in value.items() if key not in ('inFlight', 'writersQueued')}
        if steady != self.logged and any(item for key, item in steady.items() if key != 'peakInFlight'):
            self.logged = steady
            LOG.warning('hotr_ops %s', json.dumps(value, sort_keys=True, separators=(',', ':')))

    def _retain(self):
        try:
            self.retention.run_once(self.stop_event)
        except Exception as error:
            self.metrics.count('retentionFailed')
            LOG.warning('hotr_retention_failed %s', type(error).__name__)
        finally:
            with self.lock:
                self.running = False

    def stop(self):
        self.stop_event.set()
        if self.broker is not None and hasattr(self.broker, 'stop_dispatcher'):
            self.broker.stop_dispatcher()
