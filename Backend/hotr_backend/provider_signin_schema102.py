"""Atomic schema9-to10 VK sign-in addition, retaining existing signed challenges."""

PROVIDER_SIGNIN_V10_DDL = '''
ALTER TABLE identity_challenges RENAME TO identity_challenges_v9;
DROP INDEX identity_challenge_expiry;
CREATE TABLE identity_challenges (
 id TEXT PRIMARY KEY, purpose TEXT NOT NULL CHECK(purpose IN ('guest','session','recover','logout','delete','vk')),
 key_fingerprint TEXT NOT NULL, public_key TEXT NOT NULL,
 request_id TEXT NOT NULL, payload_digest TEXT NOT NULL,
 nonce TEXT NOT NULL UNIQUE, expires_at INTEGER NOT NULL, consumed_at INTEGER NOT NULL DEFAULT 0);
INSERT INTO identity_challenges SELECT * FROM identity_challenges_v9;
DROP TABLE identity_challenges_v9;
CREATE INDEX identity_challenge_expiry ON identity_challenges(expires_at);
CREATE TABLE account_provider_signins (
 id TEXT PRIMARY KEY, source_player TEXT NOT NULL REFERENCES players(id),
 source_family TEXT NOT NULL REFERENCES identity_sessions(id), source_fingerprint TEXT NOT NULL,
 request_id TEXT NOT NULL, public_key TEXT NOT NULL, key_fingerprint TEXT NOT NULL,
 completion_digest TEXT NOT NULL, configuration_digest TEXT NOT NULL,
 state_digest TEXT NOT NULL UNIQUE, state_secret TEXT NOT NULL, verifier TEXT NOT NULL,
 phase TEXT NOT NULL CHECK(phase IN ('Pending','Exchanging','Ready','Completed','Cancelled','Expired','Failed','Conflict')),
 subject_digest TEXT NOT NULL DEFAULT '', target_player TEXT REFERENCES players(id),
 expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
 UNIQUE(source_player,request_id));
CREATE UNIQUE INDEX one_pending_provider_signin ON account_provider_signins(source_player)
 WHERE phase IN ('Pending','Exchanging','Ready');
'''
