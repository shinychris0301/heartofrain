"""Pure additive managed-identity DDL; safe for storage initialization."""
# Root migration applies this constant atomically after the existing schema3.
# Missing account_states rows deliberately mean Active for operator accounts.
IDENTITY_V4_DDL = '''
CREATE TABLE account_states (
 player_id TEXT PRIMARY KEY REFERENCES players(id),
 state TEXT NOT NULL CHECK(state IN ('Active','DeletionRequested')),
 requested_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE identity_devices (
 fingerprint TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id),
 public_key TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
 created_at INTEGER NOT NULL);
CREATE TABLE identity_recovery (
 player_id TEXT PRIMARY KEY REFERENCES players(id), digest TEXT NOT NULL UNIQUE,
 updated_at INTEGER NOT NULL);
CREATE TABLE identity_sessions (
 id TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id),
 key_fingerprint TEXT NOT NULL REFERENCES identity_devices(fingerprint),
 current_refresh_digest TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL,
 last_used_at INTEGER NOT NULL, absolute_expires_at INTEGER NOT NULL,
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)));
CREATE TABLE identity_refresh (
 digest TEXT PRIMARY KEY, family_id TEXT NOT NULL REFERENCES identity_sessions(id),
 expires_at INTEGER NOT NULL, used_request_id TEXT,
 payload_digest TEXT, replacement_digest TEXT);
CREATE TABLE identity_access (
 digest TEXT PRIMARY KEY REFERENCES credentials(digest),
 family_id TEXT NOT NULL REFERENCES identity_sessions(id), created_at INTEGER NOT NULL);
CREATE TABLE identity_recovery_history (
 digest TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id),
 request_id TEXT NOT NULL, payload_digest TEXT NOT NULL,
 replacement_digest TEXT NOT NULL, key_fingerprint TEXT NOT NULL);
CREATE TABLE identity_challenges (
 id TEXT PRIMARY KEY, purpose TEXT NOT NULL CHECK(purpose IN ('guest','session','recover','logout','delete')),
 key_fingerprint TEXT NOT NULL, public_key TEXT NOT NULL,
 request_id TEXT NOT NULL, payload_digest TEXT NOT NULL,
 nonce TEXT NOT NULL UNIQUE, expires_at INTEGER NOT NULL, consumed_at INTEGER NOT NULL DEFAULT 0);
CREATE INDEX identity_challenge_expiry ON identity_challenges(expires_at);
CREATE TABLE identity_operations (
 key_fingerprint TEXT NOT NULL, purpose TEXT NOT NULL, request_id TEXT NOT NULL,
 payload_digest TEXT NOT NULL, player_id TEXT NOT NULL REFERENCES players(id),
 family_id TEXT REFERENCES identity_sessions(id), response_json TEXT NOT NULL,
 created_at INTEGER NOT NULL, PRIMARY KEY(key_fingerprint,purpose,request_id));
CREATE TABLE identity_rate_windows (
 bucket TEXT NOT NULL, window INTEGER NOT NULL, requests INTEGER NOT NULL,
 PRIMARY KEY(bucket,window));
'''
