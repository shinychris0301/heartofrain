import collections
import contextlib
import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA_VERSION = 15

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


DDL = '''
CREATE TABLE schema_info (version INTEGER NOT NULL);
INSERT INTO schema_info VALUES (1);
CREATE TABLE players (
 id TEXT PRIMARY KEY, completed INTEGER NOT NULL DEFAULT 0 CHECK(completed BETWEEN 0 AND 50),
 gift_claims INTEGER NOT NULL DEFAULT 0, last_gift_day INTEGER NOT NULL DEFAULT -1,
 reward_totals TEXT NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE clock_state (id INTEGER PRIMARY KEY CHECK(id=1), high_water INTEGER NOT NULL);
INSERT INTO clock_state VALUES (1,0);
CREATE TABLE credentials (
 digest TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id),
 role TEXT NOT NULL CHECK(role IN ('player','verifier')), expires_at INTEGER NOT NULL,
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)));
CREATE TABLE rate_windows (
 credential TEXT PRIMARY KEY REFERENCES credentials(digest), window INTEGER NOT NULL, requests INTEGER NOT NULL);
CREATE TABLE offers (
 id TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id), day INTEGER NOT NULL,
 step INTEGER NOT NULL, schedule TEXT NOT NULL, grant_json TEXT NOT NULL,
 UNIQUE(player_id,day));
CREATE TABLE rewards (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, player_id TEXT NOT NULL REFERENCES players(id),
 source TEXT NOT NULL, source_key TEXT NOT NULL, grant_json TEXT NOT NULL, created_at INTEGER NOT NULL,
 UNIQUE(player_id,source,source_key));
CREATE TABLE commands (
 player_id TEXT NOT NULL REFERENCES players(id), operation TEXT NOT NULL, command_id TEXT NOT NULL,
 payload_digest TEXT NOT NULL, response_json TEXT NOT NULL,
 PRIMARY KEY(player_id,operation,command_id));
CREATE TABLE daily_claims (
 offer_id TEXT PRIMARY KEY REFERENCES offers(id), player_id TEXT NOT NULL REFERENCES players(id),
 day INTEGER NOT NULL, reward_id TEXT NOT NULL REFERENCES rewards(id), UNIQUE(player_id,day));
CREATE TABLE verified_clears (
 player_id TEXT NOT NULL REFERENCES players(id), attempt_id TEXT NOT NULL, level INTEGER NOT NULL,
 proof_digest TEXT NOT NULL, created_at INTEGER NOT NULL, cup_id TEXT,
 PRIMARY KEY(player_id,attempt_id), UNIQUE(player_id,level));
CREATE TABLE cup_runs (
 id TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id),
 state TEXT NOT NULL CHECK(state IN ('Active','Finished','Claimed')),
 joined_at INTEGER NOT NULL, ends_at INTEGER NOT NULL, joined_completed INTEGER NOT NULL,
 points INTEGER NOT NULL DEFAULT 0, final_rank INTEGER NOT NULL DEFAULT 0, rules_json TEXT NOT NULL);
CREATE UNIQUE INDEX one_unclaimed_cup ON cup_runs(player_id) WHERE state!='Claimed';
CREATE TABLE audit_events (
 player_id TEXT NOT NULL REFERENCES players(id), event_id TEXT NOT NULL,
 payload_digest TEXT NOT NULL, payload_json TEXT NOT NULL, received_at INTEGER NOT NULL,
 trust TEXT NOT NULL CHECK(trust='client_reported'), PRIMARY KEY(player_id,event_id));
'''

# Explicit additive migration: existing staging accounts/rewards are preserved.
# Purchase credits are separate from reward_totals and from any gameplay wallet.
COMMERCE_V2 = '''
CREATE TABLE commerce_orders (
 id TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id),
 catalog_version TEXT NOT NULL, internal_product TEXT NOT NULL, store_product TEXT NOT NULL,
 app_id INTEGER NOT NULL, sandbox INTEGER NOT NULL CHECK(sandbox IN (0,1)),
 amount_minor INTEGER NOT NULL CHECK(amount_minor>0), currency TEXT NOT NULL,
 coins INTEGER NOT NULL CHECK(coins>0), binding TEXT NOT NULL UNIQUE,
 state TEXT NOT NULL DEFAULT 'Created', invoice_id TEXT, purchase_id TEXT,
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
CREATE UNIQUE INDEX commerce_one_invoice ON commerce_orders(app_id,sandbox,invoice_id) WHERE invoice_id IS NOT NULL;
CREATE UNIQUE INDEX commerce_one_purchase ON commerce_orders(app_id,sandbox,purchase_id) WHERE purchase_id IS NOT NULL;
CREATE TABLE commerce_invoice_requests (
 order_id TEXT NOT NULL REFERENCES commerce_orders(id), invoice_id TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'Pending', attempts INTEGER NOT NULL DEFAULT 0,
 last_error TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL,
 PRIMARY KEY(order_id,invoice_id));
CREATE TABLE commerce_credits (
 id TEXT PRIMARY KEY, order_id TEXT NOT NULL UNIQUE REFERENCES commerce_orders(id),
 player_id TEXT NOT NULL REFERENCES players(id), app_id INTEGER NOT NULL,
 sandbox INTEGER NOT NULL CHECK(sandbox IN (0,1)), invoice_id TEXT NOT NULL,
 purchase_id TEXT NOT NULL, coins INTEGER NOT NULL CHECK(coins>0), created_at INTEGER NOT NULL,
 UNIQUE(app_id,sandbox,invoice_id), UNIQUE(app_id,sandbox,purchase_id));
CREATE TABLE commerce_delivery_ack (
 order_id TEXT PRIMARY KEY REFERENCES commerce_orders(id),
 state TEXT NOT NULL CHECK(state IN ('Pending','Acknowledged','RefundReview')),
 updated_at INTEGER NOT NULL);
'''

WALLET_V3 = '''
CREATE TABLE wallets (
 player_id TEXT PRIMARY KEY REFERENCES players(id), initialized INTEGER NOT NULL CHECK(initialized IN (0,1)),
 revision INTEGER NOT NULL DEFAULT 0, balances TEXT NOT NULL, next_life_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE wallet_ledger (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
 player_id TEXT NOT NULL REFERENCES wallets(player_id), origin TEXT NOT NULL, delta_json TEXT NOT NULL,
 revision INTEGER NOT NULL, created_at INTEGER NOT NULL,
 UNIQUE(player_id,origin), UNIQUE(player_id,revision));
CREATE TABLE gameplay_attempts (
 id TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES wallets(player_id), level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 50),
 config_hash TEXT NOT NULL, seed INTEGER NOT NULL, selected_json TEXT NOT NULL,
 moves INTEGER NOT NULL, continues INTEGER NOT NULL DEFAULT 0,
 state TEXT NOT NULL CHECK(state IN ('Reserved','Started','AwaitingContinuation','Won','Lost','Cancelled','Released')),
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
CREATE UNIQUE INDEX one_active_gameplay_attempt ON gameplay_attempts(player_id)
 WHERE state IN ('Reserved','Started','AwaitingContinuation');
'''


# Review 136. Indexes and bookkeeping only: no game data, no schema version change, invisible to
# schema validators (operations._objects filters the prefix) and droppable for a rollback.
PERFORMANCE_PREFIX = 'perf136_'
PERFORMANCE_V136 = (
    'CREATE TABLE IF NOT EXISTS perf136_maintenance (key TEXT PRIMARY KEY, value INTEGER NOT NULL)',
    'CREATE INDEX IF NOT EXISTS perf136_identity_access_family ON identity_access(family_id)',
    'CREATE INDEX IF NOT EXISTS perf136_attempts_player_state ON gameplay_attempts(player_id,state)',
    'CREATE INDEX IF NOT EXISTS perf136_friend_low_state ON social_friend_requests(low_id,state)',
    'CREATE INDEX IF NOT EXISTS perf136_friend_high_state ON social_friend_requests(high_id,state)',
    'CREATE INDEX IF NOT EXISTS perf136_cup_runs_player ON cup_runs(player_id)',
    'CREATE INDEX IF NOT EXISTS perf136_orders_player_state ON commerce_orders(player_id,state)',
    'CREATE INDEX IF NOT EXISTS perf136_credentials_player ON credentials(player_id)',
    'CREATE INDEX IF NOT EXISTS perf136_credentials_expiry ON credentials(expires_at)',
    'CREATE INDEX IF NOT EXISTS perf136_teams_owner ON social_teams(owner_id,created_at)',
    "CREATE INDEX IF NOT EXISTS perf136_team_kicks ON commands(operation) WHERE substr(operation,1,17)='social.team.kick/'",
    'CREATE INDEX IF NOT EXISTS perf136_refresh_used ON identity_refresh(expires_at) WHERE used_request_id IS NOT NULL',
    'CREATE INDEX IF NOT EXISTS perf136_identity_ops_age ON identity_operations(purpose,created_at)',
    "CREATE INDEX IF NOT EXISTS perf136_replay_candidates ON replay_operations(updated_at) WHERE candidate_json IS NOT NULL AND state IN ('Committed','Rejected')",
)


def remove_performance_objects(db):
    """For rolling back to a backend whose validators do not know the prefix."""
    names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='index' AND substr(name,1,8)=?", (PERFORMANCE_PREFIX,))]
    tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND substr(name,1,8)=?", (PERFORMANCE_PREFIX,))]
    for name in names:
        db.execute('DROP INDEX "' + name + '"')
    for name in tables:
        db.execute('DROP TABLE "' + name + '"')
    return len(names) + len(tables)


class WriterGate:
    """First-come writer queue in front of SQLite's unordered sleep-and-retry busy wait."""
    def __init__(self):
        self._mutex = threading.Lock()
        self._waiters = collections.deque()
        self._held = False
        self.waiters = 0
        self.last_progress = 0.0
        self.lock_waits = 0
        self.lock_wait_seconds = 0.0
        self.lock_timeouts = 0

    def acquire(self, timeout):
        began = time.monotonic()
        with self._mutex:
            if not self._held and not self._waiters:
                self._held = True
                self.last_progress = began
                return 0.0
            turn = threading.Event()
            self._waiters.append(turn)
            self.waiters = len(self._waiters)
        if not turn.wait(timeout):
            with self._mutex:
                try:
                    self._waiters.remove(turn)
                except ValueError:
                    pass  # The previous writer handed over at this exact moment.
                else:
                    self.waiters = len(self._waiters)
                    self.lock_timeouts += 1
                    raise sqlite3.OperationalError('database is locked')
        waited = time.monotonic() - began
        with self._mutex:
            self.last_progress = time.monotonic()
            if waited >= .25:
                self.lock_waits += 1
                self.lock_wait_seconds += waited
        return waited

    def release(self):
        with self._mutex:
            self.last_progress = time.monotonic()
            if self._waiters:
                self._waiters.popleft().set()
                self.waiters = len(self._waiters)
            else:
                self._held = False

    def progressing(self, within=5.0):
        with self._mutex:
            return self._held and time.monotonic() - self.last_progress < within


class Database:
    def __init__(self, path, *, _versioned_staging117=False, _sdk_commerce125=False, _open_integrity_check=True):
        self.path = Path(path).resolve()
        self.writer_gate = WriterGate()
        if type(_sdk_commerce125) is not bool or (_sdk_commerce125 and _versioned_staging117):
            raise RuntimeError('Explicit isolated SDK125 storage required')
        self.sdk_commerce125 = _sdk_commerce125
        if _sdk_commerce125 and self.path.is_file() and self.path.stat().st_size:
            from .sdk_schema125 import validate_sdk_database
            # Never turn a live/preexisting ordinary15 root into SDK125 on open.
            with contextlib.closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as existing:
                validate_sdk_database(existing, full=_open_integrity_check)
        if _versioned_staging117:
            # Explicit staging path only. Never create or migrate an authority
            # here: the stopped owner-bound preparation must already exist.
            if not self.path.is_file():
                raise RuntimeError('Prepared staging authority required')
            from .staging_empty_versioned_upgrade117 import _validate16
            with contextlib.closing(sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=10, isolation_level=None)) as db:
                db.execute('PRAGMA foreign_keys=ON')
                db.execute('BEGIN')
                try:
                    _validate16(db)
                finally:
                    db.rollback()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('BEGIN IMMEDIATE')
            try:
                if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_info'").fetchone():
                    for statement in DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                version = [r[0] for r in db.execute('SELECT version FROM schema_info')]
                if version == [1]:
                    for statement in COMMERCE_V2.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=2')
                    version = [2]
                if version == [2]:
                    for statement in WALLET_V3.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=3')
                    version = [3]
                if version == [3]:
                    from .identity_schema import IDENTITY_V4_DDL
                    from .notification_schema import NOTIFICATIONS_V4_DDL
                    for statement in (IDENTITY_V4_DDL + NOTIFICATIONS_V4_DDL).split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=4')
                    version = [4]
                if version == [4]:
                    from .social_schema import SOCIAL_V5_DDL
                    from .messaging_schema import MESSAGING_V5_DDL
                    from .records_schema import RECORDS_V5_DDL
                    from .discovery_schema import DISCOVERY_V5_DDL
                    from .ugc_schema import UGC_V5_DDL
                    for statement in (SOCIAL_V5_DDL + MESSAGING_V5_DDL + RECORDS_V5_DDL + DISCOVERY_V5_DDL + UGC_V5_DDL).split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=5')
                    version = [5]
                if version == [5]:
                    from .replay_schema import REPLAY_V6_DDL
                    for statement in REPLAY_V6_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=6')
                    version = [6]
                if version == [6]:
                    from .newads_schema import NEWADS_V7_DDL
                    for statement in NEWADS_V7_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=7')
                    version = [7]
                if version == [7]:
                    from .region_schema import REGIONS_V8_DDL
                    from .provider_identity_schema import PROVIDER_IDENTITY_V8_DDL
                    from .newads_schema import NEWADS_V8_DDL
                    for statement in (REGIONS_V8_DDL + PROVIDER_IDENTITY_V8_DDL + NEWADS_V8_DDL).split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=8')
                    version = [8]
                if version == [8]:
                    from .commerce_schema import COMMERCE_V9_DDL
                    for statement in COMMERCE_V9_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=9')
                    version = [9]
                if version == [9]:
                    from .provider_signin_schema102 import PROVIDER_SIGNIN_V10_DDL
                    for statement in PROVIDER_SIGNIN_V10_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=10')
                    version = [10]
                if version == [10]:
                    from .teams_schema109 import TEAMS_V11_DDL
                    for statement in TEAMS_V11_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=11')
                    version = [11]
                if version == [11]:
                    from .team_life_schema110 import TEAM_LIFE_V12_DDL
                    for statement in TEAM_LIFE_V12_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=12')
                    version = [12]
                if version == [12]:
                    from .team_mail_schema111 import TEAM_MAIL_V13_DDL
                    for statement in TEAM_MAIL_V13_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=13')
                    version = [13]
                if version == [13]:
                    from .team_invite_schema112 import TEAM_INVITES_V14_DDL
                    for statement in TEAM_INVITES_V14_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=14')
                    version = [14]
                if version == [14]:
                    from .friend_search_schema115 import FRIEND_SEARCH_V15_DDL
                    for statement in FRIEND_SEARCH_V15_DDL.split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('UPDATE schema_info SET version=15')
                    version = [15]
                expected_version = SCHEMA_VERSION
                if _sdk_commerce125:
                    from .sdk_schema125 import SDK_SCHEMA_VERSION, apply_sdk_upgrade
                    if version == [SCHEMA_VERSION]:
                        apply_sdk_upgrade(db)
                        version = [SDK_SCHEMA_VERSION]
                    expected_version = SDK_SCHEMA_VERSION
                if version != [expected_version]:
                    raise RuntimeError('Unsupported backend schema; explicit migration required')
                for statement in PERFORMANCE_V136:
                    db.execute(statement)
                db.commit()
            except BaseException:
                db.rollback()
                raise
            if _open_integrity_check and db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise RuntimeError('Backend database integrity check failed')

    def connect(self, timeout=10):
        db = sqlite3.connect(self.path, timeout=timeout, isolation_level=None)
        try:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA synchronous=FULL')
        except BaseException:
            db.close()
            raise
        return contextlib.closing(db)

    @contextlib.contextmanager
    def transaction(self, timeout=10):
        waited = self.writer_gate.acquire(timeout)
        try:
            with self.connect(timeout=max(.05, timeout - waited)) as db:
                db.execute('BEGIN IMMEDIATE')
                try:
                    yield db
                    db.commit()
                except BaseException:
                    db.rollback()
                    raise
        finally:
            self.writer_gate.release()

    @contextlib.contextmanager
    def read(self, timeout=10):
        """One consistent WAL snapshot. Takes no write lock, waits for no writer and cannot write."""
        with self.connect(timeout=timeout) as db:
            db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN')
            try:
                yield db
            finally:
                if db.in_transaction:
                    db.rollback()
