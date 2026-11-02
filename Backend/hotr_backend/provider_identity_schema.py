"""Additive provider linking tables; no imported wallet or device credentials."""

PROVIDER_IDENTITY_V8_DDL = '''
CREATE TABLE account_provider_links (
 provider TEXT NOT NULL CHECK(provider='vk'), subject_digest TEXT NOT NULL,
 player_id TEXT NOT NULL REFERENCES players(id), linked_at INTEGER NOT NULL,
 PRIMARY KEY(provider,subject_digest), UNIQUE(provider,player_id));
CREATE TABLE account_provider_flows (
 id TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id), request_id TEXT NOT NULL,
 configuration_digest TEXT NOT NULL, state_digest TEXT NOT NULL UNIQUE,
 state_secret TEXT NOT NULL, verifier TEXT NOT NULL,
 phase TEXT NOT NULL CHECK(phase IN ('Pending','Exchanging','Linked','Cancelled','Expired','Failed','Conflict')),
 expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
 UNIQUE(player_id,request_id));
CREATE UNIQUE INDEX one_pending_provider_flow ON account_provider_flows(player_id)
 WHERE phase IN ('Pending','Exchanging');
'''
